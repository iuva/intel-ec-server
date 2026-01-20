"""
Exception handling module

Provides unified business exception classes and error code definitions
Supports multilingual messages
"""

import os
import sys
from typing import Any, Dict, Optional

try:
    from shared.common.i18n import t
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.i18n import t


class BusinessError(Exception):
    """Business exception base class

    Used for all business logic related exceptions
    Supports multilingual messages (automatic translation via message_key)
    """

    def __init__(
        self,
        message: str,
        error_code: str = "BUSINESS_ERROR",
        code: int = 400,
        http_status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        message_key: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> None:
        """Initialize business exception

        Args:
            message: Error message (if message_key is provided, message serves as default)
            error_code: Error type identifier (custom error code, can be any integer, e.g., 53009)
            code: Custom business error code (for response body)
            http_status_code: HTTP status code (for HTTP response, must be valid HTTP status code 100-599)
                             If not provided, code will be used as HTTP status code
            details: Error details
            message_key: Translation key (if provided, message will be automatically translated)
            locale: Language code (for translating message_key)
        """
        self.message_key = message_key
        self.locale = locale or "en_US"

        # If message_key exists, translate automatically
        if message_key:
            # Extract formatting variables from details
            message_kwargs = details or {}
            translated_message = t(message_key, locale=self.locale, default=message, **message_kwargs)
            self.message = translated_message
        else:
            self.message = message

        self.error_code = error_code  # Error code identifier
        self.code = code  # Custom error code (in response body)
        # Ensure http_status_code is a valid HTTP status code
        if http_status_code is None:
            # If code is a valid HTTP status code, use code; otherwise default to 400
            self.http_status_code = code if 100 <= code < 600 else 400
        else:
            # Ensure the provided status code is valid
            self.http_status_code = http_status_code if 100 <= http_status_code < 600 else 400
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.error_code}: {self.message}"

    def __repr__(self) -> str:
        return f"BusinessError(code={self.code}, error_code='{self.error_code}', message='{self.message}')"


# ==================== Error Code Prefix Definitions ====================


class ErrorCodePrefix:
    """Service-level error code prefix definitions"""

    GATEWAY = 10000  # Gateway service (10001-10999)
    AUTH = 51000  # Authentication service (51001-51999)
    ADMIN = 52000  # Management service (52001-52999)
    HOST = 53000  # Host service (53001-53999)


class ServiceErrorCodes:
    """Microservice unified error code generator"""

    # Gateway service error codes (10001-10999)
    GATEWAY_SERVICE_NOT_FOUND = 10001  # Service does not exist
    GATEWAY_SERVICE_UNAVAILABLE = 10002  # Service unavailable
    GATEWAY_CONNECTION_FAILED = 10003  # Backend connection failed
    GATEWAY_TIMEOUT = 10004  # Backend timeout
    GATEWAY_NETWORK_ERROR = 10005  # Backend network error
    GATEWAY_PROTOCOL_ERROR = 10006  # Backend protocol error (e.g., RemoteProtocolError)
    GATEWAY_INVALID_RESPONSE = 10007  # Backend response invalid
    GATEWAY_RATE_LIMITED = 10008  # Request rate limit exceeded
    GATEWAY_PROXY_ERROR = 10009  # Proxy forwarding error
    GATEWAY_INTERNAL_ERROR = 10010  # Gateway internal error
    GATEWAY_AUTH_FAILED = 10011  # WebSocket authentication failed (403)
    GATEWAY_UNAUTHORIZED = 10012  # WebSocket unauthorized (401)

    # Authentication service error codes (51001-51999)
    AUTH_INVALID_CREDENTIALS = 51001  # Invalid credentials
    AUTH_TOKEN_EXPIRED = 51002  # Token expired
    AUTH_TOKEN_INVALID = 51003  # Invalid token
    AUTH_PERMISSION_DENIED = 51004  # Permission denied
    AUTH_USER_NOT_FOUND = 51005  # User not found
    AUTH_USER_INACTIVE = 51006  # User inactive
    AUTH_PASSWORD_INCORRECT = 51007  # Password incorrect
    AUTH_TOKEN_MISSING = 51008  # Missing token
    AUTH_REFRESH_TOKEN_INVALID = 51009  # Invalid refresh token
    AUTH_SESSION_EXPIRED = 51010  # Session expired
    AUTH_CLIENT_INVALID = 51011  # Invalid client
    AUTH_OPERATION_FAILED = 51012  # Authentication operation failed

    # Management service error codes (52001-52999)
    ADMIN_USER_NOT_FOUND = 52001  # User not found
    ADMIN_USER_ALREADY_EXISTS = 52002  # User already exists
    ADMIN_USER_CREATE_FAILED = 52003  # User creation failed
    ADMIN_USER_UPDATE_FAILED = 52004  # User update failed
    ADMIN_USER_DELETE_FAILED = 52005  # User deletion failed
    ADMIN_USER_INACTIVE = 52006  # User inactive
    ADMIN_PERMISSION_DENIED = 52007  # Permission denied
    ADMIN_INVALID_ROLE = 52008  # Invalid role
    ADMIN_ROLE_NOT_FOUND = 52009  # Role not found
    ADMIN_OPERATION_FAILED = 52010  # Management operation failed
    ADMIN_CONFIG_ERROR = 52011  # Configuration error
    ADMIN_INVALID_REQUEST = 52012  # Invalid request

    # Host service error codes (53001-53999)
    HOST_NOT_FOUND = 53001  # Host not found
    HOST_ALREADY_EXISTS = 53002  # Host already exists
    HOST_CREATE_FAILED = 53003  # Host creation failed
    HOST_UPDATE_FAILED = 53004  # Host update failed
    HOST_DELETE_FAILED = 53005  # Host deletion failed
    HOST_CONNECTION_FAILED = 53006  # Host connection failed
    HOST_OPERATION_TIMEOUT = 53007  # Host operation timeout
    HOST_INVALID_STATE = 53008  # Host state invalid
    HOST_HARDWARE_API_ERROR = 53009  # Hardware API error
    HOST_HARDWARE_API_TIMEOUT = 53034  # ✅ Hardware API call timeout
    HOST_HARDWARE_API_CIRCUIT_BREAKER_OPEN = 53035  # ✅ Hardware API circuit breaker open
    HOST_VNC_CONNECTION_FAILED = 53010  # VNC connection failed
    HOST_VNC_INFO_NOT_FOUND = 53011  # VNC information not found
    HOST_OPERATION_FAILED = 53012  # Host operation failed
    HOST_AGENT_OFFLINE = 53013  # Agent offline
    HOST_INVALID_REQUEST = 53014  # Invalid request
    FILE_NOT_FOUND = 53015  # File not found
    HOST_VNC_STATE_MISMATCH = 53016  # VNC connection successful but host state mismatch
    HOST_OTA_UPDATE_RECORD_NOT_FOUND = 53017  # OTA update record not found
    HOST_OTA_CONFIG_NOT_FOUND = 53018  # OTA configuration not found
    HOST_VNC_GET_FAILED = 53019  # Failed to get VNC connection information
    HOST_VNC_CONNECTION_REPORT_FAILED = 53020  # VNC connection status reporting processing failed
    HOST_OTA_UPDATE_STATUS_REPORT_FAILED = 53021  # OTA update status reporting processing failed
    HOST_AGENT_VER_REQUIRED = 53022  # Agent version required
    HOST_INVALID_HOST_ID = 53023  # Invalid host ID format
    HOST_MISSING_DMR_CONFIG = 53024  # Missing DMR configuration
    HOST_MISSING_REVISION = 53025  # Missing revision
    HOST_HARDWARE_TEMPLATE_NOT_FOUND = 53026  # Hardware template not found
    HOST_HARDWARE_REPORT_FAILED = 53027  # Hardware information reporting failed
    HOST_UPDATE_HARDWARE_FAILED = 53028  # Updating hardware record failed
    HOST_TESTCASE_REPORT_FAILED = 53029  # Test case result reporting failed
    HOST_DUE_TIME_UPDATE_FAILED = 53030  # Expected end time reporting failed
    HOST_VNC_INFO_IN_COMPLETE = 53031  # VNC connection information incomplete
    HOST_REALVNC_ENCRYPTION_LIBRARY_MISSING = 53032  # RealVNC encryption library missing
    HOST_MULTIPLE_EXEC_LOGS_FOUND = 53033  # Multiple execution logs found


class ErrorCode:
    """Business error code definitions - classified by module (preserved for backward compatibility)"""

    # ==================== Gateway Related Errors ====================
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # ==================== Authentication and Authorization Errors ====================
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    MISSING_TOKEN = "MISSING_TOKEN"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"  # Invalid credentials
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"  # Token expired
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"  # Invalid token
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"  # Permission denied
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"  # User not found
    AUTH_USER_INACTIVE = "AUTH_USER_INACTIVE"  # User inactive
    AUTH_PASSWORD_INCORRECT = "AUTH_PASSWORD_INCORRECT"  # Password incorrect
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"  # Missing token
    AUTH_REFRESH_TOKEN_INVALID = "AUTH_REFRESH_TOKEN_INVALID"  # Invalid refresh token

    # ==================== User Related Errors ====================
    USER_NOT_FOUND = "USER_NOT_FOUND"  # User not found
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"  # User already exists
    USER_INACTIVE = "USER_INACTIVE"  # User inactive
    USER_CREATE_FAILED = "USER_CREATE_FAILED"  # User creation failed
    USER_UPDATE_FAILED = "USER_UPDATE_FAILED"  # User update failed
    USER_DELETE_FAILED = "USER_DELETE_FAILED"  # User deletion failed
    USER_EMAIL_EXISTS = "USER_EMAIL_EXISTS"  # Email already exists
    USER_USERNAME_EXISTS = "USER_USERNAME_EXISTS"  # Username already exists

    # ==================== Data Validation Errors ====================
    VALIDATION_ERROR = "VALIDATION_ERROR"  # Data validation failed
    VALIDATION_FIELD_REQUIRED = "VALIDATION_FIELD_REQUIRED"  # Required field missing
    VALIDATION_FIELD_INVALID = "VALIDATION_FIELD_INVALID"
    VALIDATION_FIELD_TOO_LONG = "VALIDATION_FIELD_TOO_LONG"  # Field length exceeded
    VALIDATION_FIELD_TOO_SHORT = "VALIDATION_FIELD_TOO_SHORT"  # Field length insufficient
    PARAMETER_INVALID = "PARAMETER_INVALID"  # Parameter invalid
    REQUEST_BODY_INVALID = "REQUEST_BODY_INVALID"  # Request body invalid

    # ==================== Resource Errors ====================
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"  # Resource does not exist
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"  # Resource already exists
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"  # Resource conflict
    RESOURCE_LOCKED = "RESOURCE_LOCKED"  # Resource locked
    RESOURCE_EXPIRED = "RESOURCE_EXPIRED"  # Resource expired

    # =================== System Errors ====================
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"  # Internal server error
    DATABASE_ERROR = "DATABASE_ERROR"  # Database error
    CACHE_ERROR = "CACHE_ERROR"  # Cache error
    NETWORK_ERROR = "NETWORK_ERROR"  # Network error
    TIMEOUT_ERROR = "TIMEOUT_ERROR"  # Timeout error
    CONFIG_ERROR = "CONFIG_ERROR"  # Configuration error

    # ==================== Business Logic Errors ====================
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"  # Business rule violation
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"  # Operation not allowed
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"  # Insufficient balance
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"  # Quota exceeded
    DUPLICATE_OPERATION = "DUPLICATE_OPERATION"  # Duplicate operation

    # ==================== External Service Errors ====================
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"  # External service error
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"  # External service timeout
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"  # External service unavailable

    # ==================== File Related Errors ====================
    FILE_NOT_FOUND = "FILE_NOT_FOUND"  # File does not exist
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"  # File type not allowed
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"  # File upload failed
    FILE_DOWNLOAD_FAILED = "FILE_DOWNLOAD_FAILED"  # File download failed


# Backward compatibility: Preserve the old ErrorType class name
ErrorType = ErrorCode


class AuthenticationError(BusinessError):
    """Authentication exception

    Used for authentication related errors
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        code: int = 401,
        error_code: str = ErrorCode.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, details=details)


class AuthorizationError(BusinessError):
    """Authorization exception

    Used for permission related errors
    """

    def __init__(
        self,
        message: str = "Insufficient permissions",
        code: int = 403,
        error_code: str = ErrorCode.FORBIDDEN,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, details=details)


class ValidationError(BusinessError):
    """Validation exception

    Used for data validation related errors
    """

    def __init__(
        self,
        message: str = "Data validation failed",
        code: int = 422,
        error_code: str = ErrorCode.VALIDATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, details=details)


class ResourceNotFoundError(BusinessError):
    """Resource not found exception

    Used for resource lookup failure errors
    """

    def __init__(
        self,
        message: str = "Resource does not exist",
        code: int = 404,
        error_code: str = ErrorCode.RESOURCE_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, details=details)


class ResourceConflictError(BusinessError):
    """Resource conflict exception

    Used for resource conflict errors
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        code: int = 409,
        error_code: str = ErrorCode.RESOURCE_CONFLICT,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, details=details)


class DatabaseError(BusinessError):
    """Database exception

    Used for database operation related errors
    """

    def __init__(
        self,
        message: str = "Database error",
        code: int = 500,
        error_code: str = ErrorCode.DATABASE_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, details=details)


class ServiceUnavailableError(BusinessError):
    """Service unavailable exception

    Used for service unavailable errors
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        code: int = 503,
        error_code: str = ErrorCode.SERVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code=error_code, code=code, http_status_code=503, details=details)


# ==================== Gateway Specific Exception Classes ====================


class GatewayError(BusinessError):
    """Gateway exception base class"""

    def __init__(
        self,
        message: str,
        code: int = 500,
        error_code: str = ErrorCode.GATEWAY_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code=error_code, code=code, http_status_code=500, details=details)


class ServiceNotFoundError(GatewayError):
    """Service not found exception"""

    def __init__(self, service_name: str):
        super().__init__(
            message=f"Service does not exist: {service_name}",
            code=ServiceErrorCodes.GATEWAY_SERVICE_NOT_FOUND,
            error_code=ErrorCode.SERVICE_NOT_FOUND,
            details={"service_name": service_name},
        )
        # Use business error code, set HTTP status code to 400 (business logic error rather than resource not found)
        self.http_status_code = 400


class RateLimitExceededError(GatewayError):
    """Rate limit exceeded exception"""

    def __init__(self, message: str = "Request frequency exceeded limit"):
        super().__init__(message=message, code=429, error_code=ErrorCode.RATE_LIMIT_EXCEEDED)
        # Override http_status_code to 429
        self.http_status_code = 429
