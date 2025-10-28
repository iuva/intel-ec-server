"""WebSocket 认证工具"""

import os
import sys
from typing import Optional, Tuple

# 使用 try-except 方式处理路径导入
try:
    import httpx
    from fastapi import WebSocket, status
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    import httpx
    from fastapi import WebSocket, status
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


async def extract_websocket_token(websocket: WebSocket) -> Optional[str]:
    """从 WebSocket 连接中提取 token

    支持以下方式：
    1. 查询参数：?token=xxx
    2. 请求头：Authorization: Bearer xxx
    3. 自定义头：X-Token: xxx

    Args:
        websocket: WebSocket 连接对象

    Returns:
        token 字符串或 None
    """
    # 1. 从查询参数中提取（最常见）
    token = websocket.query_params.get("token")
    if token:
        logger.debug("从查询参数中提取 token", extra={"method": "query_param"})
        return token

    # 2. 从 Authorization 头中提取
    auth_header = websocket.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        logger.debug("从 Authorization 头中提取 token", extra={"method": "bearer_header"})
        return token

    # 3. 从自定义 X-Token 头中提取
    token = websocket.headers.get("X-Token")
    if token:
        logger.debug("从 X-Token 头中提取 token", extra={"method": "custom_header"})
        return token

    logger.warning(
        "没有找到 token",
        extra={
            "query_params": dict(websocket.query_params),
            "headers_keys": list(websocket.headers.keys()),
        },
    )
    return None


async def verify_websocket_token(
    websocket: WebSocket,
    auth_service_url: str = "http://auth-service:8001",
) -> Tuple[bool, Optional[dict]]:
    """验证 WebSocket token

    Args:
        websocket: WebSocket 连接对象
        auth_service_url: 认证服务 URL

    Returns:
        (是否验证成功, 用户信息字典或None)
    """
    try:
        # 1. 提取 token
        token = await extract_websocket_token(websocket)
        if not token:
            logger.warning(
                "WebSocket 连接缺少 token",
                extra={
                    "client": (
                        f"{websocket.client.host}:{websocket.client.port}"
                        if websocket.client
                        else "unknown"
                    ),
                    "path": websocket.url.path,
                },
            )
            return False, None

        # 2. 调用认证服务验证 token
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{auth_service_url}/api/v1/auth/introspect",
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    # 检查 token 是否有效
                    if data.get("active", False):
                        user_info = {
                            "user_id": data.get("user_id") or data.get("sub"),
                            "username": data.get("username"),
                            "user_type": data.get("user_type"),
                            "permissions": data.get("permissions", []),
                            "roles": data.get("roles", []),
                        }

                        logger.info(
                            "WebSocket token 验证成功",
                            extra={
                                "user_id": user_info["user_id"],
                                "username": user_info["username"],
                                "client": f"{websocket.client.host}:{websocket.client.port}"
                                if websocket.client
                                else "unknown",
                                "path": websocket.url.path,
                            },
                        )
                        return True, user_info

                logger.warning(
                    "WebSocket token 无效或已过期",
                    extra={
                        "status_code": response.status_code,
                        "response": result,
                        "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
                    },
                )
                return False, None

            except httpx.RequestError as e:
                logger.error(
                    "调用认证服务失败",
                    extra={
                        "error": str(e),
                        "auth_service_url": auth_service_url,
                    },
                    exc_info=True,
                )
                return False, None

    except Exception as e:
        logger.error(
            "WebSocket token 验证异常",
            extra={"error": str(e)},
            exc_info=True,
        )
        return False, None


async def handle_websocket_auth_error(websocket: WebSocket, message: str = "认证失败"):
    """处理 WebSocket 认证错误

    Args:
        websocket: WebSocket 连接对象
        message: 错误消息
    """
    try:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=message)
        logger.warning(
            "WebSocket 连接因认证失败被关闭",
            extra={
                "reason": message,
                "client": (
                    f"{websocket.client.host}:{websocket.client.port}"
                    if websocket.client
                    else "unknown"
                ),
            },
        )
    except Exception as e:
        logger.error(
            "关闭 WebSocket 连接时出错",
            extra={"error": str(e)},
            exc_info=True,
        )


async def verify_token_string(
    token: str,
    auth_service_url: str = "http://auth-service:8001",
) -> Optional[str]:
    """验证 token 字符串并返回 user_id

    用于网关层验证 token（直接验证 token 字符串）

    Args:
        token: JWT token 字符串
        auth_service_url: 认证服务 URL

    Returns:
        user_id 或 None (验证失败时)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                logger.debug(
                    "开始验证 Token 字符串",
                    extra={
                        "token_preview": token[:20] + "..." if len(token) > 20 else token,
                        "auth_service_url": auth_service_url,
                    },
                )

                response = await client.post(
                    f"{auth_service_url}/api/v1/auth/introspect",
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

                logger.debug(
                    "Token 验证响应收到",
                    extra={
                        "status_code": response.status_code,
                        "response_keys": list(response.json().keys()) if response.status_code == 200 else None,
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    logger.debug(
                        "Token 验证响应解析",
                        extra={
                            "active": data.get("active", False),
                            "user_id": data.get("user_id"),
                            "username": data.get("username"),
                            "data_keys": list(data.keys()),
                        },
                    )

                    # 检查 token 是否有效
                    if data.get("active", False):
                        user_id = data.get("user_id") or data.get("sub")
                        
                        if user_id:
                            logger.info(
                                "Token 字符串验证成功",
                                extra={
                                    "user_id": user_id,
                                    "username": data.get("username"),
                                },
                            )
                            return str(user_id)
                        else:
                            logger.warning(
                                "Token 有效但未获取到 user_id",
                                extra={
                                    "active": True,
                                    "data_keys": list(data.keys()),
                                },
                            )
                            return None

                logger.warning(
                    "Token 字符串验证失败",
                    extra={
                        "status_code": response.status_code,
                        "active": data.get("active", False) if response.status_code == 200 else None,
                    },
                )
                return None

            except httpx.RequestError as e:
                logger.error(
                    "调用认证服务失败",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "auth_service_url": auth_service_url,
                    },
                    exc_info=True,
                )
                return None

    except Exception as e:
        logger.error(
            "Token 字符串验证异常",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return None
