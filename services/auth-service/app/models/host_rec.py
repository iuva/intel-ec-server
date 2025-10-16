"""
主机记录数据模型

定义主机记录表结构和字段
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, func
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


class HostRec(Base):
    """主机记录模型"""

    __tablename__ = "host_rec"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="主键")

    # 基础字段
    host_no: Mapped[Optional[str]] = mapped_column(String(64), comment="主机主键;对应 mongo 数据库 host 主键")
    mg_id: Mapped[str] = mapped_column(String(128), comment="唯一引导id")
    host_ip: Mapped[str] = mapped_column(String(32), comment="ip 地址")
    host_port: Mapped[Optional[int]] = mapped_column(Integer, comment="ip 端口")
    host_acct: Mapped[str] = mapped_column(String(32), comment="主机账号")
    host_pwd: Mapped[Optional[str]] = mapped_column(String(64), comment="主机密码")
    mac_addr: Mapped[Optional[str]] = mapped_column(String(255), comment="mac 地址")

    # 状态字段
    appr_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger, comment="审批状态;{disable: 0, 停用. enable: 1, 启用. new: 1, 新增. change: 2, 存在改动.}"
    )
    host_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        comment="主机状态;{free: 0, 空闲. lock: 1, 已锁定. occ: 2, 已占用. run: 3, case执行中.offline: 4, 离线. inact: 5, 待激活. hw_chg: 6, 存在潜在的硬件改动. disable: 7, 手动停用. updating: 8, 更新中.}",
    )

    # 时间字段
    subm_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), comment="申报时间")
    hw_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="硬件记录表主键;host_hw_rec 表主键")
    agent_ver: Mapped[Optional[str]] = mapped_column(String(10), comment="agent 版本号")

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
        return f"<HostRec(id={self.id}, mg_id={self.mg_id}, host_ip={self.host_ip})>"
