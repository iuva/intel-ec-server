"""
Host Service API 依赖注入

提供服务实例的依赖注入函数
"""

import os
from typing import Optional

from app.services.host_service import HostService

# 全局服务实例缓存（使用 Optional 类型注解）
_host_service_instance: Optional[HostService] = None


def get_host_service() -> HostService:
    """获取主机服务实例（单例模式）

    从环境变量中读取硬件接口 URL 配置，注入到 HostService 中。

    Returns:
        HostService: 主机服务实例
    """
    global _host_service_instance

    if _host_service_instance is None:
        # 从环境变量读取硬件接口 URL
        hardware_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")

        _host_service_instance = HostService(hardware_api_url=hardware_api_url)

    return _host_service_instance
