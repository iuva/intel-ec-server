"""
Shared Middleware Module

Provides middleware available for all microservices, including:
- Exception handling middleware
- Metrics collection middleware
- HTTP request/response logging middleware
- Request context middleware
"""

from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware
from shared.middleware.request_context_middleware import (
    RequestContextMiddleware,
    clear_request_context,
    get_client_ip,
    get_request_context,
    get_request_duration_ms,
    get_request_id,
    get_request_method,
    get_request_path,
    get_user_id,
    get_username,
    set_user_context,
)

__all__ = [
    # HTTP logging middleware
    "HTTPLoggingMiddleware",
    # Request context middleware
    "RequestContextMiddleware",
    "get_request_id",
    "get_user_id",
    "get_username",
    "get_client_ip",
    "get_request_path",
    "get_request_method",
    "get_request_duration_ms",
    "get_request_context",
    "set_user_context",
    "clear_request_context",
]
