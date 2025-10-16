"""
OAuth 2.0 Device Data Model

Transform host_rec table into OAuth 2.0 device table
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

# Use try-except approach to handle path imports
try:
    from shared.common.database import Base
except ImportError:
    # If import fails, add project root directory to Python path
    import os
    import sys

    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    )
    from shared.common.database import Base


class Device(Base):
    """OAuth 2.0 Device Model (based on transformation of host_rec table)"""

    __tablename__ = "devices"

    # Primary key (reuse host_rec's primary key)
    id: Mapped[int] = mapped_column(
        primary_key=True, comment="Primary key (reuse host_rec.id)"
    )

    # Device identifier (corresponds to mg_id)
    device_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique device identifier (original mg_id)",
    )

    # Device secret (corresponds to host_acct or generated new secret)
    device_secret_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Device secret hash"
    )

    # Basic device information
    device_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="iot", comment="Device type"
    )
    device_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Device name"
    )

    # Network information (preserve existing fields)
    host_ip: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="Host IP address"
    )
    host_port: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Host port"
    )

    # Device status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Is active"
    )
    permissions: Mapped[Optional[str]] = mapped_column(
        JSON, nullable=True, default=["device"], comment="Device permissions"
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last online time"
    )

    # Extended information
    device_metadata: Mapped[Optional[str]] = mapped_column(
        JSON, nullable=True, default={}, comment="Device metadata"
    )

    # Time fields (reuse existing fields)
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        comment="Creation time",
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Update time",
    )

    # Deletion flag (reuse existing field)
    del_flag: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        comment="Deletion flag;{useing: 0, in use. del: 1, deleted.}",
    )

    def __repr__(self) -> str:
        """String representation"""
        return f"<Device(id={self.id}, device_id={self.device_id}, host_ip={self.host_ip})>"
