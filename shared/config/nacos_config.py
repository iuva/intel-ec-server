"""
Nacos Service Discovery Configuration Module

Provides Nacos service registration, discovery, and heartbeat detection functions
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

import nacos

logger = logging.getLogger(__name__)


class NacosManager:
    """Nacos Service Discovery Manager

    Provides service registration, discovery, heartbeat detection and other functions
    """

    def __init__(
        self,
        server_addresses: str,
        namespace: str = "public",
        group: str = "DEFAULT_GROUP",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Initialize Nacos manager

        Args:
            server_addresses: Nacos server address, format: host:port
            namespace: Namespace ID
            group: Group name
            username: Username (optional)
            password: Password (optional)
        """
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.group = group
        self.username = username
        self.password = password

        # Initialize Nacos client
        self.client = nacos.NacosClient(
            server_addresses=server_addresses,
            namespace=namespace,
            username=username,
            password=password,
        )

        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_running = False

        logger.info(f"Nacos manager initialized: {server_addresses}")

    async def register_service(
        self,
        service_name: str,
        ip: str,
        port: int,
        ephemeral: bool = True,
        metadata: Optional[Dict[str, str]] = None,
        cluster_name: str = "DEFAULT",
        weight: float = 1.0,
        enabled: bool = True,
    ) -> bool:
        """Register service instance

        Args:
            service_name: Service name
            ip: Service IP address
            port: Service port
            ephemeral: Whether it is an ephemeral instance (ephemeral instances require heartbeat)
            metadata: Metadata
            cluster_name: Cluster name
            weight: Weight
            enabled: Whether enabled (note: Nacos Python SDK does not support this parameter)

        Returns:
            Whether registration is successful
        """
        try:
            # Note: Nacos Python SDK's add_naming_instance does not support the enabled parameter
            # If you need to disable an instance, use remove_naming_instance to deregister the service
            success = self.client.add_naming_instance(
                service_name=service_name,
                ip=ip,
                port=port,
                cluster_name=cluster_name,
                group_name=self.group,
                ephemeral=ephemeral,
                metadata=metadata or {},
                weight=weight,
            )

            if success:
                logger.info(
                    f"Service registered successfully: {service_name} ({ip}:{port}), "
                    + f"Ephemeral: {ephemeral}, Cluster: {cluster_name}, Weight: {weight}"
                )
            else:
                logger.error(f"Service registration failed: {service_name} ({ip}:{port})")

            return success  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Service registration exception: {service_name}, Error: {e!s}")
            return False

    async def deregister_service(self, service_name: str, ip: str, port: int, cluster_name: str = "DEFAULT") -> bool:
        """Deregister service instance

        Args:
            service_name: Service name
            ip: Service IP address
            port: Service port
            cluster_name: Cluster name

        Returns:
            Whether deregistration is successful
        """
        try:
            success = self.client.remove_naming_instance(
                service_name=service_name,
                ip=ip,
                port=port,
                cluster_name=cluster_name,
                group_name=self.group,
            )

            if success:
                logger.info(f"Service deregistered successfully: {service_name} ({ip}:{port})")
            else:
                logger.error(f"Service deregistration failed: {service_name} ({ip}:{port})")

            return success  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Service deregistration exception: {service_name}, Error: {e!s}")
            return False

    async def discover_service(
        self,
        service_name: str,
        clusters: Optional[str] = None,
        healthy_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Discover service instances

        Args:
            service_name: Service name
            clusters: Cluster names, multiple names separated by commas
            healthy_only: Whether to return only healthy instances

        Returns:
            List of service instances
        """
        try:
            instances = self.client.list_naming_instance(
                service_name=service_name,
                group_name=self.group,
                clusters=clusters or "DEFAULT",
                healthy_only=healthy_only,
            )

            hosts = instances.get("hosts", [])
            logger.debug(f"Service discovery: {service_name}, Instance count: {len(hosts)}")

            return hosts  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Service discovery exception: {service_name}, Error: {e!s}")
            return []

    async def get_service_instance(self, service_name: str, clusters: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a single service instance (load balancing)

        Args:
            service_name: Service name
            clusters: Cluster name

        Returns:
            Service instance information
        """
        try:
            # Use list_naming_instance to get all instances
            instances = self.client.list_naming_instance(
                service_name=service_name,
                group_name=self.group,
                clusters=clusters or "DEFAULT",
                healthy_only=True,  # Only get healthy instances
            )

            # Get instance list
            hosts = instances.get("hosts", [])

            if not hosts:
                logger.warning(f"No available service instances: {service_name}")
                return None

            # Simple load balancing: select the first instance (round-robin or other strategies can also be implemented)
            instance = hosts[0]
            logger.debug(f"Selected service instance: {service_name} ({instance.get('ip')}:{instance.get('port')})")
            return instance  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Get service instance exception: {service_name}, Error: {e!s}", exc_info=True)
            return None

    async def start_heartbeat(
        self,
        service_name: str,
        ip: str,
        port: int,
        interval: int = 5,
        cluster_name: str = "DEFAULT",
    ) -> None:
        """Start heartbeat detection

        Args:
            service_name: Service name
            ip: Service IP address
            port: Service port
            interval: Heartbeat interval (seconds)
            cluster_name: Cluster name
        """
        if self._heartbeat_running:
            logger.warning("Heartbeat detection is already running")
            return

        self._heartbeat_running = True

        async def heartbeat_loop() -> None:
            """Heartbeat loop"""
            while self._heartbeat_running:
                try:
                    # Send heartbeat
                    self.client.send_heartbeat(
                        service_name=service_name,
                        ip=ip,
                        port=port,
                        cluster_name=cluster_name,
                        group_name=self.group,
                    )
                    logger.debug(f"Heartbeat sent successfully: {service_name} ({ip}:{port})")

                except Exception as e:
                    logger.error(f"Heartbeat sending failed: {service_name}, Error: {e!s}")

                # Wait for next heartbeat
                await asyncio.sleep(interval)

        # Create heartbeat task
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info(f"Heartbeat detection started: {service_name} ({ip}:{port}), Interval: {interval} seconds")

    def stop_heartbeat(self) -> None:
        """Stop heartbeat detection"""
        if not self._heartbeat_running:
            logger.warning("Heartbeat detection is not running")
            return

        self._heartbeat_running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        logger.info("Heartbeat detection stopped")

    async def subscribe_service(
        self,
        service_name: str,
        callback: Callable[..., None],
        clusters: Optional[str] = None,
    ) -> None:
        """Subscribe to service changes

        Args:
            service_name: Service name
            callback: Callback function
            clusters: Cluster name
        """
        try:
            # Nacos Python SDK's subscribe method has different parameters, need to check SDK documentation
            # Temporarily commented out, as Nacos Python SDK API may be different
            logger.warning(f"Service subscription feature not yet implemented: {service_name}")
            # self.client.subscribe(
            #     service_name=service_name,
            #     listener_fn=callback,
            # )
            # logger.info(f"Service subscription successful: {service_name}")

        except Exception as e:
            logger.error(f"Service subscription exception: {service_name}, Error: {e!s}")

    async def unsubscribe_service(self, service_name: str, clusters: Optional[str] = None) -> None:
        """Unsubscribe from service

        Args:
            service_name: Service name
            clusters: Cluster name
        """
        try:
            # Nacos Python SDK's unsubscribe method has different parameters, need to check SDK documentation
            # Temporarily commented out, as Nacos Python SDK API may be different
            logger.warning(f"Unsubscribe service feature not yet implemented: {service_name}")
            # self.client.unsubscribe(
            #     service_name=service_name,
            # )
            # logger.info(f"Unsubscribe from service: {service_name}")

        except Exception as e:
            logger.error(f"Unsubscribe service exception: {service_name}, Error: {e!s}")


# Global Nacos manager instance
nacos_manager: Optional[NacosManager] = None


def init_nacos_manager(
    server_addresses: str,
    namespace: str = "public",
    group: str = "DEFAULT_GROUP",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> NacosManager:
    """Initialize global Nacos manager

    Args:
        server_addresses: Nacos server address
        namespace: Namespace
        group: Group name
        username: Username
        password: Password

    Returns:
        Nacos manager instance
    """
    global nacos_manager
    nacos_manager = NacosManager(
        server_addresses=server_addresses,
        namespace=namespace,
        group=group,
        username=username,
        password=password,
    )
    return nacos_manager


def get_nacos_manager() -> NacosManager:
    """Get global Nacos manager

    Returns:
        Nacos manager instance

    Raises:
        RuntimeError: If Nacos manager is not initialized
    """
    if nacos_manager is None:
        raise RuntimeError("Nacos manager not initialized, please call init_nacos_manager() first")
    return nacos_manager
