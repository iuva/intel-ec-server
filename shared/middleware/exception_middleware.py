"""
统一异常处理中间件

捕获路由处理器中的未处理异常，为系统提供最后的防线。
支持多语言错误消息
"""

import os
import sys
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from shared.common.exceptions import BusinessError, ErrorCode
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.exceptions import BusinessError, ErrorCode
    from shared.common.i18n import parse_accept_language
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
            
            # 获取语言偏好（从请求头或异常中的 locale）
            accept_language = request.headers.get("Accept-Language")
            locale = exc.locale or parse_accept_language(accept_language)
            
            # 如果有 message_key，使用它创建响应；否则使用 message
            if exc.message_key:
                error_response = ErrorResponse(
                    code=exc.code,
                    message_key=exc.message_key,
                    error_code=exc.error_code,
                    details=exc.details,
                    locale=locale,
                    **exc.details,  # 传递格式化变量
                )
            else:
                error_response = ErrorResponse(
                    code=exc.code,
                    message=exc.message,
                    error_code=exc.error_code,
                    details=exc.details,
                    locale=locale,
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
            
            # 获取语言偏好
            accept_language = request.headers.get("Accept-Language")
            locale = parse_accept_language(accept_language)
            
            error_response = ErrorResponse(
                code=500,
                message_key="error.internal",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                locale=locale,
            )
            return JSONResponse(status_code=500, content=error_response.model_dump())
