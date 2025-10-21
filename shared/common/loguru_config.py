"""
Log Configuration Module

Provides unified log configuration and management functions based on Loguru
Supports traditional format log output, complete exception stack traces, and environment variable configuration
"""

import json
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional

from loguru import logger


def _rename_old_log_files(log_dir: str, service_name: str) -> None:
    """Rename old log files, adding date suffix

    Args:
        log_dir: Log directory
        service_name: Service name
    """
    try:
        from datetime import datetime

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Uniformly handle regular log files and error log files
        log_files = [
            (f"{service_name}.log", f"{service_name}-{{date}}.log"),
            (f"{service_name}_error.log", f"{service_name}_error-{{date}}.log"),
        ]

        for log_file_name, new_name_template in log_files:
            log_file = os.path.join(log_dir, log_file_name)
            if not os.path.exists(log_file):
                continue

            # Get file modification time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            file_date = file_mtime.replace(hour=0, minute=0, second=0, microsecond=0)

            # If file is from yesterday or earlier, rename it
            if file_date < today:
                date_str = file_date.strftime("%Y-%m-%d")
                new_name = os.path.join(log_dir, new_name_template.format(date=date_str))

                # If target file already exists, skip (may have been processed already)
                if not os.path.exists(new_name):
                    os.rename(log_file, new_name)
    except Exception:
        # Silently handle exceptions, avoid affecting service startup
        ***REMOVED***


def _get_log_level_from_env() -> str:
    """Read log level from environment variables

    Priority:
    1. LOG_LEVEL environment variable
    2. DEBUG environment variable (if true, use DEBUG)
    3. Default INFO

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Prioritize reading LOG_LEVEL
    log_level = os.getenv("LOG_LEVEL", "").upper()

    # If LOG_LEVEL is empty, check DEBUG environment variable
    if not log_level:
        if os.getenv("DEBUG", "").lower() in ("true", "1", "yes", "on"):
            log_level = "DEBUG"
        else:
            log_level = "INFO"

    # Validate log level validity
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if log_level not in valid_levels:
        log_level = "INFO"

    return log_level


def configure_logger(
    service_name: str = "service",
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    rotation: str = "00:00",  # Rotate at midnight daily (by date slicing)
    retention: str = "30 days",  # Retain logs for 30 days
    compression: str = "zip",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_error_file: bool = True,
) -> None:
    """Configure Loguru logging system

    Args:
        service_name: Service name
        log_level: Log level (when None, read from environment variables: LOG_LEVEL or DEBUG)
        log_dir: Log directory (when None, auto-detect: Docker environment uses /app/logs,
            local environment uses ./logs)
        rotation: Log rotation strategy (default "00:00" rotates at midnight daily,
            can also use "10 MB" by size, "1 day" by day)
        retention: Log retention time (default "30 days" retains for 30 days, can also use "1 week")
        compression: Log compression format (e.g. "zip", "gz")
        enable_console: Whether to enable console output
        enable_file: Whether to enable file output
        enable_error_file: Whether to enable error log file
    """
    # Read log level from environment variables (if not specified)
    if log_level is None:
        log_level = _get_log_level_from_env()
    else:
        log_level = log_level.upper()
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if log_level not in valid_levels:
            log_level = "INFO"

    # Auto-detect log directory
    if log_dir is None:
        # Check if in Docker environment (/app directory exists and is writable)
        docker_log_dir = "/app/logs"
        if os.path.exists("/app") and os.access("/app", os.W_OK):
            log_dir = docker_log_dir
        else:
            # Local environment: Use logs directory under project root
            # Find project root directory from current file location upward (containing .git or docker-compose.yml)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            max_depth = 10
            depth = 0
            while depth < max_depth:
                if os.path.exists(os.path.join(project_root, ".git")) or os.path.exists(
                    os.path.join(project_root, "docker-compose.yml")
                ):
                    log_dir = os.path.join(project_root, "logs")
                    break
                parent_dir = os.path.dirname(project_root)
                if parent_dir == project_root:
                    # Reached root directory, use logs under current directory
                    log_dir = os.path.join(os.getcwd(), "logs")
                    break
                project_root = parent_dir
                depth += 1
            else:
                # If project root not found, use logs under current working directory
                log_dir = os.path.join(os.getcwd(), "logs")

    # Remove default log handlers
    logger.remove()

    # Create log directory
    if enable_file or enable_error_file:
        from pathlib import Path

        try:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
<<<<<<< HEAD
<<<<<<< HEAD
        except (PermissionError, OSError):
            # If no permission to create log directory, use console output and log warning
=======
        except (PermissionError, OSError) as e:
            # 如果没有权限创建日志目录，使用控制台输出并记录警告
            print(f"警告: 无法创建日志目录 {log_dir}: {e}")
            print("将仅使用控制台日志输出")
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
        except (PermissionError, OSError):
            # 如果没有权限创建日志目录，使用控制台输出并记录警告
            # 此时 logger 还未初始化，仅在启动时输出一次
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
            enable_file = False
            enable_error_file = False

    # ✅ Enable stdlib interception, make all logging.getLogger() calls go through loguru
    # Clear all existing logging handlers, avoid conflicts
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ✅ Configure loguru to intercept standard logging (including uvicorn)
    # Intercept all standard library logging calls, use loguru format uniformly
    class InterceptHandler(logging.Handler):
        """Handler that intercepts standard logging, forward logs to loguru"""

        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding loguru level
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = str(record.levelno)

            # Find caller information
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            # Forward to loguru
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Set interceptors for uvicorn and uvicorn.access
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]

    # Set interceptors for other common libraries
    logging.getLogger("fastapi").handlers = [InterceptHandler()]

    # Set root logger level
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Use patcher to append extra information and request context to messages
    def patcher(record: Any) -> None:
        """Modify record, append extra information and request context after message"""
        try:
            # ✅ Automatically inject request context
            try:
                from shared.middleware.request_context_middleware import (
                    get_request_context,
                )

                request_context = get_request_context()
                if request_context:
                    # Inject request context into extra
                    for key, value in request_context.items():
                        if key not in record["extra"]:
                            record["extra"][key] = value
            except ImportError:
                # If request context middleware not imported, skip
                ***REMOVED***

            # Collect extra fields (exclude service_name and name, as they are already displayed in format)
            extra_data = {}
            for key, value in record["extra"].items():
                if key not in ("service_name", "name"):
                    extra_data[key] = value

            # If there are extra information, append to message
            if extra_data:
                original_message = record.get("message", "")

                # Check if there are exception information (if there are exceptions, don't format extra as JSON,
                # let exception stack use original format)
                # Always append extra information, even if there is an exception
                # This ensures context (like host_id) is visible alongside the stack trace
                try:
                    # Format as key-value pairs
                    extra_lines = []
                    for k, v in extra_data.items():
                        extra_lines.append(f"  {k}: {v}")
                    extra_text = "\n".join(extra_lines)

                    # Only add when original message doesn't contain "extra information"
                    if "extra information" not in str(original_message):
                        # Ensure message doesn't have trailing newlines, then append extra information
                        msg_clean = str(original_message).rstrip("\n")
                        record["message"] = f"{msg_clean}\nExtra information:\n{extra_text}"
                except Exception:
                    try:
                        msg_clean = str(original_message).rstrip("\n")
                        record["message"] = f"{msg_clean}\nExtra information: {extra_data!s}"
                    except Exception:
                        ***REMOVED***
        except Exception:
            # Silently handle exceptions, avoid affecting log output
            ***REMOVED***

    # Traditional format log template
    # Format: Time Level [Service Name] Module:Function:Line - Message
    # Automatically append complete stack trace on exceptions
    traditional_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} "
        "{level: <8} "
        "[{extra[service_name]}] "
        "{name}:{function}:{line} - "
        "{message}"
        "{exception}"
    )

    # Build handler configuration
    handlers_config: Any = []

    # Console output (traditional format)
    if enable_console:
        handlers_config.append(
            {
                "sink": sys.stdout,
                "format": traditional_format,
                "level": log_level,
                "colorize": True,  # Enable color output
            }
        )

    # File output (traditional format)
    if enable_file:
        # Today's logs use fixed filename, only rotated old logs add date suffix
        log_file_path = os.path.join(log_dir, f"{service_name}.log")

        # At startup, check and rename old log files (if they exist and are not from today)
        _rename_old_log_files(log_dir, service_name)

        handlers_config.append(
            {
                "sink": log_file_path,
                "format": traditional_format,
                "level": log_level,
                "rotation": rotation,  # Rotate at midnight daily (default "00:00")
                "retention": retention,
                "compression": compression,
                "encoding": "utf-8",
                "backtrace": True,  # Show traceback extending beyond catch point
                "diagnose": True,  # Show variable values in traceback
                "enqueue": True,  # ✅ Enable asynchronous writing to avoid blocking
            }
        )

    # Error file output (ERROR and above levels only)
    if enable_error_file:
        # Today's error logs use fixed filename, only rotated old logs add date suffix
        error_log_file_path = os.path.join(log_dir, f"{service_name}_error.log")

        handlers_config.append(
            {
                "sink": error_log_file_path,
                "format": traditional_format,
                "level": "ERROR",  # Only record ERROR and above levels
                "rotation": rotation,  # Rotate at midnight daily (default "00:00")
                "retention": "1 month",
                "compression": compression,
                "encoding": "utf-8",
                "backtrace": True,  # Show traceback extending beyond catch point
                "diagnose": True,  # Show variable values in traceback
                "enqueue": True,  # ✅ Enable asynchronous writing to avoid blocking
            }
        )

    # Configure logger, bind service name to extra, and apply patcher
    logger.configure(
        handlers=handlers_config,
        extra={"service_name": service_name},  # Bind service name to extra
        patcher=patcher,  # Apply patcher to append extra information to message
    )

    # ✅ Set log levels for common libraries (already intercepted via InterceptHandler, use loguru format uniformly)
    logging.getLogger("uvicorn").setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logging.getLogger("uvicorn.error").setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logging.getLogger("fastapi").setLevel(getattr(logging, log_level.upper(), logging.INFO))

    logger.info(f"Log system initialization completed - Service: {service_name}, Level: {log_level}")


def get_logger(name: Optional[str] = None) -> Any:
    """Get logger

    Args:
        name: Logger name (usually use __name__)

    Returns:
        Configured logger
    """
    if name:
        return logger.bind(name=name)
    return logger


def log_with_context(
    level: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """Context-aware logging

    Automatically inject request context (request_id, user_id, etc.) into logs.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        extra: Additional log fields
        logger_instance: Custom logger instance, if None use default logger
    """
    log = logger_instance or logger
    log_extra = extra.copy() if extra else {}

    # Try to inject request context
    try:
        from shared.middleware.request_context_middleware import get_request_context

        request_context = get_request_context()
        if request_context:
            for key, value in request_context.items():
                if key not in log_extra:
                    log_extra[key] = value
    except ImportError:
        ***REMOVED***

    # Record log
    log.log(level.upper(), message, extra=log_extra)


def set_log_level(level: str) -> None:
    """Dynamically set log level

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    level = level.upper()
    if level not in valid_levels:
        logger.warning(f"Invalid log level: {level}, keeping current level")
        return

    # Update levels of all handlers
    for handler_id in logger._core.handlers:
        logger._core.handlers[handler_id]._levelno = logger.level(level).no

    logger.info(f"Log level updated to: {level}")


def log_slow_query(
    sql: str,
    duration_ms: float,
    operation: str,
    table: str,
    sql_hash: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> None:
    """Record slow query

    Args:
        sql: SQL statement
        duration_ms: Execution time (milliseconds)
        operation: Operation type (select, insert, update, delete, etc.)
        table: Table name
        sql_hash: SQL hash value (for deduplication)
        parameters: SQL parameters (optional)
    """
    # Get call stack (excluding current function and monitoring module)
    stack_trace = []
    for frame in traceback.extract_stack()[:-2]:  # Exclude current function and monitoring function
        if "sql_performance" not in frame.filename:
            stack_trace.append(f"{frame.filename}:{frame.lineno} in {frame.name}")

    logger.warning(
        f"Slow query detected: {operation.upper()} on {table} ({duration_ms:.2f}ms)",
        extra={
            "sql": sql,
            "duration_ms": duration_ms,
            "duration_seconds": duration_ms / 1000.0,
            "operation": operation,
            "table": table,
            "sql_hash": sql_hash,
            "parameters": parameters,
            "stack_trace": stack_trace[-5:],  # Only retain recent 5 stack frames
        },
    )
