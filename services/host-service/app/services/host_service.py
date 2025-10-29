"""主机管理服务

提供主机查询、状态更新等核心业务逻辑。
"""

from datetime import datetime, timezone
from typing import cast

from app.models.host_rec import HostRec
from app.schemas.host import HostStatusUpdate
from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HostService:
    """主机管理服务类

    负责主机的基本管理操作，包括查询、状态更新、心跳更新等。
    """

    @handle_service_errors(
        error_message="查询主机信息失败",
        error_code="GET_HOST_FAILED",
    )
    async def get_host_by_id(self, host_id: str) -> dict:
        """根据ID查询主机信息

        Args:
            host_id: 主机ID

        Returns:
            主机信息字典

        Raises:
            BusinessError: 主机不存在时
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

            logger.info(
                "查询主机信息成功",
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
        error_message="更新主机状态失败",
        error_code="UPDATE_HOST_STATUS_FAILED",
    )
    async def update_host_status(self, host_id: str, status_update: HostStatusUpdate) -> dict:
        """更新主机状态

        Args:
            host_id: 主机ID
            status_update: 状态更新数据

        Returns:
            更新后的主机信息

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

            # 更新主机状态
            if status_update.host_state is not None:
                host.host_state = status_update.host_state

            if status_update.appr_state is not None:
                host.appr_state = status_update.appr_state

            await session.commit()
            await session.refresh(host)

            logger.info(
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

            # 更新心跳时间
            host.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(host)

            logger.info(
                "主机心跳更新成功",
                extra={
                    "host_id": host_id,
                    "updated_at": cast(datetime, host.updated_at).isoformat(),
                },
            )

            return {
                "host_id": host_id,
                "heartbeat_at": cast(datetime, host.updated_at).isoformat(),
            }

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
                    # 主机不存在，静默失败
                    return False

                # 更新心跳时间
                host.updated_at = datetime.now(timezone.utc)
                await session.commit()

                return True

        except Exception:
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
                    extra={"host_id": host_id, "valid_values": [0, 1, 2]},
                )
                return False

            # 尝试将 host_id 转为整数
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                # 如果 host_id 不是整数，尝试通过 mg_id 查询
                session_factory = mariadb_manager.get_session()
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

            # 更新 tcp_state
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(
                        tcp_state=tcp_state,
                        updated_time=datetime.now(timezone.utc),
                    )
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"TCP状态已更新: host_id={host_id}, tcp_state={tcp_state}",
                        extra={
                            "host_id": host_id,
                            "tcp_state": tcp_state,
                            "tcp_state_name": {0: "关闭", 1: "等待", 2: "监听"}.get(tcp_state),
                        },
                    )
                    return True
                else:
                    return False

        except Exception as e:
            logger.error(
                f"更新TCP状态失败: host_id={host_id}, tcp_state={tcp_state}",
                extra={"host_id": host_id, "tcp_state": tcp_state, "error": str(e)},
                exc_info=True,
            )
            return False
