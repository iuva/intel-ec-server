"""
用户数据模型

定义用户表结构和字段
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import Base
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.database import Base


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键ID")

    # 基础字段
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment="邮箱")
    ***REMOVED***word_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")

    # 状态字段
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否超级用户")

    # 时间字段
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

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
