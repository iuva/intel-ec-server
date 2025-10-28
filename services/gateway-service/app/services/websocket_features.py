"""
WebSocket 高级特性管理器

提供心跳检测、速率限制、消息压缩等高级功能
"""

import asyncio
import base64
import gzip
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    )
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


@dataclass
class HeartbeatStats:
    """心跳统计信息"""

    total_heartbeats: int = 0
    successful_heartbeats: int = 0
    failed_heartbeats: int = 0
    last_heartbeat_time: Optional[datetime] = None
    average_response_time_ms: float = 0.0


class HeartbeatManager:
    """WebSocket 心跳检测管理器

    定期发送 ping 消息以验证连接活跃性，快速检测死连接。
    """

    def __init__(self, interval: float = 30.0, timeout: float = 10.0):
        """初始化心跳管理器

        Args:
            interval: 心跳间隔（秒）
            timeout: 心跳响应超时（秒）
        """
        self.interval = interval
        self.timeout = timeout

        # 心跳任务管理
        self._heartbeat_tasks: Dict[str, asyncio.Task[None]] = {}

        # 心跳统计
        self._stats: Dict[str, HeartbeatStats] = {}

        logger.info(
            "心跳管理器初始化",
            extra={
                "interval": interval,
                "timeout": timeout,
            },
        )

    def register_connection(
        self, connection_id: str, send_heartbeat: Callable[[], Any]
    ) -> None:
        """注册连接心跳

        Args:
            connection_id: 连接ID
            send_heartbeat: 发送心跳的可调用对象
        """
        if connection_id in self._heartbeat_tasks:
            logger.warning(f"连接 {connection_id} 的心跳已存在，将被覆盖")
            self._heartbeat_tasks[connection_id].cancel()

        # 创建心跳任务
        task = asyncio.create_task(self._heartbeat_loop(connection_id, send_heartbeat))

        self._heartbeat_tasks[connection_id] = task
        self._stats[connection_id] = HeartbeatStats()

        logger.debug(f"连接 {connection_id} 的心跳已注册")

    def unregister_connection(self, connection_id: str) -> None:
        """注销连接心跳

        Args:
            connection_id: 连接ID
        """
        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
            del self._heartbeat_tasks[connection_id]

            logger.debug(f"连接 {connection_id} 的心跳已注销")

    async def _heartbeat_loop(
        self, connection_id: str, send_heartbeat: Callable[[], Any]
    ) -> None:
        """心跳循环"""
        while True:
            try:
                await asyncio.sleep(self.interval)

                # 发送心跳
                start_time = time.time()
                await send_heartbeat()
                response_time_ms = (time.time() - start_time) * 1000

                # 更新统计
                stats = self._stats[connection_id]
                stats.total_heartbeats += 1
                stats.successful_heartbeats += 1
                stats.last_heartbeat_time = datetime.now(timezone.utc)
                stats.average_response_time_ms = (
                    stats.average_response_time_ms * 0.9 + response_time_ms * 0.1
                )

                logger.debug(
                    f"心跳发送成功: {connection_id}",
                    extra={"response_time_ms": response_time_ms},
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                # 更新失败统计
                stats = self._stats[connection_id]
                stats.total_heartbeats += 1
                stats.failed_heartbeats += 1

                logger.warning(f"心跳发送失败: {connection_id} - {e!s}")

    def get_stats(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接的心跳统计

        Args:
            connection_id: 连接ID

        Returns:
            心跳统计信息
        """
        if connection_id not in self._stats:
            return None

        stats = self._stats[connection_id]

        return {
            "total_heartbeats": stats.total_heartbeats,
            "successful_heartbeats": stats.successful_heartbeats,
            "failed_heartbeats": stats.failed_heartbeats,
            "success_rate": (
                stats.successful_heartbeats / stats.total_heartbeats
                if stats.total_heartbeats > 0
                else 0
            ),
            "average_response_time_ms": round(stats.average_response_time_ms, 2),
            "last_heartbeat_time": (
                stats.last_heartbeat_time.isoformat()
                if stats.last_heartbeat_time
                else None
            ),
        }


class RateLimiter:
    """WebSocket 速率限制管理器

    限制消息发送频率和大小，防止洪泛攻击和 DDoS。
    """

    def __init__(
        self,
        max_messages: int = 100,
        window_size: float = 60.0,
        max_size_bytes: int = 1024 * 1024,
    ):
        """初始化速率限制器

        Args:
            max_messages: 时间窗口内最多消息数
            window_size: 时间窗口大小（秒）
            max_size_bytes: 单条消息最大大小（字节）
        """
        self.max_messages = max_messages
        self.window_size = window_size
        self.max_size_bytes = max_size_bytes

        # 连接消息计数
        self._message_times: Dict[str, list[float]] = {}

        # 连接总字节数
        self._connection_bytes: Dict[str, int] = {}

        logger.info(
            "速率限制器初始化",
            extra={
                "max_messages": max_messages,
                "window_size": window_size,
                "max_size_bytes": max_size_bytes,
            },
        )

    async def check_rate_limit(
        self, connection_id: str, message_size: int
    ) -> Tuple[bool, Optional[str]]:
        """检查速率限制

        Args:
            connection_id: 连接ID
            message_size: 消息大小（字节）

        Returns:
            (是否通过限制, 错误消息)
        """
        current_time = time.time()

        # 检查单条消息大小
        if message_size > self.max_size_bytes:
            return False, f"消息大小超过限制: {message_size} > {self.max_size_bytes}"

        # 初始化连接记录
        if connection_id not in self._message_times:
            self._message_times[connection_id] = []
            self._connection_bytes[connection_id] = 0

        # 清理过期的消息时间戳
        message_times = self._message_times[connection_id]
        cutoff_time = current_time - self.window_size
        self._message_times[connection_id] = [
            t for t in message_times if t > cutoff_time
        ]

        # 检查消息频率
        if len(self._message_times[connection_id]) >= self.max_messages:
            return False, f"消息频率超过限制: {self.max_messages}/{self.window_size}s"

        # 记录消息
        self._message_times[connection_id].append(current_time)
        self._connection_bytes[connection_id] += message_size

        return True, None

    def cleanup_connection(self, connection_id: str) -> None:
        """清理连接记录

        Args:
            connection_id: 连接ID
        """
        if connection_id in self._message_times:
            del self._message_times[connection_id]
        if connection_id in self._connection_bytes:
            del self._connection_bytes[connection_id]

    def get_stats(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接的速率限制统计

        Args:
            connection_id: 连接ID

        Returns:
            速率限制统计信息
        """
        if connection_id not in self._message_times:
            return None

        current_time = time.time()
        cutoff_time = current_time - self.window_size

        # 清理过期时间戳
        message_times = self._message_times[connection_id]
        active_times = [t for t in message_times if t > cutoff_time]

        return {
            "message_count": len(active_times),
            "max_messages": self.max_messages,
            "percentage": len(active_times) / self.max_messages * 100,
            "total_bytes": self._connection_bytes[connection_id],
            "max_size_bytes": self.max_size_bytes,
        }


class MessageCompressor:
    """WebSocket 消息压缩管理器

    使用 Gzip 算法压缩消息，显著减少带宽占用。
    """

    def __init__(self, compression_threshold: int = 1024):
        """初始化消息压缩器

        Args:
            compression_threshold: 压缩阈值（字节），小于此值不压缩
        """
        self.compression_threshold = compression_threshold

        # 压缩统计
        self._stats: Dict[str, Any] = {
            "total_messages": 0,
            "compressed_count": 0,
            "uncompressed_count": 0,
            "bytes_original": 0,
            "bytes_compressed": 0,
        }

        logger.info(
            "消息压缩器初始化",
            extra={"compression_threshold": compression_threshold},
        )

    async def compress_message(
        self, message: str
    ) -> Tuple[bool, str]:
        """压缩消息

        Args:
            message: 要压缩的消息

        Returns:
            (是否被压缩, 压缩后的消息)
        """
        message_bytes = message.encode("utf-8")
        original_size = len(message_bytes)

        # 更新统计
        self._stats["total_messages"] += 1
        self._stats["bytes_original"] += original_size

        # 检查是否需要压缩
        if original_size < self.compression_threshold:
            self._stats["uncompressed_count"] += 1
            return False, message

        # 压缩消息
        compressed_bytes = gzip.compress(message_bytes)
        compressed_size = len(compressed_bytes)

        # 检查压缩是否有效
        if compressed_size >= original_size:
            self._stats["uncompressed_count"] += 1
            return False, message

        # 编码为 base64（便于通过文本通道传输）
        compressed_b64 = base64.b64encode(compressed_bytes).decode("utf-8")

        # 创建压缩消息格式
        compressed_message = json.dumps(
            {
                "type": "compressed",
                "data": compressed_b64,
                "original_size": original_size,
                "compressed_size": compressed_size,
            }
        )

        # 更新统计
        self._stats["compressed_count"] += 1
        self._stats["bytes_compressed"] += compressed_size

        logger.debug(
            "消息已压缩",
            extra={
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(compressed_size / original_size, 2),
            },
        )

        return True, compressed_message

    async def decompress_message(
        self, message: str
    ) -> Optional[str]:
        """解压消息

        Args:
            message: 压缩后的消息

        Returns:
            解压后的消息，如果失败返回 None
        """
        try:
            # 尝试解析为压缩消息
            data = json.loads(message)

            if data.get("type") != "compressed":
                return message

            # 解码 base64
            compressed_bytes = base64.b64decode(data["data"])

            # 解压
            decompressed_bytes = gzip.decompress(compressed_bytes)

            return decompressed_bytes.decode("utf-8")

        except (json.JSONDecodeError, ValueError, Exception):
            # 不是压缩消息或解压失败
            return message

    def get_stats(self) -> Dict[str, Any]:
        """获取压缩统计

        Returns:
            压缩统计信息
        """
        total = self._stats["total_messages"]
        if total == 0:
            return self._stats.copy()

        stats = self._stats.copy()
        stats["compression_rate"] = round(
            self._stats["compressed_count"] / total * 100, 2
        )

        if self._stats["bytes_original"] > 0:
            stats["compression_ratio"] = round(
                self._stats["bytes_compressed"] / self._stats["bytes_original"], 2
            )
            stats["bytes_saved"] = (
                self._stats["bytes_original"] - self._stats["bytes_compressed"]
            )

        return stats


class WebSocketFeaturesManager:
    """WebSocket 功能管理器

    聚合所有 WebSocket 高级特性：心跳、限流、压缩等。
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 10.0,
        max_messages: int = 100,
        window_size: float = 60.0,
        max_message_size: int = 1024 * 1024,
        compression_threshold: int = 1024,
    ):
        """初始化功能管理器

        Args:
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_timeout: 心跳超时（秒）
            max_messages: 时间窗口内最大消息数
            window_size: 限速时间窗口（秒）
            max_message_size: 最大消息大小（字节）
            compression_threshold: 压缩阈值（字节）
        """
        self.heartbeat_manager = HeartbeatManager(heartbeat_interval, heartbeat_timeout)
        self.rate_limiter = RateLimiter(max_messages, window_size, max_message_size)
        self.compressor = MessageCompressor(compression_threshold)

        logger.info("WebSocket 功能管理器初始化完成")

    def get_stats(self) -> Dict[str, Any]:
        """获取所有功能的统计信息

        Returns:
            统计信息字典
        """
        return {
            "heartbeat": {
                "active_connections": len(self.heartbeat_manager._heartbeat_tasks),
            },
            "rate_limiter": {
                "tracked_connections": len(self.rate_limiter._message_times),
            },
            "compressor": self.compressor.get_stats(),
        }
