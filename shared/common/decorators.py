"""
装饰器模块

提供统一的错误处理、监控和日志记录装饰器
"""

import asyncio
import time
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

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

# 类型变量
T = TypeVar("T")

# 常量
DEFAULT_ERROR_MESSAGE = "操作失败"
DEFAULT_ERROR_CODE = "OPERATION_FAILED"
DEFAULT_LOCALE = "zh_CN"
INTERNAL_ERROR_CODE = "INTERNAL_ERROR"
INTERNAL_ERROR_MESSAGE = "服务器内部错误"


def _log_service_error(func_name: str, error: Exception, args: tuple, kwargs: dict) -> None:
    """记录服务层错误日志

    Args:
        func_name: 函数名称
        error: 异常对象
        args: 函数参数（元组）
        kwargs: 函数关键字参数（字典）
    """
    # 获取堆栈跟踪信息
    tb = traceback.extract_tb(error.__traceback__)
    error_location = None
    if tb:
        # 获取最后一个堆栈帧（实际出错的位置）
        last_frame = tb[-1]
        error_location = {
            "filename": last_frame.filename,
            "lineno": last_frame.lineno,
            "function": last_frame.name,
            "code": last_frame.line,
        }

    # 构建详细的错误信息
    extra: Dict[str, Any] = {
        "function": func_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    # 添加错误位置信息
    if error_location:
        extra["error_location"] = error_location
        extra["error_file"] = error_location["filename"]
        extra["error_line"] = error_location["lineno"]
        extra["error_code_line"] = error_location["code"]

    # 如果是 BusinessError，记录详细信息
    if isinstance(error, BusinessError):
        extra.update({
            "error_code": error.error_code,
            "business_code": error.code,
            "http_status_code": error.http_status_code,
            "message": error.message,
            "message_key": error.message_key,
            "locale": error.locale,
            "details": error.details,
        })

    # 提取函数参数中的关键信息（如 host_id, agent_id 等）
    # 跳过 self 参数
    if len(args) > 1:
        # 尝试提取常见的参数名
        for i, arg in enumerate(args[1:], start=1):
            if isinstance(arg, str) and (arg.isdigit() or len(arg) > 10):
                # 可能是 ID 参数
                extra[f"arg_{i}"] = arg
            elif isinstance(arg, (int, float, bool)):
                extra[f"arg_{i}"] = arg

    # 提取 kwargs 中的关键信息
    for key, value in kwargs.items():
        if key in ("host_id", "agent_id", "user_id", "service_name", "path"):
            extra[key] = value
        elif isinstance(value, (str, int, float, bool, type(None))):
            # 只记录简单类型的值，避免记录复杂对象
            extra[f"kwarg_{key}"] = value

    # 记录完整的参数信息（用于调试）
    extra["args_count"] = len(args) - 1 if len(args) > 1 else 0
    extra["kwargs_count"] = len(kwargs)

    # 构建详细的错误消息
    error_msg = f"{func_name} 执行失败: {type(error).__name__} - {str(error)}"
    if error_location:
        error_msg += f"\n错误位置: {error_location['filename']}:{error_location['lineno']} in {error_location['function']}"
        if error_location['code']:
            error_msg += f"\n代码行: {error_location['code'].strip()}"

    # ✅ 记录完整的堆栈跟踪信息（显式传递异常对象和堆栈跟踪）
    logger.error(
        error_msg,
        extra=extra,
        exc_info=(type(error), error, error.__traceback__),  # 显式传递异常类型、异常对象和堆栈跟踪
    )


def _create_business_error(
    error: Exception, error_message: str, error_code: str
) -> BusinessError:
    """创建业务异常对象

    Args:
        error: 原始异常
        error_message: 错误消息
        error_code: 错误码

    Returns:
        BusinessError 对象
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
            async with mariadb_manager.get_session() as session:
                host = Host(**host_data.model_dump())
                session.add(host)
                await session.commit()
                return host
        ```

    注意:
        - BusinessError 会被直接重新抛出，不会被转换
        - 其他异常会被捕获并转换为 BusinessError
        - 所有异常都会被记录到日志中
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except BusinessError:
                # 重新抛出业务异常，不做转换
                raise
            except Exception as e:
                _log_service_error(func.__name__, e, args, kwargs)
                raise _create_business_error(e, error_message, error_code)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except BusinessError:
                # 重新抛出业务异常，不做转换
                raise
            except Exception as e:
                _log_service_error(func.__name__, e, args, kwargs)
                raise _create_business_error(e, error_message, error_code)

        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _build_error_response_kwargs(
    error: BusinessError, api_locale: Optional[str] = None
) -> Dict[str, Any]:
    """构建错误响应参数字典

    Args:
        error: 业务异常对象
        api_locale: API 层的 locale（可选）

    Returns:
        错误响应参数字典
    """
    # 优先使用 API 层的 locale，否则使用异常中的 locale，最后使用默认值
    locale = api_locale or error.locale or DEFAULT_LOCALE

    error_response_kwargs: Dict[str, Any] = {
        "code": error.code,  # 使用自定义错误码作为响应体中的 code
        "message": error.message,
        "error_code": error.error_code,
        "details": error.details or {},
    }

    if error.message_key:
        error_response_kwargs["message_key"] = error.message_key
        error_response_kwargs["locale"] = locale
        # 从 details 中提取格式化变量（如 host_id），传递给 ErrorResponse
        # 这样翻译函数可以使用这些变量来格式化消息
        if error.details:
            for key, value in error.details.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    error_response_kwargs[key] = value
    elif error.locale:
        error_response_kwargs["locale"] = error.locale

    return error_response_kwargs


def _handle_business_error(
    error: BusinessError, func_name: str, kwargs: dict
) -> HTTPException:
    """处理业务异常，转换为 HTTPException

    Args:
        error: 业务异常对象
        func_name: 函数名称
        kwargs: 函数关键字参数

    Returns:
        HTTPException 对象
    """
    status_code = error.http_status_code

    # 获取堆栈跟踪信息
    tb = traceback.extract_tb(error.__traceback__)
    error_location = None
    if tb:
        # 获取最后一个堆栈帧（实际出错的位置）
        last_frame = tb[-1]
        error_location = {
            "filename": last_frame.filename,
            "lineno": last_frame.lineno,
            "function": last_frame.name,
            "code": last_frame.line,
        }

    # 构建详细的错误信息
    extra: Dict[str, Any] = {
        "function": func_name,
        "error_code": error.error_code,
        "message": error.message,
        "status_code": status_code,
    }

    # 添加错误位置信息
    if error_location:
        extra["error_location"] = error_location
        extra["error_file"] = error_location["filename"]
        extra["error_line"] = error_location["lineno"]
        extra["error_code_line"] = error_location["code"]

    # 构建详细的错误消息
    error_msg = f"业务异常: {error.error_code} - {error.message}"
    if error_location:
        error_msg += f"\n错误位置: {error_location['filename']}:{error_location['lineno']} in {error_location['function']}"
        if error_location['code']:
            error_msg += f"\n代码行: {error_location['code'].strip()}"

    # ✅ 记录完整的堆栈跟踪信息
    logger.warning(
        error_msg,
        extra=extra,
        exc_info=(type(error), error, error.__traceback__),  # 显式传递异常类型、异常对象和堆栈跟踪
    )

    # 优先使用 API 层的 locale（从函数参数中提取）
    api_locale = kwargs.get("locale")
    error_response_kwargs = _build_error_response_kwargs(error, api_locale)

    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(**error_response_kwargs).model_dump(),
    )


def _handle_unexpected_error(error: Exception, func_name: str) -> HTTPException:
    """处理未预期的异常，转换为 HTTPException

    Args:
        error: 异常对象
        func_name: 函数名称

    Returns:
        HTTPException 对象
    """
    # 获取堆栈跟踪信息
    tb = traceback.extract_tb(error.__traceback__)
    error_location = None
    if tb:
        # 获取最后一个堆栈帧（实际出错的位置）
        last_frame = tb[-1]
        error_location = {
            "filename": last_frame.filename,
            "lineno": last_frame.lineno,
            "function": last_frame.name,
            "code": last_frame.line,
        }

    # 构建详细的错误信息
    extra: Dict[str, Any] = {
        "function": func_name,
        "error_type": type(error).__name__,
        "error": str(error),
    }

    # 添加错误位置信息
    if error_location:
        extra["error_location"] = error_location
        extra["error_file"] = error_location["filename"]
        extra["error_line"] = error_location["lineno"]
        extra["error_code_line"] = error_location["code"]

    # 构建详细的错误消息
    error_msg = f"API 异常: {func_name} - {type(error).__name__}: {str(error)}"
    if error_location:
        error_msg += f"\n错误位置: {error_location['filename']}:{error_location['lineno']} in {error_location['function']}"
        if error_location['code']:
            error_msg += f"\n代码行: {error_location['code'].strip()}"

    # ✅ 记录完整的堆栈跟踪信息（显式传递异常对象和堆栈跟踪）
    logger.error(
        error_msg,
        extra=extra,
        exc_info=(type(error), error, error.__traceback__),  # 显式传递异常类型、异常对象和堆栈跟踪
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
    """API 层错误处理装饰器

    用于 API 端点的统一错误处理，将 BusinessError 转换为 HTTPException。
    适用于所有 FastAPI 路由处理函数。

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数

    使用示例:
        ```python
        @router.post("/hosts")
        @handle_api_errors
        async def create_host(
            host_data: HostCreate,
            host_service: HostService = Depends(get_host_service)
        ):
            host = await host_service.create_host(host_data)
            return SuccessResponse(data=host, message="主机创建成功")
        ```

    注意:
        - BusinessError 会被转换为对应的 HTTPException
        - HTTPException 会被直接重新抛出
        - 其他异常会被转换为 500 错误
        - 所有异常都会被记录到日志中
    """

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except BusinessError as e:
            raise _handle_business_error(e, func.__name__, kwargs)
        except HTTPException:
            # 直接抛出 HTTP 异常
            raise
        except Exception as e:
            raise _handle_unexpected_error(e, func.__name__)

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except BusinessError as e:
            raise _handle_business_error(e, func.__name__, kwargs)
        except HTTPException:
            # 直接抛出 HTTP 异常
            raise
        except Exception as e:
            raise _handle_unexpected_error(e, func.__name__)

    # 根据函数类型返回对应的包装器
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def _record_operation_metrics(
    operation_name: str, status: str, duration: Optional[float] = None
) -> None:
    """记录操作指标

    Args:
        operation_name: 操作名称
        status: 操作状态（"success" 或 "failed"）
        duration: 操作耗时（秒），可选
    """
    metrics_collector.record_business_operation(
        operation=operation_name, status=status, duration=duration
    )


def _log_operation_result(
    operation_name: str,
    status: str,
    duration: Optional[float] = None,
    error: Optional[Exception] = None,
) -> None:
    """记录操作结果日志

    Args:
        operation_name: 操作名称
        status: 操作状态（"success" 或 "failed"）
        duration: 操作耗时（秒），可选
        error: 异常对象（仅在失败时提供），可选
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
        logger.info(f"{operation_name} 完成", extra=extra)
    else:
        # ✅ 记录失败时的完整堆栈跟踪信息
        if error and hasattr(error, '__traceback__') and error.__traceback__:
            logger.error(
                f"{operation_name} 失败",
                extra=extra,
                exc_info=(type(error), error, error.__traceback__),  # 显式传递异常类型、异常对象和堆栈跟踪
            )
        else:
            logger.error(
                f"{operation_name} 失败",
                extra=extra,
                exc_info=True,  # 使用当前异常上下文
            )


def monitor_operation(
    operation_name: str,
    record_duration: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time() if record_duration else None

            try:
                result = await func(*args, **kwargs)

                # 计算耗时
                duration = time.time() - start_time if start_time is not None else None

                # 记录成功指标和日志
                _record_operation_metrics(operation_name, "success", duration)
                _log_operation_result(operation_name, "success", duration)

                return result

            except Exception as e:
                # 计算耗时
                duration = time.time() - start_time if start_time is not None else None

                # 记录失败指标和日志
                _record_operation_metrics(operation_name, "failed", duration)
                _log_operation_result(operation_name, "failed", duration, error=e)

                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time() if record_duration else None

            try:
                result = func(*args, **kwargs)

                # 计算耗时
                duration = time.time() - start_time if start_time is not None else None

                # 记录成功指标和日志
                _record_operation_metrics(operation_name, "success", duration)
                _log_operation_result(operation_name, "success", duration)

                return result

            except Exception as e:
                # 计算耗时
                duration = time.time() - start_time if start_time is not None else None

                # 记录失败指标和日志
                _record_operation_metrics(operation_name, "failed", duration)
                _log_operation_result(operation_name, "failed", duration, error=e)

                raise

        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
