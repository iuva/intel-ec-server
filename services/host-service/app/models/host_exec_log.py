"""主机执行日志数据模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, VARCHAR, BigInteger, DateTime, Index, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import BaseDBModel
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
    from shared.common.database import BaseDBModel


class HostExecLog(BaseDBModel):
    """主机执行日志模型 - 对应 host_exec_log 表

    继承 BaseDBModel 获得以下字段：
    - id: BIGINT (主键, 自增)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_exec_log"

    # 主机主键;host_rec 表主键
    host_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True, comment="主机主键;host_rec 表主键"
    )

    # 执行用户
    user_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True, index=True, comment="执行用户")

    # 执行测试 id
    tc_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True, comment="执行测试 id")

    # 周期名称
    cycle_name: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True, comment="周期名称")

    # 用户名称
    user_name: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="用户名称")

    # 异常信息
    err_msg: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="异常信息")

    # 开始时间
    begin_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")

    # 结束时间
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="结束时间")

    # 预期结束时间;agent 上报的预期结束时间
    due_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="预期结束时间;agent 上报的预期结束时间")

    # 主机状态;{free: 0, 空闲. lock: 1, 已锁定. occ: 2, 已占用. run: 3, case执行中.offline: 4, 离线.}
    host_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment="主机状态;0-空闲 1-已锁定 2-已占用 3-case执行中 4-离线",
    )

    # case 执行状态;{free: 0, 空闲. start: 1, 启动. success: 2, 成功. failed: 3, 失败.}
    case_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="case 执行状态;0-空闲 1-启动 2-成功 3-失败",
    )

    # 执行结果
    result_msg: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="执行结果")

    # 执行日志 log 地址
    log_url: Mapped[Optional[str]] = mapped_column(VARCHAR(512), nullable=True, comment="执行日志 log 地址")

    # 创建人
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建人")

    # 备注信息
    exec_rmk: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="备注信息")

    # 更新人
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="更新人")

    # 邮件通知状态;{not: 0, 未通知, yes: 1, 已通知.}
    notify_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="邮件通知状态;0-未通知 1-已通知",
    )

    # 📌 注意: del_flag 字段已由 BaseDBModel 提供，不需要重复定义
    # del_flag: TINYINT, default=0 (继承自 BaseDBModel)

    __table_args__ = (
        Index("ix_host_exec_log_case_state", "case_state"),
        Index(
            "ix_host_exec_log_host_case_begin_del",
            "host_state",
            "case_state",
            "begin_time",
            "del_flag",
        ),
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<HostExecLog(id={self.id}, host_id={self.host_id}, user_id={self.user_id}, case_state={self.case_state})>"
        )
