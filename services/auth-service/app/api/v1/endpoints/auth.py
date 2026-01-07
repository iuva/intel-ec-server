"""
认证相关 API 端点

提供登录、令牌刷新、令牌验证、注销等功能
"""

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_auth_service, get_current_user
from app.schemas.auth import (
    AdminLoginRequest,
    AutoRefreshTokenRequest,
    DeviceLoginRequest,
    IntrospectRequest,
    IntrospectResponse,
    LoginResponse,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("/admin/login", response_model=Result[LoginResponse], summary="管理员登录")
@handle_api_errors
async def admin_login(
    login_data: AdminLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[LoginResponse]:
    """管理员登录（传统方式）

    使用用户名和密码进行登录，返回访问令牌

    Args:
        login_data: 登录请求数据（username, ***REMOVED***word）
        auth_service: 认证服务实例

    Returns:
        Result[LoginResponse]: 包含 token 的成功响应

    Raises:
        HTTPException: 登录失败时抛出（由 @handle_api_errors 统一处理）
    """
    # 执行登录
    login_response = await auth_service.admin_login(login_data)

    logger.info(
        "管理员登录成功",
        extra={
            "operation": "admin_login",
            "username": login_data.username,
        },
    )

    return Result(
        code=200,
        message=t("success.login", locale=locale, default="登录成功"),
        data=login_response,
        locale=locale,
    )


@router.post("/device/login", response_model=Result[LoginResponse], summary="设备登录")
@handle_api_errors
async def device_login(
    login_data: DeviceLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Optional[dict] = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[LoginResponse]:
    """设备登录（传统方式）

    使用 mg_id、host_ip 和 username 进行登录
    如果 mg_id 存在则更新信息，不存在则创建新记录

    Args:
        login_data: 设备登录请求数据（mg_id, host_ip, username）
        auth_service: 认证服务实例
        current_user: 当前用户信息（可选，用于审计）

    Returns:
        Result[LoginResponse]: 包含 token 的成功响应

    Raises:
        HTTPException: 登录失败时抛出（由 @handle_api_errors 统一处理）
    """
    # 从当前用户信息中获取 user_id（如果已认证）
    current_user_id = None
    if current_user:
        # ✅ 统一使用 id 字段（从 id 或 sub 提取，向后兼容）
        user_id = current_user.get("id") or current_user.get("sub")
        if user_id:
            try:
                current_user_id = int(user_id)
            except (ValueError, TypeError):
                logger.warning(
                    "无法将 user_id 转换为整数",
                    extra={
                        "user_id": user_id,
                        "user_id_type": type(user_id).__name__,
                    },
                )
                current_user_id = None

    # 执行登录，传递当前用户ID用于审计
    login_response = await auth_service.device_login(login_data, current_user_id=current_user_id)

    logger.info(
        "设备登录成功",
        extra={
            "operation": "device_login",
            "mg_id": login_data.mg_id,
            "host_ip": login_data.host_ip,
            "current_user_id": current_user_id,
        },
    )

    return Result(
        code=200,
        message=t("success.login", locale=locale, default="登录成功"),
        data=login_response,
        locale=locale,
    )


@router.post("/refresh", response_model=Result[TokenResponse])
@handle_api_errors
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[TokenResponse]:
    """刷新访问令牌

    Args:
        refresh_data: 刷新令牌请求数据
        auth_service: 认证服务实例

    Returns:
        Result[TokenResponse]: 包含新令牌的成功响应

    Raises:
        HTTPException: 刷新失败时抛出（由 @handle_api_errors 统一处理）
    """
    # 刷新令牌
    token_response = await auth_service.refresh_access_token(refresh_data)

    logger.info(
        "令牌刷新成功",
        extra={
            "operation": "refresh_token",
            "token_type": "refresh",
            "response_type": type(token_response).__name__,
        },
    )

    return Result(
        code=200,
        message=t("success.operation", locale=locale, default="操作成功"),
        data=token_response,
        locale=locale,
    )


@router.post("/auto-refresh", response_model=Result[TokenResponse], summary="自动续期令牌")
@handle_api_errors
async def auto_refresh_tokens(
    refresh_data: AutoRefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[TokenResponse]:
    """自动续期访问令牌和刷新令牌

    当刷新令牌将要过期时，同时生成新的 access_token 和 refresh_token
    实现真正的"双 token 续期"机制

    Args:
        refresh_data: 自动续期请求数据（包含 auto_renew 参数）
        auth_service: 认证服务实例

    Returns:
        Result[TokenResponse]: 包含新的 access_token 和 refresh_token 的成功响应

    Raises:
        HTTPException: 续期失败时抛出（由 @handle_api_errors 统一处理）
    """
    # 自动续期令牌
    token_response = await auth_service.auto_refresh_tokens(refresh_data)

    logger.info(
        "令牌自动续期成功",
        extra={
            "operation": "auto_refresh_token",
            "auto_renew": refresh_data.auto_renew,
        },
    )

    return Result(
        code=200,
        message=t("success.operation", locale=locale, default="操作成功"),
        data=token_response,
        locale=locale,
    )


@router.post("/introspect", response_model=Result[IntrospectResponse])
@handle_api_errors
async def introspect_token(
    introspect_data: IntrospectRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[IntrospectResponse]:
    """验证令牌

    Args:
        introspect_data: 令牌验证请求数据
        auth_service: 认证服务实例

    Returns:
        Result[IntrospectResponse]: 包含令牌验证结果的成功响应
    """
    try:
        # 验证令牌
        introspect_response = await auth_service.introspect_token(introspect_data.token)

        return Result(
            code=200,
            message=t("success.operation", locale=locale, default="验证成功"),
            data=introspect_response,
            locale=locale,
        )

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(
            "令牌验证异常",
            extra={
                "operation": "introspect",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # ✅ 正确：直接返回标准的成功响应，active=false 表示令牌无效
        # 不抛出 HTTPException，保持响应格式一致性
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
            message=t("error.auth.token_expired", locale=locale, default="令牌验证失败"),
            data=error_response,
            locale=locale,
        )


@router.post("/logout", response_model=SuccessResponse)
@handle_api_errors
async def logout(
    logout_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """用户注销

    Args:
        logout_data: 注销请求数据
        auth_service: 认证服务实例

    Returns:
        SuccessResponse: 注销成功响应

    Raises:
        HTTPException: 注销失败时抛出（由 @handle_api_errors 统一处理）
    """
    # 执行注销
    await auth_service.logout(logout_data.token)

    logger.info(
        "用户注销成功",
        extra={
            "operation": "logout",
        },
    )

    return SuccessResponse(
        data=None,
        message_key="success.logout",
        locale=locale,
    )
