"""
装饰器模块

提供统一的错误处理、监控和日志记录装饰器
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, TypeVar

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

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)

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
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


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

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)

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
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


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

                return result

            except Exception as e:
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

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time() if record_duration else None

            try:
                result = func(*args, **kwargs)

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

                return result

            except Exception as e:
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
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
