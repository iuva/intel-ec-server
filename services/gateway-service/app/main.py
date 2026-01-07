"""
Gateway Service 主应用入口

提供API网关功能，包括：
- 路由转发
- 负载均衡
- 认证验证
- 限流熔断
"""

import os
import sys

# 使用 try-except 方式处理路径导入
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.v1 import api_router
    from app.middleware.auth_middleware import AuthMiddleware
    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.http_client import HTTPClientConfig
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
    from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.middleware.request_context_middleware import RequestContextMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
    from shared.utils.service_discovery import init_service_discovery
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.v1 import api_router
    from app.middleware.auth_middleware import AuthMiddleware
    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.http_client import HTTPClientConfig
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
    from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.middleware.request_context_middleware import RequestContextMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
    from shared.utils.service_discovery import init_service_discovery

# 加载 .env 文件（如果存在）
try:
    from shared.utils.env_loader import ensure_env_loaded

    ensure_env_loaded()
except ImportError:
    # 如果无法导入，跳过（可能在 Docker 环境中）
    ***REMOVED***

# 配置日志（在应用启动前配置）
# 日志级别会自动从环境变量 LOG_LEVEL 或 DEBUG 读取
service_name = os.getenv("GATEWAY_SERVICE_NAME", "gateway-service")
configure_logger(service_name=service_name)

logger = get_logger(__name__)

# 创建服务配置
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="GATEWAY_SERVICE_PORT",
)

# ✅ 验证 JWT 密钥配置（生产环境必须设置）
jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment == "production":
    if not jwt_secret_key or jwt_secret_key in ("your-secret-key-here", "default_secret_key", ""):
        logger.error("生产环境必须设置 JWT_SECRET_KEY 环境变量，且不能使用默认值")
        raise ValueError(
            "生产环境必须设置 JWT_SECRET_KEY 环境变量。"
            + "请在 .env 文件中设置 JWT_SECRET_KEY，或通过环境变量传递。"
        )
# 开发环境：如果没有设置，使用默认值并警告
elif not jwt_secret_key or jwt_secret_key in ("your-secret-key-here", "default_secret_key", ""):
    logger.warning(
        "JWT_SECRET_KEY 未设置或使用默认值，这在生产环境中是不安全的。"
        + "请设置 JWT_SECRET_KEY 环境变量。"
    )

# ✅ 修复：始终初始化服务发现，支持本地多实例配置
# 即使 Nacos 未启用，也可以使用环境变量配置的多实例（如 HOST_SERVICE_INSTANCES）
# 从环境变量读取负载均衡策略（默认：round_robin 轮询）
load_balance_strategy = os.getenv("LOAD_BALANCE_STRATEGY", "round_robin")

# 初始化服务发现（在 create_service_lifespan 之前）
# 注意：Nacos 管理器将在 lifespan 中初始化（如果启用），这里先初始化服务发现实例
# 如果没有 Nacos，服务发现会使用本地多实例配置（如 HOST_SERVICE_INSTANCES）
service_discovery = init_service_discovery(
    nacos_manager=None,  # Nacos 管理器稍后在 lifespan 中设置
    cache_ttl=30,
    load_balance_strategy=load_balance_strategy,
)

if config.enable_nacos:
    logger.info(
        "✅ 服务发现已初始化（Nacos 已启用，将在 lifespan 中连接）",
        extra={"load_balance_strategy": load_balance_strategy},
    )
else:
    logger.info(
        "✅ 服务发现已初始化（Nacos 未启用，将使用本地多实例配置或后备地址）",
        extra={"load_balance_strategy": load_balance_strategy},
    )

# 创建 FastAPI 应用
app = FastAPI(
    title="Gateway Service",
    description="Intel EC API Gateway",
    version="1.0.0",
    lifespan=create_service_lifespan(config),
)

# 在应用状态中保存服务发现实例，以便在路由中使用
app.state.service_discovery = service_discovery
app.state.http_client_config = HTTPClientConfig(
    timeout=config.http_timeout,
    connect_timeout=config.http_connect_timeout,
    max_keepalive_connections=config.http_max_keepalive_connections,
    max_connections=config.http_max_connections,
    max_retries=config.http_max_retries,
    retry_delay=config.http_retry_delay,
    client_name=f"{config.service_name}_http_client",
)
app.state.health_check_http_client_config = HTTPClientConfig(
    timeout=config.health_check_timeout,
    connect_timeout=config.health_check_connect_timeout,
    max_keepalive_connections=config.health_check_max_keepalive_connections,
    max_connections=config.health_check_max_connections,
    max_retries=config.health_check_max_retries,
    retry_delay=config.health_check_retry_delay,
    client_name=f"{config.service_name}_health_check_client",
)
# ✅ 保存 WebSocket 配置
app.state.max_websocket_connections = int(os.getenv("MAX_WEBSOCKET_CONNECTIONS", "1000"))

# ✅ 在这里立即添加所有中间件（在 lifespan 之前）
# 添加 CORS 中间件
# ⚠️ 注意：当 allow_origins=["*"] 时，allow_credentials 必须为 False
# 如果需要 allow_credentials=True，必须指定具体的域名（如 ["http://localhost:3000"]）
cors_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if cors_allowed_origins == "*":
    # 允许所有来源，但不允许 credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 指定具体域名，允许 credentials
    origins_list = [origin.strip() for origin in cors_allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# ✅ 添加 HTTP 请求/响应日志中间件（记录请求和响应的详细信息）
app.add_middleware(HTTPLoggingMiddleware)
logger.info("✅ HTTP 请求/响应日志中间件已启用")

# 添加 Prometheus 指标收集中间件（根据配置开关）
if config.enable_prometheus:
    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("✅ Prometheus 指标收集中间件已启用")

# ✅ 立即添加统一异常处理中间件（必须在应用启动前添加）
app.add_middleware(UnifiedExceptionMiddleware)

# ✅ 添加请求上下文中间件（为每个请求生成 request_id，用于日志追踪）
app.add_middleware(RequestContextMiddleware)
logger.info("✅ 请求上下文中间件已启用")

# 注意：异常处理器已经在 lifespan 的 startup() 中注册（shared/app/service_factory.py:243-245）
# 所以这里不需要再调用 setup_exception_handling
# 如果调用会导致异常处理器被注册两次，可能产生冲突

# 添加健康检查路由
include_health_routes(app)

# 添加公共 metrics 路由（用于 Prometheus 采集指标，仅在启用时）
if config.enable_prometheus:
    app.include_router(metrics_router)
    logger.info("✅ Prometheus metrics 路由已启用")

# 包含 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Intel EC Gateway Service is running"}
