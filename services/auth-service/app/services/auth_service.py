"""
Authentication Service Business Logic

Implement user login, token generation, token validation and other functions
"""

import os
import time
from typing import Optional

from app.models.host_rec import HostRec
from app.models.sys_conf import SysConf
from app.models.sys_user import SysUser
from app.models.user_session import UserSession
from app.schemas.auth import (
    AdminLoginRequest,
<<<<<<< HEAD
<<<<<<< HEAD
    AutoRefreshTokenRequest,
=======
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
    AutoRefreshTokenRequest,
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
    DeviceLoginRequest,
    IntrospectResponse,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from sqlalchemy import select

# Use try-except approach to handle path imports
try:
    from shared.common.cache import get_cache, set_cache
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
<<<<<<< HEAD
    from shared.common.security import JWTManager, verify_***REMOVED***word
=======
    from shared.common.security import JWTManager, hash_***REMOVED***word, verify_***REMOVED***word
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
except ImportError:
    # If import fails, add project root directory to Python path
    import sys

    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    )
    from shared.common.cache import get_cache, set_cache
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
<<<<<<< HEAD
<<<<<<< HEAD
    from shared.common.security import JWTManager, verify_***REMOVED***word
=======
    from shared.common.security import JWTManager

# 密码加密配置
from ***REMOVED***lib.context import CryptContext

# 创建密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_admin_***REMOVED***word(plain_***REMOVED***word: str) -> str:
    """哈希管理后台用户密码

    用于创建或更新用户时对密码进行哈希处理

    Args:
        plain_***REMOVED***word: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(plain_***REMOVED***word)


def verify_admin_***REMOVED***word(plain_***REMOVED***word: str, hashed_***REMOVED***word: str) -> bool:
    """验证管理后台用户密码

    使用bcrypt进行密码验证

    Args:
        plain_***REMOVED***word: 明文密码
        hashed_***REMOVED***word: 数据库中存储的哈希密码

    Returns:
        bool: 密码是否正确
    """
    try:
        # 使用***REMOVED***lib的bcrypt上下文验证密码
        return pwd_context.verify(plain_***REMOVED***word, hashed_***REMOVED***word)
    except (ValueError, TypeError) as e:
        # 如果密码验证失败，记录错误但不抛出异常
        logger.warning(
            "密码验证异常",
            extra={"operation": "verify_***REMOVED***word", "error_type": type(e).__name__, "error_message": str(e)},
        )
        return False

>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
    from shared.common.security import JWTManager, hash_***REMOVED***word, verify_***REMOVED***word
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

logger = get_logger(__name__)


class AuthService:
    """Authentication Service Class"""

    def __init__(self):
        """Initialize authentication service"""
        self.access_token_expire_minutes = 24 * 60  # 24 hours
        self.refresh_token_expire_days = 7

<<<<<<< HEAD
        # ✅ Validate JWT key configuration (must be set in production environment)
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production":
            # In production, key must be set and have sufficient length
            if not jwt_secret_key or len(jwt_secret_key) < 32:
                logger.error(
                    "Production environment must set JWT_SECRET_KEY environment variable with at least 32 characters"
                )
                raise ValueError(
                    (
                        "Production environment must set JWT_SECRET_KEY environment variable (min 32 chars). "
                        "Please configure JWT_SECRET_KEY in .env or ***REMOVED*** through environment variable."
                    )
                )
        # Development environment: if not set or too short, warn but proceed
        elif not jwt_secret_key or len(jwt_secret_key) < 8:
            logger.warning(
                (
                    "JWT_SECRET_KEY not set or too short (unsafe), "
                    "this is insecure in production environment. Using a temporary random key for dev."
                )
            )
            # Generate a random 32-char key for development if missing/weak
            # This ensures even dev environment doesn't use a known constant string
            import secrets

            jwt_secret_key = secrets.token_urlsafe(32)

        self.jwt_manager = JWTManager(
            secret_key=jwt_secret_key,
            algorithm="HS256",
            access_token_expire_minutes=self.access_token_expire_minutes,
            refresh_token_expire_days=self.refresh_token_expire_days,
        )
        # ✅ Optimization: Cache session factory
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)

        ✅ Optimization: Cache session factory, avoid duplicate acquisition
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    # ==================== Common Helper Methods (Performance Optimization Extraction) ====================

    async def _verify_refresh_token_and_check_blacklist(
        self,
        refresh_token: str,
        operation: str = "refresh_token",
    ) -> dict:
        """Verify refresh token and check blacklist (common method)

        ✅ Performance optimization: Extract repeated token validation and blacklist check logic

        Args:
            refresh_token: Refresh token
            operation: Operation name (for logging)

        Returns:
            dict: Verified payload

        Raises:
            BusinessError: Raised when validation fails
        """
        # 1. Verify refresh token
        payload = self.jwt_manager.verify_token(refresh_token)
        if not payload:
            raise BusinessError(
                message="Refresh token is invalid or expired",
                error_code="AUTH_INVALID_REFRESH_TOKEN",
            )

        # 2. Check token type
        if payload.get("type") != "refresh":
            raise BusinessError(
                message="Token type error",
                message_key="error.auth.invalid_token_type",
                error_code="AUTH_INVALID_TOKEN_TYPE",
                code=ServiceErrorCodes.AUTH_TOKEN_INVALID,
                http_status_code=400,
            )

        # 3. Check blacklist
        blacklist_key = f"refresh_token_blacklist:{refresh_token}"
        try:
            is_blacklisted = await get_cache(blacklist_key)
            logger.debug(
                "Blacklist check completed",
                extra={
                    "operation": operation,
                    "user_id": payload.get("sub"),
                    "is_blacklisted": is_blacklisted,
                },
            )
        except Exception as redis_error:
            logger.error(
                "Redis connection exception, rejecting Token refresh",
                extra={
                    "operation": operation,
                    "user_id": payload.get("sub"),
                    "error": str(redis_error),
                },
            )
            raise BusinessError(
                message="Refresh token service temporarily unavailable, please try again later",
                error_code="AUTH_SERVICE_UNAVAILABLE",
            )

        # 4. Verify blacklist status
        if is_blacklisted is True:
            logger.warning(
                "Refresh token has been used, rejecting duplicate use",
                extra={
                    "operation": operation,
                    "error_code": "AUTH_REFRESH_TOKEN_REUSED",
                    "user_id": payload.get("sub"),
                },
            )
            raise BusinessError(
                message="Refresh token has been used, please log in again",
                error_code="AUTH_REFRESH_TOKEN_REUSED",
            )

        return payload

    async def _add_token_to_blacklist(
        self,
        token: str,
        payload: dict,
        operation: str = "refresh_token",
    ) -> None:
        """Add token to blacklist (common method)

        ✅ Performance optimization: Extract repeated blacklist addition logic

        Args:
            token: Token string
            payload: Token payload
            operation: Operation name (for logging)
        """
        blacklist_key = f"refresh_token_blacklist:{token}"
        exp = payload.get("exp", 0)
        ttl = max(1, int(exp - time.time()))

        try:
            await set_cache(blacklist_key, True, expire=ttl)
            logger.debug(
                "Token has been added to blacklist",
                extra={
                    "operation": operation,
                    "user_id": payload.get("id") or payload.get("sub"),
                    "ttl_seconds": ttl,
                },
            )
        except Exception as cache_error:
            # Cache setting failed, log warning but don't block operation
            logger.warning(
                "Failed to add token to blacklist, but continue processing",
                extra={
                    "operation": operation,
                    "user_id": payload.get("id") or payload.get("sub"),
                    "error": str(cache_error),
                },
            )

    def _build_token_payload(
        self,
        user_id: str,
        username: str,
        user_type: str = "admin",
        extra_fields: Optional[dict] = None,
    ) -> dict:
        """Build unified token payload (common method)

        ✅ Performance optimization: Extract repeated token data construction logic

        Args:
            user_id: User ID
            username: Username
            user_type: User type
            extra_fields: Extra fields

        Returns:
            dict: token payload
        """
        payload = {
            "id": str(user_id),  # ✅ Unify field name to id
            "sub": str(user_id),  # Retain sub field for compatibility with old tokens
            "username": username,
            "user_type": user_type,
        }
        if extra_fields:
            payload.update(extra_fields)
        return payload

    # ==================== Business Methods ===================

    async def refresh_access_token(
        self, refresh_data: RefreshTokenRequest
    ) -> TokenResponse:
        """Refresh access token

        ✅ Performance optimization: Use common helper methods, reduce code duplication

        Args:
            refresh_data: Refresh token request data

        Returns:
            TokenResponse: New token response

        Raises:
            BusinessError: Raised when refresh fails
        """
        try:
            # ✅ Use common method to verify token and check blacklist
            payload = await self._verify_refresh_token_and_check_blacklist(
                refresh_data.refresh_token, "refresh_token"
            )

            # ✅ Consistently use id field (extract from sub if not available, compatible with old tokens)
            user_id = payload.get("id") or payload.get("sub")
=======
    async def refresh_access_token(self, refresh_data: RefreshTokenRequest) -> TokenResponse:
        """刷新访问令牌

        Args:
            refresh_data: 刷新令牌请求数据

        Returns:
            TokenResponse: 新的令牌响应

        Raises:
            BusinessError: 刷新失败时抛出
        """
        try:
            # 验证刷新令牌
            payload = self.jwt_manager.verify_token(refresh_data.refresh_token)
            if not payload:
                raise BusinessError(
                    message="刷新令牌无效或已过期",
                    error_code="AUTH_INVALID_REFRESH_TOKEN",
                )

            # 检查令牌类型
            if payload.get("type") != "refresh":
                raise BusinessError(message="令牌类型错误", error_code="AUTH_INVALID_TOKEN_TYPE")

            # 检查 refresh_token 是否已被使用（在黑名单中）
            blacklist_key = f"refresh_token_blacklist:{refresh_data.refresh_token}"

            is_blacklisted = None
            try:
                is_blacklisted = await get_cache(blacklist_key)

                logger.debug(
                    "黑名单检查完成",
                    extra={
                        "operation": "refresh_token",
                        "user_id": payload.get("sub"),
                        "blacklist_key": blacklist_key[:50] + "...",
                        "is_blacklisted": is_blacklisted,
                        "redis_status": "连接正常" if is_blacklisted is not None or is_blacklisted is False else "未知",
                    },
                )
            except Exception as redis_error:
                # Redis 连接失败 - 为了安全起见，拒绝刷新
                logger.error(
                    "Redis 连接异常，拒绝 Token 刷新",
                    extra={
                        "operation": "refresh_token",
                        "user_id": payload.get("sub"),
                        "error": str(redis_error),
                        "error_type": type(redis_error).__name__,
                        "hint": "请检查 Redis 连接配置",
                    },
                )
                raise BusinessError(
                    message="刷新令牌服务暂时不可用，请稍后重试",
                    error_code="AUTH_SERVICE_UNAVAILABLE",
                )

            # 检查 refresh_token 是否已被使用
            if is_blacklisted is True:
                logger.warning(
                    "刷新令牌已被使用过，拒绝重复使用",
                    extra={
                        "operation": "refresh_token",
                        "error_code": "AUTH_REFRESH_TOKEN_REUSED",
                        "user_id": payload.get("sub"),
                    },
                )
                raise BusinessError(
                    message="刷新令牌已被使用，请重新登录",
                    error_code="AUTH_REFRESH_TOKEN_REUSED",
                )

            # 注意：is_blacklisted is None 或 is_blacklisted is False 都表示令牌有效
            # - None: Redis 中不存在该键（令牌未被使用过）
            # - False: Redis 中存在该键且值为 False（正常情况）
            # 两种情况下都应该允许刷新
            if is_blacklisted not in (None, False):
                # 这不应该发生，但如果发生说明有问题
                logger.warning(
                    "黑名单检查返回异常值",
                    extra={
                        "operation": "refresh_token",
                        "user_id": payload.get("sub"),
                        "blacklist_value": is_blacklisted,
                        "value_type": type(is_blacklisted).__name__,
                    },
                )
                raise BusinessError(
                    message="令牌验证异常，请重新登录",
                    error_code="AUTH_TOKEN_VERIFICATION_ERROR",
                )

            user_id = payload.get("sub")
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            username = payload.get("username")

            # ✅ Validate required fields
            if not user_id or not username:
                raise BusinessError(
                    message="Token data is incomplete, missing user information",
                    error_code="AUTH_TOKEN_INVALID",
                )

<<<<<<< HEAD
<<<<<<< HEAD
            # ✅ Use common method to build token payload
            token_data = self._build_token_payload(str(user_id), str(username))

            # Generate new access token
            access_token = self.jwt_manager.create_access_token(data=token_data)

            # ✅ Use common method to add old token to blacklist
            await self._add_token_to_blacklist(
                refresh_data.refresh_token, payload, "refresh_token"
            )

            logger.info(
                "Token refresh successful",
=======
            # 将已使用的 refresh_token 加入黑名单（过期时间设置为 refresh_token 的剩余有效期）

            exp = payload.get("exp", 0)
            ttl = max(1, int(exp - time.time()))  # 确保 TTL 至少为 1 秒

            try:
                await set_cache(blacklist_key, True, expire=ttl)
                logger.debug(
                    "令牌已添加到黑名单",
                    extra={
                        "operation": "refresh_token",
                        "user_id": user_id,
                        "ttl_seconds": ttl,
                    },
                )
            except Exception as cache_error:
                # 缓存设置失败，但不应该阻止令牌刷新
                logger.warning(
                    "添加令牌黑名单失败，但继续处理",
                    extra={
                        "operation": "refresh_token",
                        "user_id": user_id,
                        "error": str(cache_error),
                        "error_type": type(cache_error).__name__,
                    },
                )
                # 继续处理，不抛出异常

            logger.info(
                "令牌刷新成功",
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
                extra={
                    "operation": "refresh_token",
                    "user_id": user_id,
                    "username": username,
                },
            )
<<<<<<< HEAD
=======
            logger.info("令牌刷新成功", extra={"operation": "refresh_token", "user_id": user_id, "username": username})
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_data.refresh_token,
                token_type="bearer",
                expires_in=self.access_token_expire_minutes * 60,
            )
        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "令牌刷新异常",
                extra={
                    "operation": "refresh_token",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="令牌刷新失败，请重新登录",
                error_code="AUTH_REFRESH_FAILED",
            )

    async def auto_refresh_tokens(self, refresh_data: AutoRefreshTokenRequest) -> TokenResponse:
        """自动续期访问令牌和刷新令牌（双 token 续期机制）

        当刷新令牌将要过期时，自动生成新的 refresh_token 和 access_token

        Args:
            refresh_data: 自动续期请求数据

        Returns:
            TokenResponse: 新的访问令牌和刷新令牌

        Raises:
            BusinessError: 续期失败时抛出
        """
        try:
            # 验证刷新令牌
            payload = self.jwt_manager.verify_token(refresh_data.refresh_token)
            if not payload:
                raise BusinessError(
                    message="刷新令牌无效或已过期",
                    error_code="AUTH_INVALID_REFRESH_TOKEN",
                )

            # 检查令牌类型
            if payload.get("type") != "refresh":
                raise BusinessError(message="令牌类型错误", error_code="AUTH_INVALID_TOKEN_TYPE")

            # 检查 refresh_token 是否已被使用（在黑名单中）
            blacklist_key = f"refresh_token_blacklist:{refresh_data.refresh_token}"

            try:
                is_blacklisted = await get_cache(blacklist_key)
            except Exception as redis_error:
                # Redis 连接失败 - 为了安全起见，拒绝刷新
                logger.error(
                    "Redis 连接异常，拒绝 Token 刷新",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "user_id": payload.get("sub"),
                        "error": str(redis_error),
                        "hint": "请检查 Redis 连接配置",
                    },
                )
                raise BusinessError(
                    message="刷新令牌服务暂时不可用，请稍后重试",
                    error_code="AUTH_SERVICE_UNAVAILABLE",
                )

            # 使用 is True 明确检查（即使返回 None 也不会误判为 True）
            if is_blacklisted is True:
                logger.warning(
                    "刷新令牌已被使用过，拒绝重复使用",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "error_code": "AUTH_REFRESH_TOKEN_REUSED",
                        "user_id": payload.get("sub"),
                    },
                )
                raise BusinessError(
                    message="刷新令牌已被使用，请重新登录",
                    error_code="AUTH_REFRESH_TOKEN_REUSED",
                )
            if is_blacklisted is None:
                # 无法确定令牌状态 - 在严格安全模式下也应该拒绝
                logger.warning(
                    "无法访问黑名单 (可能 Redis 连接失败)",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "user_id": payload.get("sub"),
                        "hint": "Token 状态无法确认，为了安全起见拒绝刷新",
                    },
                )
                raise BusinessError(
                    message="刷新令牌验证失败，请重新登录",
                    error_code="AUTH_TOKEN_VERIFICATION_FAILED",
                )

            user_id = payload.get("sub")
            username = payload.get("username")
            user_type = payload.get("user_type", "admin")

            # 生成新的访问令牌
            excluded_keys = {"sub", "username", "user_type", "exp", "type", "iat"}
            extra_fields = {k: v for k, v in payload.items() if k not in excluded_keys}
            access_token_data = {
                "sub": user_id,
                "username": username,
                "user_type": user_type,
                **extra_fields,
            }

            access_token = self.jwt_manager.create_access_token(data=access_token_data)

            # 如果需要自动续期 refresh_token
            new_refresh_token = refresh_data.refresh_token
            if refresh_data.auto_renew:
                refresh_token_data = {
                    "sub": user_id,
                    "username": username,
                    "user_type": user_type,
                    **extra_fields,
                }

                new_refresh_token = self.jwt_manager.create_refresh_token(data=refresh_token_data)

                logger.info(
                    "令牌自动续期成功",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "user_id": user_id,
                        "username": username,
                        "auto_renewed": True,
                    },
                )
            else:
                logger.info(
                    "访问令牌自动续期成功",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "user_id": user_id,
                        "username": username,
                        "auto_renewed": False,
                    },
                )

            # 将已使用的旧 refresh_token 加入黑名单（过期时间设置为 refresh_token 的剩余有效期）
            exp = payload.get("exp", 0)

            ttl = max(1, int(exp - time.time()))  # 确保 TTL 至少为 1 秒
            await set_cache(blacklist_key, True, expire=ttl)
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)

            return TokenResponse(
                access_token=access_token,
<<<<<<< HEAD
                refresh_token=refresh_data.refresh_token,
                token_type="bearer",
=======
                refresh_token=new_refresh_token,
                token_type=token_type,
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
                expires_in=self.access_token_expire_minutes * 60,
                refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
            )

        except BusinessError:
            raise
<<<<<<< HEAD
        except Exception as e:
            logger.error(
                "Token refresh exception",
                extra={
                    "operation": "refresh_token",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Token refresh failed, please log in again",
                error_code="AUTH_REFRESH_FAILED",
            )
=======
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                "令牌自动续期异常",
                extra={
                    "operation": "auto_refresh_tokens",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
<<<<<<< HEAD
            raise BusinessError(message="令牌刷新失败", error_code="AUTH_REFRESH_ERROR")
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
            raise BusinessError(message="令牌续期失败", error_code="AUTH_REFRESH_ERROR")
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)

    async def auto_refresh_tokens(
        self, refresh_data: AutoRefreshTokenRequest
    ) -> TokenResponse:
        """Auto-renew access token and refresh token (dual token renewal mechanism)

        ✅ Performance optimization: Use common helper methods, reduce code duplication
        Note: This method uses strict mode to check blacklist (None values will also be rejected)

        Args:
            refresh_data: Auto-renewal request data

        Returns:
            TokenResponse: New access token and refresh token

        Raises:
            BusinessError: Raised when renewal fails
        """
        try:
            # ✅ Use common method to verify token and check blacklist
            payload = await self._verify_refresh_token_and_check_blacklist(
                refresh_data.refresh_token, "auto_refresh_tokens"
            )

            # ✅ Consistently use id field (extract from sub if not available, compatible with old tokens)
            user_id = payload.get("id") or payload.get("sub")
            username = payload.get("username")
            user_type = payload.get("user_type", "admin")

            # ✅ Validate required fields
            if not user_id or not username:
                raise BusinessError(
                    message="Token data is incomplete, missing user information",
                    error_code="AUTH_TOKEN_INVALID",
                )

            # Extract additional fields (exclude standard fields)
            excluded_keys = {"id", "sub", "username", "user_type", "exp", "type", "iat"}
            extra_fields = {k: v for k, v in payload.items() if k not in excluded_keys}

            # ✅ Use common method to build token payload
            token_data = self._build_token_payload(
                str(user_id), str(username), str(user_type), extra_fields
            )

            # Generate new access token
            access_token = self.jwt_manager.create_access_token(data=token_data)

            # If auto-renewal of refresh_token is needed
            new_refresh_token = refresh_data.refresh_token
            if refresh_data.auto_renew:
                new_refresh_token = self.jwt_manager.create_refresh_token(
                    data=token_data
                )

                logger.info(
                    "Token auto-renewal successful",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "user_id": user_id,
                        "username": username,
                        "auto_renewed": True,
                    },
                )
            else:
                logger.info(
                    "Access token auto-renewal successful",
                    extra={
                        "operation": "auto_refresh_tokens",
                        "user_id": user_id,
                        "username": username,
                        "auto_renewed": False,
                    },
                )

            # ✅ Use common method to add old token to blacklist
            await self._add_token_to_blacklist(
                refresh_data.refresh_token, payload, "auto_refresh_tokens"
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=self.access_token_expire_minutes * 60,
                refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
            )

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                "Token auto-renewal exception",
                extra={
                    "operation": "auto_refresh_tokens",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Token renewal failed",
                message_key="error.auth.refresh_error",
                error_code="AUTH_REFRESH_ERROR",
                code=ServiceErrorCodes.AUTH_REFRESH_TOKEN_INVALID,
                http_status_code=400,
            )

    async def introspect_token(self, token: str) -> IntrospectResponse:
        """Validate token

        Args:
            token: Token to be validated

        Returns:
            IntrospectResponse: Token validation response
        """
        try:
            # ✅ Check token blacklist cache (enhanced exception handling)
            blacklist_key = f"token_blacklist:{token}"
            try:
                is_blacklisted = await get_cache(blacklist_key)
                if is_blacklisted:
                    logger.debug(
                        "Token is in blacklist",
                        extra={
                            "blacklist_key": blacklist_key[:50] + "...",
                            "operation": "introspect_token",
                        },
                    )
                    return IntrospectResponse(active=False)
            except Exception as redis_error:
                # ✅ When Redis connection fails, log warning but continue validation (degraded processing)
                # Don't reject all requests due to Redis failure, ensure service availability
                logger.warning(
                    "Redis blacklist check failed, continuing to validate token",
                    extra={
                        "operation": "introspect_token",
                        "error": str(redis_error),
                        "error_type": type(redis_error).__name__,
                        "hint": "When Redis is unavailable, skip blacklist check and continue validating token",
                    },
                )
                # Continue executing token validation, don't reject all requests due to Redis failure

            # Validate token
            token_preview = token[:20] + "..." if len(token) > 20 else token
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                # ✅ Enhanced logging: Record detailed information about token validation failure
                logger.warning(
                    "Token validation failed - JWT validation returned None",
                    extra={
                        "operation": "introspect_token",
                        "token_preview": token_preview,
                        "token_length": len(token) if token else 0,
                        "hint": (
                            "Token may have expired, invalid signature, incorrect format, or been added to blacklist. "
                            "Check JWTManager.verify_token logs for detailed error information."
                        ),
                    },
                )
                return IntrospectResponse(active=False)

            # ✅ Consistently use id field (extract from sub if not available, compatible with old tokens)
            user_id = payload.get("id") or payload.get("sub")
            if not user_id:
                logger.warning(
                    "Token payload is missing id and sub fields",
                    extra={
                        "operation": "introspect_token",
                        "payload_keys": list(payload.keys()),
                        "token_type": payload.get("type"),
                    },
                )
                return IntrospectResponse(active=False)

            # ✅ Convert to string to avoid precision loss
            user_id = str(user_id)

            # ✅ Enhanced logging: Record detailed information about successful token validation (especially device type)
            logger.info(
                "Token validation successful - returning user information",
                extra={
                    "operation": "introspect_token",
                    "id": user_id,
                    "username": payload.get("username"),
                    "user_type": payload.get("user_type"),
                    "token_type": payload.get("type", "access"),
                    "has_mg_id": "mg_id" in payload,
                    "has_host_ip": "host_ip" in payload,
                    "payload_keys": list(payload.keys()),
                },
            )

            return IntrospectResponse(
                active=True,
                id=user_id,  # ✅ Unify field name to id
                username=payload.get("username"),
                user_id=user_id,  # Compatible field
                exp=payload.get("exp"),
                token_type=payload.get("type", "access"),
                # ✅ Added: Return all payload fields, support device login
                user_type=payload.get("user_type"),
                mg_id=payload.get("mg_id"),
                host_ip=payload.get("host_ip"),
                sub=user_id,  # Compatible field
            )

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
<<<<<<< HEAD
                "Token validation exception",
                extra={
                    "operation": "introspect_token",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
=======
                "令牌验证异常",
                extra={"operation": "introspect_token", "error_type": type(e).__name__, "error_message": str(e)},
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
                exc_info=True,
            )
            return IntrospectResponse(active=False)

    async def admin_login(self, login_data: AdminLoginRequest) -> LoginResponse:
<<<<<<< HEAD
        """Admin login (traditional method)

        Authenticate using sys_user table
=======
        """管理员登录（传统方式）

        使用 sys_user 表进行认证

        Args:
            login_data: 登录请求数据（username, ***REMOVED***word）

        Returns:
            LoginResponse: 包含 token 的登录响应

        Raises:
            BusinessError: 认证失败时抛出
        """
        try:
            # 获取数据库会话
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 查询用户（使用 user_account 字段匹配 username）
                stmt = select(SysUser).where(
                    SysUser.user_account == login_data.username,
                    SysUser.del_flag == 0,  # 未删除
                )
                result = await db_session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(
                        "管理员用户不存在",
                        extra={
                            "operation": "admin_login",
                            "username": login_data.username,
                            "error_code": "AUTH_INVALID_CREDENTIALS",
                        },
                    )
                    raise BusinessError(
                        message="用户名或密码错误",
                        error_code="AUTH_INVALID_CREDENTIALS",
                    )

                # 检查用户状态
                if user.state_flag == 1:  # 停用状态
                    logger.warning(
                        "管理员用户已被停用",
                        extra={
                            "operation": "admin_login",
                            "username": login_data.username,
                            "user_id": user.id,
                            "error_code": "AUTH_USER_DISABLED",
                        },
                    )
                    raise BusinessError(message="用户账号已被禁用", error_code="AUTH_USER_DISABLED")

                # 验证密码
                if not verify_***REMOVED***word(login_data.***REMOVED***word, user.user_pwd):
                    logger.warning(
                        "管理员密码错误",
                        extra={
                            "operation": "admin_login",
                            "username": login_data.username,
                            "error_code": "AUTH_INVALID_CREDENTIALS",
                        },
                    )
                    raise BusinessError(
                        message="用户名或密码错误",
                        error_code="AUTH_INVALID_CREDENTIALS",
                    )

                # 生成访问令牌
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "sub": str(user.id),
                        "username": user.user_account,
                        "user_type": "admin",
                        "user_name": user.user_name,
                    }
                )

                logger.info(
                    "管理员登录成功",
                    extra={
                        "operation": "admin_login",
                        "user_id": user.id,
                        "username": user.user_account,
                    },
                )

                # 生成刷新令牌
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "sub": str(user.id),
                        "username": user.user_account,
                        "user_type": "admin",
                        "user_name": user.user_name,
                    }
                )

                token_type = "bearer"
                return LoginResponse(
                    token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    expires_in=self.access_token_expire_minutes * 60,
                    refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
                )

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError, ConnectionError) as e:
            logger.error(
                "管理员登录异常",
                extra={
                    "operation": "admin_login",
                    "username": login_data.username,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(message="登录服务暂时不可用", error_code="AUTH_SERVICE_ERROR")
        except Exception as e:
            # 捕获所有其他异常，包括数据库连接异常
            logger.error(
                "管理员登录系统异常",
                extra={
                    "operation": "admin_login",
                    "username": login_data.username,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(message="服务器内部错误", error_code="INTERNAL_SERVER_ERROR")

    async def device_login(self, login_data: DeviceLoginRequest) -> LoginResponse:
        """设备登录（传统方式）

        使用 host_rec 表进行认证，如果 mg_id 存在则更新，不存在则插入

        Args:
            login_data: 设备登录请求数据（mg_id, host_ip, username）

        Returns:
            LoginResponse: 包含 token 的登录响应

        Raises:
            BusinessError: 认证失败时抛出
        """
        try:
            # 获取数据库会话
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 查询设备记录
                stmt = select(HostRec).where(
                    HostRec.mg_id == login_data.mg_id,
                    HostRec.del_flag == 0,  # 未删除
                )
                result = await db_session.execute(stmt)
                host_rec = result.scalar_one_or_none()

                if host_rec:
                    # mg_id 存在，更新 host_ip 和 username
                    host_rec.host_ip = login_data.host_ip
                    host_rec.host_acct = login_data.username
                    host_rec.updated_time = datetime.now(timezone.utc)

                    logger.info(
                        "设备信息更新",
                        extra={
                            "operation": "device_login",
                            "mg_id": login_data.mg_id,
                            "host_ip": login_data.host_ip,
                            "username": login_data.username,
                            "host_rec_id": host_rec.id,
                        },
                    )
                else:
                    # mg_id 不存在，插入新记录
                    host_rec = HostRec(
                        mg_id=login_data.mg_id,
                        host_ip=login_data.host_ip,
                        host_acct=login_data.username,
                        appr_state=5,  # 待激活
                        host_state=5,  # 待激活
                        subm_time=datetime.now(timezone.utc),
                        created_time=datetime.now(timezone.utc),
                        updated_time=datetime.now(timezone.utc),
                        del_flag=0,
                    )
                    db_session.add(host_rec)
                    await db_session.flush()  # 获取新插入记录的 ID

                    logger.info(
                        "新设备注册",
                        extra={
                            "operation": "device_login",
                            "mg_id": login_data.mg_id,
                            "host_ip": login_data.host_ip,
                            "username": login_data.username,
                            "host_rec_id": host_rec.id,
                        },
                    )

                # 提交事务
                await db_session.commit()

                # 生成访问令牌
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "sub": str(host_rec.id),
                        "mg_id": login_data.mg_id,
                        "host_ip": login_data.host_ip,
                        "username": login_data.username,
                        "user_type": "device",
                    }
                )

                logger.info(
                    "设备登录成功",
                    extra={
                        "operation": "device_login",
                        "host_rec_id": host_rec.id,
                        "mg_id": login_data.mg_id,
                        "host_ip": login_data.host_ip,
                    },
                )

                # 生成刷新令牌
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "sub": str(host_rec.id),
                        "mg_id": login_data.mg_id,
                        "host_ip": login_data.host_ip,
                        "username": login_data.username,
                        "user_type": "device",
                    }
                )

                token_type = "bearer"
                return LoginResponse(
                    token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    expires_in=self.access_token_expire_minutes * 60,
                    refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
                )

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError, ConnectionError) as e:
            logger.error(
                "设备登录异常",
                extra={
                    "operation": "device_login",
                    "mg_id": login_data.mg_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(message="登录服务暂时不可用", error_code="AUTH_SERVICE_ERROR")

    async def logout(self, token: str) -> bool:
        """用户注销
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

        Args:
            login_data: Login request data (username, ***REMOVED***word)

        Returns:
            LoginResponse: Login response containing token

        Raises:
            BusinessError: Thrown when authentication fails
        """
        try:
            # Get database session
            session_factory = self.session_factory
            async with session_factory() as db_session:
                # Query user (use user_account field to match username)
                stmt = select(SysUser).where(
                    SysUser.user_account == login_data.username,
                    SysUser.del_flag == 0,  # Not deleted
                )
                result = await db_session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(
                        "Administrator user does not exist",
                        extra={
                            "operation": "admin_login",
                            "username": login_data.username,
                            "error_code": "AUTH_INVALID_CREDENTIALS",
                        },
                    )
                    raise BusinessError(
                        message="Username or ***REMOVED***word is incorrect",
                        error_code="AUTH_INVALID_CREDENTIALS",
                        http_status_code=401,
                    )

                # Check user status
                if user.state_flag == 1:  # Disabled status
                    logger.warning(
                        "Administrator user has been disabled",
                        extra={
                            "operation": "admin_login",
                            "username": login_data.username,
                            "user_id": user.id,
                            "error_code": "AUTH_USER_DISABLED",
                        },
                    )
                    raise BusinessError(
                        message="User account has been disabled",
                        message_key="error.auth.user_disabled",
                        error_code="AUTH_USER_DISABLED",
                        code=ServiceErrorCodes.AUTH_USER_INACTIVE,
                        http_status_code=403,
                    )

                # Verify ***REMOVED***word
                if not verify_***REMOVED***word(login_data.***REMOVED***word, user.user_pwd):
                    logger.warning(
                        "Administrator ***REMOVED***word is incorrect",
                        extra={
                            "operation": "admin_login",
                            "username": login_data.username,
                            "error_code": "AUTH_INVALID_CREDENTIALS",
                        },
                    )
                    raise BusinessError(
                        message="Username or ***REMOVED***word is incorrect",
                        error_code="AUTH_INVALID_CREDENTIALS",
                        http_status_code=401,
                    )

                # Generate access token (unify using id field)
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "id": str(user.id),  # ✅ Unify field name to id
                        "sub": str(
                            user.id
                        ),  # Retain sub field for compatibility with old token
                        "username": user.user_account,
                        "user_type": "admin",
                        "user_name": user.user_name,
                    }
                )

                logger.info(
                    "Administrator login successful",
                    extra={
                        "operation": "admin_login",
                        "user_id": user.id,
                        "username": user.user_account,
                    },
                )

                # Generate refresh token (unify using id field)
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "id": str(user.id),  # ✅ Unify field name to id
                        "sub": str(
                            user.id
                        ),  # Retain sub field for compatibility with old token
                        "username": user.user_account,
                        "user_type": "admin",
                        "user_name": user.user_name,
                    }
                )

                token_type = "bearer"
                return LoginResponse(
                    access_token=access_token,
                    token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    expires_in=self.access_token_expire_minutes * 60,
                    refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
                )

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError, ConnectionError) as e:
            logger.error(
                "Administrator login exception",
                extra={
                    "operation": "admin_login",
                    "username": login_data.username,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Login service temporarily unavailable",
                message_key="error.auth.service_error",
                error_code="AUTH_SERVICE_ERROR",
                code=ServiceErrorCodes.AUTH_OPERATION_FAILED,
                http_status_code=503,
            )
        except Exception as e:
            # Catch all other exceptions, including database connection exceptions
            logger.error(
                "Administrator login system exception",
                extra={
                    "operation": "admin_login",
                    "username": login_data.username,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Internal server error",
                message_key="error.internal",
                error_code="INTERNAL_SERVER_ERROR",
                code=500,
                http_status_code=500,
            )

    async def device_login(
        self, login_data: DeviceLoginRequest, current_user_id: Optional[int] = None
    ) -> LoginResponse:
        """Device login (traditional method)

        Authenticate using host_rec table, update if mg_id exists, insert if not exists

        Args:
            login_data: Device login request data (mg_id, host_ip, username)
            current_user_id: Current user ID (obtained from token, optional)

        Returns:
            LoginResponse: Login response containing token

        Raises:
            BusinessError: Thrown when authentication fails
        """
        try:
            # Get database session
            session_factory = self.session_factory
            async with session_factory() as db_session:
                # Query device records
                stmt = select(HostRec).where(
                    HostRec.mg_id == login_data.mg_id,
                    HostRec.del_flag == 0,  # Not deleted
                )
                result = await db_session.execute(stmt)
                host_rec = result.scalar_one_or_none()

                if host_rec:
                    # Check if device is disabled
                    if host_rec.appr_state == 0:
                        logger.warning(
                            "Device is disabled",
                            extra={
                                "operation": "device_login",
                                "mg_id": login_data.mg_id,
                                "host_rec_id": host_rec.id,
                            },
                        )
                        raise BusinessError(
                            message="Device is disabled, unable to login",
                            error_code="DEVICE_DISABLED",
                            code=403,
                        )

                    # mg_id exists, update host_ip, username and updated_by
                    host_rec.host_ip = login_data.host_ip
                    host_rec.host_acct = login_data.username
                    host_rec.updated_time = datetime.now(timezone.utc)
                    host_rec.updated_by = current_user_id  # Set updater

                    logger.info(
                        "Device information updated",
                        extra={
                            "operation": "device_login",
                            "mg_id": login_data.mg_id,
                            "host_ip": login_data.host_ip,
                            "username": login_data.username,
                            "host_rec_id": host_rec.id,
                            "updated_by": current_user_id,
                        },
                    )
                else:
                    # mg_id does not exist, insert new record

                    # 1. Find default configuration (def_pwd, def_port)
                    conf_stmt = select(SysConf).where(
                        SysConf.conf_key.in_(["def_pwd", "def_port"]),
                        SysConf.del_flag == 0,
                    )
                    conf_result = await db_session.execute(conf_stmt)
                    sys_confs = conf_result.scalars().all()

                    default_pwd = None
                    default_port = None

                    for conf in sys_confs:
                        if conf.conf_key == "def_pwd":
                            default_pwd = conf.conf_val
                        elif conf.conf_key == "def_port":
                            default_port = conf.conf_val

                    # 2. If default ***REMOVED***word exists, encrypt it
                    # encrypted_pwd = None
                    # if default_pwd:
                    #     try:
                    #         encrypted_pwd = aes_encrypt(default_pwd)
                    #     except Exception as e:
                    #         logger.error(
                    #             "Default ***REMOVED***word encryption failed",
                    #             extra={"error": str(e), "default_pwd": default_pwd},
                    #         )
                    #         # If encryption fails, do not set ***REMOVED***word to avoid plain text storage
                    #         encrypted_pwd = None

                    host_rec = HostRec(
                        mg_id=login_data.mg_id,
                        host_ip=login_data.host_ip,
                        host_acct=login_data.username,
                        host_pwd=default_pwd,  # Set default ***REMOVED***word (already encrypted)
                        host_port=default_port,  # Set default port
                        appr_state=2,  # New
                        host_state=5,  # Pending activation
                        subm_time=datetime.now(timezone.utc),
                        created_by=current_user_id,  # Set creator
                        created_time=datetime.now(timezone.utc),
                        updated_by=current_user_id,  # Set updater
                        updated_time=datetime.now(timezone.utc),
                        del_flag=0,
                    )
                    db_session.add(host_rec)
                    await db_session.flush()  # Get the ID of the newly inserted record

                    logger.info(
                        "New device registration",
                        extra={
                            "operation": "device_login",
                            "mg_id": login_data.mg_id,
                            "host_ip": login_data.host_ip,
                            "username": login_data.username,
                            "host_rec_id": host_rec.id,
                            "created_by": current_user_id,
                        },
                    )

                # Commit transaction
                await db_session.commit()

                # Generate access token (unify using id field)
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "id": str(host_rec.id),  # ✅ Unify field name to id
                        "sub": str(
                            host_rec.id
                        ),  # Retain sub field for compatibility with old token
                        "mg_id": login_data.mg_id,
                        "host_ip": login_data.host_ip,
                        "username": login_data.username,
                        "user_type": "device",
                    }
                )

                logger.info(
                    "Device login successful",
                    extra={
                        "operation": "device_login",
                        "host_rec_id": host_rec.id,
                        "mg_id": login_data.mg_id,
                        "host_ip": login_data.host_ip,
                    },
                )

                # Generate refresh token (unify using id field)
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "id": str(host_rec.id),  # ✅ Unify field name to id
                        "sub": str(
                            host_rec.id
                        ),  # Retain sub field for compatibility with old token
                        "mg_id": login_data.mg_id,
                        "host_ip": login_data.host_ip,
                        "username": login_data.username,
                        "user_type": "device",
                    }
                )

                token_type = "bearer"
                return LoginResponse(
                    access_token=access_token,
                    token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    expires_in=self.access_token_expire_minutes * 60,
                    refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
                )

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError, ConnectionError) as e:
            logger.error(
                "Device login exception",
                extra={
                    "operation": "device_login",
                    "mg_id": login_data.mg_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Login service temporarily unavailable",
                message_key="error.auth.service_error",
                error_code="AUTH_SERVICE_ERROR",
                code=ServiceErrorCodes.AUTH_OPERATION_FAILED,
                http_status_code=503,
            )

    async def logout(self, token: str) -> bool:
        """User logout

        Args:
            token: Access token

        Returns:
            bool: Whether logout was successful
        """
        try:
            # Verify token
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                raise BusinessError(
                    message="Token is invalid",
                    message_key="error.auth.token_invalid",
                    error_code="AUTH_INVALID_TOKEN",
                    code=ServiceErrorCodes.AUTH_TOKEN_INVALID,
                    http_status_code=401,
                )

            # Add token to blacklist
            blacklist_key = f"token_blacklist:{token}"
            exp = payload.get("exp", 0)
            ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))

            await set_cache(blacklist_key, True, expire=ttl)

            # Delete session record
            session_factory = self.session_factory
            async with session_factory() as db_session:
<<<<<<< HEAD
<<<<<<< HEAD
                stmt = select(UserSession).where(
                    UserSession.access_token == token, ~UserSession.del_flag
                )
=======
                stmt = select(UserSession).where(UserSession.access_token == token, ~UserSession.is_deleted)
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
=======
                stmt = select(UserSession).where(UserSession.access_token == token, ~UserSession.del_flag)
>>>>>>> 1c319f3 (feat(host): 添加VNC连接结果上报功能-[#16])
                result = await db_session.execute(stmt)
                user_session = result.scalar_one_or_none()

                if user_session:
                    user_session.del_flag = True
                    await db_session.commit()

            logger.info(
<<<<<<< HEAD
                "User logout successful",
                extra={
                    "operation": "logout",
                    "user_id": payload.get("sub"),
                    "username": payload.get("username"),
                },
=======
                "用户注销成功",
                extra={"operation": "logout", "user_id": payload.get("sub"), "username": payload.get("username")},
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            )
            return True

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError, ConnectionError) as e:
            logger.error(
<<<<<<< HEAD
                "User logout exception",
                extra={
                    "operation": "logout",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Logout failed",
                message_key="error.auth.logout_error",
                error_code="AUTH_LOGOUT_ERROR",
                code=ServiceErrorCodes.AUTH_OPERATION_FAILED,
                http_status_code=400,
            )
=======
                "用户注销异常",
                extra={"operation": "logout", "error_type": type(e).__name__, "error_message": str(e)},
                exc_info=True,
            )
            raise BusinessError(message="注销失败", error_code="AUTH_LOGOUT_ERROR")
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
