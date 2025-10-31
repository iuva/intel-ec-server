"""
代理服务模块

提供请求转发功能，将客户端请求代理到后端微服务
"""

import asyncio
import contextlib
import os
import sys
import websockets
from typing import Any, Dict, Optional

from fastapi import Request, WebSocket, WebSocketDisconnect

# 使用 try-except 方式处理路径导入
try:
    from httpx import ConnectError, HTTPStatusError, NetworkError, TimeoutException

    from shared.common.exceptions import BusinessError, ServiceErrorCodes, ServiceNotFoundError
    from shared.common.http_client import AsyncHTTPClient
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    # 兼容不同版本的 httpx
    from httpx import ConnectError, TimeoutException

    from shared.common.exceptions import BusinessError, ServiceErrorCodes, ServiceNotFoundError
    from shared.common.http_client import AsyncHTTPClient
    from shared.common.loguru_config import get_logger

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

    def __init__(self, service_discovery=None):
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

        # 服务名称映射（短名称 -> 完整服务名）
        self.service_name_map = {
            "auth": "auth-service",
            "admin": "admin-service",
            "host": "host-service",
        }

        logger.info(
            "代理服务初始化完成",
            extra={
                "service_discovery_enabled": service_discovery is not None,
                "services": list(self.service_name_map.keys()),
            },
        )

        # 使用共享的 HTTP 客户端
        self.http_client = AsyncHTTPClient(
            timeout=30.0,
            connect_timeout=10.0,
            max_keepalive_connections=20,
            max_connections=100,
            max_retries=3,
            retry_delay=1.0,
        )

        # 健康检查专用客户端（缓存以避免重复创建）
        self._health_check_client = AsyncHTTPClient(
            timeout=5.0,
            connect_timeout=2.0,
            max_retries=1,
            retry_delay=0.5,
        )

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
            # 无服务发现时抛出异常
            logger.error(f"服务发现未配置，无法获取服务地址: {service_name}")
            raise ServiceNotFoundError(service_name)

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

            # 构建完整 URL
            full_url = self._build_service_url(service_url, path, service_name)

            # 记录请求日志
            logger.debug(
                "转发请求到后端服务",
                extra={
                    "service_name": service_name,
                    "method": method,
                    "path": path,
                },
            )

            # 清理请求头
            clean_headers = self._clean_headers(headers)

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
        # 获取服务发现实例（如果存在）
        service_discovery = None
        if hasattr(request.app.state, "service_discovery"):
            service_discovery = request.app.state.service_discovery
            logger.info("✅ 代理服务使用 Nacos 服务发现")
        else:
            logger.warning("⚠️ 代理服务未找到服务发现实例，使用静态配置")

        _proxy_service_instance = ProxyService(service_discovery=service_discovery)

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
        # 获取服务发现实例（如果存在）
        service_discovery = None
        if hasattr(websocket.app.state, "service_discovery"):
            service_discovery = websocket.app.state.service_discovery
            logger.info("✅ 代理服务（WebSocket）使用 Nacos 服务发现")
        else:
            logger.warning("⚠️ 代理服务（WebSocket）未找到服务发现实例，使用静态配置")

        _proxy_service_instance = ProxyService(service_discovery=service_discovery)

    return _proxy_service_instance
