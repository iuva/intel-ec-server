"""
Host Hardware Record Query Builder

Provides query building functions related to host hardware records, reducing code duplication.
"""

import os
import sys
from typing import List, Optional

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

# Use try-except approach to handle path imports
try:
    from app.models.host_hw_rec import HostHwRec
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from app.models.host_hw_rec import HostHwRec
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def build_pending_hw_records_query(
    host_id: Optional[int] = None,
    host_ids: Optional[List[int]] = None,
    sync_state: int = 1,
    diff_state: Optional[int] = None,
    include_deleted: bool = False,
) -> Select:
    """Build query statement for pending hardware records

    Args:
        host_id: Single host ID (optional)
        host_ids: List of multiple host IDs (optional, mutually exclusive with host_id)
        sync_state: Sync state (default: 1-pending sync)
        diff_state: Parameter state (optional)
        include_deleted: Whether to include deleted records

    Returns:
        SQLAlchemy Select statement (already ordered by created_time and id in descending order)

    Example:
        ```python
        # Query pending hardware records for a single host
        stmt = build_pending_hw_records_query(host_id=123)
        result = await session.execute(stmt)
        hw_recs = result.scalars().all()

        # Query pending hardware records for multiple hosts
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

    # Order by creation time and ID in descending order (to get latest records)
    return stmt.order_by(desc(HostHwRec.created_time), desc(HostHwRec.id))


async def get_latest_hw_record(
    session: AsyncSession,
    host_id: int,
    sync_state: int = 1,
    locale: str = "zh_CN",
) -> Optional[HostHwRec]:
    """Get the latest hardware record for a host

    Args:
        session: Database session
        host_id: Host ID
        sync_state: Sync state (default: 1-pending sync)
        locale: Language code (for error messages)

    Returns:
        The latest hardware record, or None if it does not exist

    Example:
        ```python
        latest_hw = await get_latest_hw_record(session, host_id=123)
        if latest_hw:
            # Process latest hardware record
            pass
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
    """Get all pending hardware records

    Args:
        session: Database session
        host_id: Single host ID (optional)
        host_ids: List of multiple host IDs (optional)
        sync_state: Sync state (default: 1-pending sync)
        diff_state: Parameter state (optional)

    Returns:
        List of hardware records

    Example:
        ```python
        # Get all pending hardware records for a single host
        hw_recs = await get_all_pending_hw_records(session, host_id=123)

        # Get all pending hardware records for multiple hosts
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
