"""
API v1 版本

注册所有 v1 版本的路由
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router

# 创建 v1 API 路由器
api_router = APIRouter()

# 注册端点路由（去掉/auth前缀，与其他服务保持一致）
api_router.include_router(auth_router, prefix="", tags=["认证"])

__all__ = ["api_router"]
