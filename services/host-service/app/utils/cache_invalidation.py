"""缓存失效工具模块

提供统一的缓存清除工具函数，确保数据更新时缓存能够及时失效。
"""

import os
import sys
from typing import Optional

# 使用 try-except 方式处理路径导入
try:
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


async def invalidate_ota_config_cache() -> bool:
    """清除 OTA 配置缓存

    Returns:
        是否清除成功
    """
    cache_key = "ota_configs:latest"
    try:
        await redis_manager.delete(cache_key)
        logger.info(
            "OTA 配置缓存已清除",
            extra={"cache_key": cache_key},
        )
        return True
    except Exception as e:
        logger.warning(
            "清除 OTA 配置缓存失败",
            extra={"cache_key": cache_key, "error": str(e)},
        )
        return False


async def invalidate_hardware_template_cache() -> bool:
    """清除硬件模板缓存

    Returns:
        是否清除成功
    """
    cache_key = "hardware_template"
    try:
        await redis_manager.delete(cache_key)
        logger.info(
            "硬件模板缓存已清除",
            extra={"cache_key": cache_key},
        )
        return True
    except Exception as e:
        logger.warning(
            "清除硬件模板缓存失败",
            extra={"cache_key": cache_key, "error": str(e)},
        )
        return False


async def invalidate_available_hosts_cache(pattern: Optional[str] = None) -> int:
    """清除可用主机列表缓存

    Args:
        pattern: 缓存键匹配模式，如果为 None 则清除所有 available_hosts 缓存
                例如: "available_hosts:first_page:*"

    Returns:
        清除的缓存数量
    """
    if pattern is None:
        pattern = "available_hosts:first_page:*"

    try:
        deleted_count = await redis_manager.delete_pattern(pattern)
        if deleted_count > 0:
            logger.info(
                "可用主机列表缓存已清除",
                extra={"pattern": pattern, "deleted_count": deleted_count},
            )
        return deleted_count
    except Exception as e:
        logger.warning(
            "清除可用主机列表缓存失败",
            extra={"pattern": pattern, "error": str(e)},
        )
        return 0


async def invalidate_sys_conf_cache(conf_key: str) -> bool:
    """根据 conf_key 清除对应的系统配置缓存

    Args:
        conf_key: 配置键，支持的值：
            - "ota": 清除 OTA 配置缓存
            - "hw_temp": 清除硬件模板缓存

    Returns:
        是否清除成功
    """
    if conf_key == "ota":
        return await invalidate_ota_config_cache()
    elif conf_key == "hw_temp":
        return await invalidate_hardware_template_cache()
    else:
        logger.warning(
            "未知的 conf_key，无法清除缓存",
            extra={"conf_key": conf_key},
        )
        return False
