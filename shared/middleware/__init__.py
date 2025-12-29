"""
共享中间件模块

提供所有微服务可使用的中间件，包括：
- 异常处理中间件
- 指标收集中间件
- HTTP 请求/响应日志中间件
"""

from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware

__all__ = ["HTTPLoggingMiddleware"]
