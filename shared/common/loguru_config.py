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

    # 使用 patcher 在消息中追加 extra 信息
    # 注意：必须在 configure 之前应用 patcher
    def patcher(record: Any) -> None:
        """修改记录，在消息后追加 extra 信息"""
        # Loguru 的 record 对象在 patcher 中是一个字典
        # extra 参数中的键值对会被直接添加到 record 字典中
        try:
            # Loguru 的标准字段列表
            standard_fields = {
                "time", "level", "message", "name", "function", "line", "file",
                "process", "thread", "exception", "elapsed", "extra", "record",
                "module", "pathname", "exc_info", "exc_text", "stack", "created",
                "msecs", "relativeCreated", "threadName", "threadId", "taskName",
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
            
            # 仅在 DEBUG 或 ERROR/CRITICAL 级别显示额外信息
            # 这样可以保证调试方便，同时异常发生时也能看到上下文
            allowed_levels = ("DEBUG", "ERROR", "CRITICAL")
            if extra_data and len(extra_data) > 0 and record["level"].name in allowed_levels:
                # 检查消息中是否已经包含这些数据的 JSON 表示（简单的去重检查）
                # 这里只做简单的检查，避免明显的重复
                msg_str = str(original_message)
                
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
                        record["message"] = f"{msg_str}\n额外信息: {str(extra_data)}"
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

            # 构建日志头部（固定格式）
            # 时间 | 级别(补齐8位) | 服务名 | 模块:函数:行号 | 
            header = f"{time_str} | {level: <8} | {service_name} | {name}:{function}:{line} | "
            
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
                    if line: # 非空行
                        formatted_lines.append(indent_str + line)
                    else: # 空行
                        formatted_lines.append("")
            else:
                # 单行消息
                formatted_lines.append(header + msg_text)

            # 最终拼接
            formatted = "\n".join(formatted_lines)

            # 添加异常信息（如果有）
            if exception:
                # Loguru 的 exception 字段是一个特殊的对象
                # message 已经包含了异常信息的摘要，这里主要是堆栈
                # 但通常 loguru 会自动处理异常显示，如果我们在 sink 中只打印 message，
                # 可能需要手动获取格式化的异常信息
                # 这里简单起见，如果 message 末尾没有异常信息，由于 patcher 也没法很好处理 exception 对象
                # 我们依赖 message.record["exception"] 存在时，
                # Loguru 默认的 sink 行为是会打印堆栈的。
                # 但在我们自定义 sink 中，我们需要自己处理。
                # message 参数其实是一个字符串（FormattedMessage），但也包含了 record 属性
                # 如果直接打印 message，通常包含了格式化好的异常信息（如果 format 参数配置了 {exception}）
                # 但我们需要自定义格式。
                
                # 实际上，如果 format 中包含了 {exception}，那么 msg_text 可能已经包含了堆栈信息（取决于实现）
                # 只有当 format 字符串包含 {exception} 时，Loguru 才会把异常栈拼接到 message 中。
                # 我们的 console_sink 使用的是 raw message (from record["message"])，
                # 它不包含堆栈，除非我们在 patcher 里处理了（但 patcher 里很难处理堆栈格式化）。
                
                # 在自定义 sink 中，我们需要显式处理异常
                # 获取格式化的异常堆栈
                exc = record["exception"]
                if exc:
                    # 使用 loguru 内部的方法格式化异常（比较复杂），或者直接用 traceback
                    # 简单方式：
                    import traceback
                    exc_lines = traceback.format_exception(exc.type, exc.value, exc.traceback)
                    exc_str = "".join(exc_lines)
                    
                    # 对堆栈信息每行加缩进
                    for exc_line in exc_str.split("\n"):
                        if exc_line:
                            formatted += f"\n{indent_str}{exc_line}"

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
