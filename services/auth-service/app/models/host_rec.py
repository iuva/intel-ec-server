"""
Host Record Data Model

Define the structure and fields of the host record table
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

# Use try-except approach to handle path imports
try:
    from shared.common.database import Base, generate_snowflake_id
except ImportError:
    # If import fails, add project root directory to Python path
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import Base, generate_snowflake_id


class HostRec(Base):
    """Host Record Model"""

    __tablename__ = "host_rec"

    # Primary key - Use Snowflake ID generator
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, default=generate_snowflake_id, comment="Primary key (Snowflake ID)"
    )

    # Basic fields
    host_no: Mapped[Optional[str]] = mapped_column(
        String(64), comment="Host primary key; corresponds to host primary key in mongo database"
    )
    mg_id: Mapped[str] = mapped_column(String(128), comment="Unique boot ID")
    host_ip: Mapped[str] = mapped_column(String(32), comment="IP address")
    host_port: Mapped[Optional[int]] = mapped_column(Integer, comment="IP port")
    host_acct: Mapped[str] = mapped_column(String(32), comment="Host account")
    host_pwd: Mapped[Optional[str]] = mapped_column(String(64), comment="Host ***REMOVED***word")
    mac_addr: Mapped[Optional[str]] = mapped_column(String(255), comment="MAC address")

    # Status fields
    appr_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        comment=(
            "Approval status;{disable: 0, disabled. "
            "enable: 1, enabled. new: 1, new addition. change: 2, changes exist.}"
        ),
    )
    host_state: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        comment=(
            "Host status;{free: 0, free. lock: 1, locked. occ: 2, occupied. run: 3, case running. "
            "offline: 4, offline. inact: 5, pending activation. hw_chg: 6, potential hardware changes exist. "
            "disable: 7, manually disabled. updating: 8, updating.}"
        ),
    )

    # Time fields
    subm_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), comment="Submission time")
    hw_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="Hardware record table primary key; host_hw_rec table primary key"
    )
    agent_ver: Mapped[Optional[str]] = mapped_column(String(10), comment="Agent version number")

    # Audit fields - support automatic setting
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="Created by (currently logged-in user ID)")
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, comment="Creation time"
    )
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="Updated by (currently logged-in user ID)")
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Update time",
    )
    del_flag: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False, comment="Deletion flag;{useing: 0, in use. del: 1, deleted.}"
    )

    def __repr__(self) -> str:
        """String representation"""
        return f"<HostRec(id={self.id}, mg_id={self.mg_id}, host_ip={self.host_ip})>"
