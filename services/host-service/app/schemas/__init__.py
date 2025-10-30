"""Pydantic 模式模块"""

from app.schemas.hardware import (
    AgentHardwareReportRequest,
    AgentHardwareReportResponse,
    DMRConfigSchema,
)
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
    # 硬件配置相关
    "AgentHardwareReportRequest",
    "AgentHardwareReportResponse",
    "DMRConfigSchema",
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
