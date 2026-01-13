"""
Unified Response Format Module

Provides standardized API response formats, including success response, error response, and pagination response.
Supports multi-language messages.
"""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, Generic, List, Optional, TypeVar
import uuid

from pydantic import BaseModel, Field, model_serializer

# Define generic type variable
T = TypeVar("T")

try:
    from shared.common.i18n import t
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.i18n import t


class SuccessResponse(BaseModel):
    """Success Response Model

    Used for all successful API responses, providing a unified response format.
    Supports multi-language messages (auto-translated via message_key).
    """

    code: int = Field(default=200, description="Response code")
    message: str = Field(default="Operation successful", description="Response message")
    message_key: Optional[str] = Field(default=None, description="Translation key (if provided, overrides message)")
    data: Any = Field(description="Response data")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Response timestamp",
    )
    locale: Optional[str] = Field(default=None, description="Language code (for translating message_key)")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """Initialize success response, supporting auto translation"""
        # If message_key exists, auto translate
        message_key = data.get("message_key")
        locale = data.get("locale", "en_US")

        if message_key:
            # Extract format variables from kwargs (exclude defined fields and complex types)
            # Only ***REMOVED*** basic types (str, int, float, bool, None) to translation function,
            # avoid ***REMOVED***ing complex types like dict
            message_kwargs = {
                k: v
                for k, v in data.items()
                if k
                not in (
                    "code",
                    "message",
                    "message_key",
                    "data",
                    "timestamp",
                    "locale",
                    "default",
                )
                and isinstance(v, (str, int, float, bool, type(None)))
            }
            default_value = data.get("default")
            default_arg: Optional[str]
            if isinstance(default_value, str) or default_value is None:
                default_arg = default_value
            elif isinstance(default_value, (int, float, bool)):
                default_arg = str(default_value)
            else:
                default_arg = None
            translated_message = t(message_key, locale=locale, default=default_arg, **message_kwargs)
            data["message"] = translated_message
            # Remove message_key to avoid Pydantic validation error
            data.pop("message_key", None)

        super().__init__(**data)

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Serialize model, excluding message_key field"""
        data = {
            "code": self.code,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        # Only add non-None locale
        if self.locale is not None:
            data["locale"] = self.locale
        return data

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Serialize model

        Note: message_key field is excluded by default (because message is already translated),
        but locale field is retained. If you need to exclude these fields, you can ***REMOVED*** the
        exclude parameter when calling.
        """
        # ✅ Exclude message_key (because message is already translated), but retain locale
        exclude = kwargs.pop("exclude", set())
        if not isinstance(exclude, set):
            exclude = set(exclude) if exclude else set()
        # Exclude message_key (because message is already translated)
        exclude.add("message_key")
        # Retain locale field so client knows used language
        exclude_none = kwargs.pop("exclude_none", True)
        return super().model_dump(exclude=exclude, exclude_none=exclude_none, **kwargs)


class Result(BaseModel, Generic[T]):
    """Unified API Response Result Model

    Used for all API responses, providing a unified response format.
    Supports generic types, ensuring FastAPI docs can correctly display the specific type of data field.

    Field Description:
        - code: Response code (200 indicates success)
        - message: Response message
        - data: Response data (Generic type T)
        - timestamp: Response timestamp (ISO 8601 format)
        - locale: Language code (Optional, for multi-language support)

    Usage Example:
        ```python
        from shared.common.response import Result

        class UserResponse(BaseModel):
            id: int
            name: str

        @router.get("/users/{user_id}", response_model=Result[UserResponse])
        async def get_user(user_id: int) -> Result[UserResponse]:
            user = UserResponse(id=1, name="John")
            return Result(
                code=200,
                message="Query successful",
                data=user,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        ```

    This way, you can see the complete data field Schema in FastAPI documentation.
    """

    code: int = Field(default=200, description="Response code")
    message: str = Field(default="Operation successful", description="Response message")
    data: T = Field(description="Response data")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Response timestamp (ISO 8601 format)",
    )
    locale: Optional[str] = Field(default=None, description="Language code (for multi-language support)")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """Initialize response result, auto set timestamp"""
        # If timestamp not provided, auto generate
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        super().__init__(**data)


class TypedSuccessResponse(BaseModel, Generic[T]):
    """Typed Success Response Wrapper Model (Deprecated, please use Result[T])

    Note: This class is deprecated, please use Result[T] instead.
    Retained for backward compatibility, new code should use Result[T].
    """

    code: int = Field(default=200, description="Response code")
    message: str = Field(default="Operation successful", description="Response message")
    data: T = Field(description="Response data")
    timestamp: str = Field(description="Response timestamp")

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """Error Response Model

    Used for all error API responses, providing a unified error format.
    Supports multi-language messages (auto-translated via message_key).
    """

    code: int = Field(
        description=(
            "Error code (Custom business error code or HTTP status code)\n"
            "- In unified error format: Custom error code (e.g., 53009)\n"
            "- In non-unified error conversion: HTTP status code (e.g., 502)"
        )
    )
    message: str = Field(description="Error message")
    message_key: Optional[str] = Field(default=None, description="Translation key (if provided, overrides message)")
    error_code: str = Field(description="Error type identifier")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Error timestamp",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request unique identifier",
    )
    data: Optional[Any] = Field(default=None, description="Error data (optional, for unified format)")
    locale: Optional[str] = Field(default=None, description="Language code (for translating message_key)")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """Initialize error response, supporting auto translation"""
        # If message_key exists, auto translate
        message_key = data.get("message_key")
        locale = data.get("locale", "en_US")

        if message_key:
            # Extract format variables from kwargs (exclude defined fields and complex types)
            # Only ***REMOVED*** basic types (str, int, float, bool, None) to translation function,
            # avoid ***REMOVED***ing complex types like dict
            message_kwargs = {
                k: v
                for k, v in data.items()
                if k
                not in (
                    "code",
                    "message",
                    "message_key",
                    "error_code",
                    "details",
                    "timestamp",
                    "request_id",
                    "locale",
                    "default",
                )
                and isinstance(v, (str, int, float, bool, type(None)))
            }
            default_value = data.get("default")
            default_arg: Optional[str]
            if isinstance(default_value, str) or default_value is None:
                default_arg = default_value
            elif isinstance(default_value, (int, float, bool)):
                default_arg = str(default_value)
            else:
                default_arg = None
            translated_message = t(message_key, locale=locale, default=default_arg, **message_kwargs)
            data["message"] = translated_message
            # ✅ FIX: Keep message_key and locale fields, do not remove them
            # This allows including multi-language info in response for client use
            # data.pop("message_key", None)  # No longer remove
            # data.pop("locale", None)  # No longer remove

        super().__init__(**data)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Serialize model

        Note: message_key field is excluded by default (because message is already translated),
        but locale field is retained. If you need to exclude these fields, you can ***REMOVED*** the
        exclude parameter when calling.
        """
        # ✅ FIX: Exclude message_key (because message is already translated), but retain locale
        exclude = kwargs.pop("exclude", set())
        if not isinstance(exclude, set):
            exclude = set(exclude) if exclude else set()
        # Exclude message_key (because message is already translated)
        exclude.add("message_key")
        # Retain locale field so client knows used language
        exclude_none = kwargs.pop("exclude_none", True)
        return super().model_dump(exclude=exclude, exclude_none=exclude_none, **kwargs)


class PaginationInfo(BaseModel):
    """Pagination Info Model

    Provides metadata information for pagination queries
    """

    page: int = Field(description="Current page number", ge=1)
    page_size: int = Field(description="Page size", ge=1, le=100)
    total: int = Field(description="Total records", ge=0)
    total_pages: int = Field(description="Total pages", ge=0)
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")

    model_config = {"from_attributes": True}


class PaginationResponse(BaseModel):
    """Pagination Response Model

    Used for API responses of pagination queries
    Supports multi-language messages (auto-translated via message_key)
    """

    code: int = Field(default=200, description="Response code")
    message: str = Field(default="Operation successful", description="Response message")
    message_key: Optional[str] = Field(default=None, description="Translation key (if provided, overrides message)")
    data: List[Any] = Field(description="Data list")
    pagination: PaginationInfo = Field(description="Pagination info")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Response timestamp",
    )
    locale: Optional[str] = Field(default=None, description="Language code (for translating message_key)")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """Initialize pagination response, supporting auto translation"""
        # If message_key exists, auto translate
        message_key = data.get("message_key")
        locale = data.get("locale", "en_US")

        if message_key:
            # Extract format variables from kwargs (exclude defined fields)
            message_kwargs = {
                k: v
                for k, v in data.items()
                if k not in ("code", "message", "message_key", "data", "pagination", "timestamp", "locale")
            }
            translated_message = t(message_key, locale=locale, **message_kwargs)
            data["message"] = translated_message
            # Remove message_key to avoid Pydantic validation error
            data.pop("message_key", None)

        super().__init__(**data)


def create_success_response(
    data: Any = None, message: str = "Operation successful", code: int = 200
) -> SuccessResponse:
    """Create success response

    Args:
        data: Response data
        message: Response message
        code: Response code

    Returns:
        Success response object
    """
    return SuccessResponse(code=code, message=message, data=data)


def create_error_response(
    message: str,
    error_code: str,
    code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create error response

    Args:
        message: Error message
        error_code: Error type identifier
        code: HTTP status code
        details: Error details
        request_id: Request unique identifier (Optional, auto generated if not provided)

    Returns:
        Error response object
    """
    if request_id:
        return ErrorResponse(code=code, message=message, error_code=error_code, details=details, request_id=request_id)
    return ErrorResponse(code=code, message=message, error_code=error_code, details=details)


def create_pagination_response(
    data: List[Any],
    page: int,
    page_size: int,
    total: int,
    message: str = "Query successful",
    code: int = 200,
) -> PaginationResponse:
    """Create pagination response

    Args:
        data: Data list
        page: Current page number
        page_size: Page size
        total: Total records
        message: Response message
        code: Response code

    Returns:
        Pagination response object
    """
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Calculate has_prev and has_next
    has_prev = page > 1
    has_next = page < total_pages

    pagination_info = PaginationInfo(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    return PaginationResponse(code=code, message=message, data=data, pagination=pagination_info)
