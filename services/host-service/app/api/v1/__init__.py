"""API v1 route configuration"""

from fastapi import APIRouter

<<<<<<< HEAD
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

api_router = APIRouter()

# Register browser extension endpoint routes
api_router.include_router(
    browser_hosts.router, prefix="/hosts", tags=["Browser Extension-Host Management"]
)
# ✅ VNC route registered under /hosts/vnc prefix, matches /api/v1/host/hosts/vnc/* path
api_router.include_router(
    browser_vnc.router,
    prefix="/hosts/vnc",
    tags=["Browser Extension-VNC Connection Management"],
)

# Agent HTTP API routes
api_router.include_router(
    agent_report.router, prefix="/agent", tags=["Agent-Hardware Information Reporting"]
)

# Agent WebSocket routes
api_router.include_router(agent_websocket.router, tags=["Agent-WebSocket Connection"])
api_router.include_router(
    agent_websocket_management.router, tags=["Agent-WebSocket Management"]
)

# Admin backend routes
api_router.include_router(
    admin_hosts.router,
    prefix="/admin/host",
    tags=["Admin Backend-Available Host Management"],
)
api_router.include_router(
    admin_appr_host.router,
    prefix="/admin/appr-host",
    tags=["Admin Backend-Pending Approval Host Management"],
)
api_router.include_router(
    admin_ota.router, prefix="/admin/ota", tags=["Admin Backend-OTA Management"]
)
# File management routes
api_router.include_router(file_manage.router, prefix="/file", tags=["File Management"])
=======
from app.api.v1.endpoints import hosts, vnc, websocket

api_router = APIRouter()

# 注册端点路由
api_router.include_router(hosts.router, prefix="/hosts", tags=["主机管理"])
api_router.include_router(vnc.router, prefix="", tags=["VNC连接管理"])
api_router.include_router(websocket.router, tags=["WebSocket通信"])
>>>>>>> af8f7cc (feat(host-service): 重构主机发现与VNC连接管理功能)
