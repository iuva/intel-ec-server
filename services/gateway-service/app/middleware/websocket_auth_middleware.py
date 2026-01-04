"""
WebSocket 认证中间件

提供 WebSocket 连接的令牌认证和授权功能
"""

import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from fastapi import WebSocket, WebSocketException

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import AuthorizationError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import AuthorizationError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager

logger = get_logger(__name__)


class WebSocketAuthMiddleware:
    """WebSocket 认证中间件

    提供以下功能：
    - JWT 令牌验证
    - 权限检查
    - 会话管理
    - 认证失败处理
    """

    def __init__(self, jwt_manager: Optional[JWTManager] = None):
        """初始化认证中间件

        Args:
            jwt_manager: JWT 管理器实例，如果为 None 则禁用认证
        """
        self.jwt_manager = jwt_manager
        self.logger = logger

    async def authenticate(self, websocket: WebSocket, require_auth: bool = False) -> Optional[Dict[str, Any]]:
        """认证 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            require_auth: 是否要求认证（True 则必须提供有效令牌）

        Returns:
            认证成功返回用户信息字典，认证失败或可选时返回 None

        Raises:
            WebSocketException: 认证失败时抛出异常
        """
        try:
            # 提取令牌
            token = self._extract_token(websocket)

            if not token:
                if require_auth:
                    self.logger.warning(
                        "WebSocket 连接缺少认证令牌",
                        extra={
                            "client": websocket.client.host if websocket.client else "unknown",
                            "path": websocket.url.path,
                        },
                    )
                    raise WebSocketException(code=1008, reason="缺少认证令牌")

                # 认证可选时返回 None
                self.logger.debug(
                    "WebSocket 连接未提供令牌，允许继续（认证可选）",
                    extra={"client": websocket.client.host if websocket.client else "unknown"},
                )
                return None

            # 验证令牌
            if not self.jwt_manager:
                self.logger.warning("JWT 管理器未配置，无法验证令牌")
                return None

            user_info = await self._verify_token(token)
            if not user_info:
                self.logger.warning(
                    "WebSocket 连接提供了无效令牌",
                    extra={"client": websocket.client.host if websocket.client else "unknown"},
                )
                raise WebSocketException(code=1008, reason="无效令牌")

            # 记录认证成功
            self.logger.info(
                "WebSocket 连接已认证",
                extra={
                    "client": websocket.client.host if websocket.client else "unknown",
                    "id": user_info.get("id"),
                    "username": user_info.get("username"),
                },
            )

            return user_info

        except WebSocketException:
            raise
        except Exception as e:
            self.logger.error(
                f"WebSocket 认证异常: {e!s}",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            raise WebSocketException(code=1011, reason="认证服务错误")

    def _extract_token(self, websocket: WebSocket) -> Optional[str]:
        """从 WebSocket 连接中提取令牌

        支持多种令牌提供方式：
        1. Authorization 查询参数: ?token=<token>
        2. Authorization 请求头: Authorization: Bearer <token>

        Args:
            websocket: WebSocket 连接对象

        Returns:
            令牌字符串，未找到返回 None
        """
        # 方式 1: 查询参数
        query_params = parse_qs(urlparse(str(websocket.url)).query)
        if "token" in query_params:
            token = query_params["token"][0]
            self.logger.debug("从查询参数中提取令牌")
            return token

        # 方式 2: Authorization 请求头
        auth_header = websocket.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除 "Bearer " 前缀
            self.logger.debug("从 Authorization 头中提取令牌")
            return token

        return None

    async def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT 令牌

        Args:
            token: JWT 令牌字符串

        Returns:
            令牌有效返回用户信息字典，无效返回 None
        """
        if not self.jwt_manager:
            return None

        try:
            user_info = self.jwt_manager.verify_token(token)
            if user_info:
                # ✅ 统一使用 id 字段（如果没有则从 sub 提取，兼容旧 token）
                user_id = user_info.get("id") or user_info.get("sub")
                # 如果原始 user_info 没有 id 字段，添加它（兼容旧 token）
                if "id" not in user_info and user_id:
                    user_info["id"] = user_id
                if not user_id:
                    self.logger.warning("Token 验证成功但 id 为空", extra={"payload_keys": list(user_info.keys())})
                    return None
                self.logger.debug("令牌验证成功", extra={"id": user_id})
            return user_info

        except Exception as e:
            self.logger.debug("令牌验证失败", extra={"error": str(e)})
            return None

    async def check_permissions(
        self,
        user_info: Optional[Dict[str, Any]],
        required_permissions: Optional[list] = None,
    ) -> bool:
        """检查用户权限

        Args:
            user_info: 用户信息字典
            required_permissions: 必需的权限列表

        Returns:
            权限检查通过返回 True，否则返回 False

        Raises:
            AuthorizationError: 权限不足时抛出异常
        """
        if not required_permissions:
            # 无权限要求，允许访问
            return True

        if not user_info:
            raise AuthorizationError("未认证用户无权访问")

        user_permissions = set(user_info.get("permissions", []))
        required_perms = set(required_permissions)

        if not required_perms.issubset(user_permissions):
            missing_perms = required_perms - user_permissions
            self.logger.warning(
                "用户权限不足",
                extra={
                    "id": user_info.get("id"),
                    "required": list(required_perms),
                    "missing": list(missing_perms),
                },
            )
            raise AuthorizationError(f"缺少权限: {', '.join(missing_perms)}")

        return True
