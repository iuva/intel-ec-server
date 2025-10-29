"""
API v1 版本

注册所有 v1 版本的路由
"""

from app.api.v1.endpoints.auth import router as auth_router
from fastapi import APIRouter

# 创建 v1 API 路由器
api_router = APIRouter()

# 注册端点路由 - 使用 /auth 前缀
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])

__all__ = ["api_router"]
