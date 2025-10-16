"""
Proxy service module

Provides request forwarding functionality, proxying client requests to backend microservices
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

# Use try-except to handle path imports
try:
    from httpx import ConnectError, HTTPStatusError, NetworkError, TimeoutException

    # Import error handling functions (code reuse)
    from app.services.proxy_error_handler import (
        raise_connection_error,
        raise_network_error,
        raise_protocol_error,
        raise_timeout_error,
    )
    from shared.common.exceptions import (
        BusinessError,
        ServiceErrorCodes,
        ServiceNotFoundError,
    )
    from shared.common.http_client import AsyncHTTPClient, HTTPClientConfig
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import ServiceDiscovery
except ImportError:
    # If import fails, add project root directory to Python path
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    )
    # Compatible with different versions of httpx
    from httpx import ConnectError, TimeoutException

    # Import error handling functions (code reuse)
    from app.services.proxy_error_handler import (
        raise_connection_error,
        raise_network_error,
        raise_protocol_error,
        raise_timeout_error,
    )
    from shared.common.exceptions import (
        BusinessError,
        ServiceErrorCodes,
        ServiceNotFoundError,
    )
    from shared.common.http_client import AsyncHTTPClient, HTTPClientConfig
    from shared.common.i18n import parse_accept_language, t
    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import ServiceDiscovery

    # Import httpx exception classes
    try:
        from httpx._exceptions import HTTPStatusError, NetworkError
    except ImportError:
        # If still fails, use base exception
        HTTPStatusError = Exception  # type: ignore[assignment, misc]
        NetworkError = Exception  # type: ignore[assignment, misc]

logger = get_logger(__name__)

# Constant definitions
EXCLUDED_HEADERS = {"content-length", "transfer-encoding", "host"}
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"


class ProxyService:
    """Proxy service class

    Responsible for forwarding requests to backend microservices
    """

    def __init__(
        self,
        service_discovery=None,
        http_client_config: Optional[HTTPClientConfig] = None,
        health_check_client_config: Optional[HTTPClientConfig] = None,
        max_websocket_connections: int = 1000,
    ):
        """Initialize proxy service

        Supports three service discovery methods:
        1. Nacos dynamic service discovery (recommended)
        2. Docker: Use service names (auth-service, host-service)
        3. Local development: Use localhost + port

        Args:
            service_discovery: ServiceDiscovery instance (optional)
            http_client_config: HTTP client configuration (optional)
            health_check_client_config: Health check client configuration (optional)
            max_websocket_connections: Maximum WebSocket connection limit, default 1000
        """
        # Service discovery tool
        self.service_discovery = service_discovery

        # HTTP client configuration (must be initialized before creating client)
        from app.core.config import settings

        # ✅ Read configuration from settings
        self.http_client_config = http_client_config or HTTPClientConfig(
            timeout=float(os.getenv("PROXY_HTTP_TIMEOUT", str(settings.http_timeout))),
            connect_timeout=float(
                os.getenv("PROXY_CONNECT_TIMEOUT", str(settings.http_connect_timeout))
            ),
            max_keepalive_connections=int(
                os.getenv(
                    "PROXY_MAX_KEEPALIVE", str(settings.http_max_keepalive_connections)
                )
            ),
            max_connections=int(
                os.getenv("PROXY_MAX_CONNECTIONS", str(settings.http_max_connections))
            ),
            max_retries=int(
                os.getenv("PROXY_MAX_RETRIES", str(settings.http_max_retries))
            ),
            retry_delay=float(
                os.getenv("PROXY_RETRY_DELAY", str(settings.http_retry_delay))
            ),
            client_name="gateway_proxy_http_client",
        )

        self.health_check_client_config = (
            health_check_client_config
            or HTTPClientConfig(
                timeout=float(
                    os.getenv(
                        "PROXY_HEALTH_TIMEOUT", str(settings.health_check_timeout)
                    )
                ),
                connect_timeout=float(
                    os.getenv(
                        "PROXY_HEALTH_CONNECT_TIMEOUT",
                        str(settings.health_check_connect_timeout),
                    )
                ),
                max_keepalive_connections=settings.health_check_max_keepalive_connections,
                max_connections=settings.health_check_max_connections,
                max_retries=settings.health_check_max_retries,
                retry_delay=settings.health_check_retry_delay,
                client_name="gateway_proxy_health_check_client",
            )
        )

        # Service name mapping (short name -> full service name)
        # ✅ Read mapping from settings
        self.service_name_map = settings.service_name_map

        # ✅ WebSocket connection management (read from settings)
        self.max_websocket_connections = max_websocket_connections or int(
            os.getenv(
                "PROXY_MAX_WEBSOCKET_CONNECTIONS",
                str(settings.websocket_max_connections),
            )
        )
        self.active_websocket_connections: Dict[
            str, Any
        ] = {}  # Track active connections
        self._websocket_connection_lock: Optional[asyncio.Lock] = (
            None  # Connection limit lock (lazy creation)
        )

        logger.info(
            "Proxy service initialization completed",
            extra={
                "service_discovery_enabled": service_discovery is not None,
                "services": list(self.service_name_map.keys()),
                "http_client_name": self.http_client_config.client_name,
                "health_check_client_name": self.health_check_client_config.client_name,
                "max_websocket_connections": max_websocket_connections,
            },
        )

        # Use shared HTTP client
        # ✅ Restore normal timeout, async version
        self.http_client = AsyncHTTPClient(config=self.http_client_config)

        # Health check dedicated client (cached to avoid repeated creation)
        self._health_check_client = AsyncHTTPClient(
            config=self.health_check_client_config
        )

    async def get_service_url(self, service_name: str) -> str:
        """Get service URL (async method)

        Priority:
        1. Use ServiceDiscovery to dynamically get from Nacos
        2. Use static fallback address

        Args:
            service_name: Service name (short name like "auth")

        Returns:
            Service URL (e.g., "http://172.20.0.101:8001")

        Raises:
            ServiceNotFoundError: Service not found
        """
        # Map short name to full service name
        full_service_name = self.service_name_map.get(service_name, service_name)

        # Use service discovery
        if self.service_discovery:
            try:
                service_url = await self.service_discovery.get_service_url(
                    full_service_name
                )
                logger.debug(
                    "Get service address",
                    extra={"service_name": service_name, "service_url": service_url},
                )
                return service_url
            except Exception as e:
                logger.error(
                    f"Service discovery failed: {service_name}",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                raise ServiceNotFoundError(service_name) from e
        else:
            # ✅ Fix: Use fallback address when no service discovery (local development environment)
            fallback_discovery = ServiceDiscovery()
            return fallback_discovery._get_fallback_url(full_service_name)

    def _clean_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Clean request headers - remove headers that may cause issues

        Args:
            headers: Original request headers

        Returns:
            Cleaned request headers
        """
        if not headers:
            return {}

        return {k: v for k, v in headers.items() if k.lower() not in EXCLUDED_HEADERS}

    def _build_service_url(
        self, service_url: str, path: str, service_name: str = ""
    ) -> str:
        """Build complete service URL

        Args:
            service_url: Service base URL
            path: Request path/subpath (e.g., 'ws/hosts', 'device/login')
            service_name: Service name (e.g., 'auth', 'admin', 'host')

        Returns:
            Complete service URL (e.g., 'http://host-service:8003/api/v1/host/ws/hosts')

        Note:
            Gateway receives URL format: /api/v1/{service_name}/{subpath}
            When forwarding to backend service, keep service_name, build complete path:
            - Gateway receives: /api/v1/host/ws/hosts → forward to: /api/v1/host/ws/hosts
            - Gateway receives: /api/v1/auth/device/login → forward to: /api/v1/auth/device/login
        """
        # ✅ Build URL - include service_name to ensure complete routing
        # Gateway receives: /api/v1/{service_name}/{subpath}
        # Forward to backend: /api/v1/{service_name}/{subpath}
        # Example:
        #   Gateway receives: /api/v1/auth/device/login
        #   Forward to Auth Service: /api/v1/auth/device/login ✅
        return f"{service_url}{API_PREFIX}/{service_name}/{path}"

    # ✅ Error handling methods moved to proxy_error_handler.py, use module-level functions:
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
        """Forward request to backend service

        Args:
            service_name: Service name
            path: Request path
            method: HTTP method
            headers: Request headers
            query_params: Query parameters
            body: Parsed request body (JSON)
            raw_body: Raw request body data (bytes)

        Returns:
            Backend service response

        Raises:
            ServiceNotFoundError: Service not found
            ServiceUnavailableError: Service unavailable
        """
        try:
            # Get service URL (async)
            service_url = await self.get_service_url(service_name)
            # logger.info(f"Get service URL: {service_url}")
            # Build complete URL
            full_url = self._build_service_url(service_url, path, service_name)
            # logger.info(f"Build complete URL: {full_url}")
            # Log request (include complete URL)
            logger.info(
                f"Forwarding request to backend service: {method} {full_url}",
                extra={
                    "service_name": service_name,
                    "method": method,
                    "path": path,
                    "full_url": full_url,
                    "service_url": service_url,
                },
            )

            # Clean request headers
            clean_headers = self._clean_headers(headers)

            # Get language preference
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)

            # Prepare request parameters
            request_kwargs: Dict[str, Any] = {
                "headers": clean_headers,
                "params": query_params,
            }

            # Set different parameters based on request body type
            if raw_body is not None:
                request_kwargs["data"] = raw_body
                # Ensure Content-Type header exists
                if "Content-Type" not in clean_headers:
                    clean_headers["Content-Type"] = "application/json"
            elif body is not None:
                request_kwargs["json"] = body

            # Use async HTTP client to send request
            # ✅ Disable retry: Gateway does not retry when interface call fails, directly returns error
            logger.info(
                f"Starting to send HTTP request: {method} {full_url}",
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
                    retry=False,  # Disable automatic retry
                    **request_kwargs,
                )

                status_code = response.get("status_code", 0)
                logger.info(
                    "HTTP request completed",
                    extra={
                        "method": method,
                        "full_url": full_url,
                        "status_code": status_code,
                        "has_body": response.get("body") is not None,
                        "body_type": type(response.get("body")).__name__
                        if response.get("body")
                        else None,
                        "body_preview": str(response.get("body"))[:200]
                        if response.get("body")
                        else None,
                    },
                )

                if 400 <= status_code < 600:
                    # Use new method to handle errors in response dict
                    await self._handle_backend_http_error_from_response(
                        service_name, method, path, response
                    )

                    # If execution reaches here, error handling function did not raise exception as expected
                    logger.error(
                        "Backend error handling did not raise exception",
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
                # ✅ BusinessError is business error (e.g., 4xx), should not be logged as ERROR
                # Directly re-raise, handled by upper layer
                raise
            except Exception as http_error:
                # Add detailed connection error log (only log real system errors)
                logger.error(
                    "HTTP request exception",
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
            # Re-raise service not found exception
            raise

        except BusinessError:
            # ✅ Re-raise business exception (error from backend service, should be directly ***REMOVED***ed through)
            raise

        except HTTPStatusError as e:
            # Handle HTTP error returned by backend service
            # _handle_backend_http_error internally raises exception, does not return
            await self._handle_backend_http_error(service_name, method, path, e)
            # Defensive programming: if exception handling fails, raise exception
            raise

        except ConnectError as e:
            # Handle connection error (use module-level function)
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_connection_error(service_name, e, locale)

        except TimeoutException as e:
            # Handle timeout error (use module-level function)
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_timeout_error(service_name, e, locale)

        except NetworkError as e:
            # Handle network error (use module-level function)
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_network_error(service_name, e, locale)

        except Exception as e:
            # Handle other errors (protocol errors, etc., use module-level function)
            accept_language = headers.get("Accept-Language") if headers else None
            locale = parse_accept_language(accept_language)
            raise_protocol_error(service_name, e, locale)

        # Should not reach here, but as defensive programming
        msg = f"Request forwarding exception (uncaught): {service_name}"
        raise RuntimeError(msg)

    async def forward_websocket(
        self,
        service_name: str,
        path: str,
        client_websocket: Any,  # WebSocket
        service_url: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> None:
        """Forward WebSocket connection to backend service (supports session stickiness)

        Args:
            service_name: Backend service name
            path: Request path
            client_websocket: Client WebSocket connection
            service_url: Service URL (optional, if not provided, obtained through service discovery)
            session_key: Session key (e.g., host_id), used for session stickiness. If provided, will use
                         hash-based session stickiness to ensure same session_key always routes to same instance

        Raises:
            ServiceNotFoundError: Service not found
            BusinessError: Connection limit reached
        """
        connection_id = None
        try:
            # ✅ Lazy create lock (in async context)
            if self._websocket_connection_lock is None:
                self._websocket_connection_lock = asyncio.Lock()

            # ✅ Check connection limit
            async with self._websocket_connection_lock:
                current_connections = len(self.active_websocket_connections)
                if current_connections >= self.max_websocket_connections:
                    logger.warning(
                        "WebSocket connection limit reached, rejecting new connection",
                        extra={
                            "service_name": service_name,
                            "current_connections": current_connections,
                            "max_connections": self.max_websocket_connections,
                        },
                    )
                    # Get language preference
                    accept_language = (
                        client_websocket.headers.get("Accept-Language")
                        if hasattr(client_websocket, "headers")
                        else None
                    )
                    locale = parse_accept_language(accept_language)
                    raise BusinessError(
                        message=t(
                            "error.websocket.connection_limit_reached", locale=locale
                        ),
                        message_key="error.websocket.connection_limit_reached",
                        error_code="WEBSOCKET_CONNECTION_LIMIT_REACHED",
                        code=ServiceErrorCodes.GATEWAY_SERVICE_UNAVAILABLE,
                        http_status_code=503,
                        locale=locale,
                    )

                # Generate connection ID and register
                connection_id = f"{service_name}_{id(client_websocket)}"
                self.active_websocket_connections[connection_id] = {
                    "service_name": service_name,
                    "path": path,
                    "created_at": asyncio.get_event_loop().time(),
                }

            # ✅ If session key is provided, use session stickiness to select instance
            if session_key and self.service_discovery:
                try:
                    resolved_service_url = (
                        await self.service_discovery.get_websocket_service_url(
                            service_name, session_key
                        )
                    )
                    logger.info(
                        "Using session stickiness to select WebSocket instance",
                        extra={
                            "service_name": service_name,
                            "session_key": session_key,
                            "selected_url": resolved_service_url,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "Session stickiness selection failed, using default method",
                        extra={
                            "service_name": service_name,
                            "session_key": session_key,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    # Fallback to default method
                    if not service_url:
                        resolved_service_url = await self.get_service_url(service_name)
                    else:
                        resolved_service_url = service_url
            elif not service_url:
                resolved_service_url = await self.get_service_url(service_name)
            else:
                resolved_service_url = service_url

            # Build WebSocket URL (convert http -> ws, add service identifier prefix)
            ws_url = resolved_service_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )

            # ✅ Add service identifier prefix (consistent with HTTP forwarding)
            # Example: service_name="host", path="/ws/host?token=xxx"
            # Result: ws://host-service:8003/api/v1/host/ws/host?token=xxx
            if not path.startswith("/api"):
                full_ws_url = f"{ws_url}/api/v1/{service_name}{path}"
            else:
                full_ws_url = f"{ws_url}{path}"

            logger.info(
                "Forwarding WebSocket connection",
                extra={
                    "service_name": service_name,
                    "path": path,
                    "target_url": full_ws_url,
                    "connection_id": connection_id,
                    "current_connections": len(self.active_websocket_connections),
                },
            )

            # Connect to backend WebSocket
            # ✅ Enable ping/pong heartbeat mechanism to prevent intermediate devices (proxies, load balancers)
            # from closing connections due to inactivity detection
            #
            # Heartbeat configuration notes:
            # 1. Protocol layer heartbeat (ping/pong): Used to keep TCP connection active, prevent intermediate
            #    devices from closing connections
            # 2. Application layer heartbeat (host-service): Agent sends via WebSocket messages, used for business
            #    logic (30-60 second interval)
            # 3. No conflict: Protocol layer heartbeat is low-level mechanism, application layer heartbeat is
            #    business message
            #
            # Configuration parameters:
            # - ping_interval: Send ping every 30 seconds (coordinated with application layer heartbeat 30-60
            #   seconds)
            # - ping_timeout: Ping timeout 10 seconds (if no pong received within 10 seconds, consider connection
            #   disconnected)
            # - close_timeout: Connection close timeout 10 seconds
            #
            # Relationship with host-service heartbeat configuration:
            # - host-service application layer heartbeat timeout: 60 seconds
            # - host-service heartbeat check interval: 10 seconds
            # - Gateway protocol layer heartbeat interval: 30 seconds (less than application layer heartbeat timeout,
            #   ensures connection stays active)
            async with websockets.connect(
                full_ws_url,
                ping_interval=30,  # Send ping every 30 seconds (coordinated with
                # application layer heartbeat 30-60 seconds)
                ping_timeout=10,  # Ping timeout 10 seconds
                close_timeout=10,  # Close timeout 10 seconds
            ) as server_websocket:
                logger.info(
                    "Backend WebSocket connection established",
                    extra={"service_name": service_name, "path": path},
                )

                # Create bidirectional message forwarding tasks
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

                # Wait for either task to complete (indicates connection closed)
                done, pending = await asyncio.wait(
                    [client_to_server, server_to_client],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Cancel other tasks and ensure cleanup
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        ***REMOVED***
                    except Exception as e:
                        logger.warning(
                            "Exception occurred while canceling task",
                            extra={"error": str(e)},
                        )

                # ✅ Ensure WebSocket connection is properly closed
                try:
                    # Check client WebSocket state
                    if hasattr(client_websocket, "client_state"):
                        if client_websocket.client_state != WebSocketState.DISCONNECTED:
                            await client_websocket.close(
                                code=1000, reason="Connection closed"
                            )
                    elif not getattr(client_websocket, "closed", True):
                        # websockets.WebSocketClientProtocol
                        await client_websocket.close()
                except Exception as e:
                    logger.debug(
                        "Error closing client WebSocket", extra={"error": str(e)}
                    )

                try:
                    # Check server WebSocket state
                    if not server_websocket.closed:
                        await server_websocket.close()
                except Exception as e:
                    logger.debug(
                        "Error closing server WebSocket", extra={"error": str(e)}
                    )

                logger.info(
                    "WebSocket connection closed",
                    extra={
                        "service_name": service_name,
                        "path": path,
                        "connection_id": connection_id,
                    },
                )

        except ServiceNotFoundError:
            # ✅ Ensure client WebSocket is closed even in exception cases
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(
                            code=1011, reason="Service not found"
                        )
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***
            raise
        except websockets.exceptions.InvalidURI as e:
            logger.error(
                "Invalid WebSocket URL",
                extra={"service_name": service_name, "path": path, "error": str(e)},
            )
            # ✅ Ensure client WebSocket is closed even in exception cases
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(code=1011, reason="Invalid URI")
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***

            # Get language preference
            accept_language = (
                client_websocket.headers.get("Accept-Language")
                if hasattr(client_websocket, "headers")
                else None
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

            # ✅ Check if authentication failed (403 Forbidden)
            if "HTTP 403" in error_msg or "403 Forbidden" in error_msg:
                logger.warning(
                    "WebSocket authentication failed",
                    extra={
                        "service_name": service_name,
                        "path": path,
                        "error_msg": error_msg,
                    },
                )
                # ✅ Ensure client WebSocket is closed even in exception cases
                try:
                    if hasattr(client_websocket, "client_state"):
                        if client_websocket.client_state != WebSocketState.DISCONNECTED:
                            await client_websocket.close(
                                code=1008, reason="Authentication failed"
                            )
                    elif not getattr(client_websocket, "closed", True):
                        await client_websocket.close()
                except Exception:
                    ***REMOVED***

                # Get language preference
                accept_language = (
                    client_websocket.headers.get("Accept-Language")
                    if hasattr(client_websocket, "headers")
                    else None
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

            # ✅ Check if unauthorized (401 Unauthorized)
            if "HTTP 401" in error_msg or "401 Unauthorized" in error_msg:
                logger.warning(
                    "WebSocket unauthorized",
                    extra={
                        "service_name": service_name,
                        "path": path,
                        "error_msg": error_msg,
                    },
                )
                # ✅ Ensure client WebSocket is closed even in exception cases
                try:
                    if hasattr(client_websocket, "client_state"):
                        if client_websocket.client_state != WebSocketState.DISCONNECTED:
                            await client_websocket.close(
                                code=1008, reason="Unauthorized"
                            )
                    elif not getattr(client_websocket, "closed", True):
                        await client_websocket.close()
                except Exception:
                    ***REMOVED***

                # Get language preference
                accept_language = (
                    client_websocket.headers.get("Accept-Language")
                    if hasattr(client_websocket, "headers")
                    else None
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

            # ✅ Other WebSocket connection errors
            logger.error(
                "WebSocket connection exception",
                extra={
                    "service_name": service_name,
                    "path": path,
                    "error_msg": error_msg,
                },
            )
            # ✅ Ensure client WebSocket is closed even in exception cases
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(
                            code=1011, reason="Connection failed"
                        )
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***

            # Get language preference
            accept_language = (
                client_websocket.headers.get("Accept-Language")
                if hasattr(client_websocket, "headers")
                else None
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
                "WebSocket forwarding exception",
                extra={
                    "service_name": service_name,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            # ✅ Ensure client WebSocket is closed even in exception cases
            try:
                if hasattr(client_websocket, "client_state"):
                    if client_websocket.client_state != WebSocketState.DISCONNECTED:
                        await client_websocket.close(code=1011, reason="Server error")
                elif not getattr(client_websocket, "closed", True):
                    await client_websocket.close()
            except Exception:
                ***REMOVED***

            # Get language preference
            accept_language = (
                client_websocket.headers.get("Accept-Language")
                if hasattr(client_websocket, "headers")
                else None
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
            # ✅ Clean up connection record
            if connection_id and connection_id in self.active_websocket_connections:
                # Ensure lock is created
                if self._websocket_connection_lock is None:
                    self._websocket_connection_lock = asyncio.Lock()

                async with self._websocket_connection_lock:
                    self.active_websocket_connections.pop(connection_id, None)
                    logger.debug(
                        "WebSocket connection record cleaned up",
                        extra={
                            "connection_id": connection_id,
                            "remaining_connections": len(
                                self.active_websocket_connections
                            ),
                        },
                    )

    async def _forward_messages(
        self,
        source: Any,  # FastAPI WebSocket or websockets.WebSocketClientProtocol
        destination: Any,  # websockets.WebSocketClientProtocol or FastAPI WebSocket
        direction: str = "unknown",
    ) -> None:
        """Forward message stream

        Args:
            source: Source WebSocket (may be FastAPI WebSocket or websockets.WebSocketClientProtocol)
            destination: Destination WebSocket (may be FastAPI WebSocket or websockets.WebSocketClientProtocol)
            direction: Forwarding direction (for logging)

        Note: Need to distinguish between FastAPI WebSocket and websockets.WebSocketClientProtocol types
        - FastAPI WebSocket: Use receive_text() / receive_bytes()
        - websockets.WebSocketClientProtocol: Directly iterate with async for or use recv()
        """

        try:
            # Determine source type to decide receive method
            is_fastapi_source = hasattr(source, "receive_text")
            is_fastapi_destination = hasattr(destination, "send_text")

            while True:
                try:
                    message = None

                    # ✅ Receive message - choose method based on source type
                    if is_fastapi_source:
                        # FastAPI WebSocket
                        try:
                            message = await source.receive_text()
                        except RuntimeError:
                            # Not text message, try receiving bytes
                            message = await source.receive_bytes()
                    else:
                        # websockets.WebSocketClientProtocol
                        message = await source.recv()

                    # ✅ Send message - choose method based on destination type
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
                    # Normal close: 1000-1001, 1005 (no status code)
                    if e.code in (1000, 1001, 1005, None):
                        logger.info(
                            "Connection closed normally",
                            extra={"direction": direction, "code": e.code},
                        )
                    else:
                        logger.warning(
                            "Connection closed abnormally",
                            extra={
                                "direction": direction,
                                "code": e.code,
                                "reason": e.reason,
                            },
                        )
                    break
                except WebSocketDisconnect as e:
                    # FastAPI WebSocketDisconnect - client disconnected normally
                    if e.code in (1000, 1001, 1005, None):
                        logger.info(
                            "Client disconnected normally",
                            extra={"direction": direction, "code": e.code},
                        )
                    else:
                        # Get close reason
                        reason = e.reason if hasattr(e, "reason") else "No reason"
                        logger.warning(
                            "Client disconnected abnormally",
                            extra={
                                "direction": direction,
                                "code": e.code,
                                "reason": reason,
                            },
                        )
                    break
                except Exception as e:
                    # Only log other exceptions as errors
                    error_type = type(e).__name__
                    logger.error(
                        "Message forwarding failed",
                        extra={
                            "direction": direction,
                            "error_type": error_type,
                            "error": str(e),
                        },
                    )
                    break

        except websockets.exceptions.ConnectionClosed as e:
            # Outer catch: connection closed normally
            logger.debug(
                "Source connection closed",
                extra={"direction": direction, "code": e.code},
            )
        except Exception as e:
            # Outer catch: forwarding exception
            error_type = type(e).__name__
            logger.error(
                "Forwarding exception",
                extra={
                    "direction": direction,
                    "error_type": error_type,
                    "error": str(e),
                },
            )
        finally:
            # ✅ Ensure destination WebSocket connection is closed
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
                logger.debug(
                    "Error closing destination WebSocket",
                    extra={"direction": direction, "error": str(e)},
                )

            # ✅ Ensure source WebSocket connection is also closed (if possible)
            try:
                if hasattr(source, "close") and not hasattr(source, "receive_text"):
                    # Only non-FastAPI WebSocket needs manual source connection closing
                    # FastAPI WebSocket is managed by framework
                    if hasattr(source, "closed") and not source.closed:
                        await source.close()
            except Exception as e:
                logger.debug(
                    "Error closing source WebSocket",
                    extra={"direction": direction, "error": str(e)},
                )

    async def _handle_backend_http_error_from_response(
        self,
        service_name: str,
        method: str,
        path: str,
        response: Dict[str, Any],
    ) -> None:
        """Handle backend HTTP error from response dict

        Args:
            service_name: Service name
            method: HTTP method
            path: Request path
            response: HTTP response dict (contains status_code, headers, body)

        Raises:
            BusinessError: Business exception
        """
        status_code = response.get("status_code", 500)
        response_body = response.get("body", {})

        # ✅ Add detailed logs for debugging
        logger.debug(
            "Handling backend error response",
            extra={
                "service_name": service_name,
                "status_code": status_code,
                "response_body_type": type(response_body).__name__,
                "response_body_is_empty": (
                    not response_body
                    or (isinstance(response_body, str) and not response_body.strip())
                ),
                "response_body_preview": str(response_body)[:200]
                if response_body
                else None,
            },
        )

        # ✅ Fix: Handle special case of 502 error (Bad Gateway)
        # 502 usually indicates gateway cannot connect to backend service, response body may be empty or invalid
        if status_code == 502:
            # Check if response body is empty or invalid
            if not response_body or (
                isinstance(response_body, str) and not response_body.strip()
            ):
                # 502 and response body is empty, indicates cannot connect to backend service
                # Try to get locale from response headers, use default if not available
                response_headers = response.get("headers", {})
                accept_language = (
                    response_headers.get("Accept-Language")
                    if isinstance(response_headers, dict)
                    else None
                )
                locale = (
                    parse_accept_language(accept_language)
                    if accept_language
                    else "zh_CN"
                )
                error_message = t("error.service.unavailable", locale=locale)
                message_key = "error.service.unavailable"
                error_code = "SERVICE_UNAVAILABLE"
                error_details = {"service_name": service_name, "status_code": 502}
                backend_error_code = status_code  # 502
            else:
                # 502 but has response body, try to parse
                response_data_502: Any = response_body
                if isinstance(response_body, str):
                    try:
                        response_data_502 = json.loads(response_body)
                    except (json.JSONDecodeError, TypeError):
                        response_data_502 = {"message": response_body}

                # Analyze error response format (supports FastAPI's detail format)
                if isinstance(response_data_502, dict):
                    if "detail" in response_data_502 and isinstance(
                        response_data_502["detail"], dict
                    ):
                        error_detail_502 = response_data_502["detail"]
                    else:
                        error_detail_502 = response_data_502
                else:
                    error_detail_502 = {"message": str(response_data_502)}

                # Try to get locale from response
                response_headers = response.get("headers", {})
                accept_language = (
                    response_headers.get("Accept-Language")
                    if isinstance(response_headers, dict)
                    else None
                )
                locale_502 = (
                    parse_accept_language(accept_language)
                    if accept_language
                    else error_detail_502.get("locale", "zh_CN")
                )
                error_message = error_detail_502.get(
                    "message", t("error.service.unavailable", locale=locale_502)
                )
                error_code = error_detail_502.get("error_code", "SERVICE_UNAVAILABLE")
                error_details_raw_502 = error_detail_502.get("details", {})
                # ✅ Extract message_key and locale (for i18n support)
                message_key = error_detail_502.get("message_key")
                locale = error_detail_502.get("locale")
                # Ensure error_details is dict type
                if isinstance(error_details_raw_502, dict):
                    error_details_502: Dict[str, Any] = error_details_raw_502
                else:
                    error_details_502 = {
                        "value": str(error_details_raw_502),
                        "service_name": service_name,
                        "status_code": 502,
                    }
                error_details = error_details_502
                # Preserve backend service's custom error code (code), don't override with HTTP status code
                backend_error_code_raw = error_detail_502.get("code")
                backend_error_code = (
                    backend_error_code_raw
                    if isinstance(backend_error_code_raw, int)
                    else status_code
                )
        else:
            # Other error status codes (4xx, 5xx)
            # Parse response body
            response_data: Any = response_body

            # Try to parse JSON response body
            if isinstance(response_body, str):
                try:
                    response_data = json.loads(response_body)
                except (json.JSONDecodeError, TypeError):
                    response_data = {"message": response_body}

            # Analyze error response format
            if isinstance(response_data, dict):
                # ✅ Prioritize checking if it's unified error response format (ErrorResponse)
                if "error_code" in response_data and "message" in response_data:
                    # Unified error response format
                    error_detail = response_data
                # FastAPI standard error format (detail may be dict or list)
                elif "detail" in response_data:
                    detail_value = response_data["detail"]
                    # ✅ Handle FastAPI validation error format (detail is list)
                    if isinstance(detail_value, list):
                        # FastAPI default validation error format:
                        # {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
                        # Convert to unified format
                        field_errors: Dict[str, str] = {}
                        for error in detail_value:
                            if isinstance(error, dict):
                                field_path = ".".join(
                                    str(loc) for loc in error.get("loc", [])
                                )
                                field_errors[field_path] = error.get(
                                    "msg", "Unknown error"
                                )

                        # Get language preference (from response or use default)
                        locale_for_validation = (
                            response_data.get("locale", "zh_CN")
                            if isinstance(response_data, dict)
                            else "zh_CN"
                        )
                        error_detail = {
                            "message": t(
                                "error.validation", locale=locale_for_validation
                            ),
                            "message_key": "error.validation",
                            "error_code": "VALIDATION_ERROR",
                            "code": 422,
                            "locale": locale_for_validation,
                            "details": {"errors": field_errors},
                        }
                    elif isinstance(detail_value, dict):
                        # detail is dict, may be nested error response
                        error_detail = detail_value
                    else:
                        # detail is other type, use original response
                        error_detail = response_data
                else:
                    # No detail field, use original response
                    error_detail = response_data
            else:
                error_detail = {"message": str(response_data)}

            # ✅ Record backend response's original content (for debugging)
            logger.debug(
                "Backend error response parsing",
                extra={
                    "service_name": service_name,
                    "path": path,
                    "status_code": status_code,
                    "response_data": response_data,
                    "error_detail": error_detail,
                },
            )

            # ✅ Extract key error information, including i18n support fields
            # Provide more friendly default message for 405 error (using i18n)
            if status_code == 405:
                # Try to get locale from response, use default if not available
                locale = error_detail.get("locale", "zh_CN")
                # Check if message_key already exists
                if "message_key" not in error_detail:
                    # Try to extract allowed methods
                    detail_str = str(error_detail.get("message", ""))
                    allowed_match = re.search(
                        r"allowed.*?\[(.*?)\]", detail_str, re.IGNORECASE
                    )
                    if allowed_match:
                        allowed_methods = allowed_match.group(1)
                        message_key = "error.http.method_not_allowed_with_methods"
                        default_message = t(
                            message_key, locale=locale, allowed_methods=allowed_methods
                        )
                    else:
                        message_key = "error.http.method_not_allowed"
                        default_message = t(message_key, locale=locale)
                else:
                    # message_key already exists, use it
                    message_key = error_detail.get("message_key")
                    default_message = error_detail.get("message", "")
            else:
                # Provide i18n support for other errors
                locale_for_error = error_detail.get("locale", "zh_CN")
                default_message = t("error.service.error", locale=locale_for_error)
                message_key = "error.service.error"
                locale = locale_for_error

            error_message = error_detail.get("message", default_message)
            error_code = error_detail.get("error_code", f"BACKEND_{status_code}")
            error_details_raw = error_detail.get("details", {})
            # ✅ Extract message_key and locale (for i18n support)
            # If 405 error doesn't have message_key, use the message_key set above
            if status_code != 405 or "message_key" not in error_detail:
                # For non-405 errors, or 405 error but backend didn't provide message_key, use backend-provided
                message_key = error_detail.get(
                    "message_key", message_key if status_code == 405 else None
                )
                locale = error_detail.get(
                    "locale", locale if status_code == 405 else "zh_CN"
                )

            # ✅ Preserve backend service's custom error code (code), don't override with HTTP status code
            backend_error_code_raw = error_detail.get("code")
            backend_error_code = (
                backend_error_code_raw
                if isinstance(backend_error_code_raw, int)
                else status_code
            )

            # Ensure error_details is dict type
            if isinstance(error_details_raw, dict):
                error_details: Dict[str, Any] = error_details_raw
            else:
                error_details = {"value": str(error_details_raw)}

        # Log detailed error
        logger.warning(
            "Backend service returned business error",
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

        # ✅ Directly ***REMOVED*** through backend service's error information, including code, message,
        # error_code, message_key and locale
        # Use backend service's HTTP status code (e.g., 401), not 502
        raise BusinessError(
            message=error_message,
            code=backend_error_code,  # Use backend's custom error code
            error_code=error_code,
            http_status_code=status_code,  # ✅ Use backend service's HTTP status code (e.g., 401)
            message_key=message_key
            if message_key
            else None,  # ✅ Pass through message_key for i18n support
            locale=locale,  # ✅ Pass through locale for i18n support
            details=error_details,
        )

    async def _handle_backend_http_error(
        self,
        service_name: str,
        method: str,
        path: str,
        http_error: Any,  # type: ignore[arg-type]
    ) -> None:
        """Handle backend service's HTTP error response

        Pass through backend service's error information, preserve original status code and detailed error content
        """
        status_code = http_error.response.status_code

        # Try to parse response body
        # Note: httpx response body can only be read once, use content attribute for multiple access
        try:
            # Read raw content (content attribute can be accessed multiple times)
            response_content = http_error.response.content

            # Add detailed logs for debugging
            logger.debug(
                "Parsing backend response",
                extra={
                    "service_name": service_name,
                    "status_code": status_code,
                    "content_length": len(response_content) if response_content else 0,
                    "has_content": bool(response_content),
                },
            )

            if not response_content:
                # 502 status code and response body is empty, may be connection issue
                if status_code == 502:
                    response_data = {
                        "message": "Backend service unavailable or connection failed",
                        "error_code": "SERVICE_UNAVAILABLE",
                    }
                else:
                    response_data = {
                        "message": f"Backend service returned empty response (status code: {status_code})"
                    }
            else:
                # Try to parse as JSON
                try:
                    response_text = response_content.decode("utf-8")
                    response_data = json.loads(response_text)

                    logger.debug(
                        "Successfully parsed JSON response",
                        extra={
                            "service_name": service_name,
                            "status_code": status_code,
                            "response_keys": list(response_data.keys())
                            if isinstance(response_data, dict)
                            else None,
                        },
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If not JSON, use text content
                    try:
                        response_text = response_content.decode(
                            "utf-8", errors="ignore"
                        )
                        response_data = {"message": response_text}

                        logger.warning(
                            "Response is not JSON format, using text content",
                            extra={
                                "service_name": service_name,
                                "status_code": status_code,
                                "response_preview": response_text[:200]
                                if len(response_text) > 200
                                else response_text,
                            },
                        )
                    except Exception as decode_error:
                        logger.error(
                            "Failed to decode response content",
                            extra={
                                "service_name": service_name,
                                "status_code": status_code,
                                "error": str(decode_error),
                            },
                            exc_info=True,
                        )
                        response_data = {
                            "message": f"Backend service returned invalid response (status code: {status_code})"
                        }
        except Exception as e:
            # If all parsing fails, use default error message
            logger.error(
                "Failed to parse backend response",
                extra={
                    "service_name": service_name,
                    "status_code": status_code,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            response_data = {
                "message": f"Backend service returned invalid response (status code: {status_code})"
            }

        # Analyze error response format
        if isinstance(response_data, dict):
            # ✅ Prioritize checking if it's unified error response format (ErrorResponse)
            if "error_code" in response_data and "message" in response_data:
                # Unified error response format
                error_detail = response_data
            # FastAPI standard error format (detail may be dict or list)
            elif "detail" in response_data:
                detail_value = response_data["detail"]
                # ✅ Handle FastAPI validation error format (detail is list)
                if isinstance(detail_value, list):
                    # FastAPI default validation error format: {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
                    # Convert to unified format
                    field_errors: Dict[str, str] = {}
                    for error in detail_value:
                        if isinstance(error, dict):
                            field_path = ".".join(
                                str(loc) for loc in error.get("loc", [])
                            )
                            field_errors[field_path] = error.get("msg", "Unknown error")

                    # Get language preference (from response or use default)
                    locale_for_validation = (
                        response_data.get("locale", "zh_CN")
                        if isinstance(response_data, dict)
                        else "zh_CN"
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
                    # detail is dict, may be nested error response
                    error_detail = detail_value
                else:
                    # detail is other type, use original response
                    error_detail = response_data
            else:
                # No detail field, use original response
                error_detail = response_data
        else:
            error_detail = {"message": str(response_data)}

        # Extract key error information
        locale_for_error = error_detail.get("locale", "zh_CN")
        error_message = error_detail.get(
            "message", t("error.service.error", locale=locale_for_error)
        )
        error_code = error_detail.get("error_code", f"BACKEND_{status_code}")
        error_details_raw = error_detail.get("details", {})
        # ✅ Extract message_key and locale (for i18n support)
        message_key = error_detail.get("message_key")
        locale = error_detail.get("locale")
        # Preserve backend service's custom error code (code), don't override with HTTP status code
        backend_error_code_raw = error_detail.get("code")
        backend_error_code = (
            backend_error_code_raw
            if isinstance(backend_error_code_raw, int)
            else status_code
        )

        # Ensure error_details is dict type
        if isinstance(error_details_raw, dict):
            error_details: Dict[str, Any] = error_details_raw
        else:
            error_details = {"value": str(error_details_raw)}

        # Log detailed error
        logger.warning(
            "Backend service returned business error",
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

        # Directly ***REMOVED*** through all HTTP status codes
        # Use backend service's custom error code (e.g., 53009), not HTTP status code (502)
        raise BusinessError(
            message=error_message,
            code=backend_error_code,  # Use backend's custom error code
            error_code=error_code,
            http_status_code=status_code,  # HTTP status code remains as original status code
            message_key=message_key,  # ✅ Pass through message_key for i18n support
            locale=locale,  # ✅ Pass through locale for i18n support
            details=error_details,
        )

    async def health_check_service(self, service_name: str) -> bool:
        """Check service health status

        Args:
            service_name: Service name

        Returns:
            Whether service is healthy
        """
        try:
            service_url = self.get_service_url(service_name)
            health_url = f"{service_url}/health"

            response = await self._health_check_client.request(
                method="GET",
                url=health_url,
                retry=False,  # Health check does not enable retry
            )

            is_healthy = response["status_code"] == 200

            logger.debug(
                "Health check completed",
                extra={
                    "service_name": service_name,
                    "is_healthy": is_healthy,
                    "status_code": response["status_code"],
                },
            )

            return is_healthy

        except ServiceNotFoundError:
            logger.warning(
                "Health check failed: Service not found",
                extra={"service_name": service_name},
            )
            return False

        except Exception as e:
            logger.warning(
                "Health check failed",
                extra={
                    "service_name": service_name,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            return False

    async def close(self) -> None:
        """Close proxy service, release resources"""
        if self.http_client:
            await self.http_client.close()

        if self._health_check_client:
            await self._health_check_client.close()

        logger.info("Proxy service closed")


# Global proxy service instance
_proxy_service_instance: Optional[ProxyService] = None


async def get_proxy_service(request: Request) -> ProxyService:
    """Get proxy service instance (HTTP dependency injection)

    Get service discovery instance from request.app.state and create/return ProxyService.

    Args:
        request: FastAPI Request object

    Returns:
        Proxy service instance
    """
    global _proxy_service_instance

    if _proxy_service_instance is None:
        # Get service discovery instance (if exists and not None)
        service_discovery = None
        if hasattr(request.app.state, "service_discovery"):
            service_discovery = request.app.state.service_discovery
            # ✅ Fix: Only consider Nacos is used when service_discovery is not None and Nacos is connected
            if (
                service_discovery is not None
                and service_discovery.nacos_manager is not None
            ):
                logger.info("✅ Proxy service using Nacos service discovery")
            # else:
            #     logger.info("⚠️ Proxy service using fallback address (Nacos not enabled or not connected)")
        # else:
        #     logger.info("⚠️ Proxy service using fallback address (service discovery not configured)")

        http_client_config = getattr(request.app.state, "http_client_config", None)
        health_check_config = getattr(
            request.app.state, "health_check_http_client_config", None
        )
        max_websocket_connections = getattr(
            request.app.state, "max_websocket_connections", 1000
        )

        _proxy_service_instance = ProxyService(
            service_discovery=service_discovery,
            http_client_config=http_client_config,
            health_check_client_config=health_check_config,
            max_websocket_connections=max_websocket_connections,
        )

    return _proxy_service_instance


async def get_proxy_service_ws(websocket: WebSocket) -> ProxyService:
    """Get proxy service instance (WebSocket dependency injection)

    Get service discovery instance from websocket.app.state and create/return ProxyService.

    Args:
        websocket: FastAPI WebSocket object

    Returns:
        Proxy service instance
    """
    global _proxy_service_instance

    if _proxy_service_instance is None:
        # Get service discovery instance (if exists and not None)
        service_discovery = None
        if hasattr(websocket.app.state, "service_discovery"):
            service_discovery = websocket.app.state.service_discovery
            # ✅ Fix: Only consider Nacos is used when service_discovery is not None and Nacos is connected
            if (
                service_discovery is not None
                and service_discovery.nacos_manager is not None
            ):
                logger.info(
                    "✅ Proxy service (WebSocket) using Nacos service discovery"
                )
            else:
                logger.info(
                    "⚠️ Proxy service (WebSocket) using fallback address (Nacos not enabled or not connected)"
                )
        else:
            logger.info(
                "⚠️ Proxy service (WebSocket) using fallback address (service discovery not configured)"
            )

        http_client_config = getattr(websocket.app.state, "http_client_config", None)
        health_check_config = getattr(
            websocket.app.state, "health_check_http_client_config", None
        )
        max_websocket_connections = getattr(
            websocket.app.state, "max_websocket_connections", 1000
        )

        _proxy_service_instance = ProxyService(
            service_discovery=service_discovery,
            http_client_config=http_client_config,
            health_check_client_config=health_check_config,
            max_websocket_connections=max_websocket_connections,
        )

    return _proxy_service_instance
