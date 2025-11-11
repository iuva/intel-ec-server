"""
日志配置模块

基于Loguru提供统一的日志配置和管理功能
"""

import logging
import os
import sys
from typing import Any, Optional

from loguru import logger


def _rename_old_log_files(log_dir: str, service_name: str) -> None:
    """重命名旧的日志文件，添加日期后缀
    
    Args:
        log_dir: 日志目录
        service_name: 服务名称
    """
    try:
        from datetime import datetime

        log_file = os.path.join(log_dir, f"{service_name}.log")
        error_log_file = os.path.join(log_dir, f"{service_name}_error.log")

        # 检查普通日志文件
        if os.path.exists(log_file):
            # 获取文件的修改时间
            file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 如果文件是昨天的或更早的，重命名它
            file_date = file_mtime.replace(hour=0, minute=0, second=0, microsecond=0)
            if file_date < today:
                date_str = file_date.strftime("%Y-%m-%d")
                new_name = os.path.join(log_dir, f"{service_name}-{date_str}.log")
                
                # 如果目标文件已存在，跳过（可能已经被处理过）
                if not os.path.exists(new_name):
                    os.rename(log_file, new_name)

        # 检查错误日志文件
        if os.path.exists(error_log_file):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(error_log_file))
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            file_date = file_mtime.replace(hour=0, minute=0, second=0, microsecond=0)
            if file_date < today:
                date_str = file_date.strftime("%Y-%m-%d")
                new_name = os.path.join(log_dir, f"{service_name}_error-{date_str}.log")
                
                if not os.path.exists(new_name):
                    os.rename(error_log_file, new_name)
    except Exception:
        # 静默处理异常，避免影响服务启动
        ***REMOVED***


def configure_logger(
    service_name: str = "service",
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    rotation: str = "00:00",  # 每天午夜轮转（按日期切片）
    retention: str = "30 days",  # 保留30天日志
    compression: str = "zip",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_error_file: bool = True,
    json_format: bool = False,
) -> None:
    """配置Loguru日志系统

    Args:
        service_name: 服务名称
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_dir: 日志目录（None时自动检测：Docker环境使用 /app/logs，本地环境使用 ./logs）
        rotation: 日志轮转策略（默认 "00:00" 每天午夜轮转，也可使用 "10 MB" 按大小、"1 day" 按天）
        retention: 日志保留时间（默认 "30 days" 保留30天，也可使用 "1 week"）
        compression: 日志压缩格式（如 "zip", "gz"）
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        enable_error_file: 是否启用错误日志文件
        json_format: 是否使用JSON格式
    """
    # 自动检测日志目录
    if log_dir is None:
        # 检查是否在Docker环境中（/app目录存在且可写）
        docker_log_dir = "/app/logs"
        if os.path.exists("/app") and os.access("/app", os.W_OK):
            log_dir = docker_log_dir
        else:
            # 本地环境：使用项目根目录下的 logs 目录
            # 从当前文件位置向上查找项目根目录（包含 .git 或 docker-compose.yml）
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
                    # 已到根目录，使用当前目录下的logs
                    log_dir = os.path.join(os.getcwd(), "logs")
                    break
                project_root = parent_dir
                depth += 1
            else:
                # 如果找不到项目根，使用当前工作目录下的logs
                log_dir = os.path.join(os.getcwd(), "logs")

    # 移除默认的日志处理器
    logger.remove()

    # 创建日志目录
    if enable_file or enable_error_file:
        from pathlib import Path

        try:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # 如果没有权限创建日志目录，使用控制台输出并记录警告
            # 此时 logger 还未初始化，仅在启动时输出一次
            enable_file = False
            enable_error_file = False

    # 启用stdlib拦截，让所有logging.getLogger()调用都通过loguru
    # 使用loguru的intercept_stdlib()方法
    # 清除所有现有的logging处理器，避免冲突
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 配置loguru拦截标准logging

    # 构建处理器配置，不使用 cast() 避免类型错误
    handlers_config: Any = [
        {
            "sink": sys.stdout,
            "format": (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                f"<cyan>{service_name}</cyan> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
                "{exception}"  # 添加异常堆栈信息（仅在异常时显示）
            ),
            "level": log_level,
            "colorize": True,
        }
    ]

    # 添加文件处理器（如果启用）
    if enable_file:
        # 当天日志使用固定文件名，轮转后的旧日志才添加日期后缀
        # 当天文件：service_name.log
        # 历史文件：service_name-YYYY-MM-DD.log
        log_file_path = os.path.join(log_dir, f"{service_name}.log")

        # 在启动时检查并重命名旧的日志文件（如果存在且不是今天的）
        _rename_old_log_files(log_dir, service_name)

        handlers_config.append(
            {
                "sink": log_file_path,
                "format": (
                    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                    "{level: <8} | "
                    f"{service_name} | "
                    "{name}:{function}:{line} | "
                    "{message}"
                    "{exception}"  # 添加异常堆栈信息（仅在异常时显示）
                ),
                "level": log_level,
                "rotation": rotation,  # 每天午夜轮转（默认 "00:00"）
                "retention": retention,
                "compression": compression,
                "encoding": "utf-8",
            }
        )

    # 添加错误文件处理器（如果启用）
    if enable_error_file:
        # 当天错误日志使用固定文件名，轮转后的旧日志才添加日期后缀
        # 当天文件：service_name_error.log
        # 历史文件：service_name_error-YYYY-MM-DD.log
        error_log_file_path = os.path.join(log_dir, f"{service_name}_error.log")
        
        handlers_config.append(
            {
                "sink": error_log_file_path,
                "format": (
                    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                    "{level: <8} | "
                    f"{service_name} | "
                    "{name}:{function}:{line} | "
                    "{message}"
                    "{exception}"  # 添加异常堆栈信息（仅在异常时显示）
                ),
                "level": "ERROR",
                "rotation": rotation,  # 每天午夜轮转（默认 "00:00"）
                "retention": "1 month",
                "compression": compression,
                "encoding": "utf-8",
            }
        )

    # 使用类型安全的配置调用
    logger.configure(handlers=handlers_config)

    # 配置常用库的日志级别（uvicorn日志由各服务单独处理）
    logging.getLogger("fastapi").setLevel(getattr(logging, log_level.upper(), logging.INFO))

    logger.info(f"日志系统初始化完成 - 服务: {service_name}, 级别: {log_level}")


def get_logger(name: Optional[str] = None) -> Any:
    """获取日志记录器

    Args:
        name: 日志记录器名称（通常使用 __name__）

    Returns:
        配置好的日志记录器
    """
    if name:
        return logger.bind(name=name)
    return logger


def log_function_call(func_name: str, args: tuple, kwargs: dict) -> None:
    """记录函数调用

    Args:
        func_name: 函数名
        args: 位置参数
        kwargs: 关键字参数
    """
    logger.debug(
        f"函数调用: {func_name}",
        extra={"function": func_name, "args": str(args), "kwargs": str(kwargs)},
    )


def log_exception(exception: Exception, context: Optional[dict] = None) -> None:
    """记录异常信息

    Args:
        exception: 异常对象
        context: 上下文信息
    """
    logger.exception(f"异常发生: {type(exception).__name__}: {exception!s}", extra=context or {})


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
) -> None:
    """记录HTTP请求

    Args:
        method: HTTP方法
        path: 请求路径
        status_code: 响应状态码
        duration_ms: 请求耗时（毫秒）
        user_id: 用户ID
    """
    logger.info(
        f"HTTP请求: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
        },
    )


def log_database_query(query: str, duration_ms: float, rows_affected: Optional[int] = None) -> None:
    """记录数据库查询

    Args:
        query: SQL查询语句
        duration_ms: 查询耗时（毫秒）
        rows_affected: 影响的行数
    """
    logger.debug(
        f"数据库查询: {query[:100]}... ({duration_ms:.2f}ms)",
        extra={
            "query": query,
            "duration_ms": duration_ms,
            "rows_affected": rows_affected,
        },
    )


def log_cache_operation(
    operation: str,
    key: str,
    hit: Optional[bool] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """记录缓存操作

    Args:
        operation: 操作类型（get, set, delete）
        key: 缓存键
        hit: 是否命中（仅用于get操作）
        duration_ms: 操作耗时（毫秒）
    """
    if hit is not None:
        status = "命中" if hit else "未命中"
        logger.debug(
            f"缓存{operation}: {key} - {status}",
            extra={
                "operation": operation,
                "key": key,
                "hit": hit,
                "duration_ms": duration_ms,
            },
        )
    else:
        logger.debug(
            f"缓存{operation}: {key}",
            extra={"operation": operation, "key": key, "duration_ms": duration_ms},
        )


def log_service_call(service_name: str, endpoint: str, method: str, status_code: int, duration_ms: float) -> None:
    """记录服务间调用

    Args:
        service_name: 服务名称
        endpoint: 端点路径
        method: HTTP方法
        status_code: 响应状态码
        duration_ms: 调用耗时（毫秒）
    """
    logger.info(
        f"服务调用: {service_name} {method} {endpoint} - {status_code} ({duration_ms:.2f}ms)",
        extra={
            "service_name": service_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
        },
    )
