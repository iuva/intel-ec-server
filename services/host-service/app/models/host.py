"""主机数据模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import BaseDBModel
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.database import BaseDBModel


class Host(BaseDBModel):
    """主机模型"""

    __tablename__ = "hosts"

    # 主机唯一标识
    host_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True, comment="主机唯一标识")

    # 主机名称
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, comment="主机名称")

    # IP 地址
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True, comment="IP地址")

    # 操作系统类型
    os_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="操作系统类型")

    # 操作系统版本
    os_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="操作系统版本")

    # 主机状态 (online, offline, error)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline", index=True, comment="主机状态")

    # 最后心跳时间
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后心跳时间"
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Host(host_id={self.host_id}, hostname={self.hostname}, status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "host_id": self.host_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "os_type": self.os_type,
            "os_version": self.os_version,
            "status": self.status,
            "last_heartbeat": (self.last_heartbeat.isoformat() if self.last_heartbeat else None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
        }
