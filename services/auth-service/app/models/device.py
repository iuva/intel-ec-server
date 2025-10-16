"""
OAuth 2.0设备数据模型

将host_rec表改造为OAuth 2.0设备表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, SmallInteger, String, func
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


class Device(Base):
    """OAuth 2.0设备模型（基于host_rec表改造）"""

    __tablename__ = "devices"

    # 主键（复用host_rec的主键）
    id: Mapped[int] = mapped_column(primary_key=True, comment="主键（复用host_rec.id）")

    # 设备标识（对应mg_id）
    device_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True, comment="设备唯一标识（原mg_id）"
    )

    # 设备密钥（对应host_acct或生成的新密钥）
    device_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="设备密钥哈希")

    # 设备基本信息
    device_type: Mapped[str] = mapped_column(String(100), nullable=False, default="iot", comment="设备类型")
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="设备名称")

    # 网络信息（保留原有字段）
    host_ip: Mapped[str] = mapped_column(String(32), nullable=False, comment="主机IP地址")
    host_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="主机端口")

    # 设备状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否激活")
    permissions: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, default=["device"], comment="设备权限")
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后在线时间"
    )

    # 扩展信息
    device_metadata: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, default={}, comment="设备元数据")

    # 时间字段（复用原有字段）
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

    # 删除标识（复用原有字段）
    del_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, comment="删除标识;{useing: 0, 使用中. del: 1, 删除.}"
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Device(id={self.id}, device_id={self.device_id}, host_ip={self.host_ip})>"
