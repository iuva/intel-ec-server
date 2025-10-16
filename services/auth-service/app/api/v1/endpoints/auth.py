"""
认证相关 API 端点

提供登录、令牌刷新、令牌验证、注销等功能
"""

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.api.v1.dependencies import get_auth_service
from app.schemas.auth import (
    IntrospectRequest,
    LogoutRequest,
    RefreshTokenRequest,
)
from app.services.auth_service import AuthService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """刷新访问令牌

    Args:
        refresh_data: 刷新令牌请求数据
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 包含新令牌的成功响应

    Raises:
        HTTPException: 刷新失败时抛出
    """
    try:
        # 刷新令牌
        token_response = await auth_service.refresh_access_token(refresh_data)

        logger.info("令牌刷新成功")

        return SuccessResponse(data=token_response.model_dump(), message="令牌刷新成功")

    except BusinessError as e:
        logger.warning(f"令牌刷新失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message=e.message,
                error_code=e.error_code,
                details=e.details,
            ).model_dump(),
        )

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"令牌刷新异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="令牌刷新失败",
                error_code="AUTH_REFRESH_ERROR",
            ).model_dump(),
        )


@router.post("/introspect", response_model=SuccessResponse)
async def introspect_token(
    introspect_data: IntrospectRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """验证令牌

    Args:
        introspect_data: 令牌验证请求数据
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 包含令牌验证结果的成功响应
    """
    try:
        # 验证令牌
        introspect_response = await auth_service.introspect_token(introspect_data.token)

        return SuccessResponse(data=introspect_response.model_dump(), message="令牌验证完成")

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"令牌验证异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="令牌验证失败",
                error_code="AUTH_INTROSPECT_ERROR",
            ).model_dump(),
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    logout_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """用户注销

    Args:
        logout_data: 注销请求数据
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 注销成功响应

    Raises:
        HTTPException: 注销失败时抛出
    """
    try:
        # 执行注销
        await auth_service.logout(logout_data.token)

        logger.info("用户注销成功")

        return SuccessResponse(data=None, message="注销成功")

    except BusinessError as e:
        logger.warning(f"注销失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message=e.message,
                error_code=e.error_code,
                details=e.details,
            ).model_dump(),
        )

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"注销异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="注销失败",
                error_code="AUTH_LOGOUT_ERROR",
            ).model_dump(),
        )
