"""主机服务通用查询工具模块

提供主机相关服务共享的查询工具函数。

用于减少 admin_host_service.py, host_discovery_service.py,
browser_host_service.py 等文件中的重复代码。
"""

import os
import sys
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 try-except 方式处理路径导入
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
    """根据 ID 获取主机记录

    Args:
        session: 数据库会话
        host_id: 主机 ID
        include_deleted: 是否包含已删除记录

    Returns:
        Optional[HostRec]: 主机记录，如果不存在则返回 None
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
    """获取活跃主机列表

    Args:
        session: 数据库会话
        host_states: 允许的主机状态列表，默认为 [0, 1, 2, 3, 4]
        appr_state: 审批状态，默认为 1（启用）
        limit: 返回数量限制

    Returns:
        List[HostRec]: 主机列表
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
    """获取空闲主机列表

    Args:
        session: 数据库会话
        appr_state: 审批状态，默认为 1（启用）
        limit: 返回数量限制

    Returns:
        List[HostRec]: 空闲主机列表
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
    """获取离线主机列表

    Args:
        session: 数据库会话
        appr_state: 审批状态，默认为 1（启用）
        limit: 返回数量限制

    Returns:
        List[HostRec]: 离线主机列表
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
    """将主机记录转换为字典

    Args:
        host: 主机记录
        include_sensitive: 是否包含敏感字段（如密码）

    Returns:
        Dict[str, Any]: 主机信息字典
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
    """格式化主机列表响应

    Args:
        hosts: 主机列表
        include_sensitive: 是否包含敏感字段

    Returns:
        List[Dict[str, Any]]: 格式化后的主机信息列表
    """
    return [host_to_dict(host, include_sensitive) for host in hosts]


def calculate_pagination(
    total: int,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    """计算分页信息

    Args:
        total: 总记录数
        page: 当前页码
        page_size: 每页数量

    Returns:
        Dict[str, Any]: 分页信息
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
    """构建主机过滤条件

    Args:
        host_state: 主机状态过滤
        appr_state: 审批状态过滤
        tcp_state: TCP 状态过滤
        keyword: 关键词搜索（匹配 hardware_id 或 host_ip）

    Returns:
        List: SQLAlchemy 过滤条件列表
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
