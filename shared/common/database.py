"""
MariaDB Database Manager - Asynchronous SQLAlchemy Integration
"""

import logging
<<<<<<< HEAD
import os
import random
import ssl
import time
=======
import random
import time
from datetime import datetime
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
from typing import AsyncGenerator, Optional

from sqlalchemy import BigInteger, DateTime, SmallInteger, event, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,  # type: ignore[attr-defined]
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,  # type: ignore[attr-defined]
    Mapped,
    mapped_column,
)

from shared.common.cache import redis_manager
from shared.monitoring.sql_performance import SQLPerformanceMonitor

from shared.common.cache import redis_manager

logger = logging.getLogger(__name__)


def generate_snowflake_id() -> int:
<<<<<<< HEAD
    """Generate Snowflake ID (Simplified)

    Generates a unique ID using timestamp + random number, suitable for distributed systems.

    Returns:
        int: Snowflake ID (64-bit integer)

    Algorithm Description:
        - High 44 bits: Millisecond-level timestamp
        - Low 20 bits: Random number (0-999999)
        - Total 64 bits, meeting BigInteger requirements

    Example:
        >>> id1 = generate_snowflake_id()
        >>> id2 = generate_snowflake_id()
        >>> id1 != id2  # Ensure uniqueness
        True
    """
    timestamp = int(time.time() * 1000)  # Millisecond-level timestamp
    random_part = random.randint(0, 999999)  # Random part
=======
    """生成雪花ID（简化版）

    使用时间戳 + 随机数生成唯一ID，适用于分布式系统

    Returns:
        int: 雪花ID（64位整数）

    算法说明:
        - 高44位: 毫秒级时间戳
        - 低20位: 随机数（0-999999）
        - 总共64位，满足BigInteger要求

    示例:
        >>> id1 = generate_snowflake_id()
        >>> id2 = generate_snowflake_id()
        >>> id1 != id2  # 保证唯一性
        True
    """
    timestamp = int(time.time() * 1000)  # 毫秒级时间戳
    random_part = random.randint(0, 999999)  # 随机数部分
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
    return (timestamp << 20) | random_part


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base"""


class BaseDBModel(Base):
    """Database Model Base Class

<<<<<<< HEAD
    Provides standard fields for all database models:
    - id: Primary Key ID (Snowflake ID)
    - created_time: Creation time
    - updated_time: Update time
    - del_flag: Soft delete flag
=======
    提供所有数据库模型的标准字段：
    - id: 主键ID（雪花ID）
    - created_time: 创建时间
    - updated_time: 更新时间
    - del_flag: 软删除标记
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
<<<<<<< HEAD
        BigInteger, primary_key=True, default=generate_snowflake_id, comment="Primary Key ID (Snowflake ID)"
=======
        BigInteger, primary_key=True, default=generate_snowflake_id, comment="主键ID（雪花ID）"
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
    )
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, comment="Creation time"
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Update time",
    )
    del_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, index=True, comment="Whether deleted"
    )


class MariaDBManager:
    """MariaDB Asynchronous Connection Pool Manager

    Provides asynchronous connection management for MariaDB 10.11 database:
    - Connection pool management
    - Session management
    - Connection health check
    - SQL performance monitoring
    """

    def __init__(self) -> None:
        """Initialize MariaDB Manager"""
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_connected: bool = False
        self._sql_monitor = None  # SQL performance monitor
        self._pool_size: int = 0
        self._max_overflow: int = 0

    async def connect(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_pre_ping: bool = True,
        echo: bool = False,
        enable_sql_monitoring: bool = True,
        slow_query_threshold: float = 2.0,
        service_name: str = "unknown",
        pool_timeout: float = 30.0,
        connect_timeout: int = 10,
        read_timeout: int = 30,
        write_timeout: int = 30,
    ) -> None:
        """Connect to MariaDB database

        Args:
            database_url: Database connection URL, format: mysql+aiomysql://user:***REMOVED***@host:port/db
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections in the pool
            pool_pre_ping: Whether to check health before using connection
            echo: Whether to print SQL statements
            enable_sql_monitoring: Whether to enable SQL performance monitoring
            slow_query_threshold: Slow query threshold (seconds), default 2.0s
            service_name: Service name, used for monitoring metrics labels
            pool_timeout: Timeout for getting connection from pool (seconds), default 30s
            connect_timeout: Connection timeout (seconds), default 10s
            read_timeout: Read timeout (seconds), default 30s
                # (Note: aiomysql does not support this, kept for backward compatibility)
            write_timeout: Write timeout (seconds), default 30s
                # (Note: aiomysql does not support this, kept for backward compatibility)
        """
        try:
            # Add timeout parameters to database connection URL
            # Note: aiomysql only supports connect_timeout, not read_timeout and write_timeout
            # If URL already has query parameters, append; otherwise add
            if "?" in database_url:
                # URL has query parameters, append timeout parameter
                timeout_params = f"&connect_timeout={connect_timeout}"
                database_url_with_timeout = database_url + timeout_params
            else:
                # URL has no query parameters, add timeout parameter
                timeout_params = f"?connect_timeout={connect_timeout}"
                database_url_with_timeout = database_url + timeout_params

            # ✅ Read SSL config from environment variables and dynamically create SSL context
            connect_args = {}
            ssl_enabled = os.getenv("MARIADB_SSL_ENABLED", "false").lower() in ("true", "1", "yes")

            if ssl_enabled:
                # Read SSL configuration
                ssl_ca = os.getenv("MARIADB_SSL_CA", "")
                ssl_cert = os.getenv("MARIADB_SSL_CERT", "")
                ssl_key = os.getenv("MARIADB_SSL_KEY", "")
                ssl_verify_cert = os.getenv("MARIADB_SSL_VERIFY_CERT", "true").lower() in ("true", "1", "yes")
                ssl_verify_identity = os.getenv("MARIADB_SSL_VERIFY_IDENTITY", "false").lower() in ("true", "1", "yes")

                # Create SSL context
                ssl_context = ssl.create_default_context()

                if not ssl_verify_cert:
                    # Do not verify certificate: Dev/Test environment
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    logger.info(
                        "MariaDB SSL enabled (certificate verification disabled)",
                        extra={
                            "ssl_enabled": True,
                            "ssl_verify_cert": False,
                        },
                    )
                else:
                    # Verify certificate: Production environment
                    ssl_context.check_hostname = ssl_verify_identity
                    ssl_context.verify_mode = ssl.CERT_REQUIRED
                    logger.info(
                        "MariaDB SSL enabled (certificate verification enabled)",
                        extra={
                            "ssl_enabled": True,
                            "ssl_verify_cert": True,
                            "ssl_verify_identity": ssl_verify_identity,
                        },
                    )

                # Load certificate files
                if ssl_ca:
                    try:
                        ssl_context.load_verify_locations(ssl_ca)
                        logger.debug(f"SSL CA certificate loaded: {ssl_ca}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to load SSL CA certificate: {ssl_ca}",
                            extra={"error": str(e)},
                        )

                if ssl_cert and ssl_key:
                    try:
                        ssl_context.load_cert_chain(ssl_cert, ssl_key)
                        logger.debug(f"SSL client certificate loaded: {ssl_cert}, {ssl_key}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to load SSL client certificate: {ssl_cert}, {ssl_key}",
                            extra={"error": str(e)},
                        )

                # Add SSL context to connect_args
                connect_args["ssl"] = ssl_context
            else:
                logger.debug("MariaDB SSL not enabled")

            # Set session timezone
            db_timezone = os.getenv("MARIADB_TIMEZONE", "+08:00")
            if db_timezone:
                connect_args["init_command"] = f"SET time_zone = '{db_timezone}'"
                logger.info("Setting database session timezone", extra={"timezone": db_timezone})

            # Save connection pool config for monitoring
            self._pool_size = pool_size
            self._max_overflow = max_overflow

            # Create async engine
            self.engine = create_async_engine(
                database_url_with_timeout,
                connect_args=connect_args if connect_args else {},
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=pool_pre_ping,
                echo=echo,
                pool_recycle=3600,  # Recycle connections every 1 hour
                pool_timeout=pool_timeout,  # Timeout for getting connection from pool
            )

            # Create session factory (wrapped to monitor connection acquisition time)
            base_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            # Wrap session factory to record connection acquisition time
            self.session_factory = self._create_monitored_session_factory(base_session_factory)

            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(func.now())

            # Initialize SQL performance monitor
            if enable_sql_monitoring:
                try:
                    self._sql_monitor = SQLPerformanceMonitor(
                        slow_query_threshold=slow_query_threshold,
                        enabled=True,
                        service_name=service_name,
                    )
                    self._sql_monitor.attach_to_engine(self.engine)
                    logger.info(
                        f"SQL performance monitoring enabled: threshold={slow_query_threshold}s, service={service_name}"
                    )
                except Exception as e:
                    logger.warning(
                        f"SQL performance monitoring initialization failed: {e!s}, continuing...", exc_info=True
                    )

            self._is_connected = True
            # Safely log connection info (hide ***REMOVED***word)
            url_parts = database_url.split("@")
            safe_url = url_parts[-1] if len(url_parts) > 1 else "unknown"
            logger.info(
                "MariaDB connection successful",
                extra={"host": safe_url.split("/")[0] if "/" in safe_url else safe_url},
            )

        except Exception as e:
            # Extract connection info for error message (hide sensitive info)
            try:
                url_parts = database_url.split("@")
                if len(url_parts) > 1:
                    host_part = url_parts[-1].split("/")[0]
                    user_part = url_parts[0].split("://")[-1].split(":")[0] if "://" in url_parts[0] else "unknown"
                    logger.error(
                        "MariaDB connection failed",
                        extra={
                            "host": host_part,
                            "user": user_part,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )
                else:
                    logger.error(f"MariaDB connection failed: {e!s}", exc_info=True)
            except Exception:
                # If parsing fails, use simple logging
                logger.error(f"MariaDB connection failed: {e!s}", exc_info=True)
            raise

    async def disconnect(self) -> None:
        """Disconnect from database"""
        # Remove SQL performance monitor
        if self._sql_monitor and self.engine:
            try:
                self._sql_monitor.detach_from_engine(self.engine)
            except Exception as e:
                logger.warning(f"Failed to remove SQL performance monitor: {e!s}", exc_info=True)

        if self.engine:
            await self.engine.dispose()
            self._is_connected = False
            logger.info("MariaDB connection closed")

    def get_session(self) -> async_sessionmaker[AsyncSession]:
        """Get database session factory

        Returns:
            Async session factory

        Raises:
            RuntimeError: If database is not connected
        """
        if not self._is_connected or not self.session_factory:
            raise RuntimeError("Database not connected, please call connect() method first")
        return self.session_factory

    def get_pool_status(self) -> dict:
        """Get connection pool status

        Returns:
            Connection pool status dictionary, including:
            - pool_size: Base pool size
            - max_overflow: Max overflow connections
            - max_connections: Max connections
            - checked_in: Current idle connections
            - checked_out: Current active connections
            - overflow: Current overflow connections
            - invalid: Invalid connections
            - usage_percent: Pool usage percentage (%)
        """
        if not self.engine:
            return {
                "pool_size": 0,
                "max_overflow": 0,
                "max_connections": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "invalid": 0,
                "usage_percent": 0.0,
                "status": "not_connected",
            }

        pool = self.engine.pool
        try:
            checked_in = pool.checkedin()
        except AttributeError:
            checked_in = 0

        try:
            checked_out = pool.checkedout()
        except AttributeError:
            checked_out = 0

        try:
            overflow = pool.overflow()
        except AttributeError:
            overflow = 0

        try:
            invalid = pool.invalid()
        except AttributeError:
            # AsyncAdaptedQueuePool may not have invalid() method
            invalid = 0

        max_connections = self._pool_size + self._max_overflow
        total_connections = checked_in + checked_out
        usage_percent = (total_connections / max_connections * 100) if max_connections > 0 else 0.0

        return {
            "pool_size": self._pool_size,
            "max_overflow": self._max_overflow,
            "max_connections": max_connections,
            "checked_in": checked_in,
            "checked_out": checked_out,
            "overflow": overflow,
            "invalid": invalid,
            "total_connections": total_connections,
            "usage_percent": round(usage_percent, 2),
            "status": "connected",
        }

    def log_pool_status(self, level: str = "info") -> None:
        """Log connection pool status

        Args:
            level: Log level (info, warning, error)
        """
        status = self.get_pool_status()

        # Determine log level based on usage
        if status["usage_percent"] >= 95:
            log_level = "error"
            message = "Database connection pool usage too high (critical)"
        elif status["usage_percent"] >= 80:
            log_level = "warning"
            message = "Database connection pool usage relatively high (warning)"
        else:
            log_level = level
            message = "Database connection pool status"

        log_func = getattr(logger, log_level, logger.info)
        log_func(
            message,
            extra={
                "pool_size": status["pool_size"],
                "max_overflow": status["max_overflow"],
                "max_connections": status["max_connections"],
                "checked_in": status["checked_in"],
                "checked_out": status["checked_out"],
                "overflow": status["overflow"],
                "invalid": status["invalid"],
                "total_connections": status["total_connections"],
                "usage_percent": status["usage_percent"],
                "status": status["status"],
            },
        )

    async def create_tables(self) -> None:
        """Create all database tables"""
        if not self.engine:
            raise RuntimeError("Database not connected")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        """Drop all database tables (Use with caution)"""
        if not self.engine:
            raise RuntimeError("Database not connected")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("Database tables deleted")

    def _create_monitored_session_factory(
        self, base_factory: async_sessionmaker[AsyncSession]
    ) -> async_sessionmaker[AsyncSession]:
        """Create monitored session factory, tracking connection acquisition time

        # Use SQLAlchemy event listener to monitor connection checkout, which is more reliable and non-intrusive.
        """

        # Ensure engine exists
        if not self.engine:
            return base_factory

        # Keep engine reference to avoid type checking issues
        engine = self.engine

        # Listen for checkout event (when connection is retrieved)
        @event.listens_for(engine.sync_engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Record wait time when connection is retrieved"""
            start_time = getattr(connection_record, "_checkout_start_time", None)
            if start_time:
                wait_time = time.time() - start_time
                # Avoid calling methods that might trigger pool operations inside event listener
                # Access pool attributes directly for status
                try:
                    if engine and engine.pool:
                        pool = engine.pool
                        checked_out = pool.checkedout() if hasattr(pool, "checkedout") else 0
                        max_connections = self._pool_size + self._max_overflow
                        usage_percent = (checked_out / max_connections * 100) if max_connections > 0 else 0.0
                    else:
                        checked_out = 0
                        max_connections = self._pool_size + self._max_overflow
                        usage_percent = 0.0
                except Exception:
                    # If getting status fails, use default values
                    checked_out = 0
                    max_connections = self._pool_size + self._max_overflow
                    usage_percent = 0.0

                # If wait time > 1s, log warning
                if wait_time > 1.0:
                    logger.warning(
                        "Database connection acquisition took too long",
                        extra={
                            "wait_time_seconds": round(wait_time, 3),
                            "pool_usage_percent": round(usage_percent, 2),
                            "checked_out": checked_out,
                            "max_connections": max_connections,
                        },
                    )
                elif wait_time > 0.5:
                    logger.debug(
                        "Database connection acquired",
                        extra={
                            "wait_time_seconds": round(wait_time, 3),
                            "pool_usage_percent": round(usage_percent, 2),
                        },
                    )
            else:
                # If no start time, record it (first checkout)
                connection_record._checkout_start_time = time.time()

        return base_factory

    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._is_connected


# Global MariaDB manager instance
mariadb_manager = MariaDBManager()


async def init_databases(
    mariadb_url: str,
    redis_url: Optional[str] = None,
    pool_size: int = 200,
    max_overflow: int = 500,
    enable_sql_monitoring: bool = True,
    slow_query_threshold: float = 2.0,
    service_name: str = "unknown",
    pool_timeout: float = 30.0,
    connect_timeout: int = 10,
    read_timeout: int = 30,
    write_timeout: int = 30,
) -> None:
    """Initialize database connection

    Args:
        mariadb_url: MariaDB database connection URL
        redis_url: Redis connection URL (Optional)
        pool_size: Connection pool size (Optimized: default 200, supports 700 concurrency)
        max_overflow: Max overflow (Optimized: default 500, max connections=700)
        enable_sql_monitoring: Whether to enable SQL performance monitoring
        slow_query_threshold: Slow query threshold (seconds), default 2.0s
        service_name: Service name, used for monitoring metrics labels
        pool_timeout: Timeout for getting connection from pool (seconds), default 30s
        connect_timeout: Connection timeout (seconds), default 10s
        read_timeout: Read timeout (seconds), default 30s
                # (Note: aiomysql does not support this, kept for backward compatibility)
        write_timeout: Write timeout (seconds), default 30s
                # (Note: aiomysql does not support this, kept for backward compatibility)
    """
    try:
        # Connect to MariaDB
        await mariadb_manager.connect(
            database_url=mariadb_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            enable_sql_monitoring=enable_sql_monitoring,
            slow_query_threshold=slow_query_threshold,
            service_name=service_name,
            pool_timeout=pool_timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        )
        logger.info("Database initialization successful")

        # ✅ Connect to Redis (if URL provided)
        if redis_url:
            await redis_manager.connect(
                redis_url=redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            logger.info("Redis connection initialized")
        else:
            logger.warning("Redis URL not provided, caching functionality unavailable")

    except Exception as e:
        logger.error(f"Database initialization failed: {e!s}")
        raise


async def close_databases() -> None:
    """Close all database connections"""
    try:
        await mariadb_manager.disconnect()
        logger.info("MariaDB connection closed")

        # ✅ Close Redis connection
        await redis_manager.disconnect()
        logger.info("Redis connection closed")

    except Exception as e:
        logger.error(f"Failed to close database connection: {e!s}")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session

    Used for FastAPI Depends injection

    Yields:
        AsyncSession: Database session
    """
    session_factory = mariadb_manager.get_session()
    session = None
    try:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        # ✅ Ensure session is always closed (even if commit/rollback raises exception)
        # Note: async with usually closes automatically, but handled explicitly here for robustness
        if session and not session.closed:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Exception occurred while closing database session: {e!s}", exc_info=True)
