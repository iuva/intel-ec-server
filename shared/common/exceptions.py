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
        error_code: str = "BUSINESS_ERROR",
        code: int = 400,
        http_status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """初始化业务异常

        Args:
            message: 错误消息
            error_code: 错误类型标识（自定义错误码，可以是任意整数，如 53009）
            code: 自定义业务错误码（用于响应体）
            http_status_code: HTTP状态码（用于HTTP响应，必须是有效的HTTP状态码 100-599）
                             如果不提供，将使用 code 作为 HTTP 状态码
            details: 错误详情
        """
        self.message = message
        self.error_code = error_code  # 错误码标识
        self.code = code  # 自定义错误码（在响应体中）
        # 确保 http_status_code 是有效的 HTTP 状态码
        if http_status_code is None:
            # 如果 code 是有效的 HTTP 状态码，使用 code；否则默认为 400
            self.http_status_code = code if 100 <= code < 600 else 400
        else:
            # 确保提供的状态码是有效的
            self.http_status_code = http_status_code if 100 <= http_status_code < 600 else 400
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.error_code}: {self.message}"

    def __repr__(self) -> str:
        return f"BusinessError(code={self.code}, error_code='{self.error_code}', message='{self.message}')"


# ==================== 错误码前缀定义 ====================


class ErrorCodePrefix:
    """服务级错误码前缀定义"""

    GATEWAY = 10000  # 网关服务 (10001-10999)
    AUTH = 51000  # 认证服务 (51001-51999)
    ADMIN = 52000  # 管理服务 (52001-52999)
    HOST = 53000  # 主机服务 (53001-53999)


class ServiceErrorCodes:
    """微服务统一错误码生成器"""

    # 网关服务错误码 (10001-10999)
    GATEWAY_SERVICE_NOT_FOUND = 10001  # 服务不存在
    GATEWAY_SERVICE_UNAVAILABLE = 10002  # 服务不可用
    GATEWAY_CONNECTION_FAILED = 10003  # 后端连接失败
    GATEWAY_TIMEOUT = 10004  # 后端超时
    GATEWAY_NETWORK_ERROR = 10005  # 后端网络错误
    GATEWAY_PROTOCOL_ERROR = 10006  # 后端协议错误（如RemoteProtocolError）
    GATEWAY_INVALID_RESPONSE = 10007  # 后端响应无效
    GATEWAY_RATE_LIMITED = 10008  # 请求频率限制
    GATEWAY_PROXY_ERROR = 10009  # 代理转发错误
    GATEWAY_INTERNAL_ERROR = 10010  # 网关内部错误
    GATEWAY_AUTH_FAILED = 10011  # WebSocket 认证失败（403）
    GATEWAY_UNAUTHORIZED = 10012  # WebSocket 未授权（401）

    # 认证服务错误码 (51001-51999)
    AUTH_INVALID_CREDENTIALS = 51001  # 无效的认证凭证
    AUTH_TOKEN_EXPIRED = 51002  # 令牌已过期
    AUTH_TOKEN_INVALID = 51003  # 无效的令牌
    AUTH_PERMISSION_DENIED = 51004  # 权限不足
    AUTH_USER_NOT_FOUND = 51005  # 用户不存在
    AUTH_USER_INACTIVE = 51006  # 用户未激活
    AUTH_PASSWORD_INCORRECT = 51007  # 密码错误
    AUTH_TOKEN_MISSING = 51008  # 缺少令牌
    AUTH_REFRESH_TOKEN_INVALID = 51009  # 无效的刷新令牌
    AUTH_SESSION_EXPIRED = 51010  # 会话已过期
    AUTH_CLIENT_INVALID = 51011  # 无效的客户端
    AUTH_OPERATION_FAILED = 51012  # 认证操作失败

    # 管理服务错误码 (52001-52999)
    ADMIN_USER_NOT_FOUND = 52001  # 用户不存在
    ADMIN_USER_ALREADY_EXISTS = 52002  # 用户已存在
    ADMIN_USER_CREATE_FAILED = 52003  # 用户创建失败
    ADMIN_USER_UPDATE_FAILED = 52004  # 用户更新失败
    ADMIN_USER_DELETE_FAILED = 52005  # 用户删除失败
    ADMIN_USER_INACTIVE = 52006  # 用户未激活
    ADMIN_PERMISSION_DENIED = 52007  # 权限不足
    ADMIN_INVALID_ROLE = 52008  # 无效的角色
    ADMIN_ROLE_NOT_FOUND = 52009  # 角色不存在
    ADMIN_OPERATION_FAILED = 52010  # 管理操作失败
    ADMIN_CONFIG_ERROR = 52011  # 配置错误
    ADMIN_INVALID_REQUEST = 52012  # 无效的请求

    # 主机服务错误码 (53001-53999)
    HOST_NOT_FOUND = 53001  # 主机不存在
    HOST_ALREADY_EXISTS = 53002  # 主机已存在
    HOST_CREATE_FAILED = 53003  # 主机创建失败
    HOST_UPDATE_FAILED = 53004  # 主机更新失败
    HOST_DELETE_FAILED = 53005  # 主机删除失败
    HOST_CONNECTION_FAILED = 53006  # 主机连接失败
    HOST_OPERATION_TIMEOUT = 53007  # 主机操作超时
    HOST_INVALID_STATE = 53008  # 主机状态无效
    HOST_HARDWARE_API_ERROR = 53009  # 硬件API错误
    HOST_VNC_CONNECTION_FAILED = 53010  # VNC连接失败
    HOST_VNC_INFO_NOT_FOUND = 53011  # VNC信息不存在
    HOST_OPERATION_FAILED = 53012  # 主机操作失败
    HOST_AGENT_OFFLINE = 53013  # Agent离线
    HOST_INVALID_REQUEST = 53014  # 无效的请求


class ErrorCode:
    """业务错误码定义 - 按模块分类 (保留用于向后兼容)"""

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
    VALIDATION_FIELD_INVALID = "VALIDATION_FIELD_INVALID"
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
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
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
        super().__init__(message, error_code=error_code, code=code, details=details)


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
        super().__init__(message, error_code=error_code, code=code, details=details)


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
        super().__init__(message, error_code=error_code, code=code, details=details)


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
        super().__init__(message, error_code=error_code, code=code, details=details)


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
        super().__init__(message, error_code=error_code, code=code, details=details)


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
        super().__init__(message, error_code=error_code, code=code, details=details)


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
        super().__init__(message, error_code=error_code, code=code, http_status_code=503, details=details)


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
        super().__init__(message, error_code=error_code, code=code, http_status_code=500, details=details)


class ServiceNotFoundError(GatewayError):
    """服务不存在异常"""

    def __init__(self, service_name: str):
        super().__init__(
            message=f"服务不存在: {service_name}",
            code=ServiceErrorCodes.GATEWAY_SERVICE_NOT_FOUND,
            error_code=ErrorCode.SERVICE_NOT_FOUND,
            details={"service_name": service_name},
        )
        # 使用业务错误码，HTTP 状态码设为 400（业务逻辑错误而非资源不存在）
        self.http_status_code = 400


class RateLimitExceededError(GatewayError):
    """限流异常"""

    def __init__(self, message: str = "请求频率超过限制"):
        super().__init__(message=message, code=429, error_code=ErrorCode.RATE_LIMIT_EXCEEDED)
        # 覆盖 http_status_code 为 429
        self.http_status_code = 429
