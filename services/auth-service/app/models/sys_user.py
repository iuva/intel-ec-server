"""
Admin User Data Model

Define the structure and fields of the admin user table
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
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


class SysUser(Base):
    """Admin User Model"""

    __tablename__ = "sys_user"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="Primary key")

    # Basic fields
    user_name: Mapped[str] = mapped_column(String(32), comment="User name")
    user_account: Mapped[str] = mapped_column(String(32), comment="Login account")
    user_pwd: Mapped[str] = mapped_column(String(128), comment="Login ***REMOVED***word")
    user_avatar: Mapped[Optional[str]] = mapped_column(
        String(32), comment="User avatar"
    )
    email: Mapped[Optional[str]] = mapped_column(String(32), comment="Email")

    # Status field
    state_flag: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        comment="Account status;{enable_flag: 0, enabled. disable_flag: 1, disabled.}",
    )

    # Time fields
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="Created by")
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        comment="Creation time",
    )
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="Updated by")
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Update time",
    )
    del_flag: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        nullable=False,
        comment="Deletion flag;{useing: 0, in use. del: 1, deleted.}",
    )

    def __repr__(self) -> str:
        """String representation"""
        return f"<SysUser(id={self.id}, user_account={self.user_account}, user_name={self.user_name})>"
