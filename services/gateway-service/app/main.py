"""
Gateway Service 主应用入口

提供API网关功能，包括：
- 路由转发
- 负载均衡
- 认证验证
- 限流熔断
"""

import asyncio
from contextlib import asynccontextmanager
import os
import sys
from typing import AsyncGenerator, List, Tuple, Union

# 使用 try-except 方式处理路径导入
try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.v1 import api_router
    from app.middleware.auth_middleware import AuthMiddleware
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.common.response import SuccessResponse
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.v1 import api_router
    from app.middleware.auth_middleware import AuthMiddleware
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.common.response import SuccessResponse
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics

# 配置日志（在应用启动前配置）
service_name = os.getenv("SERVICE_NAME", "gateway-service")

configure_logger(service_name=service_name, log_level="INFO")

logger = get_logger(__name__)

# Nacos 管理器实例
nacos_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    global nacos_manager

    # 启动时执行
    logger.info("Gateway Service 启动中...")

    try:
        # 获取环境变量
        nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", "http://intel-nacos:8848")
        service_ip = os.getenv("SERVICE_IP", "172.20.0.100")
        service_port = int(os.getenv("SERVICE_PORT", "8000"))

        # 初始化监控指标
        init_metrics(
            service_name="gateway-service",
            service_version="1.0.0",
            environment=os.getenv("ENVIRONMENT", "production"),
        )

        # Jaeger 追踪已在应用创建时初始化

        # 初始化 Nacos（从环境变量读取认证信息）
        nacos_username = os.getenv("NACOS_USERNAME", "nacos")
        nacos_***REMOVED***word = os.getenv("NACOS_PASSWORD", "nacos")
        nacos_namespace = os.getenv("NACOS_NAMESPACE", "public")
        nacos_group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")

        nacos_manager = NacosManager(
            server_addresses=nacos_server_addr.replace("http://", ""),
            namespace=nacos_namespace,
            group=nacos_group,
            username=nacos_username,
            ***REMOVED***word=nacos_***REMOVED***word,
        )

        # 注册服务
        success = await nacos_manager.register_service(
            service_name="gateway-service",
            ip=service_ip,
            port=service_port,
            ephemeral=True,
            metadata={
                "version": "1.0.0",
                "environment": "production",
                "service_type": "gateway",
            },
        )

        if success:
            # 启动心跳检测
            heartbeat_task = asyncio.create_task(
                nacos_manager.start_heartbeat(
                    service_name="gateway-service",
                    ip=service_ip,
                    port=service_port,
                    interval=5,
                )
            )
            # 存储任务引用以防止被垃圾回收
            app.state.heartbeat_task = heartbeat_task
            logger.info("Gateway Service 启动成功")
        else:
            logger.error("Gateway Service 注册失败")

    except Exception as e:
        logger.error(f"Gateway Service 启动异常: {e!s}")

    yield

    # 关闭时执行
    logger.info("Gateway Service 关闭中...")

    try:
        if nacos_manager:
            nacos_manager.stop_heartbeat()
            logger.info("Nacos 心跳检测已停止")
    except Exception as e:
        logger.error(f"Nacos 清理异常: {e!s}")

    logger.info("Gateway Service 关闭完成")


# 创建 FastAPI 应用
app = FastAPI(
    title="Gateway Service",
    description="API 网关服务，提供路由转发、负载均衡、认证验证等功能",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================================
# 中间件注册（按照注册顺序）
# ============================================================================
# 注意：FastAPI 中间件的执行顺序与注册顺序相反
# 注册顺序：CORS → Metrics → Auth
# 实际执行顺序（请求处理）：Auth → Metrics → CORS → 路由处理
# 实际执行顺序（响应处理）：路由处理 → CORS → Metrics → Auth
# ============================================================================

logger.info("=" * 80)
logger.info("开始注册中间件...")
logger.info("=" * 80)

# 1. 添加 CORS 中间件（最后执行）
logger.info("注册 CORS 中间件...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("✓ CORS 中间件注册成功")

# 2. 添加指标收集中间件（倒数第二执行）
logger.info("注册 Prometheus 指标收集中间件...")
try:
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware

    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("✓ Prometheus 指标收集中间件注册成功")
except Exception as e:
    logger.warning(f"✗ 添加指标收集中间件失败: {e!s}")

# 3. 添加认证中间件（最先执行 - 在所有路由处理之前）
logger.info("注册认证中间件...")
logger.info("认证中间件配置:")

# 定义公开路径（与 AuthMiddleware 中的配置保持一致）
public_paths = {
    "/",
    "/health",
    "/health/detailed",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/admin/login",
    "/api/v1/auth/device/login",
    "/api/v1/auth/logout",
}

logger.info(f"  - 公开路径数量: {len(public_paths)}")
logger.info("  - 公开路径列表:")
for path in sorted(public_paths):
    logger.info(f"    • {path}")

app.add_middleware(AuthMiddleware)
logger.info("✓ 认证中间件注册成功")

logger.info("=" * 80)
logger.info("中间件注册完成")
logger.info("中间件执行顺序（请求处理）：Auth → Metrics → CORS → 路由")
logger.info("=" * 80)

# 初始化 Jaeger 追踪器（在应用创建时）
jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4318/v1/traces")
try:
    init_jaeger(
        service_name="gateway-service",
        jaeger_endpoint=jaeger_endpoint,
        environment=os.getenv("ENVIRONMENT", "production"),
        service_version="1.0.0",
    )
    logger.info("Jaeger 追踪器初始化成功")

    # 在应用创建时添加FastAPI追踪中间件
    try:
        auto_instrument_app(app)
        logger.info("FastAPI Jaeger追踪中间件已启用")
    except Exception as e:
        logger.warning(f"添加FastAPI Jaeger追踪中间件失败: {e!s}")

except Exception as e:
    logger.warning(f"Jaeger 追踪器初始化失败: {e!s}")

# 添加统一异常处理中间件
try:
    from shared.app.exception_handler import setup_exception_handling

    logger.info("开始设置统一异常处理...")
    setup_exception_handling(app, "gateway-service")
    logger.info("统一异常处理中间件已启用")
except Exception as e:
    logger.error(f"添加统一异常处理失败: {e!s}", exc_info=True)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_model=SuccessResponse)
async def root():
    """根路径"""
    return SuccessResponse(
        data={
            "service": "gateway-service",
            "version": "1.0.0",
            "status": "running",
        },
        message="Gateway Service 运行正常",
    )


@app.get("/health", response_model=SuccessResponse)
async def health_check():
    """健康检查端点"""
    return SuccessResponse(
        data={
            "service": "gateway-service",
            "status": "healthy",
            "nacos": "connected" if nacos_manager else "disconnected",
        },
        message="服务健康",
    )


@app.get("/health/detailed", response_model=SuccessResponse)
async def detailed_health_check():
    """详细健康检查端点（使用并发检查提高性能）"""
    health_status = {
        "service": "gateway-service",
        "status": "healthy",
        "checks": {
            "nacos": "connected" if nacos_manager else "disconnected",
        },
    }

    # 检查后端服务健康状态
    from app.services.proxy_service import get_proxy_service

    proxy_service = get_proxy_service()

    async def check_service_health(service_name: str) -> Tuple[str, str]:
        """检查单个服务健康状态

        Args:
            service_name: 服务名称

        Returns:
            (服务名称, 健康状态) 元组
        """
        try:
            is_healthy = await proxy_service.health_check_service(service_name)
            return (service_name, "healthy" if is_healthy else "unhealthy")
        except Exception:
            return (service_name, "unknown")

    # 使用并发检查所有后端服务
    service_names = list(proxy_service.service_routes.keys())
    if service_names:
        # 并发执行所有健康检查
        health_check_tasks = [check_service_health(name) for name in service_names]
        results: List[Union[Tuple[str, str], BaseException]] = await asyncio.gather(
            *health_check_tasks, return_exceptions=True
        )

        # 处理结果
        backend_services = {}
        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"健康检查异常: {result!s}")
                continue
            # result 是 Tuple[str, str]
            service_name, status = result
            backend_services[service_name] = status

        health_status["checks"]["backend_services"] = backend_services

        # 判断整体健康状态
        all_healthy = all(status == "healthy" for status in backend_services.values()) and (nacos_manager is not None)
        health_status["status"] = "healthy" if all_healthy else "degraded"
    else:
        health_status["checks"]["backend_services"] = {}

    return SuccessResponse(
        data=health_status,
        message="详细健康检查完成",
    )


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""

    return get_metrics_response()


def setup_uvicorn_logging():
    """配置 uvicorn 日志处理器"""
    import logging
    import threading
    import time

    from loguru import logger as loguru_logger

    # 禁用uvicorn的默认日志处理器
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()

    def replace_uvicorn_handlers():
        """在uvicorn启动后替换其处理器"""
        time.sleep(1)  # 等待uvicorn启动

        class UvicornLoguruHandler(logging.Handler):
            """将 uvicorn 日志转发到 loguru"""

            def emit(self, record):
                if record.name.startswith("uvicorn"):
                    bound_logger = loguru_logger.bind(
                        name=record.name,
                        function=record.funcName or "unknown",
                        line=record.lineno or 0,
                    )
                    bound_logger.log(record.levelname, record.getMessage())

        handler = UvicornLoguruHandler()

        # 替换所有uvicorn相关logger的处理器
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            specific_logger = logging.getLogger(logger_name)
            specific_logger.handlers.clear()
            specific_logger.addHandler(handler)
            specific_logger.setLevel(logging.INFO)

    # 启动处理器替换线程
    threading.Thread(target=replace_uvicorn_handlers, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    # 配置 uvicorn 日志
    setup_uvicorn_logging()

    # 运行 uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("SERVICE_PORT", "8000")),
        log_level="info",
    )


# 捕获所有未匹配的请求，返回统一格式的404错误
# 这个路由必须在最后注册，确保最低优先级
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    operation_id="catch_all_root_handler",
)
async def catch_all_root_handler(request: Request, path: str):
    """捕获所有未匹配的根级别请求，返回统一格式的404错误

    这个路由处理器会捕获所有没有被其他路由匹配的请求，
    统一返回符合项目规范的404错误响应格式。
    """
    from fastapi.responses import JSONResponse

    from shared.common.response import ErrorResponse

    logger.warning(
        f"未找到路由: {request.method} /{path}",
        extra={
            "method": request.method,
            "path": path,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else "unknown",
        },
    )

    # 检查是否是API路径但版本不正确
    error_message = "API版本不存在" if path.startswith("api/") else "请求的资源不存在"

    # 返回统一格式的404错误响应（移除 available_endpoints）
    error_response = ErrorResponse(
        code=404,
        message=error_message,
        error_code="RESOURCE_NOT_FOUND",
        details={
            "method": request.method,
            "path": f"/{path}",
        },
    )

    return JSONResponse(status_code=404, content=error_response.model_dump())
