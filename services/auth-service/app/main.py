"""
Auth Service main application entry point

<<<<<<< HEAD
Provides user authentication, JWT token management, etc.
=======
提供用户认证、JWT令牌管理等功能
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Use try-except approach to handle path imports
try:
    from app.api.v1 import api_router
    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
    from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.middleware.request_context_middleware import RequestContextMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
except ImportError:
    # If import fails, add project root directory to Python path
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from app.api.v1 import api_router
    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
    from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.middleware.request_context_middleware import RequestContextMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router

# Load .env file (if exists)
try:
    from shared.utils.env_loader import ensure_env_loaded

    ensure_env_loaded()
except ImportError:
    # If import fails, skip (may be in Docker environment)
    ***REMOVED***

# Configure logging (before application startup)
# Log level will be automatically read from environment variables LOG_LEVEL or DEBUG
service_name = os.getenv("AUTH_SERVICE_NAME", "auth-service")
configure_logger(service_name=service_name)

logger = get_logger(__name__)

<<<<<<< HEAD
# Create service configuration
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="AUTH_SERVICE_PORT",
=======
# Nacos管理器
nacos_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    global nacos_manager

    # 启动时执行
    service_name = os.getenv("SERVICE_NAME", "auth-service")
    service_port = int(os.getenv("SERVICE_PORT", "8001"))
    service_ip = os.getenv("SERVICE_IP", "172.20.0.101")
    nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", "172.20.0.12:8848")

    logger.info(f"{service_name} 服务启动中... 端口: {service_port}")

    # 初始化数据库连接
    # 从环境变量构建 MariaDB URL
    mariadb_host = os.getenv("MARIADB_HOST", "mariadb")
    mariadb_port = os.getenv("MARIADB_PORT", "3306")
    mariadb_user = os.getenv("MARIADB_USER", "intel_user")
    mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
    mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

    # URL编码密码中的特殊字符
    from urllib.parse import quote_plus

    mariadb_***REMOVED***word_encoded = quote_plus(mariadb_***REMOVED***word)

    mariadb_url = (
        f"mysql+aiomysql://{mariadb_user}:{mariadb_***REMOVED***word_encoded}@{mariadb_host}:{mariadb_port}/{mariadb_database}"
    )

    # 从环境变量构建 Redis URL
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
    redis_db = os.getenv("REDIS_DB", "1")

    if redis_***REMOVED***word:
        redis_***REMOVED***word_encoded = quote_plus(redis_***REMOVED***word)
        redis_url = f"redis://:{redis_***REMOVED***word_encoded}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    await init_databases(
        mariadb_url=mariadb_url,
        redis_url=redis_url,
    )

    # 初始化监控指标
    init_metrics(
        service_name="auth-service",
        service_version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "production"),
    )

    # Jaeger 追踪已在应用创建时初始化

    # 初始化Nacos（从环境变量读取认证信息）
    nacos_username = os.getenv("NACOS_USERNAME", "nacos")
    nacos_***REMOVED***word = os.getenv("NACOS_PASSWORD", "nacos")
    nacos_namespace = os.getenv("NACOS_NAMESPACE", "public")
    nacos_group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")

    try:
        nacos_manager = NacosManager(
            server_addresses=nacos_server_addr.replace("http://", ""),
            namespace=nacos_namespace,
            group=nacos_group,
            username=nacos_username,
            ***REMOVED***word=nacos_***REMOVED***word,
        )

        # 注册服务
        success = await nacos_manager.register_service(
            service_name=service_name,
            ip=service_ip,
            port=service_port,
            ephemeral=True,
            metadata={
                "version": "1.0.0",
                "environment": "production",
                "service_type": "auth",
            },
        )

        if success:
            # 启动心跳检测
            heartbeat_task = asyncio.create_task(
                nacos_manager.start_heartbeat(
                    service_name=service_name,
                    ip=service_ip,
                    port=service_port,
                    interval=5,
                )
            )
            # 存储任务引用以避免垃圾回收
            app.state.heartbeat_task = heartbeat_task
            logger.info(f"{service_name} 服务注册成功")
        else:
            logger.error(f"{service_name} 服务注册失败")

    except Exception as e:
        logger.error(f"Nacos初始化异常: {e!s}")

    logger.info(f"{service_name} 服务启动完成")

    yield

    # 关闭时执行
    logger.info(f"{service_name} 服务关闭中...")

    try:
        if nacos_manager:
            nacos_manager.stop_heartbeat()
            logger.info("Nacos心跳检测已停止")
    except Exception as e:
        logger.error(f"Nacos心跳检测停止异常: {e!s}")

    # 关闭数据库连接
    await close_databases()

    logger.info(f"{service_name} 服务关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="Auth Service API",
    description="认证服务 - 提供用户认证、JWT令牌管理等功能",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
)

# Create FastAPI application
app = FastAPI(
    title="Auth Service",
    description="User authentication and JWT token management service",
    version="1.0.0",
    lifespan=create_service_lifespan(config),
)

# ✅ Add all middleware immediately here (before lifespan)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Add HTTP request/response logging middleware (records detailed request and response information)
app.add_middleware(HTTPLoggingMiddleware)
logger.info("✅ HTTP request/response logging middleware enabled")

# Add Prometheus metrics collection middleware (according to configuration switch)
if config.enable_prometheus:
    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("✅ Prometheus metrics collection middleware enabled")

# ✅ Add unified exception handling middleware immediately (must be added before application startup)
app.add_middleware(UnifiedExceptionMiddleware)

# ✅ Add request context middleware (generates request_id for each request, for log tracing)
app.add_middleware(RequestContextMiddleware)
logger.info("✅ Request context middleware enabled")

# ❌ Don't call jaeger_manager.instrument_app(app) here
# Application has already started, cannot add Jaeger middleware anymore

# Note: Exception handler has already been registered in lifespan's startup() (shared/app/service_factory.py:243-245)
# So there's no need to call setup_exception_handling here
# Calling it would cause the exception handler to be registered twice, possibly causing conflicts

# Add health check routes
include_health_routes(app)

# Add public metrics routes (for Prometheus metric collection, only when enabled)
if config.enable_prometheus:
    app.include_router(metrics_router)
    logger.info("✅ Prometheus metrics routes enabled")

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
<<<<<<< HEAD
    """Root path"""
    return {"message": "Auth Service is running"}
=======
    """根路径"""
    from shared.common.response import SuccessResponse

    return SuccessResponse(
        data={
            "service": "auth-service",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        },
        message="Auth Service 运行正常",
    )


if __name__ == "__main__":
    import logging
    import threading
    import time

    from loguru import logger
    import uvicorn

    # 禁用uvicorn的默认日志处理器
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()

    # 运行uvicorn
    def replace_uvicorn_handlers():
        """在uvicorn启动后替换其处理器"""
        time.sleep(1)  # 等待uvicorn启动

        class UvicornLoguruHandler(logging.Handler):
            def emit(self, record):
                if record.name.startswith("uvicorn"):
                    loguru_logger = logger.bind(
                        name=record.name,
                        function=record.funcName or "unknown",
                        line=record.lineno or 0,
                    )
                    loguru_logger.log(record.levelname, record.getMessage())

        handler = UvicornLoguruHandler()

        # 替换所有uvicorn相关logger的处理器
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            specific_logger = logging.getLogger(logger_name)
            specific_logger.handlers.clear()
            specific_logger.addHandler(handler)
            specific_logger.setLevel(logging.INFO)

    # 启动处理器替换线程
    threading.Thread(target=replace_uvicorn_handlers, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=8001)
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
