"""WebSocket 端点"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import WebSocketManager

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 全局 WebSocket 管理器实例
ws_manager = WebSocketManager()


@router.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """Agent WebSocket 连接端点

    Args:
        websocket: WebSocket 连接对象
        agent_id: Agent 唯一标识
    """
    await ws_manager.connect(agent_id, websocket)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            # 处理消息
            await ws_manager.handle_message(agent_id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 正常断开: {agent_id}")
        await ws_manager.disconnect(agent_id)

    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(f"WebSocket 异常: {agent_id}, 错误: {e!s}")
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
