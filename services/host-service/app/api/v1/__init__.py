"""API v1 路由配置"""

from fastapi import APIRouter

from app.api.v1.endpoints import hosts, vnc, websocket

api_router = APIRouter()

# 注册端点路由
api_router.include_router(hosts.router, prefix="/hosts", tags=["主机管理"])
api_router.include_router(vnc.router, prefix="", tags=["VNC连接管理"])
api_router.include_router(websocket.router, tags=["WebSocket通信"])
