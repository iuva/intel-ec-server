"""主机升级记录数据模型"""

from typing import Optional

from sqlalchemy import VARCHAR, BigInteger, SmallInteger
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


class HostUpd(BaseDBModel):
    """主机升级记录模型 - 对应 host_upd 表

    继承 BaseDBModel 获得以下字段：
    - id: BIGINT (主键, 自增)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_upd"

    # 主机主键;host_rec 表主键
    host_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="主机主键;host_rec 表主键")

    # 应用 key
    app_key: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="应用 key")

    # 应用名称
    app_name: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="应用名称")

    # 应用版本号
    app_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="应用版本号")

    # 更新状态;{pre-upd: 0, 预更新. updating: 1, 更新中. success: 2, 成功. failed: 3, 失败.}
    app_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        comment="更新状态;{pre-upd: 0, 预更新. updating: 1, 更新中. success: 2, 成功. failed: 3, 失败.}",
    )

    # 创建人
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建人")

    # 更新人
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="更新人")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<HostUpd(id={self.id}, host_id={self.host_id}, app_name={self.app_name}, app_state={self.app_state})>"
