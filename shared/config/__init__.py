"""
Shared Configuration Module

Provides Nacos service discovery and other configuration functions
"""

from shared.config.nacos_config import NacosManager, get_nacos_manager, init_nacos_manager, nacos_manager

__all__ = [
    "NacosManager",
    "get_nacos_manager",
    "init_nacos_manager",
    "nacos_manager",
]
