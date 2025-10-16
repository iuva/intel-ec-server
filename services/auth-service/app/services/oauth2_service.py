"""
OAuth 2.0认证服务

实现OAuth 2.0标准的密码授权和客户端凭据授权
"""

from datetime import datetime, timedelta, timezone
import os
from typing import Optional
import uuid

from app.models.device import Device
from app.models.oauth_client import OAuthClient
from app.models.sys_user import SysUser
from app.models.user_session import UserSession

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager, verify_***REMOVED***word
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager, verify_***REMOVED***word

from sqlalchemy import select

logger = get_logger(__name__)


class OAuth2Service:
    """OAuth 2.0认证服务"""

    def __init__(self):
        """初始化OAuth 2.0服务"""
        self.jwt_manager = JWTManager(
            secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
            algorithm="HS256",
        )
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    async def authenticate_client(self, client_id: str, client_secret: str) -> Optional[OAuthClient]:
        """验证OAuth客户端

        Args:
            client_id: 客户端ID
            client_secret: 客户端密钥

        Returns:
            OAuthClient: 客户端对象或None
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 查询客户端
                stmt = select(OAuthClient).where(OAuthClient.client_id == client_id, OAuthClient.is_active)
                result = await db_session.execute(stmt)
                client = result.scalar_one_or_none()

                if not client:
                    logger.warning(f"OAuth客户端不存在: {client_id}")
                    return None

                # 验证客户端密钥
                if not verify_***REMOVED***word(client_secret, client.client_secret_hash):
                    logger.warning(f"OAuth客户端密钥错误: {client_id}")
                    return None

                return client

        except Exception as e:
            logger.error(f"客户端验证异常: {e!s}")
            return None

    async def handle_admin_***REMOVED***word_grant(
        self, client_id: str, username: str, ***REMOVED***word: str, scope: str = "admin"
    ) -> dict:
        """处理管理后台密码授权

        Args:
            client_id: 客户端ID
            username: 用户名
            ***REMOVED***word: 密码
            scope: 授权范围

        Returns:
            dict: 令牌响应

        Raises:
            BusinessError: 认证失败时抛出
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 验证客户端权限（必须支持***REMOVED***word授权）
                client = await self.authenticate_client(client_id, os.getenv("ADMIN_CLIENT_SECRET") or "")
                if not client:
                    raise BusinessError("无效的客户端凭据", error_code="INVALID_CLIENT")

                if "***REMOVED***word" not in (client.grant_types or []):
                    raise BusinessError("客户端不支持密码授权", error_code="UNSUPPORTED_GRANT_TYPE")

                # 查询管理后台用户
                stmt = select(SysUser).where(
                    SysUser.user_account == username,
                    SysUser.del_flag == 0,
                )
                result = await db_session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"管理后台用户不存在: {username}")
                    raise BusinessError("用户名或密码错误", error_code="INVALID_CREDENTIALS")

                # 检查用户状态
                if user.state_flag == 1:  # 停用状态
                    logger.warning(f"管理后台用户已被停用: {username}")
                    raise BusinessError("用户账号已被禁用", error_code="ACCOUNT_DISABLED")

                # 验证密码
                if not verify_***REMOVED***word(***REMOVED***word, user.user_pwd):
                    logger.warning(f"管理后台用户密码错误: {username}")
                    raise BusinessError("用户名或密码错误", error_code="INVALID_CREDENTIALS")

                # 生成令牌
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "sub": str(user.id),
                        "username": user.user_account,
                        "client_id": client_id,
                        "scope": scope,
                        "user_type": "admin",
                        "permissions": ["admin", "read", "write"],
                    }
                )
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "sub": str(user.id),
                        "username": user.user_account,
                        "client_id": client_id,
                        "scope": scope,
                        "user_type": "admin",
                    }
                )

                # 创建会话
                session_id = str(uuid.uuid4())
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

                user_session = UserSession(
                    entity_id=user.id,
                    entity_type="admin_user",
                    session_id=session_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    client_ip=None,  # OAuth 2.0中可能没有IP信息
                    expires_at=expires_at,
                )

                db_session.add(user_session)
                await db_session.commit()

                logger.info(f"OAuth管理后台认证成功: {user.user_account}")

                return {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": self.access_token_expire_minutes * 60,
                    "refresh_token": refresh_token,
                    "scope": scope,
                    "client_id": client_id,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(f"OAuth管理后台认证异常: {e!s}")
            raise BusinessError("认证服务暂时不可用", error_code="AUTH_SERVICE_ERROR")

    async def handle_device_client_credentials_grant(
        self, client_id: str, device_id: str, device_secret: str, scope: str = "device"
    ) -> dict:
        """处理设备客户端凭据授权

        Args:
            client_id: 客户端ID
            device_id: 设备ID
            device_secret: 设备密钥
            scope: 授权范围

        Returns:
            dict: 令牌响应

        Raises:
            BusinessError: 认证失败时抛出
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 验证客户端权限（必须支持client_credentials授权）
                client = await self.authenticate_client(client_id, os.getenv("DEVICE_CLIENT_SECRET") or "")
                if not client:
                    raise BusinessError("无效的客户端凭据", error_code="INVALID_CLIENT")

                if "client_credentials" not in (client.grant_types or []):
                    raise BusinessError("客户端不支持客户端凭据授权", error_code="UNSUPPORTED_GRANT_TYPE")

                # 查询设备
                stmt = select(Device).where(
                    Device.device_id == device_id,
                    Device.del_flag == 0,
                )
                result = await db_session.execute(stmt)
                device = result.scalar_one_or_none()

                if not device:
                    logger.warning(f"设备不存在: {device_id}")
                    raise BusinessError("设备不存在", error_code="DEVICE_NOT_FOUND")

                # 检查设备状态
                if not device.is_active:
                    logger.warning(f"设备已被禁用: {device_id}")
                    raise BusinessError("设备已被禁用", error_code="DEVICE_DISABLED")

                # 验证设备密钥
                if not verify_***REMOVED***word(device_secret, device.device_secret_hash):
                    logger.warning(f"设备密钥错误: {device_id}")
                    raise BusinessError("设备凭据无效", error_code="INVALID_DEVICE_CREDENTIALS")

                # 更新设备最后在线时间
                device.last_seen = datetime.now(timezone.utc)
                db_session.add(device)

                # 生成令牌
                access_token = self.jwt_manager.create_access_token(
                    data={
                        "sub": str(device.id),
                        "device_id": device.device_id,
                        "client_id": client_id,
                        "scope": scope,
                        "user_type": "device",
                        "permissions": device.permissions or ["device"],
                        "host_ip": device.host_ip,
                    }
                )
                refresh_token = self.jwt_manager.create_refresh_token(
                    data={
                        "sub": str(device.id),
                        "device_id": device.device_id,
                        "client_id": client_id,
                        "scope": scope,
                        "user_type": "device",
                    }
                )

                # 创建会话
                session_id = str(uuid.uuid4())
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

                device_session = UserSession(
                    entity_id=device.id,
                    entity_type="device",
                    session_id=session_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    client_ip=device.host_ip,
                    expires_at=expires_at,
                )

                db_session.add(device_session)
                await db_session.commit()

                logger.info(f"OAuth设备认证成功: {device.device_id}")

                return {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": self.access_token_expire_minutes * 60,
                    "refresh_token": refresh_token,
                    "scope": scope,
                    "client_id": client_id,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(f"OAuth设备认证异常: {e!s}")
            raise BusinessError("认证服务暂时不可用", error_code="AUTH_SERVICE_ERROR")

    async def introspect_token(self, token: str) -> dict:
        """OAuth 2.0令牌内省

        Args:
            token: 要验证的令牌

        Returns:
            dict: 令牌内省响应
        """
        try:
            # 验证JWT令牌
            payload = self.jwt_manager.verify_token(token)

            if not payload:
                return {"active": False}

            # 检查令牌是否过期
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return {"active": False}

            # 返回令牌详细信息
            return {
                "active": True,
                "client_id": payload.get("client_id", "unknown"),
                "username": payload.get("username"),
                "device_id": payload.get("device_id"),
                "scope": payload.get("scope", "read"),
                "token_type": "Bearer",
                "exp": exp,
                "iat": payload.get("iat"),
                "sub": payload.get("sub"),
                "user_type": payload.get("user_type"),
                "permissions": payload.get("permissions", []),
                "roles": payload.get("roles", []),
            }

        except Exception as e:
            logger.error(f"令牌内省异常: {e!s}")
            return {"active": False}

    async def revoke_token(self, token: str) -> bool:
        """撤销令牌

        Args:
            token: 要撤销的令牌

        Returns:
            bool: 是否成功撤销
        """
        try:
            # 解析令牌获取会话信息
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                return False

            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 查找并删除会话
                stmt = select(UserSession).where(UserSession.access_token == token)
                result = await db_session.execute(stmt)
                session = result.scalar_one_or_none()

                if session:
                    db_session.delete(session)
                    await db_session.commit()
                    logger.info(f"令牌已撤销: {payload.get('sub')}")
                    return True

                return False

        except Exception as e:
            logger.error(f"撤销令牌异常: {e!s}")
            return False
