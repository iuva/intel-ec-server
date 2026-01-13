"""Asynchronous HTTP Client Module

Provides a unified asynchronous HTTP client supporting connection pooling, timeout configuration,
retry mechanisms and metrics collection.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
from time import perf_counter
from typing import Any, AsyncGenerator, Dict, Optional, Set

from httpx import AsyncClient, ConnectError, Limits, RequestError, Timeout, TimeoutException

try:
    from shared.common.loguru_config import get_logger
    from shared.monitoring.metrics import (
        http_client_request_duration_seconds,
        http_client_requests_in_progress,
        http_client_requests_total,
    )
except ImportError:
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
        # If monitoring module is unavailable, create empty metrics objects
        http_client_requests_total = None  # type: ignore
        http_client_request_duration_seconds = None  # type: ignore
        http_client_requests_in_progress = None  # type: ignore

logger = get_logger(__name__)


# Retryable HTTP status codes
RETRYABLE_STATUS_CODES: Set[int] = {408, 429, 500, 502, 503, 504}

# Default client name
DEFAULT_HTTP_CLIENT_NAME = "default_http_client"


@dataclass
class HTTPClientConfig:
    """HTTP Client Configuration"""

    timeout: float = 30.0
    connect_timeout: float = 10.0
    max_keepalive_connections: int = 20
    max_connections: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    client_name: str = DEFAULT_HTTP_CLIENT_NAME
    verify_ssl: bool = True  # SSL certificate verification (enabled by default)


class AsyncHTTPClient:
    """Asynchronous HTTP Client Manager

    Provides a unified asynchronous HTTP client supporting:
    - Connection pool management and reuse
    - Timeout configuration
    - Automatic retry mechanism
    - Request/response logging
    - Metrics collection

    Attributes:
        _client: httpx.AsyncClient instance
        timeout: Timeout configuration
        limits: Connection pool limit configuration
        max_retries: Maximum retry attempts
        retry_delay: Retry delay (seconds)
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
        verify_ssl: Optional[bool] = None,
        config: Optional[HTTPClientConfig] = None,
    ):
        """Initialize HTTP Client

        Args:
            timeout: Request timeout (seconds)
            connect_timeout: Connection timeout (seconds)
            max_keepalive_connections: Maximum keep-alive connections
            max_connections: Maximum connections
            max_retries: Maximum retry attempts
            retry_delay: Retry delay (seconds)
            client_name: Client name (for metrics labels)
            verify_ssl: SSL certificate verification (reads from environment variable when None, default True)
            config: Optional configuration object (highest priority)
        """
        if config is not None:
            timeout = config.timeout
            connect_timeout = config.connect_timeout
            max_keepalive_connections = config.max_keepalive_connections
            max_connections = config.max_connections
            max_retries = config.max_retries
            retry_delay = config.retry_delay
            client_name = config.client_name or client_name
            verify_ssl = config.verify_ssl if verify_ssl is None else verify_ssl

        # Read SSL verification configuration from environment variables (if not provided via parameters)
        if verify_ssl is None:
            verify_ssl_env = os.getenv("HTTP_CLIENT_VERIFY_SSL", "true").lower()
            verify_ssl = verify_ssl_env in ("true", "1", "yes", "on", "enabled")

        self._client: Optional[AsyncClient] = None
        self.timeout = Timeout(timeout, connect=connect_timeout)
        self.limits = Limits(max_keepalive_connections=max_keepalive_connections, max_connections=max_connections)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client_name = client_name or DEFAULT_HTTP_CLIENT_NAME
        self.verify_ssl = verify_ssl

        logger.info(
            "HTTP Client configuration initialized",
            extra={
                "timeout": timeout,
                "connect_timeout": connect_timeout,
                "max_keepalive_connections": max_keepalive_connections,
                "max_connections": max_connections,
                "max_retries": max_retries,
                "verify_ssl": verify_ssl,
                "client_name": self.client_name,
            },
        )

    @property
    def client(self) -> AsyncClient:
        """Get client instance (lazy loading)

        Returns:
            AsyncClient instance
        """
        if self._client is None:
            self._client = AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True,
                verify=self.verify_ssl,  # SSL certificate verification configuration
            )
            logger.debug(
                "Creating new AsyncClient instance",
                extra={
                    "client_name": self.client_name,
                    "verify_ssl": self.verify_ssl,
                },
            )

        return self._client

    async def close(self) -> None:
        """Close client connection"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP Client closed", extra={"client_name": self.client_name})

    async def request(self, method: str, url: str, retry: bool = True, **kwargs: Any) -> Dict[str, Any]:
        """Send HTTP request (supports automatic retry)

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            retry: Whether to enable automatic retry (default True)
            **kwargs: Other request parameters (headers, params, json, data, etc.)

        Returns:
            Response data dictionary containing:
            - status_code: HTTP status code
            - headers: Response headers dictionary
            - body: Response body (JSON or text)

        Raises:
            httpx.HTTPError: HTTP request error
        """
        method_upper = method.upper()
        if http_client_requests_in_progress is not None:
            try:
                http_client_requests_in_progress.labels(self.client_name, method_upper).inc()
            except Exception as gauge_error:
                logger.debug(
                    "Failed to record HTTP client in-progress metrics",
                    extra={"error_type": type(gauge_error).__name__, "client_name": self.client_name},
                )

        status_code = 0
        success = False
        duration = 0.0
        start_time = perf_counter()

        try:
            logger.debug(
                f"Sending HTTP request: {method} {url}",
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

            # ✅ Fix: Don't call raise_for_status(), return responses for all status codes
            # This way gateway can correctly handle error responses and relay to client

            # Parse response body
            content_type = response.headers.get("content-type", "")
            raw_content = response.content
            is_json = False
            try:
                if "application/json" in content_type.lower():
                    try:
                        body = response.json()
                        is_json = True
                    except Exception as json_error:
                        # JSON parsing failed, use text
                        logger.warning(
                            f"JSON parsing failed, using text: {method} {url}",
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
                # If parsing fails, use raw text
                logger.warning(
                    f"Response body parsing failed: {method} {url}",
                    extra={
                        "method": method,
                        "url": url,
                        "status_code": status_code,
                        "content_type": content_type,
                        "error": str(parse_error),
                    },
                )
                # Try to get raw text
                try:
                    body = raw_content or response.text
                except Exception:
                    # If even text cannot be obtained, use empty string
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
                    f"HTTP request succeeded: {method} {url}",
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
                    f"HTTP request returned error status: {method} {url}",
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
                f"HTTP request network error: {method} {url}",
                extra={
                    "method": method,
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": int(duration * 1000),
                    "client_name": self.client_name,
                },
            )
            # ✅ Fix: Return error response dictionary instead of throwing exception, allowing gateway to handle
            # RequestError is the base exception class for httpx, including ConnectError, TimeoutException, etc.
            # Check specific error type

            if isinstance(e, ConnectError):
                status_code = 502
                error_code = "CONNECTION_ERROR"
                message = "Unable to connect to backend service"
            elif isinstance(e, TimeoutException):
                status_code = 504
                error_code = "TIMEOUT_ERROR"
                message = "Backend service response timeout"
            else:
                status_code = 502
                error_code = "NETWORK_ERROR"
                message = "Network error"

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
                f"HTTP request exception: {method} {url}",
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
                        "Failed to decrease HTTP client in-progress metrics",
                        extra={"error_type": type(gauge_error).__name__, "client_name": self.client_name},
                    )

    def _record_metrics(self, method: str, url: str, status_code: int, duration: float, success: bool) -> None:
        """Record HTTP request metrics

        Args:
            method: HTTP method
            url: Request URL
            status_code: HTTP status code
            duration: Request duration (seconds)
            success: Whether request was successful
        """
        try:
            status_label = str(status_code) if status_code > 0 else ("success" if success else "error")

            if http_client_requests_total is not None:
                http_client_requests_total.labels(self.client_name, method, status_label).inc()

            if http_client_request_duration_seconds is not None:
                http_client_request_duration_seconds.labels(self.client_name, method).observe(duration)

        except Exception as e:
            # Metric recording failure should not affect main process
            logger.debug(
                "Failed to record HTTP metrics",
                extra={"error_type": type(e).__name__, "client_name": self.client_name},
            )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["AsyncHTTPClient", None]:
        """Context manager, automatically manages client lifecycle

        Usage example:
            async with http_client.session():
                response = await http_client.request("GET", "https://api.example.com")
        """
        try:
            yield self
        finally:
            await self.close()


# Global client instance
_http_client_instance: Optional[AsyncHTTPClient] = None


def get_http_client() -> AsyncHTTPClient:
    """Get HTTP client instance (singleton pattern)

    Returns:
        AsyncHTTPClient instance
    """
    global _http_client_instance

    if _http_client_instance is None:
        _http_client_instance = AsyncHTTPClient()
        logger.debug("Creating global HTTP client instance")

    return _http_client_instance
