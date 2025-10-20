"""
Authentication middleware module

Responsible for validating JWT tokens in requests, calling Auth Service for token verification
"""

import os
import sys
from typing import Any, Dict, Optional

import httpx

# Use try-except to handle path imports
try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from shared.common.cache import redis_manager
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    # If import fails, add project root directory to Python path
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    )
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from shared.common.cache import redis_manager
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse


logger = get_logger(__name__)


# ==================== Helper Functions ====================


def _get_locale_from_request(request: Request) -> str:
    """Get language preference from request

    Args:
        request: Request object

    Returns:
        Language code (e.g., "zh_CN", "en_US")
    """
    accept_language = request.headers.get("Accept-Language")
    return parse_accept_language(accept_language)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware

    Intercepts all requests and validates JWT token validity
    """

    def __init__(self, app):
        """Initialize authentication middleware

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)

        # Public path whitelist (no authentication required)
        self.public_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
<<<<<<< HEAD
            "/test-error",  # For testing
            # Authentication endpoints (public access)
            "/api/v1/auth/admin/login",
            "/api/v1/auth/device/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",  # ✅ Token refresh endpoint
            "/api/v1/auth/auto-refresh",  # ✅ Auto-renewal endpoint
            "/api/v1/auth/introspect",  # Token verification endpoint
            # ⚠️ WebSocket routes need authentication check at route level,
            # cannot be set as public path at middleware level, otherwise authentication cannot be enforced
=======
            "/test-error",  # 测试用
            # 认证端点（公开访问）
            "/api/v1/auth/admin/login",
            "/api/v1/auth/device/login",
            "/api/v1/auth/logout",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        }

        # ✅ Browser plugin interface prefixes (all paths starting with these prefixes do not require authentication)
        self.browser_plugin_prefixes = [
            "/api/v1/host/hosts",  # Browser plugin - host management interface (includes /hosts/vnc/*)
        ]

        # ✅ Read authentication service URL from unified configuration
        from app.core.config import settings

        self.auth_service_url = settings.auth_service_url.rstrip("/")

        logger.info(
            "Authentication middleware initialization completed",
            extra={
                "auth_service_url": self.auth_service_url,
            },
        )

        # ✅ Read HTTP client timeout configuration from unified config
        self.timeout = httpx.Timeout(
            settings.auth_middleware_timeout,
            connect=settings.auth_middleware_connect_timeout,
        )

    async def dispatch(self, request: Request, call_next):
        """Handle request

        Args:
            request: Request object
            call_next: Next middleware or route handler

        Returns:
            Response object
        """
<<<<<<< HEAD
        # ✅ Security measure: remove X-User-Info header from client (prevent forgery)
        # Gateway will add its own X-User-Info header after verifying token
        if "X-User-Info" in request.headers:
            logger.warning(
                "Detected X-User-Info header from client, removed (security measure)",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                    "hint": (
                        "X-User-Info header can only be added by Gateway after token verification, "
                        "client-sent headers will be removed"
                    ),
                },
            )
            # Remove X-User-Info header from client
            # Note: Starlette's headers are read-only, need to modify request object to remove
            # We will handle this in proxy.py, only log here

        # ✅ Handle OPTIONS preflight requests (CORS preflight requests)
        # OPTIONS requests should ***REMOVED*** through directly, handled by CORS middleware
        if request.method == "OPTIONS":
            logger.debug(
                "OPTIONS preflight request, skipping authentication check",
=======
        # 获取 Authorization 头（用于日志记录）
        auth_header = request.headers.get("Authorization")
        has_token = bool(auth_header)

        # 检查是否为公开路径
        is_public = self._is_public_path(request.url.path)

        # 详细的请求日志
        logger.info(
            "认证中间件处理请求",
            extra={
                "path": request.url.path,
                "method": request.method,
                "is_public_path": is_public,
                "has_authorization_header": has_token,
                "client_host": request.client.host if request.client else "unknown",
            },
        )

        # 如果是公开路径，跳过认证
        if is_public:
            logger.info(
                "公开路径，跳过认证检查",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return await call_next(request)

<<<<<<< HEAD
        # Get Authorization header (use multiple methods to ensure compatibility)
        # Starlette's headers object is case-insensitive, but use multiple methods for compatibility
        auth_header = None

        # Method 1: Standard method (Starlette headers are case-insensitive)
        auth_header = request.headers.get("Authorization")

        # Method 2: If method 1 fails, try lowercase key name
        if not auth_header:
            auth_header = request.headers.get("authorization")

        # Method 3: If still not found, try iterating through all headers (handle special cases)
        if not auth_header:
            for key, value in request.headers.items():
                if key.lower() == "authorization":
                    auth_header = value
                    logger.debug(
                        "Found Authorization header from header iteration",
                        extra={
                            "header_key": key,
                            "header_value": value,
                            "header_value_preview": value[:20] + "..."
                            if len(value) > 20
                            else value,
                        },
                    )
                    break

        has_token = bool(auth_header)

        # Debug log: record all header keys (only when Authorization not found, for debugging)
        if not auth_header:
            all_header_keys = list(request.headers.keys())
            logger.warning(
                "Authorization header not found, recording all header keys for debugging",
                extra={
                    "all_header_keys": all_header_keys,
                    "header_count": len(all_header_keys),
                    "path": request.url.path,
                    "method": request.method,
                },
            )

        # Check if path is public
        is_public = self._is_public_path(request.url.path)

        # Detailed request log
        logger.info(
            "Authentication middleware processing request",
            extra={
                "path": request.url.path,
                "method": request.method,
                "is_public_path": is_public,
                "has_authorization_header": has_token,
                "client_host": request.client.host if request.client else "unknown",
            },
        )

        # If public path, skip authentication
        if is_public:
            logger.info(
                "Public path, skipping authentication check",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return await call_next(request)

        # Check if Authorization header exists
        if not auth_header:
            logger.warning(
                "Protected path missing Authorization header",
=======
        # 检查是否有 Authorization 头
        if not auth_header:
            logger.warning(
                "受保护路径缺少 Authorization 头",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )
            return self._unauthorized_response(
<<<<<<< HEAD
                request=request,
                message="Missing authentication token",
                message_key="error.auth.missing_token",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "Please add Authorization: Bearer <token> to request headers",
=======
                message="缺少认证令牌",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "请在请求头中添加 Authorization: Bearer <token>",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                },
            )

        # Validate token format
        if not auth_header.startswith("Bearer "):
            logger.warning(
<<<<<<< HEAD
                "Invalid Authorization header format",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "auth_header_prefix": auth_header[:20]
                    if len(auth_header) > 20
                    else auth_header,
                },
            )
            return self._unauthorized_response(
                request=request,
                message="Invalid authentication token format",
                message_key="error.auth.invalid_token_format",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "Authorization header must use Bearer format",
=======
                "无效的 Authorization 头格式",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "auth_header_prefix": auth_header[:20] if len(auth_header) > 20 else auth_header,
                },
            )
            return self._unauthorized_response(
                message="无效的认证令牌格式",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "Authorization 头必须使用 Bearer 格式",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                    "expected_format": "Bearer <token>",
                },
            )

<<<<<<< HEAD
        # Extract token
        token = auth_header[7:]  # Remove "Bearer " prefix
        token_preview = token[:8] + "..." if len(token) > 8 else token

        logger.debug(
            "Starting token verification",
            extra={
                "path": request.url.path,
                "method": request.method,
                "token_preview": token_preview,
            },
        )

        # Verify token
        user_info = await self._verify_token(token, request.url.path, request.method)

        # Handle verification result
=======
        # 提取令牌
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        token_preview = token[:8] + "..." if len(token) > 8 else token

        logger.debug(
            "开始验证令牌",
            extra={
                "path": request.url.path,
                "method": request.method,
                "token_preview": token_preview,
            },
        )

        # 验证令牌
        user_info = await self._verify_token(token, request.url.path, request.method)

        # 处理验证结果
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        if not user_info:
            # ✅ Enhanced logging with more diagnostic information
            logger.warning(
<<<<<<< HEAD
                "Token verification failed, access denied",
=======
                "令牌验证失败，拒绝访问",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "token_preview": token_preview,
<<<<<<< HEAD
                    "token_length": len(token) if token else 0,
                    "auth_service_url": self.auth_service_url,
                    "hint": "Please check Gateway and Auth Service logs for detailed error information",
                },
            )
            return self._unauthorized_response(
                request=request,
                message="Invalid or expired authentication token",
                message_key="error.auth.token_invalid_or_expired",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "Token may be expired or invalid, please login again to get new token",
                    "troubleshooting": (
                        "Please check 'reason' field in Gateway and Auth Service logs for detailed error cause"
                    ),
=======
                },
            )
            return self._unauthorized_response(
                message="无效或过期的认证令牌",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "令牌可能已过期或无效，请重新登录获取新令牌",
                },
            )

        # 检查是否为服务错误（超时或连接错误）
        if isinstance(user_info, dict) and "error_type" in user_info:
            error_type = user_info["error_type"]

            if error_type == "timeout":
                logger.error(
                    "认证服务超时，返回 504 错误",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    code=504,
                    message="认证服务响应超时，请稍后重试",
                    error_code="GATEWAY_TIMEOUT",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "认证服务当前响应缓慢，请稍后重试",
                    },
                )

            elif error_type == "connection_error":
                logger.error(
                    "无法连接到认证服务，返回 503 错误",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    code=503,
                    message="认证服务暂时不可用，请稍后重试",
                    error_code="SERVICE_UNAVAILABLE",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "认证服务当前不可用，请联系系统管理员或稍后重试",
                    },
                )

            elif error_type == "request_error":
                logger.error(
                    "认证服务请求错误，返回 502 错误",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    code=502,
                    message="认证服务请求失败",
                    error_code="BAD_GATEWAY",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "网关无法从认证服务获取有效响应",
                    },
                )

            # 其他未知错误类型，返回 500
            logger.error(
                "认证过程中发生未知错误",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": error_type,
                    "token_preview": token_preview,
                },
            )
            return self._create_error_response(
                code=500,
                message="认证过程中发生内部错误",
                error_code="INTERNAL_ERROR",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "系统内部错误，请联系系统管理员",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                },
            )

        # Check if service error (timeout or connection error)
        if isinstance(user_info, dict) and "error_type" in user_info:
            error_type = user_info["error_type"]

            if error_type == "timeout":
                logger.error(
                    "Authentication service timeout, returning 504 error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    request=request,
                    code=504,
                    message="Authentication service response timeout, please try again later",
                    message_key="error.auth.service_timeout",
                    error_code="GATEWAY_TIMEOUT",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": (
                            "Authentication service is currently responding slowly, please try again later"
                        ),
                    },
                )

            if error_type == "connection_error":
                logger.error(
                    "Unable to connect to authentication service, returning 503 error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    request=request,
                    code=503,
                    message="Authentication service temporarily unavailable, please try again later",
                    message_key="error.auth.service_unavailable",
                    error_code="SERVICE_UNAVAILABLE",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": (
                            "Authentication service is currently unavailable, "
                            "please contact system administrator or try again later"
                        ),
                    },
                )

            if error_type == "request_error":
                logger.error(
                    "Authentication service request error, returning 502 error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    request=request,
                    code=502,
                    message="Authentication service request failed",
                    message_key="error.auth.service_error",
                    error_code="BAD_GATEWAY",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "Gateway cannot get valid response from authentication service",
                    },
                )

            # Other unknown error types, return 500
            logger.error(
                "Unknown error occurred during authentication",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": error_type,
                    "token_preview": token_preview,
                },
            )
            return self._create_error_response(
                request=request,
                code=500,
                message="Internal error occurred during authentication",
                message_key="error.internal",
                error_code="INTERNAL_ERROR",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": (
                        "System internal error, please contact system administrator"
                    ),
                },
            )

        # Add user information to request state
        request.state.user = user_info

        logger.info(
<<<<<<< HEAD
            "Token verification successful, access allowed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "id": user_info.get("id"),
=======
            "令牌验证成功，允许访问",
            extra={
                "path": request.url.path,
                "method": request.method,
                "user_id": user_info.get("user_id"),
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                "username": user_info.get("username"),
                "user_type": user_info.get("user_type"),
            },
        )

<<<<<<< HEAD
        # Continue processing request
=======
        # 继续处理请求
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public

        Args:
            path: Request path

        Returns:
            Whether path is public
        """
        # Remove query parameters
        clean_path = path.split("?")[0]

<<<<<<< HEAD
        # Remove trailing slash (but keep root path "/")
        if clean_path != "/" and clean_path.endswith("/"):
            clean_path = clean_path.rstrip("/")

        # Check exact match
=======
        # 移除尾部斜杠（但保留根路径 "/"）
        if clean_path != "/" and clean_path.endswith("/"):
            clean_path = clean_path.rstrip("/")

        logger.debug(
            "检查路径是否为公开路径",
            extra={
                "original_path": path,
                "clean_path": clean_path,
                "public_paths_count": len(self.public_paths),
            },
        )

        # 检查精确匹配
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        if clean_path in self.public_paths:
            logger.debug(
                "路径精确匹配公开路径",
                extra={
                    "path": clean_path,
                    "match_type": "exact",
                },
            )
            return True

<<<<<<< HEAD
        # ✅ Check prefix match (for documentation paths and browser plugin interfaces)
        # Supported prefix match path patterns:
        # - /docs, /redoc, /openapi.json (documentation paths)
        # - /api/v1/host/hosts, /api/v1/host/vnc (browser plugin interfaces)
        prefix_match_paths = {
            "/docs",  # Swagger UI
            "/redoc",  # ReDoc
            "/openapi.json",  # OpenAPI spec
        }

        # Check documentation path prefix match
        for prefix_path in prefix_match_paths:
            if clean_path.startswith(prefix_path):
                return True

        # ✅ Check browser plugin interface prefix match (all browser plugin interfaces do not require authentication)
        for prefix_path in self.browser_plugin_prefixes:
            if clean_path.startswith(prefix_path):
                return True

=======
        # 检查路径前缀匹配（仅用于特定的文档路径）
        # 只对以下路径进行前缀匹配：/docs, /redoc, /openapi.json
        prefix_match_paths = {"/docs", "/redoc", "/openapi.json"}

        for public_path in self.public_paths:
            # 只对特定路径进行前缀匹配
            if public_path in prefix_match_paths:
                if clean_path.startswith(public_path):
                    logger.debug(
                        "路径前缀匹配公开路径（文档路径）",
                        extra={
                            "path": clean_path,
                            "matched_prefix": public_path,
                            "match_type": "prefix",
                        },
                    )
                    return True

        logger.debug(
            "路径不是公开路径，需要认证",
            extra={
                "path": clean_path,
                "checked_against_paths": list(self.public_paths),
            },
        )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        return False

    async def _verify_token(
        self, token: str, request_path: str = "", request_method: str = ""
    ) -> Optional[Dict[str, Any]]:
<<<<<<< HEAD
        """Verify JWT token

        Call Auth Service's introspect endpoint to verify token

        Args:
            token: JWT access token
            request_path: Request path (for logging)
            request_method: Request method (for logging)

        Returns:
            User information, returns None if verification fails
            Special case: returns dict with error_type to indicate service error
=======
        """验证 JWT 令牌

        调用 Auth Service 的 introspect 端点验证令牌

        Args:
            token: JWT 访问令牌
            request_path: 请求路径（用于日志）
            request_method: 请求方法（用于日志）

        Returns:
            用户信息，如果验证失败则返回 None
            特殊情况：返回包含 error_type 的字典表示服务错误
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        """
        token_preview = token[:8] + "..." if len(token) > 8 else token

        try:
<<<<<<< HEAD
            # Call Auth Service's introspect endpoint to verify token
            introspect_url = f"{self.auth_service_url}/api/v1/auth/introspect"
=======
            # 使用新的 introspect 端点（去掉/auth前缀，与auth服务路由保持一致）
            introspect_url = f"{self.auth_service_url}/api/v1/introspect"

            logger.debug(
                "调用 Auth Service 验证令牌",
                extra={
                    "introspect_url": introspect_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
            )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    introspect_url,
<<<<<<< HEAD
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
=======
                    json={"token": token},  # 使用 JSON 格式
                    headers={"Content-Type": "application/json"},
                )

                logger.debug(
                    "Auth Service 响应",
                    extra={
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] if response.text else "",
                        "token_preview": token_preview,
                    },
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                )

                if response.status_code == 200:
                    result = response.json()

                    # Check if token is valid
                    if result.get("code") == 200:
                        data = result.get("data", {})
                        if data.get("active"):
<<<<<<< HEAD
                            # ✅ Use id field uniformly, return None if missing (401)
                            user_id = data.get("id")

                            if not user_id:
                                logger.warning(
                                    "Token verification successful but id is empty",
                                    extra={
                                        "data_keys": list(data.keys()),
                                        "token_preview": token_preview,
                                        "request_path": request_path,
                                        "request_method": request_method,
                                        "reason": "missing_id",
                                        "auth_service_response": {
                                            "code": result.get("code"),
                                            "message": result.get("message"),
                                            "data": data,
                                        },
                                        "hint": "Auth Service returned empty id, token is invalid",
                                    },
                                )
                                return (
                                    None  # Return None to indicate verification failure
                                )

                            # ✅ Check if user/host has been deleted (read from Redis)
                            try:
                                user_type = data.get("user_type", "user")

                                if user_id:
                                    # Determine Redis key prefix based on user_type
                                    if user_type == "device":
                                        # device type represents host
                                        deleted_key = f"deleted:host:{user_id}"
                                    else:
                                        # admin or other types represent user
                                        deleted_key = f"deleted:user:{user_id}"

                                    # Check if deleted marker exists in Redis
                                    is_deleted = await redis_manager.exists(deleted_key)

                                    if is_deleted:
                                        logger.warning(
                                            "User/host corresponding to token has been deleted",
                                            extra={
                                                "id": user_id,
                                                "user_type": user_type,
                                                "deleted_key": deleted_key,
                                                "request_path": request_path,
                                                "request_method": request_method,
                                            },
                                        )
                                        return None  # Return None to indicate verification failure,
                                        # will trigger 401 response
                            except Exception as redis_error:
                                # Log warning when Redis operation fails, but continue verification (degradation)
                                logger.warning(
                                    "Redis deletion check failed, continuing token verification",
                                    extra={
                                        "id": user_id,
                                        "user_type": data.get("user_type"),
                                        "error": str(redis_error),
                                        "error_type": type(redis_error).__name__,
                                        "request_path": request_path,
                                        "hint": (
                                            "When Redis is unavailable, skip deletion check and "
                                            "continue token verification (degradation)"
                                        ),
                                    },
                                )
                                # Continue execution, don't reject all requests due to Redis failure

                            # ✅ Construct user information (use id field uniformly)
=======
                            # 构造用户信息
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                            user_info = {
                                "id": user_id,
                                "username": data.get("username"),
                                "user_type": data.get("user_type"),
                                "active": data.get("active"),
                            }

                            logger.info(
<<<<<<< HEAD
                                "Token verification successful - Auth Service returned valid user information",
=======
                                "令牌验证成功 - Auth Service 返回有效用户信息",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                                extra={
                                    "id": user_info.get("id"),
                                    "username": user_info.get("username"),
                                    "user_type": user_info.get("user_type"),
                                    "token_preview": token_preview,
                                    "request_path": request_path,
                                },
                            )
                            return user_info
<<<<<<< HEAD
                        logger.warning(
                            "Token verification failed - token not active",
                            extra={
                                "token_preview": token_preview,
                                "active": data.get("active"),
                                "request_path": request_path,
                                "request_method": request_method,
                                "reason": "token_inactive",
                                "auth_service_response": {
                                    "code": result.get("code"),
                                    "message": result.get("message"),
                                    "data_keys": list(data.keys())
                                    if isinstance(data, dict)
                                    else [],
                                },
                                "hint": (
                                    "Token may be expired, blacklisted, or malformed"
                                ),
                            },
                        )
                    else:
                        logger.warning(
                            "Token verification failed - Auth Service returned error code",
=======
                        else:
                            logger.warning(
                                "令牌验证失败 - 令牌未激活",
                                extra={
                                    "token_preview": token_preview,
                                    "active": data.get("active"),
                                    "request_path": request_path,
                                    "request_method": request_method,
                                    "reason": "token_inactive",
                                },
                            )
                    else:
                        logger.warning(
                            "令牌验证失败 - Auth Service 返回错误码",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                            extra={
                                "response_code": result.get("code"),
                                "response_message": result.get("message"),
                                "token_preview": token_preview,
                                "request_path": request_path,
                                "request_method": request_method,
                                "reason": "auth_service_error",
                            },
                        )
                else:
                    logger.warning(
<<<<<<< HEAD
                        "Token verification failed - HTTP status code abnormal",
                        extra={
                            "status_code": response.status_code,
                            "response_text": response.text[:200]
                            if response.text
                            else "",
=======
                        "令牌验证失败 - HTTP 状态码异常",
                        extra={
                            "status_code": response.status_code,
                            "response_text": response.text[:200] if response.text else "",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                            "token_preview": token_preview,
                            "request_path": request_path,
                            "request_method": request_method,
                            "reason": "http_error",
                        },
                    )
                return None

        except httpx.TimeoutException as e:
            logger.error(
<<<<<<< HEAD
                "Token verification timeout - Auth Service response timeout",
=======
                "令牌验证超时 - Auth Service 响应超时",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "auth_service_url": self.auth_service_url,
                    "timeout_config": str(self.timeout),
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_type": "timeout",
                    "error_detail": str(e),
                },
            )
<<<<<<< HEAD
            # Return special marker to indicate timeout error
=======
            # 返回特殊标记，表示超时错误
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            return {"error_type": "timeout"}

        except httpx.ConnectError as e:
            logger.error(
<<<<<<< HEAD
                "Unable to connect to authentication service - network connection failed",
=======
                "无法连接到认证服务 - 网络连接失败",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "auth_service_url": self.auth_service_url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_detail": "connection_refused_or_network_unreachable",
                },
            )
<<<<<<< HEAD
            # Return special marker to indicate connection error
=======
            # 返回特殊标记，表示连接错误
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            return {"error_type": "connection_error"}

        except httpx.HTTPStatusError as e:
            logger.error(
<<<<<<< HEAD
                "Auth Service returned HTTP error status",
=======
                "Auth Service 返回 HTTP 错误状态",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "status_code": e.response.status_code,
                    "response_text": e.response.text[:200] if e.response.text else "",
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_type": "http_status_error",
                },
            )
            return None

        except httpx.RequestError as e:
            logger.error(
<<<<<<< HEAD
                "Auth Service request error",
=======
                "Auth Service 请求错误",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
            )
            return {"error_type": "request_error"}

        except Exception as e:
            logger.error(
<<<<<<< HEAD
                "Token verification exception - unexpected error",
=======
                "令牌验证异常 - 未预期的错误",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
                exc_info=True,
            )
            return None

    def _create_error_response(
<<<<<<< HEAD
        self,
        request: Request,
        code: int,
        message: str,
        error_code: str,
        message_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """Create unified error response (supports i18n)

        Args:
            request: Request object (for getting language preference)
            code: HTTP status code
            message: Error message (fallback message)
            error_code: Error type identifier
            message_key: Translation key (optional)
            details: Error details (optional)
=======
        self, code: int, message: str, error_code: str, details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """创建统一的错误响应

        Args:
            code: HTTP 状态码
            message: 错误消息
            error_code: 错误类型标识
            details: 错误详情（可选）
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

        Returns:
            JSON response
        """
        locale = _get_locale_from_request(request)

        error_response = ErrorResponse(
            code=code,
<<<<<<< HEAD
            message=message,  # Fallback message
            message_key=message_key,
            error_code=error_code,
            details=details,
            locale=locale,
        )

        logger.warning(
            "Returning error response",
=======
            message=message,
            error_code=error_code,
            details=details,
        )

        logger.warning(
            "返回错误响应",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            extra={
                "status_code": code,
                "error_code": error_code,
                "message": message,
                "request_id": error_response.request_id,
            },
        )

        return JSONResponse(
            status_code=code,
            content=error_response.model_dump(),
        )

<<<<<<< HEAD
    def _unauthorized_response(
        self,
        request: Request,
        message: str,
        message_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """Return unauthorized response (401) (supports i18n)

        Args:
            request: Request object (for getting language preference)
            message: Error message (fallback message)
            message_key: Translation key (optional)
            details: Error details (optional)

        Returns:
            JSON response
        """
        return self._create_error_response(
            request=request,
            code=401,
            message=message,
            message_key=message_key,
=======
    def _unauthorized_response(self, message: str, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """返回未授权响应（401）

        Args:
            message: 错误消息
            details: 错误详情（可选）

        Returns:
            JSON 响应
        """
        return self._create_error_response(
            code=401,
            message=message,
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            error_code="UNAUTHORIZED",
            details=details,
        )
