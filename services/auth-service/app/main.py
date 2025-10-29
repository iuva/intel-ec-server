"""
Auth Service main application entry point

Provides user authentication, JWT token management, etc.
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
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
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
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware

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

# Create service configuration
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="AUTH_SERVICE_PORT",
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
    """Root path"""
    return {"message": "Auth Service is running"}
