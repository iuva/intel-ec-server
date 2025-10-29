"""
认证和安全工具模块

提供JWT令牌管理、密码加密和验证等安全功能
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from ***REMOVED***lib.context import CryptContext

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTManager:
    """JWT令牌管理器

    提供JWT令牌的创建、验证和刷新功能
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """初始化JWT管理器

        Args:
            secret_key: JWT密钥
            algorithm: 加密算法
            access_token_expire_minutes: 访问令牌过期时间（分钟）
            refresh_token_expire_minutes: 刷新令牌过期时间（天）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT访问令牌
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "type": "access", "iat": datetime.now(timezone.utc)})

        try:
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"创建访问令牌失败: {e!s}")
            raise

    def create_refresh_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建刷新令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT刷新令牌
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({"exp": expire, "type": "refresh", "iat": datetime.now(timezone.utc)})

        try:
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"创建刷新令牌失败: {e!s}")
            raise

    def verify_token(self, token: str, token_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """验证令牌

        Args:
            token: JWT令牌
            token_type: 令牌类型（access或refresh）

        Returns:
            解码后的令牌数据，验证失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 验证令牌类型
            if token_type and payload.get("type") != token_type:
                logger.warning(f"令牌类型不匹配: 期望{token_type}, 实际{payload.get('type')}")
                return None

            return payload

        except jwt.ExpiredSignatureError:  # type: ignore[attr-defined]
            logger.warning("令牌已过期")
            return None
        except jwt.JWTError:  # type: ignore[attr-defined]
            logger.warning("无效的令牌")
            return None
        except Exception as e:
            logger.error(f"验证令牌失败: {e!s}")
            return None

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌（不验证签名）

        Args:
            token: JWT令牌

        Returns:
            解码后的令牌数据
        """
        try:
            return jwt.decode(token, key="", options={"verify_signature": False})
        except Exception as e:
            logger.error(f"解码令牌失败: {e!s}")
            return None


# 全局JWT管理器实例
_jwt_manager: Optional[JWTManager] = None


def init_jwt_manager(
    secret_key: str,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
) -> JWTManager:
    """初始化全局JWT管理器

    Args:
        secret_key: JWT密钥
        algorithm: 加密算法
        access_token_expire_minutes: 访问令牌过期时间（分钟）
        refresh_token_expire_days: 刷新令牌过期时间（天）

    Returns:
        JWT管理器实例
    """
    global _jwt_manager
    _jwt_manager = JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )
    logger.info("JWT管理器初始化成功")
    return _jwt_manager


def get_jwt_manager() -> JWTManager:
    """获取全局JWT管理器

    Returns:
        JWT管理器实例

    Raises:
        RuntimeError: 如果JWT管理器未初始化
    """
    if _jwt_manager is None:
        raise RuntimeError("JWT管理器未初始化，请先调用init_jwt_manager()")
    return _jwt_manager


def hash_***REMOVED***word(***REMOVED***word: str) -> str:
    """加密密码

    Args:
        ***REMOVED***word: 明文密码

    Returns:
        加密后的密码哈希
    """
    return pwd_context.hash(***REMOVED***word)


def verify_***REMOVED***word(plain_***REMOVED***word: str, hashed_***REMOVED***word: str) -> bool:
    """验证密码

    Args:
        plain_***REMOVED***word: 明文密码
        hashed_***REMOVED***word: 加密后的密码哈希

    Returns:
        密码是否匹配
    """
    try:
        return pwd_context.verify(plain_***REMOVED***word, hashed_***REMOVED***word)
    except Exception as e:
        logger.error(f"验证密码失败: {e!s}")
        return False


def get_***REMOVED***word_hash(***REMOVED***word: str) -> str:
    """获取密码哈希（hash_***REMOVED***word的别名）

    Args:
        ***REMOVED***word: 明文密码

    Returns:
        加密后的密码哈希
    """
    return hash_***REMOVED***word(***REMOVED***word)
