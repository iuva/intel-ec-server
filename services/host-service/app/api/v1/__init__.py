"""API v1 路由配置"""

from app.api.v1.endpoints import (
    admin_appr_host,
    admin_hosts,
    admin_ota,
    agent_report,
    agent_websocket,
    agent_websocket_management,
    browser_hosts,
    browser_vnc,
    file_manage,
)
from fastapi import APIRouter

api_router = APIRouter()

# 注册浏览器插件端点路由
api_router.include_router(browser_hosts.router, prefix="/hosts", tags=["浏览器插件-主机管理"])
api_router.include_router(browser_vnc.router, prefix="/vnc", tags=["浏览器插件-VNC连接管理"])

# Agent HTTP API 路由
api_router.include_router(agent_report.router, prefix="/agent", tags=["Agent-硬件信息上报"])

# Agent WebSocket 路由
api_router.include_router(agent_websocket.router, tags=["Agent-WebSocket连接"])
api_router.include_router(agent_websocket_management.router, tags=["Agent-WebSocket管理"])

# 管理后台路由
api_router.include_router(admin_hosts.router, prefix="/admin/host", tags=["管理后台-可用主机管理"])
api_router.include_router(admin_appr_host.router, prefix="/admin/appr-host", tags=["管理后台-待审批主机管理"])
api_router.include_router(admin_ota.router, prefix="/admin/ota", tags=["管理后台-OTA管理"])
# 文件管理路由
api_router.include_router(file_manage.router, prefix="/file", tags=["文件管理"])
