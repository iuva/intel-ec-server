"""
代理服务模块

提供请求转发功能，将客户端请求代理到后端微服务
"""

import asyncio
import json
import os
import re
import sys
from typing import Any, Dict, Optional

from fastapi import Request, WebSocket, WebSocketDisconnect
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.websockets import WebSocketState
import websockets

# 使用 try-except 方式处理路径导入
try:
    from httpx import ConnectError, HTTPStatusError, NetworkError, TimeoutException

    # 导入错误处理函数（代码重用）
    from app.services.proxy_error_handler import (
        raise_connection_error,
        raise_network_error,
        raise_protocol_error,
        raise_timeout_error,
    )
    from shared.common.exceptions import BusinessError, ServiceErrorCodes, ServiceNotFoundError
    from shared.common.http_client import AsyncHTTPClient, HTTPClientConfig
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import ServiceDiscovery
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    # 兼容不同版本的 httpx
    from httpx import ConnectError, TimeoutException

    # 导入错误处理函数（代码重用）
    from app.services.proxy_error_handler import (
        raise_connection_error,
        raise_network_error,
        raise_protocol_error,
        raise_timeout_error,
    )
    from shared.common.exceptions import BusinessError, ServiceErrorCodes, ServiceNotFoundError
    from shared.common.http_client import AsyncHTTPClient, HTTPClientConfig
    from shared.common.i18n import parse_accept_language, t
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
        max_websocket_connections: int = 1000,
    ):
        """初始化代理服务

        支持三种服务发现方式：
        1. Nacos 动态服务发现（推荐）
        2. Docker: 使用服务名（auth-service, host-service）
        3. 本地开发: 使用 localhost + 端口

        Args:
            service_discovery: ServiceDiscovery 实例（可选）
            http_client_config: HTTP 客户端配置（可选）
            health_check_client_config: 健康检查客户端配置（可选）
            max_websocket_connections: 最大 WebSocket 连接数限制，默认 1000
        """
        # 服务发现工具
        self.service_discovery = service_discovery

        # HTTP 客户端配置（在创建客户端之前必须初始化）
        # ✅ 优化：支持环境变量配置，提高灵活性和性能
        self.http_client_config = http_client_config or HTTPClientConfig(
            timeout=float(os.getenv("PROXY_HTTP_TIMEOUT", "30.0")),  # 增加超时时间
            connect_timeout=float(os.getenv("PROXY_CONNECT_TIMEOUT", "5.0")),
            max_keepalive_connections=int(os.getenv("PROXY_MAX_KEEPALIVE", "50")),  # 增加复用连接
            max_connections=int(os.getenv("PROXY_MAX_CONNECTIONS", "200")),  # 增加并发支持
            max_retries=0,
            retry_delay=0.0,
            client_name="gateway_proxy_http_client",
        )

        self.health_check_client_config = health_check_client_config or HTTPClientConfig(
            timeout=float(os.getenv("PROXY_HEALTH_TIMEOUT", "5.0")),
            connect_timeout=float(os.getenv("PROXY_HEALTH_CONNECT_TIMEOUT", "2.0")),
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

        # ✅ WebSocket 连接管理（支持环境变量配置）
        self.max_websocket_connections = max_websocket_connections or int(
            os.getenv("PROXY_MAX_WEBSOCKET_CONNECTIONS", "1000")
        )
        self.active_websocket_connections: Dict[str, Any] = {}  # 跟踪活跃连接
        self._websocket_connection_lock: Optional[asyncio.Lock] = None  # 连接数限制锁（延迟创建）

        logger.info(
            "代理服务初始化完成",
            extra={
                "service_discovery_enabled": service_discovery is not None,
                "services": list(self.service_name_map.keys()),
                "http_client_name": self.http_client_config.client_name,
                "health_check_client_name": self.health_check_client_config.client_name,
                "max_websocket_connections": max_websocket_connections,
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
                logger.debug("获取服务地址", extra={"service_name": service_name, "service_url": service_url})
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
            # logger.warning(
            #     f"服务发现未配置，使用后备地址: {service_name} -> {fallback_url}",
            #     extra={"service_name": service_name, "fallback_url": fallback_url},
            # )
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

    # ✅ 错误处理方法已移至 proxy_error_handler.py，使用模块级函数：
    # - log_backend_error()
    # - raise_connection_error()
    # - raise_timeout_error()
    # - raise_network_error()
    # - raise_protocol_error()

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

            # 获取语言偏好
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)

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
            elif body is not None:
                request_kwargs["json"] = body

            # 使用异步 HTTP 客户端发送请求
            # ✅ 禁用重试：网关调用接口失败时不进行重试，直接返回错误
            logger.info(
                f"开始发送 HTTP 请求: {method} {full_url}",
                extra={
                    "method": method,
                    "url": full_url,
                    "has_json": "json" in request_kwargs,
                    "has_data": "data" in request_kwargs,
                    "timeout": self.http_client_config.timeout,
                    "connect_timeout": self.http_client_config.connect_timeout,
                },
            )

            try:
                response = await self.http_client.request(
                    method=method,
                    url=full_url,
                    retry=False,  # 禁用自动重试
                    **request_kwargs,
                )

                status_code = response.get("status_code", 0)
                logger.info(
                    "HTTP 请求完成",
                    extra={
                        "method": method,
                        "full_url": full_url,
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
                        message=t("error.service.error_handling_failed", locale=locale),
                        message_key="error.service.error_handling_failed",
                        error_code="GATEWAY_ERROR_HANDLING_FAILED",
                        code=ServiceErrorCodes.GATEWAY_INTERNAL_ERROR,
                        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                        locale=locale,
                        details={
                            "service_name": service_name,
                            "method": method,
                            "path": path,
                            "status_code": status_code,
                        },
                    )

                return response
            except BusinessError:
                # ✅ BusinessError 是业务错误（如 4xx），不应该记录为 ERROR
                # 直接重新抛出，由上层处理
                raise
            except Exception as http_error:
                # 添加详细的连接错误日志（只记录真正的系统错误）
                logger.error(
                    "HTTP 请求异常",
                    extra={
                        "method": method,
                        "url": full_url,
                        "service_name": service_name,
                        "path": path,
                        "error_type": type(http_error).__name__,
                        "error": str(http_error),
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
            # 处理连接错误（使用模块级函数）
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_connection_error(service_name, e, locale)

        except TimeoutException as e:
            # 处理超时错误（使用模块级函数）
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_timeout_error(service_name, e, locale)

        except NetworkError as e:
            # 处理网络错误（使用模块级函数）
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_network_error(service_name, e, locale)

        except Exception as e:
            # 处理其他错误（协议错误等，使用模块级函数）
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_protocol_error(service_name, e, locale)

        # 不应该到达这里，但作为防御性编程
        msg = f"请求转发异常（未捕获）: {service_name}"
        raise RuntimeError(msg)

    async def forward_websocket(
        self,
        service_name: str,
        path: str,
        client_websocket: Any,  # WebSocket
        service_url: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> None:
        """转发 WebSocket 连接到后端服务（支持会话粘性）

        Args:
            service_name: 后端服务名称
            path: 请求路径
            client_websocket: 客户端 WebSocket 连接
            service_url: 服务 URL（可选，如果不提供则通过服务发现获取）
            session_key: 会话键（如 host_id），用于会话粘性。如果提供，会使用
                         基于哈希的会话粘性确保同一 session_key 总是路由到同一实例

        Raises:
            ServiceNotFoundError: 服务不存在
            BusinessError: 连接数已达上限
        """
        connection_id = None
        try:
            # ✅ 延迟创建锁（在异步上下文中）
            if self._websocket_connection_lock is None:
                self._websocket_connection_lock = asyncio.Lock()

            # ✅ 检查连接数限制
            async with self._websocket_connection_lock:
                current_connections = len(self.active_websocket_connections)
                if current_connections >= self.max_websocket_connections:
                    logger.warning(
                        "WebSocket 连接数已达上限，拒绝新连接",
                        extra={
                            "service_name": service_name,
                            "current_connections": current_connections,
                            "max_connections": self.max_websocket_connections,
                        },
                    )
                    # 获取语言偏好
                    accept_language = (
                        client_websocket.headers.get("Accept-Language")
                        if hasattr(client_websocket, "headers")
                        else None
                    )
                    locale = parse_accept_language(accept_language)
                    raise BusinessError(
                        message=t("error.websocket.connection_limit_reached", locale=locale),
                        message_key="error.websocket.connection_limit_reached",
                        error_code="WEBSOCKET_CONNECTION_LIMIT_REACHED",
                        code=ServiceErrorCodes.GATEWAY_SERVICE_UNAVAILABLE,
                        http_status_code=503,
                        locale=locale,
                    )

                # 生成连接ID并注册
                connection_id = f"{service_name}_{id(client_websocket)}"
                self.active_websocket_connections[connection_id] = {
                    "service_name": service_name,
                    "path": path,
                    "created_at": asyncio.get_event_loop().time(),
                }

            # ✅ 如果提供了会话键，使用会话粘性选择实例
            if session_key and self.service_discovery:
                try:
                    resolved_service_url = await self.service_discovery.get_websocket_service_url(
                        service_name, session_key
                    )
                    logger.info(
                        "使用会话粘性选择 WebSocket 实例",
                        extra={
                            "service_name": service_name,
                            "session_key": session_key,
                            "selected_url": resolved_service_url,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "会话粘性选择失败，使用默认方式",
                        extra={
                            "service_name": service_name,
                            "session_key": session_key,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    # 回退到默认方式
                    if not service_url:
                        resolved_service_url = await self.get_service_url(service_name)
                    else:
                        resolved_service_url = service_url
            elif not service_url:
                resolved_service_url = await self.get_service_url(service_name)
            else:
                resolved_service_url = service_url

            # 构建 WebSocket URL（转换 http -> ws，添加服务标识符前缀）
            ws_url = resolved_service_url.replace("http://", "ws://").replace("https://", "wss://")

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
                    "connection_id": connection_id,
                    "current_connections": len(self.active_websocket_connections),
                },
            )

            # 连接到后端 WebSocket
            # ✅ 启用 ping/pong 心跳机制，防止中间设备（代理、负载均衡器）因检测不到活动而关闭连接
            #
            # 心跳配置说明：
            # 1. 协议层心跳（ping/pong）：用于保持 TCP 连接活跃，防止中间设备关闭连接
            # 2. 应用层心跳（host-service）：Agent 通过 WebSocket 消息发送，用于业务逻辑（30-60秒间隔）
            # 3. 两者不会冲突：协议层心跳是底层机制，应用层心跳是业务消息
            #
            # 配置参数：
            # - ping_interval: 每 30 秒发送一次 ping（与应用层心跳间隔 30-60 秒协调）
            # - ping_timeout: ping 超时时间 10 秒（如果 10 秒内没有收到 pong，认为连接断开）
            # - close_timeout: 关闭连接的超时时间 10 秒
            #
            # 与 host-service 心跳配置的关系：
            # - host-service 应用层心跳超时：60 秒
            # - host-service 心跳检查间隔：10 秒
            # - Gateway 协议层心跳间隔：30 秒（小于应用层心跳超时，确保连接保持活跃）
            async with websockets.connect(
                full_ws_url,
                ping_interval=30,  # 每 30 秒发送一次 ping（与应用层心跳 30-60 秒协调）
                ping_timeout=10,  # ping 超时 10 秒
                close_timeout=10,  # 关闭超时 10 秒
            ) as server_websocket:
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

                # 取消其他任务并确保清理
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        ***REMOVED***
                    except Exception as e:
                        logger.warning("任务取消时出现异常", extra={"error": str(e)})

                # ✅ 确保 WebSocket 连接被正确关闭
                try:
                    # 检查客户端 WebSocket 状态
                    if hasattr(client_websocket, "client_state"):
                        if client_websocket.client_state != WebSocketState.DISCONNECTED:
                            await client_websocket.close(code=1000, reason="Connection closed")
                    elif not getattr(client_websocket, "closed", True):
                        # websockets.WebSocketClientProtocol
                        await client_websocket.close()
                except Exception as e:
                    logger.debug("关闭客户端 WebSocket 时出错", extra={"error": str(e)})

                try:
                    # 检查服务端 WebSocket 状态
                    if not server_websocket.closed:
                        await server_websocket.close()
                except Exception as e:
                    logger.debug("关闭服务端 WebSocket 时出错", extra={"error": str(e)})

                logger.info(
                    "WebSocket 连接已关闭",
                    extra={
                        "service_name": service_name,
                        "path": path,
                        "connection_id": connection_id,
                    },
                )

        except ServiceNotFoundError:
            # ✅ 确保在异常情况下也关闭客户端 WebSocket
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(code=1011, reason="Service not found")
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***
            raise
        except websockets.exceptions.InvalidURI as e:
            logger.error(
                "无效的 WebSocket URL",
                extra={"service_name": service_name, "path": path, "error": str(e)},
            )
            # ✅ 确保在异常情况下也关闭客户端 WebSocket
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(code=1011, reason="Invalid URI")
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***

            # 获取语言偏好
            accept_language = (
                client_websocket.headers.get("Accept-Language") if hasattr(client_websocket, "headers") else None
            )
            locale = parse_accept_language(accept_language)
            raise BusinessError(
                message=t("error.websocket.service_unavailable", locale=locale),
                message_key="error.websocket.service_unavailable",
                error_code="WEBSOCKET_SERVICE_UNAVAILABLE",
                code=ServiceErrorCodes.GATEWAY_SERVICE_UNAVAILABLE,
                http_status_code=503,
                locale=locale,
            )

        except websockets.exceptions.WebSocketException as e:
            error_msg = str(e)

            # ✅ 检查是否为认证失败（403 Forbidden）
            if "HTTP 403" in error_msg or "403 Forbidden" in error_msg:
                logger.warning(
                    "WebSocket 认证失败",
                    extra={"service_name": service_name, "path": path, "error_msg": error_msg},
                )
                # ✅ 确保在异常情况下也关闭客户端 WebSocket
                try:
                    if hasattr(client_websocket, "client_state"):
                        if client_websocket.client_state != WebSocketState.DISCONNECTED:
                            await client_websocket.close(code=1008, reason="Authentication failed")
                    elif not getattr(client_websocket, "closed", True):
                        await client_websocket.close()
                except Exception:
                    ***REMOVED***

                # 获取语言偏好
                accept_language = (
                    client_websocket.headers.get("Accept-Language") if hasattr(client_websocket, "headers") else None
                )
                locale = parse_accept_language(accept_language)
                raise BusinessError(
                    message=t("error.websocket.auth_failed", locale=locale),
                    message_key="error.websocket.auth_failed",
                    error_code="WEBSOCKET_AUTH_FAILED",
                    code=ServiceErrorCodes.GATEWAY_AUTH_FAILED,
                    http_status_code=403,
                    locale=locale,
                )

            # ✅ 检查是否为未授权（401 Unauthorized）
            if "HTTP 401" in error_msg or "401 Unauthorized" in error_msg:
                logger.warning(
                    "WebSocket 未授权",
                    extra={"service_name": service_name, "path": path, "error_msg": error_msg},
                )
                # ✅ 确保在异常情况下也关闭客户端 WebSocket
                try:
                    if hasattr(client_websocket, "client_state"):
                        if client_websocket.client_state != WebSocketState.DISCONNECTED:
                            await client_websocket.close(code=1008, reason="Unauthorized")
                    elif not getattr(client_websocket, "closed", True):
                        await client_websocket.close()
                except Exception:
                    ***REMOVED***

                # 获取语言偏好
                accept_language = (
                    client_websocket.headers.get("Accept-Language") if hasattr(client_websocket, "headers") else None
                )
                locale = parse_accept_language(accept_language)
                raise BusinessError(
                    message=t("error.websocket.unauthorized", locale=locale),
                    message_key="error.websocket.unauthorized",
                    error_code="WEBSOCKET_UNAUTHORIZED",
                    code=ServiceErrorCodes.GATEWAY_UNAUTHORIZED,
                    http_status_code=401,
                    locale=locale,
                )

            # ✅ 其他 WebSocket 连接错误
            logger.error(
                "WebSocket 连接异常",
                extra={"service_name": service_name, "path": path, "error_msg": error_msg},
            )
            # ✅ 确保在异常情况下也关闭客户端 WebSocket
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(code=1011, reason="Connection failed")
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***

            # 获取语言偏好
            accept_language = (
                client_websocket.headers.get("Accept-Language") if hasattr(client_websocket, "headers") else None
            )
            locale = parse_accept_language(accept_language)
            raise BusinessError(
                message=t("error.websocket.connection_failed", locale=locale),
                message_key="error.websocket.connection_failed",
                error_code="WEBSOCKET_CONNECTION_ERROR",
                code=ServiceErrorCodes.GATEWAY_CONNECTION_FAILED,
                http_status_code=502,
                locale=locale,
            )

        except Exception as e:
            logger.error(
                "WebSocket 转发异常",
                extra={"service_name": service_name, "path": path, "error_type": type(e).__name__, "error": str(e)},
                exc_info=True,
            )
            # ✅ 确保在异常情况下也关闭客户端 WebSocket
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(code=1011, reason="Server error")
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***

            # 获取语言偏好
            accept_language = (
                client_websocket.headers.get("Accept-Language") if hasattr(client_websocket, "headers") else None
            )
            locale = parse_accept_language(accept_language)
            raise BusinessError(
                message=t("error.websocket.proxy_error", locale=locale),
                message_key="error.websocket.proxy_error",
                error_code="WEBSOCKET_PROXY_ERROR",
                code=ServiceErrorCodes.GATEWAY_PROTOCOL_ERROR,
                http_status_code=502,
                locale=locale,
            )
        finally:
            # ✅ 清理连接记录
            if connection_id and connection_id in self.active_websocket_connections:
                # 确保锁已创建
                if self._websocket_connection_lock is None:
                    self._websocket_connection_lock = asyncio.Lock()

                async with self._websocket_connection_lock:
                    self.active_websocket_connections.pop(connection_id, None)
                    logger.debug(
                        "WebSocket 连接记录已清理",
                        extra={
                            "connection_id": connection_id,
                            "remaining_connections": len(self.active_websocket_connections),
                        },
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
                        logger.info("连接正常关闭", extra={"direction": direction, "code": e.code})
                    else:
                        logger.warning("连接异常关闭", extra={"direction": direction, "code": e.code, "reason": e.reason})
                    break
                except WebSocketDisconnect as e:
                    # FastAPI WebSocketDisconnect - 客户端正常断开
                    if e.code in (1000, 1001, 1005, None):
                        logger.info("客户端正常断开", extra={"direction": direction, "code": e.code})
                    else:
                        # 获取关闭原因
                        reason = e.reason if hasattr(e, "reason") else "No reason"
                        logger.warning("客户端异常断开", extra={"direction": direction, "code": e.code, "reason": reason})
                    break
                except Exception as e:
                    # 其他异常才记录为错误
                    error_type = type(e).__name__
                    logger.error("消息转发失败", extra={"direction": direction, "error_type": error_type, "error": str(e)})
                    break

        except websockets.exceptions.ConnectionClosed as e:
            # 外层捕获：连接正常关闭
            logger.debug("源连接已关闭", extra={"direction": direction, "code": e.code})
        except Exception as e:
            # 外层捕获：转发异常
            error_type = type(e).__name__
            logger.error("转发异常", extra={"direction": direction, "error_type": error_type, "error": str(e)})
        finally:
            # ✅ 确保目标 WebSocket 连接被关闭
            try:
                if hasattr(destination, "close"):
                    # FastAPI WebSocket
                    if hasattr(destination, "client_state"):
                        if destination.client_state != WebSocketState.DISCONNECTED:
                            await destination.close()
                    else:
                        await destination.close()
                elif hasattr(destination, "closed") and not destination.closed:
                    # websockets.WebSocketClientProtocol
                    await destination.close()
            except Exception as e:
                logger.debug("关闭目标 WebSocket 时出错", extra={"direction": direction, "error": str(e)})

            # ✅ 确保源 WebSocket 连接也被关闭（如果可能）
            try:
                if hasattr(source, "close") and not hasattr(source, "receive_text"):
                    # 只有非 FastAPI WebSocket 才需要手动关闭源连接
                    # FastAPI WebSocket 由框架管理
                    if hasattr(source, "closed") and not source.closed:
                        await source.close()
            except Exception as e:
                logger.debug("关闭源 WebSocket 时出错", extra={"direction": direction, "error": str(e)})

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
            "处理后端错误响应",
            extra={
                "service_name": service_name,
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
                # 尝试从响应头获取 locale，如果没有则使用默认值
                response_headers = response.get("headers", {})
                accept_language = (
                    response_headers.get("Accept-Language") if isinstance(response_headers, dict) else None
                )
                locale = parse_accept_language(accept_language) if accept_language else "zh_CN"
                error_message = t("error.service.unavailable", locale=locale)
                message_key = "error.service.unavailable"
                error_code = "SERVICE_UNAVAILABLE"
                error_details = {"service_name": service_name, "status_code": 502}
                backend_error_code = status_code  # 502
            else:
                # 502 但有响应体，尝试解析
                response_data_502: Any = response_body
                if isinstance(response_body, str):
                    try:
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

                # 尝试从响应中获取 locale
                response_headers = response.get("headers", {})
                accept_language = (
                    response_headers.get("Accept-Language") if isinstance(response_headers, dict) else None
                )
                locale_502 = (
                    parse_accept_language(accept_language)
                    if accept_language
                    else error_detail_502.get("locale", "zh_CN")
                )
                error_message = error_detail_502.get("message", t("error.service.unavailable", locale=locale_502))
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
                    response_data = json.loads(response_body)
                except (json.JSONDecodeError, TypeError):
                    response_data = {"message": response_body}

            # 分析错误响应格式
            if isinstance(response_data, dict):
                # ✅ 优先检查是否为统一错误响应格式（ErrorResponse）
                if "error_code" in response_data and "message" in response_data:
                    # 统一错误响应格式
                    error_detail = response_data
                # FastAPI 标准错误格式（detail 可能是字典或列表）
                elif "detail" in response_data:
                    detail_value = response_data["detail"]
                    # ✅ 处理 FastAPI 验证错误格式（detail 是列表）
                    if isinstance(detail_value, list):
                        # FastAPI 默认验证错误格式：{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
                        # 转换为统一格式
                        field_errors: Dict[str, str] = {}
                        for error in detail_value:
                            if isinstance(error, dict):
                                field_path = ".".join(str(loc) for loc in error.get("loc", []))
                                field_errors[field_path] = error.get("msg", "Unknown error")

                        # 获取语言偏好（从响应中或使用默认值）
                        locale_for_validation = (
                            response_data.get("locale", "zh_CN") if isinstance(response_data, dict) else "zh_CN"
                        )
                        error_detail = {
                            "message": t("error.validation", locale=locale_for_validation),
                            "message_key": "error.validation",
                            "error_code": "VALIDATION_ERROR",
                            "code": 422,
                            "locale": locale_for_validation,
                            "details": {"errors": field_errors},
                        }
                    elif isinstance(detail_value, dict):
                        # detail 是字典，可能是嵌套的错误响应
                        error_detail = detail_value
                    else:
                        # detail 是其他类型，使用原始响应
                        error_detail = response_data
                else:
                    # 没有 detail 字段，使用原始响应
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
            # 为 405 错误提供更友好的默认消息（使用多语言）
            if status_code == 405:
                # 尝试从响应中获取 locale，如果没有则使用默认值
                locale = error_detail.get("locale", "zh_CN")
                # 检查是否已有 message_key
                if "message_key" not in error_detail:
                    # 尝试提取允许的方法
                    detail_str = str(error_detail.get("message", ""))
                    allowed_match = re.search(r"allowed.*?\[(.*?)\]", detail_str, re.IGNORECASE)
                    if allowed_match:
                        allowed_methods = allowed_match.group(1)
                        message_key = "error.http.method_not_allowed_with_methods"
                        default_message = t(message_key, locale=locale, allowed_methods=allowed_methods)
                    else:
                        message_key = "error.http.method_not_allowed"
                        default_message = t(message_key, locale=locale)
                else:
                    # 已有 message_key，使用它
                    message_key = error_detail.get("message_key")
                    default_message = error_detail.get("message", "")
            else:
                # 为其他错误提供多语言支持
                locale_for_error = error_detail.get("locale", "zh_CN")
                default_message = t("error.service.error", locale=locale_for_error)
                message_key = "error.service.error"
                locale = locale_for_error

            error_message = error_detail.get("message", default_message)
            error_code = error_detail.get("error_code", f"BACKEND_{status_code}")
            error_details_raw = error_detail.get("details", {})
            # ✅ 提取 message_key 和 locale（用于多语言支持）
            # 如果 405 错误中没有 message_key，使用上面设置的 message_key
            if status_code != 405 or "message_key" not in error_detail:
                # 对于非 405 错误，或 405 错误但后端没有提供 message_key，使用后端提供的
                message_key = error_detail.get("message_key", message_key if status_code == 405 else None)
                locale = error_detail.get("locale", locale if status_code == 405 else "zh_CN")

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
            message_key=message_key if message_key else None,  # ✅ 透传 message_key 以支持多语言
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
                "解析后端响应",
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
                            "解码响应内容失败",
                            extra={
                                "service_name": service_name,
                                "status_code": status_code,
                                "error": str(decode_error),
                            },
                            exc_info=True,
                        )
                        response_data = {"message": f"后端服务返回了无效响应（状态码: {status_code}）"}
        except Exception as e:
            # 如果所有解析都失败，使用默认错误信息
            logger.error(
                "解析后端响应失败",
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
            # ✅ 优先检查是否为统一错误响应格式（ErrorResponse）
            if "error_code" in response_data and "message" in response_data:
                # 统一错误响应格式
                error_detail = response_data
            # FastAPI 标准错误格式（detail 可能是字典或列表）
            elif "detail" in response_data:
                detail_value = response_data["detail"]
                # ✅ 处理 FastAPI 验证错误格式（detail 是列表）
                if isinstance(detail_value, list):
                    # FastAPI 默认验证错误格式：{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
                    # 转换为统一格式
                    field_errors: Dict[str, str] = {}
                    for error in detail_value:
                        if isinstance(error, dict):
                            field_path = ".".join(str(loc) for loc in error.get("loc", []))
                            field_errors[field_path] = error.get("msg", "Unknown error")

                    # 获取语言偏好（从响应中或使用默认值）
                    locale_for_validation = (
                        response_data.get("locale", "zh_CN") if isinstance(response_data, dict) else "zh_CN"
                    )
                    error_detail = {
                        "message": t("error.validation", locale=locale_for_validation),
                        "message_key": "error.validation",
                        "error_code": "VALIDATION_ERROR",
                        "code": 422,
                        "locale": locale_for_validation,
                        "details": {"errors": field_errors},
                    }
                elif isinstance(detail_value, dict):
                    # detail 是字典，可能是嵌套的错误响应
                    error_detail = detail_value
                else:
                    # detail 是其他类型，使用原始响应
                    error_detail = response_data
            else:
                # 没有 detail 字段，使用原始响应
                error_detail = response_data
        else:
            error_detail = {"message": str(response_data)}

        # 提取关键错误信息
        locale_for_error = error_detail.get("locale", "zh_CN")
        error_message = error_detail.get("message", t("error.service.error", locale=locale_for_error))
        error_code = error_detail.get("error_code", f"BACKEND_{status_code}")
        error_details_raw = error_detail.get("details", {})
        # ✅ 提取 message_key 和 locale（用于多语言支持）
        message_key = error_detail.get("message_key")
        locale = error_detail.get("locale")
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
                "message_key": message_key,
                "locale": locale,
            },
        )

        # 直接透传所有 HTTP 状态码
        # 使用后端服务的自定义错误码（如 53009），而不是 HTTP 状态码（502）
        raise BusinessError(
            message=error_message,
            code=backend_error_code,  # 使用后端的自定义错误码
            error_code=error_code,
            http_status_code=status_code,  # HTTP 状态码保持为原始状态码
            message_key=message_key,  # ✅ 透传 message_key 以支持多语言
            locale=locale,  # ✅ 透传 locale 以支持多语言
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
        max_websocket_connections = getattr(request.app.state, "max_websocket_connections", 1000)

        _proxy_service_instance = ProxyService(
            service_discovery=service_discovery,
            http_client_config=http_client_config,
            health_check_client_config=health_check_config,
            max_websocket_connections=max_websocket_connections,
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
        max_websocket_connections = getattr(websocket.app.state, "max_websocket_connections", 1000)

        _proxy_service_instance = ProxyService(
            service_discovery=service_discovery,
            http_client_config=http_client_config,
            health_check_client_config=health_check_config,
            max_websocket_connections=max_websocket_connections,
        )

    return _proxy_service_instance
