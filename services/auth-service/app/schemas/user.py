"""
User-related Pydantic Data Schemas

Define request and response schemas for user information
"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """User Basic Information"""

    username: str = Field(description="Username")
    email: str = Field(description="Email")


class UserResponse(UserBase):
    """User Response"""

    id: str = Field(description="User ID")
    is_active: bool = Field(description="Whether activated")
    is_superuser: bool = Field(description="Whether superuser")
    created_time: datetime = Field(description="Creation time")
    updated_time: datetime = Field(description="Update time")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "1",
                "username": "admin",
                "email": "admin@example.com",
                "is_active": True,
                "is_superuser": True,
                "created_time": "2025-01-29T10:00:00Z",
                "updated_time": "2025-01-29T10:00:00Z",
            }
        },
    }
