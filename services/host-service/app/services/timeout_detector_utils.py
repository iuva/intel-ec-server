"""超时检测工具模块

提供用例超时和 VNC 超时检测相关的工具函数。

从 case_timeout_task.py 提取，减少主文件代码量。
"""

from datetime import datetime, timedelta, timezone
import os
import sys
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 try-except 方式处理路径导入
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


# 超时检测相关常量
DEFAULT_CASE_TIMEOUT_MINUTES = 60  # 默认用例超时时间（分钟）
DEFAULT_VNC_TIMEOUT_MINUTES = 30  # 默认 VNC 超时时间（分钟）
DEFAULT_CHECK_INTERVAL_SECONDS = 60  # 默认检查间隔（秒）


def calculate_timeout_threshold(
    timeout_minutes: int,
    current_time: Optional[datetime] = None,
) -> datetime:
    """计算超时阈值时间

    Args:
        timeout_minutes: 超时时间（分钟）
        current_time: 当前时间（默认使用 UTC 时间）

    Returns:
        datetime: 超时阈值时间
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    return current_time - timedelta(minutes=timeout_minutes)


def is_exec_log_timeout(
    exec_log: HostExecLog,
    timeout_minutes: int,
    current_time: Optional[datetime] = None,
) -> bool:
    """判断执行日志是否超时

    Args:
        exec_log: 执行日志记录
        timeout_minutes: 超时时间（分钟）
        current_time: 当前时间

    Returns:
        bool: 是否超时
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # 检查是否有预期结束时间
    if exec_log.due_time:
        # 确保时区一致
        due_time = exec_log.due_time
        if due_time.tzinfo is None:
            due_time = due_time.replace(tzinfo=timezone.utc)
        return current_time > due_time

    # 如果没有预期结束时间，使用创建时间 + 超时时间
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
    """判断 VNC 连接是否超时

    Args:
        host: 主机记录
        timeout_minutes: 超时时间（分钟）
        current_time: 当前时间

    Returns:
        bool: 是否超时
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # VNC 超时基于主机更新时间判断
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
    """查找超时的执行日志

    Args:
        session: 数据库会话
        timeout_minutes: 超时时间（分钟）
        limit: 返回数量限制

    Returns:
        List[HostExecLog]: 超时的执行日志列表
    """
    current_time = datetime.now(timezone.utc)
    timeout_threshold = calculate_timeout_threshold(timeout_minutes, current_time)

    # 查询条件：host_state = 2（已占用）, del_flag = 0, 且超时
    stmt = (
        select(HostExecLog)
        .where(
            and_(
                HostExecLog.host_state == 2,  # 已占用
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
    """查找 VNC 超时的主机

    Args:
        session: 数据库会话
        timeout_minutes: 超时时间（分钟）
        limit: 返回数量限制

    Returns:
        List[HostRec]: VNC 超时的主机列表
    """
    current_time = datetime.now(timezone.utc)
    timeout_threshold = calculate_timeout_threshold(timeout_minutes, current_time)

    # 查询条件：host_state = 2（已占用）, appr_state = 1, del_flag = 0, 且更新时间超时
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
    """格式化超时日志的 extra 字段

    Args:
        log_id: 日志 ID
        host_id: 主机 ID
        timeout_type: 超时类型（case / vnc）
        timeout_minutes: 超时时间（分钟）
        created_time: 创建时间
        due_time: 预期结束时间

    Returns:
        dict: 日志 extra 字段
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
    """获取超时消息

    Args:
        timeout_type: 超时类型
        host_id: 主机 ID
        timeout_minutes: 超时时间

    Returns:
        str: 超时消息
    """
    if timeout_type == "case":
        return f"主机 {host_id} 的测试用例执行超时（超过 {timeout_minutes} 分钟）"
    elif timeout_type == "vnc":
        return f"主机 {host_id} 的 VNC 连接超时（超过 {timeout_minutes} 分钟）"
    else:
        return f"主机 {host_id} 超时（超过 {timeout_minutes} 分钟）"
