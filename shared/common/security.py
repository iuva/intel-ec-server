"""
Authentication and Security Tools Module

Provides JWT token management, ***REMOVED***word encryption and verification security functions
"""

import base64
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any, Dict, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from ***REMOVED***lib.context import CryptContext

logger = logging.getLogger(__name__)

# Password encryption context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AES encryption configuration
AES_KEY_LENGTH = 32  # AES-256 requires 32-byte key
AES_IV_LENGTH = 16  # AES block size
AES_KEY = os.getenv("AES_ENCRYPTION_KEY", "default_aes_key_32_bytes_long_0123456789").encode()[:AES_KEY_LENGTH]

# If key length is insufficient, use PBKDF2 derivation
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
    """JWT Token Manager

    Provides JWT token creation, verification and refresh functions
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """Initialize JWT manager

        Args:
            secret_key: JWT key
            algorithm: Encryption algorithm
            access_token_expire_minutes: Access token expiration time (minutes)
            refresh_token_expire_days: Refresh token expiration time (days)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create access token

        Args:
            data: Data to encode
            expires_delta: Custom expiration time

        Returns:
            JWT access token
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
            logger.error(f"Failed to create access token: {e!s}")
            raise

    def create_refresh_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create refresh token

        Args:
            data: Data to encode
            expires_delta: Custom expiration time

        Returns:
            JWT refresh token
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
            logger.error(f"Failed to create refresh token: {e!s}")
            raise

    def verify_token(self, token: str, token_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Verify token

        Args:
            token: JWT token
            token_type: Token type (access or refresh)

        Returns:
            Decoded token data, None if verification fails
        """
        token_preview = token[:20] + "..." if len(token) > 20 else token

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify token type
            if token_type and payload.get("type") != token_type:
                logger.warning(
                    "Token type mismatch",
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
            # ✅ Enhanced logging: Record detailed expiration information
            try:
                # Try to decode token to get expiration time information
                decoded = jwt.decode(token, key="", options={"verify_signature": False})
                exp = decoded.get("exp")
                exp_time = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
                current_time = datetime.now(timezone.utc)
            except Exception:
                exp_time = None
                current_time = datetime.now(timezone.utc)

            logger.warning(
                "Token has expired",
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
            # ✅ Enhanced logging: Record JWT errors (including decoding errors and signature errors)
            # Note: In jose library, both decoding errors and signature errors throw JWTError
            error_type = type(e).__name__
            error_message = str(e).lower()
            is_signature_error = "signature" in error_message or "signature" in error_type.lower()
            is_decode_error = "decode" in error_message or "invalid" in error_message or "malformed" in error_message

            # Determine log message based on error type
            if is_signature_error:
                log_message = "Token signature invalid"
                hint = "Token may have been tampered with or signed with wrong key"
            elif is_decode_error:
                log_message = "Token format error, unable to decode"
                hint = "Token format is incorrect, may not be a valid JWT"
            else:
                log_message = "JWT verification failed"
                hint = "Token verification failed, may be format error, signature error or other JWT related issue"

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
            # ✅ Enhanced logging: Record unknown errors (non-JWT related exceptions)
            logger.error(
                "Token verification failed - Unknown error",
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
        """Decode token (without verifying signature)

        Args:
            token: JWT token

        Returns:
            Decoded token data
        """
        try:
            return jwt.decode(token, key="", options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Failed to decode token: {e!s}")
            return None


# Global JWT manager instance
_jwt_manager: Optional[JWTManager] = None


def init_jwt_manager(
    secret_key: str,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
) -> JWTManager:
    """Initialize global JWT manager

    Args:
        secret_key: JWT key
        algorithm: Encryption algorithm
        access_token_expire_minutes: Access token expiration time (minutes)
        refresh_token_expire_days: Refresh token expiration time (days)

    Returns:
        JWT manager instance
    """
    global _jwt_manager
    _jwt_manager = JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )
    logger.info("JWT manager initialized successfully")
    return _jwt_manager


def get_jwt_manager() -> JWTManager:
    """Get global JWT manager

    Returns:
        JWT manager instance

    Raises:
        RuntimeError: If JWT manager is not initialized
    """
    if _jwt_manager is None:
        raise RuntimeError("JWT manager not initialized, please call init_jwt_manager() first")
    return _jwt_manager


def hash_***REMOVED***word(***REMOVED***word: str) -> str:
    """Hash ***REMOVED***word

    Args:
        ***REMOVED***word: Plain text ***REMOVED***word

    Returns:
        Hashed ***REMOVED***word
    """
    return pwd_context.hash(***REMOVED***word)


def verify_***REMOVED***word(plain_***REMOVED***word: str, hashed_***REMOVED***word: str) -> bool:
    """Verify ***REMOVED***word

    Args:
        plain_***REMOVED***word: Plain text ***REMOVED***word
        hashed_***REMOVED***word: Hashed ***REMOVED***word

    Returns:
        Whether ***REMOVED***words match
    """
    try:
        return pwd_context.verify(plain_***REMOVED***word, hashed_***REMOVED***word)
    except Exception as e:
        logger.error(f"Failed to verify ***REMOVED***word: {e!s}")
        return False


def get_***REMOVED***word_hash(***REMOVED***word: str) -> str:
    """Get ***REMOVED***word hash (alias for hash_***REMOVED***word)

    Args:
        ***REMOVED***word: Plain text ***REMOVED***word

    Returns:
        Hashed ***REMOVED***word
    """
    return hash_***REMOVED***word(***REMOVED***word)


def aes_encrypt(plaintext: str) -> str:
    """AES encryption function

    Encrypts plaintext using AES-256-CBC mode

    Args:
        plaintext: Plain text string

    Returns:
        Encrypted Base64 encoded string

    Raises:
        Exception: Thrown when encryption fails
    """
    try:
        # Generate random IV
        iv = os.urandom(AES_IV_LENGTH)

        # Create encryptor
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Add PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8"))
        padded_data += padder.finalize()

        # Encrypt
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Combine IV and ciphertext, then Base64 encode
        encrypted_data = iv + ciphertext
        return base64.b64encode(encrypted_data).decode("utf-8")

    except Exception as e:
        logger.error(f"AES encryption failed: {e!s}")
        raise


def aes_decrypt(ciphertext: str) -> Optional[str]:
    """AES decryption function

    Decrypt ciphertext using AES-256-CBC mode

    Args:
        ciphertext: Base64 encoded ciphertext string

    Returns:
        Decrypted plaintext string, None if decryption fails

    Raises:
        Exception: Thrown when decryption fails
    """
    try:
        # Base64 decode
        encrypted_data = base64.b64decode(ciphertext.encode("utf-8"))

        # Extract IV and ciphertext
        iv = encrypted_data[:AES_IV_LENGTH]
        ciphertext_bytes = encrypted_data[AES_IV_LENGTH:]

        # Create decryptor
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt
        padded_data = decryptor.update(ciphertext_bytes) + decryptor.finalize()

        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data)
        plaintext += unpadder.finalize()

        return plaintext.decode("utf-8")

    except Exception as e:
        logger.error(f"AES decryption failed: {e!s}")
        return None
