"""
HTTP Request/Response Logging Middleware

Records detailed information for all HTTP requests and responses, including:
- Request method, path, query parameters
- Request body (JSON format)
- Response status code, response body (JSON format)
- Request duration
"""

import json
import time
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP Request/Response Logging Middleware

    Automatically records detailed information for all HTTP requests and responses:
    - Request method, path, query parameters
    - Request body (JSON format)
    - Response status code, response body (JSON format)
    - Request duration
    """

    def __init__(self, app: Any, exclude_paths: Optional[list] = None) -> None:
        """
        Initialize the middleware

        Args:
            app: FastAPI application instance
            exclude_paths: List of excluded paths (paths not to log, such as /health, /metrics)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    def _should_log(self, path: str) -> bool:
        """Determine whether to log

        Args:
            path: Request path

        Returns:
            Whether to log
        """
        # Remove query parameters
        clean_path = path.split("?")[0]

        # Check if in exclusion list
        for exclude_path in self.exclude_paths:
            if clean_path.startswith(exclude_path):
                return False

        return True

    async def _read_request_body(self, request: Request) -> Optional[dict]:
        """Read request body (JSON format)

        Args:
            request: FastAPI request object

        Returns:
            Parsed JSON object, return None if not in JSON format
        """
        try:
            # Check Content-Type
            content_type = request.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return None

            # Read body
            body = await request.body()

            # If body is empty, return None
            if not body:
                return None

            # Try to parse JSON
            try:
                return json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None

        except Exception:
            # Return None when reading fails
            return None

    async def _read_response_body(self, response: Response) -> Optional[dict]:
        """Read response body (JSON format)

        Args:
            response: FastAPI response object

        Returns:
            Parsed JSON object, return None if not in JSON format
        """
        try:
            # Check Content-Type
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return None

            # If it's a StreamingResponse, unable to read body
            if isinstance(response, StreamingResponse):
                return None

            # Method 1: Try to read from JSONResponse's body property (FastAPI/Starlette)
            if hasattr(response, "body"):
                body = response.body
                if body:
                    if isinstance(body, bytes):
                        try:
                            return json.loads(body.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            return None
                    elif isinstance(body, str):
                        try:
                            return json.loads(body)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            return None
                    elif isinstance(body, (dict, list)):
                        # If body is already a dictionary or list, return directly
                        return body

            # Method 2: Try to get content from JSONResponse's render method
            # FastAPI's JSONResponse serializes the body when rendering
            # Note: The render() method doesn't require parameters,
            # but modifies the response object, so it's not used here
            # Instead, read the body property directly in dispatch

            # Method 3: Try to read from _content property (for certain response types)
            if hasattr(response, "_content") and response._content:
                body = response._content
                if isinstance(body, bytes):
                    try:
                        return json.loads(body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        return None

            # ❌ Note: Don't try to read from body_iterator!
            # body_iterator is part of the response stream, consuming it will break the response stream
            # If attempting to recreate, an async iterator must be created, but this is complex and error-prone
            # For JSONResponse, it should be possible to read from body or content property

            return None

        except Exception:
            # Return None when reading fails
            return None

    def _extract_error_summary(self, response_body: Any) -> str:
        """Extract error summary information from response body

        Args:
            response_body: Response body (could be dictionary, list, or other type)

        Returns:
            Error summary string
        """
        if not isinstance(response_body, dict):
            # If it's a list, try to extract the first error
            if isinstance(response_body, list) and response_body:
                first_error = response_body[0]
                if isinstance(first_error, dict):
                    return f"Validation error: {first_error.get('msg', 'Unknown error')}"
            return "Unknown error format"

        # Try to extract error information
        error_parts = []

        # 1. Extract message field
        if "message" in response_body:
            error_parts.append(f"Message: {response_body['message']}")

        # 2. Extract error_code field
        if "error_code" in response_body:
            error_parts.append(f"Error code: {response_body['error_code']}")

        # 3. Extract validation errors from details (422 errors)
        if "details" in response_body and isinstance(response_body["details"], dict):
            details = response_body["details"]
            # Check if there are errors fields (validation errors)
            if "errors" in details and isinstance(details["errors"], dict):
                errors = details["errors"]
                if errors:
                    # Extract field validation errors
                    field_errors = []
                    for field, error_msg in errors.items():
                        field_errors.append(f"{field}: {error_msg}")
                    if field_errors:
                        error_parts.append(f"Validation errors: {', '.join(field_errors)}")

        # 4. If no information extracted, return keys from response body
        if not error_parts:
            error_parts.append(f"Response keys: {', '.join(response_body.keys())}")

        return " | ".join(error_parts)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process request and log

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            FastAPI response object
        """
        # Check whether to log
        if not self._should_log(request.url.path):
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Extract request information
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else "unknown"

        # Read request body (JSON format)
        request_body = await self._read_request_body(request)

        # Log request
        request_log_data = {
            "method": method,
            "path": path,
            "query_params": query_params if query_params else None,
            "client_ip": client_ip,
        }

        if request_body is not None:
            request_log_data["body"] = request_body
            logger.info(
                f"HTTP Request: {method} {path}",
                extra=request_log_data,
            )
        else:
            logger.info(
                f"HTTP Request: {method} {path}",
                extra=request_log_data,
            )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Extract response information
            status_code = response.status_code

            # ✅ Read response body (JSON format)
            # Using improved _read_response_body method
            response_body = await self._read_response_body(response)

            # Log response
            response_log_data = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            }

            # ✅ For error responses (4xx, 5xx), always try to log response body, even if reading fails log warning
            is_error_response = status_code >= 400

            if response_body is not None:
                response_log_data["body"] = response_body
                # ✅ For error responses, use WARNING level and highlight error information
                if is_error_response:
                    # Extract key error information
                    error_summary = self._extract_error_summary(response_body)
                    logger.warning(
                        (
                            f"HTTP Error Response: {method} {path} - {status_code} "
                            f"({duration * 1000:.2f}ms) - {error_summary}"
                        ),
                        extra=response_log_data,
                    )
                else:
                    logger.info(
                        f"HTTP Response: {method} {path} - {status_code} ({duration * 1000:.2f}ms)",
                        extra=response_log_data,
                    )
            else:
                # ✅ For error responses, even if unable to read body, also log warning
                if is_error_response:
                    logger.warning(
                        (
                            f"HTTP Error Response: {method} {path} - {status_code} "
                            f"({duration * 1000:.2f}ms) - Unable to read response body"
                        ),
                        extra={
                            **response_log_data,
                            "hint": (
                                "Response body may not be in JSON format, or response type "
                                "doesn't support reading (e.g., StreamingResponse)"
                            ),
                            "content_type": response.headers.get("content-type"),
                        },
                    )
                else:
                    # Even if unable to read body, still log response status code and duration
                    logger.info(
                        f"HTTP Response: {method} {path} - {status_code} ({duration * 1000:.2f}ms)",
                        extra=response_log_data,
                    )

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log exception (including full stack trace)
            logger.error(
                f"HTTP Request Exception: {method} {path} - {type(e).__name__}: {str(e)} ({duration * 1000:.2f}ms)",
                extra={
                    "method": method,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,  # Record full stack trace
            )

            # Re-raise exception
            raise
