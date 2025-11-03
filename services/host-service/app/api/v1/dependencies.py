"""
<<<<<<< HEAD
Host Service API dependency injection

Provides dependency injection functions for service instances
"""

import json
import os
import sys
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED

# Use try-except to handle path imports
try:
    from app.services.admin_appr_host_service import AdminApprHostService
    from app.services.admin_host_service import AdminHostService
    from app.services.admin_ota_service import AdminOtaService
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.file_manage_service import FileManageService
    from app.services.host_discovery_service import HostDiscoveryService
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.admin_appr_host_service import AdminApprHostService
    from app.services.admin_host_service import AdminHostService
    from app.services.admin_ota_service import AdminOtaService
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.file_manage_service import FileManageService
    from app.services.host_discovery_service import HostDiscoveryService
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse

logger = get_logger(__name__)


# ==================== Helper Functions ====================


def _get_locale_from_request(request: Request) -> str:
    """Get language preference from request

    Args:
        request: FastAPI request object

    Returns:
        Language code (e.g., "zh_CN", "en_US")
    """
    accept_language = request.headers.get("Accept-Language")
    return parse_accept_language(accept_language)


def _create_auth_error_response(
    request: Request,
    message: str,
    message_key: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
) -> HTTPException:
    """Create authentication error response

    Args:
        request: FastAPI request object
        message: Error message
        message_key: Error message key (for internationalization)
        error_code: Error code
        details: Error details

    Returns:
        HTTPException: Authentication error exception
    """
    locale = _get_locale_from_request(request)
    return HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail=ErrorResponse(
            code=HTTP_401_UNAUTHORIZED,
            message=message,
            message_key=message_key,
            error_code=error_code,
            locale=locale,
            details=details,
        ).model_dump(),
    )


def _parse_user_info_header(user_info_header: str) -> Dict[str, Any]:
    """Parse X-User-Info header

    Args:
        user_info_header: X-User-Info header value

    Returns:
        Parsed user information dictionary

    Raises:
        ValueError: Raises when parsing fails
    """
    if not user_info_header or not user_info_header.strip():
        raise ValueError("X-User-Info header is empty")

    user_info = json.loads(user_info_header)

    if not isinstance(user_info, dict):
        raise ValueError(f"X-User-Info parsed result is not dict type, but: {type(user_info).__name__}")

    return user_info


# ==================== Global Service Instance Cache ====================

# Global service instance cache (using Optional type annotation)
_browser_host_service_instance: Optional[BrowserHostService] = None
_browser_vnc_service_instance: Optional[BrowserVNCService] = None
_host_discovery_service_instance: Optional[HostDiscoveryService] = None
_admin_host_service_instance: Optional[Any] = None
_admin_appr_host_service_instance: Optional[Any] = None
_admin_ota_service_instance: Optional["AdminOtaService"] = None
_file_manage_service_instance: Optional["FileManageService"] = None


def get_host_service() -> BrowserHostService:
    """Get browser extension host service instance (singleton pattern)

    Returns:
        BrowserHostService: Browser extension host service instance
    """
    global _browser_host_service_instance

    if _browser_host_service_instance is None:
        _browser_host_service_instance = BrowserHostService()

    return _browser_host_service_instance


def get_vnc_service() -> BrowserVNCService:
    """Get browser extension VNC service instance (singleton pattern)

    Returns:
        BrowserVNCService: Browser extension VNC service instance
    """
    global _browser_vnc_service_instance

    if _browser_vnc_service_instance is None:
        _browser_vnc_service_instance = BrowserVNCService()

    return _browser_vnc_service_instance


def get_host_discovery_service() -> HostDiscoveryService:
    """Get host discovery service instance (singleton pattern)

    Reads hardware API URL configuration from environment variables and injects it into HostDiscoveryService.

    Returns:
        HostDiscoveryService: Host discovery service instance
    """
    global _host_discovery_service_instance

    if _host_discovery_service_instance is None:
        # Read hardware API URL from environment variables
        hardware_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
        _host_discovery_service_instance = HostDiscoveryService(hardware_api_url)

    return _host_discovery_service_instance


def get_admin_host_service() -> Any:
    """Get admin backend host service instance (singleton pattern)

    Returns:
        AdminHostService: Admin backend host service instance
    """
    global _admin_host_service_instance

    if _admin_host_service_instance is None:
        _admin_host_service_instance = AdminHostService()

    return _admin_host_service_instance


def get_admin_appr_host_service() -> Any:
    """Get admin backend pending approval host service instance (singleton pattern)

    Returns:
        AdminApprHostService: Admin backend pending approval host service instance
    """
    global _admin_appr_host_service_instance

    if _admin_appr_host_service_instance is None:
        _admin_appr_host_service_instance = AdminApprHostService()

    return _admin_appr_host_service_instance


def get_admin_ota_service() -> "AdminOtaService":
    """Get admin backend OTA service instance (singleton pattern)

    Returns:
        AdminOtaService: Admin backend OTA service instance
    """
    global _admin_ota_service_instance

    if _admin_ota_service_instance is None:
        _admin_ota_service_instance = AdminOtaService()

    return _admin_ota_service_instance


def get_file_manage_service() -> "FileManageService":
    """Get file management service instance (singleton pattern)

    Returns:
        FileManageService: File management service instance
    """
    global _file_manage_service_instance

    if _file_manage_service_instance is None:
        _file_manage_service_instance = FileManageService()

    return _file_manage_service_instance


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user information (from X-User-Info header ***REMOVED***ed by Gateway)

    ✅ Architecture notes:
    - Gateway has already verified token and extracted id, ensures id exists before forwarding request
    - Gateway has already removed client-provided X-User-Info header and added its own header
    - Backend service only needs to read user information from X-User-Info header

    Args:
        request: FastAPI request object

    Returns:
        dict: User information, contains id, username, user_type, active and other fields

    Raises:
        HTTPException: Raises 401 when X-User-Info header is missing or parsing fails
    """
    # ✅ Get user information from X-User-Info header ***REMOVED***ed by Gateway
    user_info_header = request.headers.get("X-User-Info")

    if not user_info_header:
        logger.warning(
            "Missing X-User-Info header",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise _create_auth_error_response(
            request=request,
            message="Missing user authentication information",
            message_key="error.auth.missing_user_info",
            error_code="UNAUTHORIZED",
            details={
                "hint": "Request must be forwarded through Gateway, "
                "Gateway will ***REMOVED*** X-User-Info header after authentication"
            },
        )

    # Parse user information JSON
    try:
        user_info = _parse_user_info_header(user_info_header)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            "Failed to parse X-User-Info header",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise _create_auth_error_response(
            request=request,
            message="User information format error",
            message_key="error.auth.invalid_user_info",
            error_code="INVALID_USER_INFO",
        )

    # ✅ Gateway has already ensured id exists, directly return user information
    return {
        "id": user_info.get("id"),
        "username": user_info.get("username"),
        "user_type": user_info.get("user_type"),
        "active": user_info.get("active"),
    }


async def get_current_agent(request: Request) -> Dict[str, Any]:
    """Get current Agent information (from X-User-Info header ***REMOVED***ed by Gateway)

    ✅ Architecture notes:
    - Gateway has already verified token and extracted id, ensures id exists before forwarding request
    - Gateway has already removed client-provided X-User-Info header and added its own header
    - Backend service only needs to read user information from X-User-Info header and verify user_type must be "device"

    Args:
        request: FastAPI request object

    Returns:
        dict: Agent information, contains id, username, user_type, permissions, mg_id and other fields

    Raises:
        HTTPException: Raises 401 when X-User-Info header is missing, parsing fails, or user_type is not "device"

    Example:
        >>> @router.post("/hardware/report")
        >>> async def report_hardware(
        >>>     agent_info: Dict[str, Any] = Depends(get_current_agent)
        >>> ):
        >>>     host_id = agent_info["id"]
    """
    # ✅ Get user information from X-User-Info header ***REMOVED***ed by Gateway
    user_info_header = request.headers.get("X-User-Info")

    if not user_info_header:
        logger.warning(
            "Agent request missing X-User-Info header",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise _create_auth_error_response(
            request=request,
            message="Missing user authentication information",
            message_key="error.auth.missing_user_info",
            error_code="UNAUTHORIZED",
            details={
                "hint": "Request must be forwarded through Gateway, "
                "Gateway will ***REMOVED*** X-User-Info header after authentication"
            },
        )

    # Parse user information JSON
    try:
        user_info = _parse_user_info_header(user_info_header)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            "Failed to parse X-User-Info header",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise _create_auth_error_response(
            request=request,
            message="User information format error",
            message_key="error.auth.invalid_user_info",
            error_code="INVALID_USER_INFO",
        )

    # ✅ Verify user_type must be "device"
    user_type = user_info.get("user_type")
    if user_type != "device":
        logger.warning(
            "Agent request user_type is not device",
            extra={
                "path": request.url.path,
                "method": request.method,
                "user_type": user_type,
                "id": user_info.get("id"),
            },
        )
        raise _create_auth_error_response(
            request=request,
            message="This interface only allows device (Agent) access",
            message_key="error.auth.invalid_user_type",
            error_code="INVALID_USER_TYPE",
            details={"hint": "Please use token obtained from device login", "user_type": user_type},
        )

    # ✅ Gateway has already ensured id exists, directly build Agent information
    return {
        "id": user_info.get("id"),
        "username": user_info.get("username"),
        "user_type": user_info.get("user_type"),
        "permissions": user_info.get("permissions", []),
        "mg_id": user_info.get("mg_id"),
    }
=======
Host Service API 依赖注入

提供服务实例的依赖注入函数
"""

<<<<<<< HEAD
from typing import Optional
=======
import os
import sys
from typing import Optional, Dict, Any
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

from fastapi import Request, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.utils.token_extractor import get_token_extractor
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.host_discovery_service import HostDiscoveryService
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.utils.token_extractor import get_token_extractor
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.host_discovery_service import HostDiscoveryService

logger = get_logger(__name__)

# 全局服务实例缓存（使用 Optional 类型注解）
_browser_host_service_instance: Optional[BrowserHostService] = None
_browser_vnc_service_instance: Optional[BrowserVNCService] = None
_host_discovery_service_instance: Optional[HostDiscoveryService] = None
_admin_host_service_instance: Optional[Any] = None


def get_host_service() -> BrowserHostService:
    """获取浏览器插件主机服务实例（单例模式）

    Returns:
        BrowserHostService: 浏览器插件主机服务实例
    """
    global _browser_host_service_instance

    if _browser_host_service_instance is None:
        _browser_host_service_instance = BrowserHostService()

<<<<<<< HEAD
    return _host_service_instance
<<<<<<< HEAD
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
=======
    return _browser_host_service_instance
>>>>>>> 2994441 (feat(host-service): 重构主机与VNC服务为浏览器插件专用版本)


def get_vnc_service() -> BrowserVNCService:
    """获取浏览器插件 VNC 服务实例（单例模式）

    Returns:
        BrowserVNCService: 浏览器插件 VNC 服务实例
    """
    global _browser_vnc_service_instance

    if _browser_vnc_service_instance is None:
        _browser_vnc_service_instance = BrowserVNCService()

    return _browser_vnc_service_instance


def get_host_discovery_service() -> HostDiscoveryService:
    """获取主机发现服务实例（单例模式）

    从环境变量中读取硬件接口 URL 配置，注入到 HostDiscoveryService 中。

    Returns:
        HostDiscoveryService: 主机发现服务实例
    """
    global _host_discovery_service_instance

    if _host_discovery_service_instance is None:
        # 从环境变量读取硬件接口 URL
        hardware_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
        _host_discovery_service_instance = HostDiscoveryService(hardware_api_url)

    return _host_discovery_service_instance
<<<<<<< HEAD
>>>>>>> af8f7cc (feat(host-service): 重构主机发现与VNC连接管理功能)
=======


def get_admin_host_service() -> Any:
    """获取管理后台主机服务实例（单例模式）

    Returns:
        AdminHostService: 管理后台主机服务实例
    """
    global _admin_host_service_instance

    if _admin_host_service_instance is None:
        try:
            from app.services.admin_host_service import AdminHostService
        except ImportError:
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
            from app.services.admin_host_service import AdminHostService

        _admin_host_service_instance = AdminHostService()

    return _admin_host_service_instance


async def get_current_user(request: Request) -> Dict[str, Any]:
    """获取当前用户信息（从 token 中提取）

    从请求的 Authorization 头中提取并验证 JWT token，
    返回用户信息。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: 用户信息

    Raises:
        HTTPException: token 缺失、无效或验证失败时抛出 401
    """
    try:
        from shared.utils.token_extractor import get_token_extractor

        extractor = get_token_extractor()
        is_valid, user_info = await extractor.extract_and_verify(request)

        if not is_valid or not user_info:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少有效的认证令牌",
                    error_code="UNAUTHORIZED",
                ).model_dump(),
            )

        return user_info

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"获取当前用户失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="认证失败",
                error_code="AUTHENTICATION_FAILED",
            ).model_dump(),
        )


async def get_current_agent(request: Request) -> Dict[str, Any]:
    """获取当前 Agent 信息（从 token 中提取）

    从请求的 Authorization 头中提取并验证 JWT token，
    调用 auth-service 验证后返回 Agent 信息。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: Agent 信息，包含：
            - host_id: 主机ID（来自 token 的 user_id/sub 字段）
            - username: Agent 用户名
            - user_type: 用户类型（应为 "device"）
            - permissions: 权限列表
            - mg_id: 管理组ID（如果有）

    Raises:
        HTTPException: token 缺失、无效或验证失败时抛出 401

    Example:
        >>> @router.post("/hardware/report")
        >>> async def report_hardware(
        >>>     agent_info: Dict[str, Any] = Depends(get_current_agent)
        >>> ):
        >>>     host_id = agent_info["host_id"]
    """
    try:
        # 获取 Token 提取器
        extractor = get_token_extractor()

        # 提取并验证 token
        is_valid, user_info = await extractor.extract_and_verify(request)

        if not is_valid or not user_info:
            logger.warning(
                "Agent token 验证失败",
                extra={
                    "path": request.url.path,
                    "client": f"{request.client.host}:{request.client.port}" if request.client else "unknown",
                },
            )
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少有效的认证令牌",
                    error_code="UNAUTHORIZED",
                ).model_dump(),
            )

        # 提取 host_id（来自 user_id/sub 字段，这是设备登录时存储的 host_rec.id）
        host_id = user_info.get("user_id")

        if not host_id:
            logger.error(
                "Token 中缺少 host_id",
                extra={
                    "user_info": user_info,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="Token 格式错误：缺少 host_id",
                    error_code="INVALID_TOKEN_FORMAT",
                ).model_dump(),
            )

        # 构建 Agent 信息（转换字段名以符合业务语义）
        agent_info = {
            "host_id": int(host_id) if isinstance(host_id, str) and host_id.isdigit() else host_id,
            "username": user_info.get("username"),
            "user_type": user_info.get("user_type"),
            "permissions": user_info.get("permissions", []),
            "mg_id": user_info.get("mg_id"),
        }

        logger.info(
            "Agent 认证成功",
            extra={
                "host_id": agent_info["host_id"],
                "username": agent_info["username"],
                "user_type": agent_info["user_type"],
                "path": request.url.path,
            },
        )

        return agent_info

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"获取当前 Agent 失败: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="认证失败",
                error_code="AUTHENTICATION_FAILED",
            ).model_dump(),
        )
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
