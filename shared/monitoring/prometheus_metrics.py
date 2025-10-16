"""
Prometheus 指标收集模块
提供统一的指标收集和导出功能
"""

from functools import wraps
import time
from typing import Any, Awaitable, Callable, Optional

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

# ==========================================
# HTTP 请求指标
# ==========================================

# HTTP 请求总数
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status", "service"],
)

# HTTP 请求响应时间
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

# HTTP 请求大小
http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint", "service"],
)

# HTTP 响应大小
http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint", "service"],
)

# 活跃请求数
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint", "service"],
)


# ==========================================
# 数据库指标
# ==========================================

# 数据库连接池
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

# 数据库查询
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
# 缓存指标
# ==========================================

# Redis 操作
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

# 缓存命中率
cache_hits_total = Counter("cache_hits_total", "Total number of cache hits", ["cache_name", "service"])

cache_misses_total = Counter("cache_misses_total", "Total number of cache misses", ["cache_name", "service"])


# ==========================================
# 业务指标
# ==========================================

# 用户操作
user_operations_total = Counter(
    "user_operations_total",
    "Total number of user operations",
    ["operation", "status", "service"],
)

# 认证操作
auth_operations_total = Counter(
    "auth_operations_total",
    "Total number of authentication operations",
    ["operation", "status", "service"],
)

# 活跃用户数
active_users = Gauge("active_users", "Number of active users", ["service"])

# 活跃会话数
active_sessions = Gauge("active_sessions", "Number of active sessions", ["service"])


# ==========================================
# 系统指标
# ==========================================

# 应用信息
app_info = Info("app_info", "Application information")

# 应用启动时间
app_start_time = Gauge("app_start_time_seconds", "Application start time in unix timestamp", ["service"])

# Python 版本信息（使用懒加载避免重复注册）
_python_info = None


def get_python_info() -> Optional[Info]:
    """获取 Python 版本信息指标（单例模式）"""
    global _python_info
    if _python_info is None:
        try:
            _python_info = Info("python_info", "Python version information")
        except ValueError:
            # 如果已经注册，从注册表获取
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
# 工具函数
# ==========================================


def track_request_metrics(
    service_name: str,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    装饰器：跟踪 HTTP 请求指标

    Args:
        service_name: 服务名称
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 从请求中获取信息
            request = kwargs.get("request") or (args[0] if args else None)

            if request:
                method = getattr(request, "method", "UNKNOWN")
                endpoint = getattr(getattr(request, "url", None), "path", "/unknown")

                # 增加进行中的请求数
                http_requests_in_progress.labels(method=method, endpoint=endpoint, service=service_name).inc()

                start_time = time.time()

                try:
                    # 执行请求
                    response = await func(*args, **kwargs)

                    # 记录请求指标
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
                    # 减少进行中的请求数
                    http_requests_in_progress.labels(method=method, endpoint=endpoint, service=service_name).dec()
            else:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def track_db_query(
    database: str, operation: str, service_name: str
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    装饰器：跟踪数据库查询指标

    Args:
        database: 数据库名称
        operation: 操作类型
        service_name: 服务名称
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 记录查询指标
                duration = time.time() - start_time

                db_queries_total.labels(database=database, operation=operation, service=service_name).inc()

                db_query_duration_seconds.labels(database=database, operation=operation, service=service_name).observe(
                    duration
                )

                return result

            except Exception:
                # 记录失败的查询
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
    装饰器：跟踪缓存操作指标

    Args:
        cache_name: 缓存名称
        service_name: 服务名称
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation = func.__name__
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 记录操作指标
                duration = time.time() - start_time

                redis_operations_total.labels(operation=operation, status="success", service=service_name).inc()

                redis_operation_duration_seconds.labels(operation=operation, service=service_name).observe(duration)

                # 记录缓存命中/未命中
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
    设置应用信息

    Args:
        service_name: 服务名称
        version: 版本号
        environment: 环境
    """
    app_info.info({"service": service_name, "version": version, "environment": environment})

    app_start_time.labels(service=service_name).set(time.time())


def set_python_info() -> None:
    """设置 Python 版本信息"""
    import sys

    info_metric = get_python_info()
    if info_metric is not None:
        info_metric.info({"version": sys.version, "implementation": sys.implementation.name})


def get_metrics() -> bytes:
    """
    获取 Prometheus 格式的指标数据

    Returns:
        指标数据（bytes）
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """
    获取指标数据的 Content-Type

    Returns:
        Content-Type 字符串
    """
    return CONTENT_TYPE_LATEST
