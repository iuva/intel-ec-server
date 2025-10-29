"""API v1 路由配置"""

from app.api.v1.endpoints import hosts, vnc, websocket, websocket_management
from fastapi import APIRouter

api_router = APIRouter()

# 注册端点路由
api_router.include_router(hosts.router, prefix="/hosts", tags=["主机管理"])
api_router.include_router(vnc.router, prefix="", tags=["VNC连接管理"])

# WebSocket 路由
api_router.include_router(websocket.router, tags=["WebSocket连接"])
api_router.include_router(websocket_management.router, tags=["WebSocket管理"])
