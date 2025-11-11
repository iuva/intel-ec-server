"""
Prometheus 指标收集中间件
自动收集 HTTP 请求的指标数据
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
    Prometheus 指标收集中间件

    自动收集所有 HTTP 请求的指标：
    - 请求总数
    - 请求响应时间
    - 请求/响应大小
    - 进行中的请求数
    """

    def __init__(self, app: Any, service_name: str) -> None:
        """
        初始化中间件

        Args:
            app: FastAPI 应用实例
            service_name: 服务名称
        """
        super().__init__(app)
        self.service_name = service_name
        logger.info(f"✅ PrometheusMetricsMiddleware 已初始化: service_name={self.service_name}")

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """
        处理请求并收集指标

        Args:
            request: HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            HTTP 响应
        """
        # 跳过 /metrics 端点本身
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # 增加进行中的请求数
        try:
            http_requests_in_progress.labels(method=method, endpoint=endpoint, service=self.service_name).inc()
            logger.debug(f"Incremented http_requests_in_progress for {method} {endpoint}")
        except Exception as e:
            logger.error(f"❌ 增加 http_requests_in_progress 失败: {e!s}")

        # 记录请求大小
        request_size = int(request.headers.get("content-length", 0))
        if request_size > 0:
            http_request_size_bytes.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                request_size
            )
            logger.debug(f"Observed request size {request_size} for {method} {endpoint}")

        # 记录开始时间
        start_time = time.time()
        logger.debug(f"Start time recorded for {method} {endpoint}")

        try:
            # 处理请求
            response = await call_next(request)
            logger.debug(f"Request processed for {method} {endpoint}")

            # 记录响应时间
            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                duration
            )
            logger.debug(f"Observed duration {duration} for {method} {endpoint}")

            # 记录请求总数
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
                logger.error(f"❌ 增加 http_requests_total 失败: {e!s}")

            # 记录响应大小
            response_size = int(response.headers.get("content-length", 0))
            if response_size > 0:
                http_response_size_bytes.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                    response_size
                )
                logger.debug(f"Observed response size {response_size} for {method} {endpoint}")

            return response

        except Exception:
            # 记录异常请求
            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint, service=self.service_name).observe(
                duration
            )
            logger.info(f"Observed duration {duration} for {method} {endpoint} (exception)")

            http_requests_total.labels(method=method, endpoint=endpoint, status=500, service=self.service_name).inc()
            logger.info(f"Incremented http_requests_total for {method} {endpoint} with status 500 (exception)")

            raise

        finally:
            # 减少进行中的请求数
            http_requests_in_progress.labels(method=method, endpoint=endpoint, service=self.service_name).dec()
            logger.debug(f"Decremented http_requests_in_progress for {method} {endpoint}")
