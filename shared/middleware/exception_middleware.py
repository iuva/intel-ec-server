"""
统一异常处理中间件
"""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.exceptions import BusinessError, ErrorCode
from shared.common.loguru_config import get_logger
from shared.common.response import ErrorResponse

logger = get_logger(__name__)


class UnifiedExceptionMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件"""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        # 调试日志
        from shared.common.loguru_config import get_logger

        logger = get_logger(__name__)
        logger.info("统一异常处理中间件已初始化")

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        try:
            return await call_next(request)
        except Exception as exc:
            from shared.common.loguru_config import get_logger

            logger = get_logger(__name__)
            logger.info(f"捕获到异常: {type(exc).__name__}: {exc!s}")
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """处理异常并返回统一格式响应"""

        if isinstance(exc, BusinessError):
            return self._handle_business_error(exc)
        if isinstance(exc, RequestValidationError):
            return self._handle_validation_error(exc)
        if isinstance(exc, StarletteHTTPException):
            return self._handle_http_exception(exc)
        return self._handle_unexpected_error(exc)

    def _handle_business_error(self, exc: BusinessError) -> JSONResponse:
        """处理业务异常"""
        logger.warning(f"业务异常: {exc}")

        error_response = ErrorResponse(
            code=exc.code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        )

        return JSONResponse(status_code=exc.code, content=error_response.model_dump())

    def _handle_validation_error(self, exc: RequestValidationError) -> JSONResponse:
        """处理验证异常"""
        logger.warning(f"参数验证失败: {exc.errors()}")

        error_response = ErrorResponse(
            code=422,
            message="请求参数验证失败",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"errors": exc.errors()},
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    def _handle_http_exception(self, exc: StarletteHTTPException) -> JSONResponse:
        """处理HTTP异常"""
        logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")

        # 检查是否已经是统一格式
        if hasattr(exc, "detail"):
            detail_value = exc.detail
            if isinstance(detail_value, dict) and "error_code" in detail_value:  # type: ignore[unreachable]
                # 类型安全：直接返回已格式化的错误响应
                return JSONResponse(status_code=exc.status_code, content=detail_value)  # type: ignore[unreachable]

        # 转换为统一格式
        error_code_map = {
            404: ErrorCode.RESOURCE_NOT_FOUND,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            500: ErrorCode.INTERNAL_SERVER_ERROR,
        }

        error_response = ErrorResponse(
            code=exc.status_code,
            message=str(exc.detail),
            error_code=error_code_map.get(exc.status_code, "HTTP_ERROR"),
        )

        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    def _handle_unexpected_error(self, exc: Exception) -> JSONResponse:
        """处理未预期的异常"""
        logger.error("未处理的异常: %s", exc, exc_info=True)

        error_response = ErrorResponse(
            code=500,
            message="服务器内部错误",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(status_code=500, content=error_response.model_dump())
