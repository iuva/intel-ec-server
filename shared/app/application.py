"""
FastAPI Application Template Module

Provides unified FastAPI application creation and configuration functionality
"""

from contextlib import asynccontextmanager
import logging
import time
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.common.cache import redis_manager
from shared.common.database import mariadb_manager
from shared.common.exceptions import BusinessError
from shared.common.loguru_config import configure_logger
from shared.common.response import create_error_response, create_success_response
from shared.common.security import init_jwt_manager
from shared.monitoring.jaeger import jaeger_manager
from shared.monitoring.metrics import get_metrics_response, init_metrics, metrics_collector

logger = logging.getLogger(__name__)


def create_lifespan_handler(
    service_name: str,
    database_url: Optional[str] = None,
    redis_url: Optional[str] = None,
    jwt_secret_key: Optional[str] = None,
    jaeger_endpoint: Optional[str] = None,
    startup_handlers: Optional[List[Callable]] = None,
    shutdown_handlers: Optional[List[Callable]] = None,
) -> Callable:
    """Create application lifecycle handler

    Args:
        service_name: Service name
        database_url: Database connection URL
        redis_url: Redis connection URL
        jwt_secret_key: JWT secret key
        jaeger_endpoint: Jaeger endpoint
        startup_handlers: List of handlers to execute during startup
        shutdown_handlers: List of handlers to execute during shutdown

    Returns:
        Lifecycle context manager
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifecycle management"""
        # ==================== Startup Phase ====================
        logger.info(f"{service_name} service starting...")

        # Initialize database connection
        if database_url:
            try:
                await mariadb_manager.connect(database_url)
                logger.info("Database connection successful")
            except Exception as e:
                logger.error(f"Database connection failed: {e!s}")
                raise

        # Initialize Redis connection
        if redis_url:
            try:
                await redis_manager.connect(redis_url)
                logger.info("Redis connection successful")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e!s}, degrading to no-cache mode")

        # Initialize JWT manager
        if jwt_secret_key:
            try:
                init_jwt_manager(jwt_secret_key)
                logger.info("JWT manager initialized successfully")
            except Exception as e:
                logger.error(f"JWT manager initialization failed: {e!s}")

        # Initialize Jaeger tracing
        if jaeger_endpoint:
            try:
                jaeger_manager.init_tracer(service_name=service_name, jaeger_endpoint=jaeger_endpoint)
                # ❌ Note: Do not call jaeger_manager.instrument_fastapi(app) here
                # Because the application is already handling requests and cannot add middleware anymore
                # Should be called immediately after creating the FastAPI app
                logger.info("Jaeger tracing initialized successfully")
            except Exception as e:
                logger.warning(f"Jaeger tracing initialization failed: {e!s}")

        # Execute custom startup handlers
        if startup_handlers:
            for handler in startup_handlers:
                try:
                    if callable(handler):
                        result = handler()
                        if hasattr(result, "__await__"):
                            await result
                except Exception as e:
                    logger.error(f"Startup handler execution failed: {e!s}")

        logger.info(f"{service_name} service startup completed")

        yield

        # ==================== Shutdown Phase ====================
        logger.info(f"{service_name} service shutting down...")

        # Execute custom shutdown handlers
        if shutdown_handlers:
            for handler in shutdown_handlers:
                try:
                    if callable(handler):
                        result = handler()
                        if hasattr(result, "__await__"):
                            await result
                except Exception as e:
                    logger.error(f"Shutdown handler execution failed: {e!s}")

        # Close Jaeger tracing
        try:
            jaeger_manager.shutdown()
        except Exception as e:
            logger.error(f"Jaeger tracing shutdown failed: {e!s}")

        # Close Redis connection
        try:
            await redis_manager.disconnect()
        except Exception as e:
            logger.error(f"Redis connection close failed: {e!s}")

        # Close database connection
        try:
            await mariadb_manager.disconnect()
        except Exception as e:
            logger.error(f"Database connection close failed: {e!s}")

        logger.info(f"{service_name} service shutdown completed")

    return lifespan


def create_exception_handlers() -> Dict[type, Callable]:
    """Create global exception handlers

    Returns:
        Exception handler dictionary
    """

    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        """Business exception handler"""
        logger.warning(f"Business exception: [{exc.code}] {exc.error_code} - {exc.message}")

        error_response = create_error_response(
            message=exc.message,
            error_code=exc.error_code,
            code=exc.code,
            details=exc.details,
        )

        return JSONResponse(status_code=exc.code, content=error_response.model_dump())

    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Request validation exception handler"""
        logger.warning(f"Request validation failed: {exc.errors()}")

        error_response = create_error_response(
            message="Request parameter validation failed",
            error_code="VALIDATION_ERROR",
            code=422,
            details={"errors": exc.errors()},
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """HTTP exception handler"""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

        # Check if detail is already in ErrorResponse format dictionary
        detail_value = getattr(exc, "detail", None)
        if isinstance(detail_value, dict) and all(key in detail_value for key in ["code", "message", "error_code"]):
            return JSONResponse(status_code=exc.status_code, content=detail_value)
        error_response = create_error_response(
            message=str(exc.detail),
            error_code="HTTP_ERROR",
            code=exc.status_code,
        )

        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """General exception handler"""
        logger.error(f"Unhandled exception: {exc!s}", exc_info=True)

        error_response = create_error_response(message="Internal server error", error_code="INTERNAL_ERROR", code=500)

        return JSONResponse(status_code=500, content=error_response.model_dump())

    return {
        BusinessError: business_error_handler,
        RequestValidationError: validation_error_handler,
        StarletteHTTPException: http_exception_handler,
        Exception: general_exception_handler,
    }


def create_fastapi_app(
    service_name: str,
    service_version: str = "1.0.0",
    description: str = "",
    database_url: Optional[str] = None,
    redis_url: Optional[str] = None,
    jwt_secret_key: Optional[str] = None,
    jaeger_endpoint: Optional[str] = None,
    log_level: str = "INFO",
    enable_docs: bool = True,
    enable_prometheus: bool = True,
    cors_origins: Optional[List[str]] = None,
    trusted_hosts: Optional[List[str]] = None,
    startup_handlers: Optional[List[Callable]] = None,
    shutdown_handlers: Optional[List[Callable]] = None,
) -> FastAPI:
    """Create FastAPI application

    Args:
        service_name: Service name
        service_version: Service version
        description: Service description
        database_url: Database connection URL
        redis_url: Redis connection URL
        jwt_secret_key: JWT secret key
        jaeger_endpoint: Jaeger endpoint
        log_level: Log level
        enable_docs: Whether to enable API documentation
        enable_prometheus: Whether to enable Prometheus monitoring (default: True)
        cors_origins: CORS allowed origins
        trusted_hosts: List of trusted hosts
        startup_handlers: Startup handler list
        shutdown_handlers: Shutdown handler list

    Returns:
        Configured FastAPI application instance
    """
    # Configure logging
    configure_logger(service_name=service_name, log_level=log_level)

    # Initialize monitoring metrics (based on switch)
    if enable_prometheus:
        init_metrics(
            service_name=service_name,
            service_version=service_version,
            environment="development",
        )

    # Create FastAPI application
    app = FastAPI(
        title=f"{service_name} API",
        description=description or f"{service_name} microservice API",
        version=service_version,
        lifespan=create_lifespan_handler(
            service_name=service_name,
            database_url=database_url,
            redis_url=redis_url,
            jwt_secret_key=jwt_secret_key,
            jaeger_endpoint=jaeger_endpoint,
            startup_handlers=startup_handlers,
            shutdown_handlers=shutdown_handlers,
        ),
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        openapi_url="/openapi.json" if enable_docs else None,
    )

    # Add middleware
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add request logging middleware (only when Prometheus is enabled)
    if enable_prometheus:

        @app.middleware("http")
        async def log_requests(request: Request, call_next: Any) -> Any:
            """Log HTTP requests"""
            start_time = time.time()

            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            metrics_collector.record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=duration,
            )

            return response

    # Register exception handlers
    exception_handlers = create_exception_handlers()
    for exc_class, handler in exception_handlers.items():
        app.add_exception_handler(exc_class, handler)

    # Health check endpoint
    @app.get("/health", tags=["Health Check"])
    async def health_check() -> Any:
        """Health check"""
        health_status = {
            "service": service_name,
            "version": service_version,
            "status": "healthy",
        }

        # Check database connection
        if mariadb_manager.is_connected:
            health_status["database"] = "connected"
        else:
            health_status["database"] = "disconnected"

        # Check Redis connection
        if redis_manager.is_connected:
            health_status["cache"] = "connected"
        else:
            health_status["cache"] = "disconnected"

        return create_success_response(data=health_status)

    # Monitoring metrics endpoint (only when Prometheus is enabled)
    if enable_prometheus:

        @app.get("/metrics", tags=["Monitoring"])
        async def metrics() -> Response:
            """Prometheus monitoring metrics"""
            return get_metrics_response()

    # Root path endpoint
    @app.get("/", tags=["Root Path"])
    async def root() -> Any:
        """Root path"""
        return create_success_response(
            data={
                "service": service_name,
                "version": service_version,
                "docs": "/docs" if enable_docs else "disabled",
                "health": "/health",
                "metrics": "/metrics" if enable_prometheus else "disabled",
            },
            message=f"{service_name} service running normally",
        )

    return app
