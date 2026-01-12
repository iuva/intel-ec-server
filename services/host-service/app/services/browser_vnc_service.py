"""Browser Plugin VNC Connection Management Service

Provides VNC connection related business logic services for browser plugins, including:
- Process VNC connection result reporting
- Get host VNC connection information
"""

from datetime import datetime, timezone
from typing import Optional, cast

from sqlalchemy import and_, select, update

from app.models.host_exec_log import HostExecLog
from app.models.host_rec import HostRec
from app.schemas.host import VNCConnectionReport

# Use try-except to handle path imports
try:
    from app.schemas.websocket_message import MessageType
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.cache_invalidation import invalidate_available_hosts_cache
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.schemas.websocket_message import MessageType
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.cache_invalidation import invalidate_available_hosts_cache
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists

# RealVNC encryption dependency
try:
    from Crypto.Cipher import DES
except ImportError:
    DES = None  # type: ignore

logger = get_logger(__name__)


def _reverse_bits(byte_val: int) -> int:
    """Reverse bit order in byte

    Args:
        byte_val: Byte value to reverse (0-255)

    Returns:
        Byte value after bit reversal
    """
    result = 0
    for i in range(8):
        if byte_val & (1 << i):
            result |= 1 << (7 - i)
    return result


def _realvnc_encrypt_***REMOVED***word(***REMOVED***word: str) -> str:
    """RealVNC ***REMOVED***word encryption algorithm

    This algorithm uses a fixed DES key to encrypt the ***REMOVED***word, ***REMOVED***word is divided into multiple 8-byte blocks:
    1. First block: First 8 characters of ***REMOVED***word (pad with null bytes if less than 8)
    2. Second block: Characters 9-16 of ***REMOVED***word (pad with null bytes if less than 8)
    3. Third block: Characters 17-24 of ***REMOVED***word (pad with null bytes if less than 8)

    Args:
        ***REMOVED***word: Password to encrypt

    Returns:
        Hexadecimal string (length depends on ***REMOVED***word length)

    Raises:
        BusinessError: When DES encryption library is not installed
    """
    if DES is None:
        raise BusinessError(
            message="RealVNC encryption requires pycryptodome library, please install: pip install pycryptodome",
            error_code="REALVNC_ENCRYPTION_LIBRARY_MISSING",
            code=ServiceErrorCodes.HOST_REALVNC_ENCRYPTION_LIBRARY_MISSING,
            http_status_code=500,
        )

    # Fixed DES key used by RealVNC
    REALVNC_DES_KEY = bytes([0x17, 0x52, 0x6B, 0x06, 0x23, 0x4E, 0x58, 0x07])

    # Bit reverse the fixed key (special requirement of VNC protocol)
    reversed_key = bytes([_reverse_bits(b) for b in REALVNC_DES_KEY])

    # Create DES encryptor
    cipher = DES.new(reversed_key, DES.MODE_ECB)

    # Divide ***REMOVED***word into 8-byte blocks for encryption
    encrypted_blocks = []

    # Calculate number of blocks needed (at least 2 blocks, at most 3 blocks)
    block_count = max(2, min(3, (len(***REMOVED***word) + 7) // 8))

    for i in range(block_count):
        start_pos = i * 8
        end_pos = start_pos + 8

        # Get ***REMOVED***word chunk for current block
        ***REMOVED***word_chunk = ***REMOVED***word[start_pos:end_pos]

        # Pad to 8 bytes
        block = ***REMOVED***word_chunk.ljust(8, "\x00").encode("ascii")

        # Encrypt current block
        encrypted_block = cipher.encrypt(block)
        encrypted_blocks.append(encrypted_block)

    # Concatenate all encryption results and convert to hexadecimal string
    result = b"".join(encrypted_blocks).hex().lower()

    return result


class BrowserVNCService:
    """Browser Plugin VNC Connection Management Service Class

    Responsible for handling VNC connection related business logic for browser plugins,
    including connection result reporting and connection information retrieval.

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
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    @handle_service_errors(
        error_message="Failed to report VNC connection result",
        error_code="REPORT_VNC_FAILED",
    )
    async def report_vnc_connection(self, vnc_report: VNCConnectionReport) -> dict:
        """Process VNC connection result reported by browser plugin

        Function description:
        1. Verify host exists based on host_id
        2. If connection_status = "success":
           - Query host_exec_log table (user_id, tc_id, cycle_name, user_name, host_id, del_flag=0)
           - If old record exists: First logically delete old record (del_flag=1)
           - Whether old record exists or not: Add a new record (host_state=1, case_state=0)
        3. Update host_rec table: host_state = 1, subm_time = current time

        Args:
            vnc_report: VNC connection result report data
                - user_id: User ID
                - tc_id: Test execution ID
                - cycle_name: Cycle name
                - user_name: User name
                - host_id: Host ID
                - connection_status: Connection status (success/failed)
                - connection_time: Connection time

        Returns:
            Processing result dictionary, containing host ID, connection status and processing message

        Raises:
            BusinessError: When host does not exist or processing fails
        """
        # Convert host_id to integer
        try:
            host_id_int = int(vnc_report.host_id)
        except (ValueError, TypeError):
            logger.warning(
                "Host ID format error",
                extra={
                    "host_id": vnc_report.host_id,
                    "error": "not a valid integer",
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
            # 1. Use utility function to validate host exists and not deleted
            host_rec = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            # Record state before update
            old_host_state = host_rec.host_state
            old_subm_time = host_rec.subm_time

            # 2. If connection status is success, process host_exec_log table
            exec_log_action = None  # Record operation type: deleted_and_created/created
            if vnc_report.connection_status == "success":
                # Query host_exec_log table
                log_stmt = select(HostExecLog).where(
                    and_(
                        HostExecLog.user_id == vnc_report.user_id,
                        HostExecLog.tc_id == vnc_report.tc_id,
                        HostExecLog.cycle_name == vnc_report.cycle_name,
                        HostExecLog.user_name == vnc_report.user_name,
                        HostExecLog.host_id == host_id_int,
                        HostExecLog.del_flag == 0,
                    )
                )
                log_result = await session.execute(log_stmt)
                logs = log_result.scalars().all()

                if len(logs) > 1:
                    logger.warning(
                        "Found multiple execution logs, cannot continue",
                        extra={
                            "user_id": vnc_report.user_id,
                            "host_id": vnc_report.host_id,
                            "count": len(logs),
                        },
                    )
                    raise BusinessError(
                        message="Multiple incomplete execution logs exist, please contact administrator",
                        error_code="MULTIPLE_EXEC_LOGS_FOUND",
                        code=ServiceErrorCodes.HOST_MULTIPLE_EXEC_LOGS_FOUND,
                        http_status_code=409,
                    )

                existing_log = logs[0] if logs else None

                if existing_log:
                    # Record exists: First logically delete
                    logger.info(
                        "Found existing execution log, performing logical delete first",
                        extra={
                            "log_id": existing_log.id,
                            "user_id": vnc_report.user_id,
                            "host_id": vnc_report.host_id,
                        },
                    )

                    update_stmt = update(HostExecLog).where(HostExecLog.id == existing_log.id).values(del_flag=1)
                    await session.execute(update_stmt)
                    exec_log_action = "deleted_and_created"
                else:
                    logger.info(
                        "No existing execution log found",
                        extra={
                            "user_id": vnc_report.user_id,
                            "host_id": vnc_report.host_id,
                        },
                    )
                    exec_log_action = "created"

                # Whether old record exists or not, add a new record
                logger.info(
                    "Creating new execution log record",
                    extra={
                        "user_id": vnc_report.user_id,
                        "host_id": vnc_report.host_id,
                    },
                )

                new_log = HostExecLog(
                    host_id=host_id_int,
                    user_id=vnc_report.user_id,
                    tc_id=vnc_report.tc_id,
                    cycle_name=vnc_report.cycle_name,
                    user_name=vnc_report.user_name,
                    host_state=1,  # Locked
                    case_state=0,  # Free
                    begin_time=datetime.now(timezone.utc),
                    del_flag=0,
                )
                session.add(new_log)

            # 3. Update host_rec table
            host_rec.host_state = 1  # Locked state
            host_rec.subm_time = datetime.now(timezone.utc)

            # Commit all changes
            await session.commit()
            await session.refresh(host_rec)

            # ✅ Optimization: If connection status is success, clear available host list cache
            # Because host state has changed to locked, it should no longer appear in available host list
            if vnc_report.connection_status == "success":
                try:
                    deleted_count = await invalidate_available_hosts_cache()
                    if deleted_count > 0:
                        logger.info(
                            "Available host list cache cleared (VNC connection succeeded)",
                            extra={
                                "host_id": vnc_report.host_id,
                                "deleted_cache_count": deleted_count,
                            },
                        )
                    else:
                        logger.debug(
                            "No available host list cache found to clear",
                            extra={"host_id": vnc_report.host_id},
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to clear available host list cache",
                        extra={
                            "host_id": vnc_report.host_id,
                            "error": str(e),
                        },
                    )

            # Format timestamps for logging
            new_subm_time_str: Optional[str] = None
            if host_rec.subm_time is not None:
                new_subm_time_str = cast(datetime, host_rec.subm_time).isoformat()

            old_subm_time_str: Optional[str] = None
            if old_subm_time is not None:
                old_subm_time_str = cast(datetime, old_subm_time).isoformat()

            connection_time_str: Optional[str] = None
            if vnc_report.connection_time is not None:
                connection_time_str = cast(datetime, vnc_report.connection_time).isoformat()

            logger.info(
                "VNC connection result report processing succeeded",
                extra={
                    "operation": "report_vnc_connection",
                    "user_id": vnc_report.user_id,
                    "tc_id": vnc_report.tc_id,
                    "cycle_name": vnc_report.cycle_name,
                    "user_name": vnc_report.user_name,
                    "host_id": vnc_report.host_id,
                    "connection_status": vnc_report.connection_status,
                    "connection_time": connection_time_str,
                    "old_host_state": old_host_state,
                    "new_host_state": host_rec.host_state,
                    "old_subm_time": old_subm_time_str,
                    "new_subm_time": new_subm_time_str,
                    "exec_log_action": exec_log_action,
                },
            )

            # ✅ If connection status is success, notify Agent via WebSocket to start log monitoring
            # Use case-insensitive comparison to ensure "success", "Success", "SUCCESS" all match
            connection_status_lower = vnc_report.connection_status.lower() if vnc_report.connection_status else ""
            if connection_status_lower == "success":
                logger.info(
                    "Preparing to send WebSocket notification to Agent",
                    extra={
                        "host_id": vnc_report.host_id,
                        "connection_status": vnc_report.connection_status,
                        "user_id": vnc_report.user_id,
                        "tc_id": vnc_report.tc_id,
                    },
                )
                try:
                    ws_manager = get_agent_websocket_manager()
                    host_id_str = str(vnc_report.host_id)

                    # Check if Agent is connected
                    if not ws_manager.is_connected(host_id_str):
                        logger.warning(
                            "Agent not connected, cannot send WebSocket notification",
                            extra={
                                "host_id": host_id_str,
                                "user_id": vnc_report.user_id,
                                "tc_id": vnc_report.tc_id,
                                "active_connections": ws_manager.get_connection_count(),
                            },
                        )
                    else:
                        # Build connection notification message
                        connection_notification = {
                            "type": MessageType.CONNECTION_NOTIFICATION,
                            "host_id": host_id_str,
                            "message": "VNC connection succeeded, please start log monitoring",
                            "action": "start_log_monitoring",
                            "details": {
                                "user_id": vnc_report.user_id,
                                "tc_id": vnc_report.tc_id,
                                "cycle_name": vnc_report.cycle_name,
                                "user_name": vnc_report.user_name,
                                "connection_time": connection_time_str,
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

                        logger.debug(
                            "Preparing to send WebSocket notification message",
                            extra={
                                "host_id": host_id_str,
                                "message_type": MessageType.CONNECTION_NOTIFICATION,
                                "message": connection_notification,
                            },
                        )

                        # Send notification
                        success = await ws_manager.send_to_host(host_id_str, connection_notification)
                        if success:
                            logger.info(
                                "Connection notification sent to Agent",
                                extra={
                                    "host_id": host_id_str,
                                    "user_id": vnc_report.user_id,
                                    "tc_id": vnc_report.tc_id,
                                    "message_type": MessageType.CONNECTION_NOTIFICATION,
                                },
                            )
                        else:
                            logger.warning(
                                "Connection notification send failed (Agent may not be connected or send failed)",
                                extra={
                                    "host_id": host_id_str,
                                    "user_id": vnc_report.user_id,
                                    "tc_id": vnc_report.tc_id,
                                    "message_type": MessageType.CONNECTION_NOTIFICATION,
                                    "is_connected": ws_manager.is_connected(host_id_str),
                                },
                            )
                except Exception as e:
                    # Notification send failure does not affect main flow, only log warning
                    logger.error(
                        "Exception sending connection notification",
                        extra={
                            "host_id": vnc_report.host_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "connection_status": vnc_report.connection_status,
                        },
                        exc_info=True,
                    )
            else:
                logger.debug(
                    "Connection status is not success, skipping WebSocket notification",
                    extra={
                        "host_id": vnc_report.host_id,
                        "connection_status": vnc_report.connection_status,
                        "connection_status_lower": connection_status_lower,
                    },
                )

            return {
                "host_id": vnc_report.host_id,
                "connection_status": vnc_report.connection_status,
                "connection_time": vnc_report.connection_time,
            }

    @handle_service_errors(
        error_message="Failed to get VNC connection information",
        error_code="GET_VNC_CONNECTION_FAILED",
    )
    async def get_vnc_connection_info(self, host_rec_id: str) -> dict:
        """Get VNC connection information for specified host

        Business logic:
        1. If host_rec_id = "1111111", return mock data (don't query database)
        2. Otherwise, query host_rec table based on host_rec_id
        3. Check data validity (del_flag=0, appr_state=1)
        4. Update host state to locked (host_state = 1)
        5. Return fields required for VNC connection

        Args:
            host_rec_id: Host record ID

        Returns:
            Dictionary containing VNC connection information
            {
                "ip": "192.168.101.118",
                "port": "5900",
                "username": "neusoft",
                "***REMOVED***word": "***REMOVED***"
            }

        Raises:
            BusinessError: When host does not exist or data is invalid
        """
        logger.info(
            "Starting to get VNC connection information",
            extra={
                "operation": "get_vnc_connection_info",
                "host_rec_id": host_rec_id,
            },
        )

        # ✅ If host_rec_id = "1111111", return mock data (don't query database)
        if host_rec_id == "1111111":
            logger.info(
                "Using mock data (test host ID: 1111111)",
                extra={
                    "operation": "get_vnc_connection_info",
                    "host_rec_id": host_rec_id,
                    "is_mock_data": True,
                },
            )
            return {
                "ip": "10.239.168.184",
                "port": "5900",
                "username": "ccr\\sys_eval",
                "***REMOVED***word": "***REMOVED***",
            }

        try:
            # Convert string ID to integer
            try:
                host_id = int(host_rec_id)
            except (ValueError, TypeError):
                logger.warning(
                    "Host ID format error",
                    extra={
                        "host_rec_id": host_rec_id,
                        "error": "not a valid integer",
                    },
                )
                raise BusinessError(
                    message="Invalid host ID format",
                    error_code="INVALID_HOST_ID",
                    code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                    http_status_code=400,
                )

            # Query host record (using cached session factory)
            session_factory = self.session_factory
            async with session_factory() as session:
                # Use utility function to validate host exists and not deleted
                host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

                # Check if host is enabled (appr_state == 1)
                if host_rec.appr_state != 1:
                    logger.warning(
                        "Host not enabled",
                        extra={
                            "host_rec_id": host_rec_id,
                            "appr_state": host_rec.appr_state,
                            "error": "host not enabled",
                        },
                    )
                    raise BusinessError(
                        message="Host not enabled",
                        message_key="error.host.not_enabled",
                        error_code="HOST_NOT_ENABLED",
                        code=ServiceErrorCodes.HOST_NOT_FOUND,
                        http_status_code=400,
                    )

                # ✅ Check host state: Only business states (< 4) allow VNC connection
                if host_rec.host_state is not None and host_rec.host_state >= 4:
                    logger.warning(
                        "Host in non-business state, VNC connection prohibited",
                        extra={
                            "host_rec_id": host_rec_id,
                            "host_state": host_rec.host_state,
                        },
                    )
                    raise BusinessError(
                        message="Current host state does not support VNC connection",
                        error_code="HOST_STATE_NOT_ALLOWED",
                        code=ServiceErrorCodes.HOST_NOT_Enabled,  # Reuse or similar code
                        http_status_code=400,
                    )

                # Check if VNC connection information is complete
                if not host_rec.host_ip or not host_rec.host_port:
                    logger.warning(
                        "VNC connection information incomplete",
                        extra={
                            "host_rec_id": host_rec_id,
                            "has_ip": bool(host_rec.host_ip),
                            "has_port": bool(host_rec.host_port),
                        },
                    )
                    raise BusinessError(
                        message="VNC connection information incomplete, missing IP address or port",
                        message_key="error.vnc.info_incomplete",
                        error_code="VNC_INFO_INCOMPLETE",
                        code=ServiceErrorCodes.HOST_VNC_INFO_INCOMPLETE,
                        http_status_code=400,
                    )

                # Process ***REMOVED***word: AES decrypt -> RealVNC encrypt
                vnc_***REMOVED***word = ""
                if host_rec.host_pwd:
                    try:
                        # 1. Use AES to decrypt ***REMOVED***word in database
                        ***REMOVED*** = aes_decrypt(host_rec.host_pwd)
                        if ***REMOVED***:
                            logger.debug(
                                "Password AES decryption succeeded",
                                extra={
                                    "host_rec_id": host_rec_id,
                                },
                            )

                            # 2. Use RealVNC encryption algorithm to encrypt ***REMOVED***word
                            vnc_***REMOVED***word = _realvnc_encrypt_***REMOVED***word(***REMOVED***)
                            logger.debug(
                                "Password RealVNC encryption succeeded",
                                extra={
                                    "host_rec_id": host_rec_id,
                                    "***REMOVED***word_length": len(***REMOVED***),
                                    "encrypted_length": len(vnc_***REMOVED***word),
                                },
                            )
                        else:
                            logger.warning(
                                "Password AES decryption returned None",
                                extra={
                                    "host_rec_id": host_rec_id,
                                    "note": "Password format may be incorrect or encryption method mismatch",
                                },
                            )
                    except Exception as e:
                        logger.warning(
                            "Password processing exception (AES decryption or RealVNC encryption)",
                            extra={
                                "host_rec_id": host_rec_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        # Return empty string when ***REMOVED***word processing fails, instead of raising exception
                        vnc_***REMOVED***word = ""

                # ✅ Update host state to locked (host_state = 1)
                old_host_state = host_rec.host_state
                host_rec.host_state = 1  # Locked state
                host_rec.subm_time = datetime.now(timezone.utc)

                # Commit state update
                await session.commit()
                await session.refresh(host_rec)

                logger.info(
                    "Host state updated to locked",
                    extra={
                        "host_rec_id": host_rec_id,
                        "old_host_state": old_host_state,
                        "new_host_state": host_rec.host_state,
                    },
                )

                # ✅ Optimization: Clear available host list cache, because host state has changed to locked
                # This host should no longer appear in available host list, need to clear related cache
                try:
                    deleted_count = await invalidate_available_hosts_cache()
                    if deleted_count > 0:
                        logger.info(
                            "Available host list cache cleared (host state locked)",
                            extra={
                                "host_rec_id": host_rec_id,
                                "deleted_cache_count": deleted_count,
                            },
                        )
                    else:
                        logger.debug(
                            "No available host list cache found to clear",
                            extra={"host_rec_id": host_rec_id},
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to clear available host list cache",
                        extra={
                            "host_rec_id": host_rec_id,
                            "error": str(e),
                        },
                    )

                # Build response data
                vnc_info = {
                    "ip": cast(str, host_rec.host_ip),
                    "port": (str(cast(int, host_rec.host_port)) if host_rec.host_port else "5900"),
                    "username": cast(str, host_rec.host_acct) or "",
                    "***REMOVED***word": vnc_***REMOVED***word,  # Return RealVNC encrypted ***REMOVED***word
                }

                logger.info(
                    "VNC connection information retrieved successfully",
                    extra={
                        "host_rec_id": host_rec_id,
                        "ip": vnc_info["ip"],
                        "port": vnc_info["port"],
                        "username": vnc_info["username"],
                        "host_state": host_rec.host_state,
                    },
                )

                return vnc_info

        except BusinessError:
            # Re-raise business exception
            raise

        except Exception as e:
            logger.error(
                "System exception getting VNC connection information",
                extra={
                    "host_rec_id": host_rec_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Failed to get VNC connection information, please retry later",
                error_code="VNC_GET_FAILED",
                code=ServiceErrorCodes.HOST_VNC_GET_FAILED,
                http_status_code=500,
            )
