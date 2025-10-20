"""
用户相关的 Pydantic 数据模式（对应 sys_user 表）
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础模式"""

    username: str = Field(description="用户账号（登录账号）")
    email: Optional[str] = Field(default=None, description="邮箱地址")


class UserCreate(UserBase):
    """用户创建请求模式"""

    ***REMOVED***word: str = Field(description="密码", min_length=8)
    is_active: bool = Field(default=True, description="是否激活")


class UserUpdate(BaseModel):
    """用户更新请求模式"""

    email: Optional[str] = Field(default=None, description="邮箱地址")
    ***REMOVED***word: Optional[str] = Field(default=None, description="密码", min_length=8)
    is_active: Optional[bool] = Field(default=None, description="是否激活")


class UserResponse(BaseModel):
    """用户响应模式"""

    id: int = Field(description="用户ID")
    user_account: Optional[str] = Field(description="登录账号")
    user_name: Optional[str] = Field(description="用户名称")
    email: Optional[str] = Field(description="邮箱地址")
    user_avatar: Optional[str] = Field(description="用户头像")
    state_flag: int = Field(description="账号状态（0=启用, 1=停用）")
    created_time: datetime = Field(description="创建时间")
    updated_time: datetime = Field(description="更新时间")

    # 添加计算属性以保持向后兼容
    @property
    def username(self) -> Optional[str]:
        """向后兼容：返回 user_account"""
        return self.user_account

    @property
    def is_active(self) -> bool:
        """向后兼容：state_flag 0=启用"""
        return self.state_flag == 0

    @property
    def created_at(self) -> datetime:
        """向后兼容：返回 created_time"""
        return self.created_time

    @property
    def updated_at(self) -> datetime:
        """向后兼容：返回 updated_time"""
        return self.updated_time

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """用户列表响应模式"""

    users: List[UserResponse] = Field(description="用户列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")

    model_config = {"from_attributes": True}
