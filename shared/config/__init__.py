"""
共享配置模块

提供Nacos服务发现等配置功能
"""

from shared.config.nacos_config import NacosManager, get_nacos_manager, init_nacos_manager, nacos_manager

__all__ = [
    "NacosManager",
    "get_nacos_manager",
    "init_nacos_manager",
    "nacos_manager",
]
