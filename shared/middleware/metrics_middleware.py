"""
Prometheus Metrics Collection Middleware
Automatically collect metrics data for HTTP requests.

Uses pure ASGI (no BaseHTTPMiddleware) so all code runs in the same async context
and avoids "no current event loop in thread" in worker threads (e.g. AnyIO).
"""

import time
from typing import Any, Callable

from shared.common.loguru_config import get_logger
from shared.monitoring.prometheus_metrics import (
    http_request_duration_seconds,
    http_request_size_bytes,
    http_requests_in_progress,
    http_requests_total,
    http_response_size_bytes,
)

logger = get_logger(__name__)


def _get_header(scope: dict, name: str) -> str:
    """Get header value from ASGI scope (case-insensitive). Default ''."""
    name_lower = name.lower().encode("utf-8")
    for k, v in scope.get("headers", []):
        if k.lower() == name_lower:
            return v.decode("utf-8", errors="replace")
    return ""


class PrometheusMetricsMiddleware:
    """
    Prometheus Metrics Collection Middleware (pure ASGI).

    Automatically collects metrics for all HTTP requests.
    Does not inherit BaseHTTPMiddleware; runs in the same async context to avoid event loop issues.
    """

    def __init__(self, app: Any, service_name: str) -> None:
        """
        Args:
            app: ASGI application (next in chain)
            service_name: Service name for metric labels
        """
        self.app = app
        self.service_name = service_name
        logger.info(f"✅ PrometheusMetricsMiddleware initialized: service_name={self.service_name}")

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        endpoint = path

        try:
            http_requests_in_progress.labels(
                method=method, endpoint=endpoint, service=self.service_name
            ).inc()
        except Exception as e:
            logger.error(f"❌ Failed to increment http_requests_in_progress: {e!s}")

        request_size = 0
        try:
            cl = _get_header(scope, "content-length")
            if cl:
                request_size = int(cl)
        except ValueError:
            pass
        if request_size > 0:
            try:
                http_request_size_bytes.labels(
                    method=method, endpoint=endpoint, service=self.service_name
                ).observe(request_size)
            except Exception as e:
                logger.error(f"❌ Failed to observe request size: {e!s}")

        start_time = time.time()
        response_status: int = 500
        response_content_length: int = 0

        async def send_wrapped(message: dict) -> None:
            nonlocal response_status, response_content_length
            if message.get("type") == "http.response.start":
                response_status = message.get("status", 500)
                for k, v in message.get("headers", []):
                    if k.lower() == b"content-length":
                        try:
                            response_content_length = int(v.decode("utf-8", errors="replace"))
                        except ValueError:
                            pass
                        break
            await send(message)

        try:
            await self.app(scope, receive, send_wrapped)
            duration = time.time() - start_time
            try:
                http_request_duration_seconds.labels(
                    method=method, endpoint=endpoint, service=self.service_name
                ).observe(duration)
            except Exception as e:
                logger.error(f"❌ Failed to observe duration: {e!s}")
            try:
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=response_status,
                    service=self.service_name,
                ).inc()
            except Exception as e:
                logger.error(f"❌ Failed to increment http_requests_total: {e!s}")
            if response_content_length > 0:
                try:
                    http_response_size_bytes.labels(
                        method=method, endpoint=endpoint, service=self.service_name
                    ).observe(response_content_length)
                except Exception as e:
                    logger.error(f"❌ Failed to observe response size: {e!s}")
        except Exception:
            duration = time.time() - start_time
            try:
                http_request_duration_seconds.labels(
                    method=method, endpoint=endpoint, service=self.service_name
                ).observe(duration)
            except Exception as e:
                logger.error(f"❌ Failed to observe duration (exception): {e!s}")
            try:
                http_requests_total.labels(
                    method=method, endpoint=endpoint, status=500, service=self.service_name
                ).inc()
            except Exception as e:
                logger.error(f"❌ Failed to increment http_requests_total (exception): {e!s}")
            raise
        finally:
            try:
                http_requests_in_progress.labels(
                    method=method, endpoint=endpoint, service=self.service_name
                ).dec()
            except Exception as e:
                logger.error(f"❌ Failed to decrement http_requests_in_progress: {e!s}")
