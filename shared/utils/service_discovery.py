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
from typing import Any, Dict, List, Optional

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

    def __init__(self, nacos_manager: Optional[NacosManager] = None, cache_ttl: int = 30, load_balance_strategy: str = "round_robin"):
        """初始化服务发现

        Args:
            nacos_manager: Nacos 管理器实例（可选）
            cache_ttl: 缓存过期时间（秒），默认 30 秒
            load_balance_strategy: 负载均衡策略，可选值：
                - "round_robin": 轮询（默认）
                - "random": 随机
                - "weighted_random": 加权随机
        """
        self.nacos_manager = nacos_manager
        self.cache_ttl = cache_ttl
        self.load_balance_strategy = load_balance_strategy

        # 服务地址缓存: {service_name: {"url": "http://...", "timestamp": 123456}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 服务实例列表缓存: {service_name: {"instances": [...], "timestamp": 123456}}
        self._instances_cache: Dict[str, Dict[str, Any]] = {}
        
        # 轮询计数器: {service_name: current_index}
        self._round_robin_index: Dict[str, int] = {}

        # 是否运行在 Docker 环境（影响默认回退 IP）
        self._is_docker = os.getenv("DOCKER_ENV") == "true" or os.path.exists("/.dockerenv")

        # 后备静态服务地址（环境变量优先）
        self._service_ip_envs = {
            "gateway-service": os.getenv("GATEWAY_SERVICE_IP"),
            "auth-service": os.getenv("AUTH_SERVICE_IP"),
            "host-service": os.getenv("HOST_SERVICE_IP"),
        }

        # Docker 默认服务名（用于容器间通信）
        self._default_service_hosts = {
            "gateway-service": "gateway-service",
            "auth-service": "auth-service",
            "host-service": "host-service",
        }

        # ✅ 从环境变量读取服务端口映射（用于后备地址）
        self._service_ports = {
            "gateway-service": int(os.getenv("GATEWAY_SERVICE_PORT", "8000")),
            "auth-service": int(os.getenv("AUTH_SERVICE_PORT", "8001")),
            "host-service": int(os.getenv("HOST_SERVICE_PORT", "8003")),
        }

        # ✅ 从环境变量读取本地多实例配置（格式：HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004）
        self._local_instances: Dict[str, List[Dict[str, Any]]] = {}
        self._load_local_instances()

        logger.info(
            "服务发现工具初始化完成",
            extra={
                "nacos_enabled": nacos_manager is not None,
                "cache_ttl": cache_ttl,
                "load_balance_strategy": load_balance_strategy,
                "service_ip_envs": self._service_ip_envs,
                "local_instances": {
                    service: len(instances) 
                    for service, instances in self._local_instances.items()
                },
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
        """获取服务 URL（支持负载均衡）

        优先级：
        1. 从 Nacos 获取服务实例列表（支持多个实例）
        2. 从环境变量读取本地多实例配置（支持轮询）
        3. 使用后备静态地址（单个实例）

        Args:
            service_name: 服务名称（可能是短名称如 "host" 或完整名称如 "host-service"）

        Returns:
            服务 URL（如 "http://172.20.0.101:8001"）

        Example:
            >>> url = await discovery.get_service_url("auth-service")
            >>> print(url)  # http://172.20.0.101:8001
        """
        # ✅ 标准化服务名称（短名称 -> 完整服务名）
        normalized_service_name = self._normalize_service_name(service_name)

        # 优先级 1: 从 Nacos 获取服务实例列表
        if self.nacos_manager:
            instances = await self._get_instances_from_nacos(normalized_service_name)
            if instances:
                # 根据负载均衡策略选择实例
                selected_instance = self._select_instance(instances, normalized_service_name)
                if selected_instance:
                    url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                    logger.info(
                        f"从 Nacos 获取服务地址: {normalized_service_name} -> {url}",
                        extra={
                            "strategy": self.load_balance_strategy,
                            "total_instances": len(instances),
                            "selected_ip": selected_instance['ip'],
                            "selected_port": selected_instance['port'],
                        },
                    )
                    return url
            else:
                # Nacos 没有实例，记录日志并继续检查本地配置
                logger.debug(
                    f"Nacos 未找到实例，检查本地配置: {normalized_service_name}",
                    extra={"service_name": service_name, "normalized": normalized_service_name},
                )

        # 优先级 2: 从环境变量读取本地多实例配置（支持轮询）
        local_instances = self._get_local_instances(normalized_service_name)
        logger.debug(
            f"检查本地实例配置: {normalized_service_name}",
            extra={
                "service_name": service_name,
                "normalized": normalized_service_name,
                "local_instances_count": len(local_instances),
                "local_instances": [f"{inst['ip']}:{inst['port']}" for inst in local_instances] if local_instances else [],
            },
        )
        if local_instances:
            selected_instance = self._select_instance(local_instances, normalized_service_name)
            if selected_instance:
                url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                logger.info(
                    f"从本地配置获取服务地址: {normalized_service_name} -> {url}",
                    extra={
                        "strategy": self.load_balance_strategy,
                        "total_instances": len(local_instances),
                        "selected_ip": selected_instance['ip'],
                        "selected_port": selected_instance['port'],
                        "all_instances": [f"{inst['ip']}:{inst['port']}" for inst in local_instances],
                    },
                )
                return url
        else:
            logger.debug(
                f"未找到本地实例配置: {normalized_service_name}",
                extra={
                    "service_name": service_name,
                    "normalized": normalized_service_name,
                },
            )

        # 优先级 3: 使用后备地址（单个实例）
        fallback_url = self._get_fallback_url(service_name)
        logger.warning(
            f"使用后备服务地址: {normalized_service_name} -> {fallback_url}",
            extra={
                "reason": "Nacos 不可用且未配置本地多实例",
                "service_name": service_name,
                "normalized": normalized_service_name,
                "nacos_manager_exists": self.nacos_manager is not None,
                "local_instances_count": len(local_instances),
            },
        )
        return fallback_url

    def _normalize_service_name(self, service_name: str) -> str:
        """标准化服务名称（短名称 -> 完整服务名）

        Args:
            service_name: 服务名称（可能是短名称如 "host" 或完整名称如 "host-service"）

        Returns:
            完整服务名称（如 "host-service"）
        """
        # 短名称到完整服务名的映射
        short_to_full = {
            "auth": "auth-service",
            "host": "host-service",
            "admin": "admin-service",
            "gateway": "gateway-service",
        }

        # 如果已经是完整服务名，直接返回
        if "-service" in service_name:
            return service_name

        # 如果是短名称，映射为完整服务名
        return short_to_full.get(service_name, service_name)

    async def get_websocket_service_url(
        self,
        service_name: str,
        session_key: str,
    ) -> str:
        """获取 WebSocket 服务 URL（支持会话粘性）

        使用 session_key 的哈希值选择实例，确保同一个 session_key
        总是路由到同一个实例。

        Args:
            service_name: 服务名称（如 "host-service"）
            session_key: 会话键（如 host_id），用于会话粘性

        Returns:
            服务 URL（如 "http://172.20.0.101:8001"）

        Example:
            >>> url = await discovery.get_websocket_service_url("host-service", "host_123")
            >>> print(url)  # http://172.20.0.103:8003
        """
        # 优先级 1: 从 Nacos 获取实例
        if self.nacos_manager:
            instances = await self._get_instances_from_nacos(service_name)
            if instances:
                selected_instance = self._select_instance_by_hash(instances, session_key)
                if selected_instance:
                    url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                    logger.info(
                        f"WebSocket 会话粘性选择（Nacos）: {service_name} -> {url}",
                        extra={
                            "session_key": session_key,
                            "strategy": "hash_based_sticky",
                            "total_instances": len(instances),
                            "selected_ip": selected_instance['ip'],
                            "selected_port": selected_instance['port'],
                        },
                    )
                    return url

        # 优先级 2: 从本地配置获取实例
        local_instances = self._get_local_instances(service_name)
        if local_instances:
            selected_instance = self._select_instance_by_hash(local_instances, session_key)
            if selected_instance:
                url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                logger.info(
                    f"WebSocket 会话粘性选择（本地）: {service_name} -> {url}",
                    extra={
                        "session_key": session_key,
                        "strategy": "hash_based_sticky",
                        "total_instances": len(local_instances),
                        "selected_ip": selected_instance['ip'],
                        "selected_port": selected_instance['port'],
                    },
                )
                return url

        # 优先级 3: 后备地址
        fallback_url = self._get_fallback_url(service_name)
        logger.warning(
            f"WebSocket 使用后备服务地址: {service_name} -> {fallback_url}",
            extra={
                "reason": "Nacos 不可用且未配置本地多实例",
                "session_key": session_key,
            },
        )
        return fallback_url

    def _select_instance_by_hash(
        self,
        instances: List[Dict[str, Any]],
        session_key: str,
    ) -> Optional[Dict[str, Any]]:
        """基于会话键的哈希值选择实例

        使用 session_key 的哈希值选择实例，确保同一个 session_key
        总是路由到同一个实例。

        Args:
            instances: 实例列表
            session_key: 会话键

        Returns:
            选中的实例
        """
        if not instances:
            return None

        if len(instances) == 1:
            return instances[0]

        # 使用会话键的哈希值选择实例
        # 使用 Python 内置 hash() 函数，确保相同输入产生相同输出
        hash_value = hash(session_key)
        selected_index = abs(hash_value) % len(instances)
        selected_instance = instances[selected_index]

        logger.debug(
            f"基于哈希选择实例",
            extra={
                "session_key": session_key,
                "hash_value": hash_value,
                "selected_index": selected_index,
                "total_instances": len(instances),
                "selected_ip": selected_instance['ip'],
                "selected_port": selected_instance['port'],
            },
        )

        return selected_instance

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

    async def _get_instances_from_nacos(self, service_name: str) -> List[Dict[str, Any]]:
        """从 Nacos 获取服务实例列表

        Args:
            service_name: 服务名称

        Returns:
            服务实例列表，如果获取失败则返回空列表
        """
        if not self.nacos_manager:
            logger.warning("Nacos 管理器未设置")
            return []

        # 检查实例缓存
        cached_instances = self._get_instances_from_cache(service_name)
        if cached_instances:
            logger.debug(f"从缓存获取服务实例列表: {service_name}, 数量: {len(cached_instances)}")
            return cached_instances

        try:
            # 获取所有健康的服务实例
            instances = await self.nacos_manager.discover_service(service_name)

            if not instances:
                logger.warning(f"Nacos 中未找到服务实例: {service_name}")
                return []

            # 过滤健康的实例
            healthy_instances = [inst for inst in instances if inst.get("healthy", True)]

            if not healthy_instances:
                logger.warning(f"没有健康的服务实例: {service_name}")
                return []

            # 更新实例缓存
            self._update_instances_cache(service_name, healthy_instances)
            logger.info(
                f"从 Nacos 获取服务实例列表: {service_name}",
                extra={
                    "total_instances": len(instances),
                    "healthy_instances": len(healthy_instances),
                },
            )

            return healthy_instances

        except Exception as e:
            logger.error(
                f"从 Nacos 获取服务实例失败: {service_name}",
                extra={"error": str(e)},
                exc_info=True,
            )
            return []

    def _get_instances_from_cache(self, service_name: str) -> List[Dict[str, Any]]:
        """从缓存获取服务实例列表

        Args:
            service_name: 服务名称

        Returns:
            服务实例列表，如果缓存过期或不存在则返回空列表
        """
        if service_name not in self._instances_cache:
            return []

        cache_entry = self._instances_cache[service_name]
        timestamp = cache_entry.get("timestamp", 0)

        # 检查是否过期
        if time.time() - timestamp > self.cache_ttl:
            logger.debug(f"实例缓存已过期: {service_name}")
            del self._instances_cache[service_name]
            return []

        return cache_entry.get("instances", [])

    def _update_instances_cache(self, service_name: str, instances: List[Dict[str, Any]]) -> None:
        """更新实例缓存

        Args:
            service_name: 服务名称
            instances: 服务实例列表
        """
        self._instances_cache[service_name] = {
            "instances": instances,
            "timestamp": time.time(),
        }

    def _select_instance(self, instances: List[Dict[str, Any]], service_name: str) -> Optional[Dict[str, Any]]:
        """根据负载均衡策略选择服务实例

        Args:
            instances: 服务实例列表
            service_name: 服务名称

        Returns:
            选中的服务实例
        """
        if not instances:
            return None

        if len(instances) == 1:
            return instances[0]

        if self.load_balance_strategy == "round_robin":
            return self._select_instance_round_robin(instances, service_name)
        elif self.load_balance_strategy == "random":
            import random
            return random.choice(instances)
        elif self.load_balance_strategy == "weighted_random":
            return self._select_instance_weighted_random(instances)
        else:
            # 默认使用轮询
            return self._select_instance_round_robin(instances, service_name)

    def _select_instance_round_robin(self, instances: List[Dict[str, Any]], service_name: str) -> Dict[str, Any]:
        """轮询选择实例

        Args:
            instances: 服务实例列表
            service_name: 服务名称

        Returns:
            选中的实例
        """
        # 初始化或获取当前索引
        if service_name not in self._round_robin_index:
            self._round_robin_index[service_name] = 0

        # 获取当前索引
        current_index = self._round_robin_index[service_name]

        # 选择实例
        selected_instance = instances[current_index % len(instances)]

        # 更新索引（下次请求时使用下一个实例）
        self._round_robin_index[service_name] = (current_index + 1) % len(instances)

        logger.debug(
            f"轮询选择实例: {service_name}",
            extra={
                "current_index": current_index,
                "total_instances": len(instances),
                "selected_ip": selected_instance.get("ip"),
                "selected_port": selected_instance.get("port"),
            },
        )

        return selected_instance

    def _select_instance_weighted_random(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """加权随机选择实例

        Args:
            instances: 服务实例列表

        Returns:
            选中的实例
        """
        import random

        # 计算总权重
        total_weight = sum(inst.get("weight", 1.0) for inst in instances)

        # 生成随机数
        rand = random.uniform(0, total_weight)

        # 加权随机选择
        current_weight = 0.0
        for instance in instances:
            current_weight += instance.get("weight", 1.0)
            if rand <= current_weight:
                return instance

        # 默认返回第一个实例
        return instances[0]

    def _update_cache(self, service_name: str, url: str) -> None:
        """更新缓存

        Args:
            service_name: 服务名称
            url: 服务 URL
        """
        self._cache[service_name] = {"url": url, "timestamp": time.time()}

    def _load_local_instances(self) -> None:
        """从环境变量加载本地多实例配置

        支持格式：
        - HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004
        - AUTH_SERVICE_INSTANCES=127.0.0.1:8001,127.0.0.1:8002
        """
        # 服务名称映射
        service_env_map = {
            "host-service": "HOST_SERVICE_INSTANCES",
            "auth-service": "AUTH_SERVICE_INSTANCES",
            "gateway-service": "GATEWAY_SERVICE_INSTANCES",
        }

        for service_name, env_key in service_env_map.items():
            instances_str = os.getenv(env_key)
            logger.debug(
                f"检查环境变量: {env_key}",
                extra={
                    "env_key": env_key,
                    "value": instances_str if instances_str else "NOT SET",
                    "service_name": service_name,
                },
            )
            if instances_str:
                instances = []
                for instance_str in instances_str.split(","):
                    instance_str = instance_str.strip()
                    if ":" in instance_str:
                        ip, port_str = instance_str.rsplit(":", 1)
                        try:
                            port = int(port_str)
                            instances.append({
                                "ip": ip.strip(),
                                "port": port,
                                "healthy": True,
                                "weight": 1.0,
                            })
                        except ValueError:
                            logger.warning(
                                f"无效的端口号: {instance_str}",
                                extra={"env_key": env_key, "instance_str": instance_str},
                            )
                    else:
                        logger.warning(
                            f"无效的实例格式（缺少端口）: {instance_str}",
                            extra={"env_key": env_key, "instance_str": instance_str},
                        )

                if instances:
                    self._local_instances[service_name] = instances
                    logger.info(
                        f"✅ 加载本地多实例配置: {service_name}",
                        extra={
                            "env_key": env_key,
                            "instances_count": len(instances),
                            "instances": [f"{inst['ip']}:{inst['port']}" for inst in instances],
                        },
                    )
                else:
                    logger.warning(
                        f"环境变量 {env_key} 存在但未解析出有效实例",
                        extra={"env_key": env_key, "value": instances_str},
                    )
            else:
                logger.debug(f"环境变量未设置: {env_key}")

    def _get_local_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """获取本地配置的服务实例列表

        Args:
            service_name: 服务名称（应该是完整服务名如 "host-service"）

        Returns:
            服务实例列表
        """
        # 直接使用服务名称查找（已经标准化）
        return self._local_instances.get(service_name, [])

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
        ip_override = self._service_ip_envs.get(full_service_name)
        if ip_override:
            fallback_host = ip_override
        else:
            if self._is_docker:
                fallback_host = self._default_service_hosts.get(full_service_name, full_service_name)
            else:
                fallback_host = "127.0.0.1"

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


def init_service_discovery(
    nacos_manager: Optional[NacosManager] = None,
    cache_ttl: int = 30,
    load_balance_strategy: str = "round_robin",
) -> ServiceDiscovery:
    """初始化全局服务发现实例

    Args:
        nacos_manager: Nacos 管理器实例
        cache_ttl: 缓存过期时间（秒）
        load_balance_strategy: 负载均衡策略，可选值：
            - "round_robin": 轮询（默认）
            - "random": 随机
            - "weighted_random": 加权随机

    Returns:
        ServiceDiscovery 实例
    """
    global _service_discovery_instance

    _service_discovery_instance = ServiceDiscovery(
        nacos_manager=nacos_manager,
        cache_ttl=cache_ttl,
        load_balance_strategy=load_balance_strategy,
    )

    logger.info(
        "✅ 服务发现实例已初始化",
        extra={"cache_ttl": cache_ttl, "load_balance_strategy": load_balance_strategy},
    )

    return _service_discovery_instance
