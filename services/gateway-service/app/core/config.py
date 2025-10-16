"""
Gateway Service Configuration Module

Provides configuration management for the gateway service, using Pydantic BaseModel for type validation and environment variable loading.
"""

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel


class GatewaySettings(BaseModel):
    """Gateway Service Configuration

    Contains configuration items for service discovery, HTTP client, WebSocket connection, etc.
    Supports exporting as dictionary via model_dump() for injection into service discovery modules.
    """

    # Basic Service Configuration
    service_name: str = "gateway-service"
    service_port: int = 8000
    deploy_mode: str = "local"  # "local" or "docker"

    # Service Host Configuration (for service discovery)
    gateway_service_host: str = "127.0.0.1"
    auth_service_host: str = "127.0.0.1"
    host_service_host: str = "127.0.0.1"

    # Service Port Configuration
    auth_service_port: int = 8001
    host_service_port: int = 8003

    # JWT Configuration
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"

    # HTTP Client Configuration
    http_timeout: float = 15.0
    http_connect_timeout: float = 5.0
    http_max_keepalive_connections: int = 20
    http_max_connections: int = 100
    http_max_retries: int = 0
    http_retry_delay: float = 0.0

    # Health Check HTTP Client Configuration
    health_check_timeout: float = 5.0
    health_check_connect_timeout: float = 2.0
    health_check_max_keepalive_connections: int = 5
    health_check_max_connections: int = 10
    health_check_max_retries: int = 1
    health_check_retry_delay: float = 0.0

    # WebSocket Configuration
    websocket_max_connections: int = 1000

    # Auth Middleware Configuration
    auth_service_url: str = "http://127.0.0.1:8001"
    auth_middleware_timeout: float = 10.0
    auth_middleware_connect_timeout: float = 5.0

    # Host Service API Configuration
    host_service_url: str = "http://127.0.0.1:8003"

    # Service Instance Lists (Used for documentation aggregation)
    auth_service_urls: Any = []  # List[str]
    host_service_urls: Any = []  # List[str]

    # Service Name Mapping (short name -> full name)
    service_name_map: Dict[str, str] = {}

    @classmethod
    def from_env(cls) -> "GatewaySettings":
        """Load configuration from environment variables"""

        def parse_bool(value: Optional[str], default: bool = False) -> bool:
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes", "on")

        def parse_int(value: Optional[str], default: int) -> int:
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        def parse_float(value: Optional[str], default: float) -> float:
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                return default

        # Detect deployment mode
        is_docker = (
            os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") is not None
        )
        deploy_mode = "docker" if is_docker else "local"

        # Service Host Configuration
        if is_docker:
            gateway_host = os.getenv("GATEWAY_SERVICE_IP", "gateway-service")
            auth_host = os.getenv("SERVICE_HOST_AUTH", "auth-service")
            host_host = os.getenv("SERVICE_HOST_HOST", "host-service")
        else:
            gateway_host = os.getenv("GATEWAY_SERVICE_IP", "127.0.0.1")
            auth_host = os.getenv("SERVICE_HOST_AUTH", "127.0.0.1")
            host_host = os.getenv("SERVICE_HOST_HOST", "127.0.0.1")

        return cls(
            # Basic Configuration
            service_name=os.getenv("GATEWAY_SERVICE_NAME", "gateway-service"),
            service_port=parse_int(os.getenv("GATEWAY_SERVICE_PORT"), 8000),
            deploy_mode=deploy_mode,
            # Service Hosts
            gateway_service_host=gateway_host,
            auth_service_host=auth_host,
            host_service_host=host_host,
            # Service Ports
            auth_service_port=parse_int(os.getenv("AUTH_SERVICE_PORT"), 8001),
            host_service_port=parse_int(os.getenv("HOST_SERVICE_PORT"), 8003),
            # JWT
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", ""),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            # HTTP Client
            http_timeout=parse_float(os.getenv("HTTP_TIMEOUT"), 15.0),
            http_connect_timeout=parse_float(os.getenv("HTTP_CONNECT_TIMEOUT"), 5.0),
            http_max_keepalive_connections=parse_int(
                os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS"), 20
            ),
            http_max_connections=parse_int(os.getenv("HTTP_MAX_CONNECTIONS"), 100),
            http_max_retries=parse_int(os.getenv("HTTP_MAX_RETRIES"), 0),
            http_retry_delay=parse_float(os.getenv("HTTP_RETRY_DELAY"), 0.0),
            # Health Check
            health_check_timeout=parse_float(os.getenv("HEALTH_CHECK_TIMEOUT"), 5.0),
            health_check_connect_timeout=parse_float(
                os.getenv("HEALTH_CHECK_CONNECT_TIMEOUT"), 2.0
            ),
            health_check_max_keepalive_connections=parse_int(
                os.getenv("HEALTH_CHECK_MAX_KEEPALIVE_CONNECTIONS"), 5
            ),
            health_check_max_connections=parse_int(
                os.getenv("HEALTH_CHECK_MAX_CONNECTIONS"), 10
            ),
            health_check_max_retries=parse_int(
                os.getenv("HEALTH_CHECK_MAX_RETRIES"), 1
            ),
            health_check_retry_delay=parse_float(
                os.getenv("HEALTH_CHECK_RETRY_DELAY"), 0.0
            ),
            # WebSocket
            websocket_max_connections=parse_int(
                os.getenv("WEBSOCKET_MAX_CONNECTIONS"), 1000
            ),
            # Auth Middleware
            auth_service_url=f"http://{auth_host}:{parse_int(os.getenv('AUTH_SERVICE_PORT'), 8001)}",
            auth_middleware_timeout=parse_float(
                os.getenv("AUTH_MIDDLEWARE_TIMEOUT"), 10.0
            ),
            auth_middleware_connect_timeout=parse_float(
                os.getenv("AUTH_MIDDLEWARE_CONNECT_TIMEOUT"), 5.0
            ),
            # Host Service API
            host_service_url=f"http://{host_host}:{parse_int(os.getenv('HOST_SERVICE_PORT'), 8003)}",
            # Service Instance Lists (Support Multi-Instance Aggregation)
            auth_service_urls=(
                [
                    f"http://{x.strip()}"
                    for x in os.getenv("AUTH_SERVICE_INSTANCES").split(",")
                ]
                if os.getenv("AUTH_SERVICE_INSTANCES")
                else [
                    f"http://{auth_host}:{parse_int(os.getenv('AUTH_SERVICE_PORT'), 8001)}"
                ]
            ),
            host_service_urls=(
                [
                    f"http://{x.strip()}"
                    for x in os.getenv("HOST_SERVICE_INSTANCES").split(",")
                ]
                if os.getenv("HOST_SERVICE_INSTANCES")
                else [
                    f"http://{host_host}:{parse_int(os.getenv('HOST_SERVICE_PORT'), 8003)}"
                ]
            ),
            # Service Name Mapping
            service_name_map={
                "auth": "auth-service",
                "host": "host-service",
                "gateway": "gateway-service",
            },
        )


# Global settings instance
settings = GatewaySettings.from_env()
