"""
数据库查询辅助工具

提供通用的数据库查询辅助函数，减少代码重复。
"""

import os
import sys
from typing import Any, List, Optional, Tuple, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 try-except 方式处理路径导入
try:
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.utils.pagination import PaginationParams, PaginationResponse

T = TypeVar("T")


async def execute_paginated_query(
    session: AsyncSession,
    base_query: Select[Tuple[Any, ...]],
    pagination_params: PaginationParams,
    order_by: Optional[Any] = None,
) -> Tuple[List[Any], int]:
    """执行分页查询

    通用的分页查询函数，自动处理计数查询和数据查询。

    Args:
        session: 数据库会话
        base_query: 基础查询语句（不包含排序和分页）
        pagination_params: 分页参数
        order_by: 排序字段（可选）

    Returns:
        Tuple[List[Any], int]: (查询结果列表, 总记录数)

    Example:
        >>> from shared.utils.pagination import PaginationParams
        >>> from sqlalchemy import select
        >>>
        >>> base_query = select(User).where(User.is_active == True)
        >>> pagination_params = PaginationParams(page=1, page_size=20)
        >>> rows, total = await execute_paginated_query(
        ...     session,
        ...     base_query,
        ...     pagination_params,
        ...     order_by=User.created_time.desc()
        ... )
    """
    # 1. 查询总数
    count_stmt = select(func.count()).select_from(base_query.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # 2. 分页查询
    stmt = base_query

    # 添加排序
    if order_by is not None:
        stmt = stmt.order_by(order_by)

    # 添加分页
    stmt = stmt.offset(pagination_params.offset).limit(pagination_params.limit)

    # 执行查询
    result = await session.execute(stmt)
    rows = list(result.all())

    return rows, total


async def build_pagination_response(
    page: int,
    page_size: int,
    total: int,
) -> PaginationResponse:
    """构建分页响应

    根据分页参数和总记录数构建分页响应对象。

    Args:
        page: 当前页码
        page_size: 每页大小
        total: 总记录数

    Returns:
        PaginationResponse: 分页响应对象

    Example:
        >>> response = await build_pagination_response(
        ...     page=1,
        ...     page_size=20,
        ...     total=100
        ... )
        >>> print(response.total_pages)  # 输出: 5
        >>> print(response.has_next)     # 输出: True
    """
    return PaginationResponse(
        page=page,
        page_size=page_size,
        total=total,
    )
