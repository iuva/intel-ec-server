"""
Internationalization Dependency Injection Module

Provides FastAPI dependency injection functions to get language preferences from request headers.
"""

import os
import sys
from typing import Optional

from fastapi import Header, Request

try:
    from shared.common.i18n import parse_accept_language, t
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.i18n import parse_accept_language, t


def get_locale(
    request: Request, accept_language: Optional[str] = Header(None, description="Accept-Language header")
) -> str:
    """Get language preference from request header

    Args:
        request: FastAPI request object
        accept_language: Accept-Language header value

    Returns:
        Language code (e.g. "zh_CN", "en_US")

    Example:
        ```python
        @app.get("/users")
        async def list_users(locale: str = Depends(get_locale)):
            message = t("success.query", locale=locale)
            return SuccessResponse(message=message, data=users)
        ```
    """
    # Prioritize getting from request header
    if accept_language:
        return parse_accept_language(accept_language)

    # Get from request object (if middleware has already parsed)
    if hasattr(request.state, "locale"):
        return request.state.locale

    # Default language
    return "zh_CN"


def translate(key: str, locale: Optional[str] = None, default: Optional[str] = None, **kwargs):
    """Translation function (for dependency injection)

    Args:
        key: Translation key
        locale: Language code (if None, get from request)
        default: Default message
        **kwargs: Formatting variables

    Returns:
        Translated message

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

    # Here return a closure function, locale needs to be ***REMOVED***ed in when actually used
    def _translate(k: str, loc: Optional[str] = locale, **kw):
        return t(k, locale=loc, default=default, **kw)

    return _translate
