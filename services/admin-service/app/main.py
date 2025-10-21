"""
Admin Service 主应用入口

提供后台管理、用户管理、系统配置等功能
"""

import asyncio
from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# 使用 try-except 方式处理路径导入
try:
    from shared.common.cache import build_redis_url, mask_sensitive_info, validate_redis_config
    from shared.common.database import close_databases, init_databases
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.common.response import SuccessResponse
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.cache import build_redis_url, mask_sensitive_info, validate_redis_config
    from shared.common.database import close_databases, init_databases
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.common.response import SuccessResponse
    from shared.config.nacos_config import NacosManager
    from shared.monitoring.jaeger import auto_instrument_app, init_jaeger
    from shared.monitoring.metrics import get_metrics_response, init_metrics

# 配置日志（在应用启动前配置）
service_name = os.getenv("ADMIN_SERVICE_NAME", "admin-service")
configure_logger(service_name=service_name, log_level="INFO")

logger = get_logger(__name__)

# Nacos管理器
nacos_manager = None


def _get_service_config() -> Tuple[str, int, str, str]:
    """获取服务配置"""
    service_name = os.getenv("ADMIN_SERVICE_NAME", "admin-service")
    service_port = int(os.getenv("ADMIN_SERVICE_PORT", "8002"))
    service_ip = os.getenv("ADMIN_SERVICE_IP", "172.20.0.102")
    nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", "172.20.0.12:8848")
    return service_name, service_port, service_ip, nacos_server_addr


def _build_database_urls() -> Tuple[str, str]:
    """构建数据库连接URL"""
    # 从环境变量构建 MariaDB URL（默认值与docker-compose.yml保持一致）
    mariadb_host = os.getenv("MARIADB_HOST", "mariadb")
    mariadb_port = os.getenv("MARIADB_PORT", "3306")
    mariadb_user = os.getenv("MARIADB_USER", "intel_user")
    mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
    mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

    # URL 编码密码中的特殊字符
    from urllib.parse import quote_plus

    encoded_***REMOVED***word = quote_plus(mariadb_***REMOVED***word)

    mariadb_url = f"mysql+aiomysql://{mariadb_user}:{encoded_***REMOVED***word}@{mariadb_host}:{mariadb_port}/{mariadb_database}"

    # Redis 配置 - 使用新的工具函数
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port_str = os.getenv("REDIS_PORT", "6379")
    redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
    redis_db_str = os.getenv("REDIS_DB", "2")

    try:
        # 验证 Redis 配置
        redis_host, redis_port, redis_db = validate_redis_config(redis_host, redis_port_str, redis_db_str)

        # 使用新的 build_redis_url 函数构建 URL
        redis_url = build_redis_url(
            host=redis_host,
            port=redis_port,
            ***REMOVED***word=redis_***REMOVED***word if redis_***REMOVED***word else None,
            db=redis_db,
        )

        # 记录 Redis 配置（脱敏）
        logger.info(
            f"Redis 配置: host={redis_host}, port={redis_port}, db={redis_db}, url={mask_sensitive_info(redis_url)}"
        )

    except ValueError as e:
        logger.error(f"Redis 配置验证失败: {e}")
        # 使用默认配置
        redis_url = f"redis://{redis_host}:6379/2"
        logger.warning(f"使用默认 Redis 配置: {redis_url}")

    return mariadb_url, redis_url


async def _initialize_databases() -> None:
    """初始化数据库连接"""
    try:
        mariadb_url, redis_url = _build_database_urls()
        logger.info("正在初始化数据库连接...")
        logger.info(f"MariaDB URL: {mariadb_url.replace(mariadb_url.split('@')[0].split('://')[1], '***:***')}")
        logger.info(f"Redis URL: {redis_url.replace(redis_url.split('@')[0] if '@' in redis_url else '', '***:***')}")

        await init_databases(mariadb_url=mariadb_url, redis_url=redis_url)
        logger.info("数据库连接初始化成功")

        # 测试数据库连接
        try:
            from shared.common.database import mariadb_manager

            # 尝试获取会话来测试连接
            session_factory = mariadb_manager.get_session()
            async with session_factory() as test_session:
                # 执行一个简单的查询来验证连接
                from sqlalchemy import text

                result = await test_session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                if row and row[0] == 1:
                    logger.info("数据库连接测试成功")
                else:
                    logger.warning("数据库连接测试失败：查询结果异常")
        except Exception as db_test_error:
            logger.error(f"数据库连接测试失败: {db_test_error}")
            raise RuntimeError(f"数据库连接测试失败: {db_test_error}")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        logger.error("请检查以下配置:")
        logger.error("  1. MariaDB服务是否运行")
        logger.error("  2. 数据库连接参数是否正确")
        logger.error("  3. 数据库用户权限是否正确")
        logger.error("  4. 网络连接是否正常")
        raise


def _initialize_monitoring() -> None:
    """初始化监控指标"""
    init_metrics(
        service_name=service_name,
        service_version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "production"),
    )


async def _initialize_nacos(app: FastAPI) -> None:
    """初始化Nacos服务发现"""
    global nacos_manager

    service_name, service_port, service_ip, nacos_server_addr = _get_service_config()

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
                "service_type": "admin",
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
            # 存储任务引用以防止被垃圾回收
            app.state.heartbeat_task = heartbeat_task
            logger.info(f"{service_name} 服务注册成功")
        else:
            logger.error(f"{service_name} 服务注册失败")

    except Exception as e:
        logger.error(f"Nacos初始化异常: {e!s}")


async def _cleanup_resources() -> None:
    """清理资源"""
    global nacos_manager

    logger.info("admin-service 服务关闭中...")

    try:
        if nacos_manager:
            nacos_manager.stop_heartbeat()
            logger.info("Nacos心跳检测已停止")
    except Exception as e:
        logger.error(f"Nacos心跳检测停止异常: {e!s}")

    # 关闭数据库连接
    await close_databases()

    logger.info("admin-service 服务关闭完成")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    service_name, service_port, _, _ = _get_service_config()

    logger.info(f"{service_name} 服务启动中... 端口: {service_port}")

    # 初始化数据库连接
    await _initialize_databases()

    # 初始化监控指标
    _initialize_monitoring()

    # 初始化Nacos服务发现
    await _initialize_nacos(app)

    # Jaeger 追踪已在应用创建时初始化

    logger.info(f"{service_name} 服务启动完成")

    yield

    # 关闭时清理资源
    await _cleanup_resources()


# 创建FastAPI应用
app = FastAPI(
    title="Admin Service API",
    description="管理服务 - 提供后台管理、用户管理、系统配置等功能",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 初始化 Jaeger 追踪器（在应用创建时）
jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4318/v1/traces")
try:
    init_jaeger(
        service_name="admin-service",
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

    setup_exception_handling(app, "admin-service")
    logger.info("统一异常处理中间件已启用")
except Exception as e:
    logger.error(f"添加统一异常处理失败: {e!s}", exc_info=True)

# 添加请求验证错误的详细处理
try:
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

    from shared.common.response import ErrorResponse

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误，提供详细的错误信息

        Args:
            request: 请求对象
            exc: 验证错误异常

        Returns:
            详细的验证错误响应
        """
        # 记录详细的验证错误信息
        logger.warning(
            "请求验证失败",
            extra={
                "operation": "request_validation",
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "validation_errors": [
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "error_type": error["type"],
                        "input_value": str(error.get("input", ""))[:100],  # 限制输入值长度
                    }
                    for error in exc.errors()
                ],
                "error_count": len(exc.errors()),
            },
        )

        # 构建详细的错误响应
        field_errors = [
            {"field": ".".join(str(loc) for loc in error["loc"]), "message": error["msg"], "error_type": error["type"]}
            for error in exc.errors()
        ]

        error_response = ErrorResponse(
            code=HTTP_422_UNPROCESSABLE_ENTITY,
            message="请求参数验证失败",
            error_code="VALIDATION_ERROR",
            details={"field_errors": field_errors, "total_errors": len(field_errors)},
        )

        return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump())

    logger.info("请求验证错误处理器已启用")

except Exception as e:
    logger.warning(f"添加请求验证错误处理器失败: {e!s}")

# 添加指标收集中间件（在最后添加，确保捕获所有请求）
try:
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware

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
    from sqlalchemy import text

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.response import SuccessResponse

    # 检查数据库连接（核心组件）
    db_status = "healthy"
    db_details = None
    try:
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
            "service": "admin-service",
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

    return SuccessResponse(
        data={
            "service": "admin-service",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        },
        message="Admin Service 运行正常",
    )


# 捕获所有未匹配的请求，返回统一格式的404错误
# 这个路由必须在最后注册，确保最低优先级
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    operation_id="admin_service_catch_all_handler",
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

    from loguru import logger
    import uvicorn

    # 禁用uvicorn的默认日志处理器
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()

    # 运行uvicorn
    import threading
    import time

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

    uvicorn.run(app, host="0.0.0.0", port=8002)
