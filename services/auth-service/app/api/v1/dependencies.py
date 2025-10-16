"""
API 依赖注入

提供服务实例的依赖注入函数
"""

from typing import Optional

from app.services.auth_service import AuthService

# 全局服务实例缓存
_auth_service_instance: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例（单例模式）

    Returns:
        AuthService: 认证服务实例
    """
    global _auth_service_instance

    if _auth_service_instance is None:
        _auth_service_instance = AuthService()

    return _auth_service_instance
