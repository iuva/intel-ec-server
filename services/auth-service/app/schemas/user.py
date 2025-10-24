"""
用户相关的 Pydantic 数据模式

定义用户信息的请求和响应模式
"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础信息"""

    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")


class UserResponse(UserBase):
    """用户响应"""

    id: int = Field(description="用户ID")
    is_active: bool = Field(description="是否激活")
    is_superuser: bool = Field(description="是否超级用户")
    created_time: datetime = Field(description="创建时间")
    updated_time: datetime = Field(description="更新时间")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_active": True,
                "is_superuser": True,
                "created_time": "2025-01-29T10:00:00Z",
                "updated_time": "2025-01-29T10:00:00Z",
            }
        },
    }
