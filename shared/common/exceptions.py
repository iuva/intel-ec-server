"""
异常处理模块

提供统一的业务异常类和错误码定义
"""

from typing import Any, Dict, Optional


class BusinessError(Exception):
    """业务异常基类

    用于所有业务逻辑相关的异常
    """

    def __init__(
        self,
        message: str,
        code: int = 400,
        error_code: str = "BUSINESS_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """初始化业务异常

        Args:
            message: 错误消息
            code: HTTP状态码
            error_code: 错误类型标识
            details: 错误详情
        """
        self.message = message
        self.code = code
        self.error_code = error_code  # 改名为 error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.error_code}: {self.message}"

    def __repr__(self) -> str:
        return f"BusinessError(code={self.code}, error_code='{self.error_code}', message='{self.message}')"


class ErrorCode:
    """业务错误码定义 - 按模块分类"""

    # ==================== 网关相关错误 ====================
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # ==================== 认证授权错误 ====================
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    MISSING_TOKEN = "MISSING_TOKEN"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"  # 无效的认证凭证
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"  # 令牌已过期
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"  # 无效的令牌
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"  # 权限不足
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"  # 用户不存在
    AUTH_USER_INACTIVE = "AUTH_USER_INACTIVE"  # 用户未激活
    AUTH_PASSWORD_INCORRECT = "AUTH_PASSWORD_INCORRECT"  # 密码错误
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"  # 缺少令牌
    AUTH_REFRESH_TOKEN_INVALID = "AUTH_REFRESH_TOKEN_INVALID"  # 无效的刷新令牌

    # ==================== 用户相关错误 ====================
    USER_NOT_FOUND = "USER_NOT_FOUND"  # 用户不存在
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"  # 用户已存在
    USER_INACTIVE = "USER_INACTIVE"  # 用户未激活
    USER_CREATE_FAILED = "USER_CREATE_FAILED"  # 用户创建失败
    USER_UPDATE_FAILED = "USER_UPDATE_FAILED"  # 用户更新失败
    USER_DELETE_FAILED = "USER_DELETE_FAILED"  # 用户删除失败
    USER_EMAIL_EXISTS = "USER_EMAIL_EXISTS"  # 邮箱已存在
    USER_USERNAME_EXISTS = "USER_USERNAME_EXISTS"  # 用户名已存在

    # ==================== 数据验证错误 ====================
    VALIDATION_ERROR = "VALIDATION_ERROR"  # 数据验证失败
    VALIDATION_FIELD_REQUIRED = "VALIDATION_FIELD_REQUIRED"  # 必填字段缺失
    VALIDATION_FIELD_INVALID = "VALIDATION_FIELD_INVALID"  # 字段格式无效
    VALIDATION_FIELD_TOO_LONG = "VALIDATION_FIELD_TOO_LONG"  # 字段长度超限
    VALIDATION_FIELD_TOO_SHORT = "VALIDATION_FIELD_TOO_SHORT"  # 字段长度不足
    PARAMETER_INVALID = "PARAMETER_INVALID"  # 参数无效
    REQUEST_BODY_INVALID = "REQUEST_BODY_INVALID"  # 请求体无效

    # ==================== 资源错误 ====================
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"  # 资源不存在
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"  # 资源已存在
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"  # 资源冲突
    RESOURCE_LOCKED = "RESOURCE_LOCKED"  # 资源被锁定
    RESOURCE_EXPIRED = "RESOURCE_EXPIRED"  # 资源已过期

    # =================== 系统错误 ====================
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"  # 系统内部错误
    DATABASE_ERROR = "DATABASE_ERROR"  # 数据库错误
    CACHE_ERROR = "CACHE_ERROR"  # 缓存错误
    NETWORK_ERROR = "NETWORK_ERROR"  # 网络错误
    TIMEOUT_ERROR = "TIMEOUT_ERROR"  # 超时错误
    CONFIG_ERROR = "CONFIG_ERROR"  # 配置错误

    # ==================== 业务逻辑错误 ====================
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"  # 业务规则违反
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"  # 操作不允许
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"  # 余额不足
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"  # 配额超限
    DUPLICATE_OPERATION = "DUPLICATE_OPERATION"  # 重复操作

    # ==================== 外部服务错误 ====================
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"  # 外部服务错误
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"  # 外部服务超时
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"  # 外部服务不可用

    # ==================== 文件相关错误 ====================
    FILE_NOT_FOUND = "FILE_NOT_FOUND"  # 文件不存在
    FILE_TOO_LARGE = "FILE_TOO_LARGE"  # 文件过大
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"  # 文件类型不允许
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"  # 文件上传失败
    FILE_DOWNLOAD_FAILED = "FILE_DOWNLOAD_FAILED"  # 文件下载失败


# 向后兼容：保留旧的 ErrorType 类名
ErrorType = ErrorCode


class AuthenticationError(BusinessError):
    """认证异常

    用于认证相关的错误
    """

    def __init__(
        self,
        message: str = "认证失败",
        code: int = 401,
        error_code: str = ErrorCode.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


class AuthorizationError(BusinessError):
    """授权异常

    用于权限相关的错误
    """

    def __init__(
        self,
        message: str = "权限不足",
        code: int = 403,
        error_code: str = ErrorCode.FORBIDDEN,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


class ValidationError(BusinessError):
    """验证异常

    用于数据验证相关的错误
    """

    def __init__(
        self,
        message: str = "数据验证失败",
        code: int = 422,
        error_code: str = ErrorCode.VALIDATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


class ResourceNotFoundError(BusinessError):
    """资源不存在异常

    用于资源查找失败的错误
    """

    def __init__(
        self,
        message: str = "资源不存在",
        code: int = 404,
        error_code: str = ErrorCode.RESOURCE_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


class ResourceConflictError(BusinessError):
    """资源冲突异常

    用于资源冲突的错误
    """

    def __init__(
        self,
        message: str = "资源冲突",
        code: int = 409,
        error_code: str = ErrorCode.RESOURCE_CONFLICT,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


class DatabaseError(BusinessError):
    """数据库异常

    用于数据库操作相关的错误
    """

    def __init__(
        self,
        message: str = "数据库错误",
        code: int = 500,
        error_code: str = ErrorCode.DATABASE_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


class ServiceUnavailableError(BusinessError):
    """服务不可用异常

    用于服务不可用的错误
    """

    def __init__(
        self,
        message: str = "服务暂时不可用",
        code: int = 503,
        error_code: str = ErrorCode.SERVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, error_code, details)


# ==================== 网关专用异常类 ====================


class GatewayError(BusinessError):
    """网关异常基类"""

    def __init__(
        self,
        message: str,
        code: int = 500,
        error_code: str = ErrorCode.GATEWAY_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, error_code, details)


class ServiceNotFoundError(GatewayError):
    """服务不存在异常"""

    def __init__(self, service_name: str):
        super().__init__(
            message=f"服务不存在: {service_name}",
            code=404,
            error_code=ErrorCode.SERVICE_NOT_FOUND,
            details={"service_name": service_name},
        )


class RateLimitExceededError(GatewayError):
    """限流异常"""

    def __init__(self, message: str = "请求频率超过限制"):
        super().__init__(message=message, code=429, error_code=ErrorCode.RATE_LIMIT_EXCEEDED)
