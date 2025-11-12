"""主机硬件记录数据模型"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, VARCHAR, BigInteger, DateTime, Index, SmallInteger
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


class HostHwRec(BaseDBModel):
    """主机硬件记录模型 - 对应 host_hw_rec 表

    记录主机硬件变动信息

    继承 BaseDBModel 获得以下字段：
    - id: BIGINT (主键, 自增)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_hw_rec"

    # mongodb 主键;mongo db 硬件 id
    hardware_id: Mapped[Optional[str]] = mapped_column(
        VARCHAR(64), nullable=True, comment="mongodb 主键;mongo db 硬件 id"
    )

    # 主机主键;host_rec 表主键
    host_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True, comment="主机主键;host_rec 表主键"
    )

    # 硬件信息;mongo db 数据格式 (存储完整的硬件配置JSON)
    hw_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="硬件信息;mongo db 数据格式")

    # 硬件版本号
    hw_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="硬件版本号")

    # 参数状态;{ver_diff: 1, 版本号变化. item_diff: 2, 内容更改. failed: 3, 异常.}
    diff_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment="参数状态;{ver_diff: 1, 版本号变化. item_diff: 2, 内容更改. failed: 3, 异常.}",
    )

    # 同步状态;{empty: 0 空状态. wait: 1, 待同步. success: 2, 通过. failed: 3, 异常.}
    sync_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="同步状态;{empty: 0 空状态. wait: 1, 待同步. success: 2, 通过. failed: 3, 异常.}",
    )

    # 审批时间
    appr_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="审批时间")

    # 审批人
    appr_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="审批人")

    # 创建人
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建人")

    # 更新人
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="更新人")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<HostHwRec(id={self.id}, host_id={self.host_id}, hw_ver={self.hw_ver}, diff_state={self.diff_state})>"

    __table_args__ = (
        Index("ix_host_hw_rec_sync_state", "sync_state", "del_flag"),
        Index("ix_host_hw_rec_diff_state", "diff_state", "del_flag"),
        Index(
            "ix_host_hw_rec_host_sync_diff_del",
            "host_id",
            "sync_state",
            "diff_state",
            "del_flag",
        ),
        Index("ix_host_hw_rec_created_time", "created_time", "id"),
    )
