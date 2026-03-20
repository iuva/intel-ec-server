"""Browser Plugin Host Management Service

Provides core business logic for browser plugin host querying, status updates, etc.
"""

from datetime import datetime, timezone
from typing import List, cast

from sqlalchemy import and_, select, update

from app.constants.host_constants import (
    APPR_STATE_ENABLE,
    CASE_STATE_SUCCESS,
    DEL_FLAG_USING,
    HOST_STATE_FREE,
    HOST_STATE_OFFLINE,
    TCP_STATE_LISTEN,
)
from app.models.host_exec_log import HostExecLog
from app.models.host_rec import HostRec
from app.schemas.host import HostStatusUpdate, RetryVNCHostInfo

# Use try-except to handle path imports
try:
    # from app.services.agent_websocket_manager import get_agent_websocket_manager  # Moved to local import
    from app.schemas.websocket_message import MessageType
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.host_validators import validate_host_exists
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    # from app.services.agent_websocket_manager import get_agent_websocket_manager  # Moved to local import
    from app.schemas.websocket_message import MessageType
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.host_validators import validate_host_exists

logger = get_logger(__name__)


class BrowserHostService:
    """Browser Plugin Host Management Service Class

    Responsible for browser plugin host management operations, including querying,
    status updates, heartbeat updates, etc.

    ✅ Optimization: Cache session factory to avoid calling get_session() on every operation
    """

    def __init__(self):
        """Initialize service"""
        # ✅ Optimization: Cache session factory
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)

        ✅ Optimization: Cache session factory to avoid repeated retrieval
        - Initialize on first call
        - Reuse cached factory instance on subsequent calls
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    @handle_service_errors(
        error_message="Failed to query host information",
        error_code="GET_HOST_FAILED",
    )
    async def get_host_by_id(self, host_id: str) -> dict:
        """Query host information by ID

        Args:
            host_id: Host ID

        Returns:
            Host information dictionary

        Raises:
            BusinessError: When host does not exist
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
                message="Invalid host ID format",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            # Use utility function to validate host exists
            host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            logger.info(
                "Query host information succeeded",
                extra={
                    "host_id": host_id,
                    "hardware_id": host.hardware_id,
                },
            )

            return {
                "id": host.id,
                "hardware_id": host.hardware_id,
                "host_acct": host.host_acct,
                "host_ip": host.host_ip,
                "host_port": host.host_port,
                "appr_state": host.appr_state,
                "host_state": host.host_state,
            }

    @handle_service_errors(
        error_message="Failed to update host status",
        error_code="UPDATE_HOST_STATUS_FAILED",
    )
    async def update_host_status(self, host_id: str, status_update: HostStatusUpdate) -> dict:
        """Update host status

        Args:
            host_id: Host ID
            status_update: Status update data

        Returns:
            Updated host information

        Raises:
            BusinessError: When host does not exist or update fails
        """
        # ✅ Record method call start (for debugging)
        status_update_str = status_update.model_dump() if hasattr(status_update, "model_dump") else str(status_update)
        logger.debug(
            f"Starting to update host status: {host_id}",
            extra={
                "host_id": host_id,
                "status_update": status_update_str,
            },
        )

        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError) as e:
            logger.error(
                f"Invalid host ID format: {host_id}",
                extra={
                    "host_id": host_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise BusinessError(
                message="Invalid host ID format",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            try:
                # Use utility function to validate host exists
                logger.debug("Validating host exists", extra={"host_id": host_id, "host_id_int": host_id_int})
                host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")
                logger.debug(
                    f"Host validation succeeded: {host_id}",
                    extra={
                        "host_id": host_id,
                        "host_found": host is not None,
                        "current_host_state": host.host_state if host else None,
                        "current_appr_state": host.appr_state if host else None,
                    },
                )
            except BusinessError as validate_error:
                # BusinessError directly re-raised, but log detailed information
                logger.error(
                    f"Host validation failed (business exception): {host_id}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "error_code": validate_error.error_code,
                        "error_message": validate_error.message,
                        "business_code": validate_error.code,
                        "details": validate_error.details,
                    },
                    exc_info=True,
                )
                raise
            except Exception as validate_error:
                # Host validation failed, log detailed error information
                logger.error(
                    f"Host validation failed (system exception): {host_id}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "error_type": type(validate_error).__name__,
                        "error_message": str(validate_error),
                    },
                    exc_info=True,
                )
                raise

            # Record current status (for debugging)
            old_host_state = host.host_state
            old_appr_state = host.appr_state

            # ✅ Update host status
            # Support two methods:
            # 1. Directly use host_state and appr_state (integers)
            # 2. Use status string (convert to corresponding host_state)
            state_changed = False
            if status_update.host_state is not None:
                if host.host_state != status_update.host_state:
                    host.host_state = status_update.host_state
                    state_changed = True
            elif hasattr(status_update, "status") and status_update.status:
                # Convert string status to host_state
                status_map = {
                    "online": None,  # Online status does not need to update host_state
                    "offline": 4,  # 4 = Offline status
                    "error": None,  # Error status temporarily not handled
                }
                mapped_state = status_map.get(status_update.status.lower())
                if mapped_state is not None and host.host_state != mapped_state:
                    host.host_state = mapped_state
                    state_changed = True

            if status_update.appr_state is not None:
                if host.appr_state != status_update.appr_state:
                    host.appr_state = status_update.appr_state
                    state_changed = True

            # Record status change information (for debugging)
            logger.debug(
                f"Host status update check: {host_id}",
                extra={
                    "host_id": host_id,
                    "old_host_state": old_host_state,
                    "new_host_state": host.host_state,
                    "old_appr_state": old_appr_state,
                    "new_appr_state": host.appr_state,
                    "state_changed": state_changed,
                    "status_update": status_update_str,
                },
            )

            # ✅ Only commit if status actually changed
            if state_changed:
                try:
                    await session.commit()
                    await session.refresh(host)
                    logger.info(
                        "Host status updated successfully",
                        extra={
                            "host_id": host_id,
                            "new_host_state": host.host_state,
                            "new_appr_state": host.appr_state,
                        },
                    )
                except Exception as commit_error:
                    # Commit failed, rollback transaction
                    await session.rollback()
                    logger.error(
                        f"Host status update commit failed: {host_id}",
                        extra={
                            "host_id": host_id,
                            "error_type": type(commit_error).__name__,
                            "error_message": str(commit_error),
                        },
                        exc_info=True,
                    )
                    raise
            else:
                # Status did not change, directly return current status
                logger.debug(
                    f"Host status unchanged, skipping update: {host_id}",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host.host_state,
                        "current_appr_state": host.appr_state,
                    },
                )
                # ✅ Save data to return before session closes
                try:
                    updated_time_str = cast(datetime, host.updated_time).isoformat() if host.updated_time else None
                except Exception as attr_error:
                    # If accessing updated_time fails, log warning but don't raise exception
                    logger.warning(
                        f"Failed to access host.updated_time: {host_id}",
                        extra={
                            "host_id": host_id,
                            "error_type": type(attr_error).__name__,
                            "error_message": str(attr_error),
                        },
                    )
                    updated_time_str = None

                result = {
                    "id": host.id,
                    "host_state": host.host_state,
                    "appr_state": host.appr_state,
                    "updated_time": updated_time_str,
                }
                logger.info(
                    "Host status updated successfully (status unchanged)",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host.host_state,
                        "current_appr_state": host.appr_state,
                    },
                )
                # ✅ Return before session closes to avoid accessing closed session object
                return result

            # ✅ Status has changed, return result before session closes
            try:
                updated_time_str = cast(datetime, host.updated_time).isoformat() if host.updated_time else None
            except Exception as attr_error:
                # If accessing updated_time fails, log warning but don't raise exception
                logger.warning(
                    f"Failed to access host.updated_time: {host_id}",
                    extra={
                        "host_id": host_id,
                        "error_type": type(attr_error).__name__,
                        "error_message": str(attr_error),
                    },
                )
                updated_time_str = None

            result = {
                "id": host.id,
                "host_state": host.host_state,
                "appr_state": host.appr_state,
                "updated_time": updated_time_str,
            }
            return result

    @handle_service_errors(
        error_message="Failed to update host heartbeat",
        error_code="UPDATE_HEARTBEAT_FAILED",
    )
    async def update_heartbeat(self, host_id: str) -> dict:
        """Update host heartbeat time

        Args:
            host_id: Host ID

        Returns:
            Updated heartbeat information

        Raises:
            BusinessError: When host does not exist or update fails
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
                message="Invalid host ID format",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            # Use utility function to validate host exists
            host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            # ✅ WebSocket update data does not need to set updated_by updater
            # ✅ Do not manually set updated_time, let database auto-update (via onupdate=func.now())
            # Only need to commit transaction, database will automatically update updated_time

            await session.commit()
            await session.refresh(host)

            logger.info(
                "Host heartbeat updated successfully",
                extra={
                    "host_id": host_id,
                    "updated_time": cast(datetime, host.updated_time).isoformat(),
                },
            )

            return {
                "host_id": host_id,
                "heartbeat_at": cast(datetime, host.updated_time).isoformat(),
            }

    async def update_heartbeat_silent(self, host_id: str) -> bool:
        """Silently update host heartbeat time (for WebSocket)

        This method is designed specifically for WebSocket heartbeat monitoring,
        does not log ERROR logs on failure.
        Suitable for scenarios where host_id may not exist in database.

        Args:
            host_id: Host ID

        Returns:
            True: Update succeeded
            False: Update failed (host does not exist or ID format invalid)

        Note:
            - Does not raise exceptions, only returns success/failure status
            - Does not log ERROR logs
            - Failure is expected behavior, does not affect WebSocket heartbeat monitoring
        """
        try:
            # Validate ID format
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            # ID format invalid, silently fail
            return False

        try:
            session_factory = self.session_factory
            async with session_factory() as session:
                stmt = select(HostRec).where(
                    and_(
                        HostRec.id == host_id_int,
                        HostRec.del_flag == 0,
                    )
                )

                result = await session.execute(stmt)
                host = result.scalar_one_or_none()

                if not host:
                    # Host does not exist, silently fail
                    return False

                # ✅ WebSocket update data does not need to set updated_by updater
                # ✅ Do not manually set updated_time, let database auto-update (via onupdate=func.now())
                # Only need to commit transaction, database will automatically update updated_time
                await session.commit()

                return True

        except Exception:
            # Database operation failed, silently fail
            return False

    async def restore_offline_to_free_on_heartbeat_silent(self, host_id: str) -> bool:
        """If host is offline (4), set to free (0) — single conditional UPDATE, idempotent.

        Used on Agent WebSocket heartbeat: proves the machine is back; avoids SELECT + UPDATE.
        Returns True only when one row was updated (was offline).
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            return False

        try:
            session_factory = self.session_factory
            async with session_factory() as session:
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                            HostRec.host_state == HOST_STATE_OFFLINE,
                        )
                    )
                    .values(host_state=HOST_STATE_FREE)
                )
                result = await session.execute(stmt)
                await session.commit()
                return bool(result.rowcount and result.rowcount > 0)
        except Exception:
            return False

    async def update_tcp_state(self, host_id: str, tcp_state: int) -> bool:
        """Update host TCP connection state

        Args:
            host_id: Host ID (corresponds to HostRec.id or mg_id)
            tcp_state: TCP state code
                - 0: Closed (connection disconnected)
                - 1: Waiting (heartbeat timeout)
                - 2: Listening (connection established successfully)

        Returns:
            True: Update succeeded
            False: Update failed (host does not exist or ID format invalid)

        Note:
            - Used for WebSocket connection lifecycle management
            - Silent failure, does not log ERROR logs
        """
        try:
            # Validate tcp_state value range
            if tcp_state not in (0, 1, 2):
                logger.warning(
                    f"Invalid tcp_state value: {tcp_state}",
                    extra={"host_id": host_id, "valid_values": [0, 1, 2]},
                )
                return False

            # Try to convert host_id to integer
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                # If host_id is not integer, try to query through mg_id
                session_factory = self.session_factory
                async with session_factory() as session:
                    stmt = select(HostRec).where(
                        and_(
                            HostRec.mg_id == host_id,
                            HostRec.del_flag == 0,
                        )
                    )
                    result = await session.execute(stmt)
                    host = result.scalar_one_or_none()

                    if not host:
                        return False

                    host_id_int = host.id

            # Update tcp_state
            session_factory = self.session_factory
            async with session_factory() as session:
                # ✅ Fix: Do not manually set updated_time, let onupdate=func.now() auto-update
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(tcp_state=tcp_state)  # Removed manually set updated_time
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"TCP state updated: host_id={host_id}, tcp_state={tcp_state}",
                        extra={
                            "host_id": host_id,
                            "tcp_state": tcp_state,
                            "tcp_state_name": {0: "Closed", 1: "Waiting", 2: "Listening"}.get(tcp_state),
                        },
                    )
                    return True
                logger.warning(
                    f"TCP state update no matching rows: host_id={host_id}, tcp_state={tcp_state}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "tcp_state": tcp_state,
                        "reason": "Record does not exist or has been deleted",
                    },
                )
                return False

        except Exception as e:
            logger.error(
                f"Failed to update TCP state: host_id={host_id}, tcp_state={tcp_state}, error: {e!s}",
                exc_info=True,
            )
            return False

    async def update_agent_version(self, host_id: str, agent_version: str) -> bool:
        """Update Agent version number

        Args:
            host_id: Host ID (string, converted to integer)
            agent_version: Agent version number (maximum length 10)

        Returns:
            Whether update succeeded
        """
        try:
            # Validate version number length
            if len(agent_version) > 10:
                logger.warning(
                    (
                        f"Agent version length exceeds limit: host_id={host_id}, "
                        f"version={agent_version}, length={len(agent_version)}"
                    ),
                    extra={
                        "host_id": host_id,
                        "agent_version": agent_version,
                        "version_length": len(agent_version),
                    },
                )
                # Truncate to 10 characters
                agent_version = agent_version[:10]

            # Convert host_id to integer
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Host ID format error: host_id={host_id}",
                    extra={
                        "host_id": host_id,
                        "error": "not a valid integer",
                    },
                )
                return False

            # Update agent_ver
            session_factory = self.session_factory
            async with session_factory() as session:
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(agent_ver=agent_version)
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"Agent version number updated: host_id={host_id}, agent_version={agent_version}",
                        extra={
                            "host_id": host_id,
                            "agent_version": agent_version,
                        },
                    )
                    return True
                logger.warning(
                    f"Agent version number update no matching rows: host_id={host_id}, agent_version={agent_version}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "agent_version": agent_version,
                        "reason": "Record does not exist or has been deleted",
                    },
                )
                return False

        except Exception as e:
            logger.error(
                (f"Failed to update Agent version: host_id={host_id}, agent_version={agent_version}, error: {e!s}"),
                exc_info=True,
            )
            return False

    @handle_service_errors(
        error_message="Failed to query retry VNC list",
        error_code="GET_RETRY_VNC_LIST_FAILED",
    )
    async def get_retry_vnc_list(self, user_id: str) -> List[RetryVNCHostInfo]:
        """Query VNC connection list that needs retry

        Business logic:
        1. Query host_exec_log table with conditions:
           - user_id = input user_id
           - case_state != 2 (non-success state)
           - del_flag = 0 (not deleted)
        2. Get host_id from these records
        3. Query corresponding host information from host_rec table
        4. Return host_id (host ID) and host_no (renamed as user_name)

        Args:
            user_id: User ID

        Returns:
            Retry VNC host information list
        """
        logger.info(
            "Querying retry VNC list",
            extra={
                "user_id": user_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # ✅ Optimization: Use JOIN query to get all data in one query, reduce database round trips
            # Merge original two queries into one JOIN query
            stmt = (
                select(HostRec.id, HostRec.host_ip, HostRec.host_no)
                .select_from(
                    HostExecLog.__table__.join(
                        HostRec.__table__,
                        HostExecLog.host_id == HostRec.id,
                    )
                )
                .where(
                    and_(
                        HostExecLog.user_id == user_id,
                        HostExecLog.case_state != CASE_STATE_SUCCESS,  # Non-success state
                        HostExecLog.del_flag == DEL_FLAG_USING,
                        HostRec.del_flag == DEL_FLAG_USING,
                        HostRec.tcp_state == TCP_STATE_LISTEN,
                        HostRec.host_state < HOST_STATE_OFFLINE,
                        HostRec.appr_state == APPR_STATE_ENABLE,
                    )
                )
                .distinct()  # Deduplicate, same host_id may have multiple failure records
            )

            result = await session.execute(stmt)
            hosts = result.fetchall()

            # If no hosts need retry, directly return empty list
            if not hosts:
                logger.info(
                    "No VNC connections need retry",
                    extra={
                        "user_id": user_id,
                    },
                )
                return []

            logger.info(
                "Found host list that needs retry (JOIN query optimization)",
                extra={
                    "user_id": user_id,
                    "host_count": len(hosts),
                },
            )

            # Build return result
            retry_vnc_list = [
                RetryVNCHostInfo(
                    host_id=str(host[0]),  # ✅ Convert to string to avoid precision loss
                    host_ip=host[1] or "",  # Prevent None value
                    user_name=host[2] or "",  # host_no renamed as user_name
                )
                for host in hosts
            ]

            logger.info(
                "Query retry VNC list succeeded",
                extra={
                    "user_id": user_id,
                    "total": len(retry_vnc_list),
                },
            )

            return retry_vnc_list

    @handle_service_errors(
        error_message="Failed to release hosts",
        error_code="RELEASE_HOSTS_FAILED",
    )
    async def release_hosts(self, user_id: str, host_list: List[str]) -> int:
        """Release hosts - logically delete execution log records and update host status

        Business logic:
        1. Logically delete records in host_exec_log table that meet conditions (set del_flag = 1)
        2. Update host_state = 0 (free state) for corresponding hosts in host_rec table
        3. Notify specified agent through WebSocket

        Args:
            user_id: User ID
            host_list: Host ID list

        Returns:
            Number of updated records
        """
        logger.info(
            "Starting to release hosts (logical delete)",
            extra={
                "user_id": user_id,
                "host_count": len(host_list),
                "host_list": host_list,
            },
        )

        # Convert strings in host_list to integers
        try:
            host_ids = [int(host_id) for host_id in host_list]
        except (ValueError, TypeError) as e:
            logger.error(
                "Host ID format conversion failed",
                extra={
                    "user_id": user_id,
                    "host_list": host_list,
                    "error": str(e),
                },
            )
            raise BusinessError(
                message="Invalid host ID format",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        logger.info(
            "Host ID conversion completed",
            extra={
                "user_id": user_id,
                "host_ids": host_ids,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. First update host_rec table host_state = 0 (free state)
            # ✅ Only hosts with business state (< 5) will be reset to free,
            # avoid affecting hosts in pending/registration state
            update_host_rec_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id.in_(host_ids),
                        HostRec.del_flag == 0,  # Only update non-deleted records
                        HostRec.host_state < 5,  # Protect non-business states
                    )
                )
                .values(host_state=HOST_STATE_FREE)  # 0 = Free state
            )

            logger.info(
                "Executing host_rec table status update operation",
                extra={
                    "user_id": user_id,
                    "host_ids": host_ids,
                    "operation": "UPDATE host_state = 0",
                },
            )

            host_rec_result = await session.execute(update_host_rec_stmt)
            host_rec_updated_count = host_rec_result.rowcount

            logger.info(
                "host_rec table status update completed",
                extra={
                    "user_id": user_id,
                    "host_ids": host_ids,
                    "host_rec_updated_count": host_rec_updated_count,
                },
            )

            # 2. Logically delete host_exec_log records
            stmt = (
                update(HostExecLog)
                .where(
                    and_(
                        HostExecLog.user_id == user_id,
                        HostExecLog.host_id.in_(host_ids),
                        HostExecLog.del_flag == 0,  # Only update non-deleted records
                    )
                )
                .values(del_flag=1)  # Set as deleted
            )

            logger.info(
                "Executing logical delete operation",
                extra={
                    "user_id": user_id,
                    "host_ids": host_ids,
                    "operation": "UPDATE del_flag = 1",
                },
            )

            # Execute update
            result = await session.execute(stmt)
            await session.commit()

            updated_count = result.rowcount

            logger.info(
                "Host release completed (logical delete)",
                extra={
                    "user_id": user_id,
                    "host_count": len(host_list),
                    "host_rec_updated_count": host_rec_updated_count,
                    "updated_count": updated_count,
                },
            )

            # 3. Notify each agent through WebSocket
            try:
                # Local import to avoid circular dependency
                from app.services.agent_websocket_manager import get_agent_websocket_manager

                ws_manager = get_agent_websocket_manager()

                for host_id in host_ids:
                    host_id_str = str(host_id)

                    # Build notification message (using HOST_OFFLINE_NOTIFICATION type)
                    notification_message = {
                        "type": MessageType.HOST_OFFLINE_NOTIFICATION,
                        "host_id": host_id_str,
                        "message": f"Host {host_id_str} has been released, status updated to free",
                        "reason": "host_released",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    # Send notification (if agent not connected, returns False but does not affect main flow)
                    success = await ws_manager.send_to_host(host_id_str, notification_message)
                    if success:
                        logger.info(
                            "Host release notification sent to Agent",
                            extra={
                                "host_id": host_id_str,
                                "user_id": user_id,
                            },
                        )
                    else:
                        logger.debug(
                            "Host release notification send failed (Agent may not be connected)",
                            extra={
                                "host_id": host_id_str,
                                "user_id": user_id,
                            },
                        )
            except Exception as e:
                # WebSocket notification failure does not affect main flow, only log warning
                logger.warning(
                    "Exception sending host release notification",
                    extra={
                        "user_id": user_id,
                        "host_ids": host_ids,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

            return updated_count

    @handle_service_errors(
        error_message="Failed to reset host for test",
        error_code="RESET_HOST_FOR_TEST_FAILED",
    )
    async def reset_host_for_test(self, host_id: str) -> dict:
        """Test reset host - reset host status and delete execution logs

        Reset host to valid state:
        1. Update host_rec table:
           - appr_state = 1 (enabled)
           - host_state = 0 (free)
           - subm_time = null
        2. Logically delete corresponding records in host_exec_log table (del_flag = 1)

        Args:
            host_id: Host ID

        Returns:
            Reset result dictionary, containing host ID, status information and deleted log record count

        Raises:
            BusinessError: When host does not exist or reset fails
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
                message="Invalid host ID format",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            # Validate host exists
            host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            # Record status before reset
            old_appr_state = host.appr_state
            old_host_state = host.host_state
            old_subm_time = host.subm_time

            logger.info(
                "Starting to reset host for test",
                extra={
                    "host_id": host_id,
                    "old_appr_state": old_appr_state,
                    "old_host_state": old_host_state,
                    "old_subm_time": old_subm_time.isoformat() if old_subm_time else None,
                },
            )

            # 1. Update host_rec table
            host.appr_state = APPR_STATE_ENABLE  # 1 = Enabled
            host.host_state = HOST_STATE_FREE  # 0 = Free
            host.subm_time = None  # Set to null

            # 2. Logically delete corresponding records in host_exec_log table
            delete_log_stmt = (
                update(HostExecLog)
                .where(
                    and_(
                        HostExecLog.host_id == host_id_int,
                        HostExecLog.del_flag == 0,  # Only delete non-deleted records
                    )
                )
                .values(del_flag=1)  # Logical delete
            )

            # Execute delete operation
            delete_log_result = await session.execute(delete_log_stmt)
            deleted_log_count = delete_log_result.rowcount

            # Commit transaction
            await session.commit()
            await session.refresh(host)

            logger.info(
                "Test reset host succeeded",
                extra={
                    "host_id": host_id,
                    "old_appr_state": old_appr_state,
                    "new_appr_state": host.appr_state,
                    "old_host_state": old_host_state,
                    "new_host_state": host.host_state,
                    "old_subm_time": old_subm_time.isoformat() if old_subm_time else None,
                    "new_subm_time": None,
                    "deleted_log_count": deleted_log_count,
                },
            )

            return {
                "host_id": host_id,
                "appr_state": host.appr_state,
                "host_state": host.host_state,
                "subm_time": None,
                "deleted_log_count": deleted_log_count,
            }
