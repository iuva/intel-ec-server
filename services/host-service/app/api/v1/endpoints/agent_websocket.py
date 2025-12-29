"""Agent WebSocket 连接端点

提供 Agent 的 WebSocket 连接接口
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import handle_websocket_auth_error, verify_websocket_token
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import handle_websocket_auth_error, verify_websocket_token

from app.services.agent_websocket_manager import get_agent_websocket_manager

logger = get_logger(__name__)

router = APIRouter()


async def _handle_websocket_connection(websocket: WebSocket, path_host_id: Optional[str] = None):
    """WebSocket 连接处理核心逻辑

    Args:
        websocket: WebSocket 连接对象
        path_host_id: 从路径获取的 host_id（兼容旧API，实际不使用）

    Note:
        - host_id 优先从查询参数获取（网关已验证）
        - 其次从 token 中的 user_id/sub 字段获取（兼容直接连接）
        - 认证失败会直接返回，不建立连接
        - 连接建立后会自动发送欢迎消息
    """
    ws_manager = get_agent_websocket_manager()
    logger.info(
        "WebSocket 连接请求",
        extra={
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            "path": websocket.url.path,
        },
    )

    # ✅ 第一步：尝试从查询参数获取 host_id（网关已验证的情况）
    host_id = websocket.query_params.get("host_id")
    user_info = None  # 初始化 user_info

    if host_id:
        # ✅ 网关已验证 token，直接使用网关传递的 host_id
        logger.info(
            "WebSocket 连接使用网关传递的 host_id",
            extra={
                "host_id": host_id,
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
        )
    else:
        # ✅ 兼容直接连接的情况：从 token 中验证并提取 host_id
        logger.info(
            "WebSocket 连接直接连接，需要从 token 中验证",
            extra={
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
        )

        is_valid, user_info = await verify_websocket_token(websocket)

        if not is_valid or not user_info:
            logger.warning("WebSocket 认证失败")
            await handle_websocket_auth_error(websocket, "缺少有效的认证令牌")
            return

        # ✅ 统一使用 id 字段，没有则返回错误
        host_id = user_info.get("id")

        if not host_id:
            logger.warning("WebSocket token 中缺少 id")
            await handle_websocket_auth_error(websocket, "Token 中缺少 id")
            return

    # 转换为字符串（确保类型一致）
    host_id = str(host_id)

    # ✅ 构建日志信息（兼容两种认证方式）
    log_extra = {
        "host_id": host_id,
        "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
    }

    # 如果有 user_info，添加额外信息
    if user_info:
        log_extra["user_type"] = user_info.get("user_type")
        log_extra["mg_id"] = user_info.get("mg_id")

    logger.info(
        "WebSocket 认证成功",
        extra=log_extra,
    )

    # ✅ 认证成功，接受连接
    await websocket.accept()

    # ✅ 注册连接
    # 记录连接前的状态
    current_connections = ws_manager.get_connection_count()
    current_hosts = ws_manager.get_active_hosts()

    logger.info(
        "准备注册 WebSocket 连接",
        extra={
            "host_id": host_id,
            "current_connection_count": current_connections,
            "current_active_hosts": current_hosts,
            "is_already_connected": ws_manager.is_connected(host_id),
        },
    )

    await ws_manager.connect(host_id, websocket)

    # 记录连接后的状态
    logger.info(
        "WebSocket 连接注册完成",
        extra={
            "host_id": host_id,
            "new_connection_count": ws_manager.get_connection_count(),
            "new_active_hosts": ws_manager.get_active_hosts(),
        },
    )

    try:
        # ✅ 消息循环 - 接收并处理消息
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(host_id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 正常断开: {host_id}")
        # ✅ 检查连接是否仍然存在，避免重复断开
        if host_id in ws_manager.active_connections:
            await ws_manager.disconnect(host_id)
        else:
            logger.debug(f"连接 {host_id} 已断开，跳过重复断开操作")

    except Exception as e:
        logger.error(
            f"WebSocket 异常: {host_id}, 错误: {e!s}",
            exc_info=True,
        )
        # ✅ 检查连接是否仍然存在，避免重复断开
        if host_id in ws_manager.active_connections:
            await ws_manager.disconnect(host_id)
        else:
            logger.debug(f"连接 {host_id} 已断开，跳过重复断开操作")


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
