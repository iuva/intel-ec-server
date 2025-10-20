"""
代理服务模块

提供请求转发功能，将客户端请求代理到后端微服务
"""

import os
import sys
from typing import Any, Dict, Optional

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import BusinessError, ServiceNotFoundError, ServiceUnavailableError
    from shared.common.http_client import AsyncHTTPClient
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.exceptions import BusinessError, ServiceNotFoundError, ServiceUnavailableError
    from shared.common.http_client import AsyncHTTPClient
    from shared.common.loguru_config import get_logger

# 导入 httpx 异常类
try:
    from httpx import HTTPStatusError, ConnectError, TimeoutException, NetworkError
except ImportError:
    # 兼容不同版本的 httpx
    from httpx import ConnectError, TimeoutException

    try:
        from httpx._exceptions import HTTPStatusError, NetworkError
    except ImportError:
        # 如果还是失败，使用基础异常
        HTTPStatusError = Exception
        NetworkError = Exception


logger = get_logger(__name__)


class ProxyService:
    """代理服务类

    负责将请求转发到后端微服务
    """

    def __init__(self):
        """初始化代理服务"""
        # 服务路由映射表 - 基础URL
        self.service_routes = {
            "auth": "http://auth-service:8001",
            "admin": "http://admin-service:8002",
            "host": "http://host-service:8003",
        }

        # 使用共享的 HTTP 客户端
        self.http_client = AsyncHTTPClient(
            timeout=30.0,
            connect_timeout=10.0,
            max_keepalive_connections=20,
            max_connections=100,
            max_retries=3,
            retry_delay=1.0,
        )

    def get_service_url(self, service_name: str) -> str:
        """获取服务 URL

        Args:
            service_name: 服务名称

        Returns:
            服务 URL

        Raises:
            ServiceNotFoundError: 服务不存在
        """
        service_url = self.service_routes.get(service_name)
        if not service_url:
            logger.warning(f"服务不存在: {service_name}")
            raise ServiceNotFoundError(service_name)

        logger.info(f"获取服务URL: service_name={service_name}, service_url={service_url}")
        return service_url

    async def forward_request(
        self,
        service_name: str,
        path: str,
        method: str,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """转发请求到后端服务

        Args:
            service_name: 服务名称
            path: 请求路径
            method: HTTP 方法
            headers: 请求头
            query_params: 查询参数
            body: 解析后的请求体（JSON）
            raw_body: 原始请求体数据（bytes）

        Returns:
            后端服务响应

        Raises:
            ServiceNotFoundError: 服务不存在
            ServiceUnavailableError: 服务不可用
        """
        try:
            # 获取服务 URL
            service_url = self.get_service_url(service_name)

            # 构建完整 URL - 所有服务都使用统一的API路径规则
            # 格式: {service_url}/api/v1/{path}
            full_url = f"{service_url}/api/v1/{path}"

            # 记录请求日志
            logger.info(
                f"转发请求: {method} {full_url}",
                extra={
                    "service_name": service_name,
                    "method": method,
                    "path": path,
                },
            )

            # 清理头部 - 移除可能导致问题的头部
            clean_headers = {}
            if headers:
                for k, v in headers.items():
                    if k.lower() not in ["content-length", "transfer-encoding", "host"]:
                        clean_headers[k] = v

            # 准备请求参数
            request_kwargs: Dict[str, Any] = {
                "headers": clean_headers,
                "params": query_params,
            }

            # 根据请求体类型设置不同的参数
            if raw_body is not None:
                request_kwargs["data"] = raw_body
            elif body is not None:
                request_kwargs["json"] = body

            # 使用异步 HTTP 客户端发送请求
            return await self.http_client.request(
                method=method,
                url=full_url,
                retry=True,  # 启用自动重试
                **request_kwargs,
            )

        except ServiceNotFoundError:
            # 重新抛出服务不存在异常
            raise

        except Exception as e:
            # 详细分析异常类型并透传后端服务信息

            # 处理 HTTP 状态错误（后端服务返回的业务错误）
            if isinstance(e, HTTPStatusError):
                await self._handle_backend_http_error(service_name, method, path, e)

            # 处理连接错误
            elif isinstance(e, ConnectError):
                logger.error(
                    f"后端服务连接失败: {service_name}",
                    extra={
                        "service_name": service_name,
                        "method": method,
                        "path": path,
                        "error_type": "CONNECTION_ERROR",
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise ServiceUnavailableError(f"无法连接到后端服务: {service_name}", details={"original_error": str(e)})

            # 处理超时错误
            elif isinstance(e, TimeoutException):
                logger.error(
                    f"后端服务响应超时: {service_name}",
                    extra={
                        "service_name": service_name,
                        "method": method,
                        "path": path,
                        "error_type": "TIMEOUT_ERROR",
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise ServiceUnavailableError(
                    f"后端服务响应超时: {service_name}", details={"original_error": str(e), "timeout": True}
                )

            # 处理其他网络错误
            elif isinstance(e, NetworkError):
                logger.error(
                    f"后端服务网络错误: {service_name}",
                    extra={
                        "service_name": service_name,
                        "method": method,
                        "path": path,
                        "error_type": "NETWORK_ERROR",
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise ServiceUnavailableError(f"后端服务网络异常: {service_name}", details={"original_error": str(e)})

            # 处理其他未知异常
            else:
                logger.error(
                    f"请求转发未知异常: {service_name}",
                    extra={
                        "service_name": service_name,
                        "method": method,
                        "path": path,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise ServiceUnavailableError(
                    f"请求转发异常: {service_name}", details={"original_error": str(e), "error_type": type(e).__name__}
                )

    async def _handle_backend_http_error(
        self, service_name: str, method: str, path: str, http_error: HTTPStatusError
    ) -> None:
        """处理后端服务的HTTP错误响应

        透传后端服务的错误信息，保持原始状态码和详细错误内容
        """
        status_code = http_error.response.status_code

        # 尝试解析响应体
        try:
            response_data = http_error.response.json()
        except Exception:
            # 如果不是JSON，尝试获取文本内容
            response_text = http_error.response.text
            response_data = {"message": response_text or "后端服务返回了无效响应"}

        # 分析错误响应格式
        if isinstance(response_data, dict):
            # FastAPI 标准错误格式
            if "detail" in response_data and isinstance(response_data["detail"], dict):
                error_detail = response_data["detail"]
            else:
                error_detail = response_data
        else:
            error_detail = {"message": str(response_data)}

        # 提取关键错误信息
        error_message = error_detail.get("message", f"后端服务错误: {status_code}")
        error_code = error_detail.get("error_code", f"BACKEND_{status_code}")
        error_details = error_detail.get("details", {})

        # 记录详细错误日志
        logger.warning(
            f"后端服务返回业务错误: {service_name}",
            extra={
                "service_name": service_name,
                "method": method,
                "path": path,
                "status_code": status_code,
                "error_code": error_code,
                "error_message": error_message,
                "error_details": error_details,
                "response_headers": dict(http_error.response.headers),
            },
        )

        # 根据状态码决定异常类型
        if 400 <= status_code < 500:
            # 客户端错误（4xx）- 业务逻辑错误，透传给客户端
            raise BusinessError(
                message=error_message,
                code=status_code,
                error_code=error_code,
                details=error_details,
            )
        elif 500 <= status_code < 600:
            # 服务器错误（5xx）- 后端服务内部错误，转换为网关错误
            raise ServiceUnavailableError(
                f"后端服务内部错误: {service_name}",
                details={
                    "backend_status_code": status_code,
                    "backend_error": error_message,
                    "backend_error_code": error_code,
                },
            )
        else:
            # 其他状态码，透传给客户端
            raise BusinessError(
                message=error_message,
                code=status_code,
                error_code=error_code,
                details=error_details,
            )

    async def health_check_service(self, service_name: str) -> bool:
        """检查服务健康状态

        Args:
            service_name: 服务名称

        Returns:
            服务是否健康
        """
        try:
            service_url = self.get_service_url(service_name)
            health_url = f"{service_url}/health"

            # 使用共享的 HTTP 客户端，配置较短的超时时间
            health_client = AsyncHTTPClient(
                timeout=5.0,
                connect_timeout=2.0,
                max_retries=1,  # 健康检查只重试一次
                retry_delay=0.5,
            )

            response = await health_client.request(
                method="GET",
                url=health_url,
                retry=False,  # 健康检查不启用重试
            )

            is_healthy = response["status_code"] == 200

            logger.debug(
                f"健康检查结果: {service_name}",
                extra={"service_name": service_name, "is_healthy": is_healthy, "status_code": response["status_code"]},
            )

            return is_healthy

        except ServiceNotFoundError:
            logger.warning(f"健康检查失败: 服务不存在 - {service_name}", extra={"service_name": service_name})
            return False

        except Exception as e:
            logger.warning(
                f"健康检查失败: {service_name}",
                extra={"service_name": service_name, "error_type": type(e).__name__, "error": str(e)},
            )
            return False

    async def close(self) -> None:
        """关闭代理服务，释放资源"""
        if self.http_client:
            await self.http_client.close()
            logger.info("代理服务 HTTP 客户端已关闭")


# 全局代理服务实例
_proxy_service_instance: Optional[ProxyService] = None


def get_proxy_service() -> ProxyService:
    """获取代理服务实例（单例模式）

    Returns:
        代理服务实例
    """
    global _proxy_service_instance

    if _proxy_service_instance is None:
        _proxy_service_instance = ProxyService()

    return _proxy_service_instance
