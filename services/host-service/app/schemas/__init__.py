"""Pydantic schemas module"""

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
<<<<<<< HEAD
    # Host related
=======
    # 硬件配置相关
    "AgentHardwareReportRequest",
    "AgentHardwareReportResponse",
    "DMRConfigSchema",
    # 主机相关
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
    "GetVNCConnectionRequest",
    "HostBase",
    "HostCreate",
    "HostListResponse",
    "HostResponse",
    "HostStatusUpdate",
    "HostUpdate",
    "VNCConnectionInfo",
]
