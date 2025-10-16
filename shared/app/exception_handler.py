"""
统一异常处理集成工具
"""

from fastapi import FastAPI

from shared.common.loguru_config import get_logger
from shared.middleware.exception_middleware import UnifiedExceptionMiddleware

logger = get_logger(__name__)


def setup_exception_handling(app: FastAPI, service_name: str = "unknown") -> None:
    """为FastAPI应用设置统一异常处理

    Args:
        app: FastAPI应用实例
        service_name: 服务名称（用于日志）
    """

    # 添加统一异常处理中间件
    app.add_middleware(UnifiedExceptionMiddleware)

    logger.info(f"已为 {service_name} 启用统一异常处理")
    logger.info(f"当前中间件列表: {[str(m) for m in app.user_middleware]}")
