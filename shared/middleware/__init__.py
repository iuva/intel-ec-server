"""
共享中间件模块

提供所有微服务可使用的中间件，包括：
- 异常处理中间件
- 指标收集中间件
- HTTP 请求/响应日志中间件
- 请求上下文中间件
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
    # HTTP 日志中间件
    "HTTPLoggingMiddleware",
    # 请求上下文中间件
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
