"""
认证服务业务逻辑

实现用户登录、令牌生成、令牌验证等功能
"""

from datetime import datetime, timezone
import os

from sqlalchemy import select

from app.models.host_rec import HostRec
from app.models.sys_user import SysUser
from app.models.user_session import UserSession
from app.schemas.auth import (
    AdminLoginRequest,
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
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.cache import get_cache, set_cache
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
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


logger = get_logger(__name__)


class AuthService:
    """认证服务类"""

    def __init__(self):
        """初始化认证服务"""
        self.jwt_manager = JWTManager(
            secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
            algorithm="HS256",
        )
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

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

            user_id = payload.get("sub")
            username = payload.get("username")

            # 生成新的访问令牌
            access_token = self.jwt_manager.create_access_token(data={"sub": user_id, "username": username})

            logger.info("令牌刷新成功", extra={"operation": "refresh_token", "user_id": user_id, "username": username})

            token_type = "bearer"
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_data.refresh_token,
                token_type=token_type,
                expires_in=self.access_token_expire_minutes * 60,
            )

        except BusinessError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                "令牌刷新异常",
                extra={"operation": "refresh_token", "error_type": type(e).__name__, "error_message": str(e)},
                exc_info=True,
            )
            raise BusinessError(message="令牌刷新失败", error_code="AUTH_REFRESH_ERROR")

    async def introspect_token(self, token: str) -> IntrospectResponse:
        """验证令牌

        Args:
            token: 待验证的令牌

        Returns:
            IntrospectResponse: 令牌验证响应
        """
        try:
            # 检查令牌黑名单缓存
            blacklist_key = f"token_blacklist:{token}"
            is_blacklisted = await get_cache(blacklist_key)
            if is_blacklisted:
                return IntrospectResponse(active=False)

            # 验证令牌
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                return IntrospectResponse(active=False)

            return IntrospectResponse(
                active=True,
                username=payload.get("username"),
                user_id=int(payload.get("sub", 0)),
                exp=payload.get("exp"),
                token_type=payload.get("type", "access"),
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
                if not verify_admin_***REMOVED***word(login_data.***REMOVED***word, user.user_pwd):
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

                token_type = "bearer"
                return LoginResponse(
                    token=access_token,
                    token_type=token_type,
                    expires_in=self.access_token_expire_minutes * 60,
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

                token_type = "bearer"
                return LoginResponse(
                    token=access_token,
                    token_type=token_type,
                    expires_in=self.access_token_expire_minutes * 60,
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

        Args:
            token: 访问令牌

        Returns:
            bool: 注销是否成功
        """
        try:
            # 验证令牌
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                raise BusinessError(message="令牌无效", error_code="AUTH_INVALID_TOKEN")

            # 将令牌加入黑名单
            blacklist_key = f"token_blacklist:{token}"
            exp = payload.get("exp", 0)
            ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))

            await set_cache(blacklist_key, True, expire=ttl)

            # 删除会话记录
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                stmt = select(UserSession).where(UserSession.access_token == token, not UserSession.is_deleted)
                result = await db_session.execute(stmt)
                user_session = result.scalar_one_or_none()

                if user_session:
                    user_session.is_deleted = True
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
            raise BusinessError(message="注销失败", error_code="AUTH_LOGOUT_ERROR")
