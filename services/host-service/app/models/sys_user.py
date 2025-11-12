"""管理后台用户数据模型

定义管理后台用户表结构和字段
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


class SysUser(Base):
    """管理后台用户模型"""

    __tablename__ = "sys_user"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="主键")

    # 基础字段
    user_name: Mapped[str] = mapped_column(String(32), comment="用户名称")
    user_account: Mapped[str] = mapped_column(String(32), comment="登录账号")
    user_pwd: Mapped[str] = mapped_column(String(128), comment="登录密码")
    user_avatar: Mapped[Optional[str]] = mapped_column(String(32), comment="用户头像")
    email: Mapped[Optional[str]] = mapped_column(String(32), comment="邮箱")

    # 状态字段
    state_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, comment="账号状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}"
    )

    # 时间字段
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="创建人")
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, comment="创建时间"
    )
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="更新人")
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
    del_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, comment="删除标识;{useing: 0, 使用中. del: 1, 删除.}"
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<SysUser(id={self.id}, user_account={self.user_account}, user_name={self.user_name})>"
