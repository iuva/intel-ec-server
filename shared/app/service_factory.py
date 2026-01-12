"""
Service initialization factory module

Provides unified service initialization, lifecycle management, and health check functions.
Simplifies main application files of microservices and reduces duplicate code.

Design principles:
1. Single responsibility - Each class is responsible for a specific initialization task
2. Dependency injection - Inject configuration and dependencies through constructor
3. Flexible and extensible - Supports custom handlers and middleware
"""

import asyncio
import inspect
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from urllib.parse import quote_plus

from fastapi import FastAPI
from sqlalchemy import text

from shared.common.cache import build_redis_url, redis_manager, validate_redis_config
from shared.common.database import close_databases, init_databases, mariadb_manager
from shared.common.loguru_config import get_logger
from shared.common.response import SuccessResponse
from shared.config.nacos_config import NacosManager
from shared.monitoring.jaeger import init_jaeger
from shared.monitoring.metrics import init_metrics
from shared.utils.docker_detection import (
    resolve_mariadb_host,
    resolve_nacos_host,
    resolve_redis_host,
    resolve_service_ip,
)

logger = get_logger(__name__)


class ServiceConfig:
    """
    Unified service configuration class

    Manages all configuration information of the service, including service name, port, database connection, etc.

    Attributes:
        service_name: Service name
        service_port: Service port
        service_ip: Service IP address
        nacos_server_addr: Nacos server address
        mariadb_url: MariaDB connection URL
        redis_url: Redis connection URL
        jwt_secret_key: JWT secret key
        jaeger_endpoint: Jaeger endpoint
        enable_nacos: Whether to enable Nacos service discovery
        enable_jaeger: Whether to enable Jaeger tracing
        enable_prometheus: Whether to enable Prometheus monitoring
    """

    def __init__(
        self,
        service_name: str,
        service_port: Optional[int] = None,
        service_ip: Optional[str] = None,
        nacos_server_addr: Optional[str] = None,
        mariadb_url: Optional[str] = None,
        redis_url: Optional[str] = None,
        jwt_secret_key: Optional[str] = None,
        jaeger_endpoint: Optional[str] = None,
        hardware_api_url: Optional[str] = None,
        enable_nacos: bool = True,
        enable_jaeger: bool = True,
        enable_prometheus: bool = True,
        http_timeout: float = 15.0,
        http_connect_timeout: float = 5.0,
        http_max_keepalive_connections: int = 20,
        http_max_connections: int = 100,
        http_max_retries: int = 0,
        http_retry_delay: float = 0.0,
        db_pool_size: int = 300,
        db_max_overflow: int = 500,
        health_check_timeout: float = 5.0,
        health_check_connect_timeout: float = 2.0,
        health_check_max_keepalive_connections: int = 5,
        health_check_max_connections: int = 10,
        health_check_max_retries: int = 1,
        health_check_retry_delay: float = 0.0,
    ):
        """
        Initialize service configuration

        Args:
            service_name: Service name
            service_port: Service port
            service_ip: Service IP
            nacos_server_addr: Nacos server address
            mariadb_url: MariaDB connection URL
            redis_url: Redis connection URL
            jwt_secret_key: JWT secret key
            jaeger_endpoint: Jaeger endpoint
            hardware_api_url: Hardware API base URL
            enable_nacos: Whether to enable Nacos service discovery (default: True)
            enable_jaeger: Whether to enable Jaeger tracing (default: True)
            enable_prometheus: Whether to enable Prometheus monitoring (default: True)
        """
        self.service_name = service_name
        self.service_port = service_port
        self.service_ip = service_ip
        self.nacos_server_addr = nacos_server_addr
        self.mariadb_url = mariadb_url
        self.redis_url = redis_url
        self.jwt_secret_key = jwt_secret_key

        self.jaeger_endpoint = jaeger_endpoint
        self.hardware_api_url = hardware_api_url

        # Component toggle configuration
        self.enable_nacos = enable_nacos
        self.enable_jaeger = enable_jaeger
        self.enable_prometheus = enable_prometheus

        # HTTP client configuration
        self.http_timeout = http_timeout
        self.http_connect_timeout = http_connect_timeout
        self.http_max_keepalive_connections = http_max_keepalive_connections
        self.http_max_connections = http_max_connections
        self.http_max_retries = http_max_retries
        self.http_retry_delay = http_retry_delay

        # Database connection pool configuration (supports high concurrency)
        self.db_pool_size = db_pool_size
        self.db_max_overflow = db_max_overflow

        # SQL performance monitoring configuration
        self.enable_sql_monitoring = os.getenv("ENABLE_SQL_MONITORING", "true").lower() == "true"
        self.slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "2.0"))

        # Health check HTTP client configuration
        self.health_check_timeout = health_check_timeout
        self.health_check_connect_timeout = health_check_connect_timeout
        self.health_check_max_keepalive_connections = health_check_max_keepalive_connections
        self.health_check_max_connections = health_check_max_connections
        self.health_check_max_retries = health_check_max_retries
        self.health_check_retry_delay = health_check_retry_delay

    @staticmethod
    def from_env(service_name: str, service_port_key: str = "SERVICE_PORT") -> "ServiceConfig":
        """
        Create service configuration from environment variables

        Args:
            service_name: Service name
            service_port_key: Service port environment variable key name

        Returns:
            ServiceConfig instance
        """
        # Basic configuration
        service_port = int(os.getenv(service_port_key, "8000"))
        # Service IP auto-detection: Prioritize environment variables, otherwise
        # automatically select based on runtime environment
        # Docker environment: Try to automatically get container IP
        # Local environment: Use 127.0.0.1
        service_ip = os.getenv("SERVICE_IP") or resolve_service_ip()

        # Nacos configuration - Intelligent host address resolution
        nacos_host = resolve_nacos_host()
        nacos_port = os.getenv("NACOS_PORT", "8848")
        nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", f"{nacos_host}:{nacos_port}")

        # Database configuration - Intelligent host address resolution
        # Prioritize environment variables, otherwise automatically select based on runtime environment
        mariadb_host = os.getenv("MARIADB_HOST") or resolve_mariadb_host(default_in_docker="mariadb")
        mariadb_port = os.getenv("MARIADB_PORT", "3306")
        # Default user and ***REMOVED***word consistent with docker-compose.yml
        mariadb_user = os.getenv("MARIADB_USER", "intel_user")
        mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
        mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

        encoded_***REMOVED***word = quote_plus(mariadb_***REMOVED***word)
        mariadb_url = (
            f"mysql+aiomysql://{mariadb_user}:{encoded_***REMOVED***word}@{mariadb_host}:{mariadb_port}/{mariadb_database}"
        )

        # Redis configuration - Intelligent host address resolution
        # Prioritize environment variables, otherwise automatically select based on runtime environment
        redis_host = os.getenv("REDIS_HOST") or resolve_redis_host(default_in_docker="redis")
        redis_port_str = os.getenv("REDIS_PORT", "6379")
        redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
        redis_db_str = os.getenv("REDIS_DB", "0")
        redis_username = os.getenv("REDIS_USERNAME")

        # Redis SSL configuration
        redis_ssl_enabled = os.getenv("REDIS_SSL_ENABLED", "false").lower() in ("true", "1", "yes")

        try:
            redis_host, redis_port, redis_db = validate_redis_config(redis_host, redis_port_str, redis_db_str)
            redis_url = build_redis_url(
                host=redis_host,
                port=redis_port,
                ***REMOVED***word=redis_***REMOVED***word if redis_***REMOVED***word else None,
                db=redis_db,
                username=redis_username,
                ssl_enabled=redis_ssl_enabled,  # ✅ Pass SSL configuration
            )
        except ValueError as e:
            logger.warning(f"Redis configuration validation failed: {e}, using default configuration")
            protocol = "rediss://" if redis_ssl_enabled else "redis://"
            redis_url = f"{protocol}{redis_host}:6379/0"

        # JWT and Jaeger configuration
        jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")

        # External service API configuration
        hardware_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")

        # Component toggle configuration (supports environment variables, enabled by default)
        # Environment variable values: true/True/1/yes/Yes means enabled, other values mean disabled
        def parse_bool_env(env_key: str, default: bool = True) -> bool:
            """Parse boolean environment variable"""
            value = os.getenv(env_key)
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes", "on", "enabled")

        enable_nacos = parse_bool_env("ENABLE_NACOS", default=True)
        enable_jaeger = parse_bool_env("ENABLE_JAEGER", default=True)
        enable_prometheus = parse_bool_env("ENABLE_PROMETHEUS", default=True)

        # HTTP client configuration (supports environment variable override)
        def parse_float_env(env_key: str, default: float) -> float:
            value = os.getenv(env_key)
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                logger.warning(
                    f"Invalid value for environment variable {env_key}: {value}, using default value {default}"
                )
                return default

        def parse_int_env(env_key: str, default: int) -> int:
            value = os.getenv(env_key)
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                logger.warning(
                    f"Invalid value for environment variable {env_key}: {value}, using default value {default}"
                )
                return default

        http_timeout = parse_float_env("HTTP_TIMEOUT", 15.0)
        http_connect_timeout = parse_float_env("HTTP_CONNECT_TIMEOUT", 5.0)
        http_max_keepalive_connections = parse_int_env("HTTP_MAX_KEEPALIVE_CONNECTIONS", 20)
        http_max_connections = parse_int_env("HTTP_MAX_CONNECTIONS", 100)
        http_max_retries = parse_int_env("HTTP_MAX_RETRIES", 0)
        http_retry_delay = parse_float_env("HTTP_RETRY_DELAY", 0.0)

        health_check_timeout = parse_float_env("HEALTH_CHECK_TIMEOUT", 5.0)
        health_check_connect_timeout = parse_float_env("HEALTH_CHECK_CONNECT_TIMEOUT", 2.0)
        health_check_max_keepalive_connections = parse_int_env("HEALTH_CHECK_MAX_KEEPALIVE_CONNECTIONS", 5)
        health_check_max_connections = parse_int_env("HEALTH_CHECK_MAX_CONNECTIONS", 10)
        health_check_max_retries = parse_int_env("HEALTH_CHECK_MAX_RETRIES", 1)
        health_check_retry_delay = parse_float_env("HEALTH_CHECK_RETRY_DELAY", 0.0)

        # Database connection pool configuration (supports 2000 concurrency, default values are optimized)
        db_pool_size = parse_int_env("DB_POOL_SIZE", 300)
        db_max_overflow = parse_int_env("DB_MAX_OVERFLOW", 500)

        return ServiceConfig(
            service_name=service_name,
            service_port=service_port,
            service_ip=service_ip,
            nacos_server_addr=nacos_server_addr,
            mariadb_url=mariadb_url,
            redis_url=redis_url,
            jwt_secret_key=jwt_secret_key,
            jaeger_endpoint=jaeger_endpoint,
            hardware_api_url=hardware_api_url,
            enable_nacos=enable_nacos,
            enable_jaeger=enable_jaeger,
            enable_prometheus=enable_prometheus,
            http_timeout=http_timeout,
            http_connect_timeout=http_connect_timeout,
            http_max_keepalive_connections=http_max_keepalive_connections,
            http_max_connections=http_max_connections,
            http_max_retries=http_max_retries,
            http_retry_delay=http_retry_delay,
            health_check_timeout=health_check_timeout,
            health_check_connect_timeout=health_check_connect_timeout,
            health_check_max_keepalive_connections=health_check_max_keepalive_connections,
            health_check_max_connections=health_check_max_connections,
            health_check_max_retries=health_check_max_retries,
            health_check_retry_delay=health_check_retry_delay,
            db_pool_size=db_pool_size,
            db_max_overflow=db_max_overflow,
        )


class ServiceLifecycleManager:
    """
    Unified service lifecycle management

    Manages the startup, running, and shutdown phases of services, simplifying duplicate code in microservices.

    Functions:
    - Initialize and close database connections
    - Initialize and close Redis connections
    - Nacos service registration and deregistration
    - Custom startup and shutdown handlers
    """

    def __init__(
        self,
        config: ServiceConfig,
        startup_handlers: Optional[List[Callable]] = None,
        shutdown_handlers: Optional[List[Callable]] = None,
    ):
        """
        Initialize the lifecycle manager

        Args:
            config: Service configuration
            startup_handlers: List of handlers to execute on startup
            shutdown_handlers: List of handlers to execute on shutdown
        """
        self.config = config
        self.startup_handlers = startup_handlers or []
        self.shutdown_handlers = shutdown_handlers or []
        self.nacos_manager: Optional[NacosManager] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.pool_monitor_task: Optional[asyncio.Task] = None

    async def startup(self, app: FastAPI) -> None:
        """
        Execute service startup process

        Execute in the following order:
        1. Initialize database connections
        2. Initialize Jaeger tracing
        3. Initialize monitoring metrics
        4. Register exception handlers (unified error response format)
        5. Initialize Nacos service registration
        6. Execute custom startup handlers

        """
        logger.info(f"{self.config.service_name} starting...")

        try:
            # 1. Initialize database connection
            logger.info("Initializing database connection...")
            if not self.config.mariadb_url or not self.config.redis_url:
                logger.error("Database configuration is incomplete, cannot initialize")
                raise ValueError("MariaDB URL and Redis URL must be configured")

            await init_databases(
                mariadb_url=self.config.mariadb_url,
                redis_url=self.config.redis_url,
                pool_size=self.config.db_pool_size,
                max_overflow=self.config.db_max_overflow,
                enable_sql_monitoring=self.config.enable_sql_monitoring,
                slow_query_threshold=self.config.slow_query_threshold,
                service_name=self.config.service_name,
            )
            logger.info("Database connection initialized successfully")

            # 2. Initialize Jaeger tracing (based on switch)
            if self.config.enable_jaeger and self.config.jaeger_endpoint:
                logger.info("Initializing Jaeger tracing...")
                try:
                    init_jaeger(
                        service_name=self.config.service_name,
                        jaeger_endpoint=self.config.jaeger_endpoint,
                        environment=os.getenv("ENVIRONMENT", "production"),
                        service_version="1.0.0",
                    )
                    # ❌ Note: Do not call auto_instrument_app(app) here
                    # Because the application is already processing requests and cannot add middleware anymore
                    # auto_instrument_app(app)
                    logger.info("Jaeger tracing initialized successfully")
                except Exception as e:
                    logger.warning(f"Jaeger tracing initialization failed: {e!s}, continuing...")

            # 3. Initialize monitoring metrics (based on switch)
            if self.config.enable_prometheus:
                logger.info("Initializing monitoring metrics...")
                try:
                    init_metrics(
                        service_name=self.config.service_name,
                        service_version="1.0.0",
                        environment=os.getenv("ENVIRONMENT", "production"),
                    )
                    logger.info("Monitoring metrics initialized successfully")
                except Exception as e:
                    logger.warning(f"Monitoring metrics initialization failed: {e!s}, continuing...")

            # ❌ Do not register exception handlers here!
            # Exception handlers must be registered when the FastAPI app is created (in main.py)
            # Registering during lifespan startup causes duplicate registration, breaking the routing table
            # Reference: services/*/app/main.py - app.add_middleware(UnifiedExceptionMiddleware)

            # 5. Initialize Nacos service registration (based on switch)
            if self.config.enable_nacos:
                logger.info("Initializing Nacos service discovery...")
                await self._init_nacos(app)
                logger.info("Nacos initialization completed")

            # 6. Start database connection pool monitoring task
            self.pool_monitor_task = asyncio.create_task(self._monitor_pool_status())
            app.state.pool_monitor_task = self.pool_monitor_task
            logger.info("Database connection pool monitoring task started")

            # 7. Set Nacos manager to service discovery instance (only when Nacos is enabled)
            if (
                self.config.enable_nacos
                and hasattr(app.state, "service_discovery")
                and app.state.service_discovery
                and self.nacos_manager
            ):
                app.state.service_discovery.set_nacos_manager(self.nacos_manager)
                logger.info("✅ Service discovery connected to Nacos")

            # 8. Execute custom startup handlers
            for handler in self.startup_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(app)
                else:
                    handler(app)

            logger.info(f"{self.config.service_name} started successfully")

        except Exception as e:
            logger.error(f"{self.config.service_name} startup failed: {e!s}", exc_info=True)
            raise

    async def _init_nacos(self, app: FastAPI) -> None:
        """Initialize Nacos service discovery and registration"""
        if not self.config.nacos_server_addr or not self.config.service_port:
            logger.warning("Nacos configuration is incomplete, skipping service registration")
            return

        # Ensure service_ip is not None
        if not self.config.service_ip:
            logger.warning("Service IP not configured, skipping Nacos registration")
            return

        try:
            # Get Nacos authentication information
            nacos_username = os.getenv("NACOS_USERNAME", "nacos")
            nacos_***REMOVED***word = os.getenv("NACOS_PASSWORD", "nacos")
            nacos_namespace = os.getenv("NACOS_NAMESPACE", "public")
            nacos_group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")

            # Create Nacos manager
            self.nacos_manager = NacosManager(
                server_addresses=self.config.nacos_server_addr.replace("http://", ""),
                namespace=nacos_namespace,
                group=nacos_group,
                username=nacos_username,
                ***REMOVED***word=nacos_***REMOVED***word,
            )

            # Register service
            success = await self.nacos_manager.register_service(
                service_name=self.config.service_name,
                ip=self.config.service_ip,
                port=self.config.service_port,
                ephemeral=True,
                metadata={
                    "version": "1.0.0",
                    "environment": os.getenv("ENVIRONMENT", "production"),
                },
            )

            if success:
                # Start heartbeat detection
                self.heartbeat_task = asyncio.create_task(
                    self.nacos_manager.start_heartbeat(
                        service_name=self.config.service_name,
                        ip=self.config.service_ip,
                        port=self.config.service_port,
                        interval=5,
                    )
                )
                # Store task reference to prevent garbage collection
                app.state.nacos_heartbeat_task = self.heartbeat_task
                logger.info("Nacos service registration and heartbeat detection started successfully")
            else:
                logger.warning("Nacos service registration failed")

        except Exception as e:
            logger.warning(f"Nacos initialization failed: {e!s}, continuing...")

    async def _monitor_pool_status(self) -> None:
        """Regularly monitor database connection pool status"""
        from shared.common.database import mariadb_manager

        while True:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds
                mariadb_manager.log_pool_status()
            except asyncio.CancelledError:
                logger.info("Database connection pool monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Database connection pool monitoring error: {e!s}", exc_info=True)
                await asyncio.sleep(30)  # Wait 30 seconds before continuing after error

    async def shutdown(self, app: Optional[FastAPI] = None) -> None:
        """
        Execute service shutdown process

        Execute in the following order:
        1. Execute custom shutdown handlers
        2. Stop Nacos heartbeat detection
        3. Close database connections

        Args:
            app: FastAPI application instance (optional, ***REMOVED***ed to shutdown handlers)
        """
        logger.info(f"{self.config.service_name} shutting down...")

        try:
            # 0. Stop connection pool monitoring task
            if self.pool_monitor_task and not self.pool_monitor_task.done():
                self.pool_monitor_task.cancel()
                try:
                    await self.pool_monitor_task
                except asyncio.CancelledError:
                    ***REMOVED***
                logger.info("Database connection pool monitoring task stopped")

            # 1. Execute custom shutdown handlers
            for handler in self.shutdown_handlers:
                if asyncio.iscoroutinefunction(handler):
                    # Check function signature, if it needs one parameter (app), then ***REMOVED*** it
                    sig = inspect.signature(handler)
                    params = list(sig.parameters.keys())
                    if len(params) > 0:
                        await handler(app)
                    else:
                        await handler()
                else:
                    sig = inspect.signature(handler)
                    params = list(sig.parameters.keys())
                    if len(params) > 0:
                        handler(app)
                    else:
                        handler()

            # 2. Stop Nacos heartbeat detection (only when Nacos is enabled)
            if self.config.enable_nacos and self.nacos_manager:
                self.nacos_manager.stop_heartbeat()
                logger.info("Nacos heartbeat detection stopped")

            # 3. Close database connections
            await close_databases()
            logger.info("Database connections closed")

            logger.info(f"{self.config.service_name} shutdown completed")

        except Exception as e:
            logger.error(f"{self.config.service_name} shutdown error: {e!s}", exc_info=True)


class HealthCheckManager:
    """
    Unified health check management

    Provides standardized health check endpoints, checking the status of dependent services such as database and Redis.

    Functions:
    - Health status checks (database, Redis)
    - Structured health check responses
    - Support degradation mode (some services unavailable)
    """

    @staticmethod
    async def perform_health_check() -> SuccessResponse:
        """
        Perform health check

        Check the status of all dependent services and return the overall health status.

        Returns:
            SuccessResponse, containing:
            - database: Database connection status
            - redis: Redis connection status
            - overall_status: Overall status (healthy/degraded/unhealthy)
        """
        # Check database connection
        db_status = await HealthCheckManager._check_database()

        # Check Redis connection
        redis_status = await HealthCheckManager._check_redis()

        # Determine overall status
        if db_status["status"] == "healthy" and redis_status["status"] == "healthy":
            overall_status = "healthy"
        elif db_status["status"] == "unhealthy":
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return SuccessResponse(
            data={
                "status": overall_status,
                "components": {
                    "database": db_status,
                    "redis": redis_status,
                },
            },
            message=f"Service status: {overall_status}",
        )

    @staticmethod
    async def _check_database() -> Dict[str, Any]:
        """Check database connection status"""
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
                return {"status": "healthy", "details": {"message": "Database connection normal"}}
        except Exception as e:
            logger.error(f"Database health check failed: {e!s}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e), "message": "Database connection abnormal"},
            }

    @staticmethod
    async def _check_redis() -> Dict[str, Any]:
        """Check Redis connection status"""
        try:
            if redis_manager.is_connected and redis_manager.client:
                await redis_manager.client.ping()
                return {
                    "status": "healthy",
                    "details": {
                        "message": "Redis connection normal",
                        "mode": "cached",
                    },
                }
            return {
                "status": "unavailable",
                "details": {
                    "message": "Redis not connected, service running in degradation mode (no cache)",
                    "mode": "degraded",
                },
            }
        except Exception as e:
            logger.warning(f"Redis health check failed: {e!s}")
            return {
                "status": "unavailable",
                "details": {
                    "error": str(e),
                    "message": "Redis connection abnormal, service running in degradation mode (no cache)",
                    "mode": "degraded",
                },
            }


def create_service_lifespan(
    config: ServiceConfig,
    startup_handlers: Optional[List[Callable]] = None,
    shutdown_handlers: Optional[List[Callable]] = None,
) -> Callable:
    """
    Create service lifecycle context manager

    Simplify the code for creating lifecycle handlers in microservices.

    Args:
        config: Service configuration
        startup_handlers: List of handlers to execute on startup
        shutdown_handlers: List of handlers to execute on shutdown

    Returns:
        Async lifecycle context manager

    Example:
        ```python
        config = ServiceConfig.from_env("my-service", "MY_SERVICE_PORT")
        app = FastAPI(lifespan=create_service_lifespan(config))
        ```
    """
    manager = ServiceLifecycleManager(config, startup_handlers, shutdown_handlers)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifecycle handling"""
        await manager.startup(app)
        yield
        await manager.shutdown(app)

    return lifespan
