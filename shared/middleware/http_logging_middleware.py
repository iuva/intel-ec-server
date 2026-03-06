"""
HTTP Request/Response Logging Middleware

Records detailed information for all HTTP requests and responses, including:
- Request method, path, query parameters
- Request body (JSON format)
- Response status code, response body (JSON format)
- Request duration

Uses pure ASGI middleware (no BaseHTTPMiddleware) so all code runs in the same
async context and avoids "no current event loop in thread" in worker threads (e.g. AnyIO).
"""

import json
import os
import time
from typing import Any, Callable, List, Optional
from urllib.parse import parse_qs

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def _get_header(scope: dict, name: str) -> Optional[str]:
    """Get header value from ASGI scope (case-insensitive)."""
    name_lower = name.lower().encode("utf-8")
    for k, v in scope.get("headers", []):
        if k.lower() == name_lower:
            return v.decode("utf-8", errors="replace")
    return None


def _parse_query_params(scope: dict) -> Optional[dict]:
    """Parse query string from scope into a dict (first value per key)."""
    qs = scope.get("query_string", b"")
    if not qs:
        return None
    try:
        parsed = parse_qs(qs.decode("utf-8", errors="replace"), keep_blank_values=True)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()} or None
    except Exception:
        return None


def _parse_json_body(body: bytes) -> Optional[dict]:
    """Parse JSON from body bytes; return None if not JSON or invalid."""
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


class HTTPLoggingMiddleware:
    """
    HTTP Request/Response Logging Middleware (pure ASGI).

    Automatically records detailed information for all HTTP requests and responses.
    Does not inherit BaseHTTPMiddleware; runs entirely in the same async context
    to avoid missing event loop in worker threads.
    """

    def __init__(self, app: Any, exclude_paths: Optional[list] = None) -> None:
        """
        Initialize the middleware.

        Args:
            app: ASGI application (next in chain)
            exclude_paths: List of path prefixes to exclude from logging (e.g. /health, /metrics)
        """
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    def _should_log(self, path: str) -> bool:
        """Return True if this path should be logged."""
        clean_path = path.split("?")[0]
        for exclude_path in self.exclude_paths:
            if clean_path.startswith(exclude_path):
                return False
        return True

    def _extract_error_summary(self, response_body: Any) -> str:
        """Extract a short error summary from response body for logging."""
        if not isinstance(response_body, dict):
            if isinstance(response_body, list) and response_body:
                first = response_body[0]
                if isinstance(first, dict):
                    return f"Validation error: {first.get('msg', 'Unknown error')}"
            return "Unknown error format"
        error_parts = []
        if "message" in response_body:
            error_parts.append(f"Message: {response_body['message']}")
        if "error_code" in response_body:
            error_parts.append(f"Error code: {response_body['error_code']}")
        if "details" in response_body and isinstance(response_body["details"], dict):
            details = response_body["details"]
            if "errors" in details and isinstance(details["errors"], dict):
                errs = details["errors"]
                if errs:
                    field_errors = [f"{f}: {msg}" for f, msg in errs.items()]
                    error_parts.append(f"Validation errors: {', '.join(field_errors)}")
        if not error_parts:
            error_parts.append(f"Response keys: {', '.join(response_body.keys())}")
        return " | ".join(error_parts)

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        if not self._should_log(path):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        query_params = _parse_query_params(scope)
        log_body = os.getenv("ENABLE_HTTP_BODY_LOGGING", "false").lower() in ("true", "1", "yes")

        # Optionally buffer request body for logging (must consume receive before calling app)
        request_body_for_log: Optional[dict] = None
        request_messages: List[dict] = []

        if log_body and ((_get_header(scope, "content-type") or "").lower().startswith("application/json")):
            while True:
                message = await receive()
                request_messages.append(message)
                if not message.get("more_body", True):
                    break
            raw = b"".join(m.get("body", b"") for m in request_messages)
            request_body_for_log = _parse_json_body(raw)

        async def new_receive() -> dict:
            if request_messages:
                return request_messages.pop(0)
            return await receive()

        request_log_data = {
            "method": method,
            "path": path,
            "query_params": query_params,
            "client_ip": client_ip,
        }
        if request_body_for_log is not None:
            request_log_data["body"] = request_body_for_log
        logger.info(f"HTTP Request: {method} {path}", extra=request_log_data)

        start_time = time.time()
        response_status: Optional[int] = None
        response_headers: List[tuple] = []
        response_body_chunks: List[bytes] = []
        response_body_complete = False

        async def send_wrapped(message: dict) -> None:
            nonlocal response_status, response_body_complete
            if message["type"] == "http.response.start":
                response_status = message.get("status")
                response_headers.extend(message.get("headers", []))
            elif message["type"] == "http.response.body":
                response_body_chunks.append(message.get("body", b""))
                if not message.get("more_body", True):
                    response_body_complete = True
            await send(message)

        try:
            await self.app(scope, new_receive, send_wrapped)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"HTTP Request Exception: {method} {path} - {type(e).__name__}: {e!s} ({duration_ms:.2f}ms)",
                extra={
                    "method": method,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration_ms, 2),
                },
                exc_info=True,
            )
            raise

        duration_ms = (time.time() - start_time) * 1000

        status_code = response_status or 0
        response_log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
        is_error_response = status_code >= 400

        if response_body_complete and response_body_chunks:
            raw_response = b"".join(response_body_chunks)
            content_type = next(
                (v.decode("utf-8", errors="replace") for k, v in response_headers if k.lower() == b"content-type"),
                "",
            )
            if "application/json" in content_type.lower():
                response_body = _parse_json_body(raw_response)
                if response_body is not None:
                    response_log_data["body"] = response_body
                    if is_error_response:
                        summary = self._extract_error_summary(response_body)
                        logger.warning(
                            f"HTTP Error Response: {method} {path} - {status_code} ({duration_ms:.2f}ms) - {summary}",
                            extra=response_log_data,
                        )
                    else:
                        logger.info(
                            f"HTTP Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
                            extra=response_log_data,
                        )
                elif is_error_response:
                    logger.warning(
                        f"HTTP Error Response: {method} {path} - {status_code} ({duration_ms:.2f}ms) - Unable to read response body",
                        extra={**response_log_data, "content_type": content_type},
                    )
                else:
                    logger.info(
                        f"HTTP Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
                        extra=response_log_data,
                    )
            else:
                if is_error_response:
                    logger.warning(
                        f"HTTP Error Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
                        extra=response_log_data,
                    )
                else:
                    logger.info(
                        f"HTTP Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
                        extra=response_log_data,
                    )
        else:
            if is_error_response:
                logger.warning(
                    f"HTTP Error Response: {method} {path} - {status_code} ({duration_ms:.2f}ms) - Unable to read response body",
                    extra={
                        **response_log_data,
                        "hint": "Response may be streaming or non-JSON",
                    },
                )
            else:
                logger.info(
                    f"HTTP Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
                    extra=response_log_data,
                )
