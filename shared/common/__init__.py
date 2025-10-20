"""
Shared common modules

Provide common functions such as database, cache, logging, response, security and exception handling
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
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    # Database
    "Base",
    "BaseDBModel",
    "BusinessError",
    "DatabaseError",
    # Response
    "ErrorResponse",
    "ErrorType",
    # Security
    "JWTManager",
    "PaginationInfo",
    "PaginationResponse",
    "ResourceConflictError",
    "ResourceNotFoundError",
    "ServiceUnavailableError",
    "SuccessResponse",
    "ValidationError",
    # Cache
    "cache_result",
    # Logging
    "configure_logger",
    "create_error_response",
    "create_pagination_response",
    "create_success_response",
    "get_cache",
    "get_db_session",
    "get_jwt_manager",
    "get_logger",
<<<<<<< HEAD
    "get_***REMOVED***word_hash",
    # Decorators
    "handle_api_errors",
    "handle_service_errors",
    "hash_***REMOVED***word",
=======
    "get_***REMOVED***word_hash",
    # 装饰器
    "handle_api_errors",
    "handle_service_errors",
    "hash_***REMOVED***word",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    "init_jwt_manager",
    "mariadb_manager",
    "monitor_operation",
    "redis_manager",
    "set_cache",
    "verify_***REMOVED***word",
]
