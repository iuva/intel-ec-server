"""
认证中间件模块

负责验证请求的 JWT 令牌，调用 Auth Service 进行令牌验证
"""

import os
import sys
from typing import Any, Dict, Optional

# 使用 try-except 方式处理路径导入
try:
    import httpx
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    import httpx
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse


logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件

    拦截所有请求，验证 JWT 令牌有效性
    """

    def __init__(self, app):
        """初始化认证中间件

        Args:
            app: FastAPI 应用实例
        """
        super().__init__(app)

        # 公开路径白名单（不需要认证）
        self.public_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/test-error",  # 测试用
            # OAuth 2.0认证端点（公开访问）
            "/api/v1/auth-service/api/v1/oauth2/admin/token",
            "/api/v1/auth-service/api/v1/oauth2/device/token",
            "/api/v1/auth-service/api/v1/oauth2/introspect",
            "/api/v1/auth-service/api/v1/oauth2/revoke",
        }

        # Auth Service URL
        self.auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")

        # HTTP 客户端配置
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def dispatch(self, request: Request, call_next):
        """处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # 检查是否为公开路径
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # 获取 Authorization 头
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(
                "缺少 Authorization 头",
                extra={"path": request.url.path, "method": request.method},
            )
            return self._unauthorized_response("缺少认证令牌")

        # 验证令牌格式
        if not auth_header.startswith("Bearer "):
            logger.warning(
                "无效的 Authorization 头格式",
                extra={"path": request.url.path, "auth_header": auth_header},
            )
            return self._unauthorized_response("无效的认证令牌格式")

        # 提取令牌
        token = auth_header[7:]  # 移除 "Bearer " 前缀

        # 验证令牌
        user_info = await self._verify_token(token)

        if not user_info:
            logger.warning(
                "令牌验证失败",
                extra={"path": request.url.path, "method": request.method},
            )
            return self._unauthorized_response("无效或过期的认证令牌")

        # 将用户信息添加到请求状态
        request.state.user = user_info

        # 继续处理请求
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径

        Args:
            path: 请求路径

        Returns:
            是否为公开路径
        """
        # 移除查询参数
        clean_path = path.split("?")[0]

        # 检查精确匹配
        if clean_path in self.public_paths:
            return True

        # 检查路径前缀匹配（用于 API 文档等）
        return any(clean_path.startswith(public_path) for public_path in self.public_paths)

    async def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证OAuth 2.0令牌

        调用 Auth Service 的 OAuth 2.0 introspect 端点验证令牌

        Args:
            token: OAuth 2.0 访问令牌

        Returns:
            用户信息，如果验证失败则返回 None
        """
        try:
            # 使用OAuth 2.0 introspect端点
            introspect_url = f"{self.auth_service_url}/api/v1/oauth2/introspect"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    introspect_url,
                    data={"token": token},  # OAuth 2.0使用form data
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    result = response.json()

                    # 检查令牌是否有效
                    if result.get("code") == 200:
                        data = result.get("data", {})
                        if data.get("active"):
                            # 构造用户信息（适配现有网关逻辑）
                            user_info = {
                                "user_id": data.get("sub"),
                                "username": data.get("username"),
                                "permissions": data.get("permissions", []),
                                "client_id": data.get("client_id"),
                                "scope": data.get("scope"),
                                "user_type": data.get("user_type"),
                                "device_id": data.get("device_id"),
                                "host_ip": data.get("host_ip"),
                                "active": data.get("active"),
                            }

                            logger.debug(
                                "OAuth令牌验证成功",
                                extra={
                                    "user_id": user_info.get("user_id"),
                                    "username": user_info.get("username"),
                                    "client_id": user_info.get("client_id"),
                                    "user_type": user_info.get("user_type"),
                                },
                            )
                            return user_info

                logger.warning(
                    "OAuth令牌验证失败",
                    extra={
                        "status_code": response.status_code,
                        "response": response.text[:200],
                    },
                )
                return None

        except httpx.TimeoutException:
            logger.error("OAuth令牌验证超时", extra={"auth_service_url": self.auth_service_url})
            return None

        except httpx.ConnectError:
            logger.error("无法连接到认证服务", extra={"auth_service_url": self.auth_service_url})
            return None

        except Exception as e:
            logger.error(
                "OAuth令牌验证异常",
                extra={"error": str(e), "auth_service_url": self.auth_service_url},
                exc_info=True,
            )
            return None

    def _unauthorized_response(self, message: str) -> JSONResponse:
        """返回未授权响应

        Args:
            message: 错误消息

        Returns:
            JSON 响应
        """
        error_response = ErrorResponse(
            code=401,
            message=message,
            error_code="UNAUTHORIZED",
        )

        return JSONResponse(
            status_code=401,
            content=error_response.model_dump(),
        )
