"""
用户会话数据模型

定义用户会话表结构和字段
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import Base
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import Base


class UserSession(Base):
    """用户会话模型"""

    __tablename__ = "user_sessions"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键ID")

    # 关联字段 - 现在支持多种实体类型
    entity_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="实体ID（管理后台用户ID或设备ID）"
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="实体类型（admin_user或device）"
    )

    # 会话字段
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment="会话ID")
    access_token: Mapped[str] = mapped_column(Text, nullable=False, comment="访问令牌")
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False, comment="刷新令牌")

    # 客户端信息
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, comment="客户端IP")
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="用户代理")

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="过期时间")

    # 时间字段
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
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已删除")

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<UserSession(id={self.id}, entity_id={self.entity_id}, "
            f"entity_type={self.entity_type}, session_id={self.session_id})>"
        )
