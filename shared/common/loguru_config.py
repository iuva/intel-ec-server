"""
日志配置模块

基于Loguru提供统一的日志配置和管理功能
"""

import json
import logging
import os
import sys
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
    # 注意：必须在 configure 之前应用 patcher
    def patcher(record: Any) -> None:
        """修改记录，在消息后追加 extra 信息"""
        # Loguru 的 record 对象在 patcher 中是一个字典
        # extra 参数中的键值对会被直接添加到 record 字典中
        try:
            # Loguru 的标准字段列表
            standard_fields = {
                "time",
                "level",
                "message",
                "name",
                "function",
                "line",
                "file",
                "process",
                "thread",
                "exception",
                "elapsed",
                "extra",
                "record",
                "module",
                "pathname",
                "exc_info",
                "exc_text",
                "stack",
                "created",
                "msecs",
                "relativeCreated",
                "threadName",
                "threadId",
                "taskName",
            }

            # 收集 extra 字段（所有非标准字段）
            extra_data = {}

            # record 在 patcher 中是字典类型
            if isinstance(record, dict):
                # 优先从 record['extra'] 中获取（如果是通过 bind() 绑定的）
                if "extra" in record and isinstance(record["extra"], dict):
                    extra_data.update(record["extra"])

                # 也可以从 record 根级别获取（某些情况下）
                for key, value in record.items():
                    # 跳过标准字段和以 _ 开头的内部字段
                    if key not in standard_fields and not key.startswith("_"):
                        extra_data[key] = value

            # 如果 extra 数据不为空，且消息中还没有包含额外信息，则追加到消息中
            original_message = record.get("message", "")

            # ✅ 检查是否有异常信息（如果有异常，不将 extra 格式化为 JSON，让异常堆栈使用原始格式）
            has_exception = record.get("exception") is not None or record.get("exc_info") is not None

            # 仅在 DEBUG 或 ERROR/CRITICAL 级别显示额外信息
            # 这样可以保证调试方便，同时异常发生时也能看到上下文
            allowed_levels = ("DEBUG", "ERROR", "CRITICAL")
            if extra_data and len(extra_data) > 0 and record["level"].name in allowed_levels:
                # 检查消息中是否已经包含这些数据的 JSON 表示（简单的去重检查）
                # 这里只做简单的检查，避免明显的重复
                msg_str = str(original_message)

                # ✅ 如果有异常信息，不添加额外信息到消息中，让异常堆栈使用原始格式显示
                # 异常堆栈信息会由 console_sink 函数自动处理，使用 traceback 原始格式
                if has_exception:
                    # 异常情况下，不修改消息内容，让 loguru 的异常处理机制正常工作
                    # 异常堆栈会通过 record["exception"] 字段由 console_sink 函数处理
                    # 这样可以确保异常堆栈使用原始格式（traceback），而不是 JSON 格式
                    # ✅ 不添加任何额外信息到消息中，确保异常堆栈信息清晰可见
                    ***REMOVED***  # 不添加额外信息，避免干扰异常堆栈显示
                else:
                    # 非异常情况，使用 JSON 格式（保持原有行为）
                    # 定义 JSON 序列化辅助函数，处理不可序列化类型
                    def default_serializer(obj):
                        if isinstance(obj, bytes):
                            return "<bytes>"
                        return str(obj)

                    try:
                        # 使用 indent=2 格式化 JSON
                        extra_json = json.dumps(extra_data, default=default_serializer, ensure_ascii=False, indent=2)

                        # 只有当原始消息不包含"额外信息"且看起来不像已经包含了这个JSON时才添加
                        if "额外信息" not in msg_str:
                            record["message"] = f"{msg_str}\n额外信息:\n{extra_json}"
                    except Exception:
                        try:
                            record["message"] = f"{msg_str}\n额外信息: {extra_data!s}"
                        except Exception:
                            ***REMOVED***
        except Exception:
            # 静默处理异常，避免影响日志输出
            ***REMOVED***

    # 在 configure 之前应用 patcher
    # logger.patch(patcher)  <-- 移除这行，改用 configure 参数

    # 构建处理器配置，使用自定义 sink 函数确保多行消息正确显示
    def console_sink(message: Any) -> None:
        """自定义控制台 sink 函数，确保多行消息正确显示且格式美观

        优化特性：
        1. 正确处理多行消息，后续行自动添加缩进，保持对齐
        2. 保留 JSON 格式的额外信息，确保完整显示
        3. 异常堆栈信息也会正确格式化并添加缩进
        4. 单行消息直接显示，性能最优
        """
        try:
            record = message.record

            # 提取记录信息
            time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            level = record["level"].name
            name = record["name"]
            function = record["function"]
            line = record["line"]
            msg_text = record["message"]
            exception = record.get("exception")

            # ✅ 优化日志格式：简化模块路径，只显示文件名
            # 例如：services.host-service.app.services.host_discovery_service -> host_discovery_service
            module_name = name.split(".")[-1] if "." in name else name

            # 构建日志头部（优化后的格式）
            # 时间 | 级别(补齐8位) | 服务名 | 模块名:函数名:行号 |
            header = f"{time_str} | {level: <8} | {service_name} | {module_name}:{function}:{line} | "

            # 计算缩进字符串
            indent_str = " " * len(header)

            # 处理消息文本
            formatted_lines = []

            if "\n" in msg_text:
                # 分割多行消息
                lines = msg_text.split("\n")

                # 第一行包含 header
                formatted_lines.append(header + lines[0])

                # 后续行添加缩进
                for line in lines[1:]:
                    if line:  # 非空行
                        formatted_lines.append(indent_str + line)
                    else:  # 空行
                        formatted_lines.append("")
            else:
                # 单行消息
                formatted_lines.append(header + msg_text)

            # 最终拼接
            formatted = "\n".join(formatted_lines)

            # 添加异常信息（如果有）
            # ✅ 检查多种方式获取异常信息，确保完整打印堆栈
            import traceback

            def format_exception_to_string(exc_type, exc_value, exc_traceback) -> str:
                """格式化异常堆栈为字符串"""
                try:
                    exc_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                    return "".join(exc_lines)
                except Exception:
                    return ""

            def append_exception_lines(exc_str: str) -> None:
                """将异常堆栈行追加到 formatted"""
                nonlocal formatted
                for exc_line in exc_str.split("\n"):
                    if exc_line.strip():  # 只处理非空行
                        formatted += f"\n{indent_str}{exc_line}"
                    else:
                        formatted += "\n"  # 保留空行以保持堆栈格式

            # 尝试多种方式获取异常信息
            exc_handled = False

            # 方式1: 从 exception 对象获取
            if (
                exception
                and hasattr(exception, "type")
                and hasattr(exception, "value")
                and hasattr(exception, "traceback")
            ):
                exc_str = format_exception_to_string(exception.type, exception.value, exception.traceback)
                if exc_str:
                    append_exception_lines(exc_str)
                    exc_handled = True

            # 方式2: 从 record["exception"] 获取
            if not exc_handled and "exception" in record:
                exc = record["exception"]
                if hasattr(exc, "type") and hasattr(exc, "value") and hasattr(exc, "traceback"):
                    exc_str = format_exception_to_string(exc.type, exc.value, exc.traceback)
                    if exc_str:
                        append_exception_lines(exc_str)
                        exc_handled = True

            # 方式3: 从 exc_info 元组获取
            if not exc_handled and "exc_info" in record and record["exc_info"]:
                if isinstance(record["exc_info"], tuple) and len(record["exc_info"]) == 3:
                    exc_type, exc_value, exc_traceback = record["exc_info"]
                    exc_str = format_exception_to_string(exc_type, exc_value, exc_traceback)
                    if exc_str:
                        append_exception_lines(exc_str)

            # 输出到控制台
            print(formatted, file=sys.stdout, flush=True)

        except Exception as e:
            # 如果格式化失败，直接输出原始消息
            print(str(message), file=sys.stdout, flush=True)
            # 避免死循环，不再打印错误日志
            print(f"Logging Error: {e}", file=sys.stderr)

    handlers_config: Any = [
        {
            "sink": console_sink,
            "level": log_level,
            "colorize": False,
            # console_sink 不需要 format 参数，因为它直接处理 message.record
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
    # 注意：patcher 已经在 configure 之前应用
    logger.configure(handlers=handlers_config, patcher=patcher)

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
    import traceback

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
