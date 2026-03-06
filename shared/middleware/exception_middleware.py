"""
Unified Exception Handling Middleware

Catches unhandled exceptions in route handlers, providing the last line of defense for the system.
Supports multilingual error messages.

Uses pure ASGI middleware (no BaseHTTPMiddleware) so exception handling runs in the same
async context and avoids "no current event loop in thread" in worker threads (e.g. AnyIO).
"""

import json
import os
import sys
from typing import Any, Callable, Dict, Optional

try:
    from shared.common.exceptions import BusinessError, ErrorCode
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.exceptions import BusinessError, ErrorCode
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse

logger = get_logger(__name__)


def _get_accept_language_from_scope(scope: dict) -> Optional[str]:
    """Extract Accept-Language from ASGI scope headers."""
    for name, value in scope.get("headers", []):
        if name.lower() == b"accept-language":
            return value.decode("utf-8", errors="replace")
    return None


def _build_error_body(
    scope: dict,
    *,
    code: int,
    message_key: Optional[str] = None,
    message: Optional[str] = None,
    error_code: Any = None,
    details: Optional[Dict[str, Any]] = None,
    locale: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build ErrorResponse model_dump in a pure sync context for ASGI to send."""
    accept_language = _get_accept_language_from_scope(scope)
    resolved_locale = locale or parse_accept_language(accept_language)
    if message_key:
        error_response = ErrorResponse(
            code=code,
            message_key=message_key,
            error_code=error_code,
            details=details,
            locale=resolved_locale,
            **(details or {}),
            **kwargs,
        )
    else:
        error_response = ErrorResponse(
            code=code,
            message=message or "",
            error_code=error_code,
            details=details,
            locale=resolved_locale,
        )
    return error_response.model_dump()


class UnifiedExceptionMiddleware:
    """Unified exception handling middleware (pure ASGI).

    Catches exceptions in routes and other middleware as the last line of defense.
    Does not inherit BaseHTTPMiddleware; runs entirely in the same async context
    to avoid missing event loop in worker threads.
    """

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        try:
            await self.app(scope, receive, send)
        except BusinessError as exc:
            logger.warning(
                f"Business exception: {exc.error_code} - {exc.message}",
                extra={"error_code": exc.error_code, "path": path, "method": method},
            )
            body = _build_error_body(
                scope,
                code=exc.code,
                message_key=exc.message_key,
                message=exc.message,
                error_code=exc.error_code,
                details=exc.details,
                locale=exc.locale,
                **(exc.details or {}),
            )
            await _send_json_response(send, exc.http_status_code, body)
        except Exception as exc:
            error_message = str(exc)
            logger.error(
                f"Unhandled exception: {type(exc).__name__} - {error_message}",
                extra={"error": error_message, "path": path, "method": method},
                exc_info=True,
            )
            body = _build_error_body(
                scope,
                code=500,
                message_key="error.internal",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            )
            await _send_json_response(send, 500, body)


async def _send_json_response(send: Callable, status: int, content: Dict[str, Any]) -> None:
    """Send JSON response according to ASGI protocol."""
    body = json.dumps(content, ensure_ascii=False).encode("utf-8")
    headers = [(b"content-type", b"application/json; charset=utf-8")]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})
