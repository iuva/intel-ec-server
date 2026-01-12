"""Request Context Middleware

Generates a unique request_id for each request and injects it into the logging context.
Supports reading an existing request_id from request headers (for distributed tracing).

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
import time
from typing import Any, Dict, Optional
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

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


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request Context Middleware

    Generates a unique request_id for each request and injects it into the logging context.
    Supports reading an existing request_id from request headers (for distributed tracing).

    Request header priority:
    1. X-Request-ID
    2. X-Trace-ID
    3. Auto-generated UUID
    """

    # Paths to skip (health checks, etc.)
    SKIP_PATHS = frozenset(
        {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }
    )

    def __init__(self, app: Any, log_requests: bool = True) -> None:
        """Initialize the middleware

        Args:
            app: FastAPI application instance
            log_requests: Whether to log requests (default True)
        """
        super().__init__(app)
        self.log_requests = log_requests

    def _generate_request_id(self) -> str:
        """Generate a unique request ID

        Returns:
            32-character UUID (without hyphens)
        """
        return uuid.uuid4().hex

    def _extract_request_id(self, request: Request) -> str:
        """Extract or generate request_id from request

        Priority from request headers:
        1. X-Request-ID
        2. X-Trace-ID
        3. Auto-generated

        Args:
            request: FastAPI request object

        Returns:
            request_id string
        """
        # Try to get from request headers
        request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-ID")

        if not request_id:
            request_id = self._generate_request_id()

        return request_id

    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP from request

        Priority from proxy headers (supports reverse proxy).

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Try to get real IP from proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For may contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Directly connected client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _should_skip(self, path: str) -> bool:
        """Determine whether to skip processing

        Args:
            path: Request path

        Returns:
            Whether to skip
        """
        clean_path = path.split("?")[0]
        return clean_path in self.SKIP_PATHS

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process request

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response object
        """
        # Skip health check and other paths
        if self._should_skip(request.url.path):
            return await call_next(request)

        # Set request context
        request_id = self._extract_request_id(request)
        client_ip = self._extract_client_ip(request)
        method = request.method
        path = request.url.path
        start_time = time.perf_counter()

        # Set context variables
        _request_id_var.set(request_id)
        _client_ip_var.set(client_ip)
        _request_path_var.set(path)
        _request_method_var.set(method)
        _request_start_time_var.set(start_time)

        # Try to get user information from request headers (set by authentication middleware)
        user_info_header = request.headers.get("X-User-Info")
        if user_info_header:
            try:
                import json

                user_info = json.loads(user_info_header)
                user_id = str(user_info.get("id") or user_info.get("sub", ""))
                username = user_info.get("username")
                if user_id:
                    _user_id_var.set(user_id)
                if username:
                    _username_var.set(username)
            except (ValueError, TypeError):
                ***REMOVED***

        try:
            # Call the next handler
            response = await call_next(request)

            # Add request_id to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        finally:
            # Clear context (ensure it doesn't leak to other requests)
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
