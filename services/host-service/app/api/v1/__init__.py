"""API v1 路由配置"""

from app.api.v1.endpoints import agent_websocket, agent_websocket_management, browser_hosts, browser_vnc
from fastapi import APIRouter

api_router = APIRouter()

# 注册浏览器插件端点路由
api_router.include_router(browser_hosts.router, prefix="/hosts", tags=["浏览器插件-主机管理"])
api_router.include_router(browser_vnc.router, prefix="", tags=["浏览器插件-VNC连接管理"])

# Agent WebSocket 路由
api_router.include_router(agent_websocket.router, tags=["Agent-WebSocket连接"])
api_router.include_router(agent_websocket_management.router, tags=["Agent-WebSocket管理"])
