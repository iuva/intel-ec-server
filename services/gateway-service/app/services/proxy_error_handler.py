"""代理服务错误处理模块

提供代理请求的错误处理和异常转换功能。

从 proxy_service.py 拆分出来，提高代码可维护性。
ProxyService 应该直接使用此模块中的函数，避免重复代码。
"""

import os
import sys

# 使用 try-except 方式处理路径导入
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
    """记录后端服务错误日志

    Args:
        service_name: 服务名称
        method: HTTP 方法
        path: 请求路径
        error_type: 错误类型
        error: 错误信息
        exc_info: 是否包含异常堆栈信息
    """
    logger.error(
        f"后端服务错误: {service_name} - {error_type}",
        extra={
            "service_name": service_name,
            "method": method,
            "path": path,
            "error_type": error_type,
            "error": error,
        },
        exc_info=exc_info,
    )


def raise_connection_error(
    service_name: str, error: Exception, locale: str = "zh_CN"
) -> None:
    """抛出连接错误

    Args:
        service_name: 服务名称
        error: 原始异常
        locale: 语言偏好

    Raises:
        BusinessError: 连接错误
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


def raise_timeout_error(
    service_name: str, error: Exception, locale: str = "zh_CN"
) -> None:
    """抛出超时错误

    Args:
        service_name: 服务名称
        error: 原始异常
        locale: 语言偏好

    Raises:
        BusinessError: 超时错误
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


def raise_network_error(
    service_name: str, error: Exception, locale: str = "zh_CN"
) -> None:
    """抛出网络错误

    Args:
        service_name: 服务名称
        error: 原始异常
        locale: 语言偏好

    Raises:
        BusinessError: 网络错误
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


def raise_protocol_error(
    service_name: str, error: Exception, locale: str = "zh_CN"
) -> None:
    """抛出协议错误

    Args:
        service_name: 服务名称
        error: 原始异常
        locale: 语言偏好

    Raises:
        BusinessError: 协议错误
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


def raise_service_not_found_error(
    service_name: str, locale: str = "zh_CN"
) -> None:
    """抛出服务不存在错误

    Args:
        service_name: 服务名称
        locale: 语言偏好

    Raises:
        BusinessError: 服务不存在错误
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
    """抛出 WebSocket 连接数限制错误

    Args:
        current_connections: 当前连接数
        max_connections: 最大连接数
        locale: 语言偏好

    Raises:
        BusinessError: 连接数限制错误
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
    """抛出 WebSocket 错误

    Args:
        service_name: 服务名称
        path: 请求路径
        error: 原始异常
        locale: 语言偏好

    Raises:
        BusinessError: WebSocket 错误
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
    """解析后端错误响应

    Args:
        status_code: HTTP 状态码
        response_body: 响应体
        service_name: 服务名称
        locale: 语言偏好

    Returns:
        dict: 解析后的错误信息
    """
    import json

    try:
        error_data = json.loads(response_body.decode("utf-8"))
        return {
            "status_code": status_code,
            "message": error_data.get("message", "未知错误"),
            "error_code": error_data.get("error_code", "UNKNOWN_ERROR"),
            "details": error_data.get("details"),
        }
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "status_code": status_code,
            "message": f"服务 {service_name} 返回错误 ({status_code})",
            "error_code": "BACKEND_ERROR",
            "details": None,
        }


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试

    Args:
        error: 异常对象

    Returns:
        bool: 是否可重试
    """
    # 连接错误和超时错误通常可以重试
    error_type = type(error).__name__
    retryable_errors = {
        "ConnectError",
        "TimeoutException",
        "ConnectionResetError",
        "ConnectionRefusedError",
    }
    return error_type in retryable_errors
