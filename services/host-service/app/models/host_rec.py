"""Host record data model"""

from datetime import datetime
from typing import Optional

from sqlalchemy import INT, VARCHAR, BigInteger, DateTime, Index, SmallInteger
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


class HostRec(BaseDBModel):
    """Host record model - corresponds to host_rec table

    Inherits from BaseDBModel to get the following fields:
    - id: BIGINT (primary key, auto-increment)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_rec"

    # Host primary key; corresponds to mongo database host primary key
    host_no: Mapped[Optional[str]] = mapped_column(
        VARCHAR(64),
        nullable=True,
        index=True,
        comment="Host primary key; corresponds to mongo database host primary key",
    )

    # Unique machine GUID
    mg_id: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True, comment="Unique machine GUID")

    # Hardware record table primary key; host_hw_rec table primary key
    hw_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="Hardware record table primary key; host_hw_rec table primary key"
    )

    # MongoDB primary key; mongo db hardware id
    hardware_id: Mapped[Optional[str]] = mapped_column(
        VARCHAR(64), nullable=True, index=True, comment="MongoDB primary key; mongo db hardware id"
    )

    # IP address
    host_ip: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="IP address")

    # IP port
    host_port: Mapped[Optional[int]] = mapped_column(INT, nullable=True, comment="IP port")

    # Host account
    host_acct: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Host account")

    # Host ***REMOVED***word
    host_pwd: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True, comment="Host ***REMOVED***word")

    # MAC address
    mac_addr: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="MAC address")

    # Approval state; {disable: 0, disabled. enable: 1, enabled. new: 1, new. change: 2, has changes.}
    appr_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment=("Approval state; {disable: 0, disabled. enable: 1, enabled. new: 1, new. change: 2, has changes.}"),
    )

    # TCP online state; {close: 0, closed. wait: 1, waiting. lsn: 2, listening.}
    tcp_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment="TCP online state; {close: 0, closed. wait: 1, waiting. lsn: 2, listening.}",
    )

    # Host state - corresponds to multiple state codes
    # {free: 0, free. lock: 1, locked. occ: 2, occupied. run: 3, case executing.
    #  offline: 4, offline. inact: 5, pending activation. hw_chg: 6,
    #  has potential hardware changes. disable: 7, manually disabled. updating: 8, updating.}
    host_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        index=True,
        comment=(
            "Host state; 0-free 1-locked 2-occupied 3-case executing 4-offline "
            "5-pending activation 6-hardware changed 7-manually disabled 8-updating"
        ),
    )

    # Submission time
    subm_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="Submission time")

    # Agent version
    agent_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(10), nullable=True, comment="Agent version")

    # Creator
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Creator")

    # 📌 Updater - corresponds to updated_by field in table
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Updater")

    # 📌 Note: del_flag field is provided by BaseDBModel, no need to redefine
    # del_flag: SmallInteger, default=0 (inherited from BaseDBModel)

    def __repr__(self) -> str:
        """String representation"""
        return f"<HostRec(id={self.id}, host_ip={self.host_ip}, host_state={self.host_state})>"

    __table_args__ = (
        Index("ix_host_rec_host_state_appr_del", "host_state", "appr_state", "del_flag"),
        Index("ix_host_rec_created_time", "created_time"),
        Index("ix_host_rec_hardware_id_state", "hardware_id", "host_state", "appr_state", "tcp_state", "del_flag"),
    )
