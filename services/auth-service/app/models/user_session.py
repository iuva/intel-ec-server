"""
User Session Data Model

Define the structure and fields of the user session table
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

# Use try-except approach to handle path imports
try:
    from shared.common.database import Base
except ImportError:
    # If import fails, add project root directory to Python path
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import Base


class UserSession(Base):
    """User Session Model"""

    __tablename__ = "user_sessions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="Primary key ID")

    # Association fields - now supports multiple entity types
    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Entity ID (admin user ID or device ID)",
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Entity type (admin_user or device)",
    )

    # Session fields
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment="Session ID")
    access_token: Mapped[str] = mapped_column(Text, nullable=False, comment="Access token")
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False, comment="Refresh token")

    # Client information
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, comment="Client IP")
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="User agent")

    # Expiration time
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="Expiration time")

    # Time fields
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
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Is deleted")

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"<UserSession(id={self.id}, entity_id={self.entity_id}, "
            f"entity_type={self.entity_type}, session_id={self.session_id})>"
        )
