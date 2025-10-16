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
    jwt_secret_key: str = Field(default="your-secret-key-here", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")

    # 认证服务配置
    auth_service_url: str = Field(default="http://auth-service:8001", description="认证服务URL")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")

    # 超时配置
    request_timeout: int = Field(default=30, description="请求超时时间（秒）")

    # 限流配置
    rate_limit_enabled: bool = Field(default=False, description="是否启用限流")
    rate_limit_requests: int = Field(default=100, description="限流请求数")
    rate_limit_period: int = Field(default=60, description="限流时间窗口（秒）")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# 创建全局配置实例
settings = GatewayConfig()
