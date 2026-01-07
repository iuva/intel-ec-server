"""共享日志工具模块

提供统一的日志记录工具函数，支持：
1. 操作日志（开始/完成）
2. 请求日志（接收/完成）
3. 数据库操作日志
4. 外部 API 调用日志
5. 请求上下文装饰器
6. 性能追踪上下文管理器

使用示例:
    from shared.utils.logging_utils import (
        log_operation_start,
        log_operation_completed,
        timed_operation,
        log_db_query,
        log_external_api_call,
    )

    # 操作日志
    log_operation_start("创建用户", extra={"username": "admin"})
    log_operation_completed("创建用户", extra={"user_id": 123})

    # 性能追踪
    async with timed_operation("数据库查询", logger):
        result = await db.execute(query)

    # 数据库操作日志
    log_db_query("select", "users", 15.5, rows_affected=10)

    # 外部 API 调用日志
    log_external_api_call("GET", "http://api.example.com", 200, 150.0)
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from loguru import logger as default_logger

# 类型变量用于装饰器
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# 基础日志函数
# ============================================================================


def log_request_received(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录请求接收日志

    Args:
        operation: 操作名称（如 "query_available_hosts", "report_hardware"）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例，如果为 None 则使用默认 logger
    """
    log = logger_instance or default_logger
    log.info(
        f"📥 接收请求: {operation}",
        extra=extra or {},
    )


def log_request_completed(
    operation: str,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录请求处理完成日志

    Args:
        operation: 操作名称
        duration_ms: 处理耗时（毫秒）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = extra.copy() if extra else {}
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)

    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
    log.info(
        f"✅ 请求完成: {operation}{duration_str}",
        extra=log_extra,
    )


def log_operation_start(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录操作开始日志

    Args:
        operation: 操作名称
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log.info(
        f"▶ 开始: {operation}",
        extra=extra or {},
    )


def log_operation_completed(
    operation: str,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录操作完成日志

    Args:
        operation: 操作名称
        duration_ms: 操作耗时（毫秒）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = extra.copy() if extra else {}
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)

    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
    log.info(
        f"✓ 完成: {operation}{duration_str}",
        extra=log_extra,
    )


def log_operation_failed(
    operation: str,
    error: Union[str, Exception],
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
    include_traceback: bool = True,
) -> None:
    """记录操作失败日志

    Args:
        operation: 操作名称
        error: 错误信息或异常对象
        duration_ms: 操作耗时（毫秒）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
        include_traceback: 是否包含完整堆栈信息（默认 True）
    """
    log = logger_instance or default_logger
    log_extra = extra.copy() if extra else {}
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)

    error_msg = str(error)
    is_exception = isinstance(error, Exception)
    if is_exception:
        log_extra["error_type"] = type(error).__name__
        log_extra["error_message"] = error_msg

    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
    message = f"✗ 失败: {operation}{duration_str} - {error_msg}"

    # 如果是异常且需要打印堆栈，使用 opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(message, extra=log_extra)
    else:
        log.error(message, extra=log_extra)


def log_error(
    message: str,
    error: Optional[Union[str, Exception]] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
    include_traceback: bool = True,
) -> None:
    """记录通用错误日志（带完整堆栈信息）

    这是一个通用的错误日志函数，适用于任何需要记录错误的场景。
    默认会打印完整的堆栈信息。

    Args:
        message: 错误描述消息
        error: 错误信息或异常对象（可选）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
        include_traceback: 是否包含完整堆栈信息（默认 True）

    Usage:
        try:
            risky_operation()
        except Exception as e:
            log_error("执行风险操作失败", error=e, extra={"user_id": 123})
    """
    log = logger_instance or default_logger
    log_extra = extra.copy() if extra else {}

    is_exception = isinstance(error, Exception)
    if is_exception:
        log_extra["error_type"] = type(error).__name__
        log_extra["error_message"] = str(error)

    full_message = f"❌ {message}"
    if error:
        full_message = f"{full_message}: {error}"

    # 如果是异常且需要打印堆栈，使用 opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(full_message, extra=log_extra)
    else:
        log.error(full_message, extra=log_extra)


def log_warning(
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录警告日志

    Args:
        message: 警告消息
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例

    Usage:
        log_warning("配置值过大", extra={"config_key": "max_connections", "value": 10000})
    """
    log = logger_instance or default_logger
    log.warning(f"⚠ {message}", extra=extra)


# ============================================================================
# 数据库操作日志
# ============================================================================


def log_db_query(
    operation: str,
    table: str,
    duration_ms: float,
    rows_affected: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录数据库查询日志

    Args:
        operation: 操作类型（select, insert, update, delete）
        table: 表名
        duration_ms: 查询耗时（毫秒）
        rows_affected: 影响的行数
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {
        "operation": operation.upper(),
        "table": table,
        "duration_ms": round(duration_ms, 2),
    }
    if rows_affected is not None:
        log_extra["rows_affected"] = rows_affected
    if extra:
        log_extra.update(extra)

    # 根据耗时选择日志级别
    if duration_ms > 1000:  # 超过1秒，警告
        log.warning(
            f"🐢 慢查询: {operation.upper()} {table} ({duration_ms:.2f}ms, {rows_affected} rows)",
            extra=log_extra,
        )
    elif duration_ms > 500:  # 超过500ms，信息级别但标记
        log.info(
            f"⚠ 较慢查询: {operation.upper()} {table} ({duration_ms:.2f}ms, {rows_affected} rows)",
            extra=log_extra,
        )
    else:
        log.debug(
            f"🔍 DB: {operation.upper()} {table} ({duration_ms:.2f}ms, {rows_affected} rows)",
            extra=log_extra,
        )


def log_db_error(
    operation: str,
    table: str,
    error: Union[str, Exception],
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
    include_traceback: bool = True,
) -> None:
    """记录数据库错误日志

    Args:
        operation: 操作类型
        table: 表名
        error: 错误信息或异常对象
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
        include_traceback: 是否包含完整堆栈信息（默认 True）
    """
    log = logger_instance or default_logger
    log_extra = {
        "operation": operation.upper(),
        "table": table,
    }
    is_exception = isinstance(error, Exception)
    if is_exception:
        log_extra["error_type"] = type(error).__name__
        log_extra["error_message"] = str(error)
    if extra:
        log_extra.update(extra)

    message = f"❌ DB错误: {operation.upper()} {table} - {error}"

    # 如果是异常且需要打印堆栈，使用 opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(message, extra=log_extra)
    else:
        log.error(message, extra=log_extra)


# ============================================================================
# 外部 API 调用日志
# ============================================================================


def log_external_api_call(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录外部 API 调用日志

    Args:
        method: HTTP 方法（GET, POST, PUT, DELETE）
        url: 请求 URL
        status_code: HTTP 响应状态码
        duration_ms: 请求耗时（毫秒）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra: Dict[str, Any] = {
        "method": method.upper(),
        "url": url,
    }
    if status_code is not None:
        log_extra["status_code"] = status_code
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)
    if extra:
        log_extra.update(extra)

    # 根据状态码选择日志级别
    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms else ""
    status_str = f" [{status_code}]" if status_code else ""

    if status_code is None:
        log.debug(
            f"🌐 API调用: {method.upper()} {url}",
            extra=log_extra,
        )
    elif 200 <= status_code < 300:
        log.debug(
            f"🌐 API成功: {method.upper()} {url}{status_str}{duration_str}",
            extra=log_extra,
        )
    elif 400 <= status_code < 500:
        log.warning(
            f"⚠ API客户端错误: {method.upper()} {url}{status_str}{duration_str}",
            extra=log_extra,
        )
    else:
        log.error(
            f"❌ API服务端错误: {method.upper()} {url}{status_str}{duration_str}",
            extra=log_extra,
        )


def log_external_api_error(
    method: str,
    url: str,
    error: Union[str, Exception],
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
    include_traceback: bool = True,
) -> None:
    """记录外部 API 调用错误日志

    Args:
        method: HTTP 方法
        url: 请求 URL
        error: 错误信息或异常对象
        duration_ms: 请求耗时（毫秒）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
        include_traceback: 是否包含完整堆栈信息（默认 True）
    """
    log = logger_instance or default_logger
    log_extra: Dict[str, Any] = {
        "method": method.upper(),
        "url": url,
    }
    is_exception = isinstance(error, Exception)
    if is_exception:
        log_extra["error_type"] = type(error).__name__
        log_extra["error_message"] = str(error)
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)
    if extra:
        log_extra.update(extra)

    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms else ""
    message = f"❌ API异常: {method.upper()} {url}{duration_str} - {error}"

    # 如果是异常且需要打印堆栈，使用 opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(message, extra=log_extra)
    else:
        log.error(message, extra=log_extra)


# ============================================================================
# 性能追踪上下文管理器
# ============================================================================


@contextmanager
def timed_operation_sync(
    operation: str,
    logger_instance: Optional[Any] = None,
    log_start: bool = True,
    extra: Optional[Dict[str, Any]] = None,
):
    """同步性能追踪上下文管理器

    用于测量代码块的执行时间，自动记录开始和完成日志。

    Args:
        operation: 操作名称
        logger_instance: 自定义 logger 实例
        log_start: 是否记录开始日志
        extra: 额外的日志字段

    Yields:
        TimingContext: 包含 elapsed_ms 属性的上下文对象

    Usage:
        with timed_operation_sync("处理数据", logger) as ctx:
            process_data()
        print(f"耗时: {ctx.elapsed_ms}ms")
    """
    log = logger_instance or default_logger

    class TimingContext:
        def __init__(self) -> None:
            self.elapsed_ms: float = 0.0
            self.start_time: float = time.perf_counter()

    ctx = TimingContext()

    if log_start:
        log_operation_start(operation, extra=extra, logger_instance=log)

    try:
        yield ctx
        ctx.elapsed_ms = (time.perf_counter() - ctx.start_time) * 1000
        log_operation_completed(operation, duration_ms=ctx.elapsed_ms, extra=extra, logger_instance=log)
    except Exception as e:
        ctx.elapsed_ms = (time.perf_counter() - ctx.start_time) * 1000
        log_operation_failed(operation, error=e, duration_ms=ctx.elapsed_ms, extra=extra, logger_instance=log)
        raise


@asynccontextmanager
async def timed_operation(
    operation: str,
    logger_instance: Optional[Any] = None,
    log_start: bool = True,
    extra: Optional[Dict[str, Any]] = None,
):
    """异步性能追踪上下文管理器

    用于测量异步代码块的执行时间，自动记录开始和完成日志。

    Args:
        operation: 操作名称
        logger_instance: 自定义 logger 实例
        log_start: 是否记录开始日志
        extra: 额外的日志字段

    Yields:
        TimingContext: 包含 elapsed_ms 属性的上下文对象

    Usage:
        async with timed_operation("数据库查询", logger) as ctx:
            result = await db.execute(query)
        print(f"耗时: {ctx.elapsed_ms}ms")
    """
    log = logger_instance or default_logger

    class TimingContext:
        def __init__(self) -> None:
            self.elapsed_ms: float = 0.0
            self.start_time: float = time.perf_counter()

    ctx = TimingContext()

    if log_start:
        log_operation_start(operation, extra=extra, logger_instance=log)

    try:
        yield ctx
        ctx.elapsed_ms = (time.perf_counter() - ctx.start_time) * 1000
        log_operation_completed(operation, duration_ms=ctx.elapsed_ms, extra=extra, logger_instance=log)
    except Exception as e:
        ctx.elapsed_ms = (time.perf_counter() - ctx.start_time) * 1000
        log_operation_failed(operation, error=e, duration_ms=ctx.elapsed_ms, extra=extra, logger_instance=log)
        raise


# ============================================================================
# 请求上下文装饰器
# ============================================================================


def with_request_logging(
    operation: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[F], F]:
    """请求日志装饰器

    自动记录函数调用的开始、完成和异常。

    Args:
        operation: 操作名称（默认使用函数名）
        log_args: 是否记录函数参数
        log_result: 是否记录返回结果

    Usage:
        @with_request_logging("创建用户", log_args=True)
        async def create_user(username: str, email: str):
            ...
    """

    def decorator(func: F) -> F:
        op_name = operation or func.__name__

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            extra: Dict[str, Any] = {}
            if log_args:
                extra["args"] = str(args)[:200]  # 限制长度
                extra["kwargs"] = str(kwargs)[:200]

            start_time = time.perf_counter()
            log_request_received(op_name, extra=extra if log_args else None)

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                result_extra: Dict[str, Any] = {}
                if log_result and result is not None:
                    result_extra["result_type"] = type(result).__name__

                log_request_completed(op_name, duration_ms=elapsed_ms, extra=result_extra if log_result else None)
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                log_operation_failed(op_name, error=e, duration_ms=elapsed_ms)
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            extra: Dict[str, Any] = {}
            if log_args:
                extra["args"] = str(args)[:200]
                extra["kwargs"] = str(kwargs)[:200]

            start_time = time.perf_counter()
            log_request_received(op_name, extra=extra if log_args else None)

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                result_extra: Dict[str, Any] = {}
                if log_result and result is not None:
                    result_extra["result_type"] = type(result).__name__

                log_request_completed(op_name, duration_ms=elapsed_ms, extra=result_extra if log_result else None)
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                log_operation_failed(op_name, error=e, duration_ms=elapsed_ms)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# ============================================================================
# WebSocket 日志
# ============================================================================


def log_websocket_connect(
    client_id: str,
    remote_addr: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录 WebSocket 连接日志

    Args:
        client_id: 客户端标识
        remote_addr: 客户端地址
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {"client_id": client_id}
    if remote_addr:
        log_extra["remote_addr"] = remote_addr
    if extra:
        log_extra.update(extra)

    log.info(
        f"🔌 WebSocket连接: {client_id}",
        extra=log_extra,
    )


def log_websocket_disconnect(
    client_id: str,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录 WebSocket 断开日志

    Args:
        client_id: 客户端标识
        reason: 断开原因
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {"client_id": client_id}
    if reason:
        log_extra["reason"] = reason
    if extra:
        log_extra.update(extra)

    reason_str = f" - {reason}" if reason else ""
    log.info(
        f"🔌 WebSocket断开: {client_id}{reason_str}",
        extra=log_extra,
    )


def log_websocket_message(
    client_id: str,
    message_type: str,
    direction: str = "recv",  # "recv" or "send"
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录 WebSocket 消息日志

    Args:
        client_id: 客户端标识
        message_type: 消息类型
        direction: 消息方向 ("recv" 或 "send")
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {
        "client_id": client_id,
        "message_type": message_type,
        "direction": direction,
    }
    if extra:
        log_extra.update(extra)

    arrow = "⬅" if direction == "recv" else "➡"
    log.debug(
        f"{arrow} WS消息: {client_id} [{message_type}]",
        extra=log_extra,
    )


# ============================================================================
# 认证日志
# ============================================================================


def log_auth_success(
    user_id: str,
    username: Optional[str] = None,
    auth_type: str = "login",
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录认证成功日志

    Args:
        user_id: 用户ID
        username: 用户名
        auth_type: 认证类型（login, token_refresh, oauth）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {
        "user_id": user_id,
        "auth_type": auth_type,
    }
    if username:
        log_extra["username"] = username
    if extra:
        log_extra.update(extra)

    user_str = f"{username}({user_id})" if username else user_id
    log.info(
        f"🔓 认证成功: {user_str} [{auth_type}]",
        extra=log_extra,
    )


def log_auth_failure(
    reason: str,
    username: Optional[str] = None,
    auth_type: str = "login",
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录认证失败日志

    Args:
        reason: 失败原因
        username: 用户名
        auth_type: 认证类型
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {
        "reason": reason,
        "auth_type": auth_type,
    }
    if username:
        log_extra["username"] = username
    if extra:
        log_extra.update(extra)

    user_str = f" ({username})" if username else ""
    log.warning(
        f"🔒 认证失败{user_str}: {reason} [{auth_type}]",
        extra=log_extra,
    )


# ============================================================================
# 服务启动日志
# ============================================================================


def log_service_startup(
    service_name: str,
    version: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录服务启动日志

    Args:
        service_name: 服务名称
        version: 服务版本
        host: 监听地址
        port: 监听端口
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra: Dict[str, Any] = {"service_name": service_name}
    if version:
        log_extra["version"] = version
    if host:
        log_extra["host"] = host
    if port:
        log_extra["port"] = port
    if extra:
        log_extra.update(extra)

    addr_str = f" @ {host}:{port}" if host and port else ""
    version_str = f" v{version}" if version else ""
    log.info(
        f"🚀 服务启动: {service_name}{version_str}{addr_str}",
        extra=log_extra,
    )


def log_service_shutdown(
    service_name: str,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录服务关闭日志

    Args:
        service_name: 服务名称
        reason: 关闭原因
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例
    """
    log = logger_instance or default_logger
    log_extra = {"service_name": service_name}
    if reason:
        log_extra["reason"] = reason
    if extra:
        log_extra.update(extra)

    reason_str = f" - {reason}" if reason else ""
    log.info(
        f"🛑 服务关闭: {service_name}{reason_str}",
        extra=log_extra,
    )


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 基础日志
    "log_request_received",
    "log_request_completed",
    "log_operation_start",
    "log_operation_completed",
    "log_operation_failed",
    "log_error",
    "log_warning",
    # 数据库日志
    "log_db_query",
    "log_db_error",
    # 外部 API 日志
    "log_external_api_call",
    "log_external_api_error",
    # 性能追踪
    "timed_operation",
    "timed_operation_sync",
    # 装饰器
    "with_request_logging",
    # WebSocket 日志
    "log_websocket_connect",
    "log_websocket_disconnect",
    "log_websocket_message",
    # 认证日志
    "log_auth_success",
    "log_auth_failure",
    # 服务日志
    "log_service_startup",
    "log_service_shutdown",
]
