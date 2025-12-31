"""
Host Service API 依赖注入

提供服务实例的依赖注入函数
"""

import json
import os
import sys
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED

# 使用 try-except 方式处理路径导入
try:
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.host_discovery_service import HostDiscoveryService
    from app.services.file_manage_service import FileManageService
    from app.services.admin_appr_host_service import AdminApprHostService
    from app.services.admin_ota_service import AdminOtaService
    from app.services.admin_host_service import AdminHostService

    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.host_discovery_service import HostDiscoveryService
    from app.services.file_manage_service import FileManageService
    from app.services.admin_appr_host_service import AdminApprHostService
    from app.services.admin_host_service import AdminHostService
    from app.services.admin_ota_service import AdminOtaService

    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse

logger = get_logger(__name__)


# ==================== 辅助函数 ====================

def _get_locale_from_request(request: Request) -> str:
    """从请求中获取语言偏好

    Args:
        request: FastAPI 请求对象

    Returns:
        语言代码（如 "zh_CN", "en_US"）
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
    """创建认证错误响应

    Args:
        request: FastAPI 请求对象
        message: 错误消息
        message_key: 错误消息键（用于多语言）
        error_code: 错误代码
        details: 错误详情

    Returns:
        HTTPException: 认证错误异常
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
    """解析 X-User-Info header

    Args:
        user_info_header: X-User-Info header 值

    Returns:
        解析后的用户信息字典

    Raises:
        ValueError: 解析失败时抛出
    """
    if not user_info_header or not user_info_header.strip():
        raise ValueError("X-User-Info header 为空")

    user_info = json.loads(user_info_header)

    if not isinstance(user_info, dict):
        raise ValueError(f"X-User-Info 解析后不是字典类型，而是: {type(user_info).__name__}")

    return user_info


# ==================== 全局服务实例缓存 ====================

# 全局服务实例缓存（使用 Optional 类型注解）
_browser_host_service_instance: Optional[BrowserHostService] = None
_browser_vnc_service_instance: Optional[BrowserVNCService] = None
_host_discovery_service_instance: Optional[HostDiscoveryService] = None
_admin_host_service_instance: Optional[Any] = None
_admin_appr_host_service_instance: Optional[Any] = None
_admin_ota_service_instance: Optional["AdminOtaService"] = None
_file_manage_service_instance: Optional["FileManageService"] = None


def get_host_service() -> BrowserHostService:
    """获取浏览器插件主机服务实例（单例模式）

    Returns:
        BrowserHostService: 浏览器插件主机服务实例
    """
    global _browser_host_service_instance

    if _browser_host_service_instance is None:
        _browser_host_service_instance = BrowserHostService()

    return _browser_host_service_instance


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


def get_admin_host_service() -> Any:
    """获取管理后台主机服务实例（单例模式）

    Returns:
        AdminHostService: 管理后台主机服务实例
    """
    global _admin_host_service_instance

    if _admin_host_service_instance is None:
        _admin_host_service_instance = AdminHostService()

    return _admin_host_service_instance


def get_admin_appr_host_service() -> Any:
    """获取管理后台待审批主机服务实例（单例模式）

    Returns:
        AdminApprHostService: 管理后台待审批主机服务实例
    """
    global _admin_appr_host_service_instance

    if _admin_appr_host_service_instance is None:
        _admin_appr_host_service_instance = AdminApprHostService()

    return _admin_appr_host_service_instance


def get_admin_ota_service() -> "AdminOtaService":
    """获取管理后台 OTA 服务实例（单例模式）

    Returns:
        AdminOtaService: 管理后台 OTA 服务实例
    """
    global _admin_ota_service_instance

    if _admin_ota_service_instance is None:
        _admin_ota_service_instance = AdminOtaService()

    return _admin_ota_service_instance


def get_file_manage_service() -> "FileManageService":
    """获取文件管理服务实例（单例模式）

    Returns:
        FileManageService: 文件管理服务实例
    """
    global _file_manage_service_instance

    if _file_manage_service_instance is None:
        _file_manage_service_instance = FileManageService()

    return _file_manage_service_instance


async def get_current_user(request: Request) -> Dict[str, Any]:
    """获取当前用户信息（从 Gateway 传递的 X-User-Info header 获取）

    ✅ 架构说明：
    - Gateway 已经验证了 token 并提取了 id，确保 id 存在后才转发请求
    - Gateway 已经删除了客户端传入的 X-User-Info header，并添加了自己的 header
    - 后端服务只需要从 X-User-Info header 读取用户信息即可

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: 用户信息，包含 id、username、user_type、active 等字段

    Raises:
        HTTPException: 缺少 X-User-Info header 或解析失败时抛出 401
    """
    # ✅ 从 Gateway 传递的 X-User-Info header 中获取用户信息
    user_info_header = request.headers.get("X-User-Info")

    if not user_info_header:
        logger.warning(
            "缺少 X-User-Info header",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise _create_auth_error_response(
            request=request,
            message="缺少用户认证信息",
            message_key="error.auth.missing_user_info",
            error_code="UNAUTHORIZED",
            details={"hint": "请求必须通过 Gateway 转发，Gateway 会在认证后传递 X-User-Info header"},
        )

    # 解析用户信息 JSON
    try:
        user_info = _parse_user_info_header(user_info_header)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            "解析 X-User-Info header 失败",
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
            message="用户信息格式错误",
            message_key="error.auth.invalid_user_info",
            error_code="INVALID_USER_INFO",
        )

    # ✅ Gateway 已经确保 id 存在，直接返回用户信息
    return {
        "id": user_info.get("id"),
        "username": user_info.get("username"),
        "user_type": user_info.get("user_type"),
        "active": user_info.get("active"),
    }


async def get_current_agent(request: Request) -> Dict[str, Any]:
    """获取当前 Agent 信息（从 Gateway 传递的 X-User-Info header 获取）

    ✅ 架构说明：
    - Gateway 已经验证了 token 并提取了 id，确保 id 存在后才转发请求
    - Gateway 已经删除了客户端传入的 X-User-Info header，并添加了自己的 header
    - 后端服务只需要从 X-User-Info header 读取用户信息，并验证 user_type 必须是 "device"

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: Agent 信息，包含 id、username、user_type、permissions、mg_id 等字段

    Raises:
        HTTPException: 缺少 X-User-Info header、解析失败或 user_type 不是 "device" 时抛出 401

    Example:
        >>> @router.post("/hardware/report")
        >>> async def report_hardware(
        >>>     agent_info: Dict[str, Any] = Depends(get_current_agent)
        >>> ):
        >>>     host_id = agent_info["id"]
    """
    # ✅ 从 Gateway 传递的 X-User-Info header 中获取用户信息
    user_info_header = request.headers.get("X-User-Info")

    if not user_info_header:
        logger.warning(
            "Agent 请求缺少 X-User-Info header",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise _create_auth_error_response(
            request=request,
            message="缺少用户认证信息",
            message_key="error.auth.missing_user_info",
            error_code="UNAUTHORIZED",
            details={
                "hint": "请求必须通过 Gateway 转发，Gateway 会在认证后传递 X-User-Info header"
            },
        )

    # 解析用户信息 JSON
    try:
        user_info = _parse_user_info_header(user_info_header)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            "解析 X-User-Info header 失败",
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
            message="用户信息格式错误",
            message_key="error.auth.invalid_user_info",
            error_code="INVALID_USER_INFO",
        )

    # ✅ 验证 user_type 必须是 "device"
    user_type = user_info.get("user_type")
    if user_type != "device":
        logger.warning(
            "Agent 请求的 user_type 不是 device",
            extra={
                "path": request.url.path,
                "method": request.method,
                "user_type": user_type,
                "id": user_info.get("id"),
            },
        )
        raise _create_auth_error_response(
            request=request,
            message="此接口仅允许设备（Agent）访问",
            message_key="error.auth.invalid_user_type",
            error_code="INVALID_USER_TYPE",
            details={"hint": "请使用设备登录获取的 token", "user_type": user_type},
        )

    # ✅ Gateway 已经确保 id 存在，直接构建 Agent 信息
    return {
        "id": user_info.get("id"),
        "username": user_info.get("username"),
        "user_type": user_info.get("user_type"),
        "permissions": user_info.get("permissions", []),
        "mg_id": user_info.get("mg_id"),
    }
