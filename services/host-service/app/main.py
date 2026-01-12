"""
Host Service main application entry point

Provides host management and WebSocket real-time communication functionality
"""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router

# Use try-except to handle path imports
try:
    from app.services.case_timeout_task import get_case_timeout_task_service
    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
    from shared.middleware.http_logging_middleware import HTTPLoggingMiddleware
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.middleware.request_context_middleware import RequestContextMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
except ImportError:
    # If import fails, add project root directory to Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from app.services.case_timeout_task import get_case_timeout_task_service
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
    # If cannot import, skip (may be in Docker environment)
    ***REMOVED***

# Configure logger (before application startup)
# Log level is automatically read from environment variable LOG_LEVEL or DEBUG
service_name = os.getenv("HOST_SERVICE_NAME", "host-service")
configure_logger(service_name=service_name)

logger = get_logger(__name__)

# Create service configuration
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="HOST_SERVICE_PORT",
)


# Scheduled task startup and shutdown handlers
async def startup_case_timeout_task(app):
    """Start Case timeout detection scheduled task

    Controlled by environment variable ENABLE_CASE_TIMEOUT_TASK, disabled by default.

    Args:
        app: FastAPI application instance (lifespan handler must accept this parameter)
    """
    # ✅ Check environment variable switch, disabled by default
    enable_task = os.getenv("ENABLE_CASE_TIMEOUT_TASK", "false").lower() in ("true", "1", "yes", "on")

    if not enable_task:
        logger.info(
            "Case timeout detection scheduled task is disabled (via ENABLE_CASE_TIMEOUT_TASK=false)",
            extra={"enable_case_timeout_task": enable_task},
        )
        return

    logger.info(
        "Case timeout detection scheduled task is enabled (via ENABLE_CASE_TIMEOUT_TASK=true)",
        extra={"enable_case_timeout_task": enable_task},
    )

    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.start()


async def shutdown_case_timeout_task(app):
    """Stop Case timeout detection scheduled task

    Args:
        app: FastAPI application instance (lifespan handler must accept this parameter)
    """
    # ✅ Check environment variable switch, if disabled then no need to stop
    enable_task = os.getenv("ENABLE_CASE_TIMEOUT_TASK", "false").lower() in ("true", "1", "yes", "on")

    if not enable_task:
        return

    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.stop()


# Create FastAPI application (integrated with scheduled task lifecycle)
app = FastAPI(
    title="Host Service",
    description="Host management and WebSocket real-time communication service",
    version="1.0.0",
    lifespan=create_service_lifespan(
        config,
        startup_handlers=[startup_case_timeout_task],
        shutdown_handlers=[shutdown_case_timeout_task],
    ),
)

# ✅ Add all middleware here immediately (before lifespan)
# Add CORS middleware
# ⚠️ Note: When allow_origins=["*"], allow_credentials must be False
# If allow_credentials=True is needed, must specify specific domains (e.g., ["http://localhost:3000"])
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
    # Specify specific domains, allow credentials
    origins_list = [origin.strip() for origin in cors_allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ✅ Add HTTP request/response logging middleware (records detailed request and response information)
app.add_middleware(HTTPLoggingMiddleware)
logger.info("✅ HTTP request/response logging middleware enabled")

# Add Prometheus metrics collection middleware (based on configuration switch)
if config.enable_prometheus:
    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("✅ Prometheus metrics collection middleware enabled")

# ✅ Add unified exception handling middleware immediately (must be added before application startup)
app.add_middleware(UnifiedExceptionMiddleware)

# ✅ Add request context middleware (generates request_id for each request, used for log tracing)
app.add_middleware(RequestContextMiddleware)
logger.info("✅ Request context middleware enabled")

# ❌ Do not call jaeger_manager.instrument_app(app) here
# Application has already started at this point, cannot add Jaeger middleware anymore

# Note: Exception handlers are already registered in lifespan startup() (shared/app/service_factory.py:243-245)
# So no need to call setup_exception_handling here
# Calling it would cause exception handlers to be registered twice, potentially causing conflicts

# Add health check routes
include_health_routes(app)

# Add public metrics route (for Prometheus metrics collection, only when enabled)
if config.enable_prometheus:
    app.include_router(metrics_router)
    logger.info("✅ Prometheus metrics route enabled")

# Register API routes (✅ Add /host prefix to match Gateway forwarding rules)
app.include_router(api_router, prefix="/api/v1/host")


@app.get("/")
async def root():
    """Root path"""
    return {"message": "Host Service is running"}
