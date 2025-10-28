"""WebSocket 端点"""

import os
import sys
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import verify_websocket_token, handle_websocket_auth_error
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import verify_websocket_token, handle_websocket_auth_error

from app.services.websocket_manager import WebSocketManager

logger = get_logger(__name__)

router = APIRouter()

# 全局 WebSocket 管理器实例
ws_manager = WebSocketManager()


@router.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """Agent WebSocket 连接端点

    需要 token 认证。支持以下方式提供 token:
    1. 查询参数: ?token=xxx
    2. 请求头: Authorization: Bearer xxx
    3. 自定义头: X-Token: xxx

    Args:
        websocket: WebSocket 连接对象
        agent_id: Agent 唯一标识
    """
    logger.info(
        "WebSocket 连接请求",
        extra={
            "agent_id": agent_id,
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            "path": websocket.url.path,
        },
    )

    # ✅ 第一步：验证 token
    is_valid, user_info = await verify_websocket_token(websocket)

    if not is_valid:
        logger.warning(
            "WebSocket 连接认证失败",
            extra={
                "agent_id": agent_id,
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
        )
        await handle_websocket_auth_error(websocket, "缺少有效的认证令牌")
        return

    # ✅ 第二步：认证成功，接受连接
    logger.info(
        "WebSocket 连接认证成功，接受连接",
        extra={
            "agent_id": agent_id,
            "user_id": user_info.get("user_id"),
            "username": user_info.get("username"),
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
        },
    )

    await websocket.accept()

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            # 处理消息
            await ws_manager.handle_message(agent_id, data)

    except WebSocketDisconnect:
        logger.info(
            "WebSocket 正常断开",
            extra={
                "agent_id": agent_id,
                "user_id": user_info.get("user_id"),
            },
        )
        await ws_manager.disconnect(agent_id)

    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(
            "WebSocket 异常",
            extra={
                "agent_id": agent_id,
                "user_id": user_info.get("user_id"),
                "error": str(e),
            },
            exc_info=True,
        )
        await ws_manager.disconnect(agent_id)


@router.get("/ws/connections")
async def get_active_connections():
    """获取活跃的 WebSocket 连接信息

    Returns:
        活跃连接列表
    """
    from shared.common.response import SuccessResponse

    connections = ws_manager.get_active_connections()
    count = ws_manager.get_connection_count()

    return SuccessResponse(
        data={"connections": connections, "count": count},
        message="获取活跃连接成功",
    )


@router.post("/ws/broadcast")
async def broadcast_message(message: dict):
    """广播消息给所有连接的 Agent

    Args:
        message: 要广播的消息

    Returns:
        广播结果
    """
    from shared.common.response import SuccessResponse

    success_count = await ws_manager.broadcast(message)

    return SuccessResponse(
        data={
            "success_count": success_count,
            "total": ws_manager.get_connection_count(),
        },
        message="消息广播成功",
    )
