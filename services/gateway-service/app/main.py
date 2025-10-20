"""
Gateway Service main application entry point

Provides API gateway functionality, including:
- Route forwarding
- Load balancing
- Authentication verification
- Rate limiting and circuit breaking
"""

import os
import sys
<<<<<<< HEAD
=======
from typing import AsyncGenerator, List, Tuple, Union
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

# Use try-except to handle path imports
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
    # If import fails, add project root directory to Python path
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    )
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

# Load .env file (if exists)
try:
    from shared.utils.env_loader import ensure_env_loaded

    ensure_env_loaded()
except ImportError:
    # If unable to import, skip (may be in Docker environment)
    ***REMOVED***

# Configure logging (before application startup)
# Log level will be automatically read from environment variable LOG_LEVEL or DEBUG
service_name = os.getenv("GATEWAY_SERVICE_NAME", "gateway-service")
configure_logger(service_name=service_name)

logger = get_logger(__name__)

# Create service configuration
from app.core.config import settings

# ✅ Restore ServiceConfig for shared lifespan compatibility
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="GATEWAY_SERVICE_PORT",
)

# ✅ Validate JWT secret key configuration (must be set in production environment)
jwt_secret_key = settings.jwt_secret_key
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment == "production":
    if not jwt_secret_key or jwt_secret_key in (
        "your-secret-key-here",
        "default_secret_key",
        "",
    ):
        logger.error(
            "Production environment must set JWT_SECRET_KEY environment variable, and cannot use default value"
        )
        raise ValueError(
            "Production environment must set JWT_SECRET_KEY environment variable. "
            "Please set JWT_SECRET_KEY in .env file, or ***REMOVED*** through environment variable."
        )
# Development environment: if not set, use default value and warn
elif not jwt_secret_key or jwt_secret_key in (
    "your-secret-key-here",
    "default_secret_key",
    "",
):
    logger.warning(
        "JWT_SECRET_KEY not set or using default value, "
        "this is unsafe in production environment. "
        "Please set JWT_SECRET_KEY environment variable."
    )

# ✅ Fix: Always initialize service discovery, support local multi-instance configuration
# Even if Nacos is not enabled, can use multi-instance configured by environment variables
# (such as HOST_SERVICE_INSTANCES)
# Read load balancing strategy from environment variable (default: round_robin)
load_balance_strategy = os.getenv("LOAD_BALANCE_STRATEGY", "round_robin")

# Initialize service discovery (before create_service_lifespan)
# Note: Nacos manager will be initialized in lifespan (if enabled), initialize service discovery instance here first
# If no Nacos, service discovery will use local multi-instance configuration (such as HOST_SERVICE_INSTANCES)
# ✅ Inject configuration from settings
service_discovery = init_service_discovery(
    nacos_manager=None,  # Nacos manager will be set later in lifespan
    cache_ttl=30,
    load_balance_strategy=load_balance_strategy,
    service_config=settings.model_dump(),  # Pass full configuration
)

# Create FastAPI application
app = FastAPI(
    title="Gateway Service",
    description="Intel EC API Gateway",
    version="1.0.0",
    lifespan=create_service_lifespan(config),
)

<<<<<<< HEAD
# Save service discovery instance in application state for use in routes
app.state.service_discovery = service_discovery
app.state.http_client_config = HTTPClientConfig(
    timeout=settings.http_timeout,
    connect_timeout=settings.http_connect_timeout,
    max_keepalive_connections=settings.http_max_keepalive_connections,
    max_connections=settings.http_max_connections,
    max_retries=settings.http_max_retries,
    retry_delay=settings.http_retry_delay,
    client_name=f"{settings.service_name}_http_client",
)
app.state.health_check_http_client_config = HTTPClientConfig(
    timeout=settings.health_check_timeout,
    connect_timeout=settings.health_check_connect_timeout,
    max_keepalive_connections=settings.health_check_max_keepalive_connections,
    max_connections=settings.health_check_max_connections,
    max_retries=settings.health_check_max_retries,
    retry_delay=settings.health_check_retry_delay,
    client_name=f"{settings.service_name}_health_check_client",
)
# ✅ Save WebSocket configuration
app.state.max_websocket_connections = settings.websocket_max_connections

# ✅ Add all middleware here immediately (before lifespan)
# Add CORS middleware
# ⚠️ Note: When allow_origins=["*"], allow_credentials must be False
# If need allow_credentials=True, must specify specific domain (such as ["http://localhost:3000"])
cors_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if cors_allowed_origins == "*":
    # Allow all origins, but do not allow credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Specify specific domain, allow credentials
    origins_list = [origin.strip() for origin in cors_allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add authentication middleware
=======
# ============================================================================
# 中间件注册（按照注册顺序）
# ============================================================================
# 注意：FastAPI 中间件的执行顺序与注册顺序相反
# 注册顺序：CORS → Metrics → Auth
# 实际执行顺序（请求处理）：Auth → Metrics → CORS → 路由处理
# 实际执行顺序（响应处理）：路由处理 → CORS → Metrics → Auth
# ============================================================================

logger.info("=" * 80)
logger.info("开始注册中间件...")
logger.info("=" * 80)

# 1. 添加 CORS 中间件（最后执行）
logger.info("注册 CORS 中间件...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("✓ CORS 中间件注册成功")

# 2. 添加指标收集中间件（倒数第二执行）
logger.info("注册 Prometheus 指标收集中间件...")
try:
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware

    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("✓ Prometheus 指标收集中间件注册成功")
except Exception as e:
    logger.warning(f"✗ 添加指标收集中间件失败: {e!s}")

# 3. 添加认证中间件（最先执行 - 在所有路由处理之前）
logger.info("注册认证中间件...")
logger.info("认证中间件配置:")

# 定义公开路径（与 AuthMiddleware 中的配置保持一致）
public_paths = {
    "/",
    "/health",
    "/health/detailed",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/admin/login",
    "/api/v1/auth/device/login",
    "/api/v1/auth/logout",
}

logger.info(f"  - 公开路径数量: {len(public_paths)}")
logger.info("  - 公开路径列表:")
for path in sorted(public_paths):
    logger.info(f"    • {path}")

>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
app.add_middleware(AuthMiddleware)
logger.info("✓ 认证中间件注册成功")

logger.info("=" * 80)
logger.info("中间件注册完成")
logger.info("中间件执行顺序（请求处理）：Auth → Metrics → CORS → 路由")
logger.info("=" * 80)

# ✅ Add HTTP request/response logging middleware (records detailed information of requests and responses)
app.add_middleware(HTTPLoggingMiddleware)
logger.info("✅ HTTP request/response logging middleware enabled")

# Add Prometheus metrics collection middleware (based on configuration switch)
if config.enable_prometheus:
    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("✅ Prometheus metrics collection middleware enabled")

# ✅ Add unified exception handling middleware immediately (must be added before application startup)
app.add_middleware(UnifiedExceptionMiddleware)

# ✅ Add request context middleware (generates request_id for each request, used for log tracking)
app.add_middleware(RequestContextMiddleware)
logger.info("✅ Request context middleware enabled")

# Note: Exception handlers have already been registered in lifespan startup() (shared/app/service_factory.py:243-245)
# So no need to call setup_exception_handling here
# If called, it will cause exception handlers to be registered twice, may cause conflicts

# Add health check routes
include_health_routes(app)

# Add public metrics route (for Prometheus to collect metrics, only when enabled)
if config.enable_prometheus:
    app.include_router(metrics_router)
    logger.info("✅ Prometheus metrics route enabled")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root path"""
    return {"message": "Intel EC Gateway Service is running"}


# ✅ Integrate custom OpenAPI aggregation
try:
    from app.core.openapi import custom_openapi

<<<<<<< HEAD
    # Use lambda to ***REMOVED*** app instance, override default openapi method
    app.openapi = lambda: custom_openapi(app)
    logger.info("✅ Custom OpenAPI aggregation enabled")
except ImportError:
    logger.warning("❌ Failed to import custom_openapi, OpenAPI aggregation disabled")
except Exception as e:
    logger.warning(f"❌ Failed to setup custom OpenAPI: {e}")
=======

@app.get("/health/detailed", response_model=SuccessResponse)
async def detailed_health_check():
    """详细健康检查端点（使用并发检查提高性能）"""
    health_status = {
        "service": "gateway-service",
        "status": "healthy",
        "checks": {
            "nacos": "connected" if nacos_manager else "disconnected",
        },
    }

    # 检查后端服务健康状态
    from app.services.proxy_service import get_proxy_service

    proxy_service = get_proxy_service()

    async def check_service_health(service_name: str) -> Tuple[str, str]:
        """检查单个服务健康状态

        Args:
            service_name: 服务名称

        Returns:
            (服务名称, 健康状态) 元组
        """
        try:
            is_healthy = await proxy_service.health_check_service(service_name)
            return (service_name, "healthy" if is_healthy else "unhealthy")
        except Exception:
            return (service_name, "unknown")

    # 使用并发检查所有后端服务
    service_names = list(proxy_service.service_routes.keys())
    if service_names:
        # 并发执行所有健康检查
        health_check_tasks = [check_service_health(name) for name in service_names]
        results: List[Union[Tuple[str, str], BaseException]] = await asyncio.gather(
            *health_check_tasks, return_exceptions=True
        )

        # 处理结果
        backend_services = {}
        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"健康检查异常: {result!s}")
                continue
            # result 是 Tuple[str, str]
            service_name, status = result
            backend_services[service_name] = status

        health_status["checks"]["backend_services"] = backend_services

        # 判断整体健康状态
        all_healthy = all(status == "healthy" for status in backend_services.values()) and (nacos_manager is not None)
        health_status["status"] = "healthy" if all_healthy else "degraded"
    else:
        health_status["checks"]["backend_services"] = {}

    return SuccessResponse(
        data=health_status,
        message="详细健康检查完成",
    )


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""

    return get_metrics_response()


def setup_uvicorn_logging():
    """配置 uvicorn 日志处理器"""
    import logging
    import threading
    import time

    from loguru import logger as loguru_logger

    # 禁用uvicorn的默认日志处理器
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()

    def replace_uvicorn_handlers():
        """在uvicorn启动后替换其处理器"""
        time.sleep(1)  # 等待uvicorn启动

        class UvicornLoguruHandler(logging.Handler):
            """将 uvicorn 日志转发到 loguru"""

            def emit(self, record):
                if record.name.startswith("uvicorn"):
                    bound_logger = loguru_logger.bind(
                        name=record.name,
                        function=record.funcName or "unknown",
                        line=record.lineno or 0,
                    )
                    bound_logger.log(record.levelname, record.getMessage())

        handler = UvicornLoguruHandler()

        # 替换所有uvicorn相关logger的处理器
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            specific_logger = logging.getLogger(logger_name)
            specific_logger.handlers.clear()
            specific_logger.addHandler(handler)
            specific_logger.setLevel(logging.INFO)

    # 启动处理器替换线程
    threading.Thread(target=replace_uvicorn_handlers, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    # 配置 uvicorn 日志
    setup_uvicorn_logging()

    # 运行 uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("SERVICE_PORT", "8000")),
        log_level="info",
    )


# 捕获所有未匹配的请求，返回统一格式的404错误
# 这个路由必须在最后注册，确保最低优先级
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    operation_id="catch_all_root_handler",
)
async def catch_all_root_handler(request: Request, path: str):
    """捕获所有未匹配的根级别请求，返回统一格式的404错误

    这个路由处理器会捕获所有没有被其他路由匹配的请求，
    统一返回符合项目规范的404错误响应格式。
    """
    from fastapi.responses import JSONResponse

    from shared.common.response import ErrorResponse

    logger.warning(
        f"未找到路由: {request.method} /{path}",
        extra={
            "method": request.method,
            "path": path,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else "unknown",
        },
    )

    # 检查是否是API路径但版本不正确
    error_message = "API版本不存在" if path.startswith("api/") else "请求的资源不存在"

    # 返回统一格式的404错误响应（移除 available_endpoints）
    error_response = ErrorResponse(
        code=404,
        message=error_message,
        error_code="RESOURCE_NOT_FOUND",
        details={
            "method": request.method,
            "path": f"/{path}",
        },
    )

    return JSONResponse(status_code=404, content=error_response.model_dump())
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
