"""
Gateway Service 自定义异常
"""

from typing import Any, Dict, Optional


class GatewayError(Exception):
    """网关异常基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "GATEWAY_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ServiceNotFoundError(GatewayError):
    """服务不存在异常"""

    def __init__(self, service_name: str):
        super().__init__(
            message=f"服务不存在: {service_name}",
            error_code="SERVICE_NOT_FOUND",
            details={"service_name": service_name},
        )


class ServiceUnavailableError(GatewayError):
    """服务不可用异常"""

    def __init__(self, service_name: str, reason: str = ""):
        super().__init__(
            message=f"服务不可用: {service_name}",
            error_code="SERVICE_UNAVAILABLE",
            details={"service_name": service_name, "reason": reason},
        )


class AuthenticationError(GatewayError):
    """认证失败异常"""

    def __init__(self, message: str = "认证失败"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
        )


class RateLimitExceededError(GatewayError):
    """限流异常"""

    def __init__(self, message: str = "请求频率超过限制"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
        )
