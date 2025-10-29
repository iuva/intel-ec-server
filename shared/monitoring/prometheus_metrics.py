"""
Prometheus Metrics Collection Module
Provides unified metrics collection and export functionality
"""

from functools import wraps
import sys
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

# ==========================================
# HTTP Request Metrics
# ==========================================

# HTTP Requests Total
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status", "service"],
)

# HTTP Request Duration
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
)

# HTTP Request Size
http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint", "service"],
)

# HTTP Response Size
http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint", "service"],
)

# Active Requests Count
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint", "service"],
)


# ==========================================
# Database Metrics
# ==========================================

# Database Connection Pool
db_connections_total = Gauge(
    "db_connections_total",
    "Total number of database connections",
    ["database", "service"],
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    ["database", "service"],
)

db_connections_idle = Gauge(
    "db_connections_idle",
    "Number of idle database connections",
    ["database", "service"],
)

# Database Queries
db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["database", "operation", "service"],
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["database", "operation", "service"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


# ==========================================
# Cache Metrics
# ==========================================

# Redis Operations
redis_operations_total = Counter(
    "redis_operations_total",
    "Total number of Redis operations",
    ["operation", "status", "service"],
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation", "service"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Cache Hit Rate
cache_hits_total = Counter("cache_hits_total", "Total number of cache hits", ["cache_name", "service"])

cache_misses_total = Counter("cache_misses_total", "Total number of cache misses", ["cache_name", "service"])


# ==========================================
# Business Metrics
# ==========================================

# User Operations
user_operations_total = Counter(
    "user_operations_total",
    "Total number of user operations",
    ["operation", "status", "service"],
)

# Authentication Operations
auth_operations_total = Counter(
    "auth_operations_total",
    "Total number of authentication operations",
    ["operation", "status", "service"],
)

# Active Users Count
active_users = Gauge("active_users", "Number of active users", ["service"])

# Active Sessions Count
active_sessions = Gauge("active_sessions", "Number of active sessions", ["service"])


# ==========================================
# System Metrics
# ==========================================

# Application Information
app_info = Info("app_info", "Application information")

# Application Start Time
app_start_time = Gauge("app_start_time_seconds", "Application start time in unix timestamp", ["service"])

# Python Version Information (using lazy loading to avoid duplicate registration)
_python_info = None


def get_python_info() -> Optional[Info]:
    """Get Python version information metric (singleton pattern)"""
    global _python_info
    if _python_info is None:
        try:
            _python_info = Info("python_info", "Python version information")
        except ValueError:
            # If already registered, get from registry
            from prometheus_client import REGISTRY

            for collector in list(REGISTRY._collector_to_names.keys()):
                if (
                    hasattr(collector, "_name")
                    and getattr(collector, "_name", None) == "python_info"
                    and isinstance(collector, Info)
                ):
                    _python_info = collector
                    break
    return _python_info


# ==========================================
# Utility Functions
# ==========================================


def track_request_metrics(
    service_name: str,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Decorator: Track HTTP request metrics

    Args:
        service_name: Service name
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get information from request
            request = kwargs.get("request") or (args[0] if args else None)

            if request:
                method = getattr(request, "method", "UNKNOWN")
                endpoint = getattr(getattr(request, "url", None), "path", "/unknown")

                # Increase in-progress requests count
                http_requests_in_progress.labels(method=method, endpoint=endpoint, service=service_name).inc()

                start_time = time.time()

                try:
                    # Execute request
                    response = await func(*args, **kwargs)

                    # Record request metrics
                    duration = time.time() - start_time
                    status = getattr(response, "status_code", 200)

                    http_requests_total.labels(
                        method=method,
                        endpoint=endpoint,
                        status=status,
                        service=service_name,
                    ).inc()

                    http_request_duration_seconds.labels(
                        method=method, endpoint=endpoint, service=service_name
                    ).observe(duration)

                    return response

                finally:
                    # Decrease in-progress requests count
                    http_requests_in_progress.labels(method=method, endpoint=endpoint, service=service_name).dec()
            else:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def track_db_query(
    database: str, operation: str, service_name: str
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Decorator: Track database query metrics

    Args:
        database: Database name
        operation: Operation type
        service_name: Service name
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Record query metrics
                duration = time.time() - start_time

                db_queries_total.labels(database=database, operation=operation, service=service_name).inc()

                db_query_duration_seconds.labels(database=database, operation=operation, service=service_name).observe(
                    duration
                )

                return result

            except Exception:
                # Record failed query
                db_queries_total.labels(
                    database=database,
                    operation=f"{operation}_error",
                    service=service_name,
                ).inc()
                raise

        return wrapper

    return decorator


def track_cache_operation(
    cache_name: str, service_name: str
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Decorator: Track cache operation metrics

    Args:
        cache_name: Cache name
        service_name: Service name
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation = func.__name__
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Record operation metrics
                duration = time.time() - start_time

                redis_operations_total.labels(operation=operation, status="success", service=service_name).inc()

                redis_operation_duration_seconds.labels(operation=operation, service=service_name).observe(duration)

                # Record cache hit/miss
                if operation == "get":
                    if result is not None:
                        cache_hits_total.labels(cache_name=cache_name, service=service_name).inc()
                    else:
                        cache_misses_total.labels(cache_name=cache_name, service=service_name).inc()

                return result

            except Exception:
                redis_operations_total.labels(operation=operation, status="error", service=service_name).inc()
                raise

        return wrapper

    return decorator


def set_app_info(service_name: str, version: str, environment: str = "development") -> None:
    """
    Set application information

    Args:
        service_name: Service name
        version: Version number
        environment: Environment
    """
    app_info.info({"service": service_name, "version": version, "environment": environment})

    app_start_time.labels(service=service_name).set(time.time())


def set_python_info() -> None:
    """Set Python version information"""

    info_metric = get_python_info()
    if info_metric is not None:
        info_metric.info({"version": sys.version, "implementation": sys.implementation.name})


def get_metrics() -> bytes:
    """
    Get metrics data in Prometheus format

    Returns:
        Metrics data (bytes)
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """
    Get Content-Type for metrics data

    Returns:
        Content-Type string
    """
    return CONTENT_TYPE_LATEST
