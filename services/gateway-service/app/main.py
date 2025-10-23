"""
Gateway Service 主应用入口

提供API网关功能，包括：
- 路由转发
- 负载均衡
- 认证验证
- 限流熔断
"""

import os
import sys

# 使用 try-except 方式处理路径导入
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.v1 import api_router
    from app.middleware.auth_middleware import AuthMiddleware
    from shared.app import (
        ServiceConfig,
        create_service_lifespan,
        include_health_routes,
        setup_exception_handling,
    )
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.v1 import api_router
    from app.middleware.auth_middleware import AuthMiddleware
    from shared.app import (
        ServiceConfig,
        create_service_lifespan,
        include_health_routes,
        setup_exception_handling,
    )
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router

# 配置日志（在应用启动前配置）
service_name = os.getenv("GATEWAY_SERVICE_NAME", "gateway-service")
configure_logger(service_name=service_name, log_level="INFO")

logger = get_logger(__name__)

# 创建服务配置
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="GATEWAY_SERVICE_PORT",
)

# 创建 FastAPI 应用
app = FastAPI(
    title="Gateway Service",
    description="Intel EC API Gateway",
    version="1.0.0",
    lifespan=create_service_lifespan(config),
)

# ✅ 在这里立即添加所有中间件（在 lifespan 之前）
# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# 添加 Prometheus 指标收集中间件
app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)

# 最后立即注册异常处理器（确保所有异常都被正确捕获）
# 注：这会添加 UnifiedExceptionMiddleware，必须最后调用以确保最高优先级
setup_exception_handling(app, service_name)

# 添加健康检查路由
include_health_routes(app)

# 添加公共 metrics 路由（用于 Prometheus 采集指标）
app.include_router(metrics_router)

# 包含 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Intel EC Gateway Service is running"}
