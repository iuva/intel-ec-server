"""
Gateway Service 配置模块
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class GatewayConfig(BaseSettings):
    """网关服务配置类"""

    # 基础服务配置
    service_name: str = Field(default="gateway-service", description="服务名称")
    service_port: int = Field(default=8000, description="服务端口")
    service_ip: str = Field(default="172.20.0.100", description="服务IP")

    # Nacos 配置
    nacos_server_addr: str = Field(default="http://intel-nacos:8848", description="Nacos服务器地址")
    nacos_namespace: str = Field(default="public", description="Nacos命名空间")
    nacos_group: str = Field(default="DEFAULT_GROUP", description="Nacos分组")

    # Redis 配置
    redis_url: str = Field(default="redis://intel-redis:6379/0", description="Redis连接URL")

    # JWT 配置
    jwt_secret_key: str = Field(
        default="", description="JWT密钥（生产环境必须设置，否则将抛出异常）"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")

    # 认证服务配置
    auth_service_url: str = Field(default="http://auth-service:8001", description="认证服务URL")
    auth_service_host: str = Field(default="auth-service", description="认证服务主机名（用于本地开发时覆盖）")
    auth_service_port: int = Field(default=8001, description="认证服务端口")

    # 认证中间件 HTTP 客户端配置
    auth_middleware_timeout: float = Field(default=10.0, description="认证中间件请求超时时间（秒）")
    auth_middleware_connect_timeout: float = Field(default=5.0, description="认证中间件连接超时时间（秒）")

    # 服务端口映射（用于服务发现后备地址）
    service_port_auth: int = Field(default=8001, description="认证服务端口")
    service_port_host: int = Field(default=8003, description="主机服务端口")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")

    # 超时配置
    request_timeout: int = Field(default=30, description="请求超时时间（秒）")

    # 限流配置
    rate_limit_enabled: bool = Field(default=False, description="是否启用限流")
    rate_limit_requests: int = Field(default=100, description="限流请求数")
    rate_limit_period: int = Field(default=60, description="限流时间窗口（秒）")

    # HTTP 客户端配置（优化：支持2000并发）
    http_timeout: float = Field(default=30.0, description="网关转发请求超时时间（秒）")
    http_connect_timeout: float = Field(default=10.0, description="网关转发连接超时时间（秒）")
    http_max_keepalive_connections: int = Field(default=1000, description="HTTP 客户端保持活动连接数")
    http_max_connections: int = Field(default=2500, description="HTTP 客户端最大连接数")
    http_max_retries: int = Field(default=0, description="HTTP 客户端最大重试次数")
    http_retry_delay: float = Field(default=0.0, description="HTTP 客户端重试延迟（秒）")

    # 健康检查 HTTP 客户端配置
    health_check_timeout: float = Field(default=5.0, description="健康检查请求超时时间（秒）")
    health_check_connect_timeout: float = Field(default=2.0, description="健康检查连接超时时间（秒）")
    health_check_max_keepalive_connections: int = Field(default=5, description="健康检查保持活动连接数")
    health_check_max_connections: int = Field(default=10, description="健康检查最大连接数")
    health_check_max_retries: int = Field(default=1, description="健康检查最大重试次数")
    health_check_retry_delay: float = Field(default=0.0, description="健康检查重试延迟（秒）")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# 创建全局配置实例
settings = GatewayConfig()
