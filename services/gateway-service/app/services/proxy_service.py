"""
代理服务模块

提供请求转发功能，将客户端请求代理到后端微服务
"""

import os
import sys
from typing import Any, Dict, Optional

# 使用 try-except 方式处理路径导入
try:
    import httpx

    from shared.common.exceptions import ServiceNotFoundError, ServiceUnavailableError
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    import httpx

    from shared.common.exceptions import ServiceNotFoundError, ServiceUnavailableError
    from shared.common.loguru_config import get_logger


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

        # HTTP 客户端配置
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

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

            # 构建完整 URL - 为每个服务添加标准的API前缀
            api_prefixes = {
                "auth": "/api/v1",
                "admin": "/api/v1",
                "host": "/api/v1",
            }
            api_prefix = api_prefixes.get(service_name, "/api/v1")
            full_url = f"{service_url}{api_prefix}{path}"

            # 记录请求日志
            logger.info(
                f"转发请求: {method} {full_url}",
                extra={
                    "service_name": service_name,
                    "method": method,
                    "path": path,
                },
            )

            # 简化请求处理 - 使用最基本的方式
            import requests

            # 清理头部 - 移除可能导致问题的头部
            clean_headers = {}
            if headers:
                for k, v in headers.items():
                    if k.lower() not in ["content-length", "transfer-encoding", "host"]:
                        clean_headers[k] = v

            # 发送同步请求
            if raw_body is not None:
                resp = requests.request(
                    method=method,
                    url=full_url,
                    headers=clean_headers,
                    params=query_params,
                    data=raw_body,
                )
            elif body is not None:
                resp = requests.request(
                    method=method,
                    url=full_url,
                    headers=clean_headers,
                    params=query_params,
                    json=body,
                )
            else:
                resp = requests.request(
                    method=method,
                    url=full_url,
                    headers=clean_headers,
                    params=query_params,
                )

            # 解析响应
            try:
                if resp.headers.get("content-type", "").startswith("application/json"):
                    response_body = resp.json()
                else:
                    response_body = resp.text
            except Exception:
                response_body = resp.text

            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": response_body,
            }

        except Exception as e:
            logger.error(
                f"请求转发异常: {service_name}",
                extra={"service_name": service_name, "error": str(e)},
                exc_info=True,
            )
            raise ServiceUnavailableError(f"请求转发异常: {service_name} - {e!s}")

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

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                return response.status_code == 200

        except Exception as e:
            logger.warning(
                f"健康检查失败: {service_name}",
                extra={"service_name": service_name, "error": str(e)},
            )
            return False


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
