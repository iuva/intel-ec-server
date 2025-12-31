"""
认证和安全工具模块

提供JWT令牌管理、密码加密和验证等安全功能
"""

import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from ***REMOVED***lib.context import CryptContext

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AES 加密配置
AES_KEY_LENGTH = 32  # AES-256 需要 32 字节密钥
AES_IV_LENGTH = 16  # AES 块大小
AES_KEY = os.getenv("AES_ENCRYPTION_KEY", "default_aes_key_32_bytes_long_0123456789").encode()[:AES_KEY_LENGTH]

# 如果密钥长度不足，使用 PBKDF2 派生
if len(AES_KEY) < AES_KEY_LENGTH:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_LENGTH,
        salt=b"intel_ec_salt_2025",
        iterations=100000,
        backend=default_backend(),
    )
    AES_KEY = kdf.derive(AES_KEY)


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
        token_preview = token[:20] + "..." if len(token) > 20 else token

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 验证令牌类型
            if token_type and payload.get("type") != token_type:
                logger.warning(
                    "令牌类型不匹配",
                    extra={
                        "expected_type": token_type,
                        "actual_type": payload.get("type"),
                        "token_preview": token_preview,
                        "operation": "verify_token",
                    },
                )
                return None

            return payload

        except ExpiredSignatureError as e:
            # ✅ 增强日志：记录详细的过期信息
            try:
                # 尝试解码 token 获取过期时间信息
                decoded = jwt.decode(token, key="", options={"verify_signature": False})
                exp = decoded.get("exp")
                exp_time = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
                current_time = datetime.now(timezone.utc)
            except Exception:
                exp_time = None
                current_time = datetime.now(timezone.utc)

            logger.warning(
                "令牌已过期",
                extra={
                    "token_preview": token_preview,
                    "operation": "verify_token",
                    "error_type": "ExpiredSignatureError",
                    "error_message": str(e),
                    "exp_time": exp_time.isoformat() if exp_time else None,
                    "current_time": current_time.isoformat(),
                    "expired_seconds_ago": (current_time - exp_time).total_seconds() if exp_time else None,
                },
            )
            return None
        except JWTError as e:
            # ✅ 增强日志：记录 JWT 错误（包括解码错误和签名错误）
            # 注意：jose 库中，解码错误和签名错误都会抛出 JWTError
            error_type = type(e).__name__
            error_message = str(e).lower()
            is_signature_error = "signature" in error_message or "signature" in error_type.lower()
            is_decode_error = "decode" in error_message or "invalid" in error_message or "malformed" in error_message

            # 根据错误类型确定日志消息
            if is_signature_error:
                log_message = "令牌签名无效"
                hint = "令牌可能被篡改或使用了错误的密钥签名"
            elif is_decode_error:
                log_message = "令牌格式错误，无法解码"
                hint = "令牌格式不正确，可能不是有效的 JWT"
            else:
                log_message = "JWT 验证失败"
                hint = "令牌验证失败，可能是格式错误、签名错误或其他 JWT 相关问题"

            logger.warning(
                log_message,
                extra={
                    "token_preview": token_preview,
                    "operation": "verify_token",
                    "error_type": error_type,
                    "error_message": str(e),
                    "is_signature_error": is_signature_error,
                    "is_decode_error": is_decode_error,
                    "hint": hint,
                },
            )
            return None
        except Exception as e:
            # ✅ 增强日志：记录未知错误（非 JWT 相关异常）
            logger.error(
                "验证令牌失败 - 未知错误",
                extra={
                    "token_preview": token_preview,
                    "operation": "verify_token",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
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


def aes_encrypt(plaintext: str) -> str:
    """AES 加密函数

    使用 AES-256-CBC 模式加密明文

    Args:
        plaintext: 明文字符串

    Returns:
        加密后的 Base64 编码字符串

    Raises:
        Exception: 加密失败时抛出异常
    """
    try:
        # 生成随机 IV
        iv = os.urandom(AES_IV_LENGTH)

        # 创建加密器
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # 添加 PKCS7 填充
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8"))
        padded_data += padder.finalize()

        # 加密
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # 将 IV 和密文组合，然后 Base64 编码
        encrypted_data = iv + ciphertext
        return base64.b64encode(encrypted_data).decode("utf-8")

    except Exception as e:
        logger.error(f"AES 加密失败: {e!s}")
        raise


def aes_decrypt(ciphertext: str) -> Optional[str]:
    """AES 解密函数

    使用 AES-256-CBC 模式解密密文

    Args:
        ciphertext: Base64 编码的密文字符串

    Returns:
        解密后的明文字符串，解密失败返回 None

    Raises:
        Exception: 解密失败时抛出异常
    """
    try:
        # Base64 解码
        encrypted_data = base64.b64decode(ciphertext.encode("utf-8"))

        # 提取 IV 和密文
        iv = encrypted_data[:AES_IV_LENGTH]
        ciphertext_bytes = encrypted_data[AES_IV_LENGTH:]

        # 创建解密器
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # 解密
        padded_data = decryptor.update(ciphertext_bytes) + decryptor.finalize()

        # 去除 PKCS7 填充
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data)
        plaintext += unpadder.finalize()

        return plaintext.decode("utf-8")

    except Exception as e:
        logger.error(f"AES 解密失败: {e!s}")
        return None
