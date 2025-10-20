"""
共享通用模块

提供数据库、缓存、日志、响应、安全和异常处理等通用功能
"""

from shared.common.cache import cache_result, get_cache, redis_manager, set_cache
from shared.common.database import Base, BaseDBModel, get_db_session, mariadb_manager
from shared.common.decorators import handle_api_errors, handle_service_errors, monitor_operation
from shared.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    DatabaseError,
    ErrorType,
    ResourceConflictError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from shared.common.loguru_config import configure_logger, get_logger
from shared.common.response import (
    ErrorResponse,
    PaginationInfo,
    PaginationResponse,
    SuccessResponse,
    create_error_response,
    create_pagination_response,
    create_success_response,
)
from shared.common.security import (
    JWTManager,
    get_jwt_manager,
    get_***REMOVED***word_hash,
    hash_***REMOVED***word,
    init_jwt_manager,
    verify_***REMOVED***word,
)

__all__ = [
    # 异常
    "AuthenticationError",
    "AuthorizationError",
    # 数据库
    "Base",
    "BaseDBModel",
    "BusinessError",
    "DatabaseError",
    # 响应
    "ErrorResponse",
    "ErrorType",
    # 安全
    "JWTManager",
    "PaginationInfo",
    "PaginationResponse",
    "ResourceConflictError",
    "ResourceNotFoundError",
    "ServiceUnavailableError",
    "SuccessResponse",
    "ValidationError",
    # 缓存
    "cache_result",
    # 日志
    "configure_logger",
    "create_error_response",
    "create_pagination_response",
    "create_success_response",
    "get_cache",
    "get_db_session",
    "get_jwt_manager",
    "get_logger",
    "get_***REMOVED***word_hash",
    # 装饰器
    "handle_api_errors",
    "handle_service_errors",
    "hash_***REMOVED***word",
    "init_jwt_manager",
    "mariadb_manager",
    "monitor_operation",
    "redis_manager",
    "set_cache",
    "verify_***REMOVED***word",
]
