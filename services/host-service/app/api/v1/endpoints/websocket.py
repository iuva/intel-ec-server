"""WebSocket API 端点

提供Host连接和消息转发的WebSocket接口
"""

import os
import sys

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
    from shared.common.websocket_auth import verify_websocket_token, handle_websocket_auth_error
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
    from shared.common.websocket_auth import verify_websocket_token, handle_websocket_auth_error

from app.services.websocket_manager import WebSocketManager

logger = get_logger(__name__)

router = APIRouter()

# 全局 WebSocket 管理器实例
ws_manager = WebSocketManager()


@router.websocket("/ws/host/{host_id}")
async def websocket_endpoint(websocket: WebSocket, host_id: str):
    """Host WebSocket 连接端点

    建立WebSocket连接，支持两种认证方式:
    1. 查询参数: ?token=xxx
    2. 请求头: Authorization: Bearer xxx

    Args:
        websocket: WebSocket 连接对象
        host_id: Host ID (唯一标识)
    """
    logger.info(
        "WebSocket 连接请求",
        extra={
            "host_id": host_id,
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
        },
    )

    # ✅ 认证验证
    is_valid, user_info = await verify_websocket_token(websocket)

    if not is_valid:
        logger.warning(f"WebSocket 认证失败: {host_id}")
        await handle_websocket_auth_error(websocket, "缺少有效的认证令牌")
        return

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


# ========== HTTP API 端点 ==========


@router.get("/ws/hosts")
async def get_active_hosts():
    """获取所有活跃连接的Host ID

    Returns:
        活跃Host列表
    """
    hosts = ws_manager.get_active_hosts()
    return SuccessResponse(
        data={"hosts": hosts, "count": len(hosts)},
        message="获取活跃Host成功",
    )


@router.get("/ws/status/{host_id}")
async def get_host_status(host_id: str):
    """检查Host连接状态

    Args:
        host_id: Host ID

    Returns:
        连接状态
    """
    is_connected = ws_manager.is_connected(host_id)
    return SuccessResponse(
        data={"host_id": host_id, "connected": is_connected},
        message="获取Host状态成功",
    )


@router.post("/ws/send/{host_id}")
async def send_message_to_host(host_id: str, message: dict):
    """发送消息给指定Host

    Args:
        host_id: Host ID
        message: 消息内容 (必须包含 type 字段)

    Returns:
        发送结果
    """
    if not message.get("type"):
        from shared.common.exceptions import BusinessError

        raise BusinessError(
            message="消息必须包含 type 字段",
            error_code="INVALID_MESSAGE_FORMAT",
            code=400,
        )

    success = await ws_manager.send_to_host(host_id, message)

    return SuccessResponse(
        data={"host_id": host_id, "success": success},
        message="消息发送成功" if success else "消息发送失败（Host未连接）",
    )


@router.post("/ws/send-to-hosts")
async def send_message_to_hosts(host_ids: list[str], message: dict):
    """发送消息给指定的多个Hosts

    Args:
        host_ids: Host ID 列表
        message: 消息内容

    Returns:
        发送结果统计
    """
    if not message.get("type"):
        from shared.common.exceptions import BusinessError

        raise BusinessError(
            message="消息必须包含 type 字段",
            error_code="INVALID_MESSAGE_FORMAT",
            code=400,
        )

    success_count = await ws_manager.send_to_hosts(host_ids, message)

    return SuccessResponse(
        data={
            "target_count": len(host_ids),
            "success_count": success_count,
            "failed_count": len(host_ids) - success_count,
        },
        message=f"消息发送完成 ({success_count}/{len(host_ids)}成功)",
    )


@router.post("/ws/broadcast")
async def broadcast_message(message: dict, exclude_host_id: str = Query(None, description="排除的Host ID")):
    """广播消息给所有连接的Host

    Args:
        message: 消息内容
        exclude_host_id: 排除的Host ID (可选)

    Returns:
        广播结果统计
    """
    if not message.get("type"):
        from shared.common.exceptions import BusinessError

        raise BusinessError(
            message="消息必须包含 type 字段",
            error_code="INVALID_MESSAGE_FORMAT",
            code=400,
        )

    success_count = await ws_manager.broadcast(message, exclude=exclude_host_id)
    total_count = ws_manager.get_connection_count()

    return SuccessResponse(
        data={
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": total_count - success_count,
        },
        message=f"广播完成 ({success_count}/{total_count}成功)",
    )
