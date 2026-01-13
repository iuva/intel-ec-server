"""
Monitoring Metrics Collection Module

Provides monitoring metrics collection based on Prometheus
"""

import logging
import time
from typing import Any, Callable, Optional

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    PlatformCollector,
    ProcessCollector,
    generate_latest,
)

from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware

logger = logging.getLogger(__name__)

# Create default registry
registry = CollectorRegistry()

# ==================== HTTP Request Metrics ====================

# HTTP Request Total Count
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status", "service"],
    registry=registry,
)

# HTTP Request Response Time
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "service"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
    registry=registry,
)

# HTTP Request Size
http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint", "service"],
    registry=registry,
)

# HTTP Response Size
http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint", "service"],
    registry=registry,
)

# In-Progress HTTP Request Count
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint", "service"],
    registry=registry,
)

# ==================== Outbound HTTP Client Metrics ====================

http_client_requests_total = Counter(
    "http_client_requests_total",
    "Total number of outbound HTTP requests",
    ["client", "method", "status"],
    registry=registry,
)

http_client_request_duration_seconds = Histogram(
    "http_client_request_duration_seconds",
    "Outbound HTTP request duration in seconds",
    ["client", "method"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
    registry=registry,
)

http_client_requests_in_progress = Gauge(
    "http_client_requests_in_progress",
    "Number of outbound HTTP requests currently being processed",
    ["client", "method"],
    registry=registry,
)

# ==================== Database Metrics ====================

# Database Query Total Count
db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["operation", "table"],
    registry=registry,
)

# Database Query Response Time
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry,
)

# Database Connection Pool
db_connections_active = Gauge("db_connections_active", "Number of active database connections", registry=registry)

db_connections_idle = Gauge("db_connections_idle", "Number of idle database connections", registry=registry)

# Slow Query Counter
db_slow_queries_total = Counter(
    "db_slow_queries_total",
    "Total number of slow database queries",
    ["operation", "table", "service", "sql_hash"],
    registry=registry,
)

# Slow Query Response Time Histogram
db_slow_query_duration_seconds = Histogram(
    "db_slow_query_duration_seconds",
    "Slow database query duration in seconds",
    ["operation", "table", "service", "sql_hash"],
    buckets=(2.0, 3.0, 5.0, 10.0, 15.0, 30.0, 60.0),
    registry=registry,
)

# ==================== Cache Metrics ====================

# Cache Operation Total Count
cache_operations_total = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "status"],
    registry=registry,
)

# Cache Hit Rate
cache_hits_total = Counter("cache_hits_total", "Total number of cache hits", registry=registry)

cache_misses_total = Counter("cache_misses_total", "Total number of cache misses", registry=registry)

# Cache Operation Response Time
cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation duration in seconds",
    ["operation"],
    registry=registry,
)

# ==================== Business Metrics ====================

# Active Users Count
active_users = Gauge("active_users", "Number of active users", registry=registry)

# Active Connections Count
active_connections = Gauge("active_connections", "Number of active connections", ["service"], registry=registry)

# Business Operation Total Count
business_operations_total = Counter(
    "business_operations_total",
    "Total number of business operations",
    ["operation", "status", "service"],
    registry=registry,
)

# Business operation response time
business_operation_duration_seconds = Histogram(
    "business_operation_duration_seconds",
    "Business operation duration in seconds",
    ["operation", "service"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

# Number of business operations in progress
business_operations_in_progress = Gauge(
    "business_operations_in_progress",
    "Number of business operations currently in progress",
    ["operation", "service"],
    registry=registry,
)

# Total number of user sessions
user_sessions_total = Counter(
    "user_sessions_total",
    "Total number of user sessions",
    ["action", "service"],
    registry=registry,
)

# Total number of authentication operations
auth_operations_total = Counter(
    "auth_operations_total",
    "Total number of authentication operations",
    ["operation", "status", "service"],
    registry=registry,
)

# Total number of validation errors
validation_errors_total = Counter(
    "validation_errors_total",
    "Total number of validation errors",
    ["field", "error_type", "service"],
    registry=registry,
)

# ==================== System Metrics ====================

# Service information
service_info = Info("service", "Service information", registry=registry)

# Service start time
service_start_time = Gauge(
    "service_start_time_seconds",
    "Service start time in unix timestamp",
    registry=registry,
)


class MetricsCollector:
    """Metrics Collector

    Provides convenient methods for metrics collection
    """

    def __init__(self, service_name: str = "unknown") -> None:
        """Initialize metrics collector

        Args:
            service_name: Service name, used to identify metrics source
        """
        self.start_time = time.time()
        self.service_name = service_name
        service_start_time.set(self.start_time)

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        service: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ) -> None:
        """Record HTTP request metrics

        Args:
            method: HTTP method
            endpoint: Request endpoint
            status: Response status code
            duration: Request duration (seconds)
            service: Service name (optional, defaults to service name used during initialization)
            request_size: Request size (bytes)
            response_size: Response size (bytes)
        """
        service_label = service or self.service_name

        # Record request total count
        http_requests_total.labels(method=method, endpoint=endpoint, status=str(status), service=service_label).inc()

        # Record response time
        http_request_duration_seconds.labels(method=method, endpoint=endpoint, service=service_label).observe(duration)

        # Record request size
        if request_size is not None:
            http_request_size_bytes.labels(method=method, endpoint=endpoint, service=service_label).observe(
                request_size
            )

        # Record response size
        if response_size is not None:
            http_response_size_bytes.labels(method=method, endpoint=endpoint, service=service_label).observe(
                response_size
            )

    def record_db_query(self, operation: str, table: str, duration: float) -> None:
        """Record database query metrics

        Args:
            operation: Operation type (select, insert, update, delete)
            table: Table name
            duration: Query duration (seconds)
        """
        db_queries_total.labels(operation=operation, table=table).inc()

        db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

    def record_cache_operation(
        self,
        operation: str,
        hit: Optional[bool] = None,
        duration: Optional[float] = None,
    ) -> None:
        """Record cache operation metrics

        Args:
            operation: Operation type (get, set, delete)
            hit: Whether hit (only for get operations)
            duration: Operation duration (seconds)
        """
        # Record operation total count
        status = "success"
        cache_operations_total.labels(operation=operation, status=status).inc()

        # Record hit rate
        if hit is not None:
            if hit:
                cache_hits_total.inc()
            else:
                cache_misses_total.inc()

        # Record operation duration
        if duration is not None:
            cache_operation_duration_seconds.labels(operation=operation).observe(duration)

    def record_business_operation(
        self,
        operation: str,
        status: str = "success",
        service: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> None:
        """Record business operation metrics

        Args:
            operation: Operation name
            status: Operation status (success, failed)
            service: Service name (optional, defaults to service name used during initialization)
            duration: Operation duration (seconds, optional)
        """
        service_label = service or self.service_name

        # Record operation total count
        business_operations_total.labels(operation=operation, status=status, service=service_label).inc()

        # Record operation duration
        if duration is not None:
            business_operation_duration_seconds.labels(operation=operation, service=service_label).observe(duration)

    def set_active_users(self, count: int) -> None:
        """Set active user count

        Args:
            count: Number of users
        """
        active_users.set(count)

    def set_active_connections(self, count: int, service: Optional[str] = None) -> None:
        """Set active connection count

        Args:
            count: Number of connections
            service: Service name (optional, defaults to service name used during initialization)
        """
        service_label = service or self.service_name
        active_connections.labels(service=service_label).set(count)

    def set_db_connections(self, active: int, idle: int) -> None:
        """Set database connection pool status

        Args:
            active: Active connection count
            idle: Idle connection count
        """
        db_connections_active.set(active)
        db_connections_idle.set(idle)

    def set_service_info(self, name: str, version: str, environment: str) -> None:
        """Set service information

        Args:
            name: Service name
            version: Service version
            environment: Runtime environment
        """
        self.service_name = name
        service_info.info({"name": name, "version": version, "environment": environment})

    def record_user_session(self, action: str, service: Optional[str] = None) -> None:
        """Record user session operation

        Args:
            action: Session operation (login, logout, refresh, expire)
            service: Service name (optional, defaults to service name used during initialization)
        """
        service_label = service or self.service_name
        user_sessions_total.labels(action=action, service=service_label).inc()

    def record_auth_operation(self, operation: str, status: str, service: Optional[str] = None) -> None:
        """Record authentication operation

        Args:
            operation: Authentication operation type (login, token_verify, token_refresh, oauth2_authorize)
            status: Operation status (success, failed)
            service: Service name (optional, defaults to service name used during initialization)
        """
        service_label = service or self.service_name
        auth_operations_total.labels(operation=operation, status=status, service=service_label).inc()

    def record_validation_error(self, field: str, error_type: str, service: Optional[str] = None) -> None:
        """Record data validation error

        Args:
            field: Field name that failed validation
            error_type: Error type (required, format, range, unique)
            service: Service name (optional, defaults to service name used during initialization)
        """
        service_label = service or self.service_name
        validation_errors_total.labels(field=field, error_type=error_type, service=service_label).inc()

    def track_operation_in_progress(self, operation: str, service: Optional[str] = None) -> "OperationTracker":
        """Track in-progress operations (context manager)

        Args:
            operation: Operation name
            service: Service name (optional, defaults to service name used during initialization)

        Returns:
            Operation tracker context manager

        Example usage:
            ```python
            with metrics_collector.track_operation_in_progress("host_create"):
                # Execute business operation
                await create_host(host_data)
            ```
        """
        service_label = service or self.service_name
        return OperationTracker(operation, service_label)


class OperationTracker:
    """Operation tracker context manager

    Used to track the number and duration of ongoing operations
    """

    def __init__(self, operation: str, service: str):
        """Initialize operation tracker

        Args:
            operation: Operation name
            service: Service name
        """
        self.operation = operation
        self.service = service
        self.start_time: Optional[float] = None

    def __enter__(self) -> "OperationTracker":
        """Enter context, increment ongoing operation count"""
        business_operations_in_progress.labels(operation=self.operation, service=self.service).inc()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context, decrement ongoing operation count and record duration"""
        business_operations_in_progress.labels(operation=self.operation, service=self.service).dec()

        if self.start_time is not None:
            duration = time.time() - self.start_time
            business_operation_duration_seconds.labels(operation=self.operation, service=self.service).observe(duration)

            # Record operation result
            status = "failed" if exc_type is not None else "success"
            business_operations_total.labels(operation=self.operation, status=status, service=self.service).inc()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_middleware(service_name: str) -> Callable:
    """Get Prometheus metrics collection middleware

    Args:
        service_name: Service name

    Returns:
        Prometheus metrics collection middleware class
    """
    return PrometheusMetricsMiddleware


def get_metrics_response() -> Response:
    """Get Prometheus metrics response

    Returns:
        FastAPI response containing metrics data
    """

    metrics_data = generate_latest(registry)
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


def init_metrics(service_name: str, service_version: str, environment: str) -> MetricsCollector:
    """Initialize monitoring metrics

    Args:
        service_name: Service name
        service_version: Service version
        environment: Runtime environment

    Returns:
        Configured metrics collector instance
    """
    # Add process metrics collector (collect system metrics like memory, CPU, etc.)
    try:
        ProcessCollector(registry=registry)
        logger.info("Process metrics collector enabled")
    except Exception as e:
        logger.warning(f"Failed to enable process metrics collector: {e}")

    # Add platform metrics collector (collect platform-related metrics)
    try:
        PlatformCollector(registry=registry)
        logger.info("Platform metrics collector enabled")
    except Exception as e:
        logger.warning(f"Failed to enable platform metrics collector: {e}")

    # Set service information
    metrics_collector.set_service_info(name=service_name, version=service_version, environment=environment)
    logger.info(f"Monitoring metrics initialization completed: {service_name} v{service_version}")

    return metrics_collector
