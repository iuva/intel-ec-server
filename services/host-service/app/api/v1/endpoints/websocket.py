"""WebSocket 连接端点

提供 Host 的 WebSocket 连接接口
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import verify_websocket_token, handle_websocket_auth_error
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import verify_websocket_token, handle_websocket_auth_error

from app.services.websocket_manager import get_websocket_manager

logger = get_logger(__name__)

router = APIRouter()


async def _handle_websocket_connection(websocket: WebSocket, path_host_id: Optional[str] = None):
    """WebSocket 连接处理核心逻辑

    Args:
        websocket: WebSocket 连接对象
        path_host_id: 从路径获取的 host_id（兼容旧API，实际不使用）

    Note:
        - host_id 从 token 中的 user_id/sub 字段获取
        - 认证失败会直接返回，不建立连接
        - 连接建立后会自动发送欢迎消息
    """
    ws_manager = get_websocket_manager()
    logger.info(
        "WebSocket 连接请求",
        extra={
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            "path": websocket.url.path,
        },
    )

    # ✅ 认证验证
    is_valid, user_info = await verify_websocket_token(websocket)

    if not is_valid or not user_info:
        logger.warning("WebSocket 认证失败")
        await handle_websocket_auth_error(websocket, "缺少有效的认证令牌")
        return

    # ✅ 从 token 中获取 host_id (来自 device_login 时存储的 host_rec.id)
    host_id = user_info.get("user_id")  # user_id 实际上是 host_rec.id

    if not host_id:
        logger.warning("WebSocket token 中缺少 host_id")
        await handle_websocket_auth_error(websocket, "Token 中缺少 host_id")
        return

    # 转换为字符串（确保类型一致）
    host_id = str(host_id)

    logger.info(
        "WebSocket 认证成功",
        extra={
            "host_id": host_id,
            "user_type": user_info.get("user_type"),
            "mg_id": user_info.get("mg_id"),
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
        },
    )

    # ✅ 认证成功，接受连接
    await websocket.accept()

    # ✅ 注册连接
    await ws_manager.connect(host_id, websocket)

    try:
        # ✅ 消息循环 - 接收并处理消息
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(host_id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 正常断开: {host_id}")
        await ws_manager.disconnect(host_id)

    except Exception as e:
        logger.error(
            f"WebSocket 异常: {host_id}, 错误: {e!s}",
            exc_info=True,
        )
        await ws_manager.disconnect(host_id)


@router.websocket("/ws/host")
async def websocket_endpoint_new(websocket: WebSocket):
    """Host WebSocket 连接端点（新版 - 推荐）

    建立WebSocket连接，支持两种认证方式:
    1. 查询参数: ?token=xxx
    2. 请求头: Authorization: Bearer xxx

    Note:
        - host_id 从 JWT token 中的 sub 字段获取（设备登录时存储的 host_rec.id）
        - 不再需要通过路径参数传递 host_id

    Args:
        websocket: WebSocket 连接对象
    """
    await _handle_websocket_connection(websocket)
