"""Agent WebSocket Redis Pub/Sub Module

Provides Redis Pub/Sub related utility functions and constant definitions.

Split from agent_websocket_manager.py to improve code maintainability.
"""

from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, Optional
import uuid

# Use try-except to handle path imports
try:
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# Redis Pub/Sub related constants
REDIS_BROADCAST_CHANNEL = "websocket:broadcast"  # Broadcast channel
REDIS_UNICAST_CHANNEL_PREFIX = "websocket:unicast:"  # Unicast channel prefix


def get_instance_id() -> str:
    """Get current service instance ID

    Prefer environment variable SERVICE_INSTANCE_ID, otherwise generate random ID.

    Returns:
        str: Instance unique ID
    """
    return os.getenv("SERVICE_INSTANCE_ID", str(uuid.uuid4())[:8])


def build_broadcast_message(
    instance_id: str,
    message: dict,
    exclude: Optional[str] = None,
) -> dict:
    """Build broadcast message structure

    Args:
        instance_id: Sending instance ID
        message: Original message content
        exclude: Excluded Host ID

    Returns:
        dict: Wrapped broadcast message
    """
    return {
        "instance_id": instance_id,
        "message": message,
        "exclude": exclude,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_unicast_message(
    instance_id: str,
    target_host_id: str,
    message: dict,
) -> dict:
    """Build unicast message structure

    Args:
        instance_id: Sending instance ID
        target_host_id: Target Host ID
        message: Original message content

    Returns:
        dict: Wrapped unicast message
    """
    return {
        "instance_id": instance_id,
        "target_host_id": target_host_id,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_unicast_channel(host_id: str) -> str:
    """Get unicast channel name

    Args:
        host_id: Host ID

    Returns:
        str: Unicast channel name
    """
    return f"{REDIS_UNICAST_CHANNEL_PREFIX}{host_id}"


async def publish_broadcast_message(
    instance_id: str,
    message: dict,
    exclude: Optional[str] = None,
) -> bool:
    """Publish broadcast message to Redis

    Args:
        instance_id: Sending instance ID
        message: Message content
        exclude: Excluded Host ID

    Returns:
        bool: Whether publish succeeded
    """
    # Check if Redis is available
    if not redis_manager.is_connected or not redis_manager.client:
        logger.debug("Redis unavailable, skipping cross-instance broadcast")
        return False

    try:
        # Build publish message
        pubsub_message = build_broadcast_message(instance_id, message, exclude)

        # Publish to Redis channel
        await redis_manager.client.publish(
            REDIS_BROADCAST_CHANNEL,
            json.dumps(pubsub_message, ensure_ascii=False),
        )

        logger.info(
            "✅ Broadcast message published to Redis",
            extra={
                "channel": REDIS_BROADCAST_CHANNEL,
                "instance_id": instance_id,
                "message_type": message.get("type", "unknown"),
            },
        )
        return True

    except Exception as e:
        logger.warning(
            "Redis publish broadcast message failed",
            extra={
                "channel": REDIS_BROADCAST_CHANNEL,
                "instance_id": instance_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


async def publish_unicast_message(
    instance_id: str,
    target_host_id: str,
    message: dict,
) -> bool:
    """Publish unicast message to Redis

    Args:
        instance_id: Sending instance ID
        target_host_id: Target Host ID
        message: Message content

    Returns:
        bool: Whether publish succeeded
    """
    # Check if Redis is available
    if not redis_manager.is_connected or not redis_manager.client:
        logger.debug("Redis unavailable, skipping cross-instance unicast")
        return False

    try:
        # Build publish message
        pubsub_message = build_unicast_message(instance_id, target_host_id, message)

        # Publish to unicast channel
        channel = get_unicast_channel(target_host_id)
        await redis_manager.client.publish(
            channel,
            json.dumps(pubsub_message, ensure_ascii=False),
        )

        logger.info(
            "✅ Unicast message published to Redis",
            extra={
                "channel": channel,
                "instance_id": instance_id,
                "target_host_id": target_host_id,
                "message_type": message.get("type", "unknown"),
            },
        )
        return True

    except Exception as e:
        logger.warning(
            "Redis publish unicast message failed",
            extra={
                "target_host_id": target_host_id,
                "instance_id": instance_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


def parse_redis_message(redis_message: dict) -> Optional[Dict[str, Any]]:
    """Parse Redis message

    Args:
        redis_message: Redis raw message

    Returns:
        dict: Parsed message content, returns None if parsing fails
    """
    try:
        data = json.loads(redis_message.get("data", "{}"))
        return data
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse Redis message",
            extra={"error": str(e)},
        )
        return None


def should_skip_own_message(source_instance_id: str, local_instance_id: str) -> bool:
    """Determine whether to skip own published message

    Args:
        source_instance_id: Message source instance ID
        local_instance_id: Local instance ID

    Returns:
        bool: Whether should skip
    """
    return source_instance_id == local_instance_id


def is_redis_available() -> bool:
    """Check if Redis is available

    Returns:
        bool: Whether Redis is available
    """
    return redis_manager.is_connected and redis_manager.client is not None
