"""
Unified health check routing module

Provides standardized health check endpoints for all microservices.

Features:
- Unified /health endpoint
- Check dependent services such as database and Redis
- Return structured health status information
- Support degradation mode
"""

from fastapi import APIRouter, FastAPI

from shared.app.service_factory import HealthCheckManager
from shared.common.response import SuccessResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> SuccessResponse:
    """
    Health check endpoint

    Returns the health status of the service and its dependent services.

    Returns:
        SuccessResponse, containing:
        - status: overall/healthy/degraded/unhealthy
        - components: Detailed status of each component (database/redis)

    Example response:
        ```json
        {
          "code": 200,
          "data": {
            "status": "healthy",
            "components": {
              "database": {"status": "healthy", "details": {...}},
              "redis": {"status": "healthy", "details": {...}}
            }
          },
          "message": "Service status: healthy"
        }
        ```
    """
    return await HealthCheckManager.perform_health_check()


def include_health_routes(app: FastAPI) -> None:
    """
    Include health check routes to the application

    Args:
        app: FastAPI application instance

    Example:
        ```python
        from shared.app.health_routes import include_health_routes

        app = FastAPI()
        include_health_routes(app)
        ```
    """
    app.include_router(router)
