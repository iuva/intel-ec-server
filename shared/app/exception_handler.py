"""
Unified Exception Handling Integration Tool
"""

import json
import re
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.common.exceptions import BusinessError, ErrorCode
from shared.common.i18n import parse_accept_language, t
from shared.common.loguru_config import get_logger
from shared.common.response import ErrorResponse

logger = get_logger(__name__)


def setup_exception_handling(app: FastAPI, service_name: str = "unknown") -> None:
    """Set up unified exception handling for FastAPI application

    Args:
        app: FastAPI application instance
        service_name: Service name (for logging)
    """

    # Register Pydantic validation error handler (handle 422 errors)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors"""
        # ✅ Enhanced logging: record detailed validation error information, including stack trace
        # Try to get request body (if available)
        request_body_preview = None
        try:
            # Check if request body has been read
            if hasattr(request, "_body") and request._body:
                body_str = (
                    request._body.decode("utf-8", errors="ignore")
                    if isinstance(request._body, bytes)
                    else str(request._body)
                )
                request_body_preview = body_str[:500] if len(body_str) > 500 else body_str
        except Exception:
            # If unable to read request body, ignore error
            ***REMOVED***

        logger.warning(
            "Parameter validation failed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params),
                "errors": exc.errors(),
                "error_count": len(exc.errors()),
                "request_body_preview": request_body_preview,
            },
            exc_info=True,  # ✅ Print complete stack trace
        )

        # Format error information, provide clearer field-level errors
        field_errors: Dict[str, str] = {}
        for error in exc.errors():
            field_path = "".join(str(loc) for loc in error["loc"])
            # Only keep error message, not type
            field_errors[field_path] = error.get("msg", "Unknown error")

        error_response = ErrorResponse(
            code=422,
            message="Request parameter validation failed",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"errors": field_errors},
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    # Register HTTP exception handler
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exception"""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

        # Get language preference
        accept_language = request.headers.get("Accept-Language")
        locale = parse_accept_language(accept_language)

        # Try to understand the actual content of detail
        detail: Any = exc.detail

        # If it's a dict and contains error_code, it means it's a unified format thrown from @handle_api_errors
        if isinstance(detail, dict) and "error_code" in detail:
            # Directly return unified format error response
            return JSONResponse(status_code=exc.status_code, content=detail)

        # If it's a string, try to parse JSON
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
                if isinstance(detail, dict) and "error_code" in detail:
                    return JSONResponse(status_code=exc.status_code, content=detail)
            except (json.JSONDecodeError, TypeError):
                # JSON parsing failed, continue with conversion logic
                ***REMOVED***

        # For non-unified format exceptions, convert to unified format
        error_code_map = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.RESOURCE_NOT_FOUND,
            405: "METHOD_NOT_ALLOWED",
            500: ErrorCode.INTERNAL_SERVER_ERROR,
        }

        # Provide more friendly error message for 405 error (using multilingual)
        if exc.status_code == 405:
            # Try to extract allowed methods from detail
            detail_str = str(detail)

            # FastAPI's 405 error may contain allowed methods information
            # For example: "Method Not Allowed" or more detailed error message
            if "Method Not Allowed" in detail_str or "method not allowed" in detail_str.lower():
                # Try to extract allowed methods (if any)
                allowed_match = re.search(r"allowed.*?\[(.*?)\]", detail_str, re.IGNORECASE)
                if allowed_match:
                    allowed_methods = allowed_match.group(1)
                    message_key = "error.http.method_not_allowed_with_methods"
                    message = t(message_key, locale=locale, allowed_methods=allowed_methods)
                else:
                    message_key = "error.http.method_not_allowed"
                    message = t(message_key, locale=locale)
            else:
                message_key = "error.http.method_not_allowed"
                message = t(message_key, locale=locale)

            error_response = ErrorResponse(
                code=exc.status_code,
                message=message,
                message_key=message_key,
                error_code=error_code_map.get(exc.status_code, "HTTP_ERROR"),
                locale=locale,
            )
        else:
            # Other errors use default message
            error_response = ErrorResponse(
                code=exc.status_code,
                message=str(detail),
                error_code=error_code_map.get(exc.status_code, "HTTP_ERROR"),
                locale=locale,
            )

        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    # Register business exception handler
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        """Handle business exception"""
        logger.warning(f"Business exception: {exc.error_code} - {exc.message}")

        error_response = ErrorResponse(
            code=exc.code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        )

        # Use http_status_code as HTTP response status code (must be valid HTTP status code 100-599)
        # The code in response body is custom error code (may be service-level error code like 53009)
        return JSONResponse(status_code=exc.http_status_code, content=error_response.model_dump())

    # ❌ Important: Do not add middleware here!
    # When setup_exception_handling is called, the application has already started in lifespan
    # Middleware cannot be added at this point
    # (will throw "Cannot add middleware after an application has started" error)
    # Middleware must be added after FastAPI application creation, before lifespan starts
    # Reference: auth-service/app/main.py lines 70-71 - Add immediately after app creation

    logger.info(f"Unified exception handling enabled for {service_name}")
    logger.info("Exception handlers registered: RequestValidationError, HTTPException, BusinessError")
