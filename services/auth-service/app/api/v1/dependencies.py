"""
API 依赖注入

提供服务实例的依赖注入函数
"""

from typing import Optional
from fastapi import Request

from app.services.auth_service import AuthService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.security import JWTManager
    from shared.common.loguru_config import get_logger
except ImportError:
    import sys
    import os

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.security import JWTManager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# 全局服务实例缓存
_auth_service_instance: Optional[AuthService] = None
_jwt_manager_instance: Optional[JWTManager] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例（单例模式）

    Returns:
        AuthService: 认证服务实例
    """
    global _auth_service_instance

    if _auth_service_instance is None:
        _auth_service_instance = AuthService()

    return _auth_service_instance


def get_jwt_manager() -> JWTManager:
    """获取JWT管理器实例（单例模式）

    Returns:
        JWTManager: JWT管理器实例
    """
    global _jwt_manager_instance

    if _jwt_manager_instance is None:
        _jwt_manager_instance = JWTManager(
            secret_key="your-secret-key-change-in-production",
            algorithm="HS256"
        )

    return _jwt_manager_instance


async def get_current_user(request: Request) -> Optional[dict]:
    """获取当前用户信息（从 token 解析）

    从请求的 Authorization 头中提取并验证 JWT token，
    返回 token 中的用户信息。如果没有 token，返回 None（可选）。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: 用户信息（包含 sub、username、permissions 等），或 None 如果未认证

    Raises:
        HTTPException: token 格式错误时抛出
    """
    try:
        # 从 Authorization 头提取 token
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            # 如果没有 token，返回 None（允许可选认证）
            return None

        token = auth_header[7:]  # 移除 "Bearer " 前缀

        # 验证 token
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.verify_token(token)

        if not payload:
            # token 验证失败，返回 None
            logger.warning("Token 验证失败")
            return None

        # 返回 token 中的用户信息
        return {
            "sub": payload.get("sub"),
            "username": payload.get("username"),
            "user_type": payload.get("user_type", "user"),
            "permissions": payload.get("permissions", []),
            "roles": payload.get("roles", []),
        }

    except Exception as e:
        logger.error(f"获取当前用户失败: {str(e)}")
        return None
