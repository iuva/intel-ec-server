"""
Gateway Service configuration module
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class GatewayConfig(BaseSettings):
    """Gateway service configuration class"""

    # Basic service configuration
    service_name: str = Field(default="gateway-service", description="Service name")
    service_port: int = Field(default=8000, description="Service port")
    service_ip: str = Field(default="172.20.0.100", description="Service IP")

    # Nacos configuration
    nacos_server_addr: str = Field(default="http://intel-nacos:8848", description="Nacos server address")
    nacos_namespace: str = Field(default="public", description="Nacos namespace")
    nacos_group: str = Field(default="DEFAULT_GROUP", description="Nacos group")

    # Redis configuration
    redis_url: str = Field(default="redis://intel-redis:6379/0", description="Redis connection URL")

    # JWT configuration
    jwt_secret_key: str = Field(
        default="", description="JWT secret key (must be set in production, otherwise will raise exception)"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")

    # Authentication service configuration
    auth_service_url: str = Field(default="http://auth-service:8001", description="Authentication service URL")
    auth_service_host: str = Field(
        default="auth-service", description="Authentication service hostname (for local development override)"
    )
    auth_service_port: int = Field(default=8001, description="Authentication service port")

    # Authentication middleware HTTP client configuration
    auth_middleware_timeout: float = Field(
        default=10.0, description="Authentication middleware request timeout (seconds)"
    )
    auth_middleware_connect_timeout: float = Field(
        default=5.0, description="Authentication middleware connection timeout (seconds)"
    )

    # Service port mapping (for service discovery fallback address)
    service_port_auth: int = Field(default=8001, description="Authentication service port")
    service_port_host: int = Field(default=8003, description="Host service port")

    # Logging configuration
    log_level: str = Field(default="INFO", description="Log level")

    # Timeout configuration
    request_timeout: int = Field(default=30, description="Request timeout (seconds)")

    # Rate limiting configuration
    rate_limit_enabled: bool = Field(default=False, description="Whether rate limiting is enabled")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests")
    rate_limit_period: int = Field(default=60, description="Rate limit time window (seconds)")

    # HTTP client configuration (optimized: supports 2000 concurrent connections)
    http_timeout: float = Field(default=30.0, description="Gateway forwarding request timeout (seconds)")
    http_connect_timeout: float = Field(default=10.0, description="Gateway forwarding connection timeout (seconds)")
    http_max_keepalive_connections: int = Field(default=1000, description="HTTP client keepalive connections")
    http_max_connections: int = Field(default=2500, description="HTTP client maximum connections")
    http_max_retries: int = Field(default=0, description="HTTP client maximum retry count")
    http_retry_delay: float = Field(default=0.0, description="HTTP client retry delay (seconds)")

    # Health check HTTP client configuration
    health_check_timeout: float = Field(default=5.0, description="Health check request timeout (seconds)")
    health_check_connect_timeout: float = Field(default=2.0, description="Health check connection timeout (seconds)")
    health_check_max_keepalive_connections: int = Field(default=5, description="Health check keepalive connections")
    health_check_max_connections: int = Field(default=10, description="Health check maximum connections")
    health_check_max_retries: int = Field(default=1, description="Health check maximum retry count")
    health_check_retry_delay: float = Field(default=0.0, description="Health check retry delay (seconds)")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Create global configuration instance
settings = GatewayConfig()
