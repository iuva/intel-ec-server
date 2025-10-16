"""创建数据库表脚本

运行方式：
  从项目根目录运行: python -m services.host_service.create_tables
  或设置 PYTHONPATH: export PYTHONPATH=/path/to/project && python create_tables.py
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 必须导入模型以注册到 Base.metadata
# 虽然 Host 看起来未使用，但导入它会将模型注册到 SQLAlchemy 的 metadata 中
try:
    from app.models.host import Host
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from app.models.host import Host

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import Base
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.database import Base
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# 使用 Host 模型确保它被注册（避免未使用警告）
_ = Host


async def create_tables():
    """创建所有数据库表"""
    # 从环境变量获取数据库 URL
    mariadb_url = os.getenv(
        "MARIADB_URL",
        "mysql+aiomysql://intel_user:intel_***REMOVED***@localhost:3306/intel_cw",
    )

    logger.info(f"连接数据库: {mariadb_url}")

    # 创建异步引擎
    engine = create_async_engine(mariadb_url, echo=True)

    try:
        # 创建所有表
        async with engine.begin() as conn:
            logger.info("开始创建表...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("表创建完成!")

        # 验证表是否创建成功
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables " + "WHERE table_schema = DATABASE()")
            )
            tables = [row[0] for row in result]
            logger.info(f"\n当前数据库中的表: {tables}")

            if "hosts" in tables:
                logger.info("✓ hosts 表创建成功")
            else:
                logger.error("✗ hosts 表创建失败")

    except Exception as e:
        logger.error(f"创建表时发生错误: {e!s}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Host Service 数据库表创建脚本")
    logger.info("=" * 50)
    asyncio.run(create_tables())
