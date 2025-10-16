"""Host Service 主应用入口

提供主机管理和 WebSocket 实时通信功能

注意：此服务需要在项目根目录运行，或设置 PYTHONPATH 环境变量
运行方式：
  1. 从项目根目录: python -m services.host_service.app.main
  2. 使用启动脚本: python services/host-service/run.py
  3. 设置环境变量: export PYTHONPATH=/path/to/project && python app/main.py
"""

from contextlib import asynccontextmanager
import os
import sys
from typing import AsyncGenerator, Optional, Tuple
from urllib.parse import quote_plus

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import close_databases, init_databases
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.database import close_databases, init_databases
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics

# 配置日志（在应用启动前配置）
service_name = os.getenv("SERVICE_NAME", "host-service")
configure_logger(service_name=service_name, log_level="INFO")

logger = get_logger(__name__)

# Nacos 管理器实例
nacos_manager: Optional[NacosManager] = None


def _build_host_database_urls() -> Tuple[str, str]:
    """构建Host Service数据库连接URL"""
    # 从环境变量构建 MariaDB URL
    mariadb_host = os.getenv("MARIADB_HOST", "localhost")
    mariadb_port = os.getenv("MARIADB_PORT", "3306")
    mariadb_user = os.getenv("MARIADB_USER", "root")
    mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "***REMOVED***word")
    mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

    # URL 编码密码中的特殊字符
    encoded_***REMOVED***word = quote_plus(mariadb_***REMOVED***word)

    mariadb_url = f"mysql+aiomysql://{mariadb_user}:{encoded_***REMOVED***word}@{mariadb_host}:{mariadb_port}/{mariadb_database}"

    # Redis 配置 (Host Service使用DB 3)
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
    redis_db = os.getenv("REDIS_DB", "3")

    if redis_***REMOVED***word:
        redis_url = f"redis://:{quote_plus(redis_***REMOVED***word)}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    return mariadb_url, redis_url


def _get_host_service_config() -> Tuple[str, str, int]:
    """获取Host Service配置"""
    nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", "http://localhost:8848")
    service_ip = os.getenv("SERVICE_IP", "127.0.0.1")
    service_port = int(os.getenv("SERVICE_PORT", "8003"))
    return nacos_server_addr, service_ip, service_port


async def _initialize_host_databases() -> None:
    """初始化Host Service数据库连接"""
    mariadb_url, redis_url = _build_host_database_urls()
    await init_databases(mariadb_url=mariadb_url, redis_url=redis_url)
    logger.info("数据库连接初始化完成")


async def _initialize_host_nacos(app: FastAPI) -> None:
    """初始化Host Service Nacos服务发现"""
    global nacos_manager

    nacos_server_addr, service_ip, service_port = _get_host_service_config()

    # 从环境变量读取 Nacos 认证信息
    nacos_username = os.getenv("NACOS_USERNAME", "nacos")
    nacos_***REMOVED***word = os.getenv("NACOS_PASSWORD", "nacos")
    nacos_namespace = os.getenv("NACOS_NAMESPACE", "public")
    nacos_group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")

    try:
        nacos_manager = NacosManager(
            server_addresses=nacos_server_addr.replace("http://", ""),
            namespace=nacos_namespace,
            group=nacos_group,
            username=nacos_username,
            ***REMOVED***word=nacos_***REMOVED***word,
        )

        # 注册服务
        if nacos_manager is not None:
            success = await nacos_manager.register_service(
                service_name="host-service",
                ip=service_ip,
                port=service_port,
                ephemeral=True,
                metadata={"version": "1.0.0", "environment": "production"},
            )

            if success:
                logger.info(f"服务注册成功: host-service ({service_ip}:{service_port})")
                # 启动心跳检测
                import asyncio

                heartbeat_task = asyncio.create_task(
                    nacos_manager.start_heartbeat(
                        service_name="host-service",
                        ip=service_ip,
                        port=service_port,
                        interval=5,
                    )
                )
                # 存储任务引用以防止被垃圾回收
                app.state.heartbeat_task = heartbeat_task
            else:
                logger.error("服务注册失败")
    except Exception as e:
        logger.error(f"Nacos 初始化异常: {e!s}")


async def _cleanup_host_resources() -> None:
    """清理Host Service资源"""
    global nacos_manager

    logger.info("Host Service 关闭中...")

    try:
        if nacos_manager:
            nacos_manager.stop_heartbeat()
            logger.info("Nacos心跳检测已停止")
    except Exception as e:
        logger.error(f"Nacos心跳检测停止异常: {e!s}")

    # 关闭数据库连接
    await close_databases()

    logger.info("Host Service 关闭完成")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    logger.info("Host Service 启动中...")

    # 初始化数据库连接
    await _initialize_host_databases()

    # Jaeger 追踪已在应用创建时初始化

    # 初始化 Nacos 服务发现
    await _initialize_host_nacos(app)

    logger.info("Host Service 启动完成")

    yield

    # 关闭时清理资源
    await _cleanup_host_resources()


# 创建 FastAPI 应用
app = FastAPI(
    title="Host Service",
    description="主机管理和 WebSocket 实时通信服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加指标收集中间件
try:
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware

    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("Prometheus指标收集中间件已启用")
except Exception as e:
    logger.warning(f"添加指标收集中间件失败: {e!s}")

# 初始化 Jaeger 追踪器（在应用创建时）
jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4318/v1/traces")
try:
    init_jaeger(
        service_name="host-service",
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

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加统一异常处理中间件
try:
    from shared.app.exception_handler import setup_exception_handling

    setup_exception_handling(app, "host-service")
    logger.info("统一异常处理中间件已启用")
except Exception as e:
    logger.error(f"添加统一异常处理失败: {e!s}", exc_info=True)

# 初始化 Prometheus 指标
init_metrics(service_name="host-service", service_version="1.0.0", environment="production")


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    from shared.common.response import SuccessResponse

    return SuccessResponse(
        data={"service": "host-service", "status": "healthy", "version": "1.0.0"},
        message="服务运行正常",
    )


# 根路径端点
@app.get("/")
async def root():
    """根路径"""
    from shared.common.response import SuccessResponse

    return SuccessResponse(
        data={
            "service": "host-service",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        },
        message="Host Service 运行正常",
    )


# Prometheus 指标端点
@app.get("/metrics")
async def metrics():
    """Prometheus 监控指标"""

    return get_metrics_response()


# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


# 捕获所有未匹配的请求，返回统一格式的404错误
# 这个路由必须在最后注册，确保最低优先级
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    operation_id="host_service_catch_all_handler",
)
async def catch_all_handler(request: Request, path: str):
    """捕获所有未匹配的请求，返回统一格式的404错误

    这个路由处理器会捕获所有没有被其他路由匹配的请求，
    统一返回符合项目规范的404错误响应格式。
    """
    from fastapi.responses import JSONResponse

    # 使用 try-except 方式处理路径导入
    try:
        from shared.common.response import ErrorResponse
    except ImportError:
        import sys

        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
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

    # 返回统一格式的404错误响应
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


if __name__ == "__main__":
    import logging
    import threading
    import time

    from loguru import logger
    import uvicorn

    # 禁用uvicorn的默认日志处理器
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()

    # 运行uvicorn
    def replace_uvicorn_handlers():
        """在uvicorn启动后替换其处理器"""
        time.sleep(1)  # 等待uvicorn启动

        class UvicornLoguruHandler(logging.Handler):
            def emit(self, record):
                if record.name.startswith("uvicorn"):
                    loguru_logger = logger.bind(
                        name=record.name,
                        function=record.funcName or "unknown",
                        line=record.lineno or 0,
                    )
                    loguru_logger.log(record.levelname, record.getMessage())

        handler = UvicornLoguruHandler()

        # 替换所有uvicorn相关logger的处理器
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            specific_logger = logging.getLogger(logger_name)
            specific_logger.handlers.clear()
            specific_logger.addHandler(handler)
            specific_logger.setLevel(logging.INFO)

    # 启动处理器替换线程
    threading.Thread(target=replace_uvicorn_handlers, daemon=True).start()

    port = int(os.getenv("SERVICE_PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
