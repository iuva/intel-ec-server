"""
API 端点模块

导出所有端点路由
"""

from app.api.v1.endpoints.auth import router as auth_router

__all__ = ["auth_router"]
