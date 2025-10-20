"""
Jaeger分布式追踪模块

基于OpenTelemetry提供分布式追踪功能
"""

import logging
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class JaegerManager:
    """Jaeger追踪管理器

    提供分布式追踪的初始化和管理功能
    """

    def __init__(self) -> None:
        """初始化Jaeger管理器"""
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._is_initialized = False

    def init_tracer(
        self,
        service_name: str,
        jaeger_endpoint: str,
        environment: str = "development",
        service_version: str = "1.0.0",
    ) -> trace.Tracer:
        """初始化Jaeger追踪器

        Args:
            service_name: 服务名称
            jaeger_endpoint: Jaeger收集器端点（gRPC 端点，如 jaeger:4317）
            environment: 环境名称
            service_version: 服务版本

        Returns:
            追踪器实例
        """
        try:
            # 创建资源
            resource = Resource.create(
                {
                    SERVICE_NAME: service_name,
                    "service.version": service_version,
                    "deployment.environment": environment,
                }
            )

            # 创建追踪器提供者
            self.tracer_provider = TracerProvider(resource=resource)

            # 创建OTLP gRPC导出器
            # ✅ 使用 gRPC 格式而不是 protobuf over HTTP
            # gRPC 原生支持二进制序列化，兼容性更好
            otlp_exporter = OTLPSpanExporter(
                endpoint=jaeger_endpoint,
                insecure=True,  # 开发环境使用 insecure=True（不验证证书）
            )

            # 创建批处理span处理器
            span_processor = BatchSpanProcessor(
                otlp_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,  # 5秒批量导出
            )
            self.tracer_provider.add_span_processor(span_processor)

            # 设置全局追踪器提供者
            trace.set_tracer_provider(self.tracer_provider)

            # 获取追踪器
            self.tracer = trace.get_tracer(__name__)

            self._is_initialized = True
            logger.info(f"Jaeger追踪器初始化成功: {service_name}, 端点: {jaeger_endpoint}")

            return self.tracer

        except Exception as e:
            logger.error(f"Jaeger追踪器初始化失败: {e!s}")
            raise

    def instrument_fastapi(self, app: Any) -> None:
        """为FastAPI应用添加追踪

        Args:
            app: FastAPI应用实例
        """
        if not self._is_initialized:
            logger.warning("Jaeger追踪器未初始化，跳过FastAPI追踪")
            return

        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI追踪已启用")
        except Exception as e:
            logger.error(f"FastAPI追踪启用失败: {e!s}")

    def instrument_app(self, app: Any) -> None:
        """为应用添加所有追踪中间件（别名方法）

        Args:
            app: FastAPI应用实例
        """
        self.instrument_fastapi(app)

    def instrument_sqlalchemy(self, engine: Any) -> None:
        """为SQLAlchemy引擎添加追踪

        Args:
            engine: SQLAlchemy引擎实例
        """
        if not self._is_initialized:
            logger.warning("Jaeger追踪器未初始化，跳过SQLAlchemy追踪")
            return

        try:
            SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)
            logger.info("SQLAlchemy追踪已启用")
        except Exception as e:
            logger.error(f"SQLAlchemy追踪启用失败: {e!s}")

    def instrument_redis(self) -> None:
        """为Redis添加追踪"""
        if not self._is_initialized:
            logger.warning("Jaeger追踪器未初始化，跳过Redis追踪")
            return

        try:
            RedisInstrumentor().instrument()
            logger.info("Redis追踪已启用")
        except Exception as e:
            logger.error(f"Redis追踪启用失败: {e!s}")

    def get_tracer(self) -> trace.Tracer:
        """获取追踪器

        Returns:
            追踪器实例

        Raises:
            RuntimeError: 如果追踪器未初始化
        """
        if not self._is_initialized or not self.tracer:
            raise RuntimeError("Jaeger追踪器未初始化，请先调用init_tracer()")
        return self.tracer

    def is_initialized(self) -> bool:
        """检查追踪器是否已初始化

        Returns:
            bool: 如果已初始化返回 True，否则返回 False
        """
        return self._is_initialized

    def shutdown(self) -> None:
        """关闭追踪器"""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Jaeger追踪器已关闭")


# 全局Jaeger管理器实例
jaeger_manager = JaegerManager()


def init_jaeger(
    service_name: str,
    jaeger_endpoint: str,
    environment: str = "development",
    service_version: str = "1.0.0",
) -> trace.Tracer:
    """初始化Jaeger追踪

    Args:
        service_name: 服务名称
        jaeger_endpoint: Jaeger收集器端点
        environment: 环境名称
        service_version: 服务版本

    Returns:
        追踪器实例
    """
    tracer = jaeger_manager.init_tracer(
        service_name=service_name,
        jaeger_endpoint=jaeger_endpoint,
        environment=environment,
        service_version=service_version,
    )

    logger.info("Jaeger追踪器初始化成功，请在应用启动后调用auto_instrument_app()添加FastAPI追踪")
    return tracer


def get_tracer() -> trace.Tracer:
    """获取全局追踪器

    如果追踪器未初始化，会尝试重新初始化

    Returns:
        追踪器实例
    """
    if not jaeger_manager.is_initialized():
        logger.warning("追踪器未初始化，尝试重新初始化")
        # 这里不能直接调用init_jaeger，因为需要服务名称等参数
        # 应该在应用启动时确保追踪器已正确初始化
        raise RuntimeError("Jaeger追踪器未初始化，请确保在应用启动时调用init_jaeger()")

    return jaeger_manager.get_tracer()


def instrument_app(app: Any) -> None:
    """为应用添加追踪

    Args:
        app: FastAPI应用实例
    """
    jaeger_manager.instrument_fastapi(app)


def auto_instrument_app(app: Any) -> None:
    """自动为应用添加所有追踪中间件（便捷方法）

    Args:
        app: FastAPI应用实例
    """
    if jaeger_manager.is_initialized():
        jaeger_manager.instrument_fastapi(app)
        logger.info("Jaeger自动追踪已启用")
    else:
        logger.warning("Jaeger追踪器未初始化，请先调用init_jaeger()")


def instrument_database(engine: Any) -> None:
    """为数据库添加追踪

    Args:
        engine: SQLAlchemy引擎实例
    """
    jaeger_manager.instrument_sqlalchemy(engine)


def instrument_cache() -> None:
    """为缓存添加追踪"""
    jaeger_manager.instrument_redis()


# 别名函数，保持向后兼容
init_jaeger_tracer = init_jaeger
