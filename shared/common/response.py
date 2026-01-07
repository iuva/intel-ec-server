"""
统一响应格式模块

提供标准化的API响应格式，包括成功响应、错误响应和分页响应
支持多语言消息
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, model_serializer

# 定义泛型类型变量
T = TypeVar("T")

try:
    from shared.common.i18n import t
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.i18n import t


class SuccessResponse(BaseModel):
    """成功响应模型

    用于所有成功的API响应，提供统一的响应格式
    支持多语言消息（通过 message_key 自动翻译）
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="操作成功", description="响应消息")
    message_key: Optional[str] = Field(default=None, description="翻译键（如果提供，将覆盖 message）")
    data: Any = Field(description="响应数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="响应时间戳",
    )
    locale: Optional[str] = Field(default=None, description="语言代码（用于翻译 message_key）")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """初始化成功响应，支持自动翻译"""
        # 如果有 message_key，自动翻译
        message_key = data.get("message_key")
        locale = data.get("locale", "en_US")

        if message_key:
            # 从 kwargs 中提取格式化变量（排除已定义的字段和复杂类型）
            # 只传递基本类型（str, int, float, bool, None）给翻译函数，避免传递字典等复杂类型
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
            # 移除 message_key，避免 Pydantic 验证错误
            data.pop("message_key", None)

        super().__init__(**data)

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """序列化模型，排除 message_key 字段"""
        data = {
            "code": self.code,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        # 只添加非 None 的 locale
        if self.locale is not None:
            data["locale"] = self.locale
        return data

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """序列化模型

        注意：默认排除 message_key 字段（因为 message 已经翻译），但保留 locale 字段
        如果需要排除这些字段，可以在调用时传递 exclude 参数
        """
        # ✅ 排除 message_key（因为 message 已经翻译），但保留 locale
        exclude = kwargs.pop("exclude", set())
        if not isinstance(exclude, set):
            exclude = set(exclude) if exclude else set()
        # 排除 message_key（因为 message 已经翻译）
        exclude.add("message_key")
        # 保留 locale 字段，以便客户端知道使用的语言
        exclude_none = kwargs.pop("exclude_none", True)
        return super().model_dump(exclude=exclude, exclude_none=exclude_none, **kwargs)


class Result(BaseModel, Generic[T]):
    """统一的 API 响应结果模型

    用于所有 API 响应，提供统一的响应格式。
    支持泛型类型，确保 FastAPI 文档能正确显示 data 字段的具体类型。

    字段说明:
        - code: 响应码（200 表示成功）
        - message: 响应消息
        - data: 响应数据（泛型类型 T）
        - timestamp: 响应时间戳（ISO 8601 格式）
        - locale: 语言代码（可选，用于多语言支持）

    使用示例:
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
                message="查询成功",
                data=user,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        ```

    这样在 FastAPI 文档中就能看到完整的 data 字段 Schema。
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="操作成功", description="响应消息")
    data: T = Field(description="响应数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="响应时间戳（ISO 8601 格式）",
    )
    locale: Optional[str] = Field(default=None, description="语言代码（用于多语言支持）")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """初始化响应结果，自动设置时间戳"""
        # 如果没有提供 timestamp，自动生成
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        super().__init__(**data)


class TypedSuccessResponse(BaseModel, Generic[T]):
    """类型化的成功响应包装模型（已废弃，请使用 Result[T]）

    注意：此类已废弃，请使用 Result[T] 替代。
    保留此类仅用于向后兼容，新代码请使用 Result[T]。
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="操作成功", description="响应消息")
    data: T = Field(description="响应数据")
    timestamp: str = Field(description="响应时间戳")

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """错误响应模型

    用于所有错误的API响应，提供统一的错误格式
    支持多语言消息（通过 message_key 自动翻译）
    """

    code: int = Field(
        description=(
            "错误码（自定义业务错误码或HTTP状态码）\n"
            "- 在统一格式错误中：为自定义错误码（如53009）\n"
            "- 在非统一格式错误转换中：为HTTP状态码（如502）"
        )
    )
    message: str = Field(description="错误消息")
    message_key: Optional[str] = Field(default=None, description="翻译键（如果提供，将覆盖 message）")
    error_code: str = Field(description="错误类型标识")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="错误时间戳",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="请求唯一标识符",
    )
    locale: Optional[str] = Field(default=None, description="语言代码（用于翻译 message_key）")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """初始化错误响应，支持自动翻译"""
        # 如果有 message_key，自动翻译
        message_key = data.get("message_key")
        locale = data.get("locale", "en_US")

        if message_key:
            # 从 kwargs 中提取格式化变量（排除已定义的字段和复杂类型）
            # 只传递基本类型（str, int, float, bool, None）给翻译函数，避免传递字典等复杂类型
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
            # ✅ 修复：保留 message_key 和 locale 字段，不删除它们
            # 这样可以在响应中包含多语言信息，供客户端使用
            # data.pop("message_key", None)  # 不再删除
            # data.pop("locale", None)  # 不再删除

        super().__init__(**data)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """序列化模型

        注意：默认排除 message_key 字段（因为 message 已经翻译），但保留 locale 字段
        如果需要排除这些字段，可以在调用时传递 exclude 参数
        """
        # ✅ 修复：排除 message_key（因为 message 已经翻译），但保留 locale
        exclude = kwargs.pop("exclude", set())
        if not isinstance(exclude, set):
            exclude = set(exclude) if exclude else set()
        # 排除 message_key（因为 message 已经翻译）
        exclude.add("message_key")
        # 保留 locale 字段，以便客户端知道使用的语言
        exclude_none = kwargs.pop("exclude_none", True)
        return super().model_dump(exclude=exclude, exclude_none=exclude_none, **kwargs)


class PaginationInfo(BaseModel):
    """分页信息模型

    提供分页查询的元数据信息
    """

    page: int = Field(description="当前页码", ge=1)
    page_size: int = Field(description="每页大小", ge=1, le=100)
    total: int = Field(description="总记录数", ge=0)
    total_pages: int = Field(description="总页数", ge=0)
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")

    model_config = {"from_attributes": True}


class PaginationResponse(BaseModel):
    """分页响应模型

    用于分页查询的API响应
    支持多语言消息（通过 message_key 自动翻译）
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="操作成功", description="响应消息")
    message_key: Optional[str] = Field(default=None, description="翻译键（如果提供，将覆盖 message）")
    data: List[Any] = Field(description="数据列表")
    pagination: PaginationInfo = Field(description="分页信息")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="响应时间戳",
    )
    locale: Optional[str] = Field(default=None, description="语言代码（用于翻译 message_key）")

    model_config = {"from_attributes": True}

    def __init__(self, **data: Any) -> None:
        """初始化分页响应，支持自动翻译"""
        # 如果有 message_key，自动翻译
        message_key = data.get("message_key")
        locale = data.get("locale", "en_US")

        if message_key:
            # 从 kwargs 中提取格式化变量（排除已定义的字段）
            message_kwargs = {
                k: v
                for k, v in data.items()
                if k not in ("code", "message", "message_key", "data", "pagination", "timestamp", "locale")
            }
            translated_message = t(message_key, locale=locale, **message_kwargs)
            data["message"] = translated_message
            # 移除 message_key，避免 Pydantic 验证错误
            data.pop("message_key", None)

        super().__init__(**data)


def create_success_response(data: Any = None, message: str = "操作成功", code: int = 200) -> SuccessResponse:
    """创建成功响应

    Args:
        data: 响应数据
        message: 响应消息
        code: 响应码

    Returns:
        成功响应对象
    """
    return SuccessResponse(code=code, message=message, data=data)


def create_error_response(
    message: str,
    error_code: str,
    code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """创建错误响应

    Args:
        message: 错误消息
        error_code: 错误类型标识
        code: HTTP状态码
        details: 错误详情
        request_id: 请求唯一标识符（可选，不提供则自动生成）

    Returns:
        错误响应对象
    """
    if request_id:
        return ErrorResponse(code=code, message=message, error_code=error_code, details=details, request_id=request_id)
    return ErrorResponse(code=code, message=message, error_code=error_code, details=details)


def create_pagination_response(
    data: List[Any],
    page: int,
    page_size: int,
    total: int,
    message: str = "查询成功",
    code: int = 200,
) -> PaginationResponse:
    """创建分页响应

    Args:
        data: 数据列表
        page: 当前页码
        page_size: 每页大小
        total: 总记录数
        message: 响应消息
        code: 响应码

    Returns:
        分页响应对象
    """
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # 计算是否有上一页和下一页
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
