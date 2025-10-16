"""
Admin Service API 依赖注入

提供JWT认证、权限检查等依赖
"""

from typing import Dict, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

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

# HTTP Bearer 认证方案
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, str]:
    """获取当前用户信息

    从JWT令牌中解析用户信息

    Args:
        request: FastAPI请求对象
        credentials: HTTP认证凭据

    Returns:
        用户信息字典

    Raises:
        HTTPException: 认证失败
    """
    # 检查公开路径
    path = request.url.path
    public_paths = {
        "/",
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    # 移除查询参数进行路径匹配
    clean_path = path.split("?")[0]
    if clean_path in public_paths:
        return {}

    # 验证令牌
    if not credentials:
        logger.warning("缺少认证令牌")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="缺少认证令牌",
                error_code="MISSING_TOKEN",
            ).model_dump(),
        )

    try:
        token = credentials.credentials
        payload = verify_token(token)

        if not payload:
            logger.warning("无效的认证令牌")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="无效的认证令牌",
                    error_code="INVALID_TOKEN",
                ).model_dump(),
            )

        # 提取用户信息
        user_id = payload.get("sub")
        username = payload.get("username")

        if not user_id or not username:
            logger.warning("令牌格式错误")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="令牌格式错误",
                    error_code="INVALID_TOKEN_FORMAT",
                ).model_dump(),
            )

        return {"user_id": user_id, "username": username}

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"令牌验证异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="认证失败",
                error_code="AUTHENTICATION_FAILED",
            ).model_dump(),
        )


async def require_admin(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """要求管理员权限

    检查当前用户是否具有管理员权限

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典

    Raises:
        HTTPException: 权限不足
    """
    # 公开路径不需要权限检查
    if not current_user:
        return {}

    # 检查是否为超级用户
    is_superuser = current_user.get("is_superuser", False)

    if not is_superuser:
        logger.warning(f"用户权限不足: {current_user.get('username')}")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                code=HTTP_403_FORBIDDEN,
                message="权限不足，需要管理员权限",
                error_code="INSUFFICIENT_PERMISSIONS",
            ).model_dump(),
        )

    return current_user
