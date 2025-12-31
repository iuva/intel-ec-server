"""
HTTP 请求/响应日志中间件

记录所有 HTTP 请求和响应的详细信息，包括：
- 请求方法、路径、查询参数
- 请求 Body（JSON格式）
- 响应状态码、响应 Body（JSON格式）
- 请求耗时
"""

import json
import time
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求/响应日志中间件

    自动记录所有 HTTP 请求和响应的详细信息：
    - 请求方法、路径、查询参数
    - 请求 Body（JSON格式）
    - 响应状态码、响应 Body（JSON格式）
    - 请求耗时
    """

    def __init__(self, app: Any, exclude_paths: Optional[list] = None) -> None:
        """
        初始化中间件

        Args:
            app: FastAPI 应用实例
            exclude_paths: 排除的路径列表（不记录日志的路径，如 /health, /metrics）
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    def _should_log(self, path: str) -> bool:
        """判断是否应该记录日志

        Args:
            path: 请求路径

        Returns:
            是否应该记录日志
        """
        # 移除查询参数
        clean_path = path.split("?")[0]

        # 检查是否在排除列表中
        for exclude_path in self.exclude_paths:
            if clean_path.startswith(exclude_path):
                return False

        return True

    async def _read_request_body(self, request: Request) -> Optional[dict]:
        """读取请求 Body（JSON格式）

        Args:
            request: FastAPI 请求对象

        Returns:
            解析后的 JSON 对象，如果不是 JSON 格式则返回 None
        """
        try:
            # 检查 Content-Type
            content_type = request.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return None

            # 读取 body
            body = await request.body()

            # 如果 body 为空，返回 None
            if not body:
                return None

            # 尝试解析 JSON
            try:
                return json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None

        except Exception:
            # 读取失败时返回 None
            return None

    async def _read_response_body(self, response: Response) -> Optional[dict]:
        """读取响应 Body（JSON格式）

        Args:
            response: FastAPI 响应对象

        Returns:
            解析后的 JSON 对象，如果不是 JSON 格式则返回 None
        """
        try:
            # 检查 Content-Type
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return None

            # 如果是 StreamingResponse，无法读取 body
            if isinstance(response, StreamingResponse):
                return None

            # 方法1: 尝试从 JSONResponse 的 body 属性读取（FastAPI/Starlette）
            if hasattr(response, "body"):
                body = response.body
                if body:
                    if isinstance(body, bytes):
                        try:
                            return json.loads(body.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            return None
                    elif isinstance(body, str):
                        try:
                            return json.loads(body)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            return None
                    elif isinstance(body, (dict, list)):
                        # 如果 body 已经是字典或列表，直接返回
                        return body

            # 方法2: 尝试从 JSONResponse 的 render 方法获取内容
            # FastAPI 的 JSONResponse 在 render 时会序列化 body
            # 注意：render() 方法不需要参数，但会修改响应对象，所以这里不使用
            # 改为在 dispatch 中直接读取 body 属性

            # 方法3: 尝试从 _content 属性读取（某些响应类型）
            if hasattr(response, "_content") and response._content:
                body = response._content
                if isinstance(body, bytes):
                    try:
                        return json.loads(body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        return None

            # ❌ 注意：不要尝试从 body_iterator 读取！
            # body_iterator 是响应流的一部分，消费它会破坏响应流
            # 如果尝试重新创建，必须创建异步迭代器，但这样会很复杂且容易出错
            # 对于 JSONResponse，应该能够从 body 或 content 属性读取

            return None

        except Exception:
            # 读取失败时返回 None
            return None

    def _extract_error_summary(self, response_body: Any) -> str:
        """从响应体中提取错误摘要信息

        Args:
            response_body: 响应体（可能是字典、列表或其他类型）

        Returns:
            错误摘要字符串
        """
        if not isinstance(response_body, dict):
            # 如果是列表，尝试提取第一个错误
            if isinstance(response_body, list) and response_body:
                first_error = response_body[0]
                if isinstance(first_error, dict):
                    return f"验证错误: {first_error.get('msg', '未知错误')}"
            return "未知错误格式"

        # 尝试提取错误信息
        error_parts = []

        # 1. 提取 message 字段
        if "message" in response_body:
            error_parts.append(f"消息: {response_body['message']}")

        # 2. 提取 error_code 字段
        if "error_code" in response_body:
            error_parts.append(f"错误码: {response_body['error_code']}")

        # 3. 提取 details 中的验证错误（422 错误）
        if "details" in response_body and isinstance(response_body["details"], dict):
            details = response_body["details"]
            # 检查是否有 errors 字段（验证错误）
            if "errors" in details and isinstance(details["errors"], dict):
                errors = details["errors"]
                if errors:
                    # 提取字段验证错误
                    field_errors = []
                    for field, error_msg in errors.items():
                        field_errors.append(f"{field}: {error_msg}")
                    if field_errors:
                        error_parts.append(f"验证错误: {', '.join(field_errors)}")

        # 4. 如果没有提取到信息，返回响应体的键
        if not error_parts:
            error_parts.append(f"响应键: {', '.join(response_body.keys())}")

        return " | ".join(error_parts)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """处理请求并记录日志

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            FastAPI 响应对象
        """
        # 检查是否应该记录日志
        if not self._should_log(request.url.path):
            return await call_next(request)

        # 记录开始时间
        start_time = time.time()

        # 提取请求信息
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else "unknown"

        # 读取请求 Body（JSON格式）
        request_body = await self._read_request_body(request)

        # 记录请求日志
        request_log_data = {
            "method": method,
            "path": path,
            "query_params": query_params if query_params else None,
            "client_ip": client_ip,
        }

        if request_body is not None:
            request_log_data["body"] = request_body
            logger.info(
                f"HTTP 请求: {method} {path}",
                extra=request_log_data,
            )
        else:
            logger.info(
                f"HTTP 请求: {method} {path}",
                extra=request_log_data,
            )

        try:
            # 处理请求
            response = await call_next(request)

            # 计算耗时
            duration = time.time() - start_time

            # 提取响应信息
            status_code = response.status_code

            # ✅ 读取响应体（JSON格式）
            # 使用改进的 _read_response_body 方法
            response_body = await self._read_response_body(response)

            # 记录响应日志
            response_log_data = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            }

            # ✅ 对于错误响应（4xx, 5xx），总是尝试记录响应体，即使读取失败也记录警告
            is_error_response = status_code >= 400

            if response_body is not None:
                response_log_data["body"] = response_body
                # ✅ 对于错误响应，使用 WARNING 级别，并突出显示错误信息
                if is_error_response:
                    # 提取关键错误信息
                    error_summary = self._extract_error_summary(response_body)
                    logger.warning(
                        f"HTTP 错误响应: {method} {path} - {status_code} ({duration*1000:.2f}ms) - {error_summary}",
                        extra=response_log_data,
                    )
                else:
                    logger.info(
                        f"HTTP 响应: {method} {path} - {status_code} ({duration*1000:.2f}ms)",
                        extra=response_log_data,
                    )
            else:
                # ✅ 对于错误响应，即使无法读取 body，也记录警告
                if is_error_response:
                    logger.warning(
                        f"HTTP 错误响应: {method} {path} - {status_code} ({duration*1000:.2f}ms) - 无法读取响应体",
                        extra={
                            **response_log_data,
                            "hint": "响应体可能不是 JSON 格式，或响应类型不支持读取（如 StreamingResponse）",
                            "content_type": response.headers.get("content-type"),
                        },
                    )
                else:
                    # 即使无法读取 body，也记录响应状态码和耗时
                    logger.info(
                        f"HTTP 响应: {method} {path} - {status_code} ({duration*1000:.2f}ms)",
                        extra=response_log_data,
                    )

            return response

        except Exception as e:
            # 计算耗时
            duration = time.time() - start_time

            # 记录异常日志（包含完整堆栈）
            logger.error(
                f"HTTP 请求异常: {method} {path} - {type(e).__name__}: {str(e)} ({duration*1000:.2f}ms)",
                extra={
                    "method": method,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,  # 记录完整堆栈信息
            )

            # 重新抛出异常
            raise
