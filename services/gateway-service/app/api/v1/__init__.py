"""
Gateway Service API v1 路由配置
"""

from app.api.v1.endpoints import proxy
from fastapi import APIRouter

# 创建 API 路由器
api_router = APIRouter()

# 注册端点路由
api_router.include_router(proxy.router, tags=["代理转发"])
