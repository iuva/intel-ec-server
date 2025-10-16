"""
共享应用模块

提供FastAPI应用创建和配置功能
"""

from shared.app.application import create_exception_handlers, create_fastapi_app, create_lifespan_handler

__all__ = [
    "create_exception_handlers",
    "create_fastapi_app",
    "create_lifespan_handler",
]
