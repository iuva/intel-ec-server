"""
Prometheus Metrics Collection Middleware
Automatically collect metrics data for HTTP requests
"""

import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from shared.common.loguru_config import get_logger
from shared.monitoring.prometheus_metrics import (
    http_request_duration_seconds,
    http_request_size_bytes,
    http_requests_in_progress,
    http_requests_total,
    http_response_size_bytes,
)

logger = get_logger(__name__)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Prometheus Metrics Collection Middleware

    Automatically collects metrics for all HTTP requests:
    - Total requests
    - Request response time
    - Request/response size
    - In-progress requests count
    """

    def __init__(self, app: Any, service_name: str) -> None:
        """
        Initialize the middleware

        Args:
            app: FastAPI application instance
            service_name: Service name
        """
        super().__init__(app)
        self.service_name = service_name
        logger.info(f"✅ PrometheusMetricsMiddleware initialized: service_name={self.service_name}")

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """
        Process request and collect metrics

        Args:
            request: HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        # Skip /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Increase in-progress requests count
        try:
            http_requests_in_progress.labels(method=method, endpoint=endpoint, service=self.service_name).inc()
            logger.debug(f"Incremented http_requests_in_progress for {method} {endpoint}")
        except Exception as e:
            logger.error(f"❌ Failed to increment http_requests_in_progress: {e!s}")

        # Record request size
        request_size = int(request.headers.get("content-length", 0))
        if request_size > 0:
            http_request_size_bytes.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                request_size
            )
            logger.debug(f"Observed request size {request_size} for {method} {endpoint}")

        # Record start time
        start_time = time.time()
        logger.debug(f"Start time recorded for {method} {endpoint}")

        try:
            # Process request
            response = await call_next(request)
            logger.debug(f"Request processed for {method} {endpoint}")

            # Record response time
            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                duration
            )
            logger.debug(f"Observed duration {duration} for {method} {endpoint}")

            # Record total requests
            status = response.status_code
            try:
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status,
                    service=self.service_name,
                ).inc()
                logger.debug(f"Incremented http_requests_total for {method} {endpoint} with status {status}")
            except Exception as e:
                logger.error(f"❌ Failed to increment http_requests_total: {e!s}")

            # Record response size
            response_size = int(response.headers.get("content-length", 0))
            if response_size > 0:
                http_response_size_bytes.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                    response_size
                )
                logger.debug(f"Observed response size {response_size} for {method} {endpoint}")

            return response

        except Exception:
            # Record exception request
            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                duration
            )
            logger.info(f"Observed duration {duration} for {method} {endpoint} (exception)")

            http_requests_total.labels(method=method, endpoint=endpoint, status=500, service=self.service_name).inc()
            logger.info(f"Incremented http_requests_total for {method} {endpoint} with status 500 (exception)")

            raise

        finally:
            # Decrease in-progress requests count
            http_requests_in_progress.labels(method=method, endpoint=endpoint, service=self.service_name).dec()
            logger.debug(f"Decremented http_requests_in_progress for {method} {endpoint}")
