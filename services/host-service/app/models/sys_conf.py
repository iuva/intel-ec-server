"""系统配置数据模型"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, VARCHAR, BigInteger, DateTime, SmallInteger, func
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


class SysConf(BaseDBModel):
    """系统配置模型 - 对应 sys_conf 表

    继承 BaseDBModel 获得以下字段：
    - id: BIGINT (主键, 自增)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "sys_conf"

    # 配置 key
    conf_key: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="配置 key")

    # 配置值
    conf_val: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="配置值")

    # 配置版本号
    conf_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="配置版本号")

    # 配置名称
    conf_name: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="配置名称")

    # 配置 json (存储硬件模板等复杂配置)
    conf_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="配置 json")

    # 状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}
    state_flag: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}",
    )

    # 创建人
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建人")

    # 更新人
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="更新人")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<SysConf(id={self.id}, conf_key={self.conf_key}, state_flag={self.state_flag})>"
