"""
Token 提取和验证工具类

提供统一的 HTTP/WebSocket token 提取和验证功能。
"""

import os
import sys
from typing import Any, Dict, Optional, Tuple

# 使用 try-except 方式处理路径导入
try:
    from fastapi import Request
    import httpx

    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from fastapi import Request
    import httpx

    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class TokenExtractor:
    """Token 提取和验证工具类

    提供从 HTTP Request 中提取 token 并调用 auth-service 验证的功能。

    Example:
        >>> extractor = TokenExtractor()
        >>> token = extractor.extract_token_from_request(request)
        >>> is_valid, payload = await extractor.verify_token(token)
        >>> if is_valid:
        >>>     user_id = payload.get("user_id")
    """

    def __init__(self, auth_service_url: str = "http://auth-service:8001"):
        """初始化 Token 提取器

        Args:
            auth_service_url: 认证服务 URL
        """
        self.auth_service_url = auth_service_url

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """从 HTTP Request 中提取 token

        支持以下方式：
        1. Authorization 头：Bearer token
        2. 查询参数：?token=xxx
        3. 自定义头：X-Token: xxx

        Args:
            request: FastAPI Request 对象

        Returns:
            token 字符串或 None

        Example:
            >>> extractor = TokenExtractor()
            >>> token = extractor.extract_token_from_request(request)
        """
        # 1. 从 Authorization 头中提取（推荐方式）
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除 "Bearer " 前缀
            logger.debug("从 Authorization 头中提取 token", extra={"method": "bearer_header"})
            return token

        # 2. 从查询参数中提取（兼容性）
        token = request.query_params.get("token")
        if token:
            logger.debug("从查询参数中提取 token", extra={"method": "query_param"})
            return token

        # 3. 从自定义 X-Token 头中提取（兼容性）
        token = request.headers.get("X-Token")
        if token:
            logger.debug("从 X-Token 头中提取 token", extra={"method": "custom_header"})
            return token

        logger.warning(
            "没有找到 token",
            extra={
                "path": request.url.path,
                "query_params": dict(request.query_params),
            },
        )
        return None

    async def verify_token(self, token: str, timeout: float = 10.0) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """验证 token 有效性

        调用 auth-service 的 introspect 接口验证 token。

        Args:
            token: JWT token 字符串
            timeout: 请求超时时间（秒）

        Returns:
            (是否有效, 用户信息字典或None)

        Example:
            >>> extractor = TokenExtractor()
            >>> is_valid, payload = await extractor.verify_token(token)
            >>> if is_valid:
            >>>     print(payload["user_id"])
        """
        if not token:
            logger.warning("Token 为空")
            return False, None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/introspect",
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    logger.debug(
                        "收到 introspect 响应",
                        extra={
                            "active": data.get("active"),
                            "user_id": data.get("user_id") or data.get("sub"),
                        },
                    )

                    # 检查 token 是否有效
                    if data.get("active", False):
                        # 构建用户信息
                        user_info = {
                            "user_id": data.get("user_id") or data.get("sub"),
                            "username": data.get("username"),
                            "user_type": data.get("user_type"),
                            "permissions": data.get("permissions", []),
                            "roles": data.get("roles", []),
                            "mg_id": data.get("mg_id"),  # 管理组ID（如果有）
                        }

                        logger.info(
                            "Token 验证成功",
                            extra={
                                "user_id": user_info["user_id"],
                                "username": user_info["username"],
                                "user_type": user_info["user_type"],
                            },
                        )
                        return True, user_info
                    logger.warning("Token 已失效或无效")
                    return False, None
                logger.warning(
                    f"Token 验证请求失败: {response.status_code}",
                    extra={"status_code": response.status_code},
                )
                return False, None

        except httpx.TimeoutException:
            logger.error("Token 验证超时: auth-service 无响应")
            return False, None

        except Exception as e:
            logger.error(f"Token 验证异常: {e!s}", exc_info=True)
            return False, None

    async def extract_and_verify(self, request: Request) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """一步到位：提取并验证 token

        从 Request 中提取 token 并调用 auth-service 验证。

        Args:
            request: FastAPI Request 对象

        Returns:
            (是否有效, 用户信息字典或None)

        Example:
            >>> extractor = TokenExtractor()
            >>> is_valid, user_info = await extractor.extract_and_verify(request)
            >>> if is_valid:
            >>>     host_id = user_info["user_id"]
        """
        # 提取 token
        token = self.extract_token_from_request(request)

        if not token:
            logger.warning("请求中未找到 token")
            return False, None

        # 验证 token
        return await self.verify_token(token)


# 全局单例实例
_token_extractor_instance: Optional[TokenExtractor] = None


def get_token_extractor() -> TokenExtractor:
    """获取 Token 提取器单例实例

    Returns:
        TokenExtractor: Token 提取器实例

    Example:
        >>> extractor = get_token_extractor()
        >>> token = extractor.extract_token_from_request(request)
    """
    global _token_extractor_instance

    if _token_extractor_instance is None:
        _token_extractor_instance = TokenExtractor()

    return _token_extractor_instance
