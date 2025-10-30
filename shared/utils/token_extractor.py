"""
<<<<<<< HEAD
Token Extraction and Verification Utility Class

Provides unified HTTP/WebSocket token extraction and verification functionality.
=======
Token 提取和验证工具类

提供统一的 HTTP/WebSocket token 提取和验证功能。
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
"""

import os
import sys
<<<<<<< HEAD
from typing import Any, Dict, Optional, Tuple

# Use try-except to handle path imports
try:
    from fastapi import Request
    import httpx

    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from fastapi import Request
    import httpx

=======
from typing import Optional, Dict, Any

# 使用 try-except 方式处理路径导入
try:
    import httpx
    from fastapi import Request
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    import httpx
    from fastapi import Request
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class TokenExtractor:
<<<<<<< HEAD
    """Token Extraction and Verification Utility Class

    Provides functionality to extract tokens from HTTP Requests and verify them with auth-service.
=======
    """Token 提取和验证工具类

    提供从 HTTP Request 中提取 token 并调用 auth-service 验证的功能。
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

    Example:
        >>> extractor = TokenExtractor()
        >>> token = extractor.extract_token_from_request(request)
        >>> is_valid, payload = await extractor.verify_token(token)
        >>> if is_valid:
        >>>     user_id = payload.get("user_id")
    """

<<<<<<< HEAD
    def __init__(self, auth_service_url: str = "http://auth-service:8001", service_discovery=None):
        """Initialize Token Extractor

        Args:
            auth_service_url: Authentication service URL (static configuration,
                              used when service_discovery is not provided)
            service_discovery: ServiceDiscovery instance (optional),
                               used to dynamically get service addresses
        """
        self.auth_service_url = auth_service_url
        self.service_discovery = service_discovery

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract token from HTTP Request

        Supports the following methods:
        1. Authorization header: Bearer token
        2. Query parameter: ?token=xxx
        3. Custom header: X-Token: xxx

        Args:
            request: FastAPI Request object

        Returns:
            token string or None
=======
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
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

        Example:
            >>> extractor = TokenExtractor()
            >>> token = extractor.extract_token_from_request(request)
        """
<<<<<<< HEAD
        # 1. Extract from Authorization header (recommended method)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug("Extracted token from Authorization header", extra={"method": "bearer_header"})
            return token

        # 2. Extract from query parameters (compatibility)
        token = request.query_params.get("token")
        if token:
            logger.debug("Extracted token from query parameters", extra={"method": "query_param"})
            return token

        # 3. Extract from custom X-Token header (compatibility)
        token = request.headers.get("X-Token")
        if token:
            logger.debug("Extracted token from X-Token header", extra={"method": "custom_header"})
            return token

        logger.warning(
            "No token found",
=======
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
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
            extra={
                "path": request.url.path,
                "query_params": dict(request.query_params),
            },
        )
        return None

<<<<<<< HEAD
    async def verify_token(self, token: str, timeout: float = 10.0) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify token validity

        Calls auth-service's introspect endpoint to verify the token.

        Args:
            token: JWT token string
            timeout: Request timeout (seconds)

        Returns:
            (is_valid, user information dictionary or None)
=======
    async def verify_token(self, token: str, timeout: float = 10.0) -> tuple[bool, Optional[Dict[str, Any]]]:
        """验证 token 有效性

        调用 auth-service 的 introspect 接口验证 token。

        Args:
            token: JWT token 字符串
            timeout: 请求超时时间（秒）

        Returns:
            (是否有效, 用户信息字典或None)
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

        Example:
            >>> extractor = TokenExtractor()
            >>> is_valid, payload = await extractor.verify_token(token)
            >>> if is_valid:
            >>>     print(payload["user_id"])
        """
        if not token:
<<<<<<< HEAD
            logger.warning("Token is empty")
            return False, None

        try:
            # Get auth-service address (dynamic or static)
            if self.service_discovery:
                auth_service_url = await self.service_discovery.get_service_url("auth-service")
            else:
                auth_service_url = self.auth_service_url

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{auth_service_url}/api/v1/auth/introspect",
=======
            logger.warning("Token 为空")
            return False, None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/introspect",
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    logger.debug(
<<<<<<< HEAD
                        "Received introspect response",
                        extra={
                            "active": data.get("active"),
                            "id": data.get("id"),
                        },
                    )

                    # Check if token is valid
                    if data.get("active", False):
                        # ✅ Use id field uniformly, return False if not present
                        user_id = data.get("id")
                        if not user_id:
                            logger.warning(
                                "Token verification successful but id is empty",
                                extra={
                                    "data_keys": list(data.keys()),
                                    "active": data.get("active"),
                                },
                            )
                            return False, None
                        # Build user information
                        user_info = {
                            "id": user_id,
=======
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
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                            "username": data.get("username"),
                            "user_type": data.get("user_type"),
                            "permissions": data.get("permissions", []),
                            "roles": data.get("roles", []),
<<<<<<< HEAD
                            "mg_id": data.get("mg_id"),  # Management group ID (if available)
                        }

                        logger.info(
                            "Token verification successful",
                            extra={
                                "id": user_info["id"],
=======
                            "mg_id": data.get("mg_id"),  # 管理组ID（如果有）
                        }

                        logger.info(
                            "Token 验证成功",
                            extra={
                                "user_id": user_info["user_id"],
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                                "username": user_info["username"],
                                "user_type": user_info["user_type"],
                            },
                        )
                        return True, user_info
<<<<<<< HEAD
                    logger.warning("Token is expired or invalid")
                    return False, None
                logger.warning(
                    f"Token verification request failed: {response.status_code}",
                    extra={"status_code": response.status_code},
                )
                return False, None

        except httpx.TimeoutException:
            logger.error("Token verification timeout: auth-service not responding")
            return False, None

        except Exception as e:
            logger.error(f"Token verification exception: {e!s}", exc_info=True)
            return False, None

    async def extract_and_verify(self, request: Request) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """One-stop: extract and verify token

        Extract token from Request and verify with auth-service.

        Args:
            request: FastAPI Request object

        Returns:
            (is_valid, user information dictionary or None)
=======
                    else:
                        logger.warning("Token 已失效或无效")
                        return False, None
                else:
                    logger.warning(
                        f"Token 验证请求失败: {response.status_code}",
                        extra={"status_code": response.status_code},
                    )
                    return False, None

        except httpx.TimeoutException:
            logger.error(f"Token 验证超时: auth-service 无响应")
            return False, None

        except Exception as e:
            logger.error(f"Token 验证异常: {str(e)}", exc_info=True)
            return False, None

    async def extract_and_verify(self, request: Request) -> tuple[bool, Optional[Dict[str, Any]]]:
        """一步到位：提取并验证 token

        从 Request 中提取 token 并调用 auth-service 验证。

        Args:
            request: FastAPI Request 对象

        Returns:
            (是否有效, 用户信息字典或None)
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

        Example:
            >>> extractor = TokenExtractor()
            >>> is_valid, user_info = await extractor.extract_and_verify(request)
            >>> if is_valid:
<<<<<<< HEAD
            >>>     id = user_info["id"]
        """
        # Extract token
        token = self.extract_token_from_request(request)

        if not token:
            logger.warning("No token found in request")
            return False, None

        # Verify token
        return await self.verify_token(token)


# Global singleton instance
=======
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
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
_token_extractor_instance: Optional[TokenExtractor] = None


def get_token_extractor() -> TokenExtractor:
<<<<<<< HEAD
    """Get Token Extractor singleton instance

    Returns:
        TokenExtractor: Token Extractor instance
=======
    """获取 Token 提取器单例实例

    Returns:
        TokenExtractor: Token 提取器实例
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

    Example:
        >>> extractor = get_token_extractor()
        >>> token = extractor.extract_token_from_request(request)
    """
    global _token_extractor_instance

    if _token_extractor_instance is None:
        _token_extractor_instance = TokenExtractor()

    return _token_extractor_instance
