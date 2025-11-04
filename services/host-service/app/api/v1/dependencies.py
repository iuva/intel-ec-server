"""
Host Service API 依赖注入

提供服务实例的依赖注入函数
"""

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

    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.utils.token_extractor import get_token_extractor
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.browser_host_service import BrowserHostService
    from app.services.browser_vnc_service import BrowserVNCService
    from app.services.host_discovery_service import HostDiscoveryService

    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
    from shared.utils.token_extractor import get_token_extractor

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
            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少有效的认证令牌",
                    message_key="error.auth.missing_token",
                    error_code="UNAUTHORIZED",
                    locale=locale,
                ).model_dump(),
            )

        return user_info

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"获取当前用户失败: {str(e)}", exc_info=True)

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
            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="缺少有效的认证令牌",
                    message_key="error.auth.missing_token",
                    error_code="UNAUTHORIZED",
                    locale=locale,
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
            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    code=HTTP_401_UNAUTHORIZED,
                    message="Token 格式错误：缺少 host_id",
                    message_key="error.auth.invalid_token_format",
                    error_code="INVALID_TOKEN_FORMAT",
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
