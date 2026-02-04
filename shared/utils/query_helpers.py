"""
Database Query Helper Tools

Provides common database query helper functions, reducing code duplication.
"""

import os
import sys
from typing import Any, List, Optional, Tuple, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Use try-except approach to handle path imports
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
    """Execute paginated query

    Generic pagination query function, automatically handles count query and data query.

    Args:
        session: Database session
        base_query: Base query statement (does not include sorting and pagination)
        pagination_params: Pagination parameters
        order_by: Sort field (optional)

    Returns:
        Tuple[List[Any], int]: (Query result list, total record count)

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
    # 1. Query total count
    count_stmt = select(func.count()).select_from(base_query.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # 2. Paginated query
    stmt = base_query

    # Add sorting
    if order_by is not None:
        stmt = stmt.order_by(order_by)

    # Add pagination
    stmt = stmt.offset(pagination_params.offset).limit(pagination_params.limit)

    # Execute query
    result = await session.execute(stmt)
    rows = list(result.all())

    return rows, total


async def build_pagination_response(
    page: int,
    page_size: int,
    total: int,
) -> PaginationResponse:
    """Build pagination response

    Build pagination response object based on pagination parameters and total record count.

    Args:
        page: Current page number
        page_size: Page size
        total: Total record count

    Returns:
        PaginationResponse: Pagination response object

    Example:
        >>> response = await build_pagination_response(
        ...     page=1,
        ...     page_size=20,
        ...     total=100
        ... )
        >>> print(response.total_pages)  # Output: 5
        >>> print(response.has_next)     # Output: True
    """
    return PaginationResponse(
        page=page,
        page_size=page_size,
        total=total,
    )
