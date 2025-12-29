"""
日志配置模块

基于Loguru提供统一的日志配置和管理功能
支持传统格式日志输出，完整异常堆栈，以及环境变量配置
"""

import json
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional

from loguru import logger


def _rename_old_log_files(log_dir: str, service_name: str) -> None:
    """重命名旧的日志文件，添加日期后缀

    Args:
        log_dir: 日志目录
        service_name: 服务名称
    """
    try:
        from datetime import datetime

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 统一处理普通日志文件和错误日志文件
        log_files = [
            (f"{service_name}.log", f"{service_name}-{{date}}.log"),
            (f"{service_name}_error.log", f"{service_name}_error-{{date}}.log"),
        ]

        for log_file_name, new_name_template in log_files:
            log_file = os.path.join(log_dir, log_file_name)
            if not os.path.exists(log_file):
                continue

            # 获取文件的修改时间
            file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            file_date = file_mtime.replace(hour=0, minute=0, second=0, microsecond=0)

            # 如果文件是昨天的或更早的，重命名它
            if file_date < today:
                date_str = file_date.strftime("%Y-%m-%d")
                new_name = os.path.join(log_dir, new_name_template.format(date=date_str))

                # 如果目标文件已存在，跳过（可能已经被处理过）
                if not os.path.exists(new_name):
                    os.rename(log_file, new_name)
    except Exception:
        # 静默处理异常，避免影响服务启动
        ***REMOVED***


def _get_log_level_from_env() -> str:
    """从环境变量读取日志级别

    优先级：
    1. LOG_LEVEL 环境变量
    2. DEBUG 环境变量（如果为 true，则使用 DEBUG）
    3. 默认 INFO

    Returns:
        日志级别字符串（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    # 优先读取 LOG_LEVEL
    log_level = os.getenv("LOG_LEVEL", "").upper()

    # 如果 LOG_LEVEL 为空，检查 DEBUG 环境变量
    if not log_level:
        if os.getenv("DEBUG", "").lower() in ("true", "1", "yes", "on"):
            log_level = "DEBUG"
        else:
            log_level = "INFO"

    # 验证日志级别有效性
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if log_level not in valid_levels:
        log_level = "INFO"

    return log_level


def configure_logger(
    service_name: str = "service",
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    rotation: str = "00:00",  # 每天午夜轮转（按日期切片）
    retention: str = "30 days",  # 保留30天日志
    compression: str = "zip",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_error_file: bool = True,
) -> None:
    """配置Loguru日志系统

    Args:
        service_name: 服务名称
        log_level: 日志级别（None时从环境变量读取：LOG_LEVEL 或 DEBUG）
        log_dir: 日志目录（None时自动检测：Docker环境使用 /app/logs，本地环境使用 ./logs）
        rotation: 日志轮转策略（默认 "00:00" 每天午夜轮转，也可使用 "10 MB" 按大小、"1 day" 按天）
        retention: 日志保留时间（默认 "30 days" 保留30天，也可使用 "1 week"）
        compression: 日志压缩格式（如 "zip", "gz"）
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        enable_error_file: 是否启用错误日志文件
    """
    # 从环境变量读取日志级别（如果未指定）
    if log_level is None:
        log_level = _get_log_level_from_env()
    else:
        log_level = log_level.upper()
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if log_level not in valid_levels:
            log_level = "INFO"

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
            enable_file = False
            enable_error_file = False

    # ✅ 启用stdlib拦截，让所有logging.getLogger()调用都通过loguru
    # 清除所有现有的logging处理器，避免冲突
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ✅ 配置loguru拦截标准logging（包括uvicorn）
    # 拦截所有标准库的logging调用，统一使用loguru格式
    class InterceptHandler(logging.Handler):
        """拦截标准logging的Handler，将日志转发到loguru"""

        def emit(self, record: logging.LogRecord) -> None:
            # 获取对应的loguru级别
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = str(record.levelno)

            # 查找调用者信息
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            # 转发到loguru
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # 为uvicorn和uvicorn.access设置拦截器
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]

    # 为其他常用库设置拦截器
    logging.getLogger("fastapi").handlers = [InterceptHandler()]

    # 设置根日志记录器级别
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 使用 patcher 在消息中追加 extra 信息
    def patcher(record: Any) -> None:
        """修改记录，在消息后追加 extra 信息"""
        try:
            # 收集 extra 字段（排除 service_name 和 name，因为它们已经在格式中显示）
            extra_data = {}
            for key, value in record["extra"].items():
                if key not in ("service_name", "name"):
                    extra_data[key] = value

            # 如果有 extra 信息，追加到消息中
            if extra_data:
                original_message = record.get("message", "")

                # 检查是否有异常信息（如果有异常，不将 extra 格式化为 JSON，让异常堆栈使用原始格式）
                has_exception = record.get("exception") is not None

                if not has_exception:
                    # 非异常情况，使用 JSON 格式
                    try:
                        extra_json = json.dumps(extra_data, ensure_ascii=False, indent=2, default=str)
                        # 只有当原始消息不包含"额外信息"时才添加
                        if "额外信息" not in str(original_message):
                            # 确保消息末尾没有多余换行，然后追加额外信息
                            msg_clean = str(original_message).rstrip("\n")
                            record["message"] = f"{msg_clean}\n额外信息:\n{extra_json}"
                    except Exception:
                        try:
                            msg_clean = str(original_message).rstrip("\n")
                            record["message"] = f"{msg_clean}\n额外信息: {extra_data!s}"
                        except Exception:
                            ***REMOVED***
        except Exception:
            # 静默处理异常，避免影响日志输出
            ***REMOVED***

    # 传统格式日志模板
    # 格式：时间 级别 [服务名] 模块名:函数名:行号 - 消息
    # 异常时自动追加完整堆栈信息
    traditional_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} "
        "{level: <8} "
        "[{extra[service_name]}] "
        "{name}:{function}:{line} - "
        "{message}"
        "{exception}"
    )

    # 构建处理器配置
    handlers_config: Any = []

    # 控制台输出（传统格式）
    if enable_console:
        handlers_config.append(
            {
                "sink": sys.stdout,
                "format": traditional_format,
                "level": log_level,
                "colorize": True,  # 启用颜色输出
            }
        )

    # 文件输出（传统格式）
    if enable_file:
        # 当天日志使用固定文件名，轮转后的旧日志才添加日期后缀
        log_file_path = os.path.join(log_dir, f"{service_name}.log")

        # 在启动时检查并重命名旧的日志文件（如果存在且不是今天的）
        _rename_old_log_files(log_dir, service_name)

        handlers_config.append(
            {
                "sink": log_file_path,
                "format": traditional_format,
                "level": log_level,
                "rotation": rotation,  # 每天午夜轮转（默认 "00:00"）
                "retention": retention,
                "compression": compression,
                "encoding": "utf-8",
            }
        )

    # 错误文件输出（仅ERROR及以上级别）
    if enable_error_file:
        # 当天错误日志使用固定文件名，轮转后的旧日志才添加日期后缀
        error_log_file_path = os.path.join(log_dir, f"{service_name}_error.log")

        handlers_config.append(
            {
                "sink": error_log_file_path,
                "format": traditional_format,
                "level": "ERROR",  # 仅记录ERROR及以上级别
                "rotation": rotation,  # 每天午夜轮转（默认 "00:00"）
                "retention": "1 month",
                "compression": compression,
                "encoding": "utf-8",
            }
        )

    # 配置logger，绑定服务名称到extra，并应用 patcher
    logger.configure(
        handlers=handlers_config,
        extra={"service_name": service_name},  # 绑定服务名称到extra
        patcher=patcher,  # 应用 patcher 追加 extra 信息到消息
    )

    # ✅ 设置常用库的日志级别（已通过InterceptHandler拦截，统一使用loguru格式）
    logging.getLogger("uvicorn").setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logging.getLogger("uvicorn.error").setLevel(getattr(logging, log_level.upper(), logging.INFO))
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


def log_slow_query(
    sql: str,
    duration_ms: float,
    operation: str,
    table: str,
    sql_hash: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> None:
    """记录慢查询

    Args:
        sql: SQL语句
        duration_ms: 执行时间（毫秒）
        operation: 操作类型（select, insert, update, delete等）
        table: 表名
        sql_hash: SQL哈希值（用于去重）
        parameters: SQL参数（可选）
    """
    # 获取调用堆栈（排除当前函数和监控模块）
    stack_trace = []
    for frame in traceback.extract_stack()[:-2]:  # 排除当前函数和监控函数
        if "sql_performance" not in frame.filename:
            stack_trace.append(f"{frame.filename}:{frame.lineno} in {frame.name}")

    logger.warning(
        f"慢查询检测: {operation.upper()} on {table} ({duration_ms:.2f}ms)",
        extra={
            "sql": sql,
            "duration_ms": duration_ms,
            "duration_seconds": duration_ms / 1000.0,
            "operation": operation,
            "table": table,
            "sql_hash": sql_hash,
            "parameters": parameters,
            "stack_trace": stack_trace[-5:],  # 只保留最近5层堆栈
        },
    )
