"""
Decorator module

Provides unified error handling, monitoring and logging decorators
"""

import asyncio
import time
<<<<<<< HEAD
<<<<<<< HEAD
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
=======
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
)
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
>>>>>>> 45558e6 (docs(websocket): 更新WebSocket认证方式和状态管理文档)

try:
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.monitoring.metrics import metrics_collector
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.monitoring.metrics import metrics_collector

logger = get_logger(__name__)

<<<<<<< HEAD
# Type variable
T = TypeVar("T")

# Constants
DEFAULT_ERROR_MESSAGE = "Operation failed"
DEFAULT_ERROR_CODE = "OPERATION_FAILED"
DEFAULT_LOCALE = "zh_CN"
INTERNAL_ERROR_CODE = "INTERNAL_ERROR"
INTERNAL_ERROR_MESSAGE = "Internal server error"


def _log_service_error(func_name: str, error: Exception, args: tuple, kwargs: dict) -> None:
    """Log service layer errors

    Args:
        func_name: Function name
        error: Exception object
        args: Function arguments (tuple)
        kwargs: Function keyword arguments (dict)
    """
    # Get stack trace information
    tb = traceback.extract_tb(error.__traceback__)
    error_location = None
    if tb:
        # Get the last frame (actual error location)
        last_frame = tb[-1]
        error_location = {
            "filename": last_frame.filename,
            "lineno": last_frame.lineno,
            "function": last_frame.name,
            "code": last_frame.line,
        }

    # Build detailed error information
    extra: Dict[str, Any] = {
        "function": func_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    # Add error location information
    if error_location:
        extra["error_location"] = error_location
        extra["error_file"] = error_location["filename"]
        extra["error_line"] = error_location["lineno"]
        extra["error_code_line"] = error_location["code"]

    # If it's BusinessError, log detailed information
    if isinstance(error, BusinessError):
        extra.update(
            {
                "error_code": error.error_code,
                "business_code": error.code,
                "http_status_code": error.http_status_code,
                "message": error.message,
                "message_key": error.message_key,
                "locale": error.locale,
                "details": error.details,
            }
        )

    # Extract key information from function parameters (e.g., host_id, agent_id, etc.)
    # Skip self parameter
    if len(args) > 1:
        # Try to extract common parameter names
        for i, arg in enumerate(args[1:], start=1):
            if isinstance(arg, str) and (arg.isdigit() or len(arg) > 10):
                # Might be an ID parameter
                extra[f"arg_{i}"] = arg
            elif isinstance(arg, (int, float, bool)):
                extra[f"arg_{i}"] = arg

    # Extract key information from kwargs
    for key, value in kwargs.items():
        if key in ("host_id", "agent_id", "user_id", "service_name", "path"):
            extra[key] = value
        elif isinstance(value, (str, int, float, bool, type(None))):
            # Only record simple type values, avoid recording complex objects
            extra[f"kwarg_{key}"] = value

    # Record complete parameter information (for debugging)
    extra["args_count"] = len(args) - 1 if len(args) > 1 else 0
    extra["kwargs_count"] = len(kwargs)

    # Build detailed error message
    error_msg = f"{func_name} execution failed: {type(error).__name__} - {error!s}"
    if error_location:
        error_msg += (
            f"\nError location: {error_location['filename']}:{error_location['lineno']} in {error_location['function']}"
        )
        if error_location["code"]:
            error_msg += f"\nCode line: {error_location['code'].strip()}"

    # ✅ Log complete stack trace information (explicitly ***REMOVED*** exception object and stack trace)
    logger.error(
        error_msg,
        extra=extra,
        exc_info=(type(error), error, error.__traceback__),  # Explicitly ***REMOVED*** exception type, object and stack trace
    )


def _create_business_error(error: Exception, error_message: str, error_code: str) -> BusinessError:
    """Create business exception object

    Args:
        error: Original exception
        error_message: Error message
        error_code: Error code

    Returns:
        BusinessError object
    """
    return BusinessError(
        message=error_message,
        error_code=error_code,
        code=HTTP_500_INTERNAL_SERVER_ERROR,
        details={"original_error": str(error), "error_type": type(error).__name__},
    )


def handle_service_errors(
    error_message: str = DEFAULT_ERROR_MESSAGE,
    error_code: str = DEFAULT_ERROR_CODE,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Service layer error handling decorator

    Used for unified error handling in service layer methods, capturing exceptions and converting them to BusinessError.
    Applicable to all business logic methods in the service layer.

    Args:
        error_message: Default error message used when unexpected exceptions occur
        error_code: Default error code used when unexpected exceptions occur

    Returns:
        Decorator function

    Usage example:
        ```python
        @handle_service_errors(
            error_message="Failed to create host"
            error_code="HOST_CREATE_FAILED"
        )
        async def create_host(self, host_data: HostCreate) -> Host:
            # Business logic
=======
# 类型变量
T = TypeVar("T")


def handle_service_errors(
    error_message: str = "操作失败",
    error_code: str = "OPERATION_FAILED",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """服务层错误处理装饰器

    用于服务层方法的统一错误处理，捕获异常并转换为 BusinessError。
    适用于所有服务层的业务逻辑方法。

    Args:
        error_message: 默认错误消息，当发生未预期异常时使用
        error_code: 默认错误码，当发生未预期异常时使用

    Returns:
        装饰器函数

    使用示例:
        ```python
        @handle_service_errors(
            error_message="创建主机失败",
            error_code="HOST_CREATE_FAILED"
        )
        async def create_host(self, host_data: HostCreate) -> Host:
            # 业务逻辑
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            async with mariadb_manager.get_session() as session:
                host = Host(**host_data.model_dump())
                session.add(host)
                await session.commit()
                return host
        ```

<<<<<<< HEAD
    Note:
        - BusinessError will be re-raised directly, not converted
        - Other exceptions will be caught and converted to BusinessError
        - All exceptions will be logged
=======
    注意:
        - BusinessError 会被直接重新抛出，不会被转换
        - 其他异常会被捕获并转换为 BusinessError
        - 所有异常都会被记录到日志中
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
<<<<<<< HEAD
            except BusinessError:
                # Re-raise business exception without conversion
                raise
            except Exception as e:
                _log_service_error(func.__name__, e, args, kwargs)
                raise _create_business_error(e, error_message, error_code)
=======

            except BusinessError:
                # 重新抛出业务异常，不做转换
                raise

            except Exception as e:
                # 记录系统异常
                logger.error(
                    f"{func.__name__} 执行失败",
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "args": str(args[1:]) if len(args) > 1 else "",  # 跳过 self
                        "kwargs": str(kwargs),
                    },
                    exc_info=True,
                )

                # 转换为业务异常
                raise BusinessError(
                    message=error_message,
                    error_code=error_code,
                    code=HTTP_500_INTERNAL_SERVER_ERROR,
                    details={"original_error": str(e), "error_type": type(e).__name__},
                )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
<<<<<<< HEAD
            except BusinessError:
                # Re-raise business exception without conversion
                raise
            except Exception as e:
                _log_service_error(func.__name__, e, args, kwargs)
                raise _create_business_error(e, error_message, error_code)

        # Return the corresponding wrapper based on function type
=======

            except BusinessError:
                # 重新抛出业务异常，不做转换
                raise

            except Exception as e:
                # 记录系统异常
                logger.error(
                    f"{func.__name__} 执行失败",
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "args": str(args[1:]) if len(args) > 1 else "",  # 跳过 self
                        "kwargs": str(kwargs),
                    },
                    exc_info=True,
                )

                # 转换为业务异常
                raise BusinessError(
                    message=error_message,
                    error_code=error_code,
                    code=HTTP_500_INTERNAL_SERVER_ERROR,
                    details={"original_error": str(e), "error_type": type(e).__name__},
                )

        # 根据函数类型返回对应的包装器
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


<<<<<<< HEAD
def _build_error_response_kwargs(error: BusinessError, api_locale: Optional[str] = None) -> Dict[str, Any]:
    """Build error response parameters dictionary

    Args:
        error: Business exception object
        api_locale: Locale for API layer (optional)

    Returns:
        Error response parameters dictionary
    """
    # Prioritize API layer locale, otherwise use locale from exception, finally use default value
    locale = api_locale or error.locale or DEFAULT_LOCALE

    error_response_kwargs: Dict[str, Any] = {
        "code": error.code,  # Use custom error code as the code in the response body
        "message": error.message,
        "error_code": error.error_code,
        "details": error.details or {},
    }

    if error.message_key:
        error_response_kwargs["message_key"] = error.message_key
        error_response_kwargs["locale"] = locale
        # Extract formatting variables (e.g., host_id) from details, ***REMOVED*** to ErrorResponse
        # This way translation functions can use these variables to format messages
        if error.details:
            for key, value in error.details.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    error_response_kwargs[key] = value
    elif error.locale:
        error_response_kwargs["locale"] = error.locale

    return error_response_kwargs


def _handle_business_error(error: BusinessError, func_name: str, kwargs: dict) -> HTTPException:
    """Handle business exception, convert to HTTPException

    Args:
        error: Business exception object
        func_name: Function name
        kwargs: Function keyword arguments

    Returns:
        HTTPException object
    """
    status_code = error.http_status_code

    # Get stack trace information
    tb = traceback.extract_tb(error.__traceback__)
    error_location = None
    if tb:
        # Get the last frame (actual error location)
        last_frame = tb[-1]
        error_location = {
            "filename": last_frame.filename,
            "lineno": last_frame.lineno,
            "function": last_frame.name,
            "code": last_frame.line,
        }

    # Build detailed error information
    extra: Dict[str, Any] = {
        "function": func_name,
        "error_code": error.error_code,
        "message": error.message,
        "status_code": status_code,
    }

    # Add error location information
    if error_location:
        extra["error_location"] = error_location
        extra["error_file"] = error_location["filename"]
        extra["error_line"] = error_location["lineno"]
        extra["error_code_line"] = error_location["code"]

    # Build detailed error message
    error_msg = f"Business exception: {error.error_code} - {error.message}"
    if error_location:
        error_msg += (
            f"\nError location: {error_location['filename']}:{error_location['lineno']} in {error_location['function']}"
        )
        if error_location["code"]:
            error_msg += f"\nCode line: {error_location['code'].strip()}"

    # ✅ Log complete stack trace information
    logger.warning(
        error_msg,
        extra=extra,
        exc_info=(type(error), error, error.__traceback__),  # Explicitly ***REMOVED*** exception type, object and stack trace
    )

    # Prioritize API layer locale (extract from function parameters)
    api_locale = kwargs.get("locale")
    error_response_kwargs = _build_error_response_kwargs(error, api_locale)

    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(**error_response_kwargs).model_dump(),
    )


def _handle_unexpected_error(error: Exception, func_name: str) -> HTTPException:
    """Handle unexpected exception, convert to HTTPException

    Args:
        error: Exception object
        func_name: Function name

    Returns:
        HTTPException object
    """
    # Get stack trace information
    tb = traceback.extract_tb(error.__traceback__)
    error_location = None
    if tb:
        # Get the last frame (actual error location)
        last_frame = tb[-1]
        error_location = {
            "filename": last_frame.filename,
            "lineno": last_frame.lineno,
            "function": last_frame.name,
            "code": last_frame.line,
        }

    # Build detailed error information
    extra: Dict[str, Any] = {
        "function": func_name,
        "error_type": type(error).__name__,
        "error": str(error),
    }

    # Add error location information
    if error_location:
        extra["error_location"] = error_location
        extra["error_file"] = error_location["filename"]
        extra["error_line"] = error_location["lineno"]
        extra["error_code_line"] = error_location["code"]

    # Build detailed error message
    error_msg = f"API exception: {func_name} - {type(error).__name__}: {error!s}"
    if error_location:
        error_msg += (
            f"\nError location: {error_location['filename']}:{error_location['lineno']} in {error_location['function']}"
        )
        if error_location["code"]:
            error_msg += f"\nCode line: {error_location['code'].strip()}"

    # ✅ Log complete stack trace information (explicitly ***REMOVED*** exception object and stack trace)
    logger.error(
        error_msg,
        extra=extra,
        exc_info=(type(error), error, error.__traceback__),  # Explicitly ***REMOVED*** exception type, object and stack trace
    )

    return HTTPException(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ErrorResponse(
            code=HTTP_500_INTERNAL_SERVER_ERROR,
            message=INTERNAL_ERROR_MESSAGE,
            error_code=INTERNAL_ERROR_CODE,
            details={"error_type": type(error).__name__},
        ).model_dump(),
    )


def handle_api_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """API layer error handling decorator

    Used for unified error handling in API endpoints, converting BusinessError to HTTPException.
    Applicable to all FastAPI route handler functions.

    Args:
        func: Function being decorated

    Returns:
        Decorated function

    Usage example:
=======
def handle_api_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """API 层错误处理装饰器

    用于 API 端点的统一错误处理，将 BusinessError 转换为 HTTPException。
    适用于所有 FastAPI 路由处理函数。

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数

    使用示例:
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        ```python
        @router.post("/hosts")
        @handle_api_errors
        async def create_host(
            host_data: HostCreate,
            host_service: HostService = Depends(get_host_service)
        ):
            host = await host_service.create_host(host_data)
<<<<<<< HEAD
            return SuccessResponse(data=host, message="Host created successfully")
        ```

    Note:
        - BusinessError will be converted to corresponding HTTPException
        - HTTPException will be directly re-raised
        - Other exceptions will be converted to 500 error
        - All exceptions will be logged
=======
            return SuccessResponse(data=host, message="主机创建成功")
        ```

    注意:
        - BusinessError 会被转换为对应的 HTTPException
        - HTTPException 会被直接重新抛出
        - 其他异常会被转换为 500 错误
        - 所有异常都会被记录到日志中
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    """

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
<<<<<<< HEAD
        except BusinessError as e:
            raise _handle_business_error(e, func.__name__, kwargs)
        except HTTPException:
            # Directly raise HTTP exception
            raise
        except Exception as e:
            raise _handle_unexpected_error(e, func.__name__)
=======

        except BusinessError as e:
            # 业务异常转换为 HTTP 异常
            # 使用 e.http_status_code 作为实际的 HTTP 状态码（必须是 100-599）
            # 响应体中的 code 是自定义错误码（可能是 53009 这样的值）
            status_code = e.http_status_code

            logger.warning(
                f"业务异常: {e.error_code}",
                extra={
                    "function": func.__name__,
                    "error_code": e.error_code,
                    "message": e.message,
                    "status_code": status_code,
                },
            )

            # ✅ 优先使用 API 层的 locale（从函数参数中提取）
            # 如果 API 层有 locale 参数，使用它；否则使用异常中的 locale
            api_locale = kwargs.get("locale") or e.locale or "zh_CN"

            # ✅ 透传 message_key 和 locale 以支持多语言
            error_response_kwargs = {
                "code": e.code,  # 使用自定义错误码作为响应体中的 code
                "message": e.message,
                "error_code": e.error_code,
                "details": e.details,
            }
            if e.message_key:
                error_response_kwargs["message_key"] = e.message_key
                # 使用 API 层的 locale 重新翻译消息
                error_response_kwargs["locale"] = api_locale
            elif e.locale:
                error_response_kwargs["locale"] = e.locale

            raise HTTPException(
                status_code=status_code,
                detail=ErrorResponse(**error_response_kwargs).model_dump(),
            )

        except HTTPException:
            # 直接抛出 HTTP 异常
            raise

        except Exception as e:
            # 未预期的异常
            logger.error(
                f"API 异常: {func.__name__}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    code=HTTP_500_INTERNAL_SERVER_ERROR,
                    message="服务器内部错误",
                    error_code="INTERNAL_ERROR",
                    details={"error_type": type(e).__name__},
                ).model_dump(),
            )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
<<<<<<< HEAD
        except BusinessError as e:
            raise _handle_business_error(e, func.__name__, kwargs)
        except HTTPException:
            # Directly raise HTTP exception
            raise
        except Exception as e:
            raise _handle_unexpected_error(e, func.__name__)

    # Return the corresponding wrapper based on function type
=======

        except BusinessError as e:
            # 业务异常转换为 HTTP 异常
            # 使用 e.http_status_code 作为实际的 HTTP 状态码（必须是 100-599）
            # 响应体中的 code 是自定义错误码（可能是 53009 这样的值）
            status_code = e.http_status_code

            logger.warning(
                f"业务异常: {e.error_code}",
                extra={
                    "function": func.__name__,
                    "error_code": e.error_code,
                    "message": e.message,
                    "status_code": status_code,
                },
            )

            # ✅ 透传 message_key 和 locale 以支持多语言
            error_response_kwargs = {
                "code": e.code,  # 使用自定义错误码作为响应体中的 code
                "message": e.message,
                "error_code": e.error_code,
                "details": e.details,
            }
            if e.message_key:
                error_response_kwargs["message_key"] = e.message_key
            if e.locale:
                error_response_kwargs["locale"] = e.locale

            raise HTTPException(
                status_code=status_code,
                detail=ErrorResponse(**error_response_kwargs).model_dump(),
            )

        except HTTPException:
            # 直接抛出 HTTP 异常
            raise

        except Exception as e:
            # 未预期的异常
            logger.error(
                f"API 异常: {func.__name__}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    code=HTTP_500_INTERNAL_SERVER_ERROR,
                    message="服务器内部错误",
                    error_code="INTERNAL_ERROR",
                    details={"error_type": type(e).__name__},
                ).model_dump(),
            )

    # 根据函数类型返回对应的包装器
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


<<<<<<< HEAD
def _record_operation_metrics(operation_name: str, status: str, duration: Optional[float] = None) -> None:
    """Record operation metrics

    Args:
        operation_name: Operation name
        status: Operation status ("success" or "failed")
        duration: Operation duration (seconds), optional
    """
    metrics_collector.record_business_operation(operation=operation_name, status=status, duration=duration)


def _log_operation_result(
    operation_name: str,
    status: str,
    duration: Optional[float] = None,
    error: Optional[Exception] = None,
) -> None:
    """Log operation result

    Args:
        operation_name: Operation name
        status: Operation status ("success" or "failed")
        duration: Operation duration (seconds), optional
        error: Exception object (provided only on failure), optional
    """
    extra: Dict[str, Any] = {
        "operation": operation_name,
        "status": status,
    }

    if duration is not None:
        extra["duration_ms"] = int(duration * 1000)

    if error is not None:
        extra["error_type"] = type(error).__name__
        extra["error"] = str(error)

    if status == "success":
        logger.info(f"{operation_name} completed", extra=extra)
    # ✅ Log complete stack trace information on failure
    elif error and hasattr(error, "__traceback__") and error.__traceback__:
        logger.error(
            f"{operation_name} failed",
            extra=extra,
            exc_info=(type(error), error, error.__traceback__),  # Pass exception info
        )
    else:
        logger.error(
            f"{operation_name} failed",
            extra=extra,
            exc_info=True,  # Use current exception context
        )


=======
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
def monitor_operation(
    operation_name: str,
    record_duration: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
<<<<<<< HEAD
    """Business operation monitoring decorator

    Used to monitor the execution of business operations, recording operation duration and success/failure counts.
    Integrates with Prometheus metric collection.

    Args:
        operation_name: Operation name, used to identify different business operations
        record_duration: Whether to record operation duration, defaults to True

    Returns:
        Decorator function

    Usage example:
        ```python
        @monitor_operation("host_create", record_duration=True)
        @handle_service_errors(
            error_message="Failed to create host"
            error_code="HOST_CREATE_FAILED"
        )
        async def create_host(self, host_data: HostCreate) -> Host:
            # Business logic
            ***REMOVED***
        ```

    Note:
        - Successful operations will be recorded as status="success"
        - Failed operations will be recorded as status="failed"
        - If record_duration=True, operation duration will be logged
        - Metrics will be automatically sent to Prometheus
=======
    """业务操作监控装饰器

    用于监控业务操作的执行情况，记录操作耗时和成功/失败次数。
    集成 Prometheus 指标收集。

    Args:
        operation_name: 操作名称，用于标识不同的业务操作
        record_duration: 是否记录操作耗时，默认为 True

    Returns:
        装饰器函数

    使用示例:
        ```python
        @monitor_operation("host_create", record_duration=True)
        @handle_service_errors(
            error_message="创建主机失败",
            error_code="HOST_CREATE_FAILED"
        )
        async def create_host(self, host_data: HostCreate) -> Host:
            # 业务逻辑
            ***REMOVED***
        ```

    注意:
        - 成功的操作会记录为 status="success"
        - 失败的操作会记录为 status="failed"
        - 如果 record_duration=True，会记录操作耗时到日志
        - 指标会自动发送到 Prometheus
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time() if record_duration else None

            try:
                result = await func(*args, **kwargs)

<<<<<<< HEAD
                # Calculate duration
                duration = time.time() - start_time if start_time is not None else None

                # Record success metrics and logs
                _record_operation_metrics(operation_name, "success", duration)
                _log_operation_result(operation_name, "success", duration)
=======
                # 记录成功指标（包含耗时）
                duration = time.time() - start_time if start_time is not None else None
                metrics_collector.record_business_operation(
                    operation=operation_name, status="success", duration=duration
                )

                # 记录耗时日志
                if start_time is not None and duration is not None:
                    logger.info(
                        f"{operation_name} 完成",
                        extra={
                            "operation": operation_name,
                            "duration_ms": int(duration * 1000),
                            "status": "success",
                        },
                    )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

                return result

            except Exception as e:
<<<<<<< HEAD
                # Calculate duration
                duration = time.time() - start_time if start_time is not None else None

                # Record failure metrics and logs
                _record_operation_metrics(operation_name, "failed", duration)
                _log_operation_result(operation_name, "failed", duration, error=e)
=======
                # 记录失败指标（包含耗时）
                duration = time.time() - start_time if start_time is not None else None
                metrics_collector.record_business_operation(
                    operation=operation_name, status="failed", duration=duration
                )

                # 记录失败日志
                if start_time is not None and duration is not None:
                    logger.error(
                        f"{operation_name} 失败",
                        extra={
                            "operation": operation_name,
                            "duration_ms": int(duration * 1000),
                            "status": "failed",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )
                else:
                    logger.error(
                        f"{operation_name} 失败",
                        extra={
                            "operation": operation_name,
                            "status": "failed",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time() if record_duration else None

            try:
                result = func(*args, **kwargs)

<<<<<<< HEAD
                # Calculate duration
                duration = time.time() - start_time if start_time is not None else None

                # Record success metrics and logs
                _record_operation_metrics(operation_name, "success", duration)
                _log_operation_result(operation_name, "success", duration)
=======
                # 记录成功指标（包含耗时）
                duration = time.time() - start_time if start_time is not None else None
                metrics_collector.record_business_operation(
                    operation=operation_name, status="success", duration=duration
                )

                # 记录耗时日志
                if start_time is not None and duration is not None:
                    logger.info(
                        f"{operation_name} 完成",
                        extra={
                            "operation": operation_name,
                            "duration_ms": int(duration * 1000),
                            "status": "success",
                        },
                    )
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

                return result

            except Exception as e:
<<<<<<< HEAD
                # Calculate duration
                duration = time.time() - start_time if start_time is not None else None

                # Record failure metrics and logs
                _record_operation_metrics(operation_name, "failed", duration)
                _log_operation_result(operation_name, "failed", duration, error=e)

                raise

        # Return the corresponding wrapper based on function type
=======
                # 记录失败指标（包含耗时）
                duration = time.time() - start_time if start_time is not None else None
                metrics_collector.record_business_operation(
                    operation=operation_name, status="failed", duration=duration
                )

                # 记录失败日志
                if start_time is not None and duration is not None:
                    logger.error(
                        f"{operation_name} 失败",
                        extra={
                            "operation": operation_name,
                            "duration_ms": int(duration * 1000),
                            "status": "failed",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )
                else:
                    logger.error(
                        f"{operation_name} 失败",
                        extra={
                            "operation": operation_name,
                            "status": "failed",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )

                raise

        # 根据函数类型返回对应的包装器
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
