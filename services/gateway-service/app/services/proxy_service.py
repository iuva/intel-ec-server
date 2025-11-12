"""
代理服务模块

提供请求转发功能，将客户端请求代理到后端微服务
"""

import asyncio
import contextlib
import os
import sys
from typing import Any, Dict, Optional

import websockets
from fastapi import Request, WebSocket, WebSocketDisconnect
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

# 使用 try-except 方式处理路径导入
try:
    from httpx import ConnectError, HTTPStatusError, NetworkError, TimeoutException

    from shared.common.exceptions import BusinessError, ServiceErrorCodes, ServiceNotFoundError
    from shared.common.http_client import AsyncHTTPClient, HTTPClientConfig
    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import ServiceDiscovery
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    # 兼容不同版本的 httpx
    from httpx import ConnectError, TimeoutException

    from shared.common.exceptions import BusinessError, ServiceErrorCodes, ServiceNotFoundError
    from shared.common.http_client import AsyncHTTPClient, HTTPClientConfig
    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import ServiceDiscovery

    # 导入 httpx 异常类
    try:
        from httpx._exceptions import HTTPStatusError, NetworkError
    except ImportError:
        # 如果还是失败，使用基础异常
        HTTPStatusError = Exception  # type: ignore[assignment, misc]
        NetworkError = Exception  # type: ignore[assignment, misc]

logger = get_logger(__name__)

# 常量定义
EXCLUDED_HEADERS = {"content-length", "transfer-encoding", "host"}
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"


class ProxyService:
    """代理服务类

    负责将请求转发到后端微服务
    """

    def __init__(
        self,
        service_discovery=None,
        http_client_config: Optional[HTTPClientConfig] = None,
        health_check_client_config: Optional[HTTPClientConfig] = None,
    ):
        """初始化代理服务

        支持三种服务发现方式：
        1. Nacos 动态服务发现（推荐）
        2. Docker: 使用服务名（auth-service, admin-service, host-service）
        3. 本地开发: 使用 localhost + 端口

        Args:
            service_discovery: ServiceDiscovery 实例（可选）
        """
        # 服务发现工具
        self.service_discovery = service_discovery

        # HTTP 客户端配置（在创建客户端之前必须初始化）
        self.http_client_config = http_client_config or HTTPClientConfig(
            timeout=15.0,
            connect_timeout=5.0,
            max_keepalive_connections=20,
            max_connections=100,
            max_retries=0,
            retry_delay=0.0,
            client_name="gateway_proxy_http_client",
        )

        self.health_check_client_config = health_check_client_config or HTTPClientConfig(
            timeout=5.0,
            connect_timeout=2.0,
            max_keepalive_connections=5,
            max_connections=10,
            max_retries=1,
            retry_delay=0.0,
            client_name="gateway_proxy_health_check_client",
        )

        # 服务名称映射（短名称 -> 完整服务名）
        self.service_name_map = {
            "auth": "auth-service",
            "host": "host-service",
        }

        logger.info(
            "代理服务初始化完成",
            extra={
                "service_discovery_enabled": service_discovery is not None,
                "services": list(self.service_name_map.keys()),
                "http_client_name": self.http_client_config.client_name,
                "health_check_client_name": self.health_check_client_config.client_name,
            },
        )

        # 使用共享的 HTTP 客户端
        # ✅ 恢复正常超时时间，异步版本
        self.http_client = AsyncHTTPClient(config=self.http_client_config)

        # 健康检查专用客户端（缓存以避免重复创建）
        self._health_check_client = AsyncHTTPClient(config=self.health_check_client_config)

    async def get_service_url(self, service_name: str) -> str:
        """获取服务 URL（异步方法）

        优先级：
        1. 使用 ServiceDiscovery 从 Nacos 动态获取
        2. 使用静态后备地址

        Args:
            service_name: 服务名称（短名称如 "auth"）

        Returns:
            服务 URL（如 "http://172.20.0.101:8001"）

        Raises:
            ServiceNotFoundError: 服务不存在
        """
        # 将短名称映射为完整服务名
        full_service_name = self.service_name_map.get(service_name, service_name)

        # 使用服务发现
        if self.service_discovery:
            try:
                service_url = await self.service_discovery.get_service_url(full_service_name)
                logger.debug(f"获取服务地址: {service_name} -> {service_url}")
                return service_url
            except Exception as e:
                logger.error(
                    f"服务发现失败: {service_name}",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                raise ServiceNotFoundError(service_name) from e
        else:
            # ✅ 修复：无服务发现时使用后备地址（本地开发环境）
            fallback_discovery = ServiceDiscovery()
            fallback_url = fallback_discovery._get_fallback_url(full_service_name)
            logger.warning(
                f"服务发现未配置，使用后备地址: {service_name} -> {fallback_url}",
                extra={"service_name": service_name, "fallback_url": fallback_url},
            )
            return fallback_url

    def _clean_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """清理请求头 - 移除可能导致问题的头部

        Args:
            headers: 原始请求头

        Returns:
            清理后的请求头
        """
        if not headers:
            return {}

        return {k: v for k, v in headers.items() if k.lower() not in EXCLUDED_HEADERS}

    def _build_service_url(self, service_url: str, path: str, service_name: str = "") -> str:
        """构建完整的服务 URL

        Args:
            service_url: 服务基础 URL
            path: 请求路径/subpath (如 'ws/hosts', 'device/login')
            service_name: 服务名称 (如 'auth', 'admin', 'host')

        Returns:
            完整的服务 URL (如 'http://host-service:8003/api/v1/host/ws/hosts')

        说明:
            Gateway接收的URL格式为 /api/v1/{service_name}/{subpath}
            转发到后端服务时，保留service_name，构建完整路径:
            - Gateway接收: /api/v1/host/ws/hosts → 转发到: /api/v1/host/ws/hosts
            - Gateway接收: /api/v1/auth/device/login → 转发到: /api/v1/auth/device/login
        """
        # ✅ 构建URL - 包含service_name，确保路由完整
        # Gateway接收: /api/v1/{service_name}/{subpath}
        # 转发到后端: /api/v1/{service_name}/{subpath}
        # 示例:
        #   Gateway接收: /api/v1/auth/device/login
        #   转发到Auth Service: /api/v1/auth/device/login ✅
        return f"{service_url}{API_PREFIX}/{service_name}/{path}"

    def _log_backend_error(self, service_name: str, method: str, path: str, error_type: str, error: str) -> None:
        """记录后端错误日志

        Args:
            service_name: 服务名称
            method: HTTP 方法
            path: 请求路径
            error_type: 错误类型
            error: 错误信息
        """
        logger.error(
            f"后端服务错误: {service_name} - {error_type}",
            extra={
                "service_name": service_name,
                "method": method,
                "path": path,
                "error_type": error_type,
                "error": error,
            },
            exc_info=True,
        )

    def _raise_connection_error(self, service_name: str, error: Exception) -> None:
        """抛出连接错误异常

        Args:
            service_name: 服务名称
            error: 原始异常
        """
        self._log_backend_error(service_name, "", "", "CONNECTION_ERROR", str(error))
        raise BusinessError(
            message=f"无法连接到后端服务: {service_name}",
            error_code="GATEWAY_CONNECTION_FAILED",
            code=ServiceErrorCodes.GATEWAY_CONNECTION_FAILED,
            http_status_code=502,
            details={"original_error": str(error), "service_name": service_name},
        )

    def _raise_timeout_error(self, service_name: str, error: Exception) -> None:
        """抛出超时错误异常

        Args:
            service_name: 服务名称
            error: 原始异常
        """
        self._log_backend_error(service_name, "", "", "TIMEOUT_ERROR", str(error))
        raise BusinessError(
            message=f"后端服务响应超时: {service_name}",
            error_code="GATEWAY_TIMEOUT",
            code=ServiceErrorCodes.GATEWAY_TIMEOUT,
            http_status_code=504,
            details={"original_error": str(error), "service_name": service_name, "timeout": True},
        )

    def _raise_network_error(self, service_name: str, error: Exception) -> None:
        """抛出网络错误异常

        Args:
            service_name: 服务名称
            error: 原始异常
        """
        self._log_backend_error(service_name, "", "", "NETWORK_ERROR", str(error))
        raise BusinessError(
            message=f"后端服务网络错误: {service_name}",
            error_code="GATEWAY_NETWORK_ERROR",
            code=ServiceErrorCodes.GATEWAY_NETWORK_ERROR,
            http_status_code=502,
            details={"original_error": str(error), "service_name": service_name},
        )

    def _raise_protocol_error(self, service_name: str, error: Exception) -> None:
        """抛出协议错误异常

        Args:
            service_name: 服务名称
            error: 原始异常
        """
        error_type = type(error).__name__
        self._log_backend_error(service_name, "", "", "PROTOCOL_ERROR", str(error))
        raise BusinessError(
            message=f"后端服务协议错误: {service_name}",
            error_code="GATEWAY_PROTOCOL_ERROR",
            code=ServiceErrorCodes.GATEWAY_PROTOCOL_ERROR,
            http_status_code=502,
            details={"original_error": str(error), "error_type": error_type, "service_name": service_name},
        )

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
            # 获取服务 URL（异步）
            service_url = await self.get_service_url(service_name)
            # logger.info(f"获取服务 URL: {service_url}")
            # 构建完整 URL
            full_url = self._build_service_url(service_url, path, service_name)
            # logger.info(f"构建完整 URL: {full_url}")
            # 记录请求日志（包含完整 URL）
            logger.info(
                f"转发请求到后端服务: {method} {full_url}",
                extra={
                    "service_name": service_name,
                    "method": method,
                    "path": path,
                    "full_url": full_url,
                    "service_url": service_url,
                },
            )

            # 清理请求头
            clean_headers = self._clean_headers(headers)

            logger.debug(
                f"清理后的请求头: {list(clean_headers.keys())}",
                extra={"headers_count": len(clean_headers)},
            )

            # 准备请求参数
            request_kwargs: Dict[str, Any] = {
                "headers": clean_headers,
                "params": query_params,
            }

            # 根据请求体类型设置不同的参数
            if raw_body is not None:
                request_kwargs["data"] = raw_body
                # 确保有 Content-Type 头
                if "Content-Type" not in clean_headers:
                    clean_headers["Content-Type"] = "application/json"
                logger.debug(f"使用原始请求体，Content-Type: {clean_headers.get('Content-Type')}")
            elif body is not None:
                request_kwargs["json"] = body
                # json 参数会自动设置 Content-Type
                logger.debug("使用 JSON 请求体")
            else:
                logger.debug("无请求体")

            # 使用异步 HTTP 客户端发送请求
            # ✅ 禁用重试：网关调用接口失败时不进行重试，直接返回错误
            logger.info(
                f"开始发送 HTTP 请求: {method} {full_url}",
                extra={
                    "method": method,
                    "url": full_url,
                    "has_json": "json" in request_kwargs,
                    "has_data": "data" in request_kwargs,
                    "timeout": 15.0,
                    "connect_timeout": 5.0,
                },
            )

            try:
                # ✅ 修复：使用共享的 AsyncHTTPClient
                # 现在 AsyncHTTPClient 不会抛出异常，而是返回所有状态码的响应
                logger.debug(f"使用 AsyncHTTPClient 发送请求: {method} {full_url}")

                response = await self.http_client.request(
                    method=method,
                    url=full_url,
                    retry=False,  # 禁用自动重试
                    **request_kwargs,
                )

                status_code = response.get("status_code", 0)
                logger.info(
                    f"HTTP 请求完成: {method} {full_url} -> {status_code}",
                    extra={
                        "status_code": status_code,
                        "has_body": response.get("body") is not None,
                        "body_type": type(response.get("body")).__name__ if response.get("body") else None,
                        "body_preview": str(response.get("body"))[:200] if response.get("body") else None,
                    },
                )

                if 400 <= status_code < 600:
                    # 使用新的方法处理响应字典中的错误
                    await self._handle_backend_http_error_from_response(service_name, method, path, response)

                    # 如果执行到此处，说明错误处理函数未按预期抛出异常
                    logger.error(
                        "后端错误处理未抛出异常",
                        extra={
                            "service_name": service_name,
                            "method": method,
                            "path": path,
                            "status_code": status_code,
                        },
                    )
                    raise BusinessError(
                        message="后端服务错误处理失败",
                        error_code="GATEWAY_ERROR_HANDLING_FAILED",
                        code=ServiceErrorCodes.GATEWAY_INTERNAL_ERROR,
                        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                        details={
                            "service_name": service_name,
                            "method": method,
                            "path": path,
                            "status_code": status_code,
                        },
                    )

                return response
            except Exception as http_error:
                # 添加详细的连接错误日志
                logger.error(
                    f"HTTP 请求异常: {method} {full_url}",
                    extra={
                        "method": method,
                        "url": full_url,
                        "service_name": service_name,
                        "path": path,
                        "error_type": type(http_error).__name__,
                        "error_message": str(http_error),
                    },
                    exc_info=True,
                )
                raise

        except ServiceNotFoundError:
            # 重新抛出服务不存在异常
            raise

        except BusinessError:
            # ✅ 重新抛出业务异常（来自后端服务的错误，应该直接透传）
            raise

        except HTTPStatusError as e:
            # 处理后端服务返回的 HTTP 错误
            # _handle_backend_http_error 内部会抛出异常，不会返回
            await self._handle_backend_http_error(service_name, method, path, e)
            # 防御性编程：如果异常处理出错，抛出异常
            raise

        except ConnectError as e:
            # 处理连接错误
            self._raise_connection_error(service_name, e)

        except TimeoutException as e:
            # 处理超时错误
            self._raise_timeout_error(service_name, e)

        except NetworkError as e:
            # 处理网络错误
            self._raise_network_error(service_name, e)

        except Exception as e:
            # 处理其他错误（协议错误等）
            self._raise_protocol_error(service_name, e)

        # 不应该到达这里，但作为防御性编程
        msg = f"请求转发异常（未捕获）: {service_name}"
        raise RuntimeError(msg)

    async def forward_websocket(
        self,
        service_name: str,
        path: str,
        client_websocket: Any,  # WebSocket
    ) -> None:
        """转发 WebSocket 连接到后端服务

        Args:
            service_name: 后端服务名称
            path: 请求路径
            client_websocket: 客户端 WebSocket 连接

        Raises:
            ServiceNotFoundError: 服务不存在
        """

        try:
            # 获取服务 URL
            service_url = self.get_service_url(service_name)

            # 构建 WebSocket URL（转换 http -> ws，添加服务标识符前缀）
            ws_url = service_url.replace("http://", "ws://").replace("https://", "wss://")

            # ✅ 添加服务标识符前缀（与 HTTP 转发保持一致）
            # 例如: service_name="host", path="/ws/host?token=xxx"
            # 结果: ws://host-service:8003/api/v1/host/ws/host?token=xxx
            if not path.startswith("/api"):
                full_ws_url = f"{ws_url}/api/v1/{service_name}{path}"
            else:
                full_ws_url = f"{ws_url}{path}"

            logger.info(
                "转发 WebSocket 连接",
                extra={
                    "service_name": service_name,
                    "path": path,
                    "target_url": full_ws_url,
                },
            )

            # 连接到后端 WebSocket
            async with websockets.connect(full_ws_url, ping_interval=None) as server_websocket:
                logger.info(
                    "后端 WebSocket 连接已建立",
                    extra={"service_name": service_name, "path": path},
                )

                # 创建双向消息转发任务
                client_to_server = asyncio.create_task(
                    self._forward_messages(
                        source=client_websocket,
                        destination=server_websocket,
                        direction="client->server",
                    )
                )

                server_to_client = asyncio.create_task(
                    self._forward_messages(
                        source=server_websocket,
                        destination=client_websocket,
                        direction="server->client",
                    )
                )

                # 等待任一任务完成（表示连接已关闭）
                done, pending = await asyncio.wait(
                    [client_to_server, server_to_client],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # 取消其他任务
                for task in pending:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

                logger.info(
                    "WebSocket 连接已关闭",
                    extra={"service_name": service_name, "path": path},
                )

        except ServiceNotFoundError:
            raise

        except websockets.exceptions.InvalidURI as e:
            logger.error(
                f"无效的 WebSocket URL: {e!s}",
                extra={"service_name": service_name, "path": path},
            )
            raise BusinessError(
                message="WebSocket 服务不可用",
                error_code="WEBSOCKET_SERVICE_UNAVAILABLE",
                code=ServiceErrorCodes.GATEWAY_SERVICE_UNAVAILABLE,
                http_status_code=503,
            )

        except websockets.exceptions.WebSocketException as e:
            error_msg = str(e)

            # ✅ 检查是否为认证失败（403 Forbidden）
            if "HTTP 403" in error_msg or "403 Forbidden" in error_msg:
                logger.warning(
                    f"WebSocket 认证失败: {error_msg}",
                    extra={"service_name": service_name, "path": path},
                )
                raise BusinessError(
                    message="WebSocket 认证失败，Token 无效或已过期",
                    error_code="WEBSOCKET_AUTH_FAILED",
                    code=ServiceErrorCodes.GATEWAY_AUTH_FAILED,
                    http_status_code=403,
                )

            # ✅ 检查是否为未授权（401 Unauthorized）
            if "HTTP 401" in error_msg or "401 Unauthorized" in error_msg:
                logger.warning(
                    f"WebSocket 未授权: {error_msg}",
                    extra={"service_name": service_name, "path": path},
                )
                raise BusinessError(
                    message="WebSocket 连接未授权，请提供有效的认证令牌",
                    error_code="WEBSOCKET_UNAUTHORIZED",
                    code=ServiceErrorCodes.GATEWAY_UNAUTHORIZED,
                    http_status_code=401,
                )

            # ✅ 其他 WebSocket 连接错误
            logger.error(
                f"WebSocket 连接异常: {error_msg}",
                extra={"service_name": service_name, "path": path},
            )
            raise BusinessError(
                message="WebSocket 连接失败",
                error_code="WEBSOCKET_CONNECTION_ERROR",
                code=ServiceErrorCodes.GATEWAY_CONNECTION_FAILED,
                http_status_code=502,
            )

        except Exception as e:
            logger.error(
                f"WebSocket 转发异常: {e!s}",
                extra={"service_name": service_name, "path": path, "error_type": type(e).__name__},
                exc_info=True,
            )
            raise BusinessError(
                message="WebSocket 转发失败",
                error_code="WEBSOCKET_PROXY_ERROR",
                code=ServiceErrorCodes.GATEWAY_PROTOCOL_ERROR,
                http_status_code=502,
            )

    async def _forward_messages(
        self,
        source: Any,  # FastAPI WebSocket 或 websockets.WebSocketClientProtocol
        destination: Any,  # websockets.WebSocketClientProtocol 或 FastAPI WebSocket
        direction: str = "unknown",
    ) -> None:
        """转发消息流

        Args:
            source: 源 WebSocket (可能是FastAPI WebSocket或websockets.WebSocketClientProtocol)
            destination: 目标 WebSocket (可能是FastAPI WebSocket或websockets.WebSocketClientProtocol)
            direction: 转发方向（用于日志）

        注意: 需要区分FastAPI WebSocket和websockets.WebSocketClientProtocol两种类型
        - FastAPI WebSocket: 使用 receive_text() / receive_bytes()
        - websockets.WebSocketClientProtocol: 直接用 async for 遍历或使用 recv()
        """

        try:
            # 判断source的类型来决定接收方法
            is_fastapi_source = hasattr(source, "receive_text")
            is_fastapi_destination = hasattr(destination, "send_text")

            while True:
                try:
                    message = None

                    # ✅ 接收消息 - 根据source类型选择方法
                    if is_fastapi_source:
                        # FastAPI WebSocket
                        try:
                            message = await source.receive_text()
                        except RuntimeError:
                            # 不是文本消息，尝试接收字节
                            message = await source.receive_bytes()
                    else:
                        # websockets.WebSocketClientProtocol
                        message = await source.recv()

                    # ✅ 发送消息 - 根据destination类型选择方法
                    if is_fastapi_destination:
                        # FastAPI WebSocket
                        if isinstance(message, bytes):
                            await destination.send_bytes(message)
                        else:
                            await destination.send_text(message)
                    else:
                        # websockets.WebSocketClientProtocol
                        await destination.send(message)

                except websockets.exceptions.ConnectionClosed as e:
                    # 正常关闭：1000-1001, 1005 (无状态码)
                    if e.code in (1000, 1001, 1005, None):
                        logger.info(f"连接正常关闭 ({direction}): code={e.code}")
                    else:
                        logger.warning(f"连接异常关闭 ({direction}): code={e.code}, reason={e.reason}")
                    break
                except WebSocketDisconnect as e:
                    # FastAPI WebSocketDisconnect - 客户端正常断开
                    if e.code in (1000, 1001, 1005, None):
                        logger.info(f"客户端正常断开 ({direction}): code={e.code}")
                    else:
                        # 获取关闭原因
                        reason = e.reason if hasattr(e, "reason") else "No reason"
                        logger.warning(f"客户端异常断开 ({direction}): code={e.code}, reason={reason}")
                    break
                except Exception as e:
                    # 其他异常才记录为错误
                    error_type = type(e).__name__
                    logger.error(f"消息转发失败 ({direction}): {error_type} - {e!s}")
                    break

        except websockets.exceptions.ConnectionClosed as e:
            # 外层捕获：连接正常关闭
            logger.debug(f"源连接已关闭 ({direction}): code={e.code}")
        except Exception as e:
            # 外层捕获：转发异常
            error_type = type(e).__name__
            logger.error(f"转发异常 ({direction}): {error_type} - {e!s}")
        finally:
            with contextlib.suppress(Exception):
                if hasattr(destination, "close"):
                    # FastAPI WebSocket
                    await destination.close()
                else:
                    # websockets.WebSocketClientProtocol
                    await destination.close()

    async def _handle_backend_http_error_from_response(
        self,
        service_name: str,
        method: str,
        path: str,
        response: Dict[str, Any],
    ) -> None:
        """从响应字典处理后端 HTTP 错误

        Args:
            service_name: 服务名称
            method: HTTP 方法
            path: 请求路径
            response: HTTP 响应字典（包含 status_code, headers, body）

        Raises:
            BusinessError: 业务异常
        """
        status_code = response.get("status_code", 500)
        response_body = response.get("body", {})

        # ✅ 添加详细日志用于调试
        logger.debug(
            f"处理后端错误响应: {service_name}",
            extra={
                "status_code": status_code,
                "response_body_type": type(response_body).__name__,
                "response_body_is_empty": (
                    not response_body or (isinstance(response_body, str) and not response_body.strip())
                ),
                "response_body_preview": str(response_body)[:200] if response_body else None,
            },
        )

        # ✅ 修复：处理 502 错误（Bad Gateway）的特殊情况
        # 502 通常表示网关无法连接到后端服务，响应体可能为空或无效
        if status_code == 502:
            # 检查响应体是否为空或无效
            if not response_body or (isinstance(response_body, str) and not response_body.strip()):
                # 502 且响应体为空，说明无法连接到后端服务
                error_message = "后端服务不可用或连接失败"
                error_code = "SERVICE_UNAVAILABLE"
                error_details = {"service_name": service_name, "status_code": 502}
                backend_error_code = status_code  # 502
                message_key = None
                locale = None
            else:
                # 502 但有响应体，尝试解析
                response_data_502: Any = response_body
                if isinstance(response_body, str):
                    try:
                        import json

                        response_data_502 = json.loads(response_body)
                    except (json.JSONDecodeError, TypeError):
                        response_data_502 = {"message": response_body}

                # 分析错误响应格式（支持 FastAPI 的 detail 格式）
                if isinstance(response_data_502, dict):
                    if "detail" in response_data_502 and isinstance(response_data_502["detail"], dict):
                        error_detail_502 = response_data_502["detail"]
                    else:
                        error_detail_502 = response_data_502
                else:
                    error_detail_502 = {"message": str(response_data_502)}

                error_message = error_detail_502.get("message", "后端服务不可用或连接失败")
                error_code = error_detail_502.get("error_code", "SERVICE_UNAVAILABLE")
                error_details_raw_502 = error_detail_502.get("details", {})
                # ✅ 提取 message_key 和 locale（用于多语言支持）
                message_key = error_detail_502.get("message_key")
                locale = error_detail_502.get("locale")
                # 确保 error_details 是字典类型
                if isinstance(error_details_raw_502, dict):
                    error_details_502: Dict[str, Any] = error_details_raw_502
                else:
                    error_details_502 = {
                        "value": str(error_details_raw_502),
                        "service_name": service_name,
                        "status_code": 502,
                    }
                error_details = error_details_502
                # 保留后端服务的自定义错误码（code），而不是用 HTTP 状态码覆盖
                backend_error_code_raw = error_detail_502.get("code")
                backend_error_code = backend_error_code_raw if isinstance(backend_error_code_raw, int) else status_code
        else:
            # 其他错误状态码（4xx, 5xx）
            # 解析响应体
            response_data: Any = response_body

            # 尝试解析 JSON 响应体
            if isinstance(response_body, str):
                try:
                    import json

                    response_data = json.loads(response_body)
                except (json.JSONDecodeError, TypeError):
                    response_data = {"message": response_body}

            # 分析错误响应格式
            if isinstance(response_data, dict):
                # FastAPI 标准错误格式
                if "detail" in response_data and isinstance(response_data["detail"], dict):
                    error_detail = response_data["detail"]
                else:
                    error_detail = response_data
            else:
                error_detail = {"message": str(response_data)}

            # ✅ 记录后端响应的原始内容（用于调试）
            logger.debug(
                "后端错误响应解析",
                extra={
                    "service_name": service_name,
                    "path": path,
                    "status_code": status_code,
                    "response_data": response_data,
                    "error_detail": error_detail,
                },
            )

            # ✅ 提取关键错误信息，包括多语言支持字段
            error_message = error_detail.get("message", f"后端服务错误: {status_code}")
            error_code = error_detail.get("error_code", f"BACKEND_{status_code}")
            error_details_raw = error_detail.get("details", {})
            # ✅ 提取 message_key 和 locale（用于多语言支持）
            message_key = error_detail.get("message_key")
            locale = error_detail.get("locale")

            # ✅ 保留后端服务的自定义错误码（code），而不是用 HTTP 状态码覆盖
            backend_error_code_raw = error_detail.get("code")
            backend_error_code = backend_error_code_raw if isinstance(backend_error_code_raw, int) else status_code

            # 确保 error_details 是字典类型
            if isinstance(error_details_raw, dict):
                error_details: Dict[str, Any] = error_details_raw
            else:
                error_details = {"value": str(error_details_raw)}

        # 记录详细错误日志
        logger.warning(
            "后端服务返回业务错误",
            extra={
                "service_name": service_name,
                "method": method,
                "path": path,
                "status_code": status_code,
                "error_code": error_code,
                "error_message": error_message,
                "error_details": error_details,
                "backend_error_code": backend_error_code,
                "message_key": message_key,
                "locale": locale,
            },
        )

        # ✅ 直接透传后端服务的错误信息，包括 code、message、error_code、message_key 和 locale
        # 使用后端服务的 HTTP 状态码（如 401），而不是 502
        raise BusinessError(
            message=error_message,
            code=backend_error_code,  # 使用后端的自定义错误码
            error_code=error_code,
            http_status_code=status_code,  # ✅ 使用后端服务的 HTTP 状态码（如 401）
            message_key=message_key,  # ✅ 透传 message_key 以支持多语言
            locale=locale,  # ✅ 透传 locale 以支持多语言
            details=error_details,
        )

    async def _handle_backend_http_error(
        self,
        service_name: str,
        method: str,
        path: str,
        http_error: Any,  # type: ignore[arg-type]
    ) -> None:
        """处理后端服务的HTTP错误响应

        透传后端服务的错误信息，保持原始状态码和详细错误内容
        """
        status_code = http_error.response.status_code

        # 尝试解析响应体
        # 注意：httpx 响应体只能读取一次，使用 content 属性可以多次访问
        try:
            # 读取原始内容（content 属性可以多次访问）
            response_content = http_error.response.content

            # 添加详细日志用于调试
            logger.debug(
                f"解析后端响应: status_code={status_code}, content_length={len(response_content) if response_content else 0}",
                extra={
                    "service_name": service_name,
                    "status_code": status_code,
                    "content_length": len(response_content) if response_content else 0,
                    "has_content": bool(response_content),
                },
            )

            if not response_content:
                # 502 状态码且响应体为空，可能是连接问题
                if status_code == 502:
                    response_data = {
                        "message": "后端服务不可用或连接失败",
                        "error_code": "SERVICE_UNAVAILABLE",
                    }
                else:
                    response_data = {"message": f"后端服务返回了空响应（状态码: {status_code}）"}
            else:
                # 尝试解析为 JSON
                try:
                    import json

                    response_text = response_content.decode("utf-8")
                    response_data = json.loads(response_text)

                    logger.debug(
                        "成功解析 JSON 响应",
                        extra={
                            "service_name": service_name,
                            "status_code": status_code,
                            "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else None,
                        },
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # 如果不是 JSON，使用文本内容
                    try:
                        response_text = response_content.decode("utf-8", errors="ignore")
                        response_data = {"message": response_text}

                        logger.warning(
                            "响应不是 JSON 格式，使用文本内容",
                            extra={
                                "service_name": service_name,
                                "status_code": status_code,
                                "response_preview": response_text[:200] if len(response_text) > 200 else response_text,
                            },
                        )
                    except Exception as decode_error:
                        logger.error(
                            f"解码响应内容失败: {str(decode_error)}",
                            extra={
                                "service_name": service_name,
                                "status_code": status_code,
                                "decode_error": str(decode_error),
                            },
                            exc_info=True,
                        )
                        response_data = {"message": f"后端服务返回了无效响应（状态码: {status_code}）"}
        except Exception as e:
            # 如果所有解析都失败，使用默认错误信息
            logger.error(
                f"解析后端响应失败: {str(e)}",
                extra={
                    "service_name": service_name,
                    "status_code": status_code,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            response_data = {"message": f"后端服务返回了无效响应（状态码: {status_code}）"}

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
        error_details_raw = error_detail.get("details", {})
        # 保留后端服务的自定义错误码（code），而不是用 HTTP 状态码覆盖
        backend_error_code_raw = error_detail.get("code")
        backend_error_code = backend_error_code_raw if isinstance(backend_error_code_raw, int) else status_code

        # 确保 error_details 是字典类型
        if isinstance(error_details_raw, dict):
            error_details: Dict[str, Any] = error_details_raw
        else:
            error_details = {"value": str(error_details_raw)}

        # 记录详细错误日志
        logger.warning(
            "后端服务返回业务错误",
            extra={
                "service_name": service_name,
                "method": method,
                "path": path,
                "status_code": status_code,
                "error_code": error_code,
                "error_message": error_message,
                "error_details": error_details,
                "backend_error_code": backend_error_code,
            },
        )

        # 直接透传所有 HTTP 状态码
        # 使用后端服务的自定义错误码（如 53009），而不是 HTTP 状态码（502）
        raise BusinessError(
            message=error_message,
            code=backend_error_code,  # 使用后端的自定义错误码
            error_code=error_code,
            http_status_code=status_code,  # HTTP 状态码保持为 502
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

            response = await self._health_check_client.request(
                method="GET",
                url=health_url,
                retry=False,  # 健康检查不启用重试
            )

            is_healthy = response["status_code"] == 200

            logger.debug(
                "健康检查完成",
                extra={
                    "service_name": service_name,
                    "is_healthy": is_healthy,
                    "status_code": response["status_code"],
                },
            )

            return is_healthy

        except ServiceNotFoundError:
            logger.warning("健康检查失败: 服务不存在", extra={"service_name": service_name})
            return False

        except Exception as e:
            logger.warning(
                "健康检查失败",
                extra={
                    "service_name": service_name,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            return False

    async def close(self) -> None:
        """关闭代理服务，释放资源"""
        if self.http_client:
            await self.http_client.close()

        if self._health_check_client:
            await self._health_check_client.close()

        logger.info("代理服务已关闭")


# 全局代理服务实例
_proxy_service_instance: Optional[ProxyService] = None


async def get_proxy_service(request: Request) -> ProxyService:
    """获取代理服务实例（HTTP依赖注入）

    从 request.app.state 获取服务发现实例并创建/返回 ProxyService。

    Args:
        request: FastAPI Request 对象

    Returns:
        代理服务实例
    """
    global _proxy_service_instance

    if _proxy_service_instance is None:
        # 获取服务发现实例（如果存在且不为 None）
        service_discovery = None
        if hasattr(request.app.state, "service_discovery"):
            service_discovery = request.app.state.service_discovery
            # ✅ 修复：只有当 service_discovery 不为 None 且已连接 Nacos 时才认为使用了 Nacos
            if service_discovery is not None and service_discovery.nacos_manager is not None:
                logger.info("✅ 代理服务使用 Nacos 服务发现")
            # else:
            #     logger.info("⚠️ 代理服务使用后备地址（Nacos 未启用或未连接）")
        # else:
        #     logger.info("⚠️ 代理服务使用后备地址（服务发现未配置）")

        http_client_config = getattr(request.app.state, "http_client_config", None)
        health_check_config = getattr(request.app.state, "health_check_http_client_config", None)

        _proxy_service_instance = ProxyService(
            service_discovery=service_discovery,
            http_client_config=http_client_config,
            health_check_client_config=health_check_config,
        )

    return _proxy_service_instance


async def get_proxy_service_ws(websocket: WebSocket) -> ProxyService:
    """获取代理服务实例（WebSocket依赖注入）

    从 websocket.app.state 获取服务发现实例并创建/返回 ProxyService。

    Args:
        websocket: FastAPI WebSocket 对象

    Returns:
        代理服务实例
    """
    global _proxy_service_instance

    if _proxy_service_instance is None:
        # 获取服务发现实例（如果存在且不为 None）
        service_discovery = None
        if hasattr(websocket.app.state, "service_discovery"):
            service_discovery = websocket.app.state.service_discovery
            # ✅ 修复：只有当 service_discovery 不为 None 且已连接 Nacos 时才认为使用了 Nacos
            if service_discovery is not None and service_discovery.nacos_manager is not None:
                logger.info("✅ 代理服务（WebSocket）使用 Nacos 服务发现")
            else:
                logger.info("⚠️ 代理服务（WebSocket）使用后备地址（Nacos 未启用或未连接）")
        else:
            logger.info("⚠️ 代理服务（WebSocket）使用后备地址（服务发现未配置）")

        http_client_config = getattr(websocket.app.state, "http_client_config", None)
        health_check_config = getattr(websocket.app.state, "health_check_http_client_config", None)

        _proxy_service_instance = ProxyService(
            service_discovery=service_discovery,
            http_client_config=http_client_config,
            health_check_client_config=health_check_config,
        )

    return _proxy_service_instance
