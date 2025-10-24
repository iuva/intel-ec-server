"""主机管理服务"""

from datetime import datetime, timezone
from typing import Optional, cast

from sqlalchemy import select

from app.models.host import Host
from app.models.host_rec import HostRec
from app.schemas.host import (
    HostStatusUpdate,
    VNCConnectionReport,
)

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HostService:
    """主机管理服务类"""

    @handle_service_errors(error_message="获取主机失败", error_code="HOST_GET_FAILED")
    async def get_host_by_id(self, host_id: str) -> Optional[Host]:
        """根据 host_id 获取主机

        Args:
            host_id: 主机ID

        Returns:
            主机对象，如果不存在则返回 None
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            stmt = select(Host).where(Host.host_id == host_id, Host.del_flag.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if host:
                logger.debug(
                    "查询主机成功",
                    extra={
                        "operation": "get_host_by_id",
                        "host_id": host_id,
                        "status": host.status,
                    },
                )
            else:
                logger.warning(
                    "主机不存在",
                    extra={
                        "operation": "get_host_by_id",
                        "host_id": host_id,
                    },
                )

            return host

    @monitor_operation("host_status_update", record_duration=True)
    @handle_service_errors(error_message="更新主机状态失败", error_code="HOST_STATUS_UPDATE_FAILED")
    async def update_host_status(self, host_id: str, status_data: HostStatusUpdate) -> Host:
        """更新主机状态

        Args:
            host_id: 主机ID
            status_data: 状态更新数据

        Returns:
            更新后的主机对象

        Raises:
            BusinessError: 主机不存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 查询主机
            stmt = select(Host).where(Host.host_id == host_id, Host.del_flag.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                logger.warning(
                    "主机不存在",
                    extra={
                        "operation": "update_host_status",
                        "host_id": host_id,
                        "error_code": "HOST_NOT_FOUND",
                    },
                )
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新状态和心跳时间
            old_status = host.status
            host.status = status_data.status
            host.last_heartbeat = datetime.now(timezone.utc)
            host.updated_time = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(host)

            logger.info(
                "主机状态更新成功",
                extra={
                    "operation": "update_host_status",
                    "host_id": host_id,
                    "old_status": old_status,
                    "new_status": status_data.status,
                },
            )
            return host

    @handle_service_errors(error_message="更新主机心跳失败", error_code="HOST_HEARTBEAT_UPDATE_FAILED")
    async def update_heartbeat(self, host_id: str) -> Host:
        """更新主机心跳时间

        Args:
            host_id: 主机ID

        Returns:
            更新后的主机对象

        Raises:
            BusinessError: 主机不存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 查询主机
            stmt = select(Host).where(Host.host_id == host_id, Host.del_flag.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                logger.warning(
                    "主机不存在",
                    extra={
                        "operation": "update_heartbeat",
                        "host_id": host_id,
                        "error_code": "HOST_NOT_FOUND",
                    },
                )
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新心跳时间和状态
            old_status = host.status
            host.last_heartbeat = datetime.now(timezone.utc)
            if host.status != "online":
                host.status = "online"
            host.updated_time = datetime.now(timezone.utc)

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
            host_rec.subm_time = datetime.now(timezone.utc)

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
                "VNC连接结果上报处理成功",
                extra={
                    "operation": "report_vnc_connection",
                    "user_id": vnc_report.user_id,
                    "host_id": vnc_report.host_id,
                    "connection_status": vnc_report.connection_status,
                    "connection_time": connection_time_str,
                    "old_host_state": old_host_state,
                    "new_host_state": host_rec.host_state,
                    "old_subm_time": old_subm_time_str,
                    "new_subm_time": new_subm_time_str,
                },
            )

            return {
                "host_id": vnc_report.host_id,
                "connection_status": vnc_report.connection_status,
                "connection_time": vnc_report.connection_time,
                "message": "VNC连接结果上报成功，主机已锁定",
            }
