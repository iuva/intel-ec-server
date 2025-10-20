"""
Admin Service 认证中间件

提供JWT令牌验证和权限检查
"""

from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.common.security import verify_token
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.common.security import verify_token

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""

    def __init__(self, app, public_paths: Optional[set] = None):
        """初始化认证中间件

        Args:
            app: FastAPI应用实例
            public_paths: 公开路径集合（不需要认证）
        """
        super().__init__(app)
        self.public_paths = public_paths or {
            "/",
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求

        Args:
            request: 请求对象
            call_next: 下一个处理函数

        Returns:
            响应对象
        """
        # 检查是否为公开路径
        path = request.url.path
        clean_path = path.split("?")[0]  # 移除查询参数

        if clean_path in self.public_paths:
            return await call_next(request)

        # 获取认证令牌
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"缺少认证令牌: {path}")
            return Response(
                content=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少认证令牌",
                    error_code="MISSING_TOKEN",
                ).model_dump_json(),
                status_code=HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )

        # 验证令牌
        token = auth_header.replace("Bearer ", "")
        payload = verify_token(token)

        if not payload:
            logger.warning(f"无效的认证令牌: {path}")
            return Response(
                content=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="无效的认证令牌",
                    error_code="INVALID_TOKEN",
                ).model_dump_json(),
                status_code=HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )

        # 将用户信息添加到请求状态
        request.state.user = {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "is_superuser": payload.get("is_superuser", False),
        }

        # 继续处理请求
        return await call_next(request)
