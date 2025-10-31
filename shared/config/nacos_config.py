"""
Nacos服务发现配置模块

提供Nacos服务注册、发现和心跳检测功能
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

import nacos

logger = logging.getLogger(__name__)


class NacosManager:
    """Nacos服务发现管理器

    提供服务注册、发现、心跳检测等功能
    """

    def __init__(
        self,
        server_addresses: str,
        namespace: str = "public",
        group: str = "DEFAULT_GROUP",
        username: Optional[str] = None,
        ***REMOVED***word: Optional[str] = None,
    ) -> None:
        """初始化Nacos管理器

        Args:
            server_addresses: Nacos服务器地址，格式：host:port
            namespace: 命名空间ID
            group: 分组名称
            username: 用户名（可选）
            ***REMOVED***word: 密码（可选）
        """
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.group = group
        self.username = username
        self.***REMOVED***word = ***REMOVED***word

        # 初始化Nacos客户端
        self.client = nacos.NacosClient(
            server_addresses=server_addresses,
            namespace=namespace,
            username=username,
            ***REMOVED***word=***REMOVED***word,
        )

        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_running = False

        logger.info(f"Nacos管理器初始化完成: {server_addresses}")

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
        """注册服务实例

        Args:
            service_name: 服务名称
            ip: 服务IP地址
            port: 服务端口
            ephemeral: 是否为临时实例（临时实例需要心跳）
            metadata: 元数据
            cluster_name: 集群名称
            weight: 权重
            enabled: 是否启用（注意：Nacos Python SDK 不支持此参数）

        Returns:
            是否注册成功
        """
        try:
            # 注意：Nacos Python SDK 的 add_naming_instance 不支持 enabled 参数
            # 如果需要禁用实例，应该使用 remove_naming_instance 注销服务
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
                    f"服务注册成功: {service_name} ({ip}:{port}), "
                    + f"临时实例: {ephemeral}, 集群: {cluster_name}, 权重: {weight}"
                )
            else:
                logger.error(f"服务注册失败: {service_name} ({ip}:{port})")

            return success  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"服务注册异常: {service_name}, 错误: {e!s}")
            return False

    async def deregister_service(self, service_name: str, ip: str, port: int, cluster_name: str = "DEFAULT") -> bool:
        """注销服务实例

        Args:
            service_name: 服务名称
            ip: 服务IP地址
            port: 服务端口
            cluster_name: 集群名称

        Returns:
            是否注销成功
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
                logger.info(f"服务注销成功: {service_name} ({ip}:{port})")
            else:
                logger.error(f"服务注销失败: {service_name} ({ip}:{port})")

            return success  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"服务注销异常: {service_name}, 错误: {e!s}")
            return False

    async def discover_service(
        self,
        service_name: str,
        clusters: Optional[str] = None,
        healthy_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """发现服务实例

        Args:
            service_name: 服务名称
            clusters: 集群名称，多个用逗号分隔
            healthy_only: 是否只返回健康实例

        Returns:
            服务实例列表
        """
        try:
            instances = self.client.list_naming_instance(
                service_name=service_name,
                group_name=self.group,
                clusters=clusters or "DEFAULT",
                healthy_only=healthy_only,
            )

            hosts = instances.get("hosts", [])
            logger.debug(f"服务发现: {service_name}, 实例数: {len(hosts)}")

            return hosts  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"服务发现异常: {service_name}, 错误: {e!s}")
            return []

    async def get_service_instance(self, service_name: str, clusters: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取单个服务实例（负载均衡）

        Args:
            service_name: 服务名称
            clusters: 集群名称

        Returns:
            服务实例信息
        """
        try:
            # 使用 list_naming_instance 获取所有实例
            instances = self.client.list_naming_instance(
                service_name=service_name,
                group_name=self.group,
                clusters=clusters or "DEFAULT",
                healthy_only=True,  # 只获取健康实例
            )

            # 获取实例列表
            hosts = instances.get("hosts", [])
            
            if not hosts:
                logger.warning(f"没有可用的服务实例: {service_name}")
                return None

            # 简单负载均衡：选择第一个实例（也可以实现轮询等策略）
            instance = hosts[0]
            logger.debug(
                f"选择服务实例: {service_name} ({instance.get('ip')}:{instance.get('port')})"
            )
            return instance  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"获取服务实例异常: {service_name}, 错误: {e!s}", exc_info=True)
            return None

    async def start_heartbeat(
        self,
        service_name: str,
        ip: str,
        port: int,
        interval: int = 5,
        cluster_name: str = "DEFAULT",
    ) -> None:
        """启动心跳检测

        Args:
            service_name: 服务名称
            ip: 服务IP地址
            port: 服务端口
            interval: 心跳间隔（秒）
            cluster_name: 集群名称
        """
        if self._heartbeat_running:
            logger.warning("心跳检测已在运行")
            return

        self._heartbeat_running = True

        async def heartbeat_loop() -> None:
            """心跳循环"""
            while self._heartbeat_running:
                try:
                    # 发送心跳
                    self.client.send_heartbeat(
                        service_name=service_name,
                        ip=ip,
                        port=port,
                        cluster_name=cluster_name,
                        group_name=self.group,
                    )
                    logger.debug(f"心跳发送成功: {service_name} ({ip}:{port})")

                except Exception as e:
                    logger.error(f"心跳发送失败: {service_name}, 错误: {e!s}")

                # 等待下一次心跳
                await asyncio.sleep(interval)

        # 创建心跳任务
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info(f"心跳检测已启动: {service_name} ({ip}:{port}), 间隔: {interval}秒")

    def stop_heartbeat(self) -> None:
        """停止心跳检测"""
        if not self._heartbeat_running:
            logger.warning("心跳检测未运行")
            return

        self._heartbeat_running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        logger.info("心跳检测已停止")

    async def subscribe_service(
        self,
        service_name: str,
        callback: Callable[..., None],
        clusters: Optional[str] = None,
    ) -> None:
        """订阅服务变化

        Args:
            service_name: 服务名称
            callback: 回调函数
            clusters: 集群名称
        """
        try:
            # Nacos Python SDK的subscribe方法参数不同，需要检查SDK文档
            # 这里暂时注释掉，因为Nacos Python SDK的API可能不同
            logger.warning(f"服务订阅功能暂未实现: {service_name}")
            # self.client.subscribe(
            #     service_name=service_name,
            #     listener_fn=callback,
            # )
            # logger.info(f"服务订阅成功: {service_name}")

        except Exception as e:
            logger.error(f"服务订阅异常: {service_name}, 错误: {e!s}")

    async def unsubscribe_service(self, service_name: str, clusters: Optional[str] = None) -> None:
        """取消订阅服务

        Args:
            service_name: 服务名称
            clusters: 集群名称
        """
        try:
            # Nacos Python SDK的unsubscribe方法参数不同，需要检查SDK文档
            # 这里暂时注释掉，因为Nacos Python SDK的API可能不同
            logger.warning(f"取消服务订阅功能暂未实现: {service_name}")
            # self.client.unsubscribe(
            #     service_name=service_name,
            # )
            # logger.info(f"取消服务订阅: {service_name}")

        except Exception as e:
            logger.error(f"取消服务订阅异常: {service_name}, 错误: {e!s}")


# 全局Nacos管理器实例
nacos_manager: Optional[NacosManager] = None


def init_nacos_manager(
    server_addresses: str,
    namespace: str = "public",
    group: str = "DEFAULT_GROUP",
    username: Optional[str] = None,
    ***REMOVED***word: Optional[str] = None,
) -> NacosManager:
    """初始化全局Nacos管理器

    Args:
        server_addresses: Nacos服务器地址
        namespace: 命名空间
        group: 分组名称
        username: 用户名
        ***REMOVED***word: 密码

    Returns:
        Nacos管理器实例
    """
    global nacos_manager
    nacos_manager = NacosManager(
        server_addresses=server_addresses,
        namespace=namespace,
        group=group,
        username=username,
        ***REMOVED***word=***REMOVED***word,
    )
    return nacos_manager


def get_nacos_manager() -> NacosManager:
    """获取全局Nacos管理器

    Returns:
        Nacos管理器实例

    Raises:
        RuntimeError: 如果Nacos管理器未初始化
    """
    if nacos_manager is None:
        raise RuntimeError("Nacos管理器未初始化，请先调用init_nacos_manager()")
    return nacos_manager
