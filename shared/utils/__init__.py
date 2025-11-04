"""
共享工具模块

提供项目中常用的工具类和辅助函数
"""

from shared.utils.json_comparator import JSONComparator
from shared.utils.pagination import (
    CursorPaginationParams,
    CursorPaginationResponse,
    PaginationParams,
    PaginationResponse,
)
from shared.utils.service_discovery import ServiceDiscovery, get_service_discovery, init_service_discovery
from shared.utils.template_validator import TemplateValidator
from shared.utils.token_extractor import TokenExtractor, get_token_extractor

__all__ = [
    # JSON 对比工具
    "JSONComparator",
    # 分页工具
    "PaginationParams",
    "PaginationResponse",
    "CursorPaginationParams",
    "CursorPaginationResponse",
    # 服务发现工具
    "ServiceDiscovery",
    "get_service_discovery",
    "init_service_discovery",
    # 模板验证工具
    "TemplateValidator",
    # Token 提取工具
    "TokenExtractor",
    "get_token_extractor",
]
