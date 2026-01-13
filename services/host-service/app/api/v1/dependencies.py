"""
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
