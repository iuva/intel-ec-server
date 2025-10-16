"""
代理转发端点

提供通用的请求代理功能，将请求转发到后端微服务
"""

import os
import sys
from typing import Any

# 使用 try-except 方式处理路径导入
try:
    from fastapi import APIRouter, Depends, HTTPException, Request
    from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

    from app.services.proxy_service import ProxyService, get_proxy_service
    from shared.common.exceptions import ServiceNotFoundError, ServiceUnavailableError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from fastapi import APIRouter, Depends, HTTPException, Request
    from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

    from app.services.proxy_service import ProxyService, get_proxy_service
    from shared.common.exceptions import ServiceNotFoundError, ServiceUnavailableError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse


logger = get_logger(__name__)

router = APIRouter()


@router.api_route(
    "/{service_name}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_service_request",
)
async def proxy_request(
    service_name: str,
    path: str,
    request: Request,
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> Any:
    """通用代理端点

    将请求转发到指定的后端微服务

    Args:
        service_name: 服务名称（如 auth-service, admin-service）
        path: 请求路径
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
                    import json

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
                from shared.common.exceptions import ValidationError

                raise ValidationError(f"无法读取请求体: {e!s}")

        # 获取请求头（在请求体处理之后）
        headers = dict(request.headers)

        # 移除可能导致冲突的头部
        headers.pop("host", None)
        # 如果使用原始请求体，也移除Content-Length头部
        if raw_body is not None:
            # Content-Length头部可能有不同的键名格式
            content_length_keys = [k for k in headers if k.lower() == "content-length"]
            for key in content_length_keys:
                del headers[key]
                logger.debug(f"移除Content-Length头部: {key}")

        # 记录请求日志
        logger.info(
            f"代理请求: {method} /{service_name}/{path}",
            extra={
                "service_name": service_name,
                "method": method,
                "path": path,
                "user": getattr(request.state, "user", None),
            },
        )

        # 准备调用forward_request
        logger.info(f"准备转发请求: service_name={service_name}, path={path}, has_raw_body={raw_body is not None}")

        # 转发请求
        response = await proxy_service.forward_request(
            service_name=service_name,
            path=f"/{path}",
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

    except ServiceUnavailableError as e:
        logger.error(
            f"服务不可用: {service_name}",
            extra={"service_name": service_name, "error": str(e)},
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
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                code=HTTP_500_INTERNAL_SERVER_ERROR,
                message="网关内部错误",
                error_code="GATEWAY_ERROR",
            ).model_dump(),
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
) -> SuccessResponse:
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
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code=HTTP_404_NOT_FOUND,
                message=e.message,
                error_code=e.error_code,
            ).model_dump(),
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
    from fastapi.responses import JSONResponse

    from shared.common.response import ErrorResponse

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
