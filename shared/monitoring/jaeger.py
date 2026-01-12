"""
Jaeger Distributed Tracing Module

Provides distributed tracing functionality based on OpenTelemetry
"""

import logging
import os
from typing import Any, Optional

# Handle OpenTelemetry import using try-except
try:
    # ✅ Disable OpenTelemetry auto-detection and Thrift agent exporter
    # Prevent environment variables from triggering automatic creation of conflicting exporters
    os.environ.pop("JAEGER_AGENT_HOST", None)
    os.environ.pop("JAEGER_AGENT_PORT", None)
    os.environ.pop("JAEGER_SAMPLER_TYPE", None)
    os.environ.pop("JAEGER_SAMPLER_PARAM", None)
    # Also disable OTEL auto-detection (if it exists)
    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    os.environ.pop("OTEL_EXPORTER_JAEGER_AGENT_HOST", None)
    os.environ.pop("OTEL_EXPORTER_JAEGER_AGENT_PORT", None)

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:
    # If import fails, retry import
    # Clean environment variables
    os.environ.pop("JAEGER_AGENT_HOST", None)
    os.environ.pop("JAEGER_AGENT_PORT", None)
    os.environ.pop("JAEGER_SAMPLER_TYPE", None)
    os.environ.pop("JAEGER_SAMPLER_PARAM", None)
    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    os.environ.pop("OTEL_EXPORTER_JAEGER_AGENT_HOST", None)
    os.environ.pop("OTEL_EXPORTER_JAEGER_AGENT_PORT", None)

    # Re-import
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
    """Jaeger Tracing Manager

    Provides initialization and management functions for distributed tracing
    """

    def __init__(self) -> None:
        """Initialize Jaeger manager"""
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._is_initialized = False
        self._fastapi_instrumented = False  # ✅ Prevent duplicate instrumentation

    def init_tracer(
        self,
        service_name: str,
        jaeger_endpoint: str,
        environment: str = "development",
        service_version: str = "1.0.0",
    ) -> trace.Tracer:
        """Initialize Jaeger tracer

        Args:
            service_name: Service name
            jaeger_endpoint: Jaeger collector endpoint (gRPC endpoint, e.g. jaeger:4317)
            environment: Environment name
            service_version: Service version

        Returns:
            Tracer instance
        """
        try:
            # Create resource
            resource = Resource.create(
                {
                    SERVICE_NAME: service_name,
                    "service.version": service_version,
                    "deployment.environment": environment,
                }
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)

            # Create OTLP gRPC exporter
            # ✅ Use gRPC format instead of protobuf over HTTP
            # gRPC natively supports binary serialization, better compatibility
            otlp_exporter = OTLPSpanExporter(
                endpoint=jaeger_endpoint,
                insecure=True,  # Use insecure=True in development environment (don't verify certificates)
            )

            # Create batch span processor
            span_processor = BatchSpanProcessor(
                otlp_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,  # 5-second batch export
            )
            self.tracer_provider.add_span_processor(span_processor)

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            self._is_initialized = True
            logger.info(f"Jaeger tracer initialized successfully: {service_name}, Endpoint: {jaeger_endpoint}")

            return self.tracer

        except Exception as e:
            logger.error(f"Jaeger tracer initialization failed: {e!s}")
            raise

    def instrument_fastapi(self, app: Any) -> None:
        """Add tracing to FastAPI application

        Args:
            app: FastAPI application instance
        """
        if not self._is_initialized:
            logger.warning("Jaeger tracer not initialized, skipping FastAPI tracing")
            return

        # ✅ Prevent duplicate instrumentation
        if self._fastapi_instrumented:
            logger.debug("FastAPI already instrumented, skipping duplicate call")
            return

        try:
            FastAPIInstrumentor.instrument_app(app)
            self._fastapi_instrumented = True
            logger.info("FastAPI tracing enabled")
        except Exception as e:
            logger.error(f"Failed to enable FastAPI tracing: {e!s}")

    def instrument_app(self, app: Any) -> None:
        """Add all tracing middleware to application (alias method)

        Args:
            app: FastAPI application instance
        """
        self.instrument_fastapi(app)

    def instrument_sqlalchemy(self, engine: Any) -> None:
        """Add tracing to SQLAlchemy engine

        Args:
            engine: SQLAlchemy engine instance
        """
        if not self._is_initialized:
            logger.warning("Jaeger tracer not initialized, skipping SQLAlchemy tracing")
            return

        try:
            SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)
            logger.info("SQLAlchemy tracing enabled")
        except Exception as e:
            logger.error(f"Failed to enable SQLAlchemy tracing: {e!s}")

    def instrument_redis(self) -> None:
        """Add tracing to Redis"""
        if not self._is_initialized:
            logger.warning("Jaeger tracer not initialized, skipping Redis tracing")
            return

        try:
            RedisInstrumentor().instrument()
            logger.info("Redis tracing enabled")
        except Exception as e:
            logger.error(f"Failed to enable Redis tracing: {e!s}")

    def get_tracer(self) -> trace.Tracer:
        """Get tracer

        Returns:
            Tracer instance

        Raises:
            RuntimeError: If tracer is not initialized
        """
        if not self._is_initialized or not self.tracer:
            raise RuntimeError("Jaeger tracer not initialized, please call init_tracer() first")
        return self.tracer

    def is_initialized(self) -> bool:
        """Check if tracer is initialized

        Returns:
            bool: Returns True if initialized, otherwise False
        """
        return self._is_initialized

    def shutdown(self) -> None:
        """Shutdown tracer"""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Jaeger tracer closed")


# Global Jaeger manager instance
jaeger_manager = JaegerManager()


def init_jaeger(
    service_name: str,
    jaeger_endpoint: str,
    environment: str = "development",
    service_version: str = "1.0.0",
) -> trace.Tracer:
    """Initialize Jaeger tracing

    Args:
        service_name: Service name
        jaeger_endpoint: Jaeger collector endpoint
        environment: Environment name
        service_version: Service version

    Returns:
        Tracer instance
    """
    tracer = jaeger_manager.init_tracer(
        service_name=service_name,
        jaeger_endpoint=jaeger_endpoint,
        environment=environment,
        service_version=service_version,
    )

    logger.info(
        "Jaeger tracer initialized successfully, call auto_instrument_app() after application "
        + "startup to add FastAPI tracing"
    )
    return tracer


def get_tracer() -> trace.Tracer:
    """Get global tracer

    If tracer is not initialized, it will attempt to re-initialize

    Returns:
        Tracer instance
    """
    if not jaeger_manager.is_initialized():
        logger.warning("Tracer not initialized, attempting to re-initialize")
        # Cannot directly call init_jaeger here, as it requires service name and other parameters
        # Should ensure tracer is properly initialized during application startup
        raise RuntimeError("Jaeger tracer not initialized, ensure to call init_jaeger() during application startup")

    return jaeger_manager.get_tracer()


def instrument_app(app: Any) -> None:
    """Add tracing to application

    Args:
        app: FastAPI application instance
    """
    jaeger_manager.instrument_fastapi(app)


def auto_instrument_app(app: Any) -> None:
    """Automatically add all tracing middleware to application (convenience method)

    Args:
        app: FastAPI application instance
    """
    if jaeger_manager.is_initialized():
        jaeger_manager.instrument_fastapi(app)
        logger.info("Jaeger auto-tracing enabled")
    else:
        logger.warning("Jaeger tracer not initialized, please call init_jaeger() first")


def instrument_database(engine: Any) -> None:
    """Add tracing to database

    Args:
        engine: SQLAlchemy engine instance
    """
    jaeger_manager.instrument_sqlalchemy(engine)


def instrument_cache() -> None:
    """Add tracing to cache"""
    jaeger_manager.instrument_redis()


# Alias function, maintain backward compatibility
init_jaeger_tracer = init_jaeger
