"""
Gateway Service custom exceptions
"""

from typing import Any, Dict, Optional


class GatewayError(Exception):
    """
    Gateway exception base class
    """

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
    """
    Service not found exception
    """

    def __init__(self, service_name: str):
        super().__init__(
            message=f"Service not found: {service_name}",
            error_code="SERVICE_NOT_FOUND",
            details={"service_name": service_name},
        )


class ServiceUnavailableError(GatewayError):
    """
    Service unavailable exception
    """

    def __init__(self, service_name: str, reason: str = ""):
        super().__init__(
            message=f"Service unavailable: {service_name}",
            error_code="SERVICE_UNAVAILABLE",
            details={"service_name": service_name, "reason": reason},
        )


class AuthenticationError(GatewayError):
    """
    Authentication failure exception
    """

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
        )


class RateLimitExceededError(GatewayError):
    """
    Rate limit exception
    """

    def __init__(self, message: str = "Request rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
        )
