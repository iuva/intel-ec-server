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

# Gateway 服务 IP 地址（用于验证请求来源）
# Docker 环境：172.20.0.100
# 本地开发环境：127.0.0.1 或 localhost
GATEWAY_IP_ADDRESSES = {
    "172.20.0.100",  # Docker 网络中的 Gateway IP
    "127.0.0.1",  # 本地开发环境
    "localhost",  # 本地开发环境
}
# 允许从环境变量配置额外的 Gateway IP（用于特殊部署场景）
GATEWAY_IP_ENV = os.getenv("GATEWAY_IP_ADDRESSES", "")
if GATEWAY_IP_ENV:
    GATEWAY_IP_ADDRESSES.update(ip.strip() for ip in GATEWAY_IP_ENV.split(",") if ip.strip())


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


def _validate_gateway_source(request: Request) -> bool:
    """验证请求是否来自 Gateway

    Args:
        request: FastAPI 请求对象

    Returns:
        是否来自 Gateway
    """
    client_host = request.client.host if request.client else None
    if not client_host:
        return False

    if client_host in GATEWAY_IP_ADDRESSES:
        return True

    # 检查代理头
    forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()

    return forwarded_for in GATEWAY_IP_ADDRESSES or real_ip in GATEWAY_IP_ADDRESSES


def _get_auth_service_url() -> str:
    """获取 auth-service URL（兼容 Docker 和本地开发环境）

    Returns:
        auth-service URL
    """
    auth_service_url = os.getenv("AUTH_SERVICE_URL")
    if auth_service_url:
        return auth_service_url

    # 根据运行环境自动选择默认值
    is_docker_env = os.getenv("DOCKER_ENV") == "true" or os.path.exists("/.dockerenv")
    auth_service_host = (
        os.getenv("AUTH_SERVICE_IP") or ("auth-service" if is_docker_env else "127.0.0.1")
    )
    auth_service_port = int(os.getenv("AUTH_SERVICE_PORT", "8001"))
    return f"http://{auth_service_host}:{auth_service_port}"


def _build_agent_info(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """构建 Agent 信息

    Args:
        user_info: 用户信息字典（必须包含 id 字段）

    Returns:
        Agent 信息字典，包含：
            - id: 主机ID
            - username: Agent 用户名
            - user_type: 用户类型
            - permissions: 权限列表
            - mg_id: 管理组ID

    Raises:
        KeyError: 如果 user_info 中缺少 id 字段
        ValueError: 如果 id 字段为空或无效
    """
    # ✅ 统一使用 id 字段，没有则抛出异常
    if "id" not in user_info:
        raise KeyError("id")

    host_id = user_info["id"]

    if not host_id:
        raise ValueError("id 字段不能为空")

    # 转换 id 为整数（如果是数字字符串）
    try:
        if isinstance(host_id, str) and host_id.isdigit():
            host_id = int(host_id)
    except (ValueError, TypeError):
        # 如果转换失败，保持原值
        ***REMOVED***

    return {
        "id": host_id,
        "username": user_info.get("username"),
        "user_type": user_info.get("user_type"),
        "permissions": user_info.get("permissions", []),
        "mg_id": user_info.get("mg_id"),
    }


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
    """获取当前用户信息（从 Gateway 传递的 header 中获取）

    ✅ 注意：认证已在 Gateway 中完成，这里只需要从 Gateway 传递的 header 中获取用户信息。
    不再需要验证 token，因为 Gateway 已经验证过了。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: 用户信息，包含：
            - id: 用户ID
            - username: 用户名
            - user_type: 用户类型（admin/device/user）
            - active: 是否激活

    Raises:
        HTTPException: 缺少用户信息时抛出 401
    """
    try:
        # ✅ 安全验证：检查请求来源 IP，确保请求来自 Gateway
        if not _validate_gateway_source(request):
            client_host = request.client.host if request.client else None
            forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            real_ip = request.headers.get("X-Real-IP", "").strip()

            logger.warning(
                (
                    f"拒绝非 Gateway 来源的请求 | client_host={client_host} | "
                    f"forwarded_for={forwarded_for} | real_ip={real_ip} | path={request.url.path}"
                ),
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": client_host,
                    "forwarded_for": forwarded_for,
                    "real_ip": real_ip,
                    "allowed_gateway_ips": list(GATEWAY_IP_ADDRESSES),
                },
            )

            raise _create_auth_error_response(
                request=request,
                message="请求必须通过 Gateway 转发",
                message_key="error.auth.invalid_request_source",
                error_code="INVALID_REQUEST_SOURCE",
                details={"hint": "请求必须通过 Gateway 转发，不允许直接访问服务"},
            )

        # ✅ 从 Gateway 传递的 header 中获取用户信息
        # Gateway 已经在认证中间件中验证了 token，并将用户信息存储在 X-User-Info header 中
        user_info_header = request.headers.get("X-User-Info")

        # 记录 X-User-Info header 信息（不记录完整内容，避免敏感信息泄露）
        if user_info_header:
            header_preview = user_info_header[:100] + "..." if len(user_info_header) > 100 else user_info_header
            logger.debug(
                "接收 X-User-Info header",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": True,
                    "x_user_info_preview": header_preview,
                    "x_user_info_length": len(user_info_header),
                },
            )
        else:
            logger.warning(
                f"未接收到 X-User-Info header | path={request.url.path} | method={request.method}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": False,
                },
            )

        if not user_info_header:
            logger.warning(
                "缺少 X-User-Info header，请求可能未通过 Gateway 认证",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )

            raise _create_auth_error_response(
                request=request,
                message="缺少用户认证信息",
                message_key="error.auth.missing_user_info",
                error_code="UNAUTHORIZED",
                details={"hint": "请求必须通过 Gateway 转发，Gateway 会在认证后传递用户信息"},
            )

        # 解析用户信息 JSON
        try:
            user_info = _parse_user_info_header(user_info_header)

            # 记录解析后的用户信息键（不记录完整内容，避免敏感信息泄露）
            logger.debug(
                "解析 X-User-Info header 成功",
                extra={
                    "user_info_keys": list(user_info.keys()),
                    "user_info_type": type(user_info).__name__,
                    "path": request.url.path,
                },
            )

            # 打印解析后的用户信息（用于调试）
            user_id = user_info.get("id")
            username = user_info.get("username")
            user_type = user_info.get("user_type")
            active = user_info.get("active")

            logger.debug(
                (
                    f"解析 X-User-Info header 成功 | id={user_id} | "
                    f"username={username} | user_type={user_type} | active={active} | "
                    f"path={request.url.path}"
                ),
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "id": user_id,
                    "username": username,
                    "user_type": user_type,
                    "active": active,
                },
            )
        except (json.JSONDecodeError, ValueError) as e:
            header_length = len(user_info_header) if user_info_header else 0
            header_preview = (
                user_info_header[:100] + "..." if user_info_header and len(user_info_header) > 100 else user_info_header
            )
            logger.opt(exception=e).error(
                (
                    f"解析 X-User-Info header 失败 | path={request.url.path} | error={str(e)} | "
                    f"error_type={type(e).__name__} | header_length={header_length} | header_preview={header_preview}"
                ),
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "header_value_preview": header_preview,
                    "header_length": header_length,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            raise _create_auth_error_response(
                request=request,
                message="用户信息格式错误",
                message_key="error.auth.invalid_user_info",
                error_code="INVALID_USER_INFO",
            )

        # ✅ 统一使用 id 字段，没有则返回错误
        user_id = user_info.get("id")
        if not user_id:
            logger.warning(
                "用户信息缺少 id 字段",
                extra={
                    "user_info_keys": str(list(user_info.keys())),
                    "path": request.url.path,
                },
            )
            # 即使缺少 id，也返回用户信息，让业务层处理
            # 因为某些场景下可能允许匿名访问
        username = user_info.get("username")
        user_type = user_info.get("user_type")
        active = user_info.get("active")

        # 构建统一的用户信息（使用 id 字段）
        result = {
            "id": user_id,
            "username": username,
            "user_type": user_type,
            "active": active,
        }

        logger.info(
            (
                f"从 Gateway 获取用户信息成功 | id={user_id} | "
                f"username={username} | user_type={user_type} | active={active}"
            ),
            extra={
                "id": user_id,
                "username": username,
                "user_type": user_type,
                "active": active,
            },
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        x_user_info_header = request.headers.get("X-User-Info")
        header_info = "有 X-User-Info header" if x_user_info_header else "无 X-User-Info header"

        logger.opt(exception=e).error(
            (
                f"获取当前用户失败 | path={request.url.path} | method={request.method} | "
                f"error_type={type(e).__name__} | error={str(e)} | {header_info}"
            ),
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "has_x_user_info": x_user_info_header is not None,
            },
        )

        raise _create_auth_error_response(
            request=request,
            message="获取用户信息失败",
            message_key="error.auth.get_user_failed",
            error_code="GET_USER_FAILED",
        )


async def get_current_agent(request: Request) -> Dict[str, Any]:
    """获取当前 Agent 信息

    支持两种认证方式：
    1. **通过 Gateway**（推荐）：从 Gateway 传递的 X-User-Info header 中获取用户信息
    2. **直接访问**（兼容）：从 Authorization header 验证 JWT token 并提取用户信息

    ✅ 注意：
    - 优先使用 Gateway 传递的 X-User-Info header（性能更好，无需重复验证）
    - 如果没有 X-User-Info header，则从 Authorization header 验证 JWT token
    - 兼容 Agent 直接访问 host-service 的场景

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: Agent 信息，包含：
            - id: 主机ID
            - username: Agent 用户名
            - user_type: 用户类型（应为 "device"）
            - permissions: 权限列表（如果有）
            - mg_id: 管理组ID（如果有）

    Raises:
        HTTPException: 缺少用户信息时抛出 401

    Example:
        >>> @router.post("/hardware/report")
        >>> async def report_hardware(
        >>>     agent_info: Dict[str, Any] = Depends(get_current_agent)
        >>> ):
        >>>     host_id = agent_info["id"]
    """
    try:
        # ✅ 方式1：优先从 Gateway 传递的 X-User-Info header 中获取用户信息
        # Gateway 已经在认证中间件中验证了 token，并将用户信息存储在 X-User-Info header 中
        user_info_header = request.headers.get("X-User-Info")

        # 如果存在 X-User-Info header，使用 Gateway 传递的信息（优先方式）
        if user_info_header:
            client_info = f"{request.client.host}:{request.client.port}" if request.client else "unknown"
            header_preview = user_info_header[:100] + "..." if len(user_info_header) > 100 else user_info_header
            logger.debug(
                (
                    f"Agent 接收 X-User-Info header（通过 Gateway） | path={request.url.path} | method={request.method} | "
                    f"header_length={len(user_info_header)} | header_preview={header_preview} | client={client_info}"
                ),
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": True,
                    "x_user_info_preview": header_preview,
                    "x_user_info_length": len(user_info_header),
                    "auth_method": "gateway_header",
                    "client": client_info,
                },
            )

            # 解析用户信息 JSON
            try:
                user_info = _parse_user_info_header(user_info_header)

                # ✅ 统一使用 id 字段，没有则返回错误
                if "id" not in user_info:
                    logger.error(
                        "X-User-Info header 中缺少 id 字段",
                        extra={
                            "user_info": user_info,
                            "user_info_keys": list(user_info.keys()),
                            "path": request.url.path,
                        },
                    )

                    raise _create_auth_error_response(
                        request=request,
                        message="用户信息格式错误：缺少 id",
                        message_key="error.auth.invalid_user_info",
                        error_code="INVALID_USER_INFO",
                    )

                host_id = user_info["id"]
                if not host_id:
                    logger.error(
                        "X-User-Info header 中 id 字段为空",
                        extra={
                            "user_info": user_info,
                            "user_info_keys": list(user_info.keys()),
                            "path": request.url.path,
                        },
                    )

                    raise _create_auth_error_response(
                        request=request,
                        message="用户信息格式错误：id 字段为空",
                        message_key="error.auth.invalid_user_info",
                        error_code="INVALID_USER_INFO",
                    )

                # 构建 Agent 信息（转换字段名以符合业务语义）
                try:
                    agent_info = _build_agent_info(user_info)
                except (KeyError, ValueError) as e:
                    logger.error(
                        f"构建 Agent 信息失败: {str(e)}",
                        extra={
                            "user_info": user_info,
                            "user_info_keys": list(user_info.keys()),
                            "path": request.url.path,
                            "error": str(e),
                        },
                    )

                    raise _create_auth_error_response(
                        request=request,
                        message=f"用户信息格式错误：{str(e)}",
                        message_key="error.auth.invalid_user_info",
                        error_code="INVALID_USER_INFO",
                    )

                logger.debug(
                    "从 Gateway 获取 Agent 信息成功",
                    extra={
                        "id": agent_info["id"],
                        "username": agent_info["username"],
                        "user_type": agent_info["user_type"],
                        "path": request.url.path,
                        "auth_method": "gateway_header",
                    },
                )

                return agent_info

            except (json.JSONDecodeError, ValueError) as e:
                header_preview = (
                    user_info_header[:100] + "..."
                    if user_info_header and len(user_info_header) > 100
                    else user_info_header
                )
                logger.error(
                    f"解析 Agent X-User-Info header 失败 | error={str(e)} | header_preview={header_preview}",
                    extra={
                        "error": str(e),
                        "header_value_preview": header_preview,
                    },
                )

                raise _create_auth_error_response(
                    request=request,
                    message="用户信息格式错误",
                    message_key="error.auth.invalid_user_info",
                    error_code="INVALID_USER_INFO",
                )

        # ✅ 方式2：如果没有 X-User-Info header，则从 Authorization header 验证 JWT token（兼容直接访问）
        logger.info(
            "Agent 请求未包含 X-User-Info header，尝试从 JWT token 验证",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": f"{request.client.host}:{request.client.port}" if request.client else "unknown",
            },
        )

        # 从 Authorization header 提取 token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(
                "Agent 请求缺少有效的 Authorization header",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_authorization": bool(auth_header),
                    "auth_header_preview": (
                        auth_header[:50] + "..." if auth_header and len(auth_header) > 50 else auth_header
                    ),
                },
            )

            raise _create_auth_error_response(
                request=request,
                message="缺少认证令牌",
                message_key="error.auth.missing_token",
                error_code="UNAUTHORIZED",
                details={"hint": "请在请求头中添加 Authorization: Bearer <token>，或通过 Gateway 转发请求"},
            )

        # 提取 token
        token = auth_header[7:]  # 移除 "Bearer " 前缀

        # 使用 TokenExtractor 验证 token
        try:
            from shared.utils.token_extractor import TokenExtractor

            auth_service_url = _get_auth_service_url()

            logger.debug(
                "初始化 TokenExtractor 验证 Agent token",
                extra={
                    "auth_service_url": auth_service_url,
                    "path": request.url.path,
                },
            )

            token_extractor = TokenExtractor(auth_service_url=auth_service_url)
            is_valid, user_info = await token_extractor.verify_token(token)

            if not is_valid or not user_info:
                logger.warning(
                    "Agent JWT token 验证失败",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token[:20] + "..." if len(token) > 20 else token,
                    },
                )

                raise _create_auth_error_response(
                    request=request,
                    message="无效或过期的认证令牌",
                    message_key="error.auth.token_invalid_or_expired",
                    error_code="UNAUTHORIZED",
                    details={"hint": "Token 可能已过期或无效，请重新登录获取新令牌"},
                )

            # 验证 user_type 必须是 "device"
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

            # ✅ 统一使用 id 字段，没有则返回错误
            if "id" not in user_info:
                logger.error(
                    "Token 验证成功但缺少 id 字段",
                    extra={
                        "user_info": user_info,
                        "user_info_keys": list(user_info.keys()),
                        "path": request.url.path,
                    },
                )

                raise _create_auth_error_response(
                    request=request,
                    message="Token 中缺少 id",
                    message_key="error.auth.missing_id",
                    error_code="INVALID_USER_INFO",
                )

            host_id = user_info["id"]
            if not host_id:
                logger.error(
                    "Token 验证成功但 id 字段为空",
                    extra={
                        "user_info": user_info,
                        "user_info_keys": list(user_info.keys()),
                        "path": request.url.path,
                    },
                )

                raise _create_auth_error_response(
                    request=request,
                    message="Token 中 id 字段为空",
                    message_key="error.auth.missing_id",
                    error_code="INVALID_USER_INFO",
                )

            # 构建 Agent 信息
            try:
                agent_info = _build_agent_info(user_info)
            except (KeyError, ValueError) as e:
                logger.error(
                    f"构建 Agent 信息失败: {str(e)}",
                    extra={
                        "user_info": user_info,
                        "user_info_keys": list(user_info.keys()),
                        "path": request.url.path,
                        "error": str(e),
                    },
                )

                raise _create_auth_error_response(
                    request=request,
                    message=f"用户信息格式错误：{str(e)}",
                    message_key="error.auth.invalid_user_info",
                    error_code="INVALID_USER_INFO",
                )

            logger.info(
                "从 JWT token 获取 Agent 信息成功（直接访问）",
                extra={
                    "id": agent_info["id"],
                    "username": agent_info["username"],
                    "user_type": agent_info["user_type"],
                    "path": request.url.path,
                    "auth_method": "jwt_token",
                },
            )

            return agent_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"验证 Agent JWT token 时发生异常: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

            raise _create_auth_error_response(
                request=request,
                message="认证服务暂时不可用",
                message_key="error.auth.service_unavailable",
                error_code="AUTHENTICATION_FAILED",
                details={"hint": "无法连接到认证服务，请稍后重试"},
            )

    except HTTPException:
        raise

    except KeyError as e:
        # 捕获 KeyError，提供更详细的错误信息
        error_key = str(e)
        logger.error(
            f"获取当前 Agent 失败：缺少必需的字段 '{error_key}'",
            extra={
                "error_type": "KeyError",
                "missing_key": error_key,
                "path": request.url.path,
                "method": request.method,
                "has_x_user_info": bool(request.headers.get("X-User-Info")),
                "has_authorization": bool(request.headers.get("Authorization")),
            },
            exc_info=True,
        )

        raise _create_auth_error_response(
            request=request,
            message=f"用户信息格式错误：缺少必需的字段 '{error_key}'",
            message_key="error.auth.invalid_user_info",
            error_code="INVALID_USER_INFO",
            details={
                "missing_key": error_key,
                "hint": "请检查 Gateway 传递的 X-User-Info header 或 Token 中的用户信息是否完整",
            },
        )

    except ValueError as e:
        # 捕获 ValueError，提供更详细的错误信息
        logger.error(
            f"获取当前 Agent 失败：字段值无效 - {str(e)}",
            extra={
                "error_type": "ValueError",
                "error_message": str(e),
                "path": request.url.path,
                "method": request.method,
                "has_x_user_info": bool(request.headers.get("X-User-Info")),
                "has_authorization": bool(request.headers.get("Authorization")),
            },
            exc_info=True,
        )

        raise _create_auth_error_response(
            request=request,
            message=f"用户信息格式错误：{str(e)}",
            message_key="error.auth.invalid_user_info",
            error_code="INVALID_USER_INFO",
            details={
                "error": str(e),
                "hint": "请检查 Gateway 传递的 X-User-Info header 或 Token 中的用户信息是否有效",
            },
        )

    except Exception as e:
        logger.error(
            f"获取当前 Agent 失败: {str(e)}",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "path": request.url.path,
                "method": request.method,
                "has_x_user_info": bool(request.headers.get("X-User-Info")),
                "has_authorization": bool(request.headers.get("Authorization")),
            },
            exc_info=True,
        )

        raise _create_auth_error_response(
            request=request,
            message="认证失败",
            message_key="error.auth.login_failed",
            error_code="AUTHENTICATION_FAILED",
            details={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
