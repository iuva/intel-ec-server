"""Proxy service error handling module

Provides error handling and exception conversion functionality for proxy requests.

Extracted from proxy_service.py to improve code maintainability.
ProxyService should directly use functions from this module to avoid code duplication.
"""

import os
import sys

# Use try-except to handle path imports
try:
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def log_backend_error(
    service_name: str,
    method: str,
    path: str,
    error_type: str,
    error: str,
    exc_info: bool = True,
) -> None:
    """Log backend service error

    Args:
        service_name: Service name
        method: HTTP method
        path: Request path
        error_type: Error type
        error: Error message
        exc_info: Whether to include exception stack information
    """
    logger.error(
        f"Backend service error: {service_name} - {error_type}",
        extra={
            "service_name": service_name,
            "method": method,
            "path": path,
            "error_type": error_type,
            "error": error,
        },
        exc_info=exc_info,
    )


def raise_connection_error(service_name: str, error: Exception, locale: str = "zh_CN") -> None:
    """Raise connection error

    Args:
        service_name: Service name
        error: Original exception
        locale: Language preference

    Raises:
        BusinessError: Connection error
    """
    log_backend_error(service_name, "", "", "CONNECTION_ERROR", str(error))
    raise BusinessError(
        message=t("error.service.connection_failed", locale=locale, service_name=service_name),
        message_key="error.service.connection_failed",
        error_code="GATEWAY_CONNECTION_FAILED",
        code=ServiceErrorCodes.GATEWAY_CONNECTION_FAILED,
        http_status_code=502,
        locale=locale,
        details={"original_error": str(error), "service_name": service_name},
    )


def raise_timeout_error(service_name: str, error: Exception, locale: str = "zh_CN") -> None:
    """Raise timeout error

    Args:
        service_name: Service name
        error: Original exception
        locale: Language preference

    Raises:
        BusinessError: Timeout error
    """
    log_backend_error(service_name, "", "", "TIMEOUT_ERROR", str(error))
    raise BusinessError(
        message=t("error.service.timeout_error", locale=locale, service_name=service_name),
        message_key="error.service.timeout_error",
        error_code="GATEWAY_TIMEOUT",
        code=ServiceErrorCodes.GATEWAY_TIMEOUT,
        http_status_code=504,
        locale=locale,
        details={"original_error": str(error), "service_name": service_name, "timeout": True},
    )


def raise_network_error(service_name: str, error: Exception, locale: str = "zh_CN") -> None:
    """Raise network error

    Args:
        service_name: Service name
        error: Original exception
        locale: Language preference

    Raises:
        BusinessError: Network error
    """
    log_backend_error(service_name, "", "", "NETWORK_ERROR", str(error))
    raise BusinessError(
        message=t("error.service.network_error", locale=locale, service_name=service_name),
        message_key="error.service.network_error",
        error_code="GATEWAY_NETWORK_ERROR",
        code=ServiceErrorCodes.GATEWAY_NETWORK_ERROR,
        http_status_code=502,
        locale=locale,
        details={"original_error": str(error), "service_name": service_name},
    )


def raise_protocol_error(service_name: str, error: Exception, locale: str = "zh_CN") -> None:
    """Raise protocol error

    Args:
        service_name: Service name
        error: Original exception
        locale: Language preference

    Raises:
        BusinessError: Protocol error
    """
    error_type = type(error).__name__
    log_backend_error(service_name, "", "", "PROTOCOL_ERROR", str(error))
    raise BusinessError(
        message=t("error.service.protocol_error", locale=locale, service_name=service_name),
        message_key="error.service.protocol_error",
        error_code="GATEWAY_PROTOCOL_ERROR",
        code=ServiceErrorCodes.GATEWAY_PROTOCOL_ERROR,
        http_status_code=502,
        locale=locale,
        details={"original_error": str(error), "error_type": error_type, "service_name": service_name},
    )


def raise_service_not_found_error(service_name: str, locale: str = "zh_CN") -> None:
    """Raise service not found error

    Args:
        service_name: Service name
        locale: Language preference

    Raises:
        BusinessError: Service not found error
    """
    raise BusinessError(
        message=t("error.proxy.service_not_found", locale=locale, service_name=service_name),
        message_key="error.proxy.service_not_found",
        error_code="SERVICE_NOT_FOUND",
        code=ServiceErrorCodes.GATEWAY_SERVICE_NOT_FOUND,
        http_status_code=503,
        locale=locale,
        details={"service_name": service_name},
    )


def raise_websocket_connection_limit_error(
    current_connections: int,
    max_connections: int,
    locale: str = "zh_CN",
) -> None:
    """Raise WebSocket connection limit error

    Args:
        current_connections: Current connection count
        max_connections: Maximum connection count
        locale: Language preference

    Raises:
        BusinessError: Connection limit error
    """
    raise BusinessError(
        message=t("error.websocket.connection_limit_reached", locale=locale),
        message_key="error.websocket.connection_limit_reached",
        error_code="WEBSOCKET_CONNECTION_LIMIT_REACHED",
        code=ServiceErrorCodes.GATEWAY_SERVICE_UNAVAILABLE,
        http_status_code=503,
        locale=locale,
        details={
            "current_connections": current_connections,
            "max_connections": max_connections,
        },
    )


def raise_websocket_error(
    service_name: str,
    path: str,
    error: Exception,
    locale: str = "zh_CN",
) -> None:
    """Raise WebSocket error

    Args:
        service_name: Service name
        path: Request path
        error: Original exception
        locale: Language preference

    Raises:
        BusinessError: WebSocket error
    """
    raise BusinessError(
        message=t("error.websocket.forward_failed", locale=locale, service_name=service_name),
        message_key="error.websocket.forward_failed",
        error_code="WEBSOCKET_FORWARD_FAILED",
        code=ServiceErrorCodes.GATEWAY_WEBSOCKET_ERROR,
        http_status_code=502,
        locale=locale,
        details={"service_name": service_name, "path": path, "error": str(error)},
    )


def parse_backend_error_response(
    status_code: int,
    response_body: bytes,
    service_name: str,
    locale: str = "zh_CN",
) -> dict:
    """Parse backend error response

    Args:
        status_code: HTTP status code
        response_body: Response body
        service_name: Service name
        locale: Language preference

    Returns:
        dict: Parsed error information
    """
    import json

    try:
        error_data = json.loads(response_body.decode("utf-8"))
        return {
            "status_code": status_code,
            "message": error_data.get("message", "Unknown error"),
            "error_code": error_data.get("error_code", "UNKNOWN_ERROR"),
            "details": error_data.get("details"),
        }
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "status_code": status_code,
            "message": f"Service {service_name} returned error ({status_code})",
            "error_code": "BACKEND_ERROR",
            "details": None,
        }


def is_retryable_error(error: Exception) -> bool:
    """Determine if error is retryable

    Args:
        error: Exception object

    Returns:
        bool: Whether error is retryable
    """
    # Connection errors and timeout errors are usually retryable
    error_type = type(error).__name__
    retryable_errors = {
        "ConnectError",
        "TimeoutException",
        "ConnectionResetError",
        "ConnectionRefusedError",
    }
    return error_type in retryable_errors
