"""主机相关的 Pydantic 模式"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HostBase(BaseModel):
    """主机基础模式"""

    host_id: str = Field(description="主机唯一标识")
    hostname: str = Field(description="主机名称")
    ip_address: str = Field(description="IP地址")
    os_type: Optional[str] = Field(default=None, description="操作系统类型")
    os_version: Optional[str] = Field(default=None, description="操作系统版本")


class HostCreate(HostBase):
    """创建主机请求模式"""


class HostUpdate(BaseModel):
    """更新主机请求模式"""

    hostname: Optional[str] = Field(default=None, description="主机名称")
    ip_address: Optional[str] = Field(default=None, description="IP地址")
    os_type: Optional[str] = Field(default=None, description="操作系统类型")
    os_version: Optional[str] = Field(default=None, description="操作系统版本")
    status: Optional[str] = Field(default=None, description="主机状态")


class HostStatusUpdate(BaseModel):
    """更新主机状态请求模式"""

    status: str = Field(description="主机状态 (online, offline, error)")


class HostResponse(HostBase):
    """主机响应模式"""

    id: int = Field(description="主键ID")
    status: str = Field(description="主机状态")
    last_heartbeat: Optional[datetime] = Field(default=None, description="最后心跳时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    is_deleted: bool = Field(description="是否已删除")

    model_config = {"from_attributes": True}


class HostListResponse(BaseModel):
    """主机列表响应模式"""

    hosts: List[HostResponse] = Field(description="主机列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
