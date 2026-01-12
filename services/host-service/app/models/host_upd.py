"""Host upgrade record data model"""

from typing import Optional

from sqlalchemy import VARCHAR, BigInteger, SmallInteger
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


class HostUpd(BaseDBModel):
    """Host upgrade record model - corresponds to host_upd table

    Inherits from BaseDBModel to get the following fields:
    - id: BIGINT (primary key, auto-increment)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "host_upd"

    # Host primary key; host_rec table primary key
    host_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Host primary key; host_rec table primary key"
    )

    # Application key
    app_key: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Application key")

    # Application name
    app_name: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Application name")

    # Application version
    app_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Application version")

    # Update state; {pre-upd: 0, pre-update. updating: 1, updating. success: 2, success. failed: 3, failed.}
    app_state: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        comment=(
            "Update state; {pre-upd: 0, pre-update. updating: 1, updating. "
            "success: 2, success. failed: 3, failed.}"
        ),
    )

    # Creator
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Creator")

    # Updater
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Updater")

    def __repr__(self) -> str:
        """String representation"""
        return f"<HostUpd(id={self.id}, host_id={self.host_id}, app_name={self.app_name}, app_state={self.app_state})>"
