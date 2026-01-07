"""
WebSocket connection pool manager

Manages WebSocket connection creation, reuse, closing, and monitoring
"""

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, Optional

try:
    import websockets  # type: ignore[import-not-found]
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    import websockets  # type: ignore[import-not-found]

# Use try-except to handle path imports
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


@dataclass
class PooledConnection:
    """Pooled WebSocket connection

    Attributes:
        connection: WebSocket connection object
        created_at: Creation time
        last_used_at: Last used time
        use_count: Usage count
        is_active: Whether active
        service_url: Service URL for connection
    """

    connection: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0
    is_active: bool = True
    service_url: str = ""

    def mark_used(self) -> None:
        """Mark as used"""
        self.last_used_at = datetime.now(timezone.utc)
        self.use_count += 1

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if connection is stale

        Args:
            timeout_seconds: Timeout in seconds, default 300 seconds

        Returns:
            True if connection is stale
        """
        age = (datetime.now(timezone.utc) - self.last_used_at).total_seconds()
        return age > timeout_seconds

    def is_expired(self, max_lifetime_seconds: int = 3600) -> bool:
        """Check if connection is expired

        Args:
            max_lifetime_seconds: Maximum lifetime in seconds, default 3600 seconds

        Returns:
            True if connection is expired
        """
        lifetime = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return lifetime > max_lifetime_seconds


class WebSocketConnectionPool:
    """WebSocket connection pool

    Manages WebSocket connections for multiple services, providing:
    - Connection reuse and caching
    - Automatic expiration cleanup
    - Connection health checks
    - Performance monitoring
    """

    def __init__(
        self,
        max_connections_per_service: int = 10,
        idle_timeout: int = 300,
        max_lifetime: int = 3600,
        health_check_interval: int = 60,
    ):
        """Initialize connection pool

        Args:
            max_connections_per_service: Maximum connections per service
            idle_timeout: Idle timeout (seconds)
            max_lifetime: Maximum connection lifetime (seconds)
            health_check_interval: Health check interval (seconds)
        """
        self.max_connections_per_service = max_connections_per_service
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        self.health_check_interval = health_check_interval

        # Connection storage: service_url -> connection list
        self.pools: Dict[str, list[PooledConnection]] = {}

        # Performance metrics
        self.stats = {
            "total_created": 0,
            "total_closed": 0,
            "total_reused": 0,
            "pool_hits": 0,
            "pool_misses": 0,
        }

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._health_check_task: Optional[asyncio.Task[None]] = None
        self._monitor_task: Optional[asyncio.Task[None]] = None

        logger.info(
            "WebSocket connection pool initialized",
            extra={
                "max_connections": max_connections_per_service,
                "idle_timeout": idle_timeout,
                "max_lifetime": max_lifetime,
            },
        )

    async def get_connection(self, service_url: str) -> Any:
        """Get connection from pool

        Args:
            service_url: Service URL

        Returns:
            Available WebSocket connection

        Raises:
            Exception: Raises exception when connection fails
        """
        # Try to get available connection from pool
        available_conn = self._get_available_connection(service_url)
        if available_conn:
            self.stats["pool_hits"] += 1
            available_conn.mark_used()
            logger.debug(
                f"Get connection from pool: {service_url}",
                extra={"use_count": available_conn.use_count},
            )
            return available_conn.connection

        # No available connection in pool, create new connection
        self.stats["pool_misses"] += 1
        try:
            new_connection = await websockets.connect(
                service_url,
                ping_interval=None,
                close_timeout=10.0,
            )

            # Create pooled connection
            pooled = PooledConnection(
                connection=new_connection,
                service_url=service_url,
            )
            pooled.mark_used()

            # Add to pool
            if service_url not in self.pools:
                self.pools[service_url] = []

            self.pools[service_url].append(pooled)
            self.stats["total_created"] += 1

            logger.info(
                f"Create new WebSocket connection: {service_url}",
                extra={
                    "pool_size": len(self.pools[service_url]),
                    "total_created": self.stats["total_created"],
                },
            )

            return new_connection

        except Exception as e:
            logger.error(
                f"WebSocket connection creation failed: {service_url}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def _get_available_connection(self, service_url: str) -> Optional[PooledConnection]:
        """Get available connection from pool

        Args:
            service_url: Service URL

        Returns:
            Available connection, returns None if not found
        """
        if service_url not in self.pools:
            return None

        pool = self.pools[service_url]

        # Find first active, non-stale, non-expired connection
        for conn in pool:
            if conn.is_active and not conn.is_stale(self.idle_timeout) and not conn.is_expired(self.max_lifetime):
                # Verify connection is still valid
                try:
                    # Use ping to check connection
                    if hasattr(conn.connection, "ping"):
                        task = asyncio.create_task(conn.connection.ping())
                        # Ensure task is tracked to avoid warnings
                        task.add_done_callback(lambda _t: None)
                    return conn
                except Exception:
                    conn.is_active = False

        # Clean up invalid connections
        self.pools[service_url] = [c for c in pool if c.is_active]

        return None

    async def release_connection(self, service_url: str, connection: Any, reusable: bool = True) -> None:
        """Release connection back to pool

        Args:
            service_url: Service URL
            connection: Connection to release
            reusable: Whether reusable
        """
        if not reusable or service_url not in self.pools:
            # Not reusable or not in pool, close connection
            try:
                await connection.close()
                self.stats["total_closed"] += 1
                logger.debug("WebSocket connection closed", extra={"service_url": service_url})
            except Exception as e:
                logger.warning(
                    "Error closing WebSocket connection", extra={"service_url": service_url, "error": str(e)}
                )
            return

        # Mark as reusable
        pool = self.pools[service_url]
        for pooled in pool:
            if pooled.connection == connection:
                pooled.is_active = True
                pooled.mark_used()
                self.stats["total_reused"] += 1
                logger.debug("Connection returned to pool", extra={"service_url": service_url})
                return

    async def cleanup(self) -> None:
        """Clean up expired and invalid connections

        Execute this method periodically to release resources
        """
        logger.info("Starting connection pool cleanup...")

        closed_count = 0

        for service_url, pool in list(self.pools.items()):
            remaining = []

            for pooled in pool:
                # Check if connection should be closed
                if not pooled.is_active or pooled.is_stale(self.idle_timeout) or pooled.is_expired(self.max_lifetime):
                    try:
                        await pooled.connection.close()
                        self.stats["total_closed"] += 1
                        closed_count += 1
                        logger.debug("Close expired connection", extra={"service_url": service_url})
                    except Exception as e:
                        logger.warning("Error closing connection", extra={"service_url": service_url, "error": str(e)})
                else:
                    remaining.append(pooled)

            if remaining:
                self.pools[service_url] = remaining
            else:
                del self.pools[service_url]

        logger.info(
            "Connection pool cleanup completed",
            extra={"closed_count": closed_count, "pools_count": len(self.pools)},
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics

        Returns:
            Statistics dictionary
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
        """Close all connections"""
        logger.info("Closing all WebSocket connections...")

        for pool in self.pools.values():
            for pooled in pool:
                with contextlib.suppress(Exception):
                    await pooled.connection.close()
                    self.stats["total_closed"] += 1

        self.pools.clear()
        logger.info("All connections closed")

    async def start_background_tasks(self) -> None:
        """Start background tasks"""
        logger.info("Starting connection pool background tasks...")

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        logger.info("Stopping connection pool background tasks...")

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
        """Periodic cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop exception", extra={"error": str(e)}, exc_info=True)

    async def _health_check_loop(self) -> None:
        """Periodic health check loop"""
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
                logger.error("Health check exception", extra={"error": str(e)}, exc_info=True)

    async def _monitor_loop(self) -> None:
        """Periodic connection pool status monitoring"""
        while True:
            try:
                await asyncio.sleep(60)

                stats = self.get_stats()
                logger.info(
                    "Connection pool status monitoring",
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
                logger.error("Monitoring exception", extra={"error": str(e)}, exc_info=True)
