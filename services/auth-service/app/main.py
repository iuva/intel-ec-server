"""
Auth Service 主应用入口

提供用户认证、JWT令牌管理等功能
"""

import asyncio
from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 使用 try-except 方式处理路径导入
try:
    from shared.common.cache import build_redis_url, mask_sensitive_info, validate_redis_config
    from shared.common.database import close_databases, init_databases
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from shared.common.cache import build_redis_url, mask_sensitive_info, validate_redis_config
    from shared.common.database import close_databases, init_databases
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics

# 配置日志（在应用启动前配置）
service_name = os.getenv("AUTH_SERVICE_NAME", "auth-service")
configure_logger(service_name=service_name, log_level="INFO")

logger = get_logger(__name__)

# Nacos管理器
nacos_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    global nacos_manager

    # 启动时执行
    service_name = os.getenv("AUTH_SERVICE_NAME", "auth-service")
    service_port = int(os.getenv("AUTH_SERVICE_PORT", "8001"))
    service_ip = os.getenv("AUTH_SERVICE_IP", "172.20.0.101")
    nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", "172.20.0.12:8848")

    logger.info(f"{service_name} 服务启动中... 端口: {service_port}")

    # 初始化数据库连接
    # 从环境变量构建 MariaDB URL
    mariadb_host = os.getenv("MARIADB_HOST", "mariadb")
    mariadb_port = os.getenv("MARIADB_PORT", "3306")
    mariadb_user = os.getenv("MARIADB_USER", "intel_user")
    mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
    mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

    # URL编码密码中的特殊字符
    from urllib.parse import quote_plus

    mariadb_***REMOVED***word_encoded = quote_plus(mariadb_***REMOVED***word)

    mariadb_url = (
        f"mysql+aiomysql://{mariadb_user}:{mariadb_***REMOVED***word_encoded}@{mariadb_host}:{mariadb_port}/{mariadb_database}"
    )

    # 从环境变量构建 Redis URL
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port_str = os.getenv("REDIS_PORT", "11001")
    redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
    redis_db_str = os.getenv("REDIS_DB", "0")
    redis_username = os.getenv("REDIS_USERNAME")  # Redis 6.0+ 可选

    # 验证 Redis 配置
    try:
        redis_host, redis_port, redis_db = validate_redis_config(redis_host, redis_port_str, redis_db_str)
    except ValueError as e:
        logger.error(f"Redis 配置验证失败: {e}")
        # 使用默认值
        redis_host = "redis"
        redis_port = 11001
        redis_db = 0

    # 使用新的 build_redis_url 函数构建 URL
    redis_url = build_redis_url(
        host=redis_host,
        port=redis_port,
        ***REMOVED***word=redis_***REMOVED***word if redis_***REMOVED***word else None,
        db=redis_db,
        username=redis_username,
    )

    # 记录 Redis 配置信息（脱敏）
    masked_redis_url = mask_sensitive_info(redis_url)
    logger.info(f"Redis 配置: host={redis_host}, port={redis_port}, db={redis_db}, url={masked_redis_url}")

    await init_databases(
        mariadb_url=mariadb_url,
        redis_url=redis_url,
    )

    # 初始化监控指标
    init_metrics(
        service_name=service_name,
        service_version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "production"),
    )

    # Jaeger 追踪已在应用创建时初始化

    # 初始化Nacos（从环境变量读取认证信息）
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
        success = await nacos_manager.register_service(
            service_name=service_name,
            ip=service_ip,
            port=service_port,
            ephemeral=True,
            metadata={
                "version": "1.0.0",
                "environment": "production",
                "service_type": "auth",
            },
        )

        if success:
            # 启动心跳检测
            heartbeat_task = asyncio.create_task(
                nacos_manager.start_heartbeat(
                    service_name=service_name,
                    ip=service_ip,
                    port=service_port,
                    interval=5,
                )
            )
            # 存储任务引用以避免垃圾回收
            app.state.heartbeat_task = heartbeat_task
            logger.info(f"{service_name} 服务注册成功")
        else:
            logger.error(f"{service_name} 服务注册失败")

    except Exception as e:
        logger.error(f"Nacos初始化异常: {e!s}")

    logger.info(f"{service_name} 服务启动完成")

    yield

    # 关闭时执行
    logger.info(f"{service_name} 服务关闭中...")

    try:
        if nacos_manager:
            nacos_manager.stop_heartbeat()
            logger.info("Nacos心跳检测已停止")
    except Exception as e:
        logger.error(f"Nacos心跳检测停止异常: {e!s}")

    # 关闭数据库连接
    await close_databases()

    logger.info(f"{service_name} 服务关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="Auth Service API",
    description="认证服务 - 提供用户认证、JWT令牌管理等功能",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 初始化 Jaeger 追踪器（在应用创建时）
# ✅ 使用 gRPC 端点（4317）而不是 HTTP 端点（4318）
jaeger_endpoint_host = os.getenv("JAEGER_ENDPOINT_HOST", "jaeger:4317")
jaeger_endpoint = jaeger_endpoint_host
try:
    init_jaeger(
        service_name=service_name,
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

# 添加CORS中间件
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

    setup_exception_handling(app, service_name)
    logger.info("统一异常处理中间件已启用")
except Exception as e:
    logger.error(f"添加统一异常处理失败: {e!s}", exc_info=True)

# 添加指标收集中间件（在最后添加，确保捕获所有请求）
try:
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware

    # 正确的方式：传递中间件类和初始化参数
    app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)
    logger.info("Prometheus指标收集中间件已启用")
except Exception as e:
    logger.warning(f"添加指标收集中间件失败: {e!s}")


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查

    返回服务的健康状态，包括数据库和 Redis 的状态。

    状态说明：
    - healthy: 所有组件正常运行
    - degraded: 部分组件不可用（如 Redis），但核心功能可用
    - unhealthy: 核心组件（如数据库）不可用
    """
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.response import SuccessResponse

    # 检查数据库连接（核心组件）
    db_status = "healthy"
    db_details = None
    try:
        from sqlalchemy import text

        session_factory = mariadb_manager.get_session()
        async with session_factory() as db_session:
            await db_session.execute(text("SELECT 1"))
            db_details = {"connected": True, "message": "数据库连接正常"}
    except Exception as e:
        db_status = "unhealthy"
        db_details = {"connected": False, "error": str(e)}
        logger.error(f"数据库健康检查失败: {e!s}")

    # 检查 Redis 连接（可选组件）
    redis_status = "unavailable"
    redis_details = None

    if redis_manager.is_connected and redis_manager.client:
        try:
            await redis_manager.client.ping()
            redis_status = "healthy"
            redis_details = {"connected": True, "message": "Redis 连接正常", "mode": "cached"}
        except Exception as e:
            redis_status = "unhealthy"
            redis_details = {"connected": False, "error": str(e), "mode": "degraded"}
            logger.warning(f"Redis 健康检查失败: {e!s}")
    else:
        # Redis 未连接，服务运行在降级模式
        redis_status = "unavailable"
        redis_details = {
            "connected": False,
            "message": "Redis 未连接，服务运行在降级模式（无缓存）",
            "mode": "degraded",
        }

    # 确定整体服务状态
    # - 数据库不可用 -> unhealthy
    # - 数据库正常但 Redis 不可用 -> degraded
    # - 所有组件正常 -> healthy
    if db_status == "unhealthy":
        overall_status = "unhealthy"
        status_message = "服务不可用：数据库连接失败"
    elif redis_status != "healthy":
        overall_status = "degraded"
        status_message = "服务运行在降级模式：Redis 不可用"
    else:
        overall_status = "healthy"
        status_message = "服务运行正常"

    return SuccessResponse(
        data={
            "service": service_name,
            "version": "1.0.0",
            "status": overall_status,
            "components": {
                "database": {"status": db_status, "details": db_details},
                "redis": {"status": redis_status, "details": redis_details},
            },
        },
        message=status_message,
    )


# Prometheus 指标端点
@app.get("/metrics")
async def metrics():
    """Prometheus 指标"""

    return get_metrics_response()


# 测试端点 - 在API路由之前注册
@app.get("/test")
async def test_endpoint():
    """测试dict响应格式"""
    from shared.common.response import ErrorResponse

    error_response = ErrorResponse(
        code=401,
        message="测试错误",
        error_code="TEST_ERROR",
    )
    result = error_response.model_dump()
    logger.debug(f"测试端点返回: {result}")
    return result


# 注册 API 路由 - 使用 try-except 处理导入
try:
    from app.api.v1 import api_router

    app.include_router(api_router, prefix="/api/v1")
except ImportError as e:
    logger.error(f"API 路由导入失败: {e!s}")
    raise


# 根路径端点
@app.get("/")
async def root():
    """根路径"""
    from shared.common.response import SuccessResponse

    return SuccessResponse(
        data={
            "service": service_name,
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        },
        message="Auth Service 运行正常",
    )


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

    uvicorn.run(app, host="0.0.0.0", port=8001)
