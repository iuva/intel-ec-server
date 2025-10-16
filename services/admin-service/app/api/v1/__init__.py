"""
Admin Service API v1 路由配置
"""

# 导入端点路由
from fastapi import APIRouter

from app.api.v1.endpoints import users

# 创建API路由器
api_router = APIRouter()

# 注册用户管理路由
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
