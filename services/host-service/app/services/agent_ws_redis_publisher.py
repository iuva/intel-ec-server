"""Agent WebSocket Redis Pub/Sub 模块

提供 Redis Pub/Sub 相关的工具函数和常量定义。

从 agent_websocket_manager.py 拆分出来，提高代码可维护性。
"""

from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, Optional
import uuid

# 使用 try-except 方式处理路径导入
try:
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.cache import redis_manager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# Redis Pub/Sub 相关常量
REDIS_BROADCAST_CHANNEL = "websocket:broadcast"  # 广播频道
REDIS_UNICAST_CHANNEL_PREFIX = "websocket:unicast:"  # 单播频道前缀


def get_instance_id() -> str:
    """获取当前服务实例 ID

    优先使用环境变量 SERVICE_INSTANCE_ID，否则生成随机 ID。

    Returns:
        str: 实例唯一 ID
    """
    return os.getenv("SERVICE_INSTANCE_ID", str(uuid.uuid4())[:8])


def build_broadcast_message(
    instance_id: str,
    message: dict,
    exclude: Optional[str] = None,
) -> dict:
    """构建广播消息结构

    Args:
        instance_id: 发送实例 ID
        message: 原始消息内容
        exclude: 排除的 Host ID

    Returns:
        dict: 包装后的广播消息
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
    """构建单播消息结构

    Args:
        instance_id: 发送实例 ID
        target_host_id: 目标 Host ID
        message: 原始消息内容

    Returns:
        dict: 包装后的单播消息
    """
    return {
        "instance_id": instance_id,
        "target_host_id": target_host_id,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_unicast_channel(host_id: str) -> str:
    """获取单播频道名称

    Args:
        host_id: Host ID

    Returns:
        str: 单播频道名称
    """
    return f"{REDIS_UNICAST_CHANNEL_PREFIX}{host_id}"


async def publish_broadcast_message(
    instance_id: str,
    message: dict,
    exclude: Optional[str] = None,
) -> bool:
    """发布广播消息到 Redis

    Args:
        instance_id: 发送实例 ID
        message: 消息内容
        exclude: 排除的 Host ID

    Returns:
        bool: 是否成功发布
    """
    # 检查 Redis 是否可用
    if not redis_manager.is_connected or not redis_manager.client:
        logger.debug("Redis 不可用，跳过跨实例广播")
        return False

    try:
        # 构建发布消息
        pubsub_message = build_broadcast_message(instance_id, message, exclude)

        # 发布到 Redis 频道
        await redis_manager.client.publish(
            REDIS_BROADCAST_CHANNEL,
            json.dumps(pubsub_message, ensure_ascii=False),
        )

        logger.info(
            "✅ 已发布广播消息到 Redis",
            extra={
                "channel": REDIS_BROADCAST_CHANNEL,
                "instance_id": instance_id,
                "message_type": message.get("type", "unknown"),
            },
        )
        return True

    except Exception as e:
        logger.warning(
            "Redis 发布广播消息失败",
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
    """发布单播消息到 Redis

    Args:
        instance_id: 发送实例 ID
        target_host_id: 目标 Host ID
        message: 消息内容

    Returns:
        bool: 是否成功发布
    """
    # 检查 Redis 是否可用
    if not redis_manager.is_connected or not redis_manager.client:
        logger.debug("Redis 不可用，跳过跨实例单播")
        return False

    try:
        # 构建发布消息
        pubsub_message = build_unicast_message(instance_id, target_host_id, message)

        # 发布到单播频道
        channel = get_unicast_channel(target_host_id)
        await redis_manager.client.publish(
            channel,
            json.dumps(pubsub_message, ensure_ascii=False),
        )

        logger.info(
            "✅ 已发布单播消息到 Redis",
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
            "Redis 发布单播消息失败",
            extra={
                "target_host_id": target_host_id,
                "instance_id": instance_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


def parse_redis_message(redis_message: dict) -> Optional[Dict[str, Any]]:
    """解析 Redis 消息

    Args:
        redis_message: Redis 原始消息

    Returns:
        dict: 解析后的消息内容，解析失败返回 None
    """
    try:
        data = json.loads(redis_message.get("data", "{}"))
        return data
    except json.JSONDecodeError as e:
        logger.error(
            "解析 Redis 消息失败",
            extra={"error": str(e)},
        )
        return None


def should_skip_own_message(source_instance_id: str, local_instance_id: str) -> bool:
    """判断是否应该跳过自己发布的消息

    Args:
        source_instance_id: 消息来源实例 ID
        local_instance_id: 本地实例 ID

    Returns:
        bool: 是否应该跳过
    """
    return source_instance_id == local_instance_id


def is_redis_available() -> bool:
    """检查 Redis 是否可用

    Returns:
        bool: Redis 是否可用
    """
    return redis_manager.is_connected and redis_manager.client is not None
