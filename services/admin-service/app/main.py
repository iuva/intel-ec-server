"""
Admin Service 主应用入口

提供后台管理、用户管理、系统配置等功能
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1 import api_router
    from shared.app import (
        ServiceConfig,
        create_service_lifespan,
        include_health_routes,
    )
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from app.api.v1 import api_router
    from shared.app import (
        ServiceConfig,
        create_service_lifespan,
        include_health_routes,
    )
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router

# 配置日志（在应用启动前配置）
service_name = os.getenv("ADMIN_SERVICE_NAME", "admin-service")
configure_logger(service_name=service_name, log_level="INFO")

logger = get_logger(__name__)

# 创建服务配置
config = ServiceConfig.from_env(
    service_name=service_name,
    service_port_key="ADMIN_SERVICE_PORT",
)

# 创建 FastAPI 应用
app = FastAPI(
    title="Admin Service",
    description="后台管理和系统配置服务",
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

# 添加 Prometheus 指标收集中间件
app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)

# 导入统一异常处理中间件
try:
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
except ImportError:
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware

# ✅ 立即添加统一异常处理中间件（必须在应用启动前添加）
app.add_middleware(UnifiedExceptionMiddleware)

# ❌ 不要在这里调用 jaeger_manager.instrument_app(app)
# 应用在此时已经启动，无法再添加 Jaeger 中间件
# 如果需要 Jaeger 追踪，应该在应用创建前就设置好

# 注意：异常处理器已经在 lifespan 的 startup() 中注册（shared/app/service_factory.py:243-245）
# 所以这里不需要再调用 setup_exception_handling
# 如果调用会导致异常处理器被注册两次，可能产生冲突

# 添加健康检查路由
include_health_routes(app)

# 添加公共 metrics 路由（用于 Prometheus 采集指标）
app.include_router(metrics_router)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Admin Service is running"}
