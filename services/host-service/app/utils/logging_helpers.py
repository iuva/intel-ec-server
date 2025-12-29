"""日志记录辅助函数

提供统一的日志记录工具函数，减少重复的日志代码。
"""

from typing import Any, Dict, Optional

from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def log_request_received(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录请求接收日志

    Args:
        operation: 操作名称（如 "query_available_hosts", "report_hardware"）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例，如果为 None 则使用模块默认 logger
    """
    log = logger_instance or logger
    log.info(
        f"接收 {operation} 请求",
        extra=extra or {},
    )


def log_request_completed(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录请求处理完成日志

    Args:
        operation: 操作名称（如 "query_available_hosts", "report_hardware"）
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例，如果为 None 则使用模块默认 logger
    """
    log = logger_instance or logger
    log.info(
        f"{operation} 处理完成",
        extra=extra or {},
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
        logger_instance: 自定义 logger 实例，如果为 None 则使用模块默认 logger
    """
    log = logger_instance or logger
    log.info(
        f"开始 {operation}",
        extra=extra or {},
    )


def log_operation_completed(
    operation: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> None:
    """记录操作完成日志

    Args:
        operation: 操作名称
        extra: 额外的日志字段
        logger_instance: 自定义 logger 实例，如果为 None 则使用模块默认 logger
    """
    log = logger_instance or logger
    log.info(
        f"{operation} 完成",
        extra=extra or {},
    )
