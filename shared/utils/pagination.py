"""
分页工具类

提供统一的分页参数处理和分页响应格式。
"""

from typing import Optional
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
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

        Example:
            >>> params = PaginationParams(page=3, page_size=10)
            >>> params.calculate_offset()
            20
        """
        return (self.page - 1) * self.page_size

    @property
    def offset(self) -> int:
        """偏移量（属性）

        Returns:
            数据库查询偏移量
        """
        return self.calculate_offset()

    @property
    def limit(self) -> int:
        """限制数量（属性）

        Returns:
            每页数量
        """
        return self.page_size

    model_config = {"from_attributes": True}


class PaginationResponse(BaseModel):
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
        """
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """是否有下一页

        Returns:
            如果当前页不是最后一页则返回True
        """
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """是否有上一页

        Returns:
            如果当前页不是第一页则返回True
        """
        return self.page > 1

    model_config = {"from_attributes": True}


class CursorPaginationParams(BaseModel):
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
    )

    model_config = {"from_attributes": True}


class CursorPaginationResponse(BaseModel):
    """游标分页响应模型

    用于游标分页查询的响应格式。

    Example:
        >>> response = CursorPaginationResponse(
        ...     page_size=20,
        ...     total=15,
        ...     has_next=False,
        ...     last_id=115
        ... )
        >>> print(response.has_next)  # 输出: False
    """

    page_size: int = Field(description="每页大小")
    total: int = Field(description="本次查询发现的记录总数")
    has_next: bool = Field(description="是否有下一页")
    last_id: Optional[int] = Field(description="当前页最后一条记录的 id，用于请求下一页")

    model_config = {"from_attributes": True}
