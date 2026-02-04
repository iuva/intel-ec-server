"""
Monitoring Module
Provides Prometheus metrics collection and health check functionality
"""

# Import metrics and utility functions from prometheus_metrics module
from .prometheus_metrics import (
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
    # Business metrics
    "active_sessions",
    "active_users",
    # System metrics
    "app_info",
    "app_start_time",
    "auth_operations_total",
    # Cache metrics
    "cache_hits_total",
    "cache_misses_total",
    # Database metrics
    "db_connections_active",
    "db_connections_idle",
    "db_connections_total",
    "db_queries_total",
    "db_query_duration_seconds",
    # Utility functions
    "get_metrics",
    "get_metrics_content_type",
    "get_python_info",
    # HTTP metrics
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
