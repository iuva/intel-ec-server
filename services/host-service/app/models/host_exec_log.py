"""Host execution log data model"""

from datetime import datetime
from typing import Optional

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


class HostExecLog(BaseDBModel):
    """Host execution log model - corresponds to host_exec_log table

    Inherits from BaseDBModel to get the following fields:
    - id: BIGINT (primary key, auto-increment)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_exec_log"

    # Host primary key; host_rec table primary key
    host_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True, comment="Host primary key; host_rec table primary key"
    )

    # Execution user
    user_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True, index=True, comment="Execution user")

    # Test case ID
    tc_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True, comment="Test case ID")

    # Cycle name
    cycle_name: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True, comment="Cycle name")

    # User name
    user_name: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="User name")

    # Error message
    err_msg: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="Error message")

    # Start time
    begin_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="Start time")

    # End time
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="End time")

    # Expected end time; expected end time reported by agent
    due_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="Expected end time; expected end time reported by agent"
    )

    # Host state; {free: 0, free. lock: 1, locked. occ: 2, occupied. run: 3, case executing. offline: 4, offline.}
    host_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment="Host state; 0-free 1-locked 2-occupied 3-case executing 4-offline",
    )

    # Case execution state; {free: 0, free. start: 1, started. success: 2, success. failed: 3, failed.}
    case_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="Case execution state; 0-free 1-started 2-success 3-failed",
    )

    # Execution result
    result_msg: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="Execution result")

    # Execution log URL
    log_url: Mapped[Optional[str]] = mapped_column(VARCHAR(512), nullable=True, comment="Execution log URL")

    # Creator
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Creator")

    # Remarks
    exec_rmk: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="Remarks")

    # Updater
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Updater")

    # Email notification state; {not: 0, not notified. yes: 1, notified.}
    notify_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="Email notification state; 0-not notified 1-notified",
    )

    # 📌 Note: del_flag field is provided by BaseDBModel, no need to redefine
    # del_flag: TINYINT, default=0 (inherited from BaseDBModel)

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
        """String representation"""
        return (
            f"<HostExecLog(id={self.id}, host_id={self.host_id}, user_id={self.user_id}, case_state={self.case_state})>"
        )
