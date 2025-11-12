"""
主机验证工具函数

提供主机相关的验证和查询构建功能，减少代码重复。

注意：这些函数需要在服务内部使用，因为它们依赖于服务特定的模型类。
"""

import os
import sys
from typing import Optional, Type, TypeVar

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# 类型变量，用于表示主机模型类
T = TypeVar("T")


async def validate_host_exists(
    session: AsyncSession,
    host_model: Type[T],
    host_id: int,
    locale: str = "zh_CN",
    raise_on_not_found: bool = True,
) -> Optional[T]:
    """验证主机是否存在且未删除

    Args:
        session: 数据库会话
        host_model: 主机模型类（如 HostRec）
        host_id: 主机ID
        locale: 语言代码（用于错误消息）
        raise_on_not_found: 如果主机不存在是否抛出异常

    Returns:
        主机记录，如果不存在且不抛出异常则返回 None

    Raises:
        BusinessError: 如果主机不存在且 raise_on_not_found=True

    Example:
        ```python
        from app.models.host_rec import HostRec

        # 验证主机存在（不存在时抛出异常）
        host_rec = await validate_host_exists(session, HostRec, host_id=123)

        # 验证主机存在（不存在时返回 None）
        host_rec = await validate_host_exists(session, HostRec, host_id=123, raise_on_not_found=False)
        if not host_rec:
            # 处理主机不存在的情况
            ***REMOVED***
        ```
    """
    stmt = select(host_model).where(
        and_(
            host_model.id == host_id,
            host_model.del_flag == 0,  # 只检查未删除的记录
        )
    )
    result = await session.execute(stmt)
    host_rec = result.scalar_one_or_none()

    if not host_rec:
        if raise_on_not_found:
            logger.warning(
                "主机不存在或已删除",
                extra={
                    "host_id": host_id,
                },
            )
            raise BusinessError(
                message=t("error.host.not_found", locale=locale, host_id=host_id),
                message_key="error.host.not_found",
                error_code="HOST_NOT_FOUND",
                code=ServiceErrorCodes.HOST_NOT_FOUND,
                http_status_code=400,
                details={"host_id": host_id},
                locale=locale,
            )
        return None

    return host_rec


def build_host_query(
    host_model: Type[T],
    host_id: Optional[int] = None,
    include_deleted: bool = False,
    host_state: Optional[int] = None,
    appr_state: Optional[int] = None,
    mg_id: Optional[str] = None,
    mac_addr: Optional[str] = None,
) -> Select:
    """构建主机查询语句

    Args:
        host_model: 主机模型类（如 HostRec）
        host_id: 主机ID（可选）
        include_deleted: 是否包含已删除的记录
        host_state: 主机状态（可选）
        appr_state: 审批状态（可选）
        mg_id: 唯一引导ID（可选，支持模糊匹配）
        mac_addr: MAC地址（可选，支持模糊匹配）

    Returns:
        SQLAlchemy Select 语句

    Example:
        ```python
        from app.models.host_rec import HostRec

        # 查询单个主机
        stmt = build_host_query(HostRec, host_id=123)
        result = await session.execute(stmt)
        host = result.scalar_one_or_none()

        # 查询特定状态的主机
        stmt = build_host_query(HostRec, host_state=0, appr_state=1)
        result = await session.execute(stmt)
        hosts = result.scalars().all()
        ```
    """
    conditions = []

    if host_id is not None:
        conditions.append(host_model.id == host_id)

    if not include_deleted:
        conditions.append(host_model.del_flag == 0)

    if host_state is not None:
        conditions.append(host_model.host_state == host_state)

    if appr_state is not None:
        conditions.append(host_model.appr_state == appr_state)

    if mg_id:
        conditions.append(host_model.mg_id.like(f"%{mg_id}%"))

    if mac_addr:
        conditions.append(host_model.mac_addr.like(f"%{mac_addr}%"))

    stmt = select(host_model)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt
