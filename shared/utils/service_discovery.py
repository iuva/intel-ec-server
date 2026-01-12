"""Service Discovery Utility Class

Provides functionality to dynamically acquire service addresses from Nacos, supporting:
- Service instance caching
- Automatic refresh
- Load balancing
- Failover
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional

# Use try-except approach to handle path imports
try:
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager

logger = get_logger(__name__)


class ServiceDiscovery:
    """Service Discovery Utility Class

    Dynamically acquires service addresses from Nacos, supporting caching and automatic refresh.

    Usage example:
        >>> discovery = ServiceDiscovery(nacos_manager)
        >>> auth_url = await discovery.get_service_url("auth-service")
        >>> print(auth_url)  # http://172.20.0.101:8001
    """

    def __init__(
        self,
        nacos_manager: Optional[NacosManager] = None,
        cache_ttl: int = 30,
        load_balance_strategy: str = "round_robin",
    ):
        """Initialize service discovery

        Args:
            nacos_manager: Nacos manager instance (optional)
            cache_ttl: Cache expiration time (seconds), default 30 seconds
            load_balance_strategy: Load balancing strategy, optional values:
                - "round_robin": Round-robin (default)
                - "random": Random
                - "weighted_random": Weighted random
        """
        self.nacos_manager = nacos_manager
        self.cache_ttl = cache_ttl
        self.load_balance_strategy = load_balance_strategy

        # Service address cache: {service_name: {"url": "http://...", "timestamp": 123456}}
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Service instance list cache: {service_name: {"instances": [...], "timestamp": 123456}}
        self._instances_cache: Dict[str, Dict[str, Any]] = {}

        # Round-robin counter: {service_name: current_index}
        self._round_robin_index: Dict[str, int] = {}

        # Whether running in Docker environment (affects default fallback IP)
        self._is_docker = os.getenv("DOCKER_ENV") == "true" or os.path.exists("/.dockerenv")

        # Fallback static service addresses (environment variables take precedence)
        self._service_ip_envs = {
            "gateway-service": os.getenv("GATEWAY_SERVICE_IP"),
            "auth-service": os.getenv("AUTH_SERVICE_IP"),
            "host-service": os.getenv("HOST_SERVICE_IP"),
        }

        # Docker default service names (for inter-container communication)
        self._default_service_hosts = {
            "gateway-service": "gateway-service",
            "auth-service": "auth-service",
            "host-service": "host-service",
        }

        # ✅ Read service port mapping from environment variables (for fallback addresses)
        self._service_ports = {
            "gateway-service": int(os.getenv("GATEWAY_SERVICE_PORT", "8000")),
            "auth-service": int(os.getenv("AUTH_SERVICE_PORT", "8001")),
            "host-service": int(os.getenv("HOST_SERVICE_PORT", "8003")),
        }

        # ✅ Read local multi-instance configuration from environment variables
        # (format: HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004)
        self._local_instances: Dict[str, List[Dict[str, Any]]] = {}
        self._load_local_instances()

        logger.info(
            "Service Discovery tool initialized",
            extra={
                "nacos_enabled": nacos_manager is not None,
                "cache_ttl": cache_ttl,
                "load_balance_strategy": load_balance_strategy,
                "service_ip_envs": self._service_ip_envs,
                "local_instances": {service: len(instances) for service, instances in self._local_instances.items()},
            },
        )

    def set_nacos_manager(self, nacos_manager: NacosManager) -> None:
        """Set Nacos manager

        Args:
            nacos_manager: Nacos manager instance
        """
        self.nacos_manager = nacos_manager
        logger.info("Nacos manager set")

    async def get_service_url(self, service_name: str) -> str:
        """Get service URL (supports load balancing)

        Priority:
        1. Get service instance list from Nacos (supports multiple instances)
        2. Read local multi-instance configuration from environment variables (supports round-robin)
        3. Use fallback static address (single instance)

        Args:
            service_name: Service name (could be short name like "host" or full name like "host-service")

        Returns:
            Service URL (e.g., "http://172.20.0.101:8001")

        Example:
            >>> url = await discovery.get_service_url("auth-service")
            >>> print(url)  # http://172.20.0.101:8001
        """
        # ✅ Standardize service name (short name -> full service name)
        normalized_service_name = self._normalize_service_name(service_name)

        # Priority 1: Get service instance list from Nacos
        if self.nacos_manager:
            instances = await self._get_instances_from_nacos(normalized_service_name)
            if instances:
                # Select instance according to load balancing strategy
                selected_instance = self._select_instance(instances, normalized_service_name)
                if selected_instance:
                    url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                    logger.info(
                        f"Get service address from Nacos: {normalized_service_name} -> {url}",
                        extra={
                            "strategy": self.load_balance_strategy,
                            "total_instances": len(instances),
                            "selected_ip": selected_instance["ip"],
                            "selected_port": selected_instance["port"],
                        },
                    )
                    return url
            else:
                # Nacos has no instances, log and continue to check local configuration
                logger.debug(
                    f"Nacos did not find instances, checking local configuration: {normalized_service_name}",
                    extra={"service_name": service_name, "normalized": normalized_service_name},
                )

        # Priority 2: Read local multi-instance configuration from environment variables (supports round-robin)
        local_instances = self._get_local_instances(normalized_service_name)
        logger.debug(
            f"Checking local instance configuration: {normalized_service_name}",
            extra={
                "service_name": service_name,
                "normalized": normalized_service_name,
                "local_instances_count": len(local_instances),
                "local_instances": [f"{inst['ip']}:{inst['port']}" for inst in local_instances]
                if local_instances
                else [],
            },
        )
        if local_instances:
            selected_instance = self._select_instance(local_instances, normalized_service_name)
            if selected_instance:
                url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                logger.info(
                    f"Get service address from local configuration: {normalized_service_name} -> {url}",
                    extra={
                        "strategy": self.load_balance_strategy,
                        "total_instances": len(local_instances),
                        "selected_ip": selected_instance["ip"],
                        "selected_port": selected_instance["port"],
                        "all_instances": [f"{inst['ip']}:{inst['port']}" for inst in local_instances],
                    },
                )
                return url
        else:
            logger.debug(
                f"Local instance configuration not found: {normalized_service_name}",
                extra={
                    "service_name": service_name,
                    "normalized": normalized_service_name,
                },
            )

        # Priority 3: Use fallback address (single instance)
        fallback_url = self._get_fallback_url(service_name)
        logger.warning(
            f"Using fallback service address: {normalized_service_name} -> {fallback_url}",
            extra={
                "reason": "Nacos unavailable and local multi-instances not configured",
                "service_name": service_name,
                "normalized": normalized_service_name,
                "nacos_manager_exists": self.nacos_manager is not None,
                "local_instances_count": len(local_instances),
            },
        )
        return fallback_url

    def _normalize_service_name(self, service_name: str) -> str:
        """Standardize service name (short name -> full service name)

        Args:
            service_name: Service name (could be short name like "host" or full name like "host-service")

        Returns:
            Full service name (e.g., "host-service")
        """
        # Mapping from short names to full service names
        short_to_full = {
            "auth": "auth-service",
            "host": "host-service",
            "admin": "admin-service",
            "gateway": "gateway-service",
        }

        # If already a full service name, return directly
        if "-service" in service_name:
            return service_name

        # If it's a short name, map to full service name
        return short_to_full.get(service_name, service_name)

    async def get_websocket_service_url(
        self,
        service_name: str,
        session_key: str,
    ) -> str:
        """Get WebSocket service URL (supports session stickiness)

        Use the hash value of session_key to select an instance, ensuring the same session_key
        always routes to the same instance.

        Args:
            service_name: Service name (e.g., "host-service")
            session_key: Session key (e.g., host_id), for session stickiness

        Returns:
            Service URL (e.g., "http://172.20.0.101:8001")

        Example:
            >>> url = await discovery.get_websocket_service_url("host-service", "host_123")
            >>> print(url)  # http://172.20.0.103:8003
        """
        # Priority 1: Get instances from Nacos
        if self.nacos_manager:
            instances = await self._get_instances_from_nacos(service_name)
            if instances:
                selected_instance = self._select_instance_by_hash(instances, session_key)
                if selected_instance:
                    url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                    logger.info(
                        f"WebSocket session stickiness selection (Nacos): {service_name} -> {url}",
                        extra={
                            "session_key": session_key,
                            "strategy": "hash_based_sticky",
                            "total_instances": len(instances),
                            "selected_ip": selected_instance["ip"],
                            "selected_port": selected_instance["port"],
                        },
                    )
                    return url

        # Priority 2: Get instances from local configuration
        local_instances = self._get_local_instances(service_name)
        if local_instances:
            selected_instance = self._select_instance_by_hash(local_instances, session_key)
            if selected_instance:
                url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                logger.info(
                    f"WebSocket session stickiness selection (local): {service_name} -> {url}",
                    extra={
                        "session_key": session_key,
                        "strategy": "hash_based_sticky",
                        "total_instances": len(local_instances),
                        "selected_ip": selected_instance["ip"],
                        "selected_port": selected_instance["port"],
                    },
                )
                return url

        # Priority 3: Fallback address
        fallback_url = self._get_fallback_url(service_name)
        logger.warning(
            f"WebSocket using fallback service address: {service_name} -> {fallback_url}",
            extra={
                "reason": "Nacos unavailable and local multi-instances not configured",
                "session_key": session_key,
            },
        )
        return fallback_url

    def _select_instance_by_hash(
        self,
        instances: List[Dict[str, Any]],
        session_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Select instance based on hash value of session key

        Use the hash value of session_key to select an instance, ensuring the same session_key
        always routes to the same instance.

        Args:
            instances: Instance list
            session_key: Session key

        Returns:
            Selected instance
        """
        if not instances:
            return None

        if len(instances) == 1:
            return instances[0]

        # Select instance using hash value of session key
        # Use Python built-in hash() function to ensure same input produces same output
        hash_value = hash(session_key)
        selected_index = abs(hash_value) % len(instances)
        selected_instance = instances[selected_index]

        logger.debug(
            "Select instance based on hash",
            extra={
                "session_key": session_key,
                "hash_value": hash_value,
                "selected_index": selected_index,
                "total_instances": len(instances),
                "selected_ip": selected_instance["ip"],
                "selected_port": selected_instance["port"],
            },
        )

        return selected_instance

    def _get_from_cache(self, service_name: str) -> Optional[str]:
        """Get service URL from cache

        Args:
            service_name: Service name

        Returns:
            Service URL, or None if cache expired or does not exist
        """
        if service_name not in self._cache:
            return None

        cache_entry = self._cache[service_name]
        timestamp = cache_entry.get("timestamp", 0)

        # Check if expired
        if time.time() - timestamp > self.cache_ttl:
            logger.debug(f"Cache expired: {service_name}")
            del self._cache[service_name]
            return None

        return cache_entry.get("url")

    async def _get_instances_from_nacos(self, service_name: str) -> List[Dict[str, Any]]:
        """Get service instance list from Nacos

        Args:
            service_name: Service name

        Returns:
            Service instance list, or empty list if acquisition fails
        """
        if not self.nacos_manager:
            logger.warning("Nacos manager not set")
            return []

        # Check instance cache
        cached_instances = self._get_instances_from_cache(service_name)
        if cached_instances:
            logger.debug(f"Get service instance list from cache: {service_name}, Count: {len(cached_instances)}")
            return cached_instances

        try:
            # Get all healthy service instances
            instances = await self.nacos_manager.discover_service(service_name)

            if not instances:
                logger.warning(f"Service instances not found in Nacos: {service_name}")
                return []

            # Filter healthy instances
            healthy_instances = [inst for inst in instances if inst.get("healthy", True)]

            if not healthy_instances:
                logger.warning(f"No healthy service instances: {service_name}")
                return []

            # Update instance cache
            self._update_instances_cache(service_name, healthy_instances)
            logger.info(
                f"Get service instance list from Nacos: {service_name}",
                extra={
                    "total_instances": len(instances),
                    "healthy_instances": len(healthy_instances),
                },
            )

            return healthy_instances

        except Exception as e:
            logger.error(
                f"Failed to get service instances from Nacos: {service_name}",
                extra={"error": str(e)},
                exc_info=True,
            )
            return []

    def _get_instances_from_cache(self, service_name: str) -> List[Dict[str, Any]]:
        """Get service instance list from cache

        Args:
            service_name: Service name

        Returns:
            Service instance list, or empty list if cache expired or does not exist
        """
        if service_name not in self._instances_cache:
            return []

        cache_entry = self._instances_cache[service_name]
        timestamp = cache_entry.get("timestamp", 0)

        # Check if expired
        if time.time() - timestamp > self.cache_ttl:
            logger.debug(f"Instance cache expired: {service_name}")
            del self._instances_cache[service_name]
            return []

        return cache_entry.get("instances", [])

    def _update_instances_cache(self, service_name: str, instances: List[Dict[str, Any]]) -> None:
        """Update instance cache

        Args:
            service_name: Service name
            instances: Service instance list
        """
        self._instances_cache[service_name] = {
            "instances": instances,
            "timestamp": time.time(),
        }

    def _select_instance(self, instances: List[Dict[str, Any]], service_name: str) -> Optional[Dict[str, Any]]:
        """Select service instance based on load balancing strategy

        Args:
            instances: Service instance list
            service_name: Service name

        Returns:
            Selected service instance
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
            # Default to round-robin
            return self._select_instance_round_robin(instances, service_name)

    def _select_instance_round_robin(self, instances: List[Dict[str, Any]], service_name: str) -> Dict[str, Any]:
        """Round-robin select instance

        Args:
            instances: Service instance list
            service_name: Service name

        Returns:
            Selected instance
        """
        # Initialize or get current index
        if service_name not in self._round_robin_index:
            self._round_robin_index[service_name] = 0

        # Get current index
        current_index = self._round_robin_index[service_name]

        # Select instance
        selected_instance = instances[current_index % len(instances)]

        # Update index (use next instance for next request)
        self._round_robin_index[service_name] = (current_index + 1) % len(instances)

        logger.debug(
            f"Round-robin select instance: {service_name}",
            extra={
                "current_index": current_index,
                "total_instances": len(instances),
                "selected_ip": selected_instance.get("ip"),
                "selected_port": selected_instance.get("port"),
            },
        )

        return selected_instance

    def _select_instance_weighted_random(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Weighted random select instance

        Args:
            instances: Service instance list

        Returns:
            Selected instance
        """
        import random

        # Calculate total weight
        total_weight = sum(inst.get("weight", 1.0) for inst in instances)

        # Generate random number
        rand = random.uniform(0, total_weight)

        # Weighted random selection
        current_weight = 0.0
        for instance in instances:
            current_weight += instance.get("weight", 1.0)
            if rand <= current_weight:
                return instance

        # Default to return first instance
        return instances[0]

    def _update_cache(self, service_name: str, url: str) -> None:
        """Update cache

        Args:
            service_name: Service name
            url: Service URL
        """
        self._cache[service_name] = {"url": url, "timestamp": time.time()}

    def _load_local_instances(self) -> None:
        """Load local multi-instance configuration from environment variables

        Supported formats:
        - HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004
        - AUTH_SERVICE_INSTANCES=127.0.0.1:8001,127.0.0.1:8002
        """
        # Service name mapping
        service_env_map = {
            "host-service": "HOST_SERVICE_INSTANCES",
            "auth-service": "AUTH_SERVICE_INSTANCES",
            "gateway-service": "GATEWAY_SERVICE_INSTANCES",
        }

        for service_name, env_key in service_env_map.items():
            instances_str = os.getenv(env_key)
            logger.debug(
                f"Checking environment variable: {env_key}",
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
                            instances.append(
                                {
                                    "ip": ip.strip(),
                                    "port": port,
                                    "healthy": True,
                                    "weight": 1.0,
                                }
                            )
                        except ValueError:
                            logger.warning(
                                f"Invalid port number: {instance_str}",
                                extra={"env_key": env_key, "instance_str": instance_str},
                            )
                    else:
                        logger.warning(
                            f"Invalid instance format (missing port): {instance_str}",
                            extra={"env_key": env_key, "instance_str": instance_str},
                        )

                if instances:
                    self._local_instances[service_name] = instances
                    logger.info(
                        f"✅ Load local multi-instance configuration: {service_name}",
                        extra={
                            "env_key": env_key,
                            "instances_count": len(instances),
                            "instances": [f"{inst['ip']}:{inst['port']}" for inst in instances],
                        },
                    )
                else:
                    logger.warning(
                        f"Environment variable {env_key} exists but no valid instances parsed",
                        extra={"env_key": env_key, "value": instances_str},
                    )
            else:
                logger.debug(f"Environment variable not set: {env_key}")

    def _get_local_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """Get locally configured service instance list

        Args:
            service_name: Service name (should be full service name like "host-service")

        Returns:
            Service instance list
        """
        # Directly use service name to look up (already normalized)
        return self._local_instances.get(service_name, [])

    def _get_fallback_url(self, service_name: str) -> str:
        """Get fallback URL

        Args:
            service_name: Service name (could be short name like "host" or full name like "host-service")

        Returns:
            Service URL
        """
        # Mapping from short names to full service names
        short_to_full = {
            "auth": "auth-service",
            "host": "host-service",
        }

        # If a short name is ***REMOVED***ed, map to full service name first
        full_service_name = short_to_full.get(service_name, service_name)

        # Get fallback hostname
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
        """Manually refresh cache

        Args:
            service_name: Service name, if None refresh all caches
        """
        if service_name:
            # Refresh single service
            if service_name in self._cache:
                del self._cache[service_name]
                logger.info(f"Cache refreshed: {service_name}")
        else:
            # Refresh all caches
            self._cache.clear()
            logger.info("All caches refreshed")

    def clear_cache(self) -> None:
        """Clear cache"""
        self._cache.clear()
        logger.info("Cache cleared")


# Global service discovery instance
_service_discovery_instance: Optional[ServiceDiscovery] = None


def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance (singleton pattern)

    Returns:
        ServiceDiscovery instance

    Note:
        - Instance is automatically created on first call
        - If Nacos manager needs to be set, call set_nacos_manager() after initialization
    """
    global _service_discovery_instance

    if _service_discovery_instance is None:
        _service_discovery_instance = ServiceDiscovery()
        logger.info("✅ Service discovery instance created")

    return _service_discovery_instance


def init_service_discovery(
    nacos_manager: Optional[NacosManager] = None,
    cache_ttl: int = 30,
    load_balance_strategy: str = "round_robin",
) -> ServiceDiscovery:
    """Initialize global service discovery instance

    Args:
        nacos_manager: Nacos manager instance
        cache_ttl: Cache expiration time (seconds)
        load_balance_strategy: Load balancing strategy, optional values:
            - "round_robin": Round-robin (default)
            - "random": Random
            - "weighted_random": Weighted random

    Returns:
        ServiceDiscovery instance
    """
    global _service_discovery_instance

    _service_discovery_instance = ServiceDiscovery(
        nacos_manager=nacos_manager,
        cache_ttl=cache_ttl,
        load_balance_strategy=load_balance_strategy,
    )

    logger.info(
        "✅ Service discovery instance initialized",
        extra={"cache_ttl": cache_ttl, "load_balance_strategy": load_balance_strategy},
    )

    return _service_discovery_instance
