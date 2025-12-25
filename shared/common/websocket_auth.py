"""WebSocket 认证工具"""

import os
import sys
from typing import TYPE_CHECKING, Optional, Tuple

# 使用 try-except 方式处理路径导入
try:
    import httpx
    from fastapi import WebSocket, status

    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import get_service_discovery
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    import httpx
    from fastapi import WebSocket, status

    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import get_service_discovery

if TYPE_CHECKING:  # pragma: no cover
    from shared.utils.service_discovery import ServiceDiscovery

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
    auth_service_url: Optional[str] = None,
) -> Tuple[bool, Optional[dict]]:
    """验证 WebSocket token

    Note:
        由于网关层已经进行了 token 验证，host-service 的 token 验证已被禁用。
        如果需要在 host-service 层重新启用验证，可以取消下方的 skip_verification 注释。

    Args:
        websocket: WebSocket 连接对象
        auth_service_url: 认证服务 URL (如果为 None，则自动从 ServiceDiscovery 获取)

    Returns:
        (是否验证成功, 用户信息字典或None)
    """
    # ⚠️ 注意：以下验证已被禁用，因为网关已进行认证
    # 如果需要在 host-service 层重新启用验证，可以删除此段代码
    skip_verification = True

    if skip_verification:
        # 即使禁用完整验证，也要从 token 中提取基本信息（特别是 host_id）
        token = await extract_websocket_token(websocket)

        logger.info(
            "WebSocket token 验证已禁用（由网关处理），从token中提取host_id",
            extra={
                "client": (f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"),
                "path": websocket.url.path,
                "token_exists": bool(token),
            },
        )

        # 如果有 token，尝试从中解码获取用户信息（特别是 host_id/user_id）
        user_info = {
            "user_id": "unknown",
            "username": "unknown",
            "user_type": "device",
            "permissions": [],
            "roles": [],
        }

        if token:
            try:
                import jwt

                # 不验证签名，只解码以获取信息
                decoded = jwt.decode(token, options={"verify_signature": False})

                # 从 token 中提取 host_id（可能在 sub 或 user_id 字段）
                user_id = decoded.get("sub") or decoded.get("user_id")
                if user_id:
                    user_info["user_id"] = str(user_id)
                    logger.debug(
                        "从token中提取到host_id",
                        extra={"host_id": user_id},
                    )

                # 提取其他可用信息
                if decoded.get("username"):
                    user_info["username"] = decoded.get("username")
                if decoded.get("user_type"):
                    user_info["user_type"] = decoded.get("user_type")
                if decoded.get("mg_id"):
                    user_info["mg_id"] = decoded.get("mg_id")

            except Exception as e:
                logger.debug(
                    "无法从token中解码信息",
                    extra={"error": str(e)},
                )

        # 直接返回成功，允许连接建立
        return True, user_info

    # ============================================================================
    # 以下是原始的 token 验证逻辑（已禁用）
    # 如需重新启用，请将上方的 skip_verification = True 改为 False
    # ============================================================================

    try:
        # 1. 提取 token
        token = await extract_websocket_token(websocket)
        if not token:
            logger.warning(
                "WebSocket 连接缺少 token",
                extra={
                    "client": (f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"),
                    "path": websocket.url.path,
                },
            )
            return False, None

        # 2. 构建候选认证服务地址列表（采用与 verify_token_string 相同的多策略方式）
        candidate_urls = []

        if auth_service_url:
            candidate_urls.append(auth_service_url)

        env_url = os.getenv("AUTH_SERVICE_BASE_URL")
        if env_url:
            candidate_urls.append(env_url)

        service_discovery_instance: Optional["ServiceDiscovery"] = None
        try:
            service_discovery_instance = get_service_discovery()
            discovered_url = await service_discovery_instance.get_service_url("auth-service")
            candidate_urls.append(discovered_url)
        except Exception as discovery_error:
            logger.debug(
                "WebSocket 服务发现获取 auth-service 地址失败",
                extra={"error": str(discovery_error)},
            )

        # 使用与 HTTP 服务一致的后备地址策略
        if service_discovery_instance:
            try:
                fallback_url = service_discovery_instance._get_fallback_url("auth-service")
                candidate_urls.append(fallback_url)
            except Exception as fallback_error:
                logger.debug(
                    "WebSocket 计算认证服务后备地址失败",
                    extra={"error": str(fallback_error)},
                )

        # 去重并规范化地址
        normalized_urls = []
        seen = set()
        for url in candidate_urls:
            if not url:
                continue
            normalized = url.rstrip("/")
            if normalized not in seen:
                seen.add(normalized)
                normalized_urls.append(normalized)

        if not normalized_urls:
            logger.error(
                "WebSocket 无法确定认证服务地址",
                extra={
                    "candidate_urls": candidate_urls,
                },
            )
            return False, None

        last_error: Optional[Exception] = None

        # 3. 尝试使用各个候选地址验证 token
        for base_url in normalized_urls:
            try:
                logger.debug(
                    "WebSocket 开始验证 token",
                    extra={
                        "token_preview": token[:20] + "..." if len(token) > 20 else token,
                        "auth_service_url": base_url,
                    },
                )

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{base_url}/api/v1/auth/introspect",
                        json={"token": token},
                        headers={"Content-Type": "application/json"},
                    )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    logger.debug(
                        "WebSocket 收到 introspect 响应",
                        extra={
                            "response_data": data,
                            "active": data.get("active"),
                        },
                    )

                    # 检查 token 是否有效
                    if data.get("active", False):
                        user_id = data.get("user_id") or data.get("sub")
                        # ✅ 验证 user_id 是否有效（不为 None、空字符串）
                        if not user_id or not str(user_id).strip():
                            logger.warning(
                                "WebSocket token 有效但 user_id 无效",
                                extra={
                                    "user_id": user_id,
                                    "user_id_type": type(user_id).__name__ if user_id is not None else "None",
                                    "auth_service_url": base_url,
                                    "data_keys": list(data.keys()),
                                },
                            )
                            # 继续尝试其他地址
                            continue

                        user_info = {
                            "user_id": user_id,
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
                                "user_type": user_info["user_type"],
                                "client": f"{websocket.client.host}:{websocket.client.port}"
                                if websocket.client
                                else "unknown",
                                "path": websocket.url.path,
                            },
                        )
                        return True, user_info
                    else:
                        logger.warning(
                            "WebSocket token active=False",
                            extra={
                                "data": data,
                                "auth_service_url": base_url,
                            },
                        )
                        # 继续尝试其他地址
                        continue
                else:
                    logger.warning(
                        "WebSocket token 验证响应错误",
                        extra={
                            "status_code": response.status_code,
                            "auth_service_url": base_url,
                        },
                    )
                    # 继续尝试其他地址
                    continue

            except httpx.RequestError as e:
                logger.debug(
                    "WebSocket 调用认证服务失败",
                    extra={
                        "error": str(e),
                        "auth_service_url": base_url,
                    },
                )
                last_error = e
                # 继续尝试其他地址
                continue

        # 所有地址都失败了
        logger.error(
            "WebSocket 无法验证 token - 所有认证服务地址都失败",
            extra={
                "last_error": str(last_error) if last_error else "unknown",
                "tried_urls": normalized_urls,
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
            exc_info=last_error,
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
                "client": (f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"),
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
    auth_service_url: Optional[str] = None,
) -> Optional[str]:
    """验证 token 字符串并返回 user_id

    用于网关层验证 token（直接验证 token 字符串）

    Args:
        token: JWT token 字符串
        auth_service_url: 认证服务 URL

    Returns:
        user_id 或 None (验证失败时)
    """
    # 构建候选认证服务地址列表（按优先级排序）
    candidate_urls = []

    if auth_service_url:
        candidate_urls.append(auth_service_url)

    env_url = os.getenv("AUTH_SERVICE_BASE_URL")
    if env_url:
        candidate_urls.append(env_url)

    service_discovery: Optional["ServiceDiscovery"] = None
    try:
        service_discovery = get_service_discovery()
        discovered_url = await service_discovery.get_service_url("auth-service")
        candidate_urls.append(discovered_url)
    except Exception as discovery_error:
        logger.debug(
            "服务发现获取 auth-service 地址失败，使用默认地址",
            extra={"error": str(discovery_error)},
        )

    # 使用与 HTTP 服务一致的后备地址策略
    if service_discovery:
        try:
            fallback_url = service_discovery._get_fallback_url("auth-service")
            candidate_urls.append(fallback_url)
        except Exception as fallback_error:
            logger.debug(
                "计算认证服务后备地址失败",
                extra={"error": str(fallback_error)},
            )

    # 去重并规范化地址
    normalized_urls = []
    seen = set()
    for url in candidate_urls:
        if not url:
            continue
        normalized = url.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            normalized_urls.append(normalized)

    last_error: Optional[Exception] = None

    for base_url in normalized_urls:
        try:
            logger.debug(
                "开始验证 Token 字符串",
                extra={
                    "token_preview": token[:20] + "..." if len(token) > 20 else token,
                    "auth_service_url": base_url,
                },
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{base_url}/api/v1/auth/introspect",
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

            logger.debug(
                "Token 验证响应收到",
                extra={
                    "status_code": response.status_code,
                    "auth_service_url": base_url,
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

                if data.get("active", False):
                    user_id = data.get("user_id") or data.get("sub")
                    # ✅ 验证 user_id 是否有效（不为 None、空字符串）
                    # ⚠️ 注意：如果 host_id 可能为 0，需要特殊处理（当前允许 0）
                    if user_id and str(user_id).strip():
                        logger.info(
                            "Token 字符串验证成功",
                            extra={
                                "user_id": user_id,
                                "username": data.get("username"),
                                "auth_service_url": base_url,
                            },
                        )
                        return str(user_id)

                    logger.warning(
                        "Token 有效但未获取到有效的 user_id",
                        extra={
                            "auth_service_url": base_url,
                            "user_id": user_id,
                            "user_id_type": type(user_id).__name__ if user_id is not None else "None",
                            "data_keys": list(data.keys()),
                        },
                    )
                    return None

                logger.warning(
                    "Token 已验证但处于非激活状态",
                    extra={
                        "auth_service_url": base_url,
                        "active": data.get("active", False),
                    },
                )
                continue

            logger.warning(
                "Token 字符串验证失败",
                extra={
                    "auth_service_url": base_url,
                    "status_code": response.status_code,
                },
            )

        except httpx.RequestError as request_error:
            logger.warning(
                "调用认证服务失败，尝试下一个候选地址",
                extra={
                    "auth_service_url": base_url,
                    "error": str(request_error),
                    "error_type": type(request_error).__name__,
                },
            )
            last_error = request_error
            continue

        except Exception as exc:
            logger.error(
                "Token 字符串验证异常",
                extra={
                    "auth_service_url": base_url,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            last_error = exc
            continue

    if last_error:
        logger.error(
            "所有认证服务地址均无法验证 Token",
            extra={"error": str(last_error), "error_type": type(last_error).__name__},
        )
    else:
        logger.warning("未找到有效的认证服务地址，Token 验证失败")

    return None
