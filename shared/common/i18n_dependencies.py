"""
国际化依赖注入模块

提供 FastAPI 依赖注入函数，用于从请求头获取语言偏好。
"""

import os
import sys
from typing import Optional

from fastapi import Header, Request

try:
    from shared.common.i18n import get_i18n_manager, parse_accept_language, t
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.i18n import get_i18n_manager, parse_accept_language, t


def get_locale(
    request: Request,
    accept_language: Optional[str] = Header(None, description="Accept-Language 请求头"),
) -> str:
    """从请求头获取语言偏好

    Args:
        request: FastAPI 请求对象
        accept_language: Accept-Language 请求头值

    Returns:
        语言代码（如 "zh_CN", "en_US"）

    Example:
        ```python
        @app.get("/users")
        async def list_users(locale: str = Depends(get_locale)):
            message = t("success.query", locale=locale)
            return SuccessResponse(message=message, data=users)
        ```
    """
    # 优先从请求头获取
    if accept_language:
        return parse_accept_language(accept_language)

    # 从请求对象获取（如果中间件已经解析过）
    if hasattr(request.state, "locale"):
        return request.state.locale

    # 默认语言
    return "zh_CN"


def translate(key: str, locale: Optional[str] = None, default: Optional[str] = None, **kwargs):
    """翻译函数（用于依赖注入）

    Args:
        key: 翻译键
        locale: 语言代码（如果为 None 则从请求中获取）
        default: 默认消息
        **kwargs: 格式化变量

    Returns:
        翻译后的消息

    Example:
        ```python
        @app.get("/users")
        async def list_users(
            locale: str = Depends(get_locale),
            _t: callable = Depends(lambda: lambda k, **kw: t(k, locale=locale, **kw))
        ):
            message = _t("success.query")
            return SuccessResponse(message=message, data=users)
        ```
    """

    # 这里返回一个闭包函数，实际使用时需要传入 locale
    def _translate(k: str, loc: Optional[str] = locale, **kw):
        return t(k, locale=loc, default=default, **kw)

    return _translate
