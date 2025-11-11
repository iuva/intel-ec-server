"""
服务初始化工厂模块

提供统一的服务初始化、生命周期管理和健康检查等功能。
简化各微服务的主应用文件，减少重复代码。

设计原则：
1. 单一职责 - 每个类负责一个特定的初始化任务
2. 依赖注入 - 通过构造函数注入配置和依赖
3. 灵活可扩展 - 支持自定义处理器和中间件
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from urllib.parse import quote_plus

from fastapi import FastAPI
from sqlalchemy import text

from shared.common.cache import build_redis_url, redis_manager, validate_redis_config
from shared.common.database import close_databases, init_databases, mariadb_manager
from shared.common.loguru_config import get_logger
from shared.common.response import SuccessResponse
from shared.config.nacos_config import NacosManager
from shared.monitoring.jaeger import init_jaeger
from shared.monitoring.metrics import init_metrics
from shared.utils.docker_detection import (
    resolve_mariadb_host,
    resolve_nacos_host,
    resolve_redis_host,
)

logger = get_logger(__name__)


class ServiceConfig:
    """
    统一的服务配置类

    管理服务的所有配置信息，包括服务名称、端口、数据库连接等。

    属性：
        service_name: 服务名称
        service_port: 服务端口
        service_ip: 服务IP地址
        nacos_server_addr: Nacos服务器地址
        mariadb_url: MariaDB连接URL
        redis_url: Redis连接URL
        jwt_secret_key: JWT密钥
        jaeger_endpoint: Jaeger端点
        enable_nacos: 是否启用Nacos服务发现
        enable_jaeger: 是否启用Jaeger追踪
        enable_prometheus: 是否启用Prometheus监控
    """

    def __init__(
        self,
        service_name: str,
        service_port: Optional[int] = None,
        service_ip: Optional[str] = None,
        nacos_server_addr: Optional[str] = None,
        mariadb_url: Optional[str] = None,
        redis_url: Optional[str] = None,
        jwt_secret_key: Optional[str] = None,
        jaeger_endpoint: Optional[str] = None,
        hardware_api_url: Optional[str] = None,
        enable_nacos: bool = True,
        enable_jaeger: bool = True,
        enable_prometheus: bool = True,
    ):
        """
        初始化服务配置

        Args:
            service_name: 服务名称
            service_port: 服务端口
            service_ip: 服务 IP
            nacos_server_addr: Nacos 服务器地址
            mariadb_url: MariaDB 连接 URL
            redis_url: Redis 连接 URL
            jwt_secret_key: JWT 密钥
            jaeger_endpoint: Jaeger 端点
            hardware_api_url: 硬件接口基础 URL
            enable_nacos: 是否启用Nacos服务发现（默认：True）
            enable_jaeger: 是否启用Jaeger追踪（默认：True）
            enable_prometheus: 是否启用Prometheus监控（默认：True）
        """
        self.service_name = service_name
        self.service_port = service_port
        self.service_ip = service_ip
        self.nacos_server_addr = nacos_server_addr
        self.mariadb_url = mariadb_url
        self.redis_url = redis_url
        self.jwt_secret_key = jwt_secret_key

        self.jaeger_endpoint = jaeger_endpoint
        self.hardware_api_url = hardware_api_url

        # 组件开关配置
        self.enable_nacos = enable_nacos
        self.enable_jaeger = enable_jaeger
        self.enable_prometheus = enable_prometheus

    @staticmethod
    def from_env(service_name: str, service_port_key: str = "SERVICE_PORT") -> "ServiceConfig":
        """
        从环境变量创建服务配置

        Args:
            service_name: 服务名称
            service_port_key: 服务端口环境变量键名

        Returns:
            ServiceConfig 实例
        """
        # 基础配置
        service_port = int(os.getenv(service_port_key, "8000"))
        service_ip = os.getenv("SERVICE_IP", "127.0.0.1")

        # Nacos 配置 - 智能解析主机地址
        nacos_host = resolve_nacos_host()
        nacos_port = os.getenv("NACOS_PORT", "8848")
        nacos_server_addr = os.getenv("NACOS_SERVER_ADDR", f"{nacos_host}:{nacos_port}")

        # 数据库配置 - 智能解析主机地址
        # 优先使用环境变量，否则根据运行环境自动选择
        mariadb_host = os.getenv("MARIADB_HOST") or resolve_mariadb_host(default_in_docker="mariadb")
        mariadb_port = os.getenv("MARIADB_PORT", "3306")
        # 默认用户和密码与 docker-compose.yml 保持一致
        mariadb_user = os.getenv("MARIADB_USER", "intel_user")
        mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
        mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

        encoded_***REMOVED***word = quote_plus(mariadb_***REMOVED***word)
        mariadb_url = (
            f"mysql+aiomysql://{mariadb_user}:{encoded_***REMOVED***word}@{mariadb_host}:{mariadb_port}/{mariadb_database}"
        )

        # Redis 配置 - 智能解析主机地址
        # 优先使用环境变量，否则根据运行环境自动选择
        redis_host = os.getenv("REDIS_HOST") or resolve_redis_host(default_in_docker="redis")
        redis_port_str = os.getenv("REDIS_PORT", "6379")
        redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
        redis_db_str = os.getenv("REDIS_DB", "0")
        redis_username = os.getenv("REDIS_USERNAME")

        try:
            redis_host, redis_port, redis_db = validate_redis_config(redis_host, redis_port_str, redis_db_str)
            redis_url = build_redis_url(
                host=redis_host,
                port=redis_port,
                ***REMOVED***word=redis_***REMOVED***word if redis_***REMOVED***word else None,
                db=redis_db,
                username=redis_username,
            )
        except ValueError as e:
            logger.warning(f"Redis 配置验证失败: {e}, 使用默认配置")
            redis_url = f"redis://{redis_host}:6379/0"

        # JWT和Jaeger配置
        jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")

        # 外部服务 API 配置
        hardware_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")

        # 组件开关配置（支持环境变量，默认启用）
        # 环境变量值：true/True/1/yes/Yes 表示启用，其他值表示禁用
        def parse_bool_env(env_key: str, default: bool = True) -> bool:
            """解析布尔环境变量"""
            value = os.getenv(env_key)
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes", "on", "enabled")

        enable_nacos = parse_bool_env("ENABLE_NACOS", default=True)
        enable_jaeger = parse_bool_env("ENABLE_JAEGER", default=True)
        enable_prometheus = parse_bool_env("ENABLE_PROMETHEUS", default=True)

        return ServiceConfig(
            service_name=service_name,
            service_port=service_port,
            service_ip=service_ip,
            nacos_server_addr=nacos_server_addr,
            mariadb_url=mariadb_url,
            redis_url=redis_url,
            jwt_secret_key=jwt_secret_key,
            jaeger_endpoint=jaeger_endpoint,
            hardware_api_url=hardware_api_url,
            enable_nacos=enable_nacos,
            enable_jaeger=enable_jaeger,
            enable_prometheus=enable_prometheus,
        )


class ServiceLifecycleManager:
    """
    统一的服务生命周期管理

    管理服务的启动、运行和关闭阶段，简化各微服务的重复代码。

    功能：
    - 数据库连接初始化和关闭
    - Redis连接初始化和关闭
    - Nacos服务注册和注销
    - 自定义启动和关闭处理器
    """

    def __init__(
        self,
        config: ServiceConfig,
        startup_handlers: Optional[List[Callable]] = None,
        shutdown_handlers: Optional[List[Callable]] = None,
    ):
        """
        初始化生命周期管理器

        Args:
            config: 服务配置
            startup_handlers: 启动时执行的处理器列表
            shutdown_handlers: 关闭时执行的处理器列表
        """
        self.config = config
        self.startup_handlers = startup_handlers or []
        self.shutdown_handlers = shutdown_handlers or []
        self.nacos_manager: Optional[NacosManager] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def startup(self, app: FastAPI) -> None:
        """
        执行服务启动流程

        按以下顺序执行：
        1. 初始化数据库连接
        2. 初始化Jaeger追踪
        3. 初始化监控指标
        4. 注册异常处理器（统一错误响应格式）
        5. 初始化Nacos服务注册
        6. 执行自定义启动处理器

        """
        logger.info(f"{self.config.service_name} 启动中...")

        try:
            # 1. 初始化数据库连接
            logger.info("初始化数据库连接...")
            if not self.config.mariadb_url or not self.config.redis_url:
                logger.error("数据库配置不完整，无法初始化")
                raise ValueError("MariaDB URL 和 Redis URL 必须配置")

            await init_databases(
                mariadb_url=self.config.mariadb_url,
                redis_url=self.config.redis_url,
            )
            logger.info("数据库连接初始化成功")

            # 2. 初始化Jaeger追踪（根据开关）
            if self.config.enable_jaeger and self.config.jaeger_endpoint:
                logger.info("初始化Jaeger追踪...")
                try:
                    init_jaeger(
                        service_name=self.config.service_name,
                        jaeger_endpoint=self.config.jaeger_endpoint,
                        environment=os.getenv("ENVIRONMENT", "production"),
                        service_version="1.0.0",
                    )
                    # ❌ 注意：不要在这里调用 auto_instrument_app(app)
                    # 因为应用已经在处理请求，无法再添加中间件
                    # auto_instrument_app(app)
                    logger.info("Jaeger 追踪初始化成功")
                except Exception as e:
                    logger.warning(f"Jaeger 追踪初始化失败: {e!s}, 继续运行...")

            # 3. 初始化监控指标（根据开关）
            if self.config.enable_prometheus:
                logger.info("初始化监控指标...")
                try:
                    init_metrics(
                        service_name=self.config.service_name,
                        service_version="1.0.0",
                        environment=os.getenv("ENVIRONMENT", "production"),
                    )
                    logger.info("监控指标初始化成功")
                except Exception as e:
                    logger.warning(f"监控指标初始化失败: {e!s}, 继续运行...")

            # ❌ 不要在这里注册异常处理器！
            # 异常处理器必须在 FastAPI app 创建时就注册（在 main.py 中）
            # 在 lifespan 启动时注册会导致重复注册，破坏路由表
            # 参考: services/*/app/main.py - app.add_middleware(UnifiedExceptionMiddleware)

            # 5. 初始化Nacos服务注册（根据开关）
            if self.config.enable_nacos:
                logger.info("初始化Nacos服务发现...")
                await self._init_nacos(app)
                logger.info("Nacos 初始化完成")

            # 6. 设置 Nacos 管理器到服务发现实例（仅在启用Nacos时）
            if (
                self.config.enable_nacos
                and hasattr(app.state, "service_discovery")
                and app.state.service_discovery
                and self.nacos_manager
            ):
                app.state.service_discovery.set_nacos_manager(self.nacos_manager)
                logger.info("✅ 服务发现已连接到 Nacos")

            # 6. 执行自定义启动处理器
            for handler in self.startup_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(app)
                else:
                    handler(app)

            logger.info(f"{self.config.service_name} 启动成功")

        except Exception as e:
            logger.error(f"{self.config.service_name} 启动失败: {e!s}", exc_info=True)
            raise

    async def _init_nacos(self, app: FastAPI) -> None:
        """初始化Nacos服务发现和注册"""
        if not self.config.nacos_server_addr or not self.config.service_port:
            logger.warning("Nacos 配置不完整，跳过服务注册")
            return

        # 确保 service_ip 不为 None
        if not self.config.service_ip:
            logger.warning("服务IP未配置，跳过Nacos注册")
            return

        try:
            # 获取Nacos认证信息
            nacos_username = os.getenv("NACOS_USERNAME", "nacos")
            nacos_***REMOVED***word = os.getenv("NACOS_PASSWORD", "nacos")
            nacos_namespace = os.getenv("NACOS_NAMESPACE", "public")
            nacos_group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")

            # 创建Nacos管理器
            self.nacos_manager = NacosManager(
                server_addresses=self.config.nacos_server_addr.replace("http://", ""),
                namespace=nacos_namespace,
                group=nacos_group,
                username=nacos_username,
                ***REMOVED***word=nacos_***REMOVED***word,
            )

            # 注册服务
            success = await self.nacos_manager.register_service(
                service_name=self.config.service_name,
                ip=self.config.service_ip,
                port=self.config.service_port,
                ephemeral=True,
                metadata={
                    "version": "1.0.0",
                    "environment": os.getenv("ENVIRONMENT", "production"),
                },
            )

            if success:
                # 启动心跳检测
                self.heartbeat_task = asyncio.create_task(
                    self.nacos_manager.start_heartbeat(
                        service_name=self.config.service_name,
                        ip=self.config.service_ip,
                        port=self.config.service_port,
                        interval=5,
                    )
                )
                # 存储任务引用以防止被垃圾回收
                app.state.nacos_heartbeat_task = self.heartbeat_task
                logger.info("Nacos 服务注册和心跳检测启动成功")
            else:
                logger.warning("Nacos 服务注册失败")

        except Exception as e:
            logger.warning(f"Nacos 初始化失败: {e!s}, 继续运行...")

    async def shutdown(self, app: Optional[FastAPI] = None) -> None:
        """
        执行服务关闭流程

        按以下顺序执行：
        1. 执行自定义关闭处理器
        2. 停止Nacos心跳检测
        3. 关闭数据库连接

        Args:
            app: FastAPI 应用实例（可选，传递给关闭处理器）
        """
        logger.info(f"{self.config.service_name} 关闭中...")

        try:
            # 1. 执行自定义关闭处理器
            for handler in self.shutdown_handlers:
                if asyncio.iscoroutinefunction(handler):
                    # 检查函数签名，如果需要一个参数（app），则传递它
                    import inspect
                    sig = inspect.signature(handler)
                    params = list(sig.parameters.keys())
                    if len(params) > 0:
                        await handler(app)
                    else:
                        await handler()
                else:
                    import inspect
                    sig = inspect.signature(handler)
                    params = list(sig.parameters.keys())
                    if len(params) > 0:
                        handler(app)
                    else:
                        handler()

            # 2. 停止Nacos心跳检测（仅在启用Nacos时）
            if self.config.enable_nacos and self.nacos_manager:
                self.nacos_manager.stop_heartbeat()
                logger.info("Nacos 心跳检测已停止")

            # 3. 关闭数据库连接
            await close_databases()
            logger.info("数据库连接已关闭")

            logger.info(f"{self.config.service_name} 关闭完成")

        except Exception as e:
            logger.error(f"{self.config.service_name} 关闭异常: {e!s}", exc_info=True)


class HealthCheckManager:
    """
    统一的健康检查管理

    提供标准化的健康检查端点，检查数据库、Redis 等依赖服务的状态。

    功能：
    - 健康状态检查（数据库、Redis）
    - 结构化的健康检查响应
    - 支持降级模式（部分服务不可用）
    """

    @staticmethod
    async def perform_health_check() -> SuccessResponse:
        """
        执行健康检查

        检查所有依赖服务的状态，返回整体健康状态。

        返回值：
            SuccessResponse，包含：
            - database: 数据库连接状态
            - redis: Redis连接状态
            - overall_status: 整体状态（healthy/degraded/unhealthy）
        """
        # 检查数据库连接
        db_status = await HealthCheckManager._check_database()

        # 检查 Redis 连接
        redis_status = await HealthCheckManager._check_redis()

        # 确定整体状态
        if db_status["status"] == "healthy" and redis_status["status"] == "healthy":
            overall_status = "healthy"
        elif db_status["status"] == "unhealthy":
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return SuccessResponse(
            data={
                "status": overall_status,
                "components": {
                    "database": db_status,
                    "redis": redis_status,
                },
            },
            message=f"服务状态: {overall_status}",
        )

    @staticmethod
    async def _check_database() -> Dict[str, Any]:
        """检查数据库连接状态"""
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
                return {"status": "healthy", "details": {"message": "数据库连接正常"}}
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e!s}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e), "message": "数据库连接异常"},
            }

    @staticmethod
    async def _check_redis() -> Dict[str, Any]:
        """检查 Redis 连接状态"""
        try:
            if redis_manager.is_connected and redis_manager.client:
                await redis_manager.client.ping()
                return {
                    "status": "healthy",
                    "details": {
                        "message": "Redis 连接正常",
                        "mode": "cached",
                    },
                }
            return {
                "status": "unavailable",
                "details": {
                    "message": "Redis 未连接，服务运行在降级模式（无缓存）",
                    "mode": "degraded",
                },
            }
        except Exception as e:
            logger.warning(f"Redis 健康检查失败: {e!s}")
            return {
                "status": "unavailable",
                "details": {
                    "error": str(e),
                    "message": "Redis 连接异常，服务运行在降级模式（无缓存）",
                    "mode": "degraded",
                },
            }


def create_service_lifespan(
    config: ServiceConfig,
    startup_handlers: Optional[List[Callable]] = None,
    shutdown_handlers: Optional[List[Callable]] = None,
) -> Callable:
    """
    创建服务生命周期上下文管理器

    简化各微服务创建生命周期处理的代码。

    Args:
        config: 服务配置
        startup_handlers: 启动时执行的处理器列表
        shutdown_handlers: 关闭时执行的处理器列表

    Returns:
        异步生命周期上下文管理器

    示例：
        ```python
        config = ServiceConfig.from_env("my-service", "MY_SERVICE_PORT")
        app = FastAPI(lifespan=create_service_lifespan(config))
        ```
    """
    manager = ServiceLifecycleManager(config, startup_handlers, shutdown_handlers)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """生命周期处理"""
        await manager.startup(app)
        yield
        await manager.shutdown(app)

    return lifespan
