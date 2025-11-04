"""
代理转发端点

提供通用的请求代理功能，将请求转发到后端微服务
"""

import json
import os
import sys
from typing import Any, Union

# 使用 try-except 方式处理路径导入
try:
    from app.services.proxy_service import ProxyService, get_proxy_service, get_proxy_service_ws
    from fastapi import APIRouter, Depends, Request, WebSocket
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

    from shared.common.exceptions import BusinessError, ServiceNotFoundError, ValidationError
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
    from shared.common.websocket_auth import verify_token_string
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.proxy_service import ProxyService, get_proxy_service, get_proxy_service_ws
    from fastapi import APIRouter, Depends, Request, WebSocket
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

    from shared.common.exceptions import BusinessError, ServiceNotFoundError, ValidationError
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
    from shared.common.websocket_auth import verify_token_string


logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/{hostname}/{apiurl:path}")
async def websocket_proxy(
    websocket: WebSocket,
    hostname: str,
    apiurl: str,
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
            # ✅ 必须先 accept 才能发送错误消息
            await websocket.accept()

            # 获取语言偏好（从 WebSocket headers 或使用默认）
            accept_language = websocket.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)

            await websocket.send_json(
                {
                    "code": 401,
                    "message": t("error.auth.missing_token", locale=locale),
                    "message_key": "error.auth.missing_token",
                    "error_code": "WEBSOCKET_MISSING_TOKEN",
                    "locale": locale,
                }
            )
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
                # ✅ 必须先 accept 才能发送错误消息
                await websocket.accept()

                # 获取语言偏好（从 WebSocket headers 或使用默认）
                accept_language = websocket.headers.get("Accept-Language")
                locale = parse_accept_language(accept_language)

                await websocket.send_json(
                    {
                        "code": 403,
                        "message": t("error.auth.token_invalid_or_expired", locale=locale),
                        "message_key": "error.auth.token_invalid_or_expired",
                        "error_code": "WEBSOCKET_AUTH_FAILED",
                        "locale": locale,
                    }
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
    service_name: str,
    subpath: str,
    request: Request,
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> Any:
    """通用代理端点

    将请求转发到指定的后端微服务

    Args:
        service_name: 服务名称（如 auth-service, admin-service）
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

        # 记录请求日志
        logger.info(
            f"代理请求: {method} /{service_name}/{subpath}",
            extra={
                "service_name": service_name,
                "method": method,
                "path": subpath,
                "user": getattr(request.state, "user", None),
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

        # 返回响应
        logger.info(f"转发成功，返回响应: {response.get('status_code')}")
        return response.get("body", {})

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

        # 直接返回JSONResponse，避免HTTPException的detail包装
        error_response = ErrorResponse(
            code=HTTP_500_INTERNAL_SERVER_ERROR,
            message="网关内部错误",
            error_code="GATEWAY_ERROR",
        )

        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
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
    service_name: str,
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
async def catch_all_handler(request: Request, path: str):
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

    # 返回统一格式的404错误响应
    error_response = ErrorResponse(
        code=404,
        message="请求的资源不存在",
        error_code="RESOURCE_NOT_FOUND",
        details={
            "method": request.method,
            "path": f"/{path}",
        },
    )

    return JSONResponse(status_code=404, content=error_response.model_dump())
