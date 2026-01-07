"""Agent WebSocket 心跳管理器模块

提供心跳检测相关的工具函数和常量定义。

从 agent_websocket_manager.py 拆分出来，提高代码可维护性。

注意：核心心跳检测逻辑仍保留在 AgentWebSocketManager 中，
因为它与连接状态紧密耦合。此模块仅提供独立的工具函数。
"""

from datetime import datetime, timezone
import os
import sys
from typing import Optional

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# 心跳相关常量
DEFAULT_HEARTBEAT_TIMEOUT = 60  # 默认心跳超时时间（秒）
DEFAULT_HEARTBEAT_WARNING_WAIT_TIME = 10  # 心跳警告后等待时间（秒）
DEFAULT_HEARTBEAT_CHECK_INTERVAL = 10  # 心跳检查间隔（秒）


def calculate_heartbeat_age(
    last_heartbeat: Optional[datetime],
    current_time: Optional[datetime] = None,
) -> float:
    """计算心跳年龄（距离上次心跳的秒数）

    Args:
        last_heartbeat: 上次心跳时间
        current_time: 当前时间（默认使用 UTC 时间）

    Returns:
        float: 心跳年龄（秒）。如果 last_heartbeat 为 None，返回 float('inf')
    """
    if last_heartbeat is None:
        return float("inf")

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # 确保时区一致
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
    """检查心跳是否超时

    Args:
        last_heartbeat: 上次心跳时间
        timeout_seconds: 超时时间（秒）
        current_time: 当前时间（默认使用 UTC 时间）

    Returns:
        bool: 是否超时
    """
    age = calculate_heartbeat_age(last_heartbeat, current_time)
    return age > timeout_seconds


def is_warning_timeout(
    warning_sent_time: Optional[datetime],
    wait_time_seconds: float = DEFAULT_HEARTBEAT_WARNING_WAIT_TIME,
    current_time: Optional[datetime] = None,
) -> bool:
    """检查警告后是否超时（需要断开连接）

    Args:
        warning_sent_time: 警告发送时间
        wait_time_seconds: 警告后等待时间（秒）
        current_time: 当前时间（默认使用 UTC 时间）

    Returns:
        bool: 是否超过等待时间
    """
    if warning_sent_time is None:
        return False

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # 确保时区一致
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
    """获取心跳状态消息

    Args:
        agent_id: Agent ID
        last_heartbeat: 上次心跳时间
        timeout_seconds: 超时时间（秒）

    Returns:
        dict: 状态消息，包含 healthy、age、timeout 等信息
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
    """格式化心跳日志的 extra 字段

    Args:
        agent_id: Agent ID
        last_heartbeat: 上次心跳时间
        warning_sent: 是否已发送警告
        current_connections: 当前连接数

    Returns:
        dict: 日志 extra 字段
    """
    age = calculate_heartbeat_age(last_heartbeat)

    return {
        "agent_id": agent_id,
        "heartbeat_age_seconds": age if age != float("inf") else -1,
        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None,
        "warning_sent": warning_sent,
        "current_connections": current_connections,
    }
