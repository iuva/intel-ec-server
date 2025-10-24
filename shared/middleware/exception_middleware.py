"""
统一异常处理中间件

捕获路由处理器中的未处理异常，为系统提供最后的防线。
"""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.exceptions import BusinessError, ErrorCode
from shared.common.loguru_config import get_logger
from shared.common.response import ErrorResponse

logger = get_logger(__name__)


class UnifiedExceptionMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件

    捕获路由处理器和其他中间件中的异常，提供最后的防线。
    大多数异常应该由应用级别的异常处理器处理。
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """中间件分发处理

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        try:
            return await call_next(request)
        except BusinessError as exc:
            # 业务异常
            logger.warning(
                f"业务异常: {exc.error_code} - {exc.message}",
                extra={
                    "error_code": exc.error_code,
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            error_response = ErrorResponse(
                code=exc.code,
                message=exc.message,
                error_code=exc.error_code,
                details=exc.details,
            )
            # 使用 http_status_code 作为 HTTP 状态码（必须是有效的 100-599）
            # 响应体中的 code 是自定义错误码（可能是 53009 这样的值）
            return JSONResponse(status_code=exc.http_status_code, content=error_response.model_dump())
        except Exception as exc:
            # 捕获所有未处理的异常
            logger.error(
                f"未处理的异常: {type(exc).__name__}",
                extra={"error": str(exc), "path": request.url.path, "method": request.method},
                exc_info=True,
            )
            error_response = ErrorResponse(
                code=500,
                message="服务器内部错误",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            )
            return JSONResponse(status_code=500, content=error_response.model_dump())
