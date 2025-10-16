"""
用户相关的 Pydantic 数据模式
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础模式"""

    username: str = Field(description="用户名")
    email: str = Field(description="邮箱地址")


class UserCreate(UserBase):
    """用户创建请求模式"""

    ***REMOVED***word: str = Field(description="密码", min_length=8)
    is_active: bool = Field(default=True, description="是否激活")
    is_superuser: bool = Field(default=False, description="是否超级用户")


class UserUpdate(BaseModel):
    """用户更新请求模式"""

    email: Optional[str] = Field(default=None, description="邮箱地址")
    ***REMOVED***word: Optional[str] = Field(default=None, description="密码", min_length=8)
    is_active: Optional[bool] = Field(default=None, description="是否激活")
    is_superuser: Optional[bool] = Field(default=None, description="是否超级用户")


class UserResponse(UserBase):
    """用户响应模式"""

    id: int = Field(description="用户ID")
    is_active: bool = Field(description="是否激活")
    is_superuser: bool = Field(description="是否超级用户")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """用户列表响应模式"""

    users: List[UserResponse] = Field(description="用户列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")

    model_config = {"from_attributes": True}
