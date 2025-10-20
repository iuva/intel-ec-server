"""
Load balancer module

Implements load balancing based on Nacos service discovery
"""

import os
import random
import sys
from typing import Any, Dict, List, Optional

# Use try-except to handle path imports
try:
    from shared.common.exceptions import ServiceUnavailableError
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager
except ImportError:
    # If import fails, add project root directory to Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import ServiceUnavailableError
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager


logger = get_logger(__name__)


class LoadBalancer:
    """Load balancer class

    Based on Nacos service discovery, implements weighted random load balancing algorithm
    """

    def __init__(self, nacos_manager: NacosManager):
        """Initialize load balancer

        Args:
            nacos_manager: Nacos manager instance
        """
        self.nacos_manager = nacos_manager
        # Service instance cache
        self.service_instances_cache: Dict[str, List[Dict[str, Any]]] = {}
        # Cache expiration time (seconds)
        self.cache_ttl = 30

    async def get_service_instance(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service instance

        Use weighted random algorithm to select service instance

        Args:
            service_name: Service name

        Returns:
            Service instance information, contains ip, port, weight, etc.

        Raises:
            ServiceUnavailableError: No available service instances
        """
        try:
            # Get service instance list
            instances = await self._get_instances(service_name)

            if not instances:
                logger.warning("No service instances found", extra={"service_name": service_name})
                raise ServiceUnavailableError(
                    message="No available service instances",
                    code=503,
                    details={"service_name": service_name},
                )

            # Filter healthy instances
            healthy_instances = [inst for inst in instances if inst.get("healthy", True)]

            if not healthy_instances:
                logger.warning("No healthy service instances", extra={"service_name": service_name})
                raise ServiceUnavailableError(
                    message="No healthy service instances",
                    code=503,
                    details={"service_name": service_name},
                )

            # Use weighted random algorithm to select instance
            selected_instance = self._select_instance_weighted(healthy_instances)

            logger.info(
                "Selected service instance",
                extra={
                    "service_name": service_name,
                    "instance_ip": selected_instance.get("ip"),
                    "instance_port": selected_instance.get("port"),
                },
            )

            return selected_instance

        except ServiceUnavailableError:
            raise

        except Exception as e:
            logger.error(
                "Exception getting service instance",
                extra={"service_name": service_name, "error": str(e)},
                exc_info=True,
            )
            raise ServiceUnavailableError(message=str(e), code=503, details={"service_name": service_name})

    async def _get_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """Get service instance list

        Get from cache first, if cache miss then get from Nacos

        Args:
            service_name: Service name

        Returns:
            Service instance list
        """
        # Check cache
        if service_name in self.service_instances_cache:
            logger.debug("Get service instances from cache", extra={"service_name": service_name})
            return self.service_instances_cache[service_name]

        # Get from Nacos
        try:
            instances = await self.nacos_manager.discover_service(service_name)

            if instances:
                # Update cache
                self.service_instances_cache[service_name] = instances
                logger.info(
                    "Get service instances from Nacos",
                    extra={
                        "service_name": service_name,
                        "instance_count": len(instances),
                    },
                )

            return instances

        except Exception as e:
            logger.error(
                "Failed to get service instances from Nacos",
                extra={"service_name": service_name, "error": str(e)},
            )
            return []

    def _select_instance_weighted(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Weighted random selection of instance

        Randomly select based on instance weight, higher weight has higher probability of being selected

        Args:
            instances: Service instance list

        Returns:
            Selected instance
        """
        if not instances:
            raise ValueError("Instance list cannot be empty")

        # If only one instance, return directly
        if len(instances) == 1:
            return instances[0]

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

        # Default return first instance
        return instances[0]

    def clear_cache(self, service_name: Optional[str] = None):
        """Clear cache

        Args:
            service_name: Service name, if None then clear all cache
        """
        if service_name:
            if service_name in self.service_instances_cache:
                del self.service_instances_cache[service_name]
                logger.info("Clear service instance cache", extra={"service_name": service_name})
        else:
            self.service_instances_cache.clear()
            logger.info("Clear all service instance cache")

    async def get_all_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """Get all service instances

        Args:
            service_name: Service name

        Returns:
            Service instance list
        """
        return await self._get_instances(service_name)

    async def check_instance_health(self, service_name: str, ip: str, port: int) -> bool:
        """Check instance health status

        Args:
            service_name: Service name
            ip: Instance IP
            port: Instance port

        Returns:
            Whether instance is healthy
        """
        try:
            instances = await self._get_instances(service_name)

            for instance in instances:
                if instance.get("ip") == ip and instance.get("port") == port:
                    return instance.get("healthy", False)

            return False

        except Exception as e:
            logger.error(
                "Exception checking instance health status",
                extra={
                    "service_name": service_name,
                    "ip": ip,
                    "port": port,
                    "error": str(e),
                },
            )
            return False


# Global load balancer instance
_load_balancer_instance: Optional[LoadBalancer] = None


def get_load_balancer(nacos_manager: NacosManager) -> LoadBalancer:
    """Get load balancer instance (singleton pattern)

    Args:
        nacos_manager: Nacos manager instance

    Returns:
        Load balancer instance
    """
    global _load_balancer_instance

    if _load_balancer_instance is None:
        _load_balancer_instance = LoadBalancer(nacos_manager)

    return _load_balancer_instance
