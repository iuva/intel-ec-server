"""
WebSocket advanced features manager

Provides advanced features such as heartbeat detection, rate limiting, and message compression
"""

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import json
import os
import sys
import time
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


@dataclass
class HeartbeatStats:
    """Heartbeat statistics"""

    total_heartbeats: int = 0
    successful_heartbeats: int = 0
    failed_heartbeats: int = 0
    last_heartbeat_time: Optional[datetime] = None
    average_response_time_ms: float = 0.0


class HeartbeatManager:
    """WebSocket heartbeat detection manager

    Periodically sends ping messages to verify connection activity and quickly detect dead connections.
    """

    def __init__(self, interval: float = 30.0, timeout: float = 10.0):
        """Initialize heartbeat manager

        Args:
            interval: Heartbeat interval (seconds)
            timeout: Heartbeat response timeout (seconds)
        """
        self.interval = interval
        self.timeout = timeout

        # Heartbeat task management
        self._heartbeat_tasks: Dict[str, asyncio.Task[None]] = {}

        # Heartbeat statistics
        self._stats: Dict[str, HeartbeatStats] = {}

        logger.info(
            "Heartbeat manager initialized",
            extra={
                "interval": interval,
                "timeout": timeout,
            },
        )

    def register_connection(self, connection_id: str, send_heartbeat: Callable[[], Any]) -> None:
        """Register connection heartbeat

        Args:
            connection_id: Connection ID
            send_heartbeat: Callable object for sending heartbeat
        """
        if connection_id in self._heartbeat_tasks:
            logger.warning(
                "Connection heartbeat already exists, will be overwritten", extra={"connection_id": connection_id}
            )
            self._heartbeat_tasks[connection_id].cancel()

        # Create heartbeat task
        task = asyncio.create_task(self._heartbeat_loop(connection_id, send_heartbeat))

        self._heartbeat_tasks[connection_id] = task
        self._stats[connection_id] = HeartbeatStats()

        logger.debug("Connection heartbeat registered", extra={"connection_id": connection_id})

    def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection heartbeat

        Args:
            connection_id: Connection ID
        """
        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
            del self._heartbeat_tasks[connection_id]

            logger.debug("Connection heartbeat unregistered", extra={"connection_id": connection_id})

    async def _heartbeat_loop(self, connection_id: str, send_heartbeat: Callable[[], Any]) -> None:
        """Heartbeat loop"""
        while True:
            try:
                await asyncio.sleep(self.interval)

                # Send heartbeat
                start_time = time.time()
                await send_heartbeat()
                response_time_ms = (time.time() - start_time) * 1000

                # Update statistics
                stats = self._stats[connection_id]
                stats.total_heartbeats += 1
                stats.successful_heartbeats += 1
                stats.last_heartbeat_time = datetime.now(timezone.utc)
                stats.average_response_time_ms = stats.average_response_time_ms * 0.9 + response_time_ms * 0.1

                logger.debug(
                    "Heartbeat sent successfully",
                    extra={"connection_id": connection_id, "response_time_ms": response_time_ms},
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Update failure statistics
                stats = self._stats[connection_id]
                stats.total_heartbeats += 1
                stats.failed_heartbeats += 1

                logger.warning("Heartbeat send failed", extra={"connection_id": connection_id, "error": str(e)})

    def get_stats(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection heartbeat statistics

        Args:
            connection_id: Connection ID

        Returns:
            Heartbeat statistics
        """
        if connection_id not in self._stats:
            return None

        stats = self._stats[connection_id]

        return {
            "total_heartbeats": stats.total_heartbeats,
            "successful_heartbeats": stats.successful_heartbeats,
            "failed_heartbeats": stats.failed_heartbeats,
            "success_rate": (stats.successful_heartbeats / stats.total_heartbeats if stats.total_heartbeats > 0 else 0),
            "average_response_time_ms": round(stats.average_response_time_ms, 2),
            "last_heartbeat_time": (stats.last_heartbeat_time.isoformat() if stats.last_heartbeat_time else None),
        }


class RateLimiter:
    """WebSocket rate limiting manager

    Limits message sending frequency and size to prevent flooding attacks and DDoS.
    """

    def __init__(
        self,
        max_messages: int = 100,
        window_size: float = 60.0,
        max_size_bytes: int = 1024 * 1024,
    ):
        """Initialize rate limiter

        Args:
            max_messages: Maximum number of messages in time window
            window_size: Time window size (seconds)
            max_size_bytes: Maximum size of single message (bytes)
        """
        self.max_messages = max_messages
        self.window_size = window_size
        self.max_size_bytes = max_size_bytes

        # Connection message count
        self._message_times: Dict[str, list[float]] = {}

        # Connection total bytes
        self._connection_bytes: Dict[str, int] = {}

        logger.info(
            "Rate limiter initialized",
            extra={
                "max_messages": max_messages,
                "window_size": window_size,
                "max_size_bytes": max_size_bytes,
            },
        )

    async def check_rate_limit(self, connection_id: str, message_size: int) -> Tuple[bool, Optional[str]]:
        """Check rate limit

        Args:
            connection_id: Connection ID
            message_size: Message size (bytes)

        Returns:
            (Whether limit ***REMOVED***ed, error message)
        """
        current_time = time.time()

        # Check single message size
        if message_size > self.max_size_bytes:
            return False, f"Message size exceeds limit: {message_size} > {self.max_size_bytes}"

        # Initialize connection record
        if connection_id not in self._message_times:
            self._message_times[connection_id] = []
            self._connection_bytes[connection_id] = 0

        # Clean up expired message timestamps
        message_times = self._message_times[connection_id]
        cutoff_time = current_time - self.window_size
        self._message_times[connection_id] = [t for t in message_times if t > cutoff_time]

        # Check message frequency
        if len(self._message_times[connection_id]) >= self.max_messages:
            return False, f"Message frequency exceeds limit: {self.max_messages}/{self.window_size}s"

        # Record message
        self._message_times[connection_id].append(current_time)
        self._connection_bytes[connection_id] += message_size

        return True, None

    def cleanup_connection(self, connection_id: str) -> None:
        """Clean up connection record

        Args:
            connection_id: Connection ID
        """
        if connection_id in self._message_times:
            del self._message_times[connection_id]
        if connection_id in self._connection_bytes:
            del self._connection_bytes[connection_id]

    def get_stats(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection rate limiting statistics

        Args:
            connection_id: Connection ID

        Returns:
            Rate limiting statistics
        """
        if connection_id not in self._message_times:
            return None

        current_time = time.time()
        cutoff_time = current_time - self.window_size

        # Clean up expired timestamps
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
    """WebSocket message compression manager

    Uses Gzip algorithm to compress messages, significantly reducing bandwidth usage.
    """

    def __init__(self, compression_threshold: int = 1024):
        """Initialize message compressor

        Args:
            compression_threshold: Compression threshold (bytes), messages smaller than this are not compressed
        """
        self.compression_threshold = compression_threshold

        # Compression statistics
        self._stats: Dict[str, Any] = {
            "total_messages": 0,
            "compressed_count": 0,
            "uncompressed_count": 0,
            "bytes_original": 0,
            "bytes_compressed": 0,
        }

        logger.info(
            "Message compressor initialized",
            extra={"compression_threshold": compression_threshold},
        )

    async def compress_message(self, message: str) -> Tuple[bool, str]:
        """Compress message

        Args:
            message: Message to compress

        Returns:
            (Whether compressed, compressed message)
        """
        message_bytes = message.encode("utf-8")
        original_size = len(message_bytes)

        # Update statistics
        self._stats["total_messages"] += 1
        self._stats["bytes_original"] += original_size

        # Check if compression is needed
        if original_size < self.compression_threshold:
            self._stats["uncompressed_count"] += 1
            return False, message

        # Compress message
        compressed_bytes = gzip.compress(message_bytes)
        compressed_size = len(compressed_bytes)

        # Check if compression is effective
        if compressed_size >= original_size:
            self._stats["uncompressed_count"] += 1
            return False, message

        # Encode as base64 (for transmission through text channel)
        compressed_b64 = base64.b64encode(compressed_bytes).decode("utf-8")

        # Create compressed message format
        compressed_message = json.dumps(
            {
                "type": "compressed",
                "data": compressed_b64,
                "original_size": original_size,
                "compressed_size": compressed_size,
            }
        )

        # Update statistics
        self._stats["compressed_count"] += 1
        self._stats["bytes_compressed"] += compressed_size

        logger.debug(
            "Message compressed",
            extra={
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(compressed_size / original_size, 2),
            },
        )

        return True, compressed_message

    async def decompress_message(self, message: str) -> Optional[str]:
        """Decompress message

        Args:
            message: Compressed message

        Returns:
            Decompressed message, returns None if failed
        """
        try:
            # Try to parse as compressed message
            data = json.loads(message)

            if data.get("type") != "compressed":
                return message

            # Decode base64
            compressed_bytes = base64.b64decode(data["data"])

            # Decompress
            decompressed_bytes = gzip.decompress(compressed_bytes)

            return decompressed_bytes.decode("utf-8")

        except (json.JSONDecodeError, ValueError, Exception):
            # Not a compressed message or decompression failed
            return message

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics

        Returns:
            Compression statistics
        """
        total = self._stats["total_messages"]
        if total == 0:
            return self._stats.copy()

        stats = self._stats.copy()
        stats["compression_rate"] = round(self._stats["compressed_count"] / total * 100, 2)

        if self._stats["bytes_original"] > 0:
            stats["compression_ratio"] = round(self._stats["bytes_compressed"] / self._stats["bytes_original"], 2)
            stats["bytes_saved"] = self._stats["bytes_original"] - self._stats["bytes_compressed"]

        return stats


class WebSocketFeaturesManager:
    """WebSocket features manager

    Aggregates all WebSocket advanced features: heartbeat, rate limiting, compression, etc.
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
        """Initialize features manager

        Args:
            heartbeat_interval: Heartbeat interval (seconds)
            heartbeat_timeout: Heartbeat timeout (seconds)
            max_messages: Maximum number of messages in time window
            window_size: Rate limiting time window (seconds)
            max_message_size: Maximum message size (bytes)
            compression_threshold: Compression threshold (bytes)
        """
        self.heartbeat_manager = HeartbeatManager(heartbeat_interval, heartbeat_timeout)
        self.rate_limiter = RateLimiter(max_messages, window_size, max_message_size)
        self.compressor = MessageCompressor(compression_threshold)

        logger.info("WebSocket features manager initialized")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all features

        Returns:
            Statistics dictionary
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
