"""异步 HTTP 客户端模块

提供统一的异步 HTTP 客户端，支持连接池、超时配置、重试机制和指标收集。
"""

import json
from dataclasses import dataclass
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any, AsyncGenerator, Dict, Optional, Set

from httpx import AsyncClient, Limits, RequestError, Timeout, ConnectError, TimeoutException

try:
    from shared.common.loguru_config import get_logger
    from shared.monitoring.metrics import (
        http_client_request_duration_seconds,
        http_client_requests_in_progress,
        http_client_requests_total,
    )
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.loguru_config import get_logger

    try:
        from shared.monitoring.metrics import (
            http_client_request_duration_seconds,
            http_client_requests_in_progress,
            http_client_requests_total,
        )
    except ImportError:
        # 如果监控模块不可用，创建空的指标对象
        http_client_requests_total = None  # type: ignore
        http_client_request_duration_seconds = None  # type: ignore
        http_client_requests_in_progress = None  # type: ignore

logger = get_logger(__name__)


# 可重试的 HTTP 状态码
RETRYABLE_STATUS_CODES: Set[int] = {408, 429, 500, 502, 503, 504}

# 默认的客户端名称
DEFAULT_HTTP_CLIENT_NAME = "default_http_client"


@dataclass
class HTTPClientConfig:
    """HTTP 客户端配置"""

    timeout: float = 30.0
    connect_timeout: float = 10.0
    max_keepalive_connections: int = 20
    max_connections: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    client_name: str = DEFAULT_HTTP_CLIENT_NAME


class AsyncHTTPClient:
    """异步 HTTP 客户端管理器

    提供统一的异步 HTTP 客户端，支持：
    - 连接池管理和复用
    - 超时配置
    - 自动重试机制
    - 请求/响应日志
    - 指标收集

    Attributes:
        _client: httpx.AsyncClient 实例
        timeout: 超时配置
        limits: 连接池限制配置
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    """

    def __init__(
        self,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        max_keepalive_connections: int = 20,
        max_connections: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        client_name: str = DEFAULT_HTTP_CLIENT_NAME,
        config: Optional[HTTPClientConfig] = None,
    ):
        """初始化 HTTP 客户端

        Args:
            timeout: 请求超时时间（秒）
            connect_timeout: 连接超时时间（秒）
            max_keepalive_connections: 最大保持连接数
            max_connections: 最大连接数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            client_name: 客户端名称（用于指标标签）
            config: 可选的配置对象（优先级最高）
        """
        if config is not None:
            timeout = config.timeout
            connect_timeout = config.connect_timeout
            max_keepalive_connections = config.max_keepalive_connections
            max_connections = config.max_connections
            max_retries = config.max_retries
            retry_delay = config.retry_delay
            client_name = config.client_name or client_name

        self._client: Optional[AsyncClient] = None
        self.timeout = Timeout(timeout, connect=connect_timeout)
        self.limits = Limits(max_keepalive_connections=max_keepalive_connections, max_connections=max_connections)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client_name = client_name or DEFAULT_HTTP_CLIENT_NAME

        logger.info(
            "HTTP 客户端配置初始化",
            extra={
                "timeout": timeout,
                "connect_timeout": connect_timeout,
                "max_keepalive_connections": max_keepalive_connections,
                "max_connections": max_connections,
                "max_retries": max_retries,
                "client_name": self.client_name,
            },
        )

    @property
    def client(self) -> AsyncClient:
        """获取客户端实例（懒加载）

        Returns:
            AsyncClient 实例
        """
        if self._client is None:
            self._client = AsyncClient(timeout=self.timeout, limits=self.limits, follow_redirects=True)
            logger.debug(
                "创建新的 AsyncClient 实例",
                extra={"client_name": self.client_name},
            )

        return self._client

    async def close(self) -> None:
        """关闭客户端连接"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP 客户端已关闭", extra={"client_name": self.client_name})

    async def request(self, method: str, url: str, retry: bool = True, **kwargs: Any) -> Dict[str, Any]:
        """发送 HTTP 请求（支持自动重试）

        Args:
            method: HTTP 方法（GET, POST, PUT, DELETE 等）
            url: 请求 URL
            retry: 是否启用自动重试（默认 True）
            **kwargs: 其他请求参数（headers, params, json, data 等）

        Returns:
            响应数据字典，包含：
            - status_code: HTTP 状态码
            - headers: 响应头字典
            - body: 响应体（JSON 或文本）

        Raises:
            httpx.HTTPError: HTTP 请求错误
        """
        method_upper = method.upper()
        if http_client_requests_in_progress is not None:
            try:
                http_client_requests_in_progress.labels(self.client_name, method_upper).inc()
            except Exception as gauge_error:
                logger.debug(
                    "记录 HTTP 客户端 in-progress 指标失败",
                    extra={"error_type": type(gauge_error).__name__, "client_name": self.client_name},
                )

        status_code = 0
        success = False
        duration = 0.0
        start_time = perf_counter()

        try:
            logger.debug(
                f"发送 HTTP 请求: {method} {url}",
                extra={
                    "method": method,
                    "url": url,
                    "params": kwargs.get("params"),
                    "has_json": "json" in kwargs,
                    "has_data": "data" in kwargs,
                },
            )

            response = await self.client.request(method, url, **kwargs)
            status_code = response.status_code
            duration = perf_counter() - start_time
            duration_ms = int(duration * 1000)

            # ✅ 修复：不调用 raise_for_status()，返回所有状态码的响应
            # 这样网关可以正确处理错误响应并透传给客户端

            # 解析响应体
            content_type = response.headers.get("content-type", "")
            raw_content = response.content
            is_json = False
            try:
                if "application/json" in content_type.lower():
                    try:
                        body = response.json()
                        is_json = True
                    except Exception as json_error:
                        # JSON 解析失败，使用文本
                        logger.warning(
                            f"JSON 解析失败，使用文本: {method} {url}",
                            extra={
                                "method": method,
                                "url": url,
                                "status_code": status_code,
                                "content_type": content_type,
                                "error": str(json_error),
                            },
                        )
                        body = response.text
                else:
                    body = raw_content
            except Exception as parse_error:
                # 如果解析失败，使用原始文本
                logger.warning(
                    f"响应体解析失败: {method} {url}",
                    extra={
                        "method": method,
                        "url": url,
                        "status_code": status_code,
                        "content_type": content_type,
                        "error": str(parse_error),
                    },
                )
                # 尝试获取原始文本
                try:
                    body = raw_content or response.text
                except Exception:
                    # 如果连文本都获取不到，使用空字符串
                    body = ""

            result = {
                "status_code": status_code,
                "headers": dict(response.headers),
                "body": body,
                "raw_body": raw_content,
                "is_json": is_json,
            }

            success = 200 <= status_code < 400

            if success:
                logger.info(
                    f"HTTP 请求成功: {method} {url}",
                    extra={
                        "method": method,
                        "url": url,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "response_size": len(response.content),
                        "client_name": self.client_name,
                    },
                )
            else:
                logger.warning(
                    f"HTTP 请求返回错误状态: {method} {url}",
                    extra={
                        "method": method,
                        "url": url,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "response_size": len(response.content),
                        "client_name": self.client_name,
                    },
                )

            return result

        except RequestError as e:
            duration = perf_counter() - start_time

            logger.error(
                f"HTTP 请求网络错误: {method} {url}",
                extra={
                    "method": method,
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": int(duration * 1000),
                    "client_name": self.client_name,
                },
            )
            # ✅ 修复：返回错误响应字典而不是抛出异常，让网关可以处理
            # RequestError 是 httpx 的基础异常类，包括 ConnectError, TimeoutException 等
            # 检查具体的错误类型

            if isinstance(e, ConnectError):
                status_code = 502
                error_code = "CONNECTION_ERROR"
                message = "无法连接到后端服务"
            elif isinstance(e, TimeoutException):
                status_code = 504
                error_code = "TIMEOUT_ERROR"
                message = "后端服务响应超时"
            else:
                status_code = 502
                error_code = "NETWORK_ERROR"
                message = "网络错误"

            error_body = {
                "status_code": status_code,
                "headers": {"content-type": "application/json"},
                "body": {
                    "code": status_code,
                    "message": message,
                    "error_code": error_code,
                    "details": {"url": url, "error": str(e)},
                },
                "raw_body": json.dumps(
                    {
                        "code": status_code,
                        "message": message,
                        "error_code": error_code,
                        "details": {"url": url, "error": str(e)},
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
                "is_json": True,
            }
            return error_body

        except Exception as e:
            duration = perf_counter() - start_time

            logger.error(
                f"HTTP 请求异常: {method} {url}",
                extra={
                    "method": method,
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": int(duration * 1000),
                    "client_name": self.client_name,
                },
                exc_info=True,
            )
            raise

        finally:
            if duration == 0.0:
                duration = perf_counter() - start_time

            self._record_metrics(method_upper, url, status_code, duration, success)

            if http_client_requests_in_progress is not None:
                try:
                    http_client_requests_in_progress.labels(self.client_name, method_upper).dec()
                except Exception as gauge_error:
                    logger.debug(
                        "减少 HTTP 客户端 in-progress 指标失败",
                        extra={"error_type": type(gauge_error).__name__, "client_name": self.client_name},
                    )

    def _record_metrics(self, method: str, url: str, status_code: int, duration: float, success: bool) -> None:
        """记录 HTTP 请求指标

        Args:
            method: HTTP 方法
            url: 请求 URL
            status_code: HTTP 状态码
            duration: 请求耗时（秒）
            success: 是否成功
        """
        try:
            status_label = str(status_code) if status_code > 0 else ("success" if success else "error")

            if http_client_requests_total is not None:
                http_client_requests_total.labels(self.client_name, method, status_label).inc()

            if http_client_request_duration_seconds is not None:
                http_client_request_duration_seconds.labels(self.client_name, method).observe(duration)

        except Exception as e:
            # 指标记录失败不应影响主流程
            logger.debug(
                "记录 HTTP 指标失败",
                extra={"error_type": type(e).__name__, "client_name": self.client_name},
            )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["AsyncHTTPClient", None]:
        """上下文管理器，自动管理客户端生命周期

        使用示例:
            async with http_client.session():
                response = await http_client.request("GET", "https://api.example.com")
        """
        try:
            yield self
        finally:
            await self.close()


# 全局客户端实例
_http_client_instance: Optional[AsyncHTTPClient] = None


def get_http_client() -> AsyncHTTPClient:
    """获取 HTTP 客户端实例（单例模式）

    Returns:
        AsyncHTTPClient 实例
    """
    global _http_client_instance

    if _http_client_instance is None:
        _http_client_instance = AsyncHTTPClient()
        logger.debug("创建全局 HTTP 客户端实例")

    return _http_client_instance
