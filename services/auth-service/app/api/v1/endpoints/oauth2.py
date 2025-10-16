"""
OAuth 2.0认证端点

实现OAuth 2.0标准的令牌端点、内省端点和撤销端点
"""

from typing import Optional, Union

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

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

from app.services.oauth2_service import OAuth2Service

logger = get_logger(__name__)

router = APIRouter()
security = HTTPBasic()


def get_oauth2_service() -> OAuth2Service:
    """获取OAuth 2.0服务实例"""
    return OAuth2Service()


# ruff: noqa: PLR0911  # 业务逻辑需要多个返回点进行错误处理
@router.post("/admin/token", response_model=Union[SuccessResponse, ErrorResponse])
async def admin_token(
    request: Request,
    grant_type: Optional[str] = Form(None, description="授权类型"),
    username: Optional[str] = Form(None, description="用户名"),
    ***REMOVED***word: Optional[str] = Form(None, description="密码"),
    scope: str = Form("admin", description="授权范围"),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> SuccessResponse:
    """管理后台令牌端点

    OAuth 2.0密码授权流程，用于管理后台用户认证。

    Args:
        request: FastAPI请求对象
        grant_type: 授权类型（必须为"***REMOVED***word"）
        username: 用户名（管理后台账号）
        ***REMOVED***word: 密码
        scope: 授权范围（默认为"admin"）
        credentials: HTTP基本认证凭据（客户端ID和密钥）
        oauth2_service: OAuth 2.0服务实例

    Returns:
        SuccessResponse: 包含访问令牌的成功响应

    Raises:
        HTTPException: 认证失败时抛出
    """
    try:
        # 手动验证HTTP Basic认证
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少客户端认证信息",
                    error_code="INVALID_CLIENT",
                ).model_dump(),
            )

        # 解码Basic认证
        import base64

        try:
            encoded_credentials = auth_header[6:]  # 移除"Basic "前缀
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            client_id, client_secret = decoded_credentials.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="客户端认证信息格式错误",
                    error_code="INVALID_CLIENT",
                ).model_dump(),
            )

        # 验证客户端凭据
        client = await oauth2_service.authenticate_client(client_id, client_secret)
        if not client:
            logger.info("OAuth2 admin token: 客户端凭据无效，返回错误响应")
            error_response = ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="无效的客户端凭据",
                error_code="INVALID_CLIENT",
            )
            result = error_response.model_dump()
            logger.info(f"OAuth2 admin token: 返回响应: {result}")
            return result

        # 验证必需的Form参数
        if not grant_type:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: grant_type",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        if not username:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: username",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        if not ***REMOVED***word:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: ***REMOVED***word",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        # 验证授权类型
        if grant_type != "***REMOVED***word":
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="不支持的授权类型",
                    error_code="UNSUPPORTED_GRANT_TYPE",
                ).model_dump(),
            )

        # 处理OAuth 2.0密码授权
        token_response = await oauth2_service.handle_admin_***REMOVED***word_grant(
            client_id=client_id, username=username, ***REMOVED***word=***REMOVED***word, scope=scope
        )

        logger.info(f"OAuth管理后台令牌生成成功: {username}")

        return SuccessResponse(
            data=token_response,
            message="管理后台认证成功",
        )

    except BusinessError as e:
        logger.warning(f"OAuth管理后台认证失败: {e.message}")
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message=e.message,
                error_code=e.error_code,
                details=e.details,
            ).model_dump(),
        )

    # 所有错误都通过直接返回JSONResponse处理，不再抛出HTTPException

    except Exception as e:
        logger.error(f"OAuth管理后台令牌异常: {type(e).__name__}: {e!s}")
        import traceback

        logger.error(f"异常详情: {traceback.format_exc()}")
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="管理后台认证失败",
                error_code="OAUTH_ADMIN_ERROR",
            ).model_dump(),
        )


# ruff: noqa: PLR0911  # 业务逻辑需要多个返回点进行错误处理
@router.post("/device/token", response_model=Union[SuccessResponse, ErrorResponse])
async def device_token(
    request: Request,
    grant_type: Optional[str] = Form(None, description="授权类型"),
    device_id: Optional[str] = Form(None, description="设备ID"),
    device_secret: Optional[str] = Form(None, description="设备密钥"),
    scope: str = Form("device", description="授权范围"),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> SuccessResponse:
    """设备令牌端点

    OAuth 2.0客户端凭据授权流程，用于设备认证。

    Args:
        request: FastAPI请求对象
        grant_type: 授权类型（必须为"client_credentials"）
        device_id: 设备ID（原mg_id）
        device_secret: 设备密钥
        scope: 授权范围（默认为"device"）
        credentials: HTTP基本认证凭据（客户端ID和密钥）
        oauth2_service: OAuth 2.0服务实例

    Returns:
        SuccessResponse: 包含访问令牌的成功响应

    Raises:
        HTTPException: 认证失败时抛出
    """
    try:
        # 手动验证HTTP Basic认证
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少客户端认证信息",
                    error_code="INVALID_CLIENT",
                ).model_dump(),
            )

        # 解码Basic认证
        import base64

        try:
            encoded_credentials = auth_header[6:]  # 移除"Basic "前缀
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            client_id, client_secret = decoded_credentials.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="客户端认证信息格式错误",
                    error_code="INVALID_CLIENT",
                ).model_dump(),
            )

        # 验证客户端凭据
        client = await oauth2_service.authenticate_client(client_id, client_secret)
        if not client:
            error_response = ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="无效的客户端凭据",
                error_code="INVALID_CLIENT",
            )
            return error_response.model_dump()

        # 验证必需的Form参数
        if not grant_type:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: grant_type",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        if not device_id:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: device_id",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        if not device_secret:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: device_secret",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        # 验证授权类型
        if grant_type != "client_credentials":
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="不支持的授权类型",
                    error_code="UNSUPPORTED_GRANT_TYPE",
                ).model_dump(),
            )

        # 处理OAuth 2.0客户端凭据授权
        token_response = await oauth2_service.handle_device_client_credentials_grant(
            client_id=client_id, device_id=device_id, device_secret=device_secret, scope=scope
        )

        logger.info(f"OAuth设备令牌生成成功: {device_id}")

        return SuccessResponse(
            data=token_response,
            message="设备认证成功",
        )

    except BusinessError as e:
        logger.warning(f"OAuth设备认证失败: {e.message}")
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message=e.message,
                error_code=e.error_code,
                details=e.details,
            ).model_dump(),
        )

    # 所有错误都通过直接返回JSONResponse处理，不再抛出HTTPException

    except Exception as e:
        logger.error(f"OAuth设备令牌异常: {e!s}")
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="设备认证失败",
                error_code="OAUTH_DEVICE_ERROR",
            ).model_dump(),
        )


@router.post("/introspect", response_model=Union[SuccessResponse, ErrorResponse])
async def introspect_token(
    token: Optional[str] = Form(None, description="要内省的令牌"),
    token_type_hint: str = Form("access_token", description="令牌类型提示"),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> SuccessResponse:
    """OAuth 2.0令牌内省端点

    验证令牌的有效性并返回令牌详细信息。

    Args:
        token: 要验证的令牌
        token_type_hint: 令牌类型提示（默认为access_token）
        oauth2_service: OAuth 2.0服务实例

    Returns:
        SuccessResponse: 包含令牌验证结果的成功响应
    """
    try:
        # 验证必需的Form参数
        if not token:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: token",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        # 执行令牌内省
        introspection_result = await oauth2_service.introspect_token(token)

        return SuccessResponse(
            data=introspection_result,
            message="令牌内省完成",
        )

    except Exception as e:
        logger.error(f"OAuth令牌内省异常: {e!s}")
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="令牌内省失败",
                error_code="OAUTH_INTROSPECT_ERROR",
            ).model_dump(),
        )


@router.post("/revoke", response_model=Union[SuccessResponse, ErrorResponse])
async def revoke_token(
    token: Optional[str] = Form(None, description="要撤销的令牌"),
    token_type_hint: str = Form("access_token", description="令牌类型提示"),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> SuccessResponse:
    """OAuth 2.0令牌撤销端点

    撤销指定的访问令牌或刷新令牌。

    Args:
        token: 要撤销的令牌
        token_type_hint: 令牌类型提示（默认为access_token）
        oauth2_service: OAuth 2.0服务实例

    Returns:
        SuccessResponse: 撤销结果的成功响应
    """
    try:
        # 验证必需的Form参数
        if not token:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    code=HTTP_400_BAD_REQUEST,
                    message="缺少必需参数: token",
                    error_code="MISSING_PARAMETER",
                ).model_dump(),
            )

        # 执行令牌撤销
        revoked = await oauth2_service.revoke_token(token)

        if not revoked:
            logger.warning("令牌撤销失败: 令牌不存在或已无效")

        return SuccessResponse(
            data={"revoked": revoked},
            message="令牌撤销完成",
        )

    except Exception as e:
        logger.error(f"OAuth令牌撤销异常: {e!s}")
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="令牌撤销失败",
                error_code="OAUTH_REVOKE_ERROR",
            ).model_dump(),
        )
