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
            - user_id: 用户ID
            - username: 用户名
            - user_type: 用户类型（admin/device/user）
            - active: 是否激活

    Raises:
        HTTPException: 缺少用户信息时抛出 401
    """
    try:
        # ✅ 从 Gateway 传递的 header 中获取用户信息
        # Gateway 已经在认证中间件中验证了 token，并将用户信息存储在 X-User-Info header 中
        user_info_header = request.headers.get("X-User-Info")

        # 打印 X-User-Info header 信息（用于调试）
        if user_info_header:
            header_preview = user_info_header[:200] + "..." if len(user_info_header) > 200 else user_info_header
            logger.info(
                "接收 X-User-Info header",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": True,
                    "x_user_info_preview": header_preview,
                    "x_user_info_length": len(user_info_header),
                    "x_user_info_full": user_info_header,
                },
            )
        else:
            logger.warning(
                f"未接收到 X-User-Info header | path={request.url.path} | method={request.method}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": False,
                    "all_headers": dict(request.headers),
                },
            )

        if not user_info_header:
            # 如果没有 X-User-Info header，说明请求可能不是通过 Gateway 转发的
            # 或者 Gateway 认证中间件没有设置用户信息
            logger.warning(
                "缺少 X-User-Info header，请求可能未通过 Gateway 认证",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )

            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少用户认证信息",
                    message_key="error.auth.missing_user_info",
                    error_code="UNAUTHORIZED",
                    locale=locale,
                    details={
                        "hint": "请求必须通过 Gateway 转发，Gateway 会在认证后传递用户信息",
                    },
                ).model_dump(),
            )

        # 解析用户信息 JSON
        try:
            # 先验证 JSON 格式
            if not user_info_header or not user_info_header.strip():
                raise ValueError("X-User-Info header 为空")

            user_info = json.loads(user_info_header)

            # 验证 user_info 是字典类型
            if not isinstance(user_info, dict):
                raise ValueError(f"X-User-Info 解析后不是字典类型，而是: {type(user_info).__name__}")

            # 记录解析后的用户信息键（用于调试）
            user_info_keys = list(user_info.keys()) if isinstance(user_info, dict) else []
            logger.info(
                "解析 X-User-Info header 成功（原始内容已记录）",
                extra={
                    "user_info_keys": user_info_keys,
                    "user_info_type": type(user_info).__name__,
                    "raw_header": user_info_header,
                    "path": request.url.path,
                },
            )

            # 打印解析后的用户信息（用于调试）- 使用 .get() 避免 KeyError
            user_id = user_info.get("user_id")
            username = user_info.get("username")
            user_type = user_info.get("user_type")
            active = user_info.get("active")

            logger.info(
                (
                    f"解析 X-User-Info header 成功 | user_id={user_id} | "
                    f"username={username} | user_type={user_type} | active={active} | "
                    f"path={request.url.path}"
                ),
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "user_id": user_id,
                    "username": username,
                    "user_type": user_type,
                    "active": active,
                },
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            header_length = len(user_info_header) if user_info_header else 0
            header_preview = (
                user_info_header[:200] + "..." if user_info_header and len(user_info_header) > 200 else user_info_header
            )
            logger.opt(exception=e).error(
                (
                    "解析 X-User-Info header 失败 | path={} | error={} | error_type={} | "
                    "header_length={} | header_preview={}"
                ).format(
                    request.url.path,
                    str(e),
                    type(e).__name__,
                    header_length,
                    header_preview,
                ),
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "header_value_preview": header_preview,
                    "header_length": header_length,
                    "header_full": user_info_header,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="用户信息格式错误",
                    message_key="error.auth.invalid_user_info",
                    error_code="INVALID_USER_INFO",
                    locale=locale,
                ).model_dump(),
            )

        # 验证用户信息是否包含必要字段
        if not user_info.get("user_id"):
            logger.warning(
                "用户信息缺少 user_id 字段",
                extra={
                    "user_info_keys": str(list(user_info.keys())),
                    "path": request.url.path,
                },
            )
            # 即使缺少 user_id，也返回用户信息，让业务层处理
            # 因为某些场景下可能允许匿名访问

        user_id = user_info.get("user_id")
        username = user_info.get("username")
        user_type = user_info.get("user_type")
        active = user_info.get("active")

        logger.info(
            (
                f"从 Gateway 获取用户信息成功 | user_id={user_id} | "
                f"username={username} | user_type={user_type} | active={active}"
            ),
            extra={
                "user_id": user_id,
                "username": username,
                "user_type": user_type,
                "active": active,
            },
        )

        return user_info

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
                "x_user_info_header": x_user_info_header,
            },
        )

        # 获取语言偏好
        accept_language = request.headers.get("Accept-Language")
        locale = parse_accept_language(accept_language)

        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="获取用户信息失败",
                message_key="error.auth.get_user_failed",
                error_code="GET_USER_FAILED",
                locale=locale,
            ).model_dump(),
        )


async def get_current_agent(request: Request) -> Dict[str, Any]:
    """获取当前 Agent 信息（从 Gateway 传递的 header 中获取）

    ✅ 注意：认证已在 Gateway 中完成，这里只需要从 Gateway 传递的 header 中获取用户信息。
    不再需要验证 token，因为 Gateway 已经验证过了。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: Agent 信息，包含：
            - host_id: 主机ID（来自 user_id 字段）
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
        >>>     host_id = agent_info["host_id"]
    """
    try:
        # ✅ 从 Gateway 传递的 header 中获取用户信息
        # Gateway 已经在认证中间件中验证了 token，并将用户信息存储在 X-User-Info header 中
        user_info_header = request.headers.get("X-User-Info")

        # 打印 X-User-Info header 信息（用于调试）
        if user_info_header:
            client_info = f"{request.client.host}:{request.client.port}" if request.client else "unknown"
            header_preview = user_info_header[:200] + "..." if len(user_info_header) > 200 else user_info_header
            logger.info(
                (
                    f"Agent 接收 X-User-Info header | path={request.url.path} | "
                    f"method={request.method} | header_length={len(user_info_header)} | "
                    f"header_preview={header_preview} | client={client_info}"
                ),
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": True,
                    "x_user_info_preview": header_preview,
                    "x_user_info_length": len(user_info_header),
                    "x_user_info_full": user_info_header,
                    "client": client_info,
                },
            )
        else:
            client_info = f"{request.client.host}:{request.client.port}" if request.client else "unknown"
            logger.warning(
                f"Agent 未接收到 X-User-Info header | path={request.url.path} | client={client_info}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "has_x_user_info": False,
                    "client": client_info,
                },
            )

        if not user_info_header:
            logger.warning(
                "Agent 请求缺少 X-User-Info header，请求可能未通过 Gateway 认证",
                extra={
                    "path": request.url.path,
                    "client": f"{request.client.host}:{request.client.port}" if request.client else "unknown",
                },
            )
            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少用户认证信息",
                    message_key="error.auth.missing_user_info",
                    error_code="UNAUTHORIZED",
                    locale=locale,
                    details={
                        "hint": "请求必须通过 Gateway 转发，Gateway 会在认证后传递用户信息",
                    },
                ).model_dump(),
            )

        # 解析用户信息 JSON
        try:
            user_info = json.loads(user_info_header)

            # 打印解析后的 Agent 用户信息（用于调试）
            user_id = user_info.get("user_id")
            username = user_info.get("username")
            user_type = user_info.get("user_type")

            logger.info(
                (
                    f"解析 Agent X-User-Info header 成功 | user_id={user_id} | "
                    f"username={username} | user_type={user_type} | path={request.url.path}"
                ),
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "user_info": user_info,
                    "user_id": user_id,
                    "username": username,
                    "user_type": user_type,
                },
            )
        except json.JSONDecodeError as e:
            logger.error(
                "解析 Agent X-User-Info header 失败",
                extra={
                    "error": str(e),
                    "header_value_preview": user_info_header[:100] if len(user_info_header) > 100 else user_info_header,
                },
            )

            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="用户信息格式错误",
                    message_key="error.auth.invalid_user_info",
                    error_code="INVALID_USER_INFO",
                    locale=locale,
                ).model_dump(),
            )

        # 提取 host_id（来自 user_id 字段，这是设备登录时存储的 host_rec.id）
        host_id = user_info.get("user_id")

        if not host_id:
            logger.error(
                "用户信息中缺少 user_id (host_id)",
                extra={
                    "user_info": user_info,
                    "path": request.url.path,
                },
            )
            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="用户信息格式错误：缺少 user_id",
                    message_key="error.auth.invalid_user_info",
                    error_code="INVALID_USER_INFO",
                    locale=locale,
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

        logger.debug(
            "从 Gateway 获取 Agent 信息成功",
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
        # 获取语言偏好
        accept_language = request.headers.get("Accept-Language")
        locale = parse_accept_language(accept_language)

        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code=HTTP_401_UNAUTHORIZED,
                message="认证失败",
                message_key="error.auth.login_failed",
                error_code="AUTHENTICATION_FAILED",
                locale=locale,
            ).model_dump(),
        )
