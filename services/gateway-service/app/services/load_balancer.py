"""
负载均衡器模块

基于 Nacos 服务发现实现负载均衡
"""

import os
import random
import sys
from typing import Any, Dict, List, Optional

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import ServiceUnavailableError
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import ServiceUnavailableError
    from shared.common.loguru_config import get_logger
    from shared.config.nacos_config import NacosManager


logger = get_logger(__name__)


class LoadBalancer:
    """负载均衡器类

    基于 Nacos 服务发现，实现加权随机负载均衡算法
    """

    def __init__(self, nacos_manager: NacosManager):
        """初始化负载均衡器

        Args:
            nacos_manager: Nacos 管理器实例
        """
        self.nacos_manager = nacos_manager
        # 服务实例缓存
        self.service_instances_cache: Dict[str, List[Dict[str, Any]]] = {}
        # 缓存过期时间（秒）
        self.cache_ttl = 30

    async def get_service_instance(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务实例

        使用加权随机算法选择服务实例

        Args:
            service_name: 服务名称

        Returns:
            服务实例信息，包含 ip、port、weight 等

        Raises:
            ServiceUnavailableError: 没有可用的服务实例
        """
        try:
            # 获取服务实例列表
            instances = await self._get_instances(service_name)

            if not instances:
                logger.warning(f"没有找到服务实例: {service_name}")
                raise ServiceUnavailableError(
                    message="没有可用的服务实例",
                    code=503,
                    details={"service_name": service_name},
                )

            # 过滤健康的实例
            healthy_instances = [inst for inst in instances if inst.get("healthy", True)]

            if not healthy_instances:
                logger.warning(f"没有健康的服务实例: {service_name}")
                raise ServiceUnavailableError(
                    message="没有健康的服务实例",
                    code=503,
                    details={"service_name": service_name},
                )

            # 使用加权随机算法选择实例
            selected_instance = self._select_instance_weighted(healthy_instances)

            logger.info(
                f"选择服务实例: {service_name}",
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
                f"获取服务实例异常: {service_name}",
                extra={"service_name": service_name, "error": str(e)},
                exc_info=True,
            )
            raise ServiceUnavailableError(message=str(e), code=503, details={"service_name": service_name})

    async def _get_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """获取服务实例列表

        优先从缓存获取，缓存未命中则从 Nacos 获取

        Args:
            service_name: 服务名称

        Returns:
            服务实例列表
        """
        # 检查缓存
        if service_name in self.service_instances_cache:
            logger.debug(f"从缓存获取服务实例: {service_name}")
            return self.service_instances_cache[service_name]

        # 从 Nacos 获取
        try:
            instances = await self.nacos_manager.discover_service(service_name)

            if instances:
                # 更新缓存
                self.service_instances_cache[service_name] = instances
                logger.info(
                    f"从 Nacos 获取服务实例: {service_name}",
                    extra={
                        "service_name": service_name,
                        "instance_count": len(instances),
                    },
                )

            return instances

        except Exception as e:
            logger.error(
                f"从 Nacos 获取服务实例失败: {service_name}",
                extra={"service_name": service_name, "error": str(e)},
            )
            return []

    def _select_instance_weighted(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """加权随机选择实例

        根据实例的权重进行随机选择，权重越高被选中的概率越大

        Args:
            instances: 服务实例列表

        Returns:
            选中的实例
        """
        if not instances:
            raise ValueError("实例列表不能为空")

        # 如果只有一个实例，直接返回
        if len(instances) == 1:
            return instances[0]

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

    def clear_cache(self, service_name: Optional[str] = None):
        """清除缓存

        Args:
            service_name: 服务名称，如果为 None 则清除所有缓存
        """
        if service_name:
            if service_name in self.service_instances_cache:
                del self.service_instances_cache[service_name]
                logger.info(f"清除服务实例缓存: {service_name}")
        else:
            self.service_instances_cache.clear()
            logger.info("清除所有服务实例缓存")

    async def get_all_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """获取所有服务实例

        Args:
            service_name: 服务名称

        Returns:
            服务实例列表
        """
        return await self._get_instances(service_name)

    async def check_instance_health(self, service_name: str, ip: str, port: int) -> bool:
        """检查实例健康状态

        Args:
            service_name: 服务名称
            ip: 实例 IP
            port: 实例端口

        Returns:
            实例是否健康
        """
        try:
            instances = await self._get_instances(service_name)

            for instance in instances:
                if instance.get("ip") == ip and instance.get("port") == port:
                    return instance.get("healthy", False)

            return False

        except Exception as e:
            logger.error(
                f"检查实例健康状态异常: {service_name}",
                extra={
                    "service_name": service_name,
                    "ip": ip,
                    "port": port,
                    "error": str(e),
                },
            )
            return False


# 全局负载均衡器实例
_load_balancer_instance: Optional[LoadBalancer] = None


def get_load_balancer(nacos_manager: NacosManager) -> LoadBalancer:
    """获取负载均衡器实例（单例模式）

    Args:
        nacos_manager: Nacos 管理器实例

    Returns:
        负载均衡器实例
    """
    global _load_balancer_instance

    if _load_balancer_instance is None:
        _load_balancer_instance = LoadBalancer(nacos_manager)

    return _load_balancer_instance
