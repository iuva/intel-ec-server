"""
代理转发端点

提供通用的请求代理功能，将请求转发到后端微服务
"""

import json
import os
import sys
from typing import Any, Dict, Optional, Union

# 使用 try-except 方式处理路径导入
try:
    from app.services.proxy_service import ProxyService, get_proxy_service, get_proxy_service_ws
    from fastapi import APIRouter, Depends, Path, Request, WebSocket, Response
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

    from shared.common.exceptions import BusinessError, ServiceNotFoundError, ValidationError
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
    from shared.common.websocket_auth import verify_token_string
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.proxy_service import ProxyService, get_proxy_service, get_proxy_service_ws
    from fastapi import APIRouter, Depends, Path, Request, WebSocket, Response
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

    from shared.common.exceptions import BusinessError, ServiceNotFoundError, ValidationError
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


def _get_locale_from_websocket(websocket: WebSocket) -> str:
    """从 WebSocket 中获取语言偏好

    Args:
        websocket: WebSocket 连接对象

    Returns:
        语言代码（如 "zh_CN", "en_US"）
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
    """创建统一的错误响应

    Args:
        request: FastAPI 请求对象
        code: HTTP 状态码
        message: 错误消息
        error_code: 错误代码
        message_key: 翻译键（可选）
        details: 错误详情（可选）

    Returns:
        JSON 响应
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
    """发送 WebSocket 错误消息并关闭连接

    Args:
        websocket: WebSocket 连接对象
        code: 错误代码
        message: 错误消息
        error_code: 错误类型标识
        close_code: WebSocket 关闭码
        close_reason: 关闭原因
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
    hostname: str = Path(..., description="主机名或服务标识符（如 host-service）"),
    apiurl: str = Path(..., description="WebSocket API 路径（转发到后端服务的完整路径）"),
    proxy_service: ProxyService = Depends(get_proxy_service_ws),
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

        # 如果仍然没有，尝试读取常见自定义头
        if not token:
            token = websocket.headers.get("X-Token") or websocket.headers.get("token")

        if not token:
            logger.warning(
                "WebSocket 连接缺少认证令牌",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "client": websocket.client.host if websocket.client else "unknown",
                },
            )
            # ✅ 必须先 accept 才能发送错误消息
            await websocket.accept()

            locale = _get_locale_from_websocket(websocket)
            await _send_websocket_error(
                websocket=websocket,
                code=401,
                message=t("error.auth.missing_token", locale=locale),
                error_code="WEBSOCKET_MISSING_TOKEN",
                close_reason="缺少认证令牌",
            )
            return

        # ✅ 验证 token 有效性（网关在此处验证）
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
                # ✅ 必须先 accept 才能发送错误消息
                await websocket.accept()

                locale = _get_locale_from_websocket(websocket)
                await _send_websocket_error(
                    websocket=websocket,
                    code=403,
                    message=t("error.auth.token_invalid_or_expired", locale=locale),
                    error_code="WEBSOCKET_AUTH_FAILED",
                    close_reason="认证令牌无效或已过期",
                )
                return

            logger.info(
                "WebSocket 连接认证成功",
                extra={
                    "hostname": hostname,
                    "apiurl": apiurl,
                    "id": user_id,  # ✅ 统一字段名为 id
                    "client": websocket.client.host if websocket.client else "unknown",
                },
            )

            # ✅ 网关已验证 token，提取 host_id 以传递给后端服务
            # 这样后端服务（host-service）就不需要重复验证 token
            host_id_param = f"host_id={user_id}"

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
        # 例如: host-service -> host, auth-service -> auth
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
        # 获取后端服务地址
        service_url = await proxy_service.get_service_url(hostname)

        backend_path = f"/ws/{apiurl}"

        # ✅ 优化：传递网关已验证的 host_id 和 token
        # 后端服务无需重复验证 token，直接使用 host_id
        query_params = f"token={token}&{host_id_param}"
        if not backend_path.startswith("?"):
            backend_path = f"{backend_path}?{query_params}"

        # ✅ 提取 host_id 作为会话键（用于会话粘性）
        session_key = None
        try:
            # 优先从查询参数获取 host_id
            host_id_from_query = websocket.query_params.get("host_id")
            if host_id_from_query:
                session_key = str(host_id_from_query)
            elif user_id:
                # 如果没有查询参数，使用 user_id（实际是 host_rec.id）
                session_key = str(user_id)
        except Exception as e:
            logger.debug(
                "提取会话键失败，将使用默认负载均衡",
                extra={"error": str(e)},
            )

        logger.info(
            "WebSocket 代理参数准备",
            extra={
                "hostname": hostname,
                "apiurl": apiurl,
                "id": user_id,  # ✅ 统一字段名为 id
                "session_key": session_key,
                "backend_path": backend_path[:100],  # 避免日志过长
                "has_host_id": bool(user_id),
                "has_session_key": bool(session_key),
            },
        )

        # 转发到后端服务（传递 session_key 实现会话粘性）
        await proxy_service.forward_websocket(
            service_name=service_short_name,
            path=backend_path,
            client_websocket=websocket,
            service_url=service_url,
            session_key=session_key,  # ✅ 传递会话键实现会话粘性
        )

    except Exception as e:
        # ✅ 检查是否为 BusinessError（包含准确的错误信息）

        if isinstance(e, BusinessError):
            error_code = e.http_status_code or 500
            error_message = e.message
            error_type = e.error_code

            logger.warning(
                f"WebSocket 业务异常: {hostname}/{apiurl}",
                extra={
                    "error_code": error_code,
                    "error_message": error_message,
                    "hostname": hostname,
                    "apiurl": apiurl,
                },
            )
        else:
            # ✅ 其他未知异常
            error_code = 500
            error_message = "WebSocket 转发异常"
            error_type = "WEBSOCKET_PROXY_ERROR"

            logger.error(
                f"WebSocket 转发失败: {hostname}/{apiurl}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "hostname": hostname,
                    "apiurl": apiurl,
                },
                exc_info=True,
            )

        # ✅ 尝试发送准确的错误消息
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.send_json(
                    {
                        "code": error_code,
                        "message": error_message,
                        "error_code": error_type,
                    }
                )

                # ✅ 根据错误码设置正确的关闭码
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
    service_name: str = Path(..., description="服务名称（如 auth、host、admin）"),
    subpath: str = Path(..., description="子路径（转发到后端服务的完整路径）"),
    request: Request = ...,
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> Any:
    """通用代理端点

    将请求转发到指定的后端微服务

    Args:
        service_name: 服务名称（如 auth-service, host-service）
        subpath: 子路径
        request: 请求对象
        proxy_service: 代理服务实例

    Returns:
        后端服务响应

    Raises:
        HTTPException: 服务不存在或不可用
    """
    try:
        # 获取请求方法
        method = request.method

        # 获取查询参数
        query_params = dict(request.query_params)

        # 获取请求体
        body = None
        raw_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # 尝试读取原始请求体
                raw_body = await request.body()

                # 如果有请求体内容，尝试解析为JSON
                if raw_body:
                    try:
                        body = json.loads(raw_body.decode("utf-8"))
                        logger.debug(f"解析请求体成功: {len(raw_body)} bytes")
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"请求体不是有效JSON，将作为原始数据转发: {e}")
                        # 如果不是JSON，保持为None，使用原始数据
                        body = None
                else:
                    logger.debug("请求体为空")

            except Exception as e:
                logger.error(f"读取请求体失败: {e}", exc_info=True)
                # 如果读取失败，抛出适当的错误
                raise ValidationError(f"无法读取请求体: {e!s}")

        # 获取请求头（在请求体处理之后）
        headers = dict(request.headers)

        # ✅ 安全措施：删除客户端传入的 X-User-Info header（防止伪造）
        # Gateway 会在验证 token 后添加自己的 X-User-Info header
        x_user_info_keys = [k for k in headers if k.lower() == "x-user-info"]
        if x_user_info_keys:
            for key in x_user_info_keys:
                logger.warning(
                    "删除客户端传入的 X-User-Info header（安全措施）",
                    extra={
                        "header_key": key,
                        "service_name": service_name,
                        "subpath": subpath,
                        "method": method,
                        "hint": "X-User-Info header 只能由 Gateway 在验证 token 后添加，客户端传入的将被删除",
                    },
                )
                del headers[key]

        # 移除可能导致冲突的头部
        headers.pop("host", None)

        # 处理Content-Type头
        if raw_body is not None:
            # 如果使用原始请求体，确保Content-Type为application/json
            if "content-type" not in [k.lower() for k in headers]:
                headers["Content-Type"] = "application/json"
                logger.debug("为原始请求体添加Content-Type: application/json")
            # 移除Content-Length头部
            content_length_keys = [k for k in headers if k.lower() == "content-length"]
            for key in content_length_keys:
                del headers[key]
                logger.debug(f"移除Content-Length头部: {key}")

        # ✅ 添加用户信息到请求头（从request.state.user获取）
        user_info = getattr(request.state, "user", None)

        # ✅ 增强日志：记录用户信息状态（用于诊断）
        logger.debug(
            "检查用户信息状态",
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
            },
        )

        if user_info:
            # ✅ 统一使用 id 字段，没有则返回 401 错误
            user_id = user_info.get("id")
            if not user_id or (isinstance(user_id, str) and not user_id.strip()):
                logger.error(
                    "用户信息中缺少 id，拒绝转发请求",
                    extra={
                        "user_info_keys": list(user_info.keys()),
                        "id_value": user_id,
                        "id_type": type(user_id).__name__ if user_id is not None else None,
                        "service_name": service_name,
                        "subpath": subpath,
                        "method": method,
                        "hint": "请检查 Gateway 认证中间件日志，确认 token 验证是否成功",
                    },
                )

                # ✅ 返回 401 错误，而不是跳过设置 header
                locale = _get_locale_from_request(request)
                return _create_error_response(
                    request=request,
                    code=HTTP_401_UNAUTHORIZED,
                    message=t("error.auth.missing_id", locale=locale),
                    error_code="MISSING_ID",
                    message_key="error.auth.missing_id",
                    details={
                        "hint": "用户信息中缺少必需的 id 字段，请重新登录获取有效令牌",
                        "user_info_keys": list(user_info.keys()),
                    },
                )

            # ✅ 确保 user_info 包含统一的 id 字段
            if "id" not in user_info:
                user_info = user_info.copy()
                user_info["id"] = user_id
            # 将用户信息序列化为JSON并添加到请求头
            headers["X-User-Info"] = json.dumps(user_info, ensure_ascii=False)
            logger.info(
                "✅ 添加用户信息到请求头",
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
                "request.state.user 不存在，跳过设置 X-User-Info header",
                extra={
                    "service_name": service_name,
                    "subpath": subpath,
                    "method": method,
                    "hint": "请求可能未通过认证中间件，或路径被设为公开路径",
                    },
                )

        # 记录请求日志
        logger.info(
            f"代理请求: {method} /{service_name}/{subpath}",
            extra={
                "service_name": service_name,
                "method": method,
                "path": subpath,
                "user": user_info,
                "has_user_info_header": "X-User-Info" in headers,
            },
        )

        # 准备调用forward_request
        logger.info(
            f"准备转发请求: service_name={service_name}, subpath={subpath}, has_raw_body={raw_body is not None}"
        )

        # 转发请求
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
            proxy_response: Response = JSONResponse(content=body, status_code=status_code)
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
            proxy_response = Response(content=content_bytes, status_code=status_code, media_type=media_type)

        for header_name, header_value in response_headers.items():
            if header_name.lower() in HOP_BY_HOP_RESPONSE_HEADERS:
                continue
            proxy_response.headers[header_name] = header_value

        logger.info(f"转发成功，返回响应: {status_code}")
        return proxy_response

    except ServiceNotFoundError as e:
        logger.warning(
            f"服务不存在: {service_name}",
            extra={"service_name": service_name, "error": str(e)},
        )
        raise e

    except BusinessError as e:
        # 透传后端服务的业务错误（4xx状态码）
        logger.warning(
            f"透传后端服务业务错误: {service_name}",
            extra={
                "service_name": service_name,
                "error_message": e.message,
                "error_code": e.error_code,
                "status_code": e.code,
                "error_details": e.details,
            },
        )
        raise e

    except Exception as e:
        logger.error(
            f"代理请求异常: {service_name} - 异常类型: {type(e).__name__}",
            extra={
                "service_name": service_name,
                "error": str(e),
                "exception_type": type(e).__name__,
            },
            exc_info=True,
        )

        locale = _get_locale_from_request(request)
        return _create_error_response(
            request=request,
            code=HTTP_500_INTERNAL_SERVER_ERROR,
            message=t("error.gateway.internal_error", locale=locale),
            error_code="GATEWAY_ERROR",
            message_key="error.gateway.internal_error",
        )


@router.get("/services", response_model=SuccessResponse)
async def list_services(
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> SuccessResponse:
    """获取可用服务列表

    Returns:
        服务列表
    """
    services = list(proxy_service.service_routes.keys())

    return SuccessResponse(
        data={
            "services": services,
            "count": len(services),
        },
        message="获取服务列表成功",
    )


@router.get("/services/{service_name}/health", response_model=SuccessResponse)
async def check_service_health(
    service_name: str = Path(..., description="服务名称（如 auth、host、admin）"),
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> Union[SuccessResponse, JSONResponse]:
    """检查服务健康状态

    Args:
        service_name: 服务名称
        proxy_service: 代理服务实例

    Returns:
        健康状态

    Raises:
        HTTPException: 服务不存在
    """
    try:
        is_healthy = await proxy_service.health_check_service(service_name)

        return SuccessResponse(
            data={
                "service_name": service_name,
                "healthy": is_healthy,
                "status": "healthy" if is_healthy else "unhealthy",
            },
            message="健康检查完成",
        )

    except ServiceNotFoundError as e:
        # 直接返回JSONResponse，避免HTTPException的detail包装
        error_response = ErrorResponse(
            code=e.code,  # 使用业务错误码
            message=e.message,
            error_code=e.error_code,
            details=e.details,
        )

        return JSONResponse(
            status_code=e.http_status_code,  # 使用异常定义的HTTP状态码（400）
            content=error_response.model_dump(),
        )


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    operation_id="catch_all_api_handler",
)
async def catch_all_handler(
    request: Request = ...,
    path: str = Path(..., description="请求路径"),
):
    """捕获所有未匹配的请求，返回统一格式的404错误

    这个路由处理器会捕获所有没有被其他路由匹配的请求，
    统一返回符合项目规范的404错误响应格式。
    """

    logger.warning(
        f"未找到路由: {request.method} /{path}",
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
        message=t("error.gateway.resource_not_found", locale=_get_locale_from_request(request)),
        error_code="RESOURCE_NOT_FOUND",
        message_key="error.gateway.resource_not_found",
        details={
            "method": request.method,
            "path": f"/{path}",
        },
    )
