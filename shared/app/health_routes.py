"""
统一的健康检查路由模块

提供标准化的健康检查端点，用于所有微服务。

特性：
- 统一的 /health 端点
- 检查数据库、Redis 等依赖服务
- 返回结构化的健康状态信息
- 支持降级模式
"""

from fastapi import APIRouter, FastAPI

from shared.app.service_factory import HealthCheckManager
from shared.common.response import SuccessResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> SuccessResponse:
    """
    健康检查端点

    返回服务和依赖服务的健康状态。

    返回：
        SuccessResponse，包含：
        - status: overall/healthy/degraded/unhealthy
        - components: 各组件（database/redis）的详细状态

    示例响应：
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
          "message": "服务状态: healthy"
        }
        ```
    """
    return await HealthCheckManager.perform_health_check()


def include_health_routes(app: FastAPI) -> None:
    """
    包含健康检查路由到应用

    Args:
        app: FastAPI 应用实例

    示例：
        ```python
        from shared.app.health_routes import include_health_routes

        app = FastAPI()
        include_health_routes(app)
        ```
    """
    app.include_router(router)
