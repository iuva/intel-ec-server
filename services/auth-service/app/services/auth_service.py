"""
认证服务业务逻辑

实现用户登录、令牌生成、令牌验证等功能
"""

from datetime import datetime, timezone
import os
import time
from typing import Optional

from sqlalchemy import select

from app.models.host_rec import HostRec
from app.models.sys_conf import SysConf
from app.models.sys_user import SysUser
from app.models.user_session import UserSession
from app.schemas.auth import (
    AdminLoginRequest,
    AutoRefreshTokenRequest,
    DeviceLoginRequest,
    IntrospectResponse,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
)

# 使用 try-except 方式处理路径导入
try:
    from shared.common.cache import get_cache, set_cache
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager, verify_***REMOVED***word
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.cache import get_cache, set_cache
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager, verify_***REMOVED***word

logger = get_logger(__name__)


class AuthService:
    """认证服务类"""

    def __init__(self):
        """初始化认证服务"""
        self.access_token_expire_minutes = 24 * 60  # 24 小时
        self.refresh_token_expire_days = 7

        # ✅ 验证 JWT 密钥配置（生产环境必须设置）
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production":
            if not jwt_secret_key or jwt_secret_key in (
                "your-secret-key-change-in-production",
                "your-secret-key-here",
                "default_secret_key",
                "",
            ):
                logger.error("生产环境必须设置 JWT_SECRET_KEY 环境变量，且不能使用默认值")
                raise ValueError("生产环境必须设置 JWT_SECRET_KEY 环境变量，请在 .env 中配置 JWT_SECRET_KEY 或通过环境变量传递。")
        # 开发环境：如果没有设置，使用默认值并警告
        elif not jwt_secret_key or jwt_secret_key in (
            "your-secret-key-change-in-production",
            "your-secret-key-here",
            "default_secret_key",
            "",
        ):
            logger.warning(
                "JWT_SECRET_KEY 未设置或使用默认值，这在生产环境中是不安全的，请设置该环境变量。"
            )
            jwt_secret_key = "your-secret-key-change-in-production"

        self.jwt_manager = JWTManager(
            secret_key=jwt_secret_key,
            algorithm="HS256",
            access_token_expire_minutes=self.access_token_expire_minutes,
            refresh_token_expire_days=self.refresh_token_expire_days,
        )
        # ✅ 优化：缓存会话工厂
        self._session_factory = None

    @property
    def session_factory(self):
        """获取会话工厂（延迟初始化，单例模式）

        ✅ 优化：缓存会话工厂，避免重复获取
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    # ==================== 通用辅助方法（性能优化提取） ====================

    async def _verify_refresh_token_and_check_blacklist(
        self,
        refresh_token: str,
        operation: str = "refresh_token",
    ) -> dict:
        """验证刷新令牌并检查黑名单（通用方法）

        ✅ 性能优化：提取重复的 token 验证和黑名单检查逻辑

        Args:
            refresh_token: 刷新令牌
            operation: 操作名称（用于日志）

        Returns:
            dict: 验证后的 payload

        Raises:
            BusinessError: 验证失败时抛出
        """
        # 1. 验证刷新令牌
        payload = self.jwt_manager.verify_token(refresh_token)
        if not payload:
            raise BusinessError(
                message="刷新令牌无效或已过期",
                error_code="AUTH_INVALID_REFRESH_TOKEN",
            )

        # 2. 检查令牌类型
        if payload.get("type") != "refresh":
            raise BusinessError(
                message="令牌类型错误",
                message_key="error.auth.invalid_token_type",
                error_code="AUTH_INVALID_TOKEN_TYPE",
                code=ServiceErrorCodes.AUTH_TOKEN_INVALID,
                http_status_code=400,
            )

        # 3. 检查黑名单
        blacklist_key = f"refresh_token_blacklist:{refresh_token}"
        try:
            is_blacklisted = await get_cache(blacklist_key)
            logger.debug(
                "黑名单检查完成",
                extra={
                    "operation": operation,
                    "user_id": payload.get("sub"),
                    "is_blacklisted": is_blacklisted,
                },
            )
        except Exception as redis_error:
            logger.error(
                "Redis 连接异常，拒绝 Token 刷新",
                extra={
                    "operation": operation,
                    "user_id": payload.get("sub"),
                    "error": str(redis_error),
                },
            )
            raise BusinessError(
                message="刷新令牌服务暂时不可用，请稍后重试",
                error_code="AUTH_SERVICE_UNAVAILABLE",
            )

        # 4. 验证黑名单状态
        if is_blacklisted is True:
            logger.warning(
                "刷新令牌已被使用过，拒绝重复使用",
                extra={
                    "operation": operation,
                    "error_code": "AUTH_REFRESH_TOKEN_REUSED",
                    "user_id": payload.get("sub"),
                },
            )
            raise BusinessError(
                message="刷新令牌已被使用，请重新登录",
                error_code="AUTH_REFRESH_TOKEN_REUSED",
            )

        return payload

    async def _add_token_to_blacklist(
        self,
        token: str,
        payload: dict,
        operation: str = "refresh_token",
    ) -> None:
        """将令牌加入黑名单（通用方法）

        ✅ 性能优化：提取重复的黑名单添加逻辑

        Args:
            token: 令牌字符串
            payload: 令牌 payload
            operation: 操作名称（用于日志）
        """
        blacklist_key = f"refresh_token_blacklist:{token}"
        exp = payload.get("exp", 0)
        ttl = max(1, int(exp - time.time()))

        try:
            await set_cache(blacklist_key, True, expire=ttl)
            logger.debug(
                "令牌已添加到黑名单",
                extra={
                    "operation": operation,
                    "user_id": payload.get("id") or payload.get("sub"),
                    "ttl_seconds": ttl,
                },
            )
        except Exception as cache_error:
            # 缓存设置失败，记录警告但不阻止操作
            logger.warning(
                "添加令牌黑名单失败，但继续处理",
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
        """构建统一的 token payload（通用方法）

        ✅ 性能优化：提取重复的 token 数据构建逻辑

        Args:
            user_id: 用户ID
            username: 用户名
            user_type: 用户类型
            extra_fields: 额外字段

        Returns:
            dict: token payload
        """
        payload = {
            "id": str(user_id),  # ✅ 统一字段名为 id
            "sub": str(user_id),  # 保留 sub 字段以兼容旧 token
            "username": username,
            "user_type": user_type,
        }
        if extra_fields:
            payload.update(extra_fields)
        return payload

    # ==================== 业务方法 ====================

    async def refresh_access_token(self, refresh_data: RefreshTokenRequest) -> TokenResponse:
        """刷新访问令牌

        ✅ 性能优化：使用通用辅助方法，减少代码重复

        Args:
            refresh_data: 刷新令牌请求数据

        Returns:
            TokenResponse: 新的令牌响应

        Raises:
            BusinessError: 刷新失败时抛出
        """
        try:
            # ✅ 使用通用方法验证 token 和检查黑名单
            payload = await self._verify_refresh_token_and_check_blacklist(
                refresh_data.refresh_token, "refresh_token"
            )

            # ✅ 统一使用 id 字段（如果没有则从 sub 提取，兼容旧 token）
            user_id = payload.get("id") or payload.get("sub")
            username = payload.get("username")

            # ✅ 验证必需字段
            if not user_id or not username:
                raise BusinessError(
                    message="令牌数据不完整，缺少用户信息",
                    error_code="AUTH_TOKEN_INVALID",
                )

            # ✅ 使用通用方法构建 token payload
            token_data = self._build_token_payload(str(user_id), str(username))

            # 生成新的访问令牌
            access_token = self.jwt_manager.create_access_token(data=token_data)

            # ✅ 使用通用方法将旧 token 加入黑名单
            await self._add_token_to_blacklist(
                refresh_data.refresh_token, payload, "refresh_token"
            )

            logger.info(
                "令牌刷新成功",
                extra={
                    "operation": "refresh_token",
                    "user_id": user_id,
                    "username": username,
                },
            )

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

        ✅ 性能优化：使用通用辅助方法，减少代码重复
        注意：此方法使用严格模式检查黑名单（None 值也会拒绝）

        Args:
            refresh_data: 自动续期请求数据

        Returns:
            TokenResponse: 新的访问令牌和刷新令牌

        Raises:
            BusinessError: 续期失败时抛出
        """
        try:
            # ✅ 使用通用方法验证 token 和检查黑名单
            payload = await self._verify_refresh_token_and_check_blacklist(
                refresh_data.refresh_token, "auto_refresh_tokens"
            )

            # ✅ 统一使用 id 字段（如果没有则从 sub 提取，兼容旧 token）
            user_id = payload.get("id") or payload.get("sub")
            username = payload.get("username")
            user_type = payload.get("user_type", "admin")

            # ✅ 验证必需字段
            if not user_id or not username:
                raise BusinessError(
                    message="令牌数据不完整，缺少用户信息",
                    error_code="AUTH_TOKEN_INVALID",
                )

            # 提取额外字段（排除标准字段）
            excluded_keys = {"id", "sub", "username", "user_type", "exp", "type", "iat"}
            extra_fields = {k: v for k, v in payload.items() if k not in excluded_keys}

            # ✅ 使用通用方法构建 token payload
            token_data = self._build_token_payload(
                str(user_id), str(username), str(user_type), extra_fields
            )

            # 生成新的访问令牌
            access_token = self.jwt_manager.create_access_token(data=token_data)

            # 如果需要自动续期 refresh_token
            new_refresh_token = refresh_data.refresh_token
            if refresh_data.auto_renew:
                new_refresh_token = self.jwt_manager.create_refresh_token(data=token_data)

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

            # ✅ 使用通用方法将旧 token 加入黑名单
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
                "令牌自动续期异常",
                extra={
                    "operation": "auto_refresh_tokens",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="令牌续期失败",
                message_key="error.auth.refresh_error",
                error_code="AUTH_REFRESH_ERROR",
                code=ServiceErrorCodes.AUTH_REFRESH_TOKEN_INVALID,
                http_status_code=400,
            )

    async def introspect_token(self, token: str) -> IntrospectResponse:
        """验证令牌

        Args:
            token: 待验证的令牌

        Returns:
            IntrospectResponse: 令牌验证响应
        """
        try:
            # ✅ 检查令牌黑名单缓存（增强异常处理）
            blacklist_key = f"token_blacklist:{token}"
            try:
                is_blacklisted = await get_cache(blacklist_key)
                if is_blacklisted:
                    logger.debug(
                        "Token 在黑名单中",
                        extra={
                            "blacklist_key": blacklist_key[:50] + "...",
                            "operation": "introspect_token",
                        },
                    )
                    return IntrospectResponse(active=False)
            except Exception as redis_error:
                # ✅ Redis 连接失败时，记录警告但继续验证（降级处理）
                # 不因为 Redis 失败而拒绝所有请求，确保服务可用性
                logger.warning(
                    "Redis 黑名单检查失败，继续验证 token",
                    extra={
                        "operation": "introspect_token",
                        "error": str(redis_error),
                        "error_type": type(redis_error).__name__,
                        "hint": "Redis 不可用时，跳过黑名单检查，继续验证 token",
                    },
                )
                # 继续执行 token 验证，不因为 Redis 失败而拒绝所有请求

            # 验证令牌
            token_preview = token[:20] + "..." if len(token) > 20 else token
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                # ✅ 增强日志：记录 token 验证失败的详细信息
                logger.warning(
                    "Token 验证失败 - JWT 验证返回 None",
                    extra={
                        "operation": "introspect_token",
                        "token_preview": token_preview,
                        "token_length": len(token) if token else 0,
                        "hint": "Token 可能已过期、签名无效、格式错误或被加入黑名单。详细错误信息请查看 JWTManager.verify_token 的日志",
                    },
                )
                return IntrospectResponse(active=False)

            # ✅ 统一使用 id 字段（如果没有则从 sub 提取，兼容旧 token）
            user_id = payload.get("id") or payload.get("sub")
            if not user_id:
                logger.warning(
                    "Token payload 中缺少 id 和 sub 字段",
                    extra={
                        "operation": "introspect_token",
                        "payload_keys": list(payload.keys()),
                        "token_type": payload.get("type"),
                    },
                )
                return IntrospectResponse(active=False)

            # ✅ 转换为字符串避免精度丢失
            user_id = str(user_id)

            # ✅ 增强日志：记录 token 验证成功的详细信息（特别是 device 类型）
            logger.info(
                "Token 验证成功 - 返回用户信息",
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
                id=user_id,  # ✅ 统一字段名为 id
                username=payload.get("username"),
                user_id=user_id,  # 兼容字段
                exp=payload.get("exp"),
                token_type=payload.get("type", "access"),
                # ✅ 新增：返回所有 payload 字段，支持设备登录
                user_type=payload.get("user_type"),
                mg_id=payload.get("mg_id"),
                host_ip=payload.get("host_ip"),
                sub=user_id,  # 兼容字段
            )

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                "令牌验证异常",
                extra={"operation": "introspect_token", "error_type": type(e).__name__, "error_message": str(e)},
                exc_info=True,
            )
            return IntrospectResponse(active=False)

    async def admin_login(self, login_data: AdminLoginRequest) -> LoginResponse:
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
            session_factory = self.session_factory
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
                        http_status_code=401,
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
                    raise BusinessError(
                        message="用户账号已被禁用",
                        message_key="error.auth.user_disabled",
                        error_code="AUTH_USER_DISABLED",
                        code=ServiceErrorCodes.AUTH_USER_INACTIVE,
                        http_status_code=403,
                    )

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
                        http_status_code=401,
                    )

                # 生成访问令牌（统一使用 id 字段）
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "id": str(user.id),  # ✅ 统一字段名为 id
                        "sub": str(user.id),  # 保留 sub 字段以兼容旧 token
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

                # 生成刷新令牌（统一使用 id 字段）
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "id": str(user.id),  # ✅ 统一字段名为 id
                        "sub": str(user.id),  # 保留 sub 字段以兼容旧 token
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
                "管理员登录异常",
                extra={
                    "operation": "admin_login",
                    "username": login_data.username,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="登录服务暂时不可用",
                message_key="error.auth.service_error",
                error_code="AUTH_SERVICE_ERROR",
                code=ServiceErrorCodes.AUTH_OPERATION_FAILED,
                http_status_code=503,
            )
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
            raise BusinessError(
                message="服务器内部错误",
                message_key="error.internal",
                error_code="INTERNAL_SERVER_ERROR",
                code=500,
                http_status_code=500,
            )

    async def device_login(
        self, login_data: DeviceLoginRequest, current_user_id: Optional[int] = None
    ) -> LoginResponse:
        """设备登录（传统方式）

        使用 host_rec 表进行认证，如果 mg_id 存在则更新，不存在则插入

        Args:
            login_data: 设备登录请求数据（mg_id, host_ip, username）
            current_user_id: 当前用户ID（从token获取，可选）

        Returns:
            LoginResponse: 包含 token 的登录响应

        Raises:
            BusinessError: 认证失败时抛出
        """
        try:
            # 获取数据库会话
            session_factory = self.session_factory
            async with session_factory() as db_session:
                # 查询设备记录
                stmt = select(HostRec).where(
                    HostRec.mg_id == login_data.mg_id,
                    HostRec.del_flag == 0,  # 未删除
                )
                result = await db_session.execute(stmt)
                host_rec = result.scalar_one_or_none()

                if host_rec:
                    # 检查设备是否被停用
                    if host_rec.appr_state == 0:
                        logger.warning(
                            "设备已停用",
                            extra={
                                "operation": "device_login",
                                "mg_id": login_data.mg_id,
                                "host_rec_id": host_rec.id,
                            },
                        )
                        raise BusinessError(
                            message="设备已停用，无法登录",
                            error_code="DEVICE_DISABLED",
                            code=403,
                        )

                    # mg_id 存在，更新 host_ip、username 和 updated_by
                    host_rec.host_ip = login_data.host_ip
                    host_rec.host_acct = login_data.username
                    host_rec.updated_time = datetime.now(timezone.utc)
                    host_rec.updated_by = current_user_id  # 设置更新人

                    logger.info(
                        "设备信息更新",
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
                    # mg_id 不存在，插入新记录

                    # 1. 查找默认配置（def_pwd, def_port）
                    conf_stmt = select(SysConf).where(
                        SysConf.conf_key.in_(["def_pwd", "def_port"]),
                        SysConf.del_flag == 0
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

                    # 2. 如果存在默认密码，进行加密
                    # encrypted_pwd = None
                    # if default_pwd:
                    #     try:
                    #         encrypted_pwd = aes_encrypt(default_pwd)
                    #     except Exception as e:
                    #         logger.error(
                    #             "默认密码加密失败",
                    #             extra={"error": str(e), "default_pwd": default_pwd},
                    #         )
                    #         # 加密失败则不设置密码，避免明文存储
                    #         encrypted_pwd = None

                    host_rec = HostRec(
                        mg_id=login_data.mg_id,
                        host_ip=login_data.host_ip,
                        host_acct=login_data.username,
                        host_pwd=default_pwd,  # 设置默认密码（已加密）
                        host_port=default_port,  # 设置默认端口
                        appr_state=2,  # 新增

                        host_state=5,  # 待激活
                        subm_time=datetime.now(timezone.utc),
                        created_by=current_user_id,  # 设置创建人
                        created_time=datetime.now(timezone.utc),
                        updated_by=current_user_id,  # 设置更新人
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
                            "created_by": current_user_id,
                        },
                    )

                # 提交事务
                await db_session.commit()

                # 生成访问令牌（统一使用 id 字段）
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "id": str(host_rec.id),  # ✅ 统一字段名为 id
                        "sub": str(host_rec.id),  # 保留 sub 字段以兼容旧 token
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

                # 生成刷新令牌（统一使用 id 字段）
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "id": str(host_rec.id),  # ✅ 统一字段名为 id
                        "sub": str(host_rec.id),  # 保留 sub 字段以兼容旧 token
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
                "设备登录异常",
                extra={
                    "operation": "device_login",
                    "mg_id": login_data.mg_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="登录服务暂时不可用",
                message_key="error.auth.service_error",
                error_code="AUTH_SERVICE_ERROR",
                code=ServiceErrorCodes.AUTH_OPERATION_FAILED,
                http_status_code=503,
            )

    async def logout(self, token: str) -> bool:
        """用户注销

        Args:
            token: 访问令牌

        Returns:
            bool: 注销是否成功
        """
        try:
            # 验证令牌
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                raise BusinessError(
                    message="令牌无效",
                    message_key="error.auth.token_invalid",
                    error_code="AUTH_INVALID_TOKEN",
                    code=ServiceErrorCodes.AUTH_TOKEN_INVALID,
                    http_status_code=401,
                )

            # 将令牌加入黑名单
            blacklist_key = f"token_blacklist:{token}"
            exp = payload.get("exp", 0)
            ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))

            await set_cache(blacklist_key, True, expire=ttl)

            # 删除会话记录
            session_factory = self.session_factory
            async with session_factory() as db_session:
                stmt = select(UserSession).where(UserSession.access_token == token, ~UserSession.del_flag)
                result = await db_session.execute(stmt)
                user_session = result.scalar_one_or_none()

                if user_session:
                    user_session.del_flag = True
                    await db_session.commit()

            logger.info(
                "用户注销成功",
                extra={"operation": "logout", "user_id": payload.get("sub"), "username": payload.get("username")},
            )
            return True

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError, ConnectionError) as e:
            logger.error(
                "用户注销异常",
                extra={"operation": "logout", "error_type": type(e).__name__, "error_message": str(e)},
                exc_info=True,
            )
            raise BusinessError(
                message="注销失败",
                message_key="error.auth.logout_error",
                error_code="AUTH_LOGOUT_ERROR",
                code=ServiceErrorCodes.AUTH_OPERATION_FAILED,
                http_status_code=400,
            )
