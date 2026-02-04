"""
Shared App Module

Provides unified initialization, lifecycle management, and exception handling for microservice applications.
"""

from shared.app.application import create_exception_handlers
from shared.app.exception_handler import setup_exception_handling
from shared.app.health_routes import include_health_routes
from shared.app.health_routes import router as health_router
from shared.app.service_factory import (
    HealthCheckManager,
    ServiceConfig,
    ServiceLifecycleManager,
    create_service_lifespan,
)

__all__ = [
    "HealthCheckManager",
    "ServiceConfig",
    "ServiceLifecycleManager",
    "create_exception_handlers",
    "create_service_lifespan",
    "health_router",
    "include_health_routes",
    "setup_exception_handling",
]
