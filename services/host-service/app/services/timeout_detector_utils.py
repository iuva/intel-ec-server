"""Timeout detection utility module

Provides utility functions for case timeout and VNC timeout detection.

Extracted from case_timeout_task.py to reduce main file code size.
"""

from datetime import datetime, timedelta, timezone
import os
import sys
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Use try-except to handle path imports
try:
    from app.constants.host_constants import HOST_STATE_OCCUPIED
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import HOST_STATE_OCCUPIED
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# Timeout detection related constants
DEFAULT_CASE_TIMEOUT_MINUTES = 60  # Default case timeout (minutes)
DEFAULT_VNC_TIMEOUT_MINUTES = 30  # Default VNC timeout (minutes)
DEFAULT_CHECK_INTERVAL_SECONDS = 60  # Default check interval (seconds)


def calculate_timeout_threshold(
    timeout_minutes: int,
    current_time: Optional[datetime] = None,
) -> datetime:
    """Calculate timeout threshold time

    Args:
        timeout_minutes: Timeout duration (minutes)
        current_time: Current time (defaults to UTC time)

    Returns:
        datetime: Timeout threshold time
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    return current_time - timedelta(minutes=timeout_minutes)


def is_exec_log_timeout(
    exec_log: HostExecLog,
    timeout_minutes: int,
    current_time: Optional[datetime] = None,
) -> bool:
    """Check if execution log is timeout

    Args:
        exec_log: Execution log record
        timeout_minutes: Timeout duration (minutes)
        current_time: Current time

    Returns:
        bool: Whether timeout
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Check if there is expected end time
    if exec_log.due_time:
        # Ensure timezone consistency
        due_time = exec_log.due_time
        if due_time.tzinfo is None:
            due_time = due_time.replace(tzinfo=timezone.utc)
        return current_time > due_time

    # If no expected end time, use creation time + timeout duration
    created_time = exec_log.created_time
    if created_time:
        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=timezone.utc)
        timeout_threshold = created_time + timedelta(minutes=timeout_minutes)
        return current_time > timeout_threshold

    return False


def is_vnc_connection_timeout(
    host: HostRec,
    timeout_minutes: int,
    current_time: Optional[datetime] = None,
) -> bool:
    """Check if VNC connection is timeout

    Args:
        host: Host record
        timeout_minutes: Timeout duration (minutes)
        current_time: Current time

    Returns:
        bool: Whether timeout
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # VNC timeout is determined based on host update time
    if host.updated_time:
        updated_time = host.updated_time
        if updated_time.tzinfo is None:
            updated_time = updated_time.replace(tzinfo=timezone.utc)
        timeout_threshold = updated_time + timedelta(minutes=timeout_minutes)
        return current_time > timeout_threshold

    return False


async def find_timeout_exec_logs(
    session: AsyncSession,
    timeout_minutes: int,
    limit: int = 100,
) -> List[HostExecLog]:
    """Find timeout execution logs

    Args:
        session: Database session
        timeout_minutes: Timeout duration (minutes)
        limit: Return count limit

    Returns:
        List[HostExecLog]: List of timeout execution logs
    """
    current_time = datetime.now(timezone.utc)
    timeout_threshold = calculate_timeout_threshold(timeout_minutes, current_time)

    # Query conditions: host_state = 2 (occupied), del_flag = 0, and timeout
    stmt = (
        select(HostExecLog)
        .where(
            and_(
                HostExecLog.host_state == 2,  # Occupied
                HostExecLog.del_flag == 0,
                HostExecLog.created_time < timeout_threshold,
            )
        )
        .limit(limit)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def find_vnc_timeout_hosts(
    session: AsyncSession,
    timeout_minutes: int,
    limit: int = 100,
) -> List[HostRec]:
    """Find VNC timeout hosts

    Args:
        session: Database session
        timeout_minutes: Timeout duration (minutes)
        limit: Return count limit

    Returns:
        List[HostRec]: List of VNC timeout hosts
    """
    current_time = datetime.now(timezone.utc)
    timeout_threshold = calculate_timeout_threshold(timeout_minutes, current_time)

    # Query conditions: host_state = 2 (occupied), appr_state = 1, del_flag = 0, and update time timeout
    stmt = (
        select(HostRec)
        .where(
            and_(
                HostRec.host_state == HOST_STATE_OCCUPIED,
                HostRec.appr_state == 1,
                HostRec.del_flag == 0,
                HostRec.updated_time < timeout_threshold,
            )
        )
        .limit(limit)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


def format_timeout_log_extra(
    log_id: int,
    host_id: int,
    timeout_type: str,
    timeout_minutes: int,
    created_time: Optional[datetime] = None,
    due_time: Optional[datetime] = None,
) -> dict:
    """Format timeout log extra field

    Args:
        log_id: Log ID
        host_id: Host ID
        timeout_type: Timeout type (case / vnc)
        timeout_minutes: Timeout duration (minutes)
        created_time: Creation time
        due_time: Expected end time

    Returns:
        dict: Log extra field
    """
    return {
        "log_id": log_id,
        "host_id": host_id,
        "timeout_type": timeout_type,
        "timeout_minutes": timeout_minutes,
        "created_time": created_time.isoformat() if created_time else None,
        "due_time": due_time.isoformat() if due_time else None,
    }


def get_timeout_message(
    timeout_type: str,
    host_id: int,
    timeout_minutes: int,
) -> str:
    """Get timeout message

    Args:
        timeout_type: Timeout type
        host_id: Host ID
        timeout_minutes: Timeout duration

    Returns:
        str: Timeout message
    """
    if timeout_type == "case":
        return f"Host {host_id} test case execution timeout (exceeded {timeout_minutes} minutes)"
    if timeout_type == "vnc":
        return f"Host {host_id} VNC connection timeout (exceeded {timeout_minutes} minutes)"
    return f"Host {host_id} timeout (exceeded {timeout_minutes} minutes)"
