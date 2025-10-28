"""
统一异常处理集成工具
"""

import json
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.common.exceptions import BusinessError, ErrorCode
from shared.common.loguru_config import get_logger
from shared.common.response import ErrorResponse
from shared.middleware.exception_middleware import UnifiedExceptionMiddleware

logger = get_logger(__name__)


def setup_exception_handling(app: FastAPI, service_name: str = "unknown") -> None:
    """为FastAPI应用设置统一异常处理

    Args:
        app: FastAPI应用实例
        service_name: 服务名称（用于日志）
    """

    # 注册 Pydantic 验证错误处理器（处理 422 错误）
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理 Pydantic 验证错误"""
        logger.warning(f"参数验证失败: {exc.errors()}")

        # 格式化错误信息，提供更清晰的字段级别错误
        field_errors: Dict[str, str] = {}
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            # 只保留错误信息，不保留类型
            field_errors[field_path] = error.get("msg", "Unknown error")

        error_response = ErrorResponse(
            code=422,
            message="请求参数验证失败",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"errors": field_errors},
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    # 注册 HTTP 异常处理器
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """处理 HTTP 异常"""
        logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")

        # 尝试理解 detail 的实际内容
        detail: Any = exc.detail

        # 如果是dict且包含error_code，说明是从@handle_api_errors抛出的统一格式
        if isinstance(detail, dict) and "error_code" in detail:
            # 直接返回统一格式的错误响应
            return JSONResponse(status_code=exc.status_code, content=detail)

        # 如果是字符串，尝试解析JSON
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
                if isinstance(detail, dict) and "error_code" in detail:
                    return JSONResponse(status_code=exc.status_code, content=detail)
            except (json.JSONDecodeError, TypeError):
                # JSON解析失败，继续使用转换逻辑
                ***REMOVED***

        # 对于非统一格式的异常，转换为统一格式
        error_code_map = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.RESOURCE_NOT_FOUND,
            500: ErrorCode.INTERNAL_SERVER_ERROR,
        }

        error_response = ErrorResponse(
            code=exc.status_code,
            message=str(detail),
            error_code=error_code_map.get(exc.status_code, "HTTP_ERROR"),
        )

        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    # 注册业务异常处理器
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        """处理业务异常"""
        logger.warning(f"业务异常: {exc.error_code} - {exc.message}")

        error_response = ErrorResponse(
            code=exc.code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        )

        # 使用 http_status_code 作为 HTTP 响应状态码（必须是有效的 HTTP 状态码 100-599）
        # 响应体中的 code 是自定义错误码（可能是 53009 这样的服务级错误码）
        return JSONResponse(status_code=exc.http_status_code, content=error_response.model_dump())

    # ❌ 重要: 不要在这里添加中间件！
    # 当 setup_exception_handling 被调用时，应用已经在 lifespan 中启动
    # 此时无法再添加中间件（会抛出 "Cannot add middleware after an application has started" 错误）
    # 中间件必须在 FastAPI 应用创建后、lifespan 启动前添加
    # 参考: auth-service/app/main.py 第70-71行 - 在创建app之后立即添加

    logger.info(f"已为 {service_name} 启用统一异常处理")
    logger.info("已注册异常处理器: RequestValidationError, HTTPException, BusinessError")
