"""
MariaDB 数据库管理器 - 异步 SQLAlchemy 集成
"""

import logging
import random
import time
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import BigInteger, DateTime, SmallInteger, func
from sqlalchemy.ext.asyncio import AsyncEngine  # type: ignore[attr-defined]
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase  # type: ignore[attr-defined]
from sqlalchemy.orm import Mapped, mapped_column

from shared.common.cache import redis_manager

logger = logging.getLogger(__name__)


def generate_snowflake_id() -> int:
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
    return (timestamp << 20) | random_part


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""


class BaseDBModel(Base):
    """数据库模型基类

    提供所有数据库模型的标准字段：
    - id: 主键ID（雪花ID）
    - created_time: 创建时间
    - updated_time: 更新时间
    - del_flag: 软删除标记
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, default=generate_snowflake_id, comment="主键ID（雪花ID）"
    )
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, comment="创建时间"
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
    del_flag: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, index=True, comment="是否已删除")


class MariaDBManager:
    """MariaDB异步连接池管理器

    提供MariaDB 10.11数据库的异步连接管理功能：
    - 连接池管理
    - 会话管理
    - 连接健康检查
    - SQL性能监控
    """

    def __init__(self) -> None:
        """初始化MariaDB管理器"""
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_connected: bool = False
        self._sql_monitor = None  # SQL性能监控器
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
        """连接到MariaDB数据库

        Args:
            database_url: 数据库连接URL，格式：mysql+aiomysql://user:***REMOVED***@host:port/db
            pool_size: 连接池大小
            max_overflow: 连接池最大溢出数
            pool_pre_ping: 是否在使用连接前进行健康检查
            echo: 是否打印SQL语句
            enable_sql_monitoring: 是否启用SQL性能监控
            slow_query_threshold: 慢查询阈值（秒），默认2秒
            service_name: 服务名称，用于监控指标标签
            pool_timeout: 连接池获取连接的超时时间（秒），默认30秒
            connect_timeout: 连接超时时间（秒），默认10秒
            read_timeout: 读取超时时间（秒），默认30秒（注意：aiomysql不支持此参数，保留仅为向后兼容）
            write_timeout: 写入超时时间（秒），默认30秒（注意：aiomysql不支持此参数，保留仅为向后兼容）
        """
        try:
            # 在数据库连接 URL 中添加超时参数
            # 注意：aiomysql 只支持 connect_timeout 参数，不支持 read_timeout 和 write_timeout
            # 如果 URL 中已经包含查询参数，则追加；否则添加
            if "?" in database_url:
                # URL 中已有查询参数，追加超时参数
                timeout_params = f"&connect_timeout={connect_timeout}"
                database_url_with_timeout = database_url + timeout_params
            else:
                # URL 中没有查询参数，添加超时参数
                timeout_params = f"?connect_timeout={connect_timeout}"
                database_url_with_timeout = database_url + timeout_params

            # 保存连接池配置用于监控
            self._pool_size = pool_size
            self._max_overflow = max_overflow

            # 创建异步引擎
            self.engine = create_async_engine(
                database_url_with_timeout,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=pool_pre_ping,
                echo=echo,
                pool_recycle=3600,  # 1小时回收连接
                pool_timeout=pool_timeout,  # 连接池获取连接的超时时间
            )

            # 创建会话工厂（包装以监控连接获取时间）
            base_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            # 包装会话工厂以记录连接获取时间
            self.session_factory = self._create_monitored_session_factory(base_session_factory)

            # 测试连接
            async with self.engine.begin() as conn:
                await conn.execute(func.now())

            # 初始化SQL性能监控器
            if enable_sql_monitoring:
                try:
                    from shared.monitoring.sql_performance import SQLPerformanceMonitor

                    self._sql_monitor = SQLPerformanceMonitor(
                        slow_query_threshold=slow_query_threshold,
                        enabled=True,
                        service_name=service_name,
                    )
                    self._sql_monitor.attach_to_engine(self.engine)
                    logger.info(
                        f"SQL性能监控已启用: threshold={slow_query_threshold}s, service={service_name}"
                    )
                except Exception as e:
                    logger.warning(f"SQL性能监控初始化失败: {e!s}，继续运行...", exc_info=True)

            self._is_connected = True
            # 安全地记录连接信息（隐藏密码）
            url_parts = database_url.split("@")
            safe_url = url_parts[-1] if len(url_parts) > 1 else "unknown"
            logger.info(
                "MariaDB连接成功",
                extra={"host": safe_url.split("/")[0] if "/" in safe_url else safe_url},
            )

        except Exception as e:
            # 提取连接信息用于错误提示（隐藏敏感信息）
            try:
                url_parts = database_url.split("@")
                if len(url_parts) > 1:
                    host_part = url_parts[-1].split("/")[0]
                    user_part = url_parts[0].split("://")[-1].split(":")[0] if "://" in url_parts[0] else "unknown"
                    logger.error(
                        "MariaDB连接失败",
                        extra={
                            "host": host_part,
                            "user": user_part,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )
                else:
                    logger.error(f"MariaDB连接失败: {e!s}", exc_info=True)
            except Exception:
                # 如果解析失败，使用简单日志
                logger.error(f"MariaDB连接失败: {e!s}", exc_info=True)
            raise

    async def disconnect(self) -> None:
        """断开数据库连接"""
        # 移除SQL性能监控器
        if self._sql_monitor and self.engine:
            try:
                self._sql_monitor.detach_from_engine(self.engine)
            except Exception as e:
                logger.warning(f"移除SQL性能监控器失败: {e!s}", exc_info=True)

        if self.engine:
            await self.engine.dispose()
            self._is_connected = False
            logger.info("MariaDB连接已关闭")

    def get_session(self) -> async_sessionmaker[AsyncSession]:
        """获取数据库会话工厂

        Returns:
            异步会话工厂

        Raises:
            RuntimeError: 如果数据库未连接
        """
        if not self._is_connected or not self.session_factory:
            raise RuntimeError("数据库未连接，请先调用connect()方法")
        return self.session_factory

    def get_pool_status(self) -> dict:
        """获取连接池状态信息

        Returns:
            连接池状态字典，包含：
            - pool_size: 基础连接池大小
            - max_overflow: 最大溢出连接数
            - max_connections: 最大连接数
            - checked_in: 当前空闲连接数
            - checked_out: 当前使用中的连接数
            - overflow: 当前溢出连接数
            - invalid: 无效连接数
            - usage_percent: 连接池使用率（%）
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
            # AsyncAdaptedQueuePool 可能没有 invalid() 方法
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
        """记录连接池状态到日志

        Args:
            level: 日志级别（info, warning, error）
        """
        status = self.get_pool_status()

        # 根据使用率决定日志级别
        if status["usage_percent"] >= 95:
            log_level = "error"
            message = "数据库连接池使用率过高（严重）"
        elif status["usage_percent"] >= 80:
            log_level = "warning"
            message = "数据库连接池使用率较高（警告）"
        else:
            log_level = level
            message = "数据库连接池状态"

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
        """创建所有数据库表"""
        if not self.engine:
            raise RuntimeError("数据库未连接")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建成功")

    async def drop_tables(self) -> None:
        """删除所有数据库表（谨慎使用）"""
        if not self.engine:
            raise RuntimeError("数据库未连接")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("数据库表已删除")

    def _create_monitored_session_factory(
        self, base_factory: async_sessionmaker[AsyncSession]
    ) -> async_sessionmaker[AsyncSession]:
        """创建带监控的会话工厂，记录连接获取时间
        
        使用 SQLAlchemy 事件监听器监控连接获取，更可靠且不侵入代码逻辑。
        """
        from sqlalchemy import event
        from sqlalchemy.pool import Pool

        # 监听连接池的 checkout 事件（连接被取出时）
        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """连接被取出时记录等待时间"""
            start_time = getattr(connection_record, "_checkout_start_time", None)
            if start_time:
                wait_time = time.time() - start_time
                # 避免在事件监听器中调用可能触发连接池操作的方法
                # 直接访问连接池属性获取状态
                try:
                    pool = self.engine.pool
                    checked_out = pool.checkedout() if hasattr(pool, "checkedout") else 0
                    max_connections = self._pool_size + self._max_overflow
                    usage_percent = (checked_out / max_connections * 100) if max_connections > 0 else 0.0
                except Exception:
                    # 如果获取状态失败，使用默认值
                    checked_out = 0
                    max_connections = self._pool_size + self._max_overflow
                    usage_percent = 0.0

                # 如果等待时间超过1秒，记录警告
                if wait_time > 1.0:
                    logger.warning(
                        "数据库连接获取耗时较长",
                        extra={
                            "wait_time_seconds": round(wait_time, 3),
                            "pool_usage_percent": round(usage_percent, 2),
                            "checked_out": checked_out,
                            "max_connections": max_connections,
                        },
                    )
                elif wait_time > 0.5:
                    logger.debug(
                        "数据库连接获取",
                        extra={
                            "wait_time_seconds": round(wait_time, 3),
                            "pool_usage_percent": round(usage_percent, 2),
                        },
                    )
            else:
                # 如果没有开始时间，记录开始时间（首次 checkout）
                connection_record._checkout_start_time = time.time()

        return base_factory

    @property
    def is_connected(self) -> bool:
        """检查数据库是否已连接"""
        return self._is_connected


# 全局MariaDB管理器实例
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
    """初始化数据库连接

    Args:
        mariadb_url: MariaDB数据库连接URL
        redis_url: Redis连接URL（可选）
        pool_size: 连接池大小（优化：默认200，支持700并发）
        max_overflow: 连接池最大溢出数（优化：默认500，最大连接数=700）
        enable_sql_monitoring: 是否启用SQL性能监控
        slow_query_threshold: 慢查询阈值（秒），默认2秒
        service_name: 服务名称，用于监控指标标签
        pool_timeout: 连接池获取连接的超时时间（秒），默认30秒
        connect_timeout: 连接超时时间（秒），默认10秒
        read_timeout: 读取超时时间（秒），默认30秒（注意：aiomysql不支持此参数，保留仅为向后兼容）
        write_timeout: 写入超时时间（秒），默认30秒（注意：aiomysql不支持此参数，保留仅为向后兼容）
    """
    try:
        # 连接MariaDB
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
        logger.info("数据库初始化成功")

        # ✅ 连接Redis（如果提供了URL）
        if redis_url:
            await redis_manager.connect(
                redis_url=redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            logger.info("Redis连接已初始化")
        else:
            logger.warning("未提供Redis URL，缓存功能不可用")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e!s}")
        raise


async def close_databases() -> None:
    """关闭所有数据库连接"""
    try:
        await mariadb_manager.disconnect()
        logger.info("MariaDB连接已关闭")

        # ✅ 关闭Redis连接
        await redis_manager.disconnect()
        logger.info("Redis连接已关闭")

    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e!s}")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入函数

    用于FastAPI的Depends依赖注入

    Yields:
        AsyncSession: 数据库会话
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
        # ✅ 确保会话总是被关闭（即使 commit/rollback 抛出异常）
        # 注意：async with 语句通常会自动关闭，但这里显式处理以确保健壮性
        if session and not session.closed:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"关闭数据库会话时出现异常: {e!s}", exc_info=True)
