"""Pydantic 模式模块"""

from app.schemas.host import (
    GetVNCConnectionRequest,
    HostBase,
    HostCreate,
    HostListResponse,
    HostResponse,
    HostStatusUpdate,
    HostUpdate,
    VNCConnectionInfo,
)

__all__ = [
    # 主机相关
    "GetVNCConnectionRequest",
    "HostBase",
    "HostCreate",
    "HostListResponse",
    "HostResponse",
    "HostStatusUpdate",
    "HostUpdate",
    "VNCConnectionInfo",
]
