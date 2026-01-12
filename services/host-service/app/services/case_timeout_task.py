"""Case timeout detection scheduled task service

Periodically detects timeout test cases and notifies relevant personnel via email.

Features:
1. Execute timeout detection every 10 minutes
2. Query case_timeout configuration from sys_conf table (cached for 1 hour)
3. Query timeout host_exec_log records (prefer due_time, otherwise use case_timeout)
4. Only query records with notify_state = 0 (not notified) to avoid duplicate notifications
5. Notify relevant personnel via email (send hardware_id, host_ip, begin_time, due_time)
6. After email is sent successfully, update notify_state = 1 (notified) to mark as notified
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
from typing import List, Optional

from sqlalchemy import and_, or_, select, update

# Use try-except to handle path imports
try:
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_LOCKED
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.websocket_message import MessageType
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.logging_helpers import log_operation_start
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_LOCKED
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.websocket_message import MessageType
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.logging_helpers import log_operation_start
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# Cache keys
CACHE_KEY_CASE_TIMEOUT = "sys_conf:case_timeout"
# Cache expiration time: 1 hour (3600 seconds)
CACHE_EXPIRE_CASE_TIMEOUT = 3600


class CaseTimeoutTaskService:
    """Case timeout detection scheduled task service"""

    def __init__(self):
        """Initialize scheduled task service"""
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        # Task execution interval: 10 minutes (600 seconds)
        self.interval: int = 600
        # Record whether configuration missing has been warned (avoid duplicate warnings)
        self._has_warned_missing_config: bool = False
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

    async def start(self) -> None:
        """Start scheduled task"""
        if self._running:
            logger.warning("Scheduled task is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Case timeout detection scheduled task started",
            extra={
                "interval_seconds": self.interval,
                "interval_minutes": self.interval // 60,
            },
        )

    async def stop(self) -> None:
        """Stop scheduled task"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                ***REMOVED***

        logger.info("Case timeout detection scheduled task stopped")

    async def _run_loop(self) -> None:
        """Scheduled task loop"""
        # ✅ Delay first check on service startup to avoid immediately checking historical data causing many warnings
        # Wait 60 seconds before executing first check, giving service time to establish connections
        await asyncio.sleep(60)

        while self._running:
            try:
                # Execute timeout detection
                await self._check_timeout_cases()

                # ✅ Execute VNC connection timeout detection
                await self._check_vnc_connection_timeout()

                # Wait for specified interval
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info("Scheduled task loop cancelled")
                break
            except Exception as e:
                logger.error(
                    "Scheduled task execution exception",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                    exc_info=True,
                )
                # Wait for a period after exception before continuing
                await asyncio.sleep(60)

    async def _check_timeout_cases(self) -> None:
        """Check timeout test cases"""
        try:
            log_operation_start(
                "Detect timeout test cases",
                logger_instance=logger,
            )

            # 1. Get case_timeout configuration (with cache)
            timeout_minutes = await self._get_case_timeout_config()
            if timeout_minutes is None or timeout_minutes <= 0:
                # Only log warning on first detection to avoid duplicate logs
                if not self._has_warned_missing_config:
                    logger.warning(
                        (
                            "case_timeout configuration is invalid or not set, skipping detection. "
                            "Please insert configuration in sys_conf table: "
                            "INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag) "
                            "VALUES ('case_timeout', '30', 'Case timeout (minutes)', 0, 0);"
                        ),
                        extra={"timeout_minutes": timeout_minutes},
                    )
                    self._has_warned_missing_config = True
                else:
                    logger.debug(
                        "case_timeout configuration is invalid or not set, skipping detection",
                        extra={"timeout_minutes": timeout_minutes},
                    )
                return

            # If configuration exists, reset warning flag (configuration may have just been added)
            if self._has_warned_missing_config:
                self._has_warned_missing_config = False

            logger.debug(
                "Retrieved case_timeout configuration",
                extra={"timeout_minutes": timeout_minutes},
            )

            # If configuration exists, reset warning flag (configuration may have just been added)
            if self._has_warned_missing_config:
                self._has_warned_missing_config = False
                logger.info("case_timeout configuration is now effective", extra={"timeout_minutes": timeout_minutes})

            # 2. Query timeout host_exec_log records (prefer due_time, otherwise use case_timeout)
            timeout_cases = await self._query_timeout_cases(timeout_minutes)
            if not timeout_cases:
                logger.debug("No timeout test cases found")
                return

            logger.info(
                "Found timeout test cases",
                extra={
                    "count": len(timeout_cases),
                    "timeout_minutes": timeout_minutes,
                },
            )

            # 3. Send email notifications
            success_count = 0
            failed_count = 0

            for exec_log in timeout_cases:
                if not exec_log.host_id:
                    logger.warning(
                        "Execution log record missing host_id, skipping",
                        extra={"log_id": exec_log.id},
                    )
                    failed_count += 1
                    continue

                # Send email notification
                success = await self._send_timeout_email_notification(exec_log)

                if success:
                    success_count += 1
                    logger.info(
                        "Timeout email notification sent",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                            "tc_id": exec_log.tc_id,
                        },
                    )
                else:
                    failed_count += 1
                    logger.error(
                        "Timeout email notification failed",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )

            logger.info(
                "Timeout detection completed",
                extra={
                    "total": len(timeout_cases),
                    "success": success_count,
                    "failed": failed_count,
                },
            )

        except Exception as e:
            logger.error(
                "Exception detecting timeout test cases",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

    async def _get_case_timeout_config(self) -> Optional[int]:
        """Get case_timeout configuration value (with cache)

        Returns:
            Timeout duration (minutes), returns None if not found or invalid
        """
        try:
            # 1. First get from cache
            cached_value = await redis_manager.get(CACHE_KEY_CASE_TIMEOUT)
            if cached_value is not None:
                # After JSON parsing, may be int or string, convert to int uniformly
                if isinstance(cached_value, int):
                    timeout_minutes = cached_value
                elif isinstance(cached_value, str):
                    try:
                        timeout_minutes = int(cached_value)
                    except (ValueError, TypeError):
                        logger.warning(
                            "case_timeout configuration format in cache is invalid, will retrieve from database"
                        )
                        timeout_minutes = None
                else:
                    logger.warning(
                        "case_timeout configuration type in cache is invalid, will retrieve from database",
                        extra={"cached_type": type(cached_value).__name__},
                    )
                    timeout_minutes = None

                if timeout_minutes is not None:
                    logger.debug(
                        "Retrieved case_timeout configuration from cache",
                        extra={"timeout_minutes": timeout_minutes},
                    )
                    return timeout_minutes

            # 2. Query from database
            session_factory = self.session_factory
            async with session_factory() as session:
                stmt = (
                    select(SysConf)
                    .where(
                        and_(
                            SysConf.conf_key == "case_timeout",
                            SysConf.del_flag == 0,
                            SysConf.state_flag == 0,  # Enabled state
                        )
                    )
                    .limit(1)
                )

                result = await session.execute(stmt)
                sys_conf = result.scalar_one_or_none()

                if not sys_conf or not sys_conf.conf_val:
                    # Lower log level to avoid warning on every scheduled task execution
                    # Specific warning already handled in _check_timeout_cases
                    logger.debug("case_timeout configuration not found")
                    return None

                # 3. Parse configuration value
                try:
                    timeout_minutes = int(sys_conf.conf_val)
                    logger.info(
                        "Retrieved case_timeout configuration from database",
                        extra={"timeout_minutes": timeout_minutes},
                    )

                    # 4. Store in cache (expires in 1 hour)
                    await redis_manager.set(
                        CACHE_KEY_CASE_TIMEOUT,
                        timeout_minutes,
                        expire=CACHE_EXPIRE_CASE_TIMEOUT,
                    )
                    logger.debug(
                        "case_timeout configuration cached",
                        extra={
                            "timeout_minutes": timeout_minutes,
                            "expire_seconds": CACHE_EXPIRE_CASE_TIMEOUT,
                        },
                    )

                    return timeout_minutes

                except (ValueError, TypeError):
                    logger.error(
                        "case_timeout configuration value format is invalid (should be integer)",
                        extra={"conf_val": sys_conf.conf_val},
                    )
                    return None

        except Exception as e:
            logger.error(
                "Exception getting case_timeout configuration",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return None

    async def _query_timeout_cases(self, timeout_minutes: int) -> List[HostExecLog]:
        """Query timeout host_exec_log records

        Timeout judgment logic:
        1. If due_time exists, check if due_time < current time
        2. If due_time does not exist, check if begin_time < current time - timeout_minutes
        3. Only query records with notify_state = 0 (not notified) to avoid duplicate notifications

        Args:
            timeout_minutes: Timeout duration (minutes, used when due_time does not exist)

        Returns:
            List of timeout execution log records (only includes unnotified records)
        """
        try:
            now = datetime.now(timezone.utc)
            timeout_threshold = now - timedelta(minutes=timeout_minutes)

            session_factory = self.session_factory
            async with session_factory() as session:
                # Query conditions:
                # - host_state in (2, 3)  # Occupied or case executing
                # - case_state = 1        # Started
                # - del_flag = 0          # Not deleted
                # - notify_state = 0      # Not notified
                # - (due_time IS NOT NULL AND due_time < current time) OR
                #   (due_time IS NULL AND begin_time < current time - timeout_minutes)
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_state.in_([2, 3]),
                            HostExecLog.case_state == 1,
                            HostExecLog.del_flag == 0,
                            HostExecLog.notify_state == 0,  # Only query unnotified records
                            or_(
                                and_(
                                    HostExecLog.due_time.is_not(None),
                                    HostExecLog.due_time < now,
                                ),
                                and_(
                                    HostExecLog.due_time.is_(None),
                                    HostExecLog.begin_time < timeout_threshold,
                                ),
                            ),
                        )
                    )
                    .order_by(HostExecLog.begin_time.asc())
                )

                result = await session.execute(stmt)
                exec_logs = result.scalars().all()

                logger.debug(
                    "Query timeout execution logs",
                    extra={
                        "timeout_minutes": timeout_minutes,
                        "timeout_threshold": timeout_threshold.isoformat(),
                        "now": now.isoformat(),
                        "count": len(exec_logs),
                    },
                )

                return list(exec_logs)

        except Exception as e:
            logger.error(
                "Exception querying timeout execution logs",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timeout_minutes": timeout_minutes,
                },
                exc_info=True,
            )
            return []

    async def _check_vnc_connection_timeout(self) -> None:
        """Check VNC connection timeout

        Business logic:
        1. Query hosts with host_state = 1 (locked) and subm_time - now() > 5 minutes
        2. For each timeout host:
           - Try to notify Agent to go offline via WebSocket
           - If Agent is not online, perform cleanup:
             - Update host_rec table: host_state = 0, subm_time = null
             - Logically delete valid data in host_exec_log table: del_flag = 1
        """
        try:
            log_operation_start(
                "Detect VNC connection timeout",
                logger_instance=logger,
            )

            # 1. Query timeout hosts (host_state = 1 and subm_time - now() > 5 minutes)
            timeout_hosts = await self._query_vnc_timeout_hosts()
            if not timeout_hosts:
                logger.debug("No VNC connection timeout hosts found")
                return

            logger.info(
                "Found VNC connection timeout hosts",
                extra={"count": len(timeout_hosts)},
            )

            # 2. Get WebSocket manager
            ws_manager = get_agent_websocket_manager()

            # 3. Process each timeout host
            success_count = 0
            failed_count = 0

            for host_rec in timeout_hosts:
                try:
                    host_id = host_rec.id
                    host_id_str = str(host_id)

                    # 3.1 Try to notify Agent to go offline
                    offline_notification = {
                        "type": MessageType.HOST_OFFLINE_NOTIFICATION,
                        "host_id": host_id_str,
                        "message": "VNC connection timeout, Host is offline",
                        "reason": "VNC connection timeout (exceeded 5 minutes without establishing connection)",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    # Check if Agent is online
                    is_agent_online = ws_manager.is_connected(host_id_str)

                    if is_agent_online:
                        # Agent is online, send offline notification
                        logger.info(
                            "Agent is online, sending offline notification",
                            extra={
                                "host_id": host_id,
                                "host_id_str": host_id_str,
                            },
                        )
                        notification_sent = await ws_manager.send_to_host(host_id_str, offline_notification)

                        if notification_sent:
                            logger.info(
                                "VNC connection timeout offline notification sent to Agent",
                                extra={
                                    "host_id": host_id,
                                    "host_id_str": host_id_str,
                                },
                            )
                            success_count += 1
                            # Notification sent, wait for Agent to process, do not cleanup immediately
                            continue
                        else:
                            logger.warning(
                                "VNC connection timeout offline notification failed, Agent may have disconnected",
                                extra={
                                    "host_id": host_id,
                                    "host_id_str": host_id_str,
                                },
                            )
                            # Notification failed, perform cleanup
                    else:
                        logger.info(
                            "Agent is not online, skip notification, perform cleanup directly",
                            extra={
                                "host_id": host_id,
                                "host_id_str": host_id_str,
                            },
                        )

                    # 3.2 Agent is not online or notification failed, perform cleanup
                    cleanup_success = await self._cleanup_vnc_timeout_host(host_id)

                    if cleanup_success:
                        success_count += 1
                        logger.info(
                            "VNC connection timeout host cleanup completed",
                            extra={
                                "host_id": host_id,
                                "host_id_str": host_id_str,
                            },
                        )
                    else:
                        failed_count += 1
                        logger.error(
                            "VNC connection timeout host cleanup failed",
                            extra={
                                "host_id": host_id,
                                "host_id_str": host_id_str,
                            },
                        )

                except Exception as e:
                    failed_count += 1
                    logger.error(
                        "Exception processing VNC connection timeout host",
                        extra={
                            "host_id": host_rec.id if host_rec else None,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )

            logger.info(
                "VNC connection timeout detection completed",
                extra={
                    "total": len(timeout_hosts),
                    "success": success_count,
                    "failed": failed_count,
                },
            )

        except Exception as e:
            logger.error(
                "Exception detecting VNC connection timeout",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

    async def _query_vnc_timeout_hosts(self) -> List[HostRec]:
        """Query VNC connection timeout hosts

        Query conditions:
        - host_state = 1 (locked)
        - subm_time IS NOT NULL
        - subm_time < current time - 5 minutes

        Returns:
            List of VNC connection timeout hosts
        """
        try:
            now = datetime.now(timezone.utc)
            timeout_threshold = now - timedelta(minutes=5)  # 5 minutes timeout

            session_factory = self.session_factory
            async with session_factory() as session:
                stmt = (
                    select(HostRec)
                    .where(
                        and_(
                            HostRec.host_state == HOST_STATE_LOCKED,  # Locked state
                            HostRec.subm_time.is_not(None),  # subm_time is not null
                            HostRec.subm_time < timeout_threshold,  # Exceeded 5 minutes
                            HostRec.del_flag == 0,  # Not deleted
                        )
                    )
                    .order_by(HostRec.subm_time.asc())  # Order by subm_time ascending, prioritize earliest timeout
                )

                result = await session.execute(stmt)
                host_recs = result.scalars().all()

                logger.debug(
                    "Query VNC connection timeout hosts",
                    extra={
                        "timeout_threshold": timeout_threshold.isoformat(),
                        "now": now.isoformat(),
                        "count": len(host_recs),
                    },
                )

                return list(host_recs)

        except Exception as e:
            logger.error(
                "Exception querying VNC connection timeout hosts",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return []

    async def _cleanup_vnc_timeout_host(self, host_id: int) -> bool:
        """Cleanup VNC connection timeout host

        Business logic (executed in the same transaction):
        1. Update host_rec table: host_state = 0, subm_time = null
        2. Logically delete valid data in host_exec_log table: del_flag = 1
           - Query condition: host_id = host_id, del_flag = 0

        Args:
            host_id: Host ID

        Returns:
            Whether cleanup succeeded
        """
        try:
            session_factory = self.session_factory
            async with session_factory() as session:
                # ✅ Use transaction to ensure data consistency
                try:
                    # 1. Update host_rec table
                    update_host_stmt = (
                        update(HostRec)
                        .where(
                            and_(
                                HostRec.id == host_id,
                                HostRec.del_flag == 0,
                                HostRec.host_state < 5,  # Protect non-business states
                            )
                        )
                        .values(
                            host_state=HOST_STATE_FREE,  # Set to free
                            subm_time=None,  # Clear subm_time
                        )
                    )
                    await session.execute(update_host_stmt)

                    logger.debug(
                        "host_rec table updated (VNC connection timeout cleanup)",
                        extra={
                            "host_id": host_id,
                            "new_host_state": HOST_STATE_FREE,
                            "subm_time": None,
                        },
                    )

                    # 2. Logically delete valid data in host_exec_log table
                    update_exec_log_stmt = (
                        update(HostExecLog)
                        .where(
                            and_(
                                HostExecLog.host_id == host_id,
                                HostExecLog.del_flag == 0,  # Only update non-deleted records
                            )
                        )
                        .values(del_flag=1)  # Logical delete
                    )
                    exec_log_result = await session.execute(update_exec_log_stmt)

                    deleted_count = exec_log_result.rowcount

                    logger.debug(
                        "host_exec_log table updated (VNC connection timeout cleanup)",
                        extra={
                            "host_id": host_id,
                            "deleted_count": deleted_count,
                        },
                    )

                    # 3. Commit transaction
                    await session.commit()

                    logger.info(
                        "VNC connection timeout host cleanup succeeded (transaction committed)",
                        extra={
                            "host_id": host_id,
                            "deleted_exec_log_count": deleted_count,
                        },
                    )

                    return True

                except Exception as e:
                    # Rollback transaction
                    await session.rollback()
                    logger.error(
                        "VNC connection timeout host cleanup failed, transaction rolled back",
                        extra={
                            "host_id": host_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )
                    return False

        except Exception as e:
            logger.error(
                "Exception cleaning up VNC connection timeout host",
                extra={
                    "host_id": host_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return False

    async def _send_timeout_email_notification(self, exec_log: HostExecLog) -> bool:
        """Send task timeout email notification

        After email is sent successfully, automatically updates notify_state = 1 (notified),
        ensuring the same record will not be notified repeatedly.

        Args:
            exec_log: Execution log record

        Returns:
            Whether notification succeeded (updates notify_state = 1 on success)
        """
        try:
            # 1. Query host_rec table to get hardware_id and host_ip
            session_factory = self.session_factory
            async with session_factory() as session:
                host_stmt = select(HostRec).where(
                    and_(
                        HostRec.id == exec_log.host_id,
                        HostRec.del_flag == 0,
                    )
                )
                host_result = await session.execute(host_stmt)
                host_rec = host_result.scalar_one_or_none()

                if not host_rec:
                    logger.warning(
                        "Host record not found, skipping email notification",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )
                    return False

                hardware_id = host_rec.hardware_id or "-"
                host_ip = host_rec.host_ip or "-"

                # 2. Query sys_conf table to get email configuration
                email_stmt = (
                    select(SysConf)
                    .where(
                        and_(
                            SysConf.conf_key == "email",
                            SysConf.state_flag == 0,
                            SysConf.del_flag == 0,
                        )
                    )
                    .order_by(SysConf.updated_time.desc())
                    .limit(1)
                )
                email_result = await session.execute(email_stmt)
                email_conf = email_result.scalar_one_or_none()

                if not email_conf or not email_conf.conf_val:
                    logger.warning(
                        "Email configuration not found, skipping email notification",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )
                    return False

                # 3. Parse email list
                email_str = email_conf.conf_val.strip()
                email_list = [e.strip() for e in email_str.split(",") if e.strip()]

                if not email_list:
                    logger.warning(
                        "Email list is empty, skipping email notification",
                        extra={"host_id": exec_log.host_id, "log_id": exec_log.id},
                    )
                    return False

                # 4. Build email content
                begin_time_str = exec_log.begin_time.isoformat() if exec_log.begin_time else "-"
                due_time_str = exec_log.due_time.isoformat() if exec_log.due_time else "-"

                subject = t(
                    "email.case.timeout.subject",
                    locale="zh_CN",
                    default="Test case execution timeout notification",
                )

                content = self._build_timeout_email_content(
                    hardware_id=hardware_id,
                    host_ip=host_ip,
                    begin_time=begin_time_str,
                    due_time=due_time_str,
                    tc_id=exec_log.tc_id or "-",
                    log_id=exec_log.id,
                )

                # 5. Send email
                email_result = await send_email(
                    to_emails=email_list,
                    subject=subject,
                    content=content,
                    locale="zh_CN",
                )

                if email_result.get("sent_count", 0) > 0:
                    # 6. After email is sent successfully, update notify_state = 1 (notified)
                    update_stmt = update(HostExecLog).where(HostExecLog.id == exec_log.id).values(notify_state=1)
                    await session.execute(update_stmt)
                    await session.commit()

                    logger.info(
                        "Timeout email notification sent successfully, notification state updated",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                            "sent_count": email_result.get("sent_count", 0),
                            "recipient_count": len(email_list),
                            "notify_state": 1,
                        },
                    )
                    return True
                else:
                    logger.error(
                        "Timeout email notification failed",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                            "errors": email_result.get("errors", []),
                        },
                    )
                    return False

        except Exception as e:
            logger.error(
                "Exception sending timeout email notification",
                extra={
                    "host_id": exec_log.host_id,
                    "log_id": exec_log.id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return False

    def _build_timeout_email_content(
        self,
        hardware_id: str,
        host_ip: str,
        begin_time: str,
        due_time: str,
        tc_id: str,
        log_id: int,
    ) -> str:
        """Build timeout email content

        Args:
            hardware_id: Hardware ID
            host_ip: Host IP
            begin_time: Start time
            due_time: Expected end time
            tc_id: Test case ID
            log_id: Execution log ID

        Returns:
            HTML formatted email content
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #FF6B6B;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
            margin-bottom: 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 5px 5px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #FF6B6B;
        }}
        .info-item {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}
        .info-item::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #FF6B6B;
            font-weight: bold;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
        }}
        .info-value {{
            color: #333;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #888;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">Test Case Execution Timeout Notification</h2>
    </div>
    <div class="content">
        <p style="font-size: 16px; margin-top: 0;">Dear Maintenance Staff:</p>

        <p style="font-size: 15px; color: #2c3e50; margin: 20px 0;">
            Test case execution timeout detected, please pay attention.
        </p>

        <div class="section">
            <div class="section-title">Timeout Task Information</div>
            <div class="info-item">
                <span class="info-label">Hardware ID：</span>
                <span class="info-value">{hardware_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Host IP：</span>
                <span class="info-value">{host_ip}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Test Case ID:</span>
                <span class="info-value">{tc_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Execution Log ID:</span>
                <span class="info-value">{log_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Start Time:</span>
                <span class="info-value">{begin_time}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Expected End Time:</span>
                <span class="info-value">{due_time}</span>
            </div>
        </div>

        <p style="margin-top: 25px; color: #555;">
            Please pay attention to the execution status of related tasks in a timely manner.
        </p>

        <div class="footer">
            This email is automatically sent by the system, please do not reply.
        </div>
    </div>
</body>
</html>
"""


# Global scheduled task service instance (singleton)
_case_timeout_task_instance: Optional[CaseTimeoutTaskService] = None


def get_case_timeout_task_service() -> CaseTimeoutTaskService:
    """Get Case timeout detection scheduled task service instance (singleton)

    Returns:
        CaseTimeoutTaskService instance
    """
    global _case_timeout_task_instance

    if _case_timeout_task_instance is None:
        _case_timeout_task_instance = CaseTimeoutTaskService()
        logger.info("Case timeout detection scheduled task service instance created")

    return _case_timeout_task_instance
