<<<<<<< HEAD
"""Browser Plugin Host Management Service

Provides core business logic for browser plugin host querying, status updates, etc.
"""

from datetime import datetime, timezone
from typing import List, cast

from sqlalchemy import and_, select, update

<<<<<<< HEAD
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
=======
"""浏览器插件主机管理服务

提供浏览器插件使用的主机查询、状态更新等核心业务逻辑。
"""

<<<<<<<< HEAD:services/host-service/app/services/host_service.py
from datetime import datetime
from typing import Optional, cast

from sqlalchemy import select
========
from datetime import datetime, timezone
from typing import List, cast
>>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本):services/host-service/app/services/browser_host_service.py

from app.models.host_exec_log import HostExecLog
from app.models.host_rec import HostRec
<<<<<<<< HEAD:services/host-service/app/services/host_service.py
from app.schemas.host import (
    HostStatusUpdate,
    VNCConnectionReport,
)
========
from app.schemas.host import HostStatusUpdate, RetryVNCHostInfo
from sqlalchemy import and_, select, update
>>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本):services/host-service/app/services/browser_host_service.py
=======
from app.models.host_exec_log import HostExecLog
from app.models.host_rec import HostRec
from app.schemas.host import HostStatusUpdate, RetryVNCHostInfo
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
<<<<<<< HEAD
    # from app.services.agent_websocket_manager import get_agent_websocket_manager  # Moved to local import
    from app.schemas.websocket_message import MessageType
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.host_validators import validate_host_exists
=======
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)

logger = get_logger(__name__)


class BrowserHostService:
<<<<<<< HEAD
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
=======
    """浏览器插件主机管理服务类

<<<<<<<< HEAD:services/host-service/app/services/host_service.py
    @handle_service_errors(error_message="获取主机失败", error_code="HOST_GET_FAILED")
    async def get_host_by_id(self, host_id: str) -> Optional[Host]:
        """根据 host_id 获取主机
========
    负责浏览器插件的主机管理操作，包括查询、状态更新、心跳更新等。
    """

    @handle_service_errors(
        error_message="查询主机信息失败",
        error_code="GET_HOST_FAILED",
    )
    async def get_host_by_id(self, host_id: str) -> dict:
        """根据ID查询主机信息
>>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本):services/host-service/app/services/browser_host_service.py

        Args:
            host_id: 主机ID

        Returns:
            主机信息字典

        Raises:
            BusinessError: 主机不存在时
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
<<<<<<< HEAD
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
=======
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        session_factory = mariadb_manager.get_session()
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
                raise BusinessError(
                    message=f"主机不存在: {host_id}",
                    error_code="HOST_NOT_FOUND",
                    code=404,
                )

            # 更新状态和心跳时间
            old_status = host.status
            host.status = status_data.status
            host.last_heartbeat = datetime.utcnow()
            host.updated_time = datetime.utcnow()
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)

            await session.commit()
            await session.refresh(host)

            logger.info(
<<<<<<< HEAD
                "Host heartbeat updated successfully",
                extra={
                    "host_id": host_id,
                    "updated_time": cast(datetime, host.updated_time).isoformat(),
=======
                "主机状态更新成功",
                extra={
                    "host_id": host_id,
                    "new_host_state": host.host_state,
                    "new_appr_state": host.appr_state,
                },
            )

            return {
                "id": host.id,
                "host_state": host.host_state,
                "appr_state": host.appr_state,
                "updated_at": cast(datetime, host.updated_at).isoformat() if host.updated_at else None,
            }

    @handle_service_errors(
        error_message="更新主机心跳失败",
        error_code="UPDATE_HEARTBEAT_FAILED",
    )
    async def update_heartbeat(self, host_id: str) -> dict:
        """更新主机心跳时间

        Args:
            host_id: 主机ID

        Returns:
            更新后的心跳信息

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        session_factory = mariadb_manager.get_session()
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
                raise BusinessError(
                    message=f"主机不存在: {host_id}",
                    error_code="HOST_NOT_FOUND",
                    code=404,
                )

            # 更新心跳时间和状态
            old_status = host.status
            host.last_heartbeat = datetime.utcnow()
            if host.status != "online":
                host.status = "online"
            host.updated_time = datetime.utcnow()

            await session.commit()
            await session.refresh(host)

            logger.debug(
                "主机心跳更新",
                extra={
                    "operation": "update_heartbeat",
                    "host_id": host_id,
                    "old_status": old_status,
                    "new_status": host.status,
                },
            )
            return host

    @monitor_operation("vnc_connection_report", record_duration=True)
    @handle_service_errors(error_message="VNC连接结果上报失败", error_code="VNC_CONNECTION_REPORT_FAILED")
    async def report_vnc_connection(self, vnc_report: VNCConnectionReport) -> dict:
        """处理浏览器插件上报的VNC连接结果

        功能描述：根据 host_id 更新 host_rec 表，设置 host_state = 1（已锁定），
                 subm_time = 当前时间。如果数据不存在，直接返回"主机不存在"。

        Args:
            vnc_report: VNC连接结果上报数据
                - user_id: 用户ID
                - host_id: 主机ID
                - connection_status: 连接状态 (success/failed)
                - connection_time: 连接时间

        Returns:
            处理结果字典，包含主机ID、连接状态和处理消息

        Raises:
            BusinessError: 主机不存在或处理失败
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 根据 host_id 查询 host_rec 表
            # 注意：host_id 是字符串类型的 ID，对应 host_rec 表的 id 字段
            stmt = select(HostRec).where(
                HostRec.id == int(vnc_report.host_id),
                HostRec.del_flag == 0,  # 未删除的记录
            )
            result = await session.execute(stmt)
            host_rec = result.scalar_one_or_none()

            # 如果主机不存在，返回错误
            if not host_rec:
                logger.warning(
                    "主机记录不存在",
                    extra={
                        "operation": "report_vnc_connection",
                        "host_id": vnc_report.host_id,
                        "user_id": vnc_report.user_id,
                        "error_code": "HOST_NOT_FOUND",
                    },
                )
                raise BusinessError(
                    message=f"主机不存在: {vnc_report.host_id}",
                    error_code="HOST_NOT_FOUND",
                    code=400,  # 改为 400 而不是 404
                )

            # 记录更新前的状态
            old_host_state = host_rec.host_state
            old_subm_time = host_rec.subm_time

            # 根据连接状态更新 host_rec 表
            # 设置 host_state = 1（已锁定），subm_time = 当前时间
            host_rec.host_state = 1  # 已锁定状态
            host_rec.subm_time = datetime.utcnow()

            # 提交更新
            await session.commit()
            await session.refresh(host_rec)

            # 格式化时间戳用于日志记录
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
                "主机心跳更新成功",
                extra={
                    "host_id": host_id,
                    "updated_at": cast(datetime, host.updated_at).isoformat(),
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                },
            )

            return {
                "host_id": host_id,
<<<<<<< HEAD
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
=======
                "heartbeat_at": cast(datetime, host.updated_at).isoformat(),
            }
<<<<<<<< HEAD:services/host-service/app/services/host_service.py
========

    async def update_heartbeat_silent(self, host_id: str) -> bool:
        """静默更新主机心跳时间（用于WebSocket）

        此方法专为 WebSocket 心跳监控设计，失败时不记录 ERROR 日志。
        适用于 host_id 可能不在数据库中的场景。

        Args:
            host_id: 主机ID

        Returns:
            True: 更新成功
            False: 更新失败（主机不存在或ID格式无效）

        Note:
            - 不抛出异常，仅返回成功/失败状态
            - 不记录 ERROR 日志
            - 失败是预期行为，不影响 WebSocket 心跳监控
        """
        try:
            # 验证 ID 格式
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            # ID 格式无效，静默失败
            return False

        try:
            session_factory = mariadb_manager.get_session()
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
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
<<<<<<< HEAD
                    # Host does not exist, silently fail
                    return False

                # ✅ WebSocket update data does not need to set updated_by updater
                # ✅ Do not manually set updated_time, let database auto-update (via onupdate=func.now())
                # Only need to commit transaction, database will automatically update updated_time
=======
                    # 主机不存在，静默失败
                    return False

                # 更新心跳时间
                host.updated_at = datetime.now(timezone.utc)
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                await session.commit()

                return True

        except Exception:
<<<<<<< HEAD
            # Database operation failed, silently fail
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
=======
            # 数据库操作失败，静默失败
            return False

    async def update_tcp_state(self, host_id: str, tcp_state: int) -> bool:
        """更新主机TCP连接状态

        Args:
            host_id: 主机ID (对应 HostRec.id 或 mg_id)
            tcp_state: TCP状态码
                - 0: 关闭 (连接断开)
                - 1: 等待 (心跳超时)
                - 2: 监听 (连接建立成功)

        Returns:
            True: 更新成功
            False: 更新失败（主机不存在或ID格式无效）

        Note:
            - 用于 WebSocket 连接生命周期管理
            - 静默失败，不记录 ERROR 日志
        """
        try:
            # 验证 tcp_state 取值范围
            if tcp_state not in (0, 1, 2):
                logger.warning(
                    f"无效的 tcp_state 值: {tcp_state}",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                    extra={"host_id": host_id, "valid_values": [0, 1, 2]},
                )
                return False

<<<<<<< HEAD
            # Try to convert host_id to integer
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                # If host_id is not integer, try to query through mg_id
                session_factory = self.session_factory
=======
            # 尝试将 host_id 转为整数
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                # 如果 host_id 不是整数，尝试通过 mg_id 查询
                session_factory = mariadb_manager.get_session()
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
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

<<<<<<< HEAD
            # Update tcp_state
            session_factory = self.session_factory
            async with session_factory() as session:
                # ✅ Fix: Do not manually set updated_time, let onupdate=func.now() auto-update
=======
            # 更新 tcp_state
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # ✅ 修复：不手动设置 updated_time，让 onupdate=func.now() 自动更新
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
<<<<<<< HEAD
                    .values(tcp_state=tcp_state)  # Removed manually set updated_time
=======
                    .values(tcp_state=tcp_state)  # 移除手动设置的 updated_time
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
<<<<<<< HEAD
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
=======
                        f"TCP状态已更新: host_id={host_id}, tcp_state={tcp_state}",
                        extra={
                            "host_id": host_id,
                            "tcp_state": tcp_state,
                            "tcp_state_name": {0: "关闭", 1: "等待", 2: "监听"}.get(tcp_state),
                        },
                    )
                    return True
                logger.warning(
                    f"TCP状态更新无匹配行: host_id={host_id}, tcp_state={tcp_state}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "tcp_state": tcp_state,
                        "reason": "记录不存在或已删除",
                    },
                )
                return False

        except Exception as e:
            logger.error(
                f"更新TCP状态异常: host_id={host_id}, tcp_state={tcp_state}, 错误类型={type(e).__name__}, 错误消息={e!s}",
                extra={
                    "host_id": host_id,
                    "tcp_state": tcp_state,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                exc_info=True,
            )
            return False

    @handle_service_errors(
<<<<<<< HEAD
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
=======
        error_message="查询重试 VNC 列表失败",
        error_code="GET_RETRY_VNC_LIST_FAILED",
    )
    async def get_retry_vnc_list(self, user_id: str) -> List[RetryVNCHostInfo]:
        """查询需要重试的 VNC 连接列表

        业务逻辑：
        1. 查询 host_exec_log 表，条件：
           - user_id = 入参的user_id
           - case_state != 2（非成功状态）
           - del_flag = 0（未删除）
        2. 获取这些记录的 host_id
        3. 查询 host_rec 表对应的主机信息
        4. 返回 host_id（主机ID）和 host_acct（重命名为 user_name）

        Args:
            user_id: 用户ID

        Returns:
            重试 VNC 主机信息列表
        """
        logger.info(
            "查询重试 VNC 列表",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
            extra={
                "user_id": user_id,
            },
        )

<<<<<<< HEAD
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
=======
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 查询 host_exec_log 表，获取需要重试的 host_id 列表
            log_stmt = (
                select(HostExecLog.host_id)
                .where(
                    and_(
                        HostExecLog.user_id == user_id,
                        HostExecLog.case_state != 2,  # 非成功状态
                        HostExecLog.del_flag == 0,
                    )
                )
                .distinct()  # 去重，同一个 host_id 可能有多条失败记录
            )

            log_result = await session.execute(log_stmt)
            host_ids = [row[0] for row in log_result.fetchall() if row[0] is not None]

            logger.info(
                "查询到需要重试的主机ID列表",
                extra={
                    "user_id": user_id,
                    "host_id_count": len(host_ids),
                    "host_ids": host_ids,
                },
            )

            # 2. 如果没有需要重试的主机，直接返回空列表
            if not host_ids:
                logger.info(
                    "没有需要重试的 VNC 连接",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                    extra={
                        "user_id": user_id,
                    },
                )
                return []

<<<<<<< HEAD
            logger.info(
                "Found host list that needs retry (JOIN query optimization)",
=======
            # 3. 查询 host_rec 表，获取主机详细信息
            host_stmt = select(HostRec.id, HostRec.host_ip, HostRec.host_acct).where(
                and_(
                    HostRec.id.in_(host_ids),
                    HostRec.del_flag == 0,
                )
            )

            host_result = await session.execute(host_stmt)
            hosts = host_result.fetchall()

            logger.info(
                "查询到主机详细信息",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                extra={
                    "user_id": user_id,
                    "host_count": len(hosts),
                },
            )

<<<<<<< HEAD
            # Build return result
            retry_vnc_list = [
                RetryVNCHostInfo(
                    host_id=str(host[0]),  # ✅ Convert to string to avoid precision loss
                    host_ip=host[1] or "",  # Prevent None value
                    user_name=host[2] or "",  # host_no renamed as user_name
=======
            # 4. 构建返回结果
            retry_vnc_list = [
                RetryVNCHostInfo(
                    host_id=host[0],
                    host_ip=host[1] or "",  # 防止 None 值
                    user_name=host[2] or "",  # host_acct 重命名为 user_name
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                )
                for host in hosts
            ]

            logger.info(
<<<<<<< HEAD
                "Query retry VNC list succeeded",
=======
                "查询重试 VNC 列表成功",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                extra={
                    "user_id": user_id,
                    "total": len(retry_vnc_list),
                },
            )

            return retry_vnc_list

    @handle_service_errors(
<<<<<<< HEAD
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
=======
        error_message="释放主机失败",
        error_code="RELEASE_HOSTS_FAILED",
    )
    async def release_hosts(self, user_id: str, host_list: List[str]) -> int:
        """释放主机 - 逻辑删除执行日志记录

        逻辑删除 host_exec_log 表中符合条件的记录（设置 del_flag = 1）：
        - user_id = 入参的 user_id
        - host_id IN (host_list)
        - del_flag = 0（只删除未删除的记录）

        Args:
            user_id: 用户ID
            host_list: 主机ID列表

        Returns:
            更新的记录数
        """
        logger.info(
            "开始释放主机（逻辑删除）",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
            extra={
                "user_id": user_id,
                "host_count": len(host_list),
                "host_list": host_list,
            },
        )

<<<<<<< HEAD
        # Convert strings in host_list to integers
=======
        # 将 host_list 中的字符串转换为整数
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
        try:
            host_ids = [int(host_id) for host_id in host_list]
        except (ValueError, TypeError) as e:
            logger.error(
<<<<<<< HEAD
                "Host ID format conversion failed",
=======
                "主机ID格式转换失败",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                extra={
                    "user_id": user_id,
                    "host_list": host_list,
                    "error": str(e),
                },
            )
            raise BusinessError(
<<<<<<< HEAD
                message="Invalid host ID format",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        logger.info(
            "Host ID conversion completed",
=======
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        logger.info(
            "主机ID转换完成",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
            extra={
                "user_id": user_id,
                "host_ids": host_ids,
            },
        )

<<<<<<< HEAD
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
=======
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建逻辑删除语句（UPDATE del_flag = 1）
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
            stmt = (
                update(HostExecLog)
                .where(
                    and_(
                        HostExecLog.user_id == user_id,
                        HostExecLog.host_id.in_(host_ids),
<<<<<<< HEAD
                        HostExecLog.del_flag == 0,  # Only update non-deleted records
                    )
                )
                .values(del_flag=1)  # Set as deleted
            )

            logger.info(
                "Executing logical delete operation",
=======
                        HostExecLog.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(del_flag=1)  # 设置为已删除
            )

            logger.info(
                "执行逻辑删除操作",
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                extra={
                    "user_id": user_id,
                    "host_ids": host_ids,
                    "operation": "UPDATE del_flag = 1",
                },
            )

<<<<<<< HEAD
            # Execute update
=======
            # 执行更新
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
            result = await session.execute(stmt)
            await session.commit()

            updated_count = result.rowcount

            logger.info(
<<<<<<< HEAD
                "Host release completed (logical delete)",
                extra={
                    "user_id": user_id,
                    "host_count": len(host_list),
                    "host_rec_updated_count": host_rec_updated_count,
=======
                "释放主机完成（逻辑删除）",
                extra={
                    "user_id": user_id,
                    "host_count": len(host_list),
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
                    "updated_count": updated_count,
                },
            )

<<<<<<< HEAD
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
=======
            return updated_count
>>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本):services/host-service/app/services/browser_host_service.py
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)
