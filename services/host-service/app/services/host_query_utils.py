"""Host service common query utility module

Provides shared query utility functions for host-related services.

Used to reduce duplicate code in files like admin_host_service.py, host_discovery_service.py,
browser_host_service.py, etc.
"""

import os
import sys
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Use try-except to handle path imports
try:
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_OFFLINE
    from app.models.host_rec import HostRec
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_OFFLINE
    from app.models.host_rec import HostRec
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


async def get_host_by_id(
    session: AsyncSession,
    host_id: int,
    include_deleted: bool = False,
) -> Optional[HostRec]:
    """Get host record by ID

    Args:
        session: Database session
        host_id: Host ID
        include_deleted: Whether to include deleted records

    Returns:
        Optional[HostRec]: Host record, returns None if not exists
    """
    conditions = [HostRec.id == host_id]
    if not include_deleted:
        conditions.append(HostRec.del_flag == 0)

    stmt = select(HostRec).where(and_(*conditions))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_hosts(
    session: AsyncSession,
    host_states: Optional[List[int]] = None,
    appr_state: int = 1,
    limit: Optional[int] = None,
) -> List[HostRec]:
    """Get active host list

    Args:
        session: Database session
        host_states: Allowed host state list, default is [0, 1, 2, 3, 4]
        appr_state: Approval state, default is 1 (enabled)
        limit: Return count limit

    Returns:
        List[HostRec]: Host list
    """
    if host_states is None:
        host_states = [0, 1, 2, 3, 4]

    conditions = [
        HostRec.host_state.in_(host_states),
        HostRec.appr_state == appr_state,
        HostRec.del_flag == 0,
    ]

    stmt = select(HostRec).where(and_(*conditions))

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_free_hosts(
    session: AsyncSession,
    appr_state: int = 1,
    limit: Optional[int] = None,
) -> List[HostRec]:
    """Get free host list

    Args:
        session: Database session
        appr_state: Approval state, default is 1 (enabled)
        limit: Return count limit

    Returns:
        List[HostRec]: Free host list
    """
    return await get_active_hosts(
        session=session,
        host_states=[HOST_STATE_FREE],
        appr_state=appr_state,
        limit=limit,
    )


async def get_offline_hosts(
    session: AsyncSession,
    appr_state: int = 1,
    limit: Optional[int] = None,
) -> List[HostRec]:
    """Get offline host list

    Args:
        session: Database session
        appr_state: Approval state, default is 1 (enabled)
        limit: Return count limit

    Returns:
        List[HostRec]: Offline host list
    """
    return await get_active_hosts(
        session=session,
        host_states=[HOST_STATE_OFFLINE],
        appr_state=appr_state,
        limit=limit,
    )


def host_to_dict(
    host: HostRec,
    include_sensitive: bool = False,
) -> Dict[str, Any]:
    """Convert host record to dictionary

    Args:
        host: Host record
        include_sensitive: Whether to include sensitive fields (e.g., password)

    Returns:
        Dict[str, Any]: Host information dictionary
    """
    result = {
        "id": host.id,
        "hardware_id": host.hardware_id,
        "host_ip": host.host_ip,
        "host_state": host.host_state,
        "appr_state": host.appr_state,
        "tcp_state": host.tcp_state,
        "tcp_port": host.tcp_port,
        "agent_ver": host.agent_ver,
        "os_ver": host.os_ver,
        "created_time": host.created_time.isoformat() if host.created_time else None,
        "updated_time": host.updated_time.isoformat() if host.updated_time else None,
    }

    if include_sensitive:
        result["vnc_pwd"] = host.vnc_pwd

    return result


def format_host_list_response(
    hosts: List[HostRec],
    include_sensitive: bool = False,
) -> List[Dict[str, Any]]:
    """Format host list response

    Args:
        hosts: Host list
        include_sensitive: Whether to include sensitive fields

    Returns:
        List[Dict[str, Any]]: Formatted host information list
    """
    return [host_to_dict(host, include_sensitive) for host in hosts]


def calculate_pagination(
    total: int,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    """Calculate pagination information

    Args:
        total: Total record count
        page: Current page number
        page_size: Items per page

    Returns:
        Dict[str, Any]: Pagination information
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
    }


def build_host_filter_conditions(
    host_state: Optional[int] = None,
    appr_state: Optional[int] = None,
    tcp_state: Optional[int] = None,
    keyword: Optional[str] = None,
) -> List:
    """Build host filter conditions

    Args:
        host_state: Host state filter
        appr_state: Approval state filter
        tcp_state: TCP state filter
        keyword: Keyword search (matches hardware_id or host_ip)

    Returns:
        List: SQLAlchemy filter conditions list
    """
    from sqlalchemy import or_

    conditions = [HostRec.del_flag == 0]

    if host_state is not None:
        conditions.append(HostRec.host_state == host_state)

    if appr_state is not None:
        conditions.append(HostRec.appr_state == appr_state)

    if tcp_state is not None:
        conditions.append(HostRec.tcp_state == tcp_state)

    if keyword:
        keyword_pattern = f"%{keyword}%"
        conditions.append(
            or_(
                HostRec.hardware_id.like(keyword_pattern),
                HostRec.host_ip.like(keyword_pattern),
            )
        )

    return conditions
