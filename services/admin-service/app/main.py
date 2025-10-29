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

    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from app.api.v1 import api_router

    from shared.app import ServiceConfig, create_service_lifespan, include_health_routes
    from shared.common.loguru_config import configure_logger, get_logger
    from shared.middleware.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.metrics_endpoint import router as metrics_router
    from shared.middleware.exception_middleware import UnifiedExceptionMiddleware

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

# 添加 Prometheus 指标收集中间件
app.add_middleware(PrometheusMetricsMiddleware, service_name=service_name)

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
