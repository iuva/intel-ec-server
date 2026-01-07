"""
API 依赖注入

提供服务实例的依赖注入函数
"""

import os
import sys
from typing import Any, Dict, Optional

from fastapi import Request

from app.services.auth_service import AuthService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

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


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """获取当前用户信息（从 Gateway 传递的 X-User-Info header 获取）

    ✅ 架构说明：
    - 所有 token 验证都在 Gateway 中完成，Gateway 调用 auth-service 验证 token
    - Gateway 验证成功后，将用户信息通过 X-User-Info header 传递给后端服务
    - 后端服务不再验证 token，只从 X-User-Info header 中读取用户信息
    - 如果没有 X-User-Info header，返回 None（允许可选认证场景）

    ✅ 注意：
    - 统一使用 `id` 字段
    - 支持可选认证（某些端点允许未认证访问，如 device_login 用于审计）
    - 如果缺少 X-User-Info header，返回 None 而不是报错（可选认证）

    Args:
        request: FastAPI 请求对象

    Returns:
        Optional[Dict[str, Any]]: 用户信息字典，包含：
            - id: 用户ID（统一字段）
            - username: 用户名
            - user_type: 用户类型（admin/device/user）
            - permissions: 权限列表
            - roles: 角色列表
        如果没有 X-User-Info header，返回 None（可选认证）

    Example:
        >>> @router.post("/device/login")
        >>> async def device_login(
        >>>     current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
        >>> ):
        >>>     if current_user:
        >>>         user_id = current_user.get("id")
    """
    try:
        import json

        # ✅ 只从 Gateway 传递的 X-User-Info header 中获取用户信息
        # Gateway 已经在认证中间件中验证了 token，并将用户信息存储在 X-User-Info header 中
        user_info_header = request.headers.get("X-User-Info")

        if not user_info_header:
            # ✅ 如果没有 X-User-Info header，返回 None（允许可选认证）
            logger.debug(
                "请求未包含 X-User-Info header（可选认证）",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "请求应该通过 Gateway 转发，Gateway 会在认证后传递 X-User-Info header",
                },
            )
            return None

        # 解析用户信息 JSON
        try:
            user_info = json.loads(user_info_header)

            # ✅ 统一使用 id 字段
            user_id = user_info.get("id")
            if not user_id:
                logger.warning(
                    "X-User-Info header 中缺少 id 字段",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "user_info_keys": list(user_info.keys()),
                        "hint": "Gateway 应该确保 X-User-Info header 包含 id 字段",
                    },
                )
                # 即使缺少 id，也返回用户信息（可选认证）
                # 让业务层决定如何处理

            # ✅ 构建统一的用户信息字典
            result: Dict[str, Any] = {
                "id": str(user_id) if user_id else None,
                "username": user_info.get("username"),
                "user_type": user_info.get("user_type", "user"),
                "permissions": user_info.get("permissions", []),
                "roles": user_info.get("roles", []),
            }

            # ✅ 保留 sub 字段以兼容旧代码（向后兼容）
            if user_info.get("sub"):
                result["sub"] = user_info["sub"]

            logger.debug(
                "从 Gateway 获取用户信息成功",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "user_id": result["id"],
                    "username": result["username"],
                    "user_type": result["user_type"],
                },
            )

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "解析 X-User-Info header 失败",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "header_preview": (
                        user_info_header[:100] + "..."
                        if len(user_info_header) > 100
                        else user_info_header
                    ),
                    "hint": "Gateway 传递的 X-User-Info header 格式错误",
                },
                exc_info=True,
            )
            # 解析失败，返回 None（可选认证）
            return None

    except Exception as e:
        logger.error(
            "获取当前用户失败",
            extra={
                "path": request.url.path,
                "method": request.method,
                "operation": "get_current_user",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # 异常时返回 None，允许可选认证的端点继续处理
        return None
