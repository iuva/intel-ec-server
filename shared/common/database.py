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
    """

    def __init__(self) -> None:
        """初始化MariaDB管理器"""
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_connected: bool = False

    async def connect(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_pre_ping: bool = True,
        echo: bool = False,
    ) -> None:
        """连接到MariaDB数据库

        Args:
            database_url: 数据库连接URL，格式：mysql+aiomysql://user:***REMOVED***@host:port/db
            pool_size: 连接池大小
            max_overflow: 连接池最大溢出数
            pool_pre_ping: 是否在使用连接前进行健康检查
            echo: 是否打印SQL语句
        """
        try:
            # 创建异步引擎
            self.engine = create_async_engine(
                database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=pool_pre_ping,
                echo=echo,
                pool_recycle=3600,  # 1小时回收连接
            )

            # 创建会话工厂
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # 测试连接
            async with self.engine.begin() as conn:
                await conn.execute(func.now())

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

    @property
    def is_connected(self) -> bool:
        """检查数据库是否已连接"""
        return self._is_connected


# 全局MariaDB管理器实例
mariadb_manager = MariaDBManager()


async def init_databases(
    mariadb_url: str,
    redis_url: Optional[str] = None,
    pool_size: int = 10,
    max_overflow: int = 20,
) -> None:
    """初始化数据库连接

    Args:
        mariadb_url: MariaDB数据库连接URL
        redis_url: Redis连接URL（可选）
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出数
    """
    try:
        # 连接MariaDB
        await mariadb_manager.connect(
            database_url=mariadb_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
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
