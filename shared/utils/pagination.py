"""
<<<<<<< HEAD
Pagination Utility Classes

Provides unified pagination parameter handling and pagination response formats.
"""

from typing import Optional

=======
分页工具类

提供统一的分页参数处理和分页响应格式。
"""

from typing import Optional
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
<<<<<<< HEAD
    """Pagination Parameters Model

    Used to uniformly handle pagination request parameters, providing auxiliary functions like offset calculation.

    Example:
        >>> params = PaginationParams(page=2, page_size=20)
        >>> print(params.offset)  # Output: 20
        >>> print(params.limit)   # Output: 20
    """

    page: int = Field(default=1, ge=1, description="Page number (starting from 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")

    def calculate_offset(self) -> int:
        """Calculate offset

        Calculate the database query offset based on page number and page size.

        Returns:
            Offset value
=======
    """分页参数模型

    用于统一处理分页请求参数，提供offset计算等辅助功能。

    Example:
        >>> params = PaginationParams(page=2, page_size=20)
        >>> print(params.offset)  # 输出: 20
        >>> print(params.limit)   # 输出: 20
    """

    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小（1-100）")

    def calculate_offset(self) -> int:
        """计算偏移量

        根据页码和每页大小计算数据库查询的偏移量。

        Returns:
            偏移量值
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

        Example:
            >>> params = PaginationParams(page=3, page_size=10)
            >>> params.calculate_offset()
            20
        """
        return (self.page - 1) * self.page_size

    @property
    def offset(self) -> int:
<<<<<<< HEAD
        """Offset (property)

        Returns:
            Database query offset
=======
        """偏移量（属性）

        Returns:
            数据库查询偏移量
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
        """
        return self.calculate_offset()

    @property
    def limit(self) -> int:
<<<<<<< HEAD
        """Limit quantity (property)

        Returns:
            Page size
=======
        """限制数量（属性）

        Returns:
            每页数量
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
        """
        return self.page_size

    model_config = {"from_attributes": True}


class PaginationResponse(BaseModel):
<<<<<<< HEAD
    """Pagination Response Model

    Used to standardize the response format for pagination queries,
    providing auxiliary attributes like total pages,
    whether there is a next page, etc.

    Example:
        >>> response = PaginationResponse(page=2, page_size=20, total=55)
        >>> print(response.total_pages)  # Output: 3
        >>> print(response.has_next)     # Output: True
        >>> print(response.has_prev)     # Output: True
    """

    page: int = Field(description="Current page number")
    page_size: int = Field(description="Page size")
    total: int = Field(description="Total record count")

    @property
    def total_pages(self) -> int:
        """Total pages

        Calculate total pages based on total records and page size.

        Returns:
            Total number of pages
=======
    """分页响应模型

    用于统一分页查询的响应格式，提供总页数、是否有下一页等辅助属性。

    Example:
        >>> response = PaginationResponse(page=2, page_size=20, total=55)
        >>> print(response.total_pages)  # 输出: 3
        >>> print(response.has_next)     # 输出: True
        >>> print(response.has_prev)     # 输出: True
    """

    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total: int = Field(description="总记录数")

    @property
    def total_pages(self) -> int:
        """总页数

        根据总记录数和每页大小计算总页数。

        Returns:
            总页数
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
        """
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
<<<<<<< HEAD
        """Has next page

        Returns:
            Returns True if the current page is not the last page
=======
        """是否有下一页

        Returns:
            如果当前页不是最后一页则返回True
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
        """
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
<<<<<<< HEAD
        """Has previous page

        Returns:
            Returns True if the current page is not the first page
=======
        """是否有上一页

        Returns:
            如果当前页不是第一页则返回True
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
        """
        return self.page > 1

    model_config = {"from_attributes": True}


class CursorPaginationParams(BaseModel):
<<<<<<< HEAD
    """Cursor Pagination Parameters Model

    Used for cursor pagination scenarios, avoiding state pollution issues with concurrent multi-user access.

    Example:
        >>> params = CursorPaginationParams(page_size=20, last_id=100)
        >>> print(params.page_size)  # Output: 20
        >>> print(params.last_id)    # Output: 100
    """

    page_size: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    last_id: Optional[int] = Field(
        default=None,
        description=(
            "ID of the last record from the previous page. "
            "Null for the first request, subsequent requests "
            "need to ***REMOVED*** the ID of the last record from the previous page"
        ),
=======
    """游标分页参数模型

    用于游标分页场景，避免多用户并发时的状态污染问题。

    Example:
        >>> params = CursorPaginationParams(page_size=20, last_id=100)
        >>> print(params.page_size)  # 输出: 20
        >>> print(params.last_id)    # 输出: 100
    """

    page_size: int = Field(default=20, ge=1, le=100, description="每页数量（1-100）")
    last_id: Optional[int] = Field(
        default=None,
        description="上一页最后一条记录的 id。首次请求为 null，后续请求需要传入上一页最后一条记录的 id",
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
    )

    model_config = {"from_attributes": True}


class CursorPaginationResponse(BaseModel):
<<<<<<< HEAD
    """Cursor Pagination Response Model

    Used for the response format of cursor pagination queries.
=======
    """游标分页响应模型

    用于游标分页查询的响应格式。
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

    Example:
        >>> response = CursorPaginationResponse(
        ...     page_size=20,
        ...     total=15,
        ...     has_next=False,
        ...     last_id=115
        ... )
<<<<<<< HEAD
        >>> print(response.has_next)  # Output: False
    """

    page_size: int = Field(description="Page size")
    total: int = Field(description="Total number of records found in this query")
    has_next: bool = Field(description="Whether there is a next page")
    last_id: Optional[int] = Field(
        description="ID of the last record in the current page, used to request the next page"
    )
=======
        >>> print(response.has_next)  # 输出: False
    """

    page_size: int = Field(description="每页大小")
    total: int = Field(description="本次查询发现的记录总数")
    has_next: bool = Field(description="是否有下一页")
    last_id: Optional[int] = Field(description="当前页最后一条记录的 id，用于请求下一页")
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

    model_config = {"from_attributes": True}
