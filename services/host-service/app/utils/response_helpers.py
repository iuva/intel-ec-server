"""响应构建辅助函数

提供统一的响应构建工具函数，减少代码重复。
"""

from typing import Any, Optional

from shared.common.i18n import t
from shared.common.response import Result


def create_success_result(
    data: Any,
    message_key: str,
    locale: str = "zh_CN",
    default_message: Optional[str] = None,
    code: int = 200,
) -> Result[Any]:
    """创建成功响应结果

    Args:
        data: 响应数据
        message_key: 消息键（用于多语言）
        locale: 语言偏好，默认 "zh_CN"
        default_message: 默认消息（如果翻译键不存在时使用）
        code: HTTP 状态码，默认 200

    Returns:
        Result: 成功响应结果
    """
    message = t(message_key, locale=locale, default=default_message or "操作成功")
    return Result(code=code, message=message, data=data, locale=locale)
