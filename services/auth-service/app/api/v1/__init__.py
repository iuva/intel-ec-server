"""
API v1 版本

注册所有 v1 版本的路由
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.oauth2 import router as oauth2_router

# 创建 v1 API 路由器
api_router = APIRouter()

# 注册端点路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(oauth2_router, prefix="/oauth2", tags=["OAuth 2.0"])

__all__ = ["api_router"]
