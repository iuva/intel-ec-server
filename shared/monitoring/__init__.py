"""
监控模块
提供 Prometheus 指标收集和健康检查功能
"""

from .prometheus_metrics import (  # HTTP 指标; 数据库指标; 缓存指标; 业务指标; 系统指标; 工具函数
    active_sessions,
    active_users,
    app_info,
    app_start_time,
    auth_operations_total,
    cache_hits_total,
    cache_misses_total,
    db_connections_active,
    db_connections_idle,
    db_connections_total,
    db_queries_total,
    db_query_duration_seconds,
    get_metrics,
    get_metrics_content_type,
    get_python_info,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_requests_in_progress,
    http_requests_total,
    http_response_size_bytes,
    redis_operation_duration_seconds,
    redis_operations_total,
    set_app_info,
    set_python_info,
    track_cache_operation,
    track_db_query,
    track_request_metrics,
    user_operations_total,
)

__all__ = [
    # 业务指标
    "active_sessions",
    "active_users",
    # 系统指标
    "app_info",
    "app_start_time",
    "auth_operations_total",
    # 缓存指标
    "cache_hits_total",
    "cache_misses_total",
    # 数据库指标
    "db_connections_active",
    "db_connections_idle",
    "db_connections_total",
    "db_queries_total",
    "db_query_duration_seconds",
    # 工具函数
    "get_metrics",
    "get_metrics_content_type",
    "get_python_info",
    # HTTP 指标
    "http_request_duration_seconds",
    "http_request_size_bytes",
    "http_requests_in_progress",
    "http_requests_total",
    "http_response_size_bytes",
    "redis_operation_duration_seconds",
    "redis_operations_total",
    "set_app_info",
    "set_python_info",
    "track_cache_operation",
    "track_db_query",
    "track_request_metrics",
    "user_operations_total",
]
