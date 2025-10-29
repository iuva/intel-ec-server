"""主机记录数据模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import INT, VARCHAR, BigInteger, DateTime, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import BaseDBModel
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import BaseDBModel


class HostRec(BaseDBModel):
    """主机记录模型 - 对应 host_rec 表

    继承 BaseDBModel 获得以下字段：
    - id: BIGINT (主键, 自增)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_rec"

    # 主机主键;对应 mongo 数据库 host 主键
    host_no: Mapped[Optional[str]] = mapped_column(
        VARCHAR(64), nullable=True, index=True, comment="主机主键;对应 mongo 数据库 host 主键"
    )

    # 唯一引导 id
    mg_id: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True, comment="唯一引导id")

    # 硬件记录表主键;host_hw_rec 表主键
    hw_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="硬件记录表主键;host_hw_rec 表主键")

    # mongodb 主键;mongo db 硬件 id
    hardware_id: Mapped[Optional[str]] = mapped_column(
        VARCHAR(64), nullable=True, comment="mongodb 主键;mongo db 硬件 id"
    )

    # ip 地址
    host_ip: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="ip 地址")

    # ip 端口
    host_port: Mapped[Optional[int]] = mapped_column(INT, nullable=True, comment="ip 端口")

    # 主机账号
    host_acct: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="主机账号")

    # 主机密码
    host_pwd: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True, comment="主机密码")

    # mac 地址
    mac_addr: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="mac 地址")

    # 审批状态;{disable: 0, 停用. enable: 1, 启用. new: 1, 新增. change: 2, 存在改动.}
    appr_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment=("审批状态;{disable: 0, 停用. enable: 1, 启用. new: 1, 新增. change: 2, 存在改动.}"),
    )

    # TCP在线状态;{close: 0, 关闭. wait: 1, 等待. lsn: 2, 监听.}
    tcp_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment="tcp在线状态;{close: 0, 关闭. wait: 1, 等待. lsn: 2, 监听.}",
    )

    # 主机状态 - 对应多个状态码
    # {free: 0, 空闲. lock: 1, 已锁定. occ: 2, 已占用. run: 3, case执行中.
    #  offline: 4, 离线. inact: 5, 待激活. hw_chg: 6, 存在潜在的硬件改动.
    #  disable: 7, 手动停用. updating: 8, 更新中.}
    host_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment=("主机状态;0-空闲 1-已锁定 2-已占用 3-case执行中 4-离线 5-待激活 6-硬件改动 7-手动停用 8-更新中"),
    )

    # 申报时间
    subm_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="申报时间")

    # agent 版本号
    agent_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(10), nullable=True, comment="agent 版本号")

    # 创建人
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建人")

    # 📌 更新人 - 对应表中 updated_by 字段
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="更新人")

    # 📌 注意: del_flag 字段已由 BaseDBModel 提供，不需要重复定义
    # del_flag: SmallInteger, default=0 (继承自 BaseDBModel)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<HostRec(id={self.id}, host_ip={self.host_ip}, host_state={self.host_state})>"
