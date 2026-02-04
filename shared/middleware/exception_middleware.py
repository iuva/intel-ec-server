"""
Unified Exception Handling Middleware

Catches unhandled exceptions in route handlers, providing the last line of defense for the system.
Supports multilingual error messages
"""

import os
import sys
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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


class UnifiedExceptionMiddleware(BaseHTTPMiddleware):
    """Unified Exception Handling Middleware

    Catches exceptions in route handlers and other middleware, providing the last line of defense.
    Most exceptions should be handled by application-level exception handlers.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Middleware dispatch handling

        Args:
            request: Request object
            call_next: Next middleware or route handler

        Returns:
            Response object
        """
        try:
            return await call_next(request)
        except BusinessError as exc:
            # Business exception
            logger.warning(
                f"Business exception: {exc.error_code} - {exc.message}",
                extra={
                    "error_code": exc.error_code,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            # Get language preference (from request headers or locale in exception)
            accept_language = request.headers.get("Accept-Language")
            locale = exc.locale or parse_accept_language(accept_language)

            # If there is a message_key, use it to create response; otherwise use message
            if exc.message_key:
                error_response = ErrorResponse(
                    code=exc.code,
                    message_key=exc.message_key,
                    error_code=exc.error_code,
                    details=exc.details,
                    locale=locale,
                    **exc.details,  # Pass formatting variables
                )
            else:
                error_response = ErrorResponse(
                    code=exc.code,
                    message=exc.message,
                    error_code=exc.error_code,
                    details=exc.details,
                    locale=locale,
                )

            # Use http_status_code as HTTP status code (must be valid 100-599)
            # The code in response body is a custom error code (could be a value like 53009)
            return JSONResponse(status_code=exc.http_status_code, content=error_response.model_dump())
        except Exception as exc:
            # Catch all unhandled exceptions
            error_message = str(exc)
            logger.error(
                f"Unhandled exception: {type(exc).__name__} - {error_message}",
                extra={"error": error_message, "path": request.url.path, "method": request.method},
                exc_info=True,
            )

            # Get language preference
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            error_response = ErrorResponse(
                code=500,
                message_key="error.internal",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                locale=locale,
            )
            return JSONResponse(status_code=500, content=error_response.model_dump())
