"""Shared Logging Utilities Module

Provides unified logging utility functions, supporting:
1. Operation logs (start/complete)
2. Request logs (receive/complete)
3. Database operation logs
4. External API call logs
5. Request context decorators
6. Performance tracking context managers

Usage example:
    from shared.utils.logging_utils import (
        log_operation_start,
        log_operation_completed,
        timed_operation,
        log_db_query,
        log_external_api_call,
    )

    # Operation logs
    log_operation_start("Create User", extra={"username": "admin"})
    log_operation_completed("Create User", extra={"user_id": 123})

    # Performance tracking
    async with timed_operation("Database Query", logger):
        result = await db.execute(query)

    # Database operation logs
    log_db_query("select", "users", 15.5, rows_affected=10)

    # External API call logs
    log_external_api_call("GET", "http://api.example.com", 200, 150.0)
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from loguru import logger as default_logger

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Basic logging functions
# ============================================================================


def log_request_received(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record request received log

    Args:
        operation: Operation name (e.g., "query_available_hosts", "report_hardware")
        extra: Additional log fields
        logger_instance: Custom logger instance, if None then use default logger
    """
    log = logger_instance or default_logger
    log.info(
        f"📥 Request Received: {operation}",
        extra=extra or {},
    )


def log_request_completed(
    operation: str,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record request processing completed log

    Args:
        operation: Operation name
        duration_ms: Processing time (milliseconds)
        extra: Additional log fields
        logger_instance: Custom logger instance
    """
    log = logger_instance or default_logger
    log_extra = extra.copy() if extra else {}
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)

    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
    log.info(
        f"✅ Request Completed: {operation}{duration_str}",
        extra=log_extra,
    )


def log_operation_start(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record operation start log

    Args:
        operation: Operation name
        extra: Additional log fields
        logger_instance: Custom logger instance
    """
    log = logger_instance or default_logger
    log.info(
        f"▶ Started: {operation}",
        extra=extra or {},
    )


def log_operation_completed(
    operation: str,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record operation completed log

    Args:
        operation: Operation name
        duration_ms: Operation time (milliseconds)
        extra: Additional log fields
        logger_instance: Custom logger instance
    """
    log = logger_instance or default_logger
    log_extra = extra.copy() if extra else {}
    if duration_ms is not None:
        log_extra["duration_ms"] = round(duration_ms, 2)

    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
    log.info(
        f"✓ Completed: {operation}{duration_str}",
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
    """Record operation failed log

    Args:
        operation: Operation name
        error: Error message or exception object
        duration_ms: Operation time (milliseconds)
        extra: Additional log fields
        logger_instance: Custom logger instance
        include_traceback: Whether to include full stack trace (default True)
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
    message = f"✗ Failed: {operation}{duration_str} - {error_msg}"

    # If it's an exception and needs to print the stack, use opt(exception=True)
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
    """Record general error log (with full stack trace)

    This is a general error logging function, suitable for any scenario requiring error logging.
    By default, it will print the full stack trace.

    Args:
        message: Error description message
        error: Error message or exception object (optional)
        extra: Additional log fields
        logger_instance: Custom logger instance
        include_traceback: Whether to include full stack trace (default True)

    Usage:
        try:
            risky_operation()
        except Exception as e:
            log_error("Failed to execute risky operation", error=e, extra={"user_id": 123})
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

    # If it's an exception and needs to print the stack, use opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(full_message, extra=log_extra)
    else:
        log.error(full_message, extra=log_extra)


def log_warning(
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record warning log

    Args:
        message: Warning message
        extra: Additional log fields
        logger_instance: Custom logger instance

    Usage:
        log_warning("Configuration value too large", extra={"config_key": "max_connections", "value": 10000})
    """
    log = logger_instance or default_logger
    log.warning(f"⚠ {message}", extra=extra)


# ============================================================================
# Database operation logs
# ============================================================================


def log_db_query(
    operation: str,
    table: str,
    duration_ms: float,
    rows_affected: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record database query log

    Args:
        operation: Operation type (select, insert, update, delete)
        table: Table name
        duration_ms: Query time (milliseconds)
        rows_affected: Number of affected rows
        extra: Additional log fields
        logger_instance: Custom logger instance
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

    # Choose log level based on duration
    if duration_ms > 1000:  # Over 1 second, warning
        log.warning(
            f"🐢 Slow Query: {operation.upper()} {table} ({duration_ms:.2f}ms, {rows_affected} rows)",
            extra=log_extra,
        )
    elif duration_ms > 500:  # Over 500ms, info level but marked
        log.info(
            f"⚠ Slower Query: {operation.upper()} {table} ({duration_ms:.2f}ms, {rows_affected} rows)",
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
    """Record database error log

    Args:
        operation: Operation type
        table: Table name
        error: Error message or exception object
        extra: Additional log fields
        logger_instance: Custom logger instance
        include_traceback: Whether to include full stack trace (default True)
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

    message = f"❌ DB Error: {operation.upper()} {table} - {error}"

    # If it's an exception and needs to print the stack, use opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(message, extra=log_extra)
    else:
        log.error(message, extra=log_extra)


# ============================================================================
# External API call logs
# ============================================================================


def log_external_api_call(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record external API call log

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        url: Request URL
        status_code: HTTP response status code
        duration_ms: Request time (milliseconds)
        extra: Additional log fields
        logger_instance: Custom logger instance
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

    # Choose log level based on status code
    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms else ""
    status_str = f" [{status_code}]" if status_code else ""

    if status_code is None:
        log.debug(
            f"🌐 API Call: {method.upper()} {url}",
            extra=log_extra,
        )
    elif 200 <= status_code < 300:
        log.debug(
            f"🌐 API Success: {method.upper()} {url}{status_str}{duration_str}",
            extra=log_extra,
        )
    elif 400 <= status_code < 500:
        log.warning(
            f"⚠ API Client Error: {method.upper()} {url}{status_str}{duration_str}",
            extra=log_extra,
        )
    else:
        log.error(
            f"❌ API Server Error: {method.upper()} {url}{status_str}{duration_str}",
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
    """Record external API call error log

    Args:
        method: HTTP method
        url: Request URL
        error: Error message or exception object
        duration_ms: Request time (milliseconds)
        extra: Additional log fields
        logger_instance: Custom logger instance
        include_traceback: Whether to include full stack trace (default True)
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
    message = f"❌ API Exception: {method.upper()} {url}{duration_str} - {error}"

    # If it's an exception and needs to print the stack, use opt(exception=True)
    if is_exception and include_traceback:
        log.opt(exception=error).error(message, extra=log_extra)
    else:
        log.error(message, extra=log_extra)


# ============================================================================
# Performance tracking context managers
# ============================================================================


@contextmanager
def timed_operation_sync(
    operation: str,
    logger_instance: Optional[Any] = None,
    log_start: bool = True,
    extra: Optional[Dict[str, Any]] = None,
):
    """Synchronous performance tracking context manager

    Used to measure execution time of code blocks, automatically recording start and completion logs.

    Args:
        operation: Operation name
        logger_instance: Custom logger instance
        log_start: Whether to record start log
        extra: Additional log fields

    Yields:
        TimingContext: Context object containing elapsed_ms property

    Usage:
        with timed_operation_sync("Processing Data", logger) as ctx:
            process_data()
        print(f"Duration: {ctx.elapsed_ms}ms")
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
    """Asynchronous performance tracking context manager

    Used to measure execution time of asynchronous code blocks, automatically recording start and completion logs.

    Args:
        operation: Operation name
        logger_instance: Custom logger instance
        log_start: Whether to record start log
        extra: Additional log fields

    Yields:
        TimingContext: Context object containing elapsed_ms property

    Usage:
        async with timed_operation("Database Query", logger) as ctx:
            result = await db.execute(query)
        print(f"Duration: {ctx.elapsed_ms}ms")
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
# Request context decorators
# ============================================================================


def with_request_logging(
    operation: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[F], F]:
    """Request logging decorator

    Automatically records function call start, completion and exceptions.

    Args:
        operation: Operation name (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log return result

    Usage:
        @with_request_logging("Create User", log_args=True)
        async def create_user(username: str, email: str):
            ...
    """

    def decorator(func: F) -> F:
        op_name = operation or func.__name__

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            extra: Dict[str, Any] = {}
            if log_args:
                extra["args"] = str(args)[:200]  # Limit length
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
# WebSocket logs
# ============================================================================


def log_websocket_connect(
    client_id: str,
    remote_addr: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record WebSocket connection log

    Args:
        client_id: Client identifier
        remote_addr: Client address
        extra: Additional log fields
        logger_instance: Custom logger instance
    """
    log = logger_instance or default_logger
    log_extra = {"client_id": client_id}
    if remote_addr:
        log_extra["remote_addr"] = remote_addr
    if extra:
        log_extra.update(extra)

    log.info(
        f"🔌 WebSocket Connected: {client_id}",
        extra=log_extra,
    )


def log_websocket_disconnect(
    client_id: str,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record WebSocket disconnection log

    Args:
        client_id: Client identifier
        reason: Disconnection reason
        extra: Additional log fields
        logger_instance: Custom logger instance
    """
    log = logger_instance or default_logger
    log_extra = {"client_id": client_id}
    if reason:
        log_extra["reason"] = reason
    if extra:
        log_extra.update(extra)

    reason_str = f" - {reason}" if reason else ""
    log.info(
        f"🔌 WebSocket Disconnected: {client_id}{reason_str}",
        extra=log_extra,
    )


def log_websocket_message(
    client_id: str,
    message_type: str,
    direction: str = "recv",  # "recv" or "send"
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record WebSocket message log

    Args:
        client_id: Client identifier
        message_type: Message type
        direction: Message direction ("recv" or "send")
        extra: Additional log fields
        logger_instance: Custom logger instance
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
        f"{arrow} WS Message: {client_id} [{message_type}]",
        extra=log_extra,
    )


# ============================================================================
# Authentication logs
# ============================================================================


def log_auth_success(
    user_id: str,
    username: Optional[str] = None,
    auth_type: str = "login",
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record authentication success log

    Args:
        user_id: User ID
        username: Username
        auth_type: Authentication type (login, token_refresh, oauth)
        extra: Additional log fields
        logger_instance: Custom logger instance
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
        f"🔓 Authentication Success: {user_str} [{auth_type}]",
        extra=log_extra,
    )


def log_auth_failure(
    reason: str,
    username: Optional[str] = None,
    auth_type: str = "login",
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record authentication failure log

    Args:
        reason: Failure reason
        username: Username
        auth_type: Authentication type
        extra: Additional log fields
        logger_instance: Custom logger instance
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
        f"🔒 Authentication Failed{user_str}: {reason} [{auth_type}]",
        extra=log_extra,
    )


# ============================================================================
# Service startup logs
# ============================================================================


def log_service_startup(
    service_name: str,
    version: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record service startup log

    Args:
        service_name: Service name
        version: Service version
        host: Listening address
        port: Listening port
        extra: Additional log fields
        logger_instance: Custom logger instance
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
        f"🚀 Service Started: {service_name}{version_str}{addr_str}",
        extra=log_extra,
    )


def log_service_shutdown(
    service_name: str,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Record service shutdown log

    Args:
        service_name: Service name
        reason: Shutdown reason
        extra: Additional log fields
        logger_instance: Custom logger instance
    """
    log = logger_instance or default_logger
    log_extra = {"service_name": service_name}
    if reason:
        log_extra["reason"] = reason
    if extra:
        log_extra.update(extra)

    reason_str = f" - {reason}" if reason else ""
    log.info(
        f"🛑 Service Shutdown: {service_name}{reason_str}",
        extra=log_extra,
    )


# ============================================================================
# Export
# ============================================================================

__all__ = [
    # Basic logs
    "log_request_received",
    "log_request_completed",
    "log_operation_start",
    "log_operation_completed",
    "log_operation_failed",
    "log_error",
    "log_warning",
    # Database logs
    "log_db_query",
    "log_db_error",
    # External API logs
    "log_external_api_call",
    "log_external_api_error",
    # Performance tracking
    "timed_operation",
    "timed_operation_sync",
    # Decorators
    "with_request_logging",
    # WebSocket logs
    "log_websocket_connect",
    "log_websocket_disconnect",
    "log_websocket_message",
    # Authentication logs
    "log_auth_success",
    "log_auth_failure",
    # Service logs
    "log_service_startup",
    "log_service_shutdown",
]
