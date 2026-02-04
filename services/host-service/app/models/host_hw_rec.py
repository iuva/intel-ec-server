"""Host hardware record data model"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, VARCHAR, BigInteger, DateTime, Index, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

# Use try-except to handle path imports
try:
    from shared.common.database import BaseDBModel
except ImportError:
    # If import fails, add project root directory to Python path
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
    from shared.common.database import BaseDBModel


class HostHwRec(BaseDBModel):
    """Host hardware record model - corresponds to host_hw_rec table

    Records host hardware change information

    Inherits from BaseDBModel to get the following fields:
    - id: BIGINT (primary key, auto-increment)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_hw_rec"

    # MongoDB primary key; mongo db hardware id
    hardware_id: Mapped[Optional[str]] = mapped_column(
        VARCHAR(64), nullable=True, comment="MongoDB primary key; mongo db hardware id"
    )

    # Host primary key; host_rec table primary key
    host_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True, comment="Host primary key; host_rec table primary key"
    )

    # Hardware information; mongo db data format (stores complete hardware configuration JSON)
    hw_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, comment="Hardware information; mongo db data format"
    )

    # Hardware version
    hw_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Hardware version")

    # Parameter state; {ver_diff: 1, version changed. item_diff: 2, content changed. failed: 3, exception.}
    diff_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment="Parameter state; {ver_diff: 1, version changed. item_diff: 2, content changed. failed: 3, exception.}",
    )

    # Sync state; {empty: 0, empty state. wait: 1, pending sync. success: 2, passed. failed: 3, exception.}
    sync_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="Sync state; {empty: 0, empty state. wait: 1, pending sync. success: 2, passed. failed: 3, exception.}",
    )

    # Approval time
    appr_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="Approval time")

    # Approver
    appr_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Approver")

    # Creator
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Creator")

    # Updater
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Updater")

    def __repr__(self) -> str:
        """String representation"""
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
