"""
Authentication-related API endpoints

Provide functions such as login, token refresh, token validation, logout, etc.
"""

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_auth_service, get_current_user
from app.schemas.auth import (
    AdminLoginRequest,
<<<<<<< HEAD
<<<<<<< HEAD
    AutoRefreshTokenRequest,
=======
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
    AutoRefreshTokenRequest,
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
    DeviceLoginRequest,
    IntrospectRequest,
    IntrospectResponse,
    LoginResponse,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

# Use try-except approach to handle path imports
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse
except ImportError:
    # If import fails, add project root directory to Python path
    import os
    import sys

    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    )
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


<<<<<<< HEAD
@router.post(
    "/admin/login", response_model=Result[LoginResponse], summary="Admin Login"
)
@handle_api_errors
async def admin_login(
    login_data: AdminLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[LoginResponse]:
    """Admin login (traditional method)

    Use username and ***REMOVED***word to login, return access token

    Args:
        login_data: Login request data (username, ***REMOVED***word)
        auth_service: Authentication service instance

    Returns:
        Result[LoginResponse]: Success response containing token

    Raises:
        HTTPException: Thrown when login fails (handled uniformly by @handle_api_errors)
    """
    # Execute login
    login_response = await auth_service.admin_login(login_data)

    logger.info(
        "Admin login successful",
        extra={
            "operation": "admin_login",
            "username": login_data.username,
        },
    )

    return Result(
        code=200,
        message=t("success.login", locale=locale, default="Login successful"),
        data=login_response,
        locale=locale,
    )


@router.post(
    "/device/login", response_model=Result[LoginResponse], summary="Device Login"
)
@handle_api_errors
async def device_login(
    login_data: DeviceLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Optional[dict] = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[LoginResponse]:
    """Device login (traditional method)

    Use mg_id, host_ip and username to login
    If mg_id exists, update information; if not, create new record

    Args:
        login_data: Device login request data (mg_id, host_ip, username)
        auth_service: Authentication service instance
        current_user: Current user information (optional, for audit)

    Returns:
        Result[LoginResponse]: Success response containing token

    Raises:
        HTTPException: Thrown when login fails (handled uniformly by @handle_api_errors)
    """
    # Get user_id from current user information (if authenticated)
    current_user_id = None
    if current_user:
        # ✅ Uniformly use id field (extract from id or sub, backward compatible)
        user_id = current_user.get("id") or current_user.get("sub")
        if user_id:
            try:
                current_user_id = int(user_id)
            except (ValueError, TypeError):
                logger.warning(
                    "Unable to convert user_id to integer",
                    extra={
                        "user_id": user_id,
                        "user_id_type": type(user_id).__name__,
                    },
                )
                current_user_id = None

    # Execute login, ***REMOVED*** current user ID for audit
    login_response = await auth_service.device_login(
        login_data, current_user_id=current_user_id
    )

    logger.info(
        "Device login successful",
        extra={
            "operation": "device_login",
            "mg_id": login_data.mg_id,
            "host_ip": login_data.host_ip,
            "current_user_id": current_user_id,
        },
    )

    return Result(
        code=200,
        message=t("success.login", locale=locale, default="Login successful"),
        data=login_response,
        locale=locale,
    )


@router.post("/refresh", response_model=Result[TokenResponse])
@handle_api_errors
=======
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
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[TokenResponse]:
    """Refresh access token

    Args:
        refresh_data: Refresh token request data
        auth_service: Authentication service instance

    Returns:
        Result[TokenResponse]: Success response containing new token

    Raises:
        HTTPException: Thrown when refresh fails (handled uniformly by @handle_api_errors)
    """
    # Refresh token
    token_response = await auth_service.refresh_access_token(refresh_data)

<<<<<<< HEAD
    logger.info(
        "Token refresh successful",
        extra={
            "operation": "refresh_token",
            "token_type": "refresh",
            "response_type": type(token_response).__name__,
        },
    )

    return Result(
        code=200,
        message=t("success.operation", locale=locale, default="Operation successful"),
        data=token_response,
        locale=locale,
    )


@router.post(
    "/auto-refresh", response_model=Result[TokenResponse], summary="Auto Renew Token"
)
@handle_api_errors
async def auto_refresh_tokens(
    refresh_data: AutoRefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[TokenResponse]:
    """Auto renew access token and refresh token

    When refresh token is about to expire, generate new access_token and refresh_token simultaneously
    Implement true "dual token renewal" mechanism

    Args:
        refresh_data: Auto renewal request data (contains auto_renew parameter)
        auth_service: Authentication service instance

    Returns:
        Result[TokenResponse]: Success response containing new access_token and refresh_token

    Raises:
        HTTPException: Thrown when renewal fails (handled uniformly by @handle_api_errors)
    """
    # Auto renew token
    token_response = await auth_service.auto_refresh_tokens(refresh_data)

    logger.info(
        "Token auto renewal successful",
        extra={
            "operation": "auto_refresh_token",
            "auto_renew": refresh_data.auto_renew,
        },
    )

    return Result(
        code=200,
        message=t("success.operation", locale=locale, default="Operation successful"),
        data=token_response,
        locale=locale,
    )


@router.post("/introspect", response_model=Result[IntrospectResponse])
@handle_api_errors
=======
        logger.info(
            "令牌刷新成功",
            extra={
                "operation": "refresh_token",
                "token_type": "refresh",
                "response_type": type(token_response).__name__,
            },
        )

        return SuccessResponse(data=token_response.model_dump(), message="令牌刷新成功")

    except BusinessError as e:
        logger.warning(
            "令牌刷新失败",
            extra={
                "operation": "refresh_token",
                "error_code": e.error_code,
                "error_message": e.message,
                "details": e.details,
            },
        )
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


@router.post("/auto-refresh", response_model=SuccessResponse, summary="自动续期令牌")
async def auto_refresh_tokens(
    refresh_data: AutoRefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """自动续期访问令牌和刷新令牌

    当刷新令牌将要过期时，同时生成新的 access_token 和 refresh_token
    实现真正的"双 token 续期"机制

    Args:
        refresh_data: 自动续期请求数据（包含 auto_renew 参数）
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 包含新的 access_token 和 refresh_token 的成功响应

    Raises:
        HTTPException: 续期失败时抛出
    """
    try:
        # 自动续期令牌
        token_response = await auth_service.auto_refresh_tokens(refresh_data)

        logger.info("令牌自动续期成功", extra={"auto_renew": refresh_data.auto_renew})

        return SuccessResponse(
            data=token_response.model_dump(),
            message="令牌续期成功",
        )

    except BusinessError as e:
        logger.warning(f"令牌续期失败: {e.message}")
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
        logger.error(f"令牌续期异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="令牌续期失败",
                error_code="AUTH_REFRESH_ERROR",
            ).model_dump(),
        )


@router.post("/introspect", response_model=SuccessResponse)
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
async def introspect_token(
    introspect_data: IntrospectRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[IntrospectResponse]:
    """Validate token

    Args:
        introspect_data: Token validation request data
        auth_service: Authentication service instance

    Returns:
        Result[IntrospectResponse]: Success response containing token validation result
    """
    try:
        # Validate token
        introspect_response = await auth_service.introspect_token(introspect_data.token)

        return Result(
            code=200,
            message=t(
                "success.operation", locale=locale, default="Validation successful"
            ),
            data=introspect_response,
            locale=locale,
        )

    except (ValueError, KeyError, AttributeError) as e:
<<<<<<< HEAD
        logger.error(
            "Token validation exception",
            extra={
                "operation": "introspect",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # ✅ Correct: Directly return standard success response, active=false indicates invalid token
        # Don't throw HTTPException, maintain response format consistency
        error_response = IntrospectResponse(
            active=False,
            username=None,
            user_id=None,
            exp=None,
            token_type=None,
            error=str(e),
        )
        return Result(
            code=200,
            message=t(
                "error.auth.token_expired",
                locale=locale,
                default="Token validation failed",
            ),
            data=error_response,
            locale=locale,
=======
        logger.error(f"令牌验证异常: {e!s}")
        # ✅ 正确：直接返回标准的成功响应，active=false 表示令牌无效
        # 不抛出 HTTPException，保持响应格式一致性
        return SuccessResponse(
            data={"active": False, "username": None, "user_id": None, "exp": None, "token_type": None, "error": str(e)},
            message="令牌验证失败或已过期",
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)
        )


@router.post("/logout", response_model=SuccessResponse)
@handle_api_errors
async def logout(
    logout_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """User logout

    Args:
        logout_data: Logout request data
        auth_service: Authentication service instance

    Returns:
        SuccessResponse: Logout success response

    Raises:
        HTTPException: Thrown when logout fails (handled uniformly by @handle_api_errors)
    """
    # Execute logout
    await auth_service.logout(logout_data.token)

    logger.info(
        "User logout successful",
        extra={
            "operation": "logout",
        },
    )

    return SuccessResponse(
        data=None,
        message_key="success.logout",
        locale=locale,
    )
