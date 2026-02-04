"""Agent WebSocket Heartbeat Manager Module

Provides heartbeat detection related utility functions and constant definitions.

Split from agent_websocket_manager.py to improve code maintainability.

Note: Core heartbeat detection logic remains in AgentWebSocketManager,
as it is tightly coupled with connection state. This module only provides independent utility functions.
"""

from datetime import datetime, timezone
import os
import sys
from typing import Optional

# Use try-except to handle path imports
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# Heartbeat related constants
DEFAULT_HEARTBEAT_TIMEOUT = 60  # Default heartbeat timeout (seconds)
DEFAULT_HEARTBEAT_WARNING_WAIT_TIME = 10  # Wait time after heartbeat warning (seconds)
DEFAULT_HEARTBEAT_CHECK_INTERVAL = 10  # Heartbeat check interval (seconds)


def calculate_heartbeat_age(
    last_heartbeat: Optional[datetime],
    current_time: Optional[datetime] = None,
) -> float:
    """Calculate heartbeat age (seconds since last heartbeat)

    Args:
        last_heartbeat: Last heartbeat time
        current_time: Current time (defaults to UTC time)

    Returns:
        float: Heartbeat age (seconds). Returns float('inf') if last_heartbeat is None
    """
    if last_heartbeat is None:
        return float("inf")

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Ensure timezone consistency
    if last_heartbeat.tzinfo is None:
        last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    return (current_time - last_heartbeat).total_seconds()


def is_heartbeat_timeout(
    last_heartbeat: Optional[datetime],
    timeout_seconds: float = DEFAULT_HEARTBEAT_TIMEOUT,
    current_time: Optional[datetime] = None,
) -> bool:
    """Check if heartbeat is timeout

    Args:
        last_heartbeat: Last heartbeat time
        timeout_seconds: Timeout duration (seconds)
        current_time: Current time (defaults to UTC time)

    Returns:
        bool: Whether timeout
    """
    age = calculate_heartbeat_age(last_heartbeat, current_time)
    return age > timeout_seconds


def is_warning_timeout(
    warning_sent_time: Optional[datetime],
    wait_time_seconds: float = DEFAULT_HEARTBEAT_WARNING_WAIT_TIME,
    current_time: Optional[datetime] = None,
) -> bool:
    """Check if timeout after warning (need to disconnect)

    Args:
        warning_sent_time: Warning sent time
        wait_time_seconds: Wait time after warning (seconds)
        current_time: Current time (defaults to UTC time)

    Returns:
        bool: Whether exceeded wait time
    """
    if warning_sent_time is None:
        return False

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Ensure timezone consistency
    if warning_sent_time.tzinfo is None:
        warning_sent_time = warning_sent_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    elapsed = (current_time - warning_sent_time).total_seconds()
    return elapsed > wait_time_seconds


def get_heartbeat_status_message(
    agent_id: str,
    last_heartbeat: Optional[datetime],
    timeout_seconds: float = DEFAULT_HEARTBEAT_TIMEOUT,
) -> dict:
    """Get heartbeat status message

    Args:
        agent_id: Agent ID
        last_heartbeat: Last heartbeat time
        timeout_seconds: Timeout duration (seconds)

    Returns:
        dict: Status message, containing healthy, age, timeout and other information
    """
    age = calculate_heartbeat_age(last_heartbeat)
    is_timeout = age > timeout_seconds

    return {
        "agent_id": agent_id,
        "healthy": not is_timeout,
        "age_seconds": age if age != float("inf") else -1,
        "timeout_seconds": timeout_seconds,
        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None,
        "status": "timeout" if is_timeout else "healthy",
    }


def format_heartbeat_log_extra(
    agent_id: str,
    last_heartbeat: Optional[datetime],
    warning_sent: bool = False,
    current_connections: int = 0,
) -> dict:
    """Format heartbeat log extra field

    Args:
        agent_id: Agent ID
        last_heartbeat: Last heartbeat time
        warning_sent: Whether warning has been sent
        current_connections: Current connection count

    Returns:
        dict: Log extra field
    """
    age = calculate_heartbeat_age(last_heartbeat)

    return {
        "agent_id": agent_id,
        "heartbeat_age_seconds": age if age != float("inf") else -1,
        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None,
        "warning_sent": warning_sent,
        "current_connections": current_connections,
    }
