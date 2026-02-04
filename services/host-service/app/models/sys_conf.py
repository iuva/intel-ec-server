"""System configuration data model"""

from typing import Any, Dict, Optional

from sqlalchemy import JSON, VARCHAR, BigInteger, SmallInteger
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


class SysConf(BaseDBModel):
    """System configuration model - corresponds to sys_conf table

    Inherits from BaseDBModel to get the following fields:
    - id: BIGINT (primary key, auto-increment)
    - created_time: DATETIME DEFAULT CURRENT_TIMESTAMP
    - updated_time: DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    - del_flag: TINYINT DEFAULT 0
    """

    __tablename__ = "sys_conf"

    # Configuration key
    conf_key: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Configuration key")

    # Configuration value
    conf_val: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True, comment="Configuration value")

    # Configuration version
    conf_ver: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Configuration version")

    # Configuration name
    conf_name: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True, comment="Configuration name")

    # Configuration JSON (stores complex configurations like hardware templates)
    conf_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="Configuration JSON")

    # State; {enable_flag: 0, enabled. disable_flag: 1, disabled.}
    state_flag: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        index=True,
        comment="State; {enable_flag: 0, enabled. disable_flag: 1, disabled.}",
    )

    # Creator
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Creator")

    # Updater
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="Updater")

    def __repr__(self) -> str:
        """String representation"""
        return f"<SysConf(id={self.id}, conf_key={self.conf_key}, state_flag={self.state_flag})>"
