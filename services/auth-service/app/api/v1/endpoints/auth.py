"""
认证相关 API 端点

提供登录、令牌刷新、令牌验证、注销等功能
"""

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.api.v1.dependencies import get_auth_service
from app.schemas.auth import (
    AdminLoginRequest,
    DeviceLoginRequest,
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


@router.post("/admin/login", response_model=SuccessResponse, summary="管理员登录")
async def admin_login(
    login_data: AdminLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """管理员登录（传统方式）

    使用用户名和密码进行登录，返回访问令牌

    Args:
        login_data: 登录请求数据（username, ***REMOVED***word）
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 包含 token 的成功响应

    Raises:
        HTTPException: 登录失败时抛出
    """
    try:
        # 执行登录
        login_response = await auth_service.admin_login(login_data)

        logger.info(
            "管理员登录成功",
            extra={
                "operation": "admin_login",
                "username": login_data.username,
            },
        )

        return SuccessResponse(data=login_response.model_dump(), message="登录成功")

    except BusinessError as e:
        logger.warning(f"管理员登录失败: {e.message}")
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
        logger.error(f"管理员登录异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="登录失败",
                error_code="AUTH_LOGIN_ERROR",
            ).model_dump(),
        )


@router.post("/device/login", response_model=SuccessResponse, summary="设备登录")
async def device_login(
    login_data: DeviceLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """设备登录（传统方式）

    使用 mg_id、host_ip 和 username 进行登录
    如果 mg_id 存在则更新信息，不存在则创建新记录

    Args:
        login_data: 设备登录请求数据（mg_id, host_ip, username）
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 包含 token 的成功响应

    Raises:
        HTTPException: 登录失败时抛出
    """
    try:
        # 执行登录
        login_response = await auth_service.device_login(login_data)

        logger.info(
            "设备登录成功",
            extra={
                "operation": "device_login",
                "mg_id": login_data.mg_id,
                "host_ip": login_data.host_ip,
            },
        )

        return SuccessResponse(data=login_response.model_dump(), message="登录成功")

    except BusinessError as e:
        logger.warning(f"设备登录失败: {e.message}")
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
        logger.error(f"设备登录异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="登录失败",
                error_code="AUTH_LOGIN_ERROR",
            ).model_dump(),
        )


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
