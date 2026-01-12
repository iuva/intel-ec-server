"""Cache invalidation utility module

Provides unified cache clearing utility functions to ensure cache is invalidated in time when data is updated.
"""

import os
import sys
from typing import Optional

# Use try-except to handle path imports
try:
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


async def invalidate_ota_config_cache() -> bool:
    """Clear OTA configuration cache

    Returns:
        Whether clearing was successful
    """
    cache_key = "ota_configs:latest"
    try:
        await redis_manager.delete(cache_key)
        logger.info(
            "OTA configuration cache cleared",
            extra={"cache_key": cache_key},
        )
        return True
    except Exception as e:
        logger.warning(
            "Failed to clear OTA configuration cache",
            extra={"cache_key": cache_key, "error": str(e)},
        )
        return False


async def invalidate_hardware_template_cache() -> bool:
    """Clear hardware template cache

    Returns:
        Whether clearing was successful
    """
    cache_key = "hardware_template"
    try:
        await redis_manager.delete(cache_key)
        logger.info(
            "Hardware template cache cleared",
            extra={"cache_key": cache_key},
        )
        return True
    except Exception as e:
        logger.warning(
            "Failed to clear hardware template cache",
            extra={"cache_key": cache_key, "error": str(e)},
        )
        return False


async def invalidate_available_hosts_cache(pattern: Optional[str] = None) -> int:
    """Clear available host list cache

    Args:
        pattern: Cache key matching pattern, if None then clear all available_hosts cache
                 Example: "available_hosts:first_page:*"

    Returns:
        Number of caches cleared
    """
    if pattern is None:
        pattern = "available_hosts:first_page:*"

    try:
        deleted_count = await redis_manager.delete_pattern(pattern)
        if deleted_count > 0:
            logger.info(
                "Available host list cache cleared",
                extra={"pattern": pattern, "deleted_count": deleted_count},
            )
        return deleted_count
    except Exception as e:
        logger.warning(
            "Failed to clear available host list cache",
            extra={"pattern": pattern, "error": str(e)},
        )
        return 0


async def invalidate_sys_conf_cache(conf_key: str) -> bool:
    """Clear corresponding system configuration cache based on conf_key

    Args:
        conf_key: Configuration key, supported values:
            - "ota": Clear OTA configuration cache
            - "hw_temp": Clear hardware template cache

    Returns:
        Whether clearing was successful
    """
    if conf_key == "ota":
        return await invalidate_ota_config_cache()
    elif conf_key == "hw_temp":
        return await invalidate_hardware_template_cache()
    else:
        logger.warning(
            "Unknown conf_key, cannot clear cache",
            extra={"conf_key": conf_key},
        )
        return False
