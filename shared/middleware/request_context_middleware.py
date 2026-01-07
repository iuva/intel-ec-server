"""请求上下文中间件

为每个请求生成唯一的 request_id，并注入到日志上下文中。
支持从请求头中读取已有的 request_id（用于分布式追踪）。

使用方式：
    from shared.middleware.request_context_middleware import (
        RequestContextMiddleware,
        get_request_id,
        get_request_context,
    )

    # 在 FastAPI 应用中添加中间件
    app.add_middleware(RequestContextMiddleware)

    # 在任何地方获取当前请求 ID
    request_id = get_request_id()

    # 获取完整上下文
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

# 请求上下文变量
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
    """获取当前请求的 request_id

    Returns:
        当前请求的 request_id，如果不在请求上下文中则返回 None
    """
    return _request_id_var.get()


def get_user_id() -> Optional[str]:
    """获取当前请求的 user_id

    Returns:
        当前请求的 user_id，如果未认证则返回 None
    """
    return _user_id_var.get()


def get_username() -> Optional[str]:
    """获取当前请求的 username

    Returns:
        当前请求的 username，如果未认证则返回 None
    """
    return _username_var.get()


def get_client_ip() -> Optional[str]:
    """获取当前请求的客户端 IP

    Returns:
        当前请求的客户端 IP
    """
    return _client_ip_var.get()


def get_request_path() -> Optional[str]:
    """获取当前请求的路径

    Returns:
        当前请求的路径
    """
    return _request_path_var.get()


def get_request_method() -> Optional[str]:
    """获取当前请求的方法

    Returns:
        当前请求的方法
    """
    return _request_method_var.get()


def get_request_duration_ms() -> Optional[float]:
    """获取当前请求的已执行时长（毫秒）

    Returns:
        请求已执行的时长（毫秒），如果不在请求上下文中则返回 None
    """
    start_time = _request_start_time_var.get()
    if start_time is not None:
        return (time.perf_counter() - start_time) * 1000
    return None


def get_request_context() -> Dict[str, Any]:
    """获取当前请求的完整上下文信息

    返回包含 request_id、user_id、username、client_ip 等信息的字典。
    用于在日志中自动添加上下文信息。

    Returns:
        包含请求上下文的字典
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
    """设置用户上下文（通常在认证后调用）

    Args:
        user_id: 用户 ID
        username: 用户名
    """
    if user_id:
        _user_id_var.set(user_id)
    if username:
        _username_var.set(username)


def clear_request_context() -> None:
    """清除请求上下文"""
    _request_id_var.set(None)
    _user_id_var.set(None)
    _username_var.set(None)
    _client_ip_var.set(None)
    _request_path_var.set(None)
    _request_method_var.set(None)
    _request_start_time_var.set(None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件

    为每个请求生成唯一的 request_id，并注入到日志上下文中。
    支持从请求头中读取已有的 request_id（用于分布式追踪）。

    请求头优先级：
    1. X-Request-ID
    2. X-Trace-ID
    3. 自动生成 UUID
    """

    # 需要跳过的路径（健康检查等）
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
        """初始化中间件

        Args:
            app: FastAPI 应用实例
            log_requests: 是否记录请求日志（默认 True）
        """
        super().__init__(app)
        self.log_requests = log_requests

    def _generate_request_id(self) -> str:
        """生成唯一的请求 ID

        Returns:
            32 字符的 UUID（无连字符）
        """
        return uuid.uuid4().hex

    def _extract_request_id(self, request: Request) -> str:
        """从请求中提取或生成 request_id

        优先从请求头中读取：
        1. X-Request-ID
        2. X-Trace-ID
        3. 自动生成

        Args:
            request: FastAPI 请求对象

        Returns:
            request_id 字符串
        """
        # 尝试从请求头获取
        request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-ID")

        if not request_id:
            request_id = self._generate_request_id()

        return request_id

    def _extract_client_ip(self, request: Request) -> str:
        """从请求中提取客户端 IP

        优先从代理头中读取（支持反向代理）。

        Args:
            request: FastAPI 请求对象

        Returns:
            客户端 IP 地址
        """
        # 尝试从代理头获取真实 IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For 可能包含多个 IP，取第一个
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 直接连接的客户端 IP
        if request.client:
            return request.client.host

        return "unknown"

    def _should_skip(self, path: str) -> bool:
        """判断是否应该跳过处理

        Args:
            path: 请求路径

        Returns:
            是否跳过
        """
        clean_path = path.split("?")[0]
        return clean_path in self.SKIP_PATHS

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """处理请求

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # 跳过健康检查等路径
        if self._should_skip(request.url.path):
            return await call_next(request)

        # 设置请求上下文
        request_id = self._extract_request_id(request)
        client_ip = self._extract_client_ip(request)
        method = request.method
        path = request.url.path
        start_time = time.perf_counter()

        # 设置上下文变量
        _request_id_var.set(request_id)
        _client_ip_var.set(client_ip)
        _request_path_var.set(path)
        _request_method_var.set(method)
        _request_start_time_var.set(start_time)

        # 尝试从请求头中获取用户信息（由认证中间件设置）
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
            # 调用下一个处理器
            response = await call_next(request)

            # 在响应头中添加 request_id
            response.headers["X-Request-ID"] = request_id

            return response

        finally:
            # 清除上下文（确保不会泄露到其他请求）
            clear_request_context()


# 导出
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
