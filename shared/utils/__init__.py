"""
共享工具模块

提供项目中常用的工具类和辅助函数
"""

from shared.utils.json_comparator import JSONComparator
from shared.utils.pagination import (
    CursorPaginationParams,
    CursorPaginationResponse,
    PaginationParams,
    PaginationResponse,
)
from shared.utils.service_discovery import ServiceDiscovery, get_service_discovery, init_service_discovery
from shared.utils.template_validator import TemplateValidator
from shared.utils.token_extractor import TokenExtractor, get_token_extractor

# 日志工具
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

# 主机验证和查询工具（延迟导入，避免循环依赖）
try:
    from shared.utils.host_validators import build_host_query, validate_host_exists
except ImportError:
    # 如果导入失败，提供占位符（避免循环导入）
    validate_host_exists = None  # type: ignore[assignment, misc]
    build_host_query = None  # type: ignore[assignment, misc]

__all__ = [
    # JSON 对比工具
    "JSONComparator",
    # 分页工具
    "PaginationParams",
    "PaginationResponse",
    "CursorPaginationParams",
    "CursorPaginationResponse",
    # 服务发现工具
    "ServiceDiscovery",
    "get_service_discovery",
    "init_service_discovery",
    # 模板验证工具
    "TemplateValidator",
    # Token 提取工具
    "TokenExtractor",
    "get_token_extractor",
    # 主机验证工具
    "validate_host_exists",
    "build_host_query",
    # 日志工具
    "log_request_received",
    "log_request_completed",
    "log_operation_start",
    "log_operation_completed",
    "log_operation_failed",
    "log_db_query",
    "log_db_error",
    "log_external_api_call",
    "log_external_api_error",
    "timed_operation",
    "timed_operation_sync",
    "with_request_logging",
    "log_websocket_connect",
    "log_websocket_disconnect",
    "log_websocket_message",
    "log_auth_success",
    "log_auth_failure",
    "log_service_startup",
    "log_service_shutdown",
]
