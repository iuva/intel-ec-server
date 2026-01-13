"""
Pagination Utility Classes

Provides unified pagination parameter handling and pagination response formats.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
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

        Example:
            >>> params = PaginationParams(page=3, page_size=10)
            >>> params.calculate_offset()
            20
        """
        return (self.page - 1) * self.page_size

    @property
    def offset(self) -> int:
        """Offset (property)

        Returns:
            Database query offset
        """
        return self.calculate_offset()

    @property
    def limit(self) -> int:
        """Limit quantity (property)

        Returns:
            Page size
        """
        return self.page_size

    model_config = {"from_attributes": True}


class PaginationResponse(BaseModel):
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
        """
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Has next page

        Returns:
            Returns True if the current page is not the last page
        """
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Has previous page

        Returns:
            Returns True if the current page is not the first page
        """
        return self.page > 1

    model_config = {"from_attributes": True}


class CursorPaginationParams(BaseModel):
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
    )

    model_config = {"from_attributes": True}


class CursorPaginationResponse(BaseModel):
    """Cursor Pagination Response Model

    Used for the response format of cursor pagination queries.

    Example:
        >>> response = CursorPaginationResponse(
        ...     page_size=20,
        ...     total=15,
        ...     has_next=False,
        ...     last_id=115
        ... )
        >>> print(response.has_next)  # Output: False
    """

    page_size: int = Field(description="Page size")
    total: int = Field(description="Total number of records found in this query")
    has_next: bool = Field(description="Whether there is a next page")
    last_id: Optional[int] = Field(
        description="ID of the last record in the current page, used to request the next page"
    )

    model_config = {"from_attributes": True}
