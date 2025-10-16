"""
FastAPI应用模板模块

提供统一的FastAPI应用创建和配置功能
"""

from contextlib import asynccontextmanager
import logging
import time
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.common.cache import redis_manager
from shared.common.database import mariadb_manager
from shared.common.exceptions import BusinessError
from shared.common.loguru_config import configure_logger
from shared.common.response import create_error_response, create_success_response
from shared.common.security import init_jwt_manager
from shared.monitoring.jaeger import jaeger_manager
from shared.monitoring.metrics import get_metrics_response, init_metrics, metrics_collector

logger = logging.getLogger(__name__)


def create_lifespan_handler(
    service_name: str,
    database_url: Optional[str] = None,
    redis_url: Optional[str] = None,
    jwt_secret_key: Optional[str] = None,
    jaeger_endpoint: Optional[str] = None,
    startup_handlers: Optional[List[Callable]] = None,
    shutdown_handlers: Optional[List[Callable]] = None,
) -> Callable:
    """创建应用生命周期处理器

    Args:
        service_name: 服务名称
        database_url: 数据库连接URL
        redis_url: Redis连接URL
        jwt_secret_key: JWT密钥
        jaeger_endpoint: Jaeger端点
        startup_handlers: 启动时执行的处理器列表
        shutdown_handlers: 关闭时执行的处理器列表

    Returns:
        生命周期上下文管理器
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """应用生命周期管理"""
        # ==================== 启动阶段 ====================
        logger.info(f"{service_name} 服务启动中...")

        # 初始化数据库连接
        if database_url:
            try:
                await mariadb_manager.connect(database_url)
                logger.info("数据库连接成功")
            except Exception as e:
                logger.error(f"数据库连接失败: {e!s}")
                raise

        # 初始化Redis连接
        if redis_url:
            try:
                await redis_manager.connect(redis_url)
                logger.info("Redis连接成功")
            except Exception as e:
                logger.warning(f"Redis连接失败: {e!s}, 降级到无缓存模式")

        # 初始化JWT管理器
        if jwt_secret_key:
            try:
                init_jwt_manager(jwt_secret_key)
                logger.info("JWT管理器初始化成功")
            except Exception as e:
                logger.error(f"JWT管理器初始化失败: {e!s}")

        # 初始化Jaeger追踪
        if jaeger_endpoint:
            try:
                jaeger_manager.init_tracer(service_name=service_name, jaeger_endpoint=jaeger_endpoint)
                jaeger_manager.instrument_fastapi(app)
                logger.info("Jaeger追踪初始化成功")
            except Exception as e:
                logger.warning(f"Jaeger追踪初始化失败: {e!s}")

        # 执行自定义启动处理器
        if startup_handlers:
            for handler in startup_handlers:
                try:
                    if callable(handler):
                        result = handler()
                        if hasattr(result, "__await__"):
                            await result
                except Exception as e:
                    logger.error(f"启动处理器执行失败: {e!s}")

        logger.info(f"{service_name} 服务启动完成")

        yield

        # ==================== 关闭阶段 ====================
        logger.info(f"{service_name} 服务关闭中...")

        # 执行自定义关闭处理器
        if shutdown_handlers:
            for handler in shutdown_handlers:
                try:
                    if callable(handler):
                        result = handler()
                        if hasattr(result, "__await__"):
                            await result
                except Exception as e:
                    logger.error(f"关闭处理器执行失败: {e!s}")

        # 关闭Jaeger追踪
        try:
            jaeger_manager.shutdown()
        except Exception as e:
            logger.error(f"Jaeger追踪关闭失败: {e!s}")

        # 关闭Redis连接
        try:
            await redis_manager.disconnect()
        except Exception as e:
            logger.error(f"Redis连接关闭失败: {e!s}")

        # 关闭数据库连接
        try:
            await mariadb_manager.disconnect()
        except Exception as e:
            logger.error(f"数据库连接关闭失败: {e!s}")

        logger.info(f"{service_name} 服务关闭完成")

    return lifespan


def create_exception_handlers() -> Dict[type, Callable]:
    """创建全局异常处理器

    Returns:
        异常处理器字典
    """

    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        """业务异常处理器"""
        logger.warning(f"业务异常: [{exc.code}] {exc.error_code} - {exc.message}")

        error_response = create_error_response(
            message=exc.message,
            error_code=exc.error_code,
            code=exc.code,
            details=exc.details,
        )

        return JSONResponse(status_code=exc.code, content=error_response.model_dump())

    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """请求验证异常处理器"""
        logger.warning(f"请求验证失败: {exc.errors()}")

        error_response = create_error_response(
            message="请求参数验证失败",
            error_code="VALIDATION_ERROR",
            code=422,
            details={"errors": exc.errors()},
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """HTTP异常处理器"""
        logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")

        # 检查 detail 是否已经是 ErrorResponse 格式的字典
        if hasattr(exc, "detail"):
            detail_value = exc.detail
            if isinstance(detail_value, dict) and all(key in detail_value for key in ["code", "message", "error_code"]):  # type: ignore[unreachable]
                # 类型安全：直接返回已格式化的错误响应
                return JSONResponse(status_code=exc.status_code, content=detail_value)  # type: ignore[unreachable]
        # 如果不是，按照原来的方式处理
        error_response = create_error_response(message=str(exc.detail), error_code="HTTP_ERROR", code=exc.status_code)

        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """通用异常处理器"""
        logger.error(f"未处理的异常: {exc!s}", exc_info=True)

        error_response = create_error_response(message="服务器内部错误", error_code="INTERNAL_ERROR", code=500)

        return JSONResponse(status_code=500, content=error_response.model_dump())

    return {
        BusinessError: business_error_handler,
        RequestValidationError: validation_error_handler,
        StarletteHTTPException: http_exception_handler,
        Exception: general_exception_handler,
    }


def create_fastapi_app(
    service_name: str,
    service_version: str = "1.0.0",
    description: str = "",
    database_url: Optional[str] = None,
    redis_url: Optional[str] = None,
    jwt_secret_key: Optional[str] = None,
    jaeger_endpoint: Optional[str] = None,
    log_level: str = "INFO",
    enable_docs: bool = True,
    cors_origins: Optional[List[str]] = None,
    trusted_hosts: Optional[List[str]] = None,
    startup_handlers: Optional[List[Callable]] = None,
    shutdown_handlers: Optional[List[Callable]] = None,
) -> FastAPI:
    """创建FastAPI应用

    Args:
        service_name: 服务名称
        service_version: 服务版本
        description: 服务描述
        database_url: 数据库连接URL
        redis_url: Redis连接URL
        jwt_secret_key: JWT密钥
        jaeger_endpoint: Jaeger端点
        log_level: 日志级别
        enable_docs: 是否启用API文档
        cors_origins: CORS允许的源
        trusted_hosts: 信任的主机列表
        startup_handlers: 启动处理器列表
        shutdown_handlers: 关闭处理器列表

    Returns:
        配置好的FastAPI应用实例
    """
    # 配置日志
    configure_logger(service_name=service_name, log_level=log_level)

    # 初始化监控指标
    init_metrics(
        service_name=service_name,
        service_version=service_version,
        environment="development",
    )

    # 创建FastAPI应用
    app = FastAPI(
        title=f"{service_name} API",
        description=description or f"{service_name} 微服务API",
        version=service_version,
        lifespan=create_lifespan_handler(
            service_name=service_name,
            database_url=database_url,
            redis_url=redis_url,
            jwt_secret_key=jwt_secret_key,
            jaeger_endpoint=jaeger_endpoint,
            startup_handlers=startup_handlers,
            shutdown_handlers=shutdown_handlers,
        ),
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        openapi_url="/openapi.json" if enable_docs else None,
    )

    # 添加中间件
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 添加请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        """记录HTTP请求"""
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算耗时
        duration = time.time() - start_time

        # 记录指标
        metrics_collector.record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration,
        )

        return response

    # 注册异常处理器
    exception_handlers = create_exception_handlers()
    for exc_class, handler in exception_handlers.items():
        app.add_exception_handler(exc_class, handler)

    # 健康检查端点
    @app.get("/health", tags=["健康检查"])
    async def health_check() -> Any:
        """健康检查"""
        health_status = {
            "service": service_name,
            "version": service_version,
            "status": "healthy",
        }

        # 检查数据库连接
        if mariadb_manager.is_connected:
            health_status["database"] = "connected"
        else:
            health_status["database"] = "disconnected"

        # 检查Redis连接
        if redis_manager.is_connected:
            health_status["cache"] = "connected"
        else:
            health_status["cache"] = "disconnected"

        return create_success_response(data=health_status)

    # 监控指标端点
    @app.get("/metrics", tags=["监控"])
    async def metrics() -> Response:
        """Prometheus监控指标"""
        return get_metrics_response()

    # 根路径端点
    @app.get("/", tags=["根路径"])
    async def root() -> Any:
        """根路径"""
        return create_success_response(
            data={
                "service": service_name,
                "version": service_version,
                "docs": "/docs" if enable_docs else "disabled",
                "health": "/health",
                "metrics": "/metrics",
            },
            message=f"{service_name} 服务运行正常",
        )

    return app
