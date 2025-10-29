"""
WebSocket 连接池管理器

管理 WebSocket 连接的创建、复用、关闭和监控
"""

import asyncio
import contextlib
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import websockets  # type: ignore[import-not-found]
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    import websockets  # type: ignore[import-not-found]

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


@dataclass
class PooledConnection:
    """池化 WebSocket 连接

    Attributes:
        connection: WebSocket 连接对象
        created_at: 创建时间
        last_used_at: 最后使用时间
        use_count: 使用次数
        is_active: 是否活跃
        service_url: 连接的服务 URL
    """

    connection: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0
    is_active: bool = True
    service_url: str = ""

    def mark_used(self) -> None:
        """标记为已使用"""
        self.last_used_at = datetime.now(timezone.utc)
        self.use_count += 1

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """检查连接是否过时

        Args:
            timeout_seconds: 超时秒数，默认 300 秒

        Returns:
            连接过时返回 True
        """
        age = (datetime.now(timezone.utc) - self.last_used_at).total_seconds()
        return age > timeout_seconds

    def is_expired(self, max_lifetime_seconds: int = 3600) -> bool:
        """检查连接是否过期

        Args:
            max_lifetime_seconds: 最大生命周期秒数，默认 3600 秒

        Returns:
            连接过期返回 True
        """
        lifetime = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return lifetime > max_lifetime_seconds


class WebSocketConnectionPool:
    """WebSocket 连接池

    管理多个服务的 WebSocket 连接，提供：
    - 连接复用和缓存
    - 自动过期清理
    - 连接健康检查
    - 性能监控
    """

    def __init__(
        self,
        max_connections_per_service: int = 10,
        idle_timeout: int = 300,
        max_lifetime: int = 3600,
        health_check_interval: int = 60,
    ):
        """初始化连接池

        Args:
            max_connections_per_service: 每个服务的最大连接数
            idle_timeout: 空闲超时时间（秒）
            max_lifetime: 连接最大生命周期（秒）
            health_check_interval: 健康检查间隔（秒）
        """
        self.max_connections_per_service = max_connections_per_service
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        self.health_check_interval = health_check_interval

        # 连接存储: service_url -> 连接列表
        self.pools: Dict[str, list[PooledConnection]] = {}

        # 性能指标
        self.stats = {
            "total_created": 0,
            "total_closed": 0,
            "total_reused": 0,
            "pool_hits": 0,
            "pool_misses": 0,
        }

        # 后台任务
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._health_check_task: Optional[asyncio.Task[None]] = None
        self._monitor_task: Optional[asyncio.Task[None]] = None

        logger.info(
            "WebSocket 连接池已初始化",
            extra={
                "max_connections": max_connections_per_service,
                "idle_timeout": idle_timeout,
                "max_lifetime": max_lifetime,
            },
        )

    async def get_connection(self, service_url: str) -> Any:
        """从池中获取连接

        Args:
            service_url: 服务 URL

        Returns:
            可用的 WebSocket 连接

        Raises:
            Exception: 连接失败时抛出异常
        """
        # 尝试从池中获取可用连接
        available_conn = self._get_available_connection(service_url)
        if available_conn:
            self.stats["pool_hits"] += 1
            available_conn.mark_used()
            logger.debug(
                f"从连接池中获取连接: {service_url}",
                extra={"use_count": available_conn.use_count},
            )
            return available_conn.connection

        # 池中没有可用连接，创建新连接
        self.stats["pool_misses"] += 1
        try:
            new_connection = await websockets.connect(
                service_url,
                ping_interval=None,
                close_timeout=10.0,
            )

            # 创建池化连接
            pooled = PooledConnection(
                connection=new_connection,
                service_url=service_url,
            )
            pooled.mark_used()

            # 添加到池
            if service_url not in self.pools:
                self.pools[service_url] = []

            self.pools[service_url].append(pooled)
            self.stats["total_created"] += 1

            logger.info(
                f"创建新的 WebSocket 连接: {service_url}",
                extra={
                    "pool_size": len(self.pools[service_url]),
                    "total_created": self.stats["total_created"],
                },
            )

            return new_connection

        except Exception as e:
            logger.error(
                f"WebSocket 连接创建失败: {service_url}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def _get_available_connection(self, service_url: str) -> Optional[PooledConnection]:
        """从池中获取可用连接

        Args:
            service_url: 服务 URL

        Returns:
            可用连接，未找到返回 None
        """
        if service_url not in self.pools:
            return None

        pool = self.pools[service_url]

        # 查找第一个活跃、未过时、未过期的连接
        for conn in pool:
            if conn.is_active and not conn.is_stale(self.idle_timeout) and not conn.is_expired(self.max_lifetime):
                # 验证连接是否仍然有效
                try:
                    # 使用 ping 检查连接
                    if hasattr(conn.connection, "ping"):
                        task = asyncio.create_task(conn.connection.ping())
                        # 确保任务被追踪，避免警告
                        task.add_done_callback(lambda _t: None)
                    return conn
                except Exception:
                    conn.is_active = False

        # 清理失效连接
        self.pools[service_url] = [c for c in pool if c.is_active]

        return None

    async def release_connection(self, service_url: str, connection: Any, reusable: bool = True) -> None:
        """释放连接回池

        Args:
            service_url: 服务 URL
            connection: 要释放的连接
            reusable: 是否可复用
        """
        if not reusable or service_url not in self.pools:
            # 不可复用或未在池中，关闭连接
            try:
                await connection.close()
                self.stats["total_closed"] += 1
                logger.debug(f"WebSocket 连接已关闭: {service_url}")
            except Exception as e:
                logger.warning(f"关闭 WebSocket 连接时出错: {e!s}")
            return

        # 标记为可复用
        pool = self.pools[service_url]
        for pooled in pool:
            if pooled.connection == connection:
                pooled.is_active = True
                pooled.mark_used()
                self.stats["total_reused"] += 1
                logger.debug(f"连接已返回到池: {service_url}")
                return

    async def cleanup(self) -> None:
        """清理过期和失效连接

        定期执行此方法以释放资源
        """
        logger.info("开始清理连接池...")

        closed_count = 0

        for service_url, pool in list(self.pools.items()):
            remaining = []

            for pooled in pool:
                # 检查连接是否应该关闭
                if not pooled.is_active or pooled.is_stale(self.idle_timeout) or pooled.is_expired(self.max_lifetime):
                    try:
                        await pooled.connection.close()
                        self.stats["total_closed"] += 1
                        closed_count += 1
                        logger.debug(f"关闭过期连接: {service_url}")
                    except Exception as e:
                        logger.warning(f"关闭连接时出错: {e!s}")
                else:
                    remaining.append(pooled)

            if remaining:
                self.pools[service_url] = remaining
            else:
                del self.pools[service_url]

        logger.info(
            f"连接池清理完成，关闭 {closed_count} 个连接",
            extra={"pools_count": len(self.pools)},
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息

        Returns:
            统计信息字典
        """
        total_connections = sum(len(pool) for pool in self.pools.values())
        active_connections = sum(sum(1 for c in pool if c.is_active) for pool in self.pools.values())

        hit_rate = (
            self.stats["pool_hits"] / (self.stats["pool_hits"] + self.stats["pool_misses"])
            if (self.stats["pool_hits"] + self.stats["pool_misses"]) > 0
            else 0
        )

        return {
            "total_connections": total_connections,
            "active_connections": active_connections,
            "pools": {
                service_url: {
                    "size": len(pool),
                    "active": sum(1 for c in pool if c.is_active),
                }
                for service_url, pool in self.pools.items()
            },
            "stats": self.stats.copy(),
            "hit_rate": hit_rate,
        }

    async def close_all(self) -> None:
        """关闭所有连接"""
        logger.info("关闭所有 WebSocket 连接...")

        for pool in self.pools.values():
            for pooled in pool:
                with contextlib.suppress(Exception):
                    await pooled.connection.close()
                    self.stats["total_closed"] += 1

        self.pools.clear()
        logger.info("所有连接已关闭")

    async def start_background_tasks(self) -> None:
        """启动后台任务"""
        logger.info("启动连接池后台任务...")

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_background_tasks(self) -> None:
        """停止后台任务"""
        logger.info("停止连接池后台任务...")

        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()

        try:
            if self._cleanup_task:
                await self._cleanup_task
            if self._health_check_task:
                await self._health_check_task
            if self._monitor_task:
                await self._monitor_task
        except asyncio.CancelledError:
            ***REMOVED***

    async def _cleanup_loop(self) -> None:
        """定期清理连接"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理循环异常: {e!s}", exc_info=True)

    async def _health_check_loop(self) -> None:
        """定期健康检查"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval // 2)

                for _service_url, pool in list(self.pools.items()):
                    for pooled in pool:
                        if pooled.is_active:
                            try:
                                if hasattr(pooled.connection, "ping"):
                                    await pooled.connection.ping()
                            except Exception:
                                pooled.is_active = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {e!s}", exc_info=True)

    async def _monitor_loop(self) -> None:
        """定期监控连接池状态"""
        while True:
            try:
                await asyncio.sleep(60)

                stats = self.get_stats()
                logger.info(
                    "连接池状态监控",
                    extra={
                        "total": stats["total_connections"],
                        "active": stats["active_connections"],
                        "hit_rate": f"{stats['hit_rate']:.2%}",
                        "created": stats["stats"]["total_created"],
                        "closed": stats["stats"]["total_closed"],
                    },
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控异常: {e!s}", exc_info=True)
