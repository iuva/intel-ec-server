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
app.add_middleware(AuthMiddleware)

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

    # Use lambda to ***REMOVED*** app instance, override default openapi method
    app.openapi = lambda: custom_openapi(app)
    logger.info("✅ Custom OpenAPI aggregation enabled")
except ImportError:
    logger.warning("❌ Failed to import custom_openapi, OpenAPI aggregation disabled")
except Exception as e:
    logger.warning(f"❌ Failed to setup custom OpenAPI: {e}")
