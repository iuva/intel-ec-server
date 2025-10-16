"""
数据库连接管理模块

提供MariaDB 10.11异步连接池管理和基础数据库模型类
"""

from datetime import datetime
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import Boolean, DateTime, Integer, func
from sqlalchemy.ext.asyncio import (  # type: ignore[attr-defined]
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""


class BaseDBModel(Base):
    """数据库模型基类

    提供所有数据库模型的标准字段：
    - id: 主键ID
    - created_at: 创建时间
    - updated_at: 更新时间
    - is_deleted: 软删除标记
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已删除")


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
            logger.info(f"MariaDB连接成功: {database_url.split('@')[-1]}")

        except Exception as e:
            logger.error(f"MariaDB连接失败: {e!s}")
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
        redis_url: Redis连接URL（可选，暂未实现）
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
    except Exception as e:
        logger.error(f"数据库初始化失败: {e!s}")
        raise


async def close_databases() -> None:
    """关闭所有数据库连接"""
    try:
        await mariadb_manager.disconnect()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e!s}")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入函数

    用于FastAPI的Depends依赖注入

    Yields:
        AsyncSession: 数据库会话
    """
    session_factory = mariadb_manager.get_session()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
