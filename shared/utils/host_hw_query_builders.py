"""
主机硬件记录查询构建器

提供主机硬件记录相关的查询构建功能，减少代码重复。
"""

import os
import sys
from typing import List, Optional

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_hw_rec import HostHwRec

    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from app.models.host_hw_rec import HostHwRec

    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def build_pending_hw_records_query(
    host_id: Optional[int] = None,
    host_ids: Optional[List[int]] = None,
    sync_state: int = 1,
    diff_state: Optional[int] = None,
    include_deleted: bool = False,
) -> Select:
    """构建待审批硬件记录查询语句

    Args:
        host_id: 单个主机ID（可选）
        host_ids: 多个主机ID列表（可选，与 host_id 互斥）
        sync_state: 同步状态（默认：1-待同步）
        diff_state: 参数状态（可选）
        include_deleted: 是否包含已删除的记录

    Returns:
        SQLAlchemy Select 语句（已按 created_time 和 id 倒序排序）

    Example:
        ```python
        # 查询单个主机的待审批硬件记录
        stmt = build_pending_hw_records_query(host_id=123)
        result = await session.execute(stmt)
        hw_recs = result.scalars().all()

        # 查询多个主机的待审批硬件记录
        stmt = build_pending_hw_records_query(host_ids=[123, 456])
        result = await session.execute(stmt)
        hw_recs = result.scalars().all()
        ```
    """
    conditions = []

    if host_id is not None:
        conditions.append(HostHwRec.host_id == host_id)
    elif host_ids is not None:
        conditions.append(HostHwRec.host_id.in_(host_ids))

    if sync_state is not None:
        conditions.append(HostHwRec.sync_state == sync_state)

    if diff_state is not None:
        conditions.append(HostHwRec.diff_state == diff_state)

    if not include_deleted:
        conditions.append(HostHwRec.del_flag == 0)

    stmt = select(HostHwRec)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    # 按创建时间和ID倒序排序（获取最新记录）
    stmt = stmt.order_by(desc(HostHwRec.created_time), desc(HostHwRec.id))

    return stmt


async def get_latest_hw_record(
    session: AsyncSession,
    host_id: int,
    sync_state: int = 1,
    locale: str = "zh_CN",
) -> Optional[HostHwRec]:
    """获取主机的最新硬件记录

    Args:
        session: 数据库会话
        host_id: 主机ID
        sync_state: 同步状态（默认：1-待同步）
        locale: 语言代码（用于错误消息）

    Returns:
        最新的硬件记录，如果不存在则返回 None

    Example:
        ```python
        latest_hw = await get_latest_hw_record(session, host_id=123)
        if latest_hw:
            # 处理最新硬件记录
            ***REMOVED***
        ```
    """
    stmt = build_pending_hw_records_query(
        host_id=host_id,
        sync_state=sync_state,
    ).limit(1)

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_pending_hw_records(
    session: AsyncSession,
    host_id: Optional[int] = None,
    host_ids: Optional[List[int]] = None,
    sync_state: int = 1,
    diff_state: Optional[int] = None,
) -> List[HostHwRec]:
    """获取所有待审批硬件记录

    Args:
        session: 数据库会话
        host_id: 单个主机ID（可选）
        host_ids: 多个主机ID列表（可选）
        sync_state: 同步状态（默认：1-待同步）
        diff_state: 参数状态（可选）

    Returns:
        硬件记录列表

    Example:
        ```python
        # 获取单个主机的所有待审批硬件记录
        hw_recs = await get_all_pending_hw_records(session, host_id=123)

        # 获取多个主机的所有待审批硬件记录
        hw_recs = await get_all_pending_hw_records(session, host_ids=[123, 456])
        ```
    """
    stmt = build_pending_hw_records_query(
        host_id=host_id,
        host_ids=host_ids,
        sync_state=sync_state,
        diff_state=diff_state,
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())

