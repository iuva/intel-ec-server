"""
Redis缓存管理模块

提供Redis异步连接管理、缓存操作和装饰器功能
"""

from functools import wraps
import hashlib
import json
import logging
from typing import Any, Callable, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis缓存管理器

    提供Redis的异步连接管理和缓存操作功能：
    - 连接管理
    - 基础缓存操作（get/set/delete）
    - 批量操作
    - 模式匹配删除
    """

    def __init__(self) -> None:
        """初始化Redis管理器"""
        self.client: Optional[redis.Redis] = None
        self._is_connected: bool = False

    async def connect(
        self,
        redis_url: str,
        encoding: str = "utf-8",
        decode_responses: bool = True,
        max_connections: int = 50,
    ) -> None:
        """连接到Redis服务器

        Args:
            redis_url: Redis连接URL，格式：redis://host:port/db
            encoding: 字符编码
            decode_responses: 是否自动解码响应
            max_connections: 最大连接数
        """
        try:
            self.client = await redis.from_url(
                redis_url,
                encoding=encoding,
                decode_responses=decode_responses,
                max_connections=max_connections,
            )

            # 测试连接
            await self.client.ping()

            self._is_connected = True
            logger.info(f"Redis连接成功: {redis_url}")

        except Exception as e:
            logger.error(f"Redis连接失败: {e!s}")
            # 降级到无缓存模式
            self.client = None
            self._is_connected = False
            logger.warning("Redis连接失败，降级到无缓存模式")

    async def disconnect(self) -> None:
        """断开Redis连接"""
        if self.client:
            await self.client.close()
            self._is_connected = False
            logger.info("Redis连接已关闭")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或连接失败则返回None
        """
        if not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e!s}")
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒），默认1小时

        Returns:
            是否设置成功
        """
        if not self.client:
            return False

        try:
            await self.client.setex(key, expire, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e!s}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.client:
            return False

        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e!s}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """按模式批量删除缓存

        Args:
            pattern: 匹配模式，如 "user:*"

        Returns:
            删除的键数量
        """
        if not self.client:
            return 0

        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"批量删除缓存: {pattern}, 数量: {deleted}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"批量删除缓存失败: {pattern}, 错误: {e!s}")
            return 0

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not self.client:
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在失败: {key}, 错误: {e!s}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """设置缓存过期时间

        Args:
            key: 缓存键
            seconds: 过期时间（秒）

        Returns:
            是否设置成功
        """
        if not self.client:
            return False

        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"设置缓存过期时间失败: {key}, 错误: {e!s}")
            return False

    async def ttl(self, key: str) -> int:
        """获取缓存剩余过期时间

        Args:
            key: 缓存键

        Returns:
            剩余秒数，-1表示永不过期，-2表示不存在
        """
        if not self.client:
            return -2

        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"获取缓存TTL失败: {key}, 错误: {e!s}")
            return -2

    @property
    def is_connected(self) -> bool:
        """检查Redis是否已连接"""
        return self._is_connected


# 全局Redis管理器实例
redis_manager = RedisManager()


def cache_result(
    expire: int = 3600,
    key_prefix: str = "cache",
    serialize_func: Optional[Callable[[Any], str]] = None,
    deserialize_func: Optional[Callable[[str], Any]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """缓存函数结果的装饰器

    Args:
        expire: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        serialize_func: 自定义序列化函数
        deserialize_func: 自定义反序列化函数

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)

            # 尝试从缓存获取
            cached_value = await redis_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                if deserialize_func:
                    return deserialize_func(cached_value)
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            if result is not None:
                value_to_cache = serialize_func(result) if serialize_func else result
                await redis_manager.set(cache_key, value_to_cache, expire)
                logger.debug(f"缓存已设置: {cache_key}")

            return result

        return wrapper

    return decorator


def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存键

    Args:
        prefix: 键前缀
        func_name: 函数名
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        缓存键
    """
    # 将参数转换为字符串
    args_str = str(args) + str(sorted(kwargs.items()))

    # 生成哈希值
    hash_value = hashlib.md5(args_str.encode()).hexdigest()

    return f"{prefix}:{func_name}:{hash_value}"


async def get_cache(key: str, deserialize_func: Optional[Callable[[str], Any]] = None) -> Optional[Any]:
    """获取缓存的辅助函数

    Args:
        key: 缓存键
        deserialize_func: 反序列化函数

    Returns:
        缓存值
    """
    value = await redis_manager.get(key)
    if value is not None and deserialize_func:
        return deserialize_func(value)
    return value


async def set_cache(
    key: str,
    value: Any,
    expire: int = 3600,
    serialize_func: Optional[Callable[[Any], str]] = None,
) -> bool:
    """设置缓存的辅助函数

    Args:
        key: 缓存键
        value: 缓存值
        expire: 过期时间（秒）
        serialize_func: 序列化函数

    Returns:
        是否设置成功
    """
    value_to_cache = serialize_func(value) if serialize_func else value
    return await redis_manager.set(key, value_to_cache, expire)
