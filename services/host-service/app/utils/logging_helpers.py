"""日志记录辅助函数

提供统一的日志记录工具函数，重导出共享模块的函数以保持向后兼容。

注意：此模块为向后兼容保留，新代码应直接从 shared.utils.logging_utils 导入。
"""

# 重导出共享模块的函数，保持向后兼容
from shared.utils.logging_utils import (
    log_auth_failure,
    log_auth_success,
    log_db_error,
    log_db_query,
    log_external_api_call,
    log_external_api_error,
    log_operation_completed,
    log_operation_failed,
    log_operation_start,
    log_request_completed,
    log_request_received,
    log_service_shutdown,
    log_service_startup,
    log_websocket_connect,
    log_websocket_disconnect,
    log_websocket_message,
    timed_operation,
    timed_operation_sync,
    with_request_logging,
)

__all__ = [
    # 基础日志
    "log_request_received",
    "log_request_completed",
    "log_operation_start",
    "log_operation_completed",
    "log_operation_failed",
    # 数据库日志
    "log_db_query",
    "log_db_error",
    # 外部 API 日志
    "log_external_api_call",
    "log_external_api_error",
    # 性能追踪
    "timed_operation",
    "timed_operation_sync",
    # 装饰器
    "with_request_logging",
    # WebSocket 日志
    "log_websocket_connect",
    "log_websocket_disconnect",
    "log_websocket_message",
    # 认证日志
    "log_auth_success",
    "log_auth_failure",
    # 服务日志
    "log_service_startup",
    "log_service_shutdown",
]
