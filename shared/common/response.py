"""
统一响应格式模块

提供标准化的API响应格式，包括成功响应、错误响应和分页响应
支持多语言消息
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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
        locale = data.get("locale", "zh_CN")

        if message_key:
            # 从 kwargs 中提取格式化变量（排除已定义的字段）
            message_kwargs = {
                k: v
                for k, v in data.items()
                if k not in ("code", "message", "message_key", "data", "timestamp", "locale")
            }
            translated_message = t(message_key, locale=locale, **message_kwargs)
            data["message"] = translated_message
            # 移除 message_key，避免 Pydantic 验证错误
            data.pop("message_key", None)

        super().__init__(**data)


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
        locale = data.get("locale", "zh_CN")

        if message_key:
            # 从 kwargs 中提取格式化变量（排除已定义的字段）
            message_kwargs = {
                k: v
                for k, v in data.items()
                if k
                not in ("code", "message", "message_key", "error_code", "details", "timestamp", "request_id", "locale")
            }
            translated_message = t(message_key, locale=locale, **message_kwargs)
            data["message"] = translated_message
            # 移除 message_key，避免 Pydantic 验证错误
            data.pop("message_key", None)

        super().__init__(**data)


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
        locale = data.get("locale", "zh_CN")

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
