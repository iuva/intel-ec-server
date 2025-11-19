"""服务发现工具类

提供从 Nacos 动态获取服务地址的功能，支持：
- 服务实例缓存
- 自动刷新
- 负载均衡
- 故障转移
"""

import os
import sys
import time
from typing import Any, Dict, Optional

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager

logger = get_logger(__name__)


class ServiceDiscovery:
    """服务发现工具类

    从 Nacos 动态获取服务地址，支持缓存和自动刷新。

    使用示例:
        >>> discovery = ServiceDiscovery(nacos_manager)
        >>> auth_url = await discovery.get_service_url("auth-service")
        >>> print(auth_url)  # http://172.20.0.101:8001
    """

    def __init__(self, nacos_manager: Optional[NacosManager] = None, cache_ttl: int = 30):
        """初始化服务发现

        Args:
            nacos_manager: Nacos 管理器实例（可选）
            cache_ttl: 缓存过期时间（秒），默认 30 秒
        """
        self.nacos_manager = nacos_manager
        self.cache_ttl = cache_ttl

        # 服务地址缓存: {service_name: {"url": "http://...", "timestamp": 123456}}
        self._cache: Dict[str, Dict[str, Any]] = {}

        # 后备静态服务地址（环境变量优先）
        # ✅ 修复：本地开发环境使用 127.0.0.1，Docker 环境使用服务名
        # 检查是否在 Docker 环境中（通过检查环境变量或文件系统）
        is_docker = os.getenv("DOCKER_ENV") == "true" or os.path.exists("/.dockerenv")
        auth_host = os.getenv("SERVICE_HOST_AUTH", "127.0.0.1" if not is_docker else "auth-service")
        host_host = os.getenv("SERVICE_HOST_HOST", "127.0.0.1" if not is_docker else "host-service")

        self._fallback_urls = {
            "auth-service": auth_host,
            "host-service": host_host,
        }

        # ✅ 从环境变量读取服务端口映射（用于后备地址）
        self._service_ports = {
            "auth-service": int(os.getenv("SERVICE_PORT_AUTH", "8001")),
            "host-service": int(os.getenv("SERVICE_PORT_HOST", "8003")),
        }

        logger.info(
            "服务发现工具初始化完成",
            extra={
                "nacos_enabled": nacos_manager is not None,
                "cache_ttl": cache_ttl,
                "fallback_urls": self._fallback_urls,
            },
        )

    def set_nacos_manager(self, nacos_manager: NacosManager) -> None:
        """设置 Nacos 管理器

        Args:
            nacos_manager: Nacos 管理器实例
        """
        self.nacos_manager = nacos_manager
        logger.info("Nacos 管理器已设置")

    async def get_service_url(self, service_name: str) -> str:
        """获取服务 URL

        优先级：
        1. 尝试从缓存获取（如果未过期）
        2. 从 Nacos 获取最新实例
        3. 使用后备静态地址

        Args:
            service_name: 服务名称（如 "auth-service"）

        Returns:
            服务 URL（如 "http://172.20.0.101:8001"）

        Example:
            >>> url = await discovery.get_service_url("auth-service")
            >>> print(url)  # http://172.20.0.101:8001
        """
        # 检查缓存
        cached_url = self._get_from_cache(service_name)
        if cached_url:
            logger.debug(f"从缓存获取服务地址: {service_name} -> {cached_url}")
            return cached_url

        # 从 Nacos 获取
        if self.nacos_manager:
            nacos_url = await self._get_from_nacos(service_name)
            if nacos_url:
                # 更新缓存
                self._update_cache(service_name, nacos_url)
                logger.info(f"从 Nacos 获取服务地址: {service_name} -> {nacos_url}")
                return nacos_url

        # 使用后备地址
        fallback_url = self._get_fallback_url(service_name)
        logger.warning(
            f"使用后备服务地址: {service_name} -> {fallback_url}",
            extra={"reason": "Nacos 不可用或未配置"},
        )
        return fallback_url

    def _get_from_cache(self, service_name: str) -> Optional[str]:
        """从缓存获取服务 URL

        Args:
            service_name: 服务名称

        Returns:
            服务 URL，如果缓存过期或不存在则返回 None
        """
        if service_name not in self._cache:
            return None

        cache_entry = self._cache[service_name]
        timestamp = cache_entry.get("timestamp", 0)

        # 检查是否过期
        if time.time() - timestamp > self.cache_ttl:
            logger.debug(f"缓存已过期: {service_name}")
            del self._cache[service_name]
            return None

        return cache_entry.get("url")

    async def _get_from_nacos(self, service_name: str) -> Optional[str]:
        """从 Nacos 获取服务实例

        Args:
            service_name: 服务名称

        Returns:
            服务 URL，如果获取失败则返回 None
        """
        if not self.nacos_manager:
            logger.warning("Nacos 管理器未设置")
            return None

        try:
            # 获取健康的服务实例
            instance = await self.nacos_manager.get_service_instance(service_name)

            if not instance:
                logger.warning(f"Nacos 中未找到服务实例: {service_name}")
                return None

            # 构建 URL
            ip = instance.get("ip")
            port = instance.get("port")

            if not ip or not port:
                logger.error(f"服务实例缺少 IP 或端口: {service_name}, 实例: {instance}")
                return None

            url = f"http://{ip}:{port}"
            return url

        except Exception as e:
            logger.error(
                f"从 Nacos 获取服务实例失败: {service_name}",
                extra={"error": str(e)},
                exc_info=True,
            )
            return None

    def _update_cache(self, service_name: str, url: str) -> None:
        """更新缓存

        Args:
            service_name: 服务名称
            url: 服务 URL
        """
        self._cache[service_name] = {"url": url, "timestamp": time.time()}

    def _get_fallback_url(self, service_name: str) -> str:
        """获取后备 URL

        Args:
            service_name: 服务名称（可能是短名称如 "host" 或完整名称如 "host-service"）

        Returns:
            服务 URL
        """
        # 短名称到完整服务名的映射
        short_to_full = {
            "auth": "auth-service",
            "host": "host-service",
        }

        # 如果传入的是短名称，先映射为完整服务名
        full_service_name = short_to_full.get(service_name, service_name)

        # 获取后备主机名
        fallback_host = self._fallback_urls.get(full_service_name, full_service_name)

        # ✅ 从配置读取端口（支持环境变量覆盖）
        port = self._service_ports.get(full_service_name, 8000)

        return f"http://{fallback_host}:{port}"

    async def refresh_cache(self, service_name: Optional[str] = None) -> None:
        """手动刷新缓存

        Args:
            service_name: 服务名称，如果为 None 则刷新所有缓存
        """
        if service_name:
            # 刷新单个服务
            if service_name in self._cache:
                del self._cache[service_name]
                logger.info(f"缓存已刷新: {service_name}")
        else:
            # 刷新所有缓存
            self._cache.clear()
            logger.info("所有缓存已刷新")

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("缓存已清空")


# 全局服务发现实例
_service_discovery_instance: Optional[ServiceDiscovery] = None


def get_service_discovery() -> ServiceDiscovery:
    """获取全局服务发现实例（单例模式）

    Returns:
        ServiceDiscovery 实例

    Note:
        - 首次调用时会自动创建实例
        - 如果需要设置 Nacos 管理器，请在初始化后调用 set_nacos_manager()
    """
    global _service_discovery_instance

    if _service_discovery_instance is None:
        _service_discovery_instance = ServiceDiscovery()
        logger.info("✅ 服务发现实例已创建")

    return _service_discovery_instance


def init_service_discovery(nacos_manager: Optional[NacosManager] = None, cache_ttl: int = 30) -> ServiceDiscovery:
    """初始化全局服务发现实例

    Args:
        nacos_manager: Nacos 管理器实例
        cache_ttl: 缓存过期时间（秒）

    Returns:
        ServiceDiscovery 实例
    """
    global _service_discovery_instance

    _service_discovery_instance = ServiceDiscovery(nacos_manager=nacos_manager, cache_ttl=cache_ttl)

    logger.info("✅ 服务发现实例已初始化", extra={"cache_ttl": cache_ttl})

    return _service_discovery_instance
