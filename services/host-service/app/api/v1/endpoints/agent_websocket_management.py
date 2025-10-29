"""Agent WebSocket 管理 HTTP API 端点

提供 Agent WebSocket 连接管理和消息发送的 HTTP 接口
"""

import os
import sys
from typing import Dict, List

from fastapi import APIRouter, Query

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

from app.services.agent_websocket_manager import get_agent_websocket_manager

logger = get_logger(__name__)

router = APIRouter()


# ========== 连接管理端点 ==========


@router.get("/ws/hosts")
async def get_active_hosts():
    """获取所有活跃连接的 Host ID

    Returns:
        活跃 Host 列表和总数

    Example:
        ```
        GET /api/v1/ws/hosts
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "获取活跃Host成功",
            "data": {
                "hosts": ["1846486359367955051", "1846486359367955052"],
                "count": 2
            }
        }
        ```
    """
    ws_manager = get_agent_websocket_manager()
    hosts = ws_manager.get_active_hosts()

    logger.info(f"查询活跃Host列表: 共 {len(hosts)} 个")

    return SuccessResponse(
        data={"hosts": hosts, "count": len(hosts)},
        message="获取活跃Host成功",
    )


@router.get("/ws/status/{host_id}")
async def get_host_status(host_id: str):
    """检查 Host 连接状态

    Args:
        host_id: Host ID

    Returns:
        连接状态信息

    Example:
        ```
        GET /api/v1/ws/status/1846486359367955051
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "获取Host状态成功",
            "data": {
                "host_id": "1846486359367955051",
                "connected": true
            }
        }
        ```
    """
    ws_manager = get_agent_websocket_manager()
    is_connected = ws_manager.is_connected(host_id)

    logger.debug(f"查询Host连接状态: {host_id} -> {'已连接' if is_connected else '未连接'}")

    return SuccessResponse(
        data={"host_id": host_id, "connected": is_connected},
        message="获取Host状态成功",
    )


# ========== 消息发送端点 ==========


@router.post("/ws/send/{host_id}")
async def send_message_to_host(host_id: str, message: Dict):
    """发送消息给指定 Host

    Args:
        host_id: 目标 Host ID
        message: 消息内容（必须包含 type 字段）

    Returns:
        发送结果

    Raises:
        BusinessError: 消息格式错误（缺少 type 字段）

    Example:
        ```
        POST /api/v1/ws/send/1846486359367955051
        {
            "type": "command",
            "command_id": "cmd_123",
            "command": "restart",
            "args": {"service": "nginx"}
        }
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "消息发送成功",
            "data": {
                "host_id": "1846486359367955051",
                "success": true
            }
        }
        ```
    """
    # 验证消息格式
    if not message.get("type"):
        raise BusinessError(
            message="消息必须包含 type 字段",
            error_code="INVALID_MESSAGE_FORMAT",
            code=400,
        )

    ws_manager = get_agent_websocket_manager()
    success = await ws_manager.send_to_host(host_id, message)

    if success:
        logger.info(f"✅ 消息已发送到Host: {host_id}, 类型: {message.get('type')}")
    else:
        logger.warning(f"⚠️ 消息发送失败: {host_id} (Host未连接)")

    return SuccessResponse(
        data={"host_id": host_id, "success": success},
        message="消息发送成功" if success else "消息发送失败（Host未连接）",
    )


@router.post("/ws/send-to-hosts")
async def send_message_to_hosts(host_ids: List[str], message: Dict):
    """发送消息给指定的多个 Hosts（多播）

    Args:
        host_ids: 目标 Host ID 列表
        message: 消息内容（必须包含 type 字段）

    Returns:
        发送结果统计

    Raises:
        BusinessError: 消息格式错误（缺少 type 字段）

    Example:
        ```
        POST /api/v1/ws/send-to-hosts
        {
            "host_ids": ["1846486359367955051", "1846486359367955052"],
            "message": {
                "type": "notification",
                "message": "系统维护通知",
                "data": {"maintenance_time": "2025-10-28 22:00:00"}
            }
        }
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "消息发送完成 (2/2成功)",
            "data": {
                "target_count": 2,
                "success_count": 2,
                "failed_count": 0
            }
        }
        ```
    """
    # 验证消息格式
    if not message.get("type"):
        raise BusinessError(
            message="消息必须包含 type 字段",
            error_code="INVALID_MESSAGE_FORMAT",
            code=400,
        )

    ws_manager = get_agent_websocket_manager()
    success_count = await ws_manager.send_to_hosts(host_ids, message)

    logger.info(f"多播消息完成: 目标 {len(host_ids)} 个Host, 成功 {success_count} 个, 类型: {message.get('type')}")

    return SuccessResponse(
        data={
            "target_count": len(host_ids),
            "success_count": success_count,
            "failed_count": len(host_ids) - success_count,
        },
        message=f"消息发送完成 ({success_count}/{len(host_ids)}成功)",
    )


@router.post("/ws/broadcast")
async def broadcast_message(message: Dict, exclude_host_id: str = Query(None, description="排除的Host ID")):
    """广播消息给所有连接的 Hosts

    Args:
        message: 消息内容（必须包含 type 字段）
        exclude_host_id: 排除的 Host ID（可选）

    Returns:
        广播结果统计

    Raises:
        BusinessError: 消息格式错误（缺少 type 字段）

    Example:
        ```
        POST /api/v1/ws/broadcast?exclude_host_id=1846486359367955051
        {
            "type": "notification",
            "message": "系统更新通知",
            "data": {"version": "2.0.0"}
        }
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "广播完成 (99/100成功)",
            "data": {
                "total_count": 100,
                "success_count": 99,
                "failed_count": 1
            }
        }
        ```
    """
    # 验证消息格式
    if not message.get("type"):
        raise BusinessError(
            message="消息必须包含 type 字段",
            error_code="INVALID_MESSAGE_FORMAT",
            code=400,
        )

    ws_manager = get_agent_websocket_manager()
    success_count = await ws_manager.broadcast(message, exclude=exclude_host_id)
    total_count = ws_manager.get_connection_count()

    logger.info(
        f"广播消息完成: 目标 {total_count} 个Host, 成功 {success_count} 个, 排除: {exclude_host_id or '无'}, 类型: {message.get('type')}"
    )

    return SuccessResponse(
        data={
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": total_count - success_count,
            "exclude_host_id": exclude_host_id,
        },
        message=f"广播完成 ({success_count}/{total_count}成功)",
    )
