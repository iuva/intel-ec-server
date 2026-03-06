"""Request Context Middleware

Generates a unique request_id for each request and injects it into the logging context.
Supports reading an existing request_id from request headers (for distributed tracing).

Uses pure ASGI (no BaseHTTPMiddleware) so context runs in the same async context
and avoids "no current event loop in thread" in worker threads (e.g. AnyIO).

Usage:
    from shared.middleware.request_context_middleware import (
        RequestContextMiddleware,
        get_request_id,
        get_request_context,
    )

    # Add middleware to FastAPI app
    app.add_middleware(RequestContextMiddleware)

    # Get current request ID anywhere
    request_id = get_request_id()

    # Get full context
    context = get_request_context()
"""

import contextvars
import json
import time
from typing import Any, Callable, Dict, Optional
import uuid


try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
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


# Request context variables
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
_username_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("username", default=None)
_client_ip_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("client_ip", default=None)
_request_path_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_path", default=None)
_request_method_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_method", default=None)
_request_start_time_var: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "request_start_time", default=None
)


def get_request_id() -> Optional[str]:
    """Get the request_id for the current request

    Returns:
        The request_id for the current request, or None if not in request context
    """
    return _request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get the user_id for the current request

    Returns:
        The user_id for the current request, or None if not authenticated
    """
    return _user_id_var.get()


def get_username() -> Optional[str]:
    """Get the username for the current request

    Returns:
        The username for the current request, or None if not authenticated
    """
    return _username_var.get()


def get_client_ip() -> Optional[str]:
    """Get the client IP for the current request

    Returns:
        The client IP for the current request
    """
    return _client_ip_var.get()


def get_request_path() -> Optional[str]:
    """Get the path for the current request

    Returns:
        The path for the current request
    """
    return _request_path_var.get()


def get_request_method() -> Optional[str]:
    """Get the method for the current request

    Returns:
        The method for the current request
    """
    return _request_method_var.get()


def get_request_duration_ms() -> Optional[float]:
    """Get the elapsed time for the current request (in milliseconds)

    Returns:
        Elapsed time for the request (in milliseconds), or None if not in request context
    """
    start_time = _request_start_time_var.get()
    if start_time is not None:
        return (time.perf_counter() - start_time) * 1000
    return None


def get_request_context() -> Dict[str, Any]:
    """Get the complete context information for the current request

    Returns a dictionary containing request_id, user_id, username, client_ip, etc.
    Used to automatically add context information to logs.

    Returns:
        Dictionary containing request context
    """
    context: Dict[str, Any] = {}

    request_id = get_request_id()
    if request_id:
        context["request_id"] = request_id

    user_id = get_user_id()
    if user_id:
        context["user_id"] = user_id

    username = get_username()
    if username:
        context["username"] = username

    client_ip = get_client_ip()
    if client_ip:
        context["client_ip"] = client_ip

    request_path = get_request_path()
    if request_path:
        context["path"] = request_path

    request_method = get_request_method()
    if request_method:
        context["method"] = request_method

    duration_ms = get_request_duration_ms()
    if duration_ms is not None:
        context["elapsed_ms"] = round(duration_ms, 2)

    return context


def set_user_context(user_id: Optional[str] = None, username: Optional[str] = None) -> None:
    """Set user context (typically called after authentication)

    Args:
        user_id: User ID
        username: Username
    """
    if user_id:
        _user_id_var.set(user_id)
    if username:
        _username_var.set(username)


def clear_request_context() -> None:
    """Clear request context"""
    _request_id_var.set(None)
    _user_id_var.set(None)
    _username_var.set(None)
    _client_ip_var.set(None)
    _request_path_var.set(None)
    _request_method_var.set(None)
    _request_start_time_var.set(None)


# Paths to skip (health checks, etc.)
_SKIP_PATHS = frozenset(
    {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
)


def _extract_request_id_from_scope(scope: dict) -> str:
    """Extract or generate request_id from ASGI scope. Priority: X-Request-ID, X-Trace-ID, then UUID."""
    request_id = _get_header(scope, "X-Request-ID") or _get_header(scope, "X-Trace-ID")
    if not request_id:
        request_id = uuid.uuid4().hex
    return request_id


def _extract_client_ip_from_scope(scope: dict) -> str:
    """Extract client IP from ASGI scope (proxy headers or client)."""
    forwarded_for = _get_header(scope, "X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = _get_header(scope, "X-Real-IP")
    if real_ip:
        return real_ip
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


class RequestContextMiddleware:
    """Request Context Middleware (pure ASGI).

    Generates a unique request_id for each request and injects it into the logging context.
    Supports reading an existing request_id from request headers (for distributed tracing).
    Does not inherit BaseHTTPMiddleware; runs in the same async context to avoid event loop issues.

    Request header priority: X-Request-ID, X-Trace-ID, then auto-generated UUID.
    """

    def __init__(self, app: Any, log_requests: bool = True) -> None:
        """
        Args:
            app: ASGI application (next in chain)
            log_requests: Whether to log requests (default True)
        """
        self.app = app
        self.log_requests = log_requests

    def _should_skip(self, path: str) -> bool:
        clean_path = path.split("?")[0]
        return clean_path in _SKIP_PATHS

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if self._should_skip(path):
            await self.app(scope, receive, send)
            return

        request_id = _extract_request_id_from_scope(scope)
        client_ip = _extract_client_ip_from_scope(scope)
        method = scope.get("method", "")

        _request_id_var.set(request_id)
        _client_ip_var.set(client_ip)
        _request_path_var.set(path)
        _request_method_var.set(method)
        _request_start_time_var.set(time.perf_counter())

        user_info_header = _get_header(scope, "X-User-Info")
        if user_info_header:
            try:
                user_info = json.loads(user_info_header)
                user_id = str(user_info.get("id") or user_info.get("sub", ""))
                username = user_info.get("username")
                if user_id:
                    _user_id_var.set(user_id)
                if username:
                    _username_var.set(username)
            except (ValueError, TypeError):
                pass

        async def send_wrapped(message: dict) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapped)
        finally:
            clear_request_context()


# Export
__all__ = [
    "RequestContextMiddleware",
    "clear_request_context",
    "get_client_ip",
    "get_request_context",
    "get_request_duration_ms",
    "get_request_id",
    "get_request_method",
    "get_request_path",
    "get_user_id",
    "get_username",
    "set_user_context",
]
