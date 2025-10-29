"""
用户数据模型

定义用户表结构和字段（对应 sys_user 表）
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
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


class User(Base):
    """用户模型（对应 sys_user 表）"""

    __tablename__ = "sys_user"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, comment="主键")

    # 基础字段
    user_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="用户名称")
    user_account: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="登录账号")
    user_pwd: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="登录密码")
    user_avatar: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="用户头像")
    email: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="邮箱")

    # 状态字段
    state_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, comment="账号状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}"
    )

    # 审计字段
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建人")
    created_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.current_timestamp(), nullable=False, comment="创建时间"
    )
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="更新人")
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
        comment="更新时间",
    )

    # 删除标识
    del_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, comment="删除标识;{useing: 0, 使用中. del: 1, 删除.}"
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<User(id={self.id}, user_account={self.user_account}, user_name={self.user_name})>"
