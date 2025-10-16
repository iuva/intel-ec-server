"""主机管理服务"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, select

from app.models.host import Host
from app.schemas.host import HostCreate, HostStatusUpdate, HostUpdate

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HostService:
    """主机管理服务类"""

    async def create_host(self, host_data: HostCreate) -> Host:
        """创建主机

        Args:
            host_data: 主机创建数据

        Returns:
            创建的主机对象

        Raises:
            BusinessError: 主机已存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 检查主机是否已存在
            stmt = select(Host).where(Host.host_id == host_data.host_id, Host.is_deleted.is_(False))
            result = await session.execute(stmt)
            existing_host = result.scalar_one_or_none()

            if existing_host:
                raise BusinessError(
                    message=f"主机已存在: {host_data.host_id}",
                    error_code="HOST_ALREADY_EXISTS",
                )

            # 创建新主机
            new_host = Host(
                host_id=host_data.host_id,
                hostname=host_data.hostname,
                ip_address=host_data.ip_address,
                os_type=host_data.os_type,
                os_version=host_data.os_version,
                status="offline",  # 默认状态为离线
                last_heartbeat=None,
            )

            session.add(new_host)
            await session.commit()
            await session.refresh(new_host)

            logger.info(f"主机创建成功: {new_host.host_id}")
            return new_host

    async def get_host_by_id(self, host_id: str) -> Optional[Host]:
        """根据 host_id 获取主机

        Args:
            host_id: 主机ID

        Returns:
            主机对象，如果不存在则返回 None
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            stmt = select(Host).where(Host.host_id == host_id, Host.is_deleted.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if host:
                logger.debug(f"查询主机成功: {host_id}")
            else:
                logger.warning(f"主机不存在: {host_id}")

            return host

    async def list_hosts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[Host], int]:
        """获取主机列表

        Args:
            page: 页码
            page_size: 每页大小
            status: 状态过滤

        Returns:
            (主机列表, 总数)
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建查询条件
            conditions = [Host.is_deleted.is_(False)]
            if status:
                conditions.append(Host.status == status)

            # 查询总数
            count_stmt = select(func.count(Host.id)).where(*conditions)
            total_result = await session.execute(count_stmt)
            total = total_result.scalar_one()

            # 查询数据
            offset = (page - 1) * page_size
            stmt = select(Host).where(*conditions).order_by(Host.created_at.desc()).offset(offset).limit(page_size)
            result = await session.execute(stmt)
            hosts = result.scalars().all()

            logger.info(f"查询主机列表: page={page}, size={page_size}, total={total}")
            return list(hosts), total

    async def update_host(self, host_id: str, host_data: HostUpdate) -> Host:
        """更新主机信息

        Args:
            host_id: 主机ID
            host_data: 更新数据

        Returns:
            更新后的主机对象

        Raises:
            BusinessError: 主机不存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 查询主机
            stmt = select(Host).where(Host.host_id == host_id, Host.is_deleted.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新字段
            update_data = host_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(host, field, value)

            host.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(host)

            logger.info(f"主机更新成功: {host_id}")
            return host

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
            stmt = select(Host).where(Host.host_id == host_id, Host.is_deleted.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新状态和心跳时间
            host.status = status_data.status
            host.last_heartbeat = datetime.utcnow()
            host.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(host)

            logger.info(f"主机状态更新成功: {host_id} -> {status_data.status}")
            return host

    async def delete_host(self, host_id: str) -> bool:
        """删除主机（软删除）

        Args:
            host_id: 主机ID

        Returns:
            是否删除成功

        Raises:
            BusinessError: 主机不存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 查询主机
            stmt = select(Host).where(Host.host_id == host_id, Host.is_deleted.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 软删除
            host.is_deleted = True
            host.updated_at = datetime.utcnow()

            await session.commit()

            logger.info(f"主机删除成功: {host_id}")
            return True

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
            stmt = select(Host).where(Host.host_id == host_id, Host.is_deleted.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新心跳时间和状态
            host.last_heartbeat = datetime.utcnow()
            if host.status != "online":
                host.status = "online"
            host.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(host)

            logger.debug(f"主机心跳更新: {host_id}")
            return host
