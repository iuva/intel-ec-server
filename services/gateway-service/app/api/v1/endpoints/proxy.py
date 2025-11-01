"""
Proxy forwarding endpoints

Provides generic request proxy functionality, forwarding requests to backend microservices
"""

import json
import os
import sys
from typing import Any, Dict, Optional, Union

# Use try-except to handle path imports
try:
    from fastapi import APIRouter, Depends, Path, Request, Response, WebSocket
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

    from app.services.proxy_service import (
        ProxyService,
        get_proxy_service,
        get_proxy_service_ws,
    )
    from shared.common.exceptions import (
        BusinessError,
        ServiceNotFoundError,
        ValidationError,
    )
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
    from shared.common.websocket_auth import verify_token_string
except ImportError:
    # If import fails, add project root directory to Python path
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    )
    from fastapi import APIRouter, Depends, Path, Request, Response, WebSocket
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

    from app.services.proxy_service import (
        ProxyService,
        get_proxy_service,
        get_proxy_service_ws,
    )
    from shared.common.exceptions import (
        BusinessError,
        ServiceNotFoundError,
        ValidationError,
    )
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
    from shared.common.websocket_auth import verify_token_string


logger = get_logger(__name__)

router = APIRouter()
HOP_BY_HOP_RESPONSE_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "date",
    "server",
}


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


def _get_locale_from_websocket(websocket: WebSocket) -> str:
    """Get language preference from WebSocket

    Args:
        websocket: WebSocket connection object

    Returns:
        Language code (e.g., "zh_CN", "en_US")
    """
    accept_language = websocket.headers.get("Accept-Language")
    return parse_accept_language(accept_language)


def _create_error_response(
    request: Request,
    code: int,
    message: str,
    error_code: str,
    message_key: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Create unified error response

    Args:
        request: FastAPI request object
        code: HTTP status code
        message: Error message
        error_code: Error code
        message_key: Translation key (optional)
        details: Error details (optional)

    Returns:
        JSON response
    """
    locale = _get_locale_from_request(request)
    error_response = ErrorResponse(
        code=code,
        message=message,
        message_key=message_key,
        error_code=error_code,
        locale=locale,
        details=details,
    )
    return JSONResponse(status_code=code, content=error_response.model_dump())


async def _send_websocket_error(
    websocket: WebSocket,
    code: int,
    message: str,
    error_code: str,
    close_code: int = 1008,
    close_reason: str = "",
) -> None:
    """Send WebSocket error message and close connection

    Args:
        websocket: WebSocket connection object
        code: Error code
        message: Error message
        error_code: Error type identifier
        close_code: WebSocket close code
        close_reason: Close reason
    """
    locale = _get_locale_from_websocket(websocket)
    await websocket.send_json(
        {
            "code": code,
            "message": message,
            "error_code": error_code,
            "locale": locale,
        }
    )
    await websocket.close(code=close_code, reason=close_reason or message)


@router.websocket("/ws/{hostname}/{apiurl:path}")
async def websocket_proxy(
    websocket: WebSocket = ...,
    hostname: str = Path(
        ..., description="Hostname or service identifier (e.g., host-service)"
    ),
    apiurl: str = Path(
        ..., description="WebSocket API path (full path forwarded to backend service)"
    ),
    proxy_service: ProxyService = Depends(get_proxy_service_ws),
) -> None:
    """WebSocket forwarding endpoint

    New format: /ws/{hostname}/{apiurl}
    Example: /ws/host-service/agent/agent-123

    Forwards client WebSocket connection to backend microservice
    Requires valid authentication token

    Args:
        websocket: Client WebSocket connection
        hostname: Service hostname (e.g., host-service, auth-service)
        apiurl: API path (e.g., agent/agent-123)
        proxy_service: Proxy service instance
    """
    try:
        # ✅ Step 1: Extract and verify token (before accepting connection)
        token = None

        # Try to extract token from query parameters
        token = websocket.query_params.get("token")

        # If not found, try to extract from Authorization header
        if not token:
            auth_header = websocket.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        # If still not found, try reading common custom headers
        if not token:
            token = websocket.headers.get("X-Token") or websocket.headers.get("token")

        if not token:
            logger.warning(
                "WebSocket connection missing authentication token",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "client": websocket.client.host if websocket.client else "unknown",
                },
            )
            # ✅ Must accept before sending error message
            await websocket.accept()

            locale = _get_locale_from_websocket(websocket)
            await _send_websocket_error(
                websocket=websocket,
                code=401,
                message=t("error.auth.missing_token", locale=locale),
                error_code="WEBSOCKET_MISSING_TOKEN",
                close_reason="Missing authentication token",
            )
            return

        # ✅ Verify token validity (gateway verifies here)
        try:
            user_id = await verify_token_string(token)
            if not user_id:
                logger.warning(
                    "WebSocket connection token verification failed",
                    extra={
                        "hostname": hostname,
                        "apiurl": apiurl,
                        "client": websocket.client.host
                        if websocket.client
                        else "unknown",
                        "token_preview": token[:20] + "..."
                        if len(token) > 20
                        else token,
                    },
                )
                # ✅ Must accept before sending error message
                await websocket.accept()

                locale = _get_locale_from_websocket(websocket)
                await _send_websocket_error(
                    websocket=websocket,
                    code=403,
                    message=t("error.auth.token_invalid_or_expired", locale=locale),
                    error_code="WEBSOCKET_AUTH_FAILED",
                    close_reason="Authentication token invalid or expired",
                )
                return

            logger.info(
                "WebSocket connection authentication successful",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "id": user_id,  # ✅ Unified field name is id
                    "client": websocket.client.host if websocket.client else "unknown",
                },
            )

            # ✅ Gateway has verified token, extract host_id to ***REMOVED*** to backend service
            # This way backend service (host-service) doesn't need to verify token again
            host_id_param = f"host_id={user_id}"

        except Exception as e:
            logger.error(
                "WebSocket connection token verification exception",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "error": str(e),
                },
                exc_info=True,
            )
            await websocket.close(code=1011, reason="Internal server error")
            return

        # ✅ Step 2: Accept connection
        await websocket.accept()

        logger.info(
            f"WebSocket connection established: {hostname}/{apiurl}",
            extra={
                "hostname": hostname,
                "apiurl": apiurl,
                "client": websocket.client.host if websocket.client else "unknown",
                "has_token": bool(token),
            },
        )

        # Map full service name to short name
        # Example: host-service -> host, auth-service -> auth
        service_short_name = hostname.replace("-service", "")

        logger.info(
            f"Service name mapping: {hostname} -> {service_short_name}",
            extra={
                "hostname": hostname,
                "service_short_name": service_short_name,
                "apiurl": apiurl,
            },
        )

        # Build backend path (add /api/v1/ws/ prefix)
        # Get backend service address
        service_url = await proxy_service.get_service_url(hostname)

        backend_path = f"/ws/{apiurl}"

        # ✅ Optimization: ***REMOVED*** gateway-verified host_id and token
        # Backend service doesn't need to verify token again, directly use host_id
        query_params = f"token={token}&{host_id_param}"
        if not backend_path.startswith("?"):
            backend_path = f"{backend_path}?{query_params}"

        # ✅ Extract host_id as session key (for session stickiness)
        session_key = None
        try:
            # Prefer getting host_id from query parameters
            host_id_from_query = websocket.query_params.get("host_id")
            if host_id_from_query:
                session_key = str(host_id_from_query)
            elif user_id:
                # If no query parameter, use user_id (actually host_rec.id)
                session_key = str(user_id)
        except Exception as e:
            logger.debug(
                "Failed to extract session key, will use default load balancing",
                extra={"error": str(e)},
            )

        logger.info(
            "WebSocket proxy parameters prepared",
            extra={
                "hostname": hostname,
                "apiurl": apiurl,
                "id": user_id,  # ✅ Unified field name is id
                "session_key": session_key,
                "backend_path": backend_path[:100],  # Avoid log being too long
                "has_host_id": bool(user_id),
                "has_session_key": bool(session_key),
            },
        )

        # Forward to backend service (***REMOVED*** session_key for session stickiness)
        await proxy_service.forward_websocket(
            service_name=service_short_name,
            path=backend_path,
            client_websocket=websocket,
            service_url=service_url,
            session_key=session_key,  # ✅ Pass session key for session stickiness
        )

    except Exception as e:
        # ✅ Check if it's BusinessError (contains accurate error information)

        if isinstance(e, BusinessError):
            error_code = e.http_status_code or 500
            error_message = e.message
            error_type = e.error_code

            logger.warning(
                f"WebSocket business exception: {hostname}/{apiurl}",
                extra={
                    "error_code": error_code,
                    "error_message": error_message,
                    "hostname": hostname,
                    "apiurl": apiurl,
                },
            )
        else:
            # ✅ Other unknown exceptions
            error_code = 500
            error_message = "WebSocket forwarding exception"
            error_type = "WEBSOCKET_PROXY_ERROR"

            logger.error(
                f"WebSocket forwarding failed: {hostname}/{apiurl}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "hostname": hostname,
                    "apiurl": apiurl,
                },
                exc_info=True,
            )

        # ✅ Try to send accurate error message
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.send_json(
                    {
                        "code": error_code,
                        "message": error_message,
                        "error_code": error_type,
                    }
                )

                # ✅ Set correct close code based on error code
                if error_code == 403:
                    close_code = 1008  # Policy Violation
                    close_reason = "Authentication failed"
                elif error_code == 401:
                    close_code = 1008  # Policy Violation
                    close_reason = "Unauthorized"
                else:
                    close_code = 1011  # Internal Error
                    close_reason = "Server error"

                await websocket.close(code=close_code, reason=close_reason)
            except Exception as close_error:
                logger.debug(
                    "Error closing WebSocket", extra={"error": str(close_error)}
                )


# ✅ New: Support simplified format WebSocket proxy routes
# Supported format: /host/ws/agent/agent-123 -> ws://host-service:8003/api/v1/ws/agent/agent-123
SERVICE_SHORT_NAMES = {
    "auth": "auth-service",
    "host": "host-service",
}


# ❌ Removed: New format WebSocket routes conflict with HTTP routes, only use old format under /api/v1
# @router.websocket("/{service_short_name}/{path:path}")
# Please use: /api/v1/ws/host-service/ws/agent/agent-123 (old format)


@router.websocket("/ws/{hostname}/{apiurl:path}")
async def websocket_proxy(
    websocket: WebSocket,
    hostname: str,
    apiurl: str,
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> None:
    """WebSocket 转发端点

    新格式: /ws/{hostname}/{apiurl}
    例如: /ws/host-service/agent/agent-123

    将客户端 WebSocket 连接转发到后端微服务
    需要提供有效的认证令牌

    Args:
        websocket: 客户端 WebSocket 连接
        hostname: 服务主机名（如 host-service, auth-service）
        apiurl: API 路径（如 agent/agent-123）
        proxy_service: 代理服务实例
    """
    try:
        # ✅ 第一步：提取并验证 token（在接受连接前）
        token = None

        # 尝试从查询参数提取 token
        token = websocket.query_params.get("token")

        # 如果没有，尝试从 Authorization 头提取
        if not token:
            auth_header = websocket.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        # 如果还是没有，尝试从自定义头提取
        if not token:
            token = websocket.headers.get("X-Token")

        if not token:
            logger.warning(
                "WebSocket 连接缺少认证令牌",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "client": websocket.client.host if websocket.client else "unknown",
                },
            )
            # 拒绝连接
            await websocket.close(code=1008, reason="缺少认证令牌")
            return

        # ✅ 验证 token 有效性
        try:
            user_id = await verify_token_string(token)
            if not user_id:
                logger.warning(
                    "WebSocket 连接 token 验证失败",
                    extra={
                        "hostname": hostname,
                        "apiurl": apiurl,
                        "client": websocket.client.host if websocket.client else "unknown",
                        "token_preview": token[:20] + "..." if len(token) > 20 else token,
                    },
                )
                await websocket.close(code=1008, reason="认证令牌无效或已过期")
                return

            logger.info(
                "WebSocket 连接认证成功",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "user_id": user_id,
                    "client": websocket.client.host if websocket.client else "unknown",
                },
            )

        except Exception as e:
            logger.error(
                "WebSocket 连接 token 验证异常",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "error": str(e),
                },
                exc_info=True,
            )
            await websocket.close(code=1011, reason="服务器内部错误")
            return

        # ✅ 第二步：接受连接
        await websocket.accept()

        logger.info(
            f"WebSocket 连接已建立: {hostname}/{apiurl}",
            extra={
                "hostname": hostname,
                "apiurl": apiurl,
                "client": websocket.client.host if websocket.client else "unknown",
                "has_token": bool(token),
            },
        )

        # 映射完整服务名称到短名称
        # 例如: host-service -> host, auth-service -> auth, admin-service -> admin
        service_short_name = hostname.replace("-service", "")

        logger.info(
            f"服务名称映射: {hostname} -> {service_short_name}",
            extra={
                "hostname": hostname,
                "service_short_name": service_short_name,
                "apiurl": apiurl,
            },
        )

        # 构建后端路径（添加 /api/v1/ws/ 前缀）
        backend_path = f"/ws/{apiurl}"

        # 转发 token 到后端（作为查询参数）
        # 这样后端服务也能进行认证
        if not backend_path.startswith("?"):
            backend_path = f"{backend_path}?token={token}"

        # 转发到后端服务
        await proxy_service.forward_websocket(
            service_name=service_short_name,
            path=backend_path,
            client_websocket=websocket,
        )

    except Exception as e:
        logger.error(
            f"WebSocket 转发失败: {hostname}/{apiurl}",
            extra={
                "error": str(e),
                "hostname": hostname,
                "apiurl": apiurl,
            },
            exc_info=True,
        )

        # 尝试发送错误消息
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.send_json(
                    {
                        "code": 500,
                        "message": "WebSocket 转发异常",
                        "error_code": "WEBSOCKET_PROXY_ERROR",
                    }
                )
                await websocket.close(code=1011, reason="Server error")
            except Exception as close_error:
                logger.debug(f"关闭 WebSocket 时出错: {close_error!s}")


# ✅ 新增：支持简化格式的 WebSocket 代理路由
# 支持格式: /host/ws/agent/agent-123 -> ws://host-service:8003/api/v1/ws/agent/agent-123
SERVICE_SHORT_NAMES = {
    "auth": "auth-service",
    "host": "host-service",
}


# ❌ 已删除：新格式 WebSocket 路由与 HTTP 路由冲突，仅在 /api/v1 下使用旧格式
# @router.websocket("/{service_short_name}/{path:path}")
# 请使用: /api/v1/ws/host-service/ws/agent/agent-123 (旧格式)


@router.api_route(
    "/{service_name}/{subpath:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_service_request",
)
async def proxy_request(
    service_name: str = Path(..., description="Service name (e.g., auth, host, admin)"),
    subpath: str = Path(
        ..., description="Subpath (full path forwarded to backend service)"
    ),
    request: Request = ...,
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> Any:
    """Generic proxy endpoint

    Forwards request to specified backend microservice

    Args:
        service_name: Service name (e.g., auth-service, host-service)
        subpath: Subpath
        request: Request object
        proxy_service: Proxy service instance

    Returns:
        Backend service response

    Raises:
        HTTPException: Service not found or unavailable
    """
    try:
        # Get request method
        method = request.method

        # Get query parameters
        query_params = dict(request.query_params)

        # Get request body
        body = None
        raw_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # Try to read raw request body
                raw_body = await request.body()

                # If request body has content, try to parse as JSON
                if raw_body:
                    try:
                        body = json.loads(raw_body.decode("utf-8"))
                        logger.debug(
                            "Request body parsed successfully",
                            extra={"body_size_bytes": len(raw_body)},
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(
                            "Request body is not valid JSON, will forward as raw data",
                            extra={"error": str(e)},
                        )
                        # If not JSON, keep as None, use raw data
                        body = None
                else:
                    logger.debug("Request body is empty")

            except Exception as e:
                logger.error(
                    "Failed to read request body",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                # If read fails, raise appropriate error
                raise ValidationError(f"Unable to read request body: {e!s}")

        # Get request headers (after request body processing)
        headers = dict(request.headers)

        # ✅ Security measure: remove X-User-Info header from client (prevent forgery)
        # Gateway will add its own X-User-Info header after verifying token
        x_user_info_keys = [k for k in headers if k.lower() == "x-user-info"]
        if x_user_info_keys:
            for key in x_user_info_keys:
                logger.warning(
                    "Removed X-User-Info header from client (security measure)",
                    extra={
                        "header_key": key,
                        "service_name": service_name,
                        "subpath": subpath,
                        "method": method,
                        "hint": (
                            "X-User-Info header can only be added by Gateway after token verification, "
                            "client-sent headers will be removed"
                        ),
                    },
                )
                del headers[key]

        # Remove headers that may cause conflicts
        headers.pop("host", None)

        # Handle Content-Type header
        if raw_body is not None:
            # If using raw request body, ensure Content-Type is application/json
            if "content-type" not in [k.lower() for k in headers]:
                headers["Content-Type"] = "application/json"
                logger.debug(
                    "Added Content-Type for raw request body: application/json"
                )
            # Remove Content-Length header
            content_length_keys = [k for k in headers if k.lower() == "content-length"]
            for key in content_length_keys:
                del headers[key]
                logger.debug("Removed Content-Length header", extra={"header_key": key})

        # ✅ Add user information to request headers (get from request.state.user)
        user_info = getattr(request.state, "user", None)

        # ✅ Enhanced logging: record user information status (for diagnosis)
        logger.debug(
            "Checking user information status",
            extra={
                "has_user_info": user_info is not None,
                "user_info_type": type(user_info).__name__ if user_info else None,
                "user_info_keys": list(user_info.keys()) if user_info else None,
                "id": user_info.get("id") if user_info else None,
                "id_type": (
                    type(user_info.get("id")).__name__
                    if user_info and user_info.get("id")
                    else None
                ),
                "service_name": service_name,
                "subpath": subpath,
                "method": method,
<<<<<<< HEAD
            },
        )

        if user_info:
            # ✅ Use id field uniformly, return 401 error if missing
            user_id = user_info.get("id")
            if not user_id or (isinstance(user_id, str) and not user_id.strip()):
                logger.error(
                    "User information missing id, refusing to forward request",
                    extra={
                        "user_info_keys": list(user_info.keys()),
                        "id_value": user_id,
                        "id_type": type(user_id).__name__
                        if user_id is not None
                        else None,
                        "service_name": service_name,
                        "subpath": subpath,
                        "method": method,
                        "hint": (
                            "Please check Gateway authentication middleware logs "
                            "to confirm if token verification succeeded"
                        ),
                    },
                )
=======
                "path": subpath,
                "user": getattr(request.state, "user", None),
            },
        )

        # 准备调用forward_request
<<<<<<< HEAD
        logger.info(f"准备转发请求: service_name={service_name}, subpath={subpath}, has_raw_body={raw_body is not None}")
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
        logger.info(
            f"准备转发请求: service_name={service_name}, subpath={subpath}, has_raw_body={raw_body is not None}"
        )
>>>>>>> 0c5b1ec (🔧 更新 .env.example 文件，添加 Redis 配置并简化环境变量说明)

                # ✅ Return 401 error instead of skipping header setting
                locale = _get_locale_from_request(request)
                return _create_error_response(
                    request=request,
                    code=HTTP_401_UNAUTHORIZED,
                    message=t("error.auth.missing_id", locale=locale),
                    error_code="MISSING_ID",
                    message_key="error.auth.missing_id",
                    details={
                        "hint": "User information missing required id field, please login again to get valid token",
                        "user_info_keys": list(user_info.keys()),
                    },
                )

            # ✅ Ensure user_info contains unified id field
            if "id" not in user_info:
                user_info = user_info.copy()
                user_info["id"] = user_id
            # Serialize user information to JSON and add to request headers
            headers["X-User-Info"] = json.dumps(user_info, ensure_ascii=False)
            logger.info(
                "✅ Added user information to request headers",
                extra={
                    "id": user_id,
                    "username": user_info.get("username"),
                    "user_type": user_info.get("user_type"),
                    "service_name": service_name,
                    "subpath": subpath,
                    "method": method,
                },
            )
        else:
            logger.warning(
                "request.state.user does not exist, skipping X-User-Info header setting",
                extra={
                    "service_name": service_name,
                    "subpath": subpath,
                    "method": method,
                    "hint": "Request may not have ***REMOVED***ed authentication middleware, or path is set as public",
                },
            )

        # Log request
        logger.info(
            "Proxying request",
            extra={
                "service_name": service_name,
                "method": method,
                "path": subpath,
                "user": user_info,
                "has_user_info_header": "X-User-Info" in headers,
            },
        )

        # Prepare to call forward_request
        logger.info(
            "Preparing to forward request",
            extra={
                "service_name": service_name,
                "subpath": subpath,
                "has_raw_body": raw_body is not None,
            },
        )

        # Forward request
        response = await proxy_service.forward_request(
            service_name=service_name,
            path=subpath,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
            raw_body=raw_body,
        )

        status_code = response.get("status_code", 200)
        response_headers = response.get("headers") or {}
        is_json_response = response.get("is_json", False)
        body = response.get("body")
        raw_body = response.get("raw_body")

        if is_json_response and isinstance(body, (dict, list)):
            proxy_response: Response = JSONResponse(
                content=body, status_code=status_code
            )
        else:
            if raw_body is not None:
                content_bytes = raw_body
            elif isinstance(body, bytes):
                content_bytes = body
            elif isinstance(body, str):
                content_bytes = body.encode("utf-8")
            elif body is None:
                content_bytes = b""
            else:
                content_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

            media_type = response_headers.get("content-type")
            proxy_response = Response(
                content=content_bytes, status_code=status_code, media_type=media_type
            )

        for header_name, header_value in response_headers.items():
            if header_name.lower() in HOP_BY_HOP_RESPONSE_HEADERS:
                continue
            proxy_response.headers[header_name] = header_value

        logger.info(
            "Forwarding successful, returning response",
            extra={"status_code": status_code},
        )
        return proxy_response

    except ServiceNotFoundError as e:
        logger.warning(
            "Service not found",
            extra={"service_name": service_name, "error": str(e)},
        )
        raise e

    except BusinessError as e:
<<<<<<< HEAD
        # Pass through backend service business errors (4xx status codes)
        logger.warning(
            "Passing through backend service business error",
=======
        # 透传后端服务的业务错误（4xx状态码）
        logger.warning(
            f"透传后端服务业务错误: {service_name}",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            extra={
                "service_name": service_name,
                "error_message": e.message,
                "error_code": e.error_code,
                "status_code": e.code,
                "error_details": e.details,
            },
<<<<<<< HEAD
=======
        )
        raise e

<<<<<<< HEAD
    except ServiceUnavailableError as e:
        # 后端服务不可用错误（503状态码）
        logger.error(
            f"后端服务不可用: {service_name}",
            extra={
                "service_name": service_name,
                "error_message": e.message,
                "error_details": e.details,
            },
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        )
        raise e

=======
>>>>>>> 1d435cd (fix: 修复WebSocket 403问题 - 修复auth-service路由前缀注册错误)
    except Exception as e:
        logger.error(
            "Proxy request exception",
            extra={
                "service_name": service_name,
                "error": str(e),
                "exception_type": type(e).__name__,
            },
            exc_info=True,
        )

<<<<<<< HEAD
        locale = _get_locale_from_request(request)
        return _create_error_response(
            request=request,
            code=HTTP_500_INTERNAL_SERVER_ERROR,
            message=t("error.gateway.internal_error", locale=locale),
            error_code="GATEWAY_ERROR",
            message_key="error.gateway.internal_error",
=======
        # 直接返回JSONResponse，避免HTTPException的detail包装
        error_response = ErrorResponse(
            code=HTTP_500_INTERNAL_SERVER_ERROR,
            message="网关内部错误",
            error_code="GATEWAY_ERROR",
        )

        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
        )


@router.get("/services", response_model=SuccessResponse)
async def list_services(
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> SuccessResponse:
    """Get available service list

    Returns:
        Service list
    """
    services = list(proxy_service.service_routes.keys())

    return SuccessResponse(
        data={
            "services": services,
            "count": len(services),
        },
        message="Service list retrieved successfully",
    )


@router.get("/services/{service_name}/health", response_model=SuccessResponse)
async def check_service_health(
    service_name: str = Path(..., description="Service name (e.g., auth, host, admin)"),
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> Union[SuccessResponse, JSONResponse]:
<<<<<<< HEAD
    """Check service health status
=======
    """检查服务健康状态
>>>>>>> 1d435cd (fix: 修复WebSocket 403问题 - 修复auth-service路由前缀注册错误)

    Args:
        service_name: Service name
        proxy_service: Proxy service instance

    Returns:
        Health status

    Raises:
        HTTPException: Service not found
    """
    try:
        is_healthy = await proxy_service.health_check_service(service_name)

        return SuccessResponse(
            data={
                "service_name": service_name,
                "healthy": is_healthy,
                "status": "healthy" if is_healthy else "unhealthy",
            },
            message="Health check completed",
        )

    except ServiceNotFoundError as e:
<<<<<<< HEAD
        # Return JSONResponse directly to avoid HTTPException's detail wrapping
        error_response = ErrorResponse(
            code=e.code,  # Use business error code
            message=e.message,
            error_code=e.error_code,
            details=e.details,
        )

        return JSONResponse(
            status_code=e.http_status_code,  # Use exception-defined HTTP status code (400)
=======
        # 直接返回JSONResponse，避免HTTPException的detail包装
        error_response = ErrorResponse(
            code=HTTP_404_NOT_FOUND,
            message=e.message,
            error_code=e.error_code,
        )

        return JSONResponse(
            status_code=HTTP_404_NOT_FOUND,
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
            content=error_response.model_dump(),
        )


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    operation_id="catch_all_api_handler",
)
async def catch_all_handler(
    request: Request = ...,
    path: str = Path(..., description="Request path"),
):
    """Catch all unmatched requests, return unified format 404 error

    This route handler catches all requests that are not matched by other routes,
    and returns a unified 404 error response format that conforms to project specifications.
    """
<<<<<<< HEAD
<<<<<<< HEAD
=======
    from shared.common.response import ErrorResponse
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
>>>>>>> 45558e6 (docs(websocket): 更新WebSocket认证方式和状态管理文档)

    logger.warning(
        "Route not found",
        extra={
            "method": request.method,
            "path": path,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else "unknown",
        },
    )

    return _create_error_response(
        request=request,
        code=404,
        message=t(
            "error.gateway.resource_not_found", locale=_get_locale_from_request(request)
        ),
        error_code="RESOURCE_NOT_FOUND",
        message_key="error.gateway.resource_not_found",
        details={
            "method": request.method,
            "path": f"/{path}",
        },
    )
