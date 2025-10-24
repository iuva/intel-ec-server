"""
Host Service API 依赖注入

提供服务实例的依赖注入函数
"""

import os
from typing import Optional

from app.services.host_discovery_service import HostDiscoveryService
from app.services.host_service import HostService
from app.services.vnc_service import VNCService

# 全局服务实例缓存（使用 Optional 类型注解）
_host_service_instance: Optional[HostService] = None
_vnc_service_instance: Optional[VNCService] = None
_host_discovery_service_instance: Optional[HostDiscoveryService] = None


def get_host_service() -> HostService:
    """获取主机服务实例（单例模式）

    Returns:
        HostService: 主机服务实例
    """
    global _host_service_instance

    if _host_service_instance is None:
        _host_service_instance = HostService()

    return _host_service_instance


def get_vnc_service() -> VNCService:
    """获取 VNC 服务实例（单例模式）

    Returns:
        VNCService: VNC 服务实例
    """
    global _vnc_service_instance

    if _vnc_service_instance is None:
        _vnc_service_instance = VNCService()

    return _vnc_service_instance


def get_host_discovery_service() -> HostDiscoveryService:
    """获取主机发现服务实例（单例模式）

    从环境变量中读取硬件接口 URL 配置，注入到 HostDiscoveryService 中。

    Returns:
        HostDiscoveryService: 主机发现服务实例
    """
    global _host_discovery_service_instance

    if _host_discovery_service_instance is None:
        # 从环境变量读取硬件接口 URL
        hardware_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
        _host_discovery_service_instance = HostDiscoveryService(hardware_api_url)

    return _host_discovery_service_instance
