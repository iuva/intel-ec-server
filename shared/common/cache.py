"""
Redis缓存管理模块

提供Redis异步连接管理、缓存操作和装饰器功能
"""

import hashlib
import json
import logging
import re
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import quote_plus

import redis.asyncio as redis

logger = logging.getLogger(__name__)


def build_redis_url(
    host: str,
    port: int,
    ***REMOVED***word: Optional[str] = None,
    db: int = 0,
    username: Optional[str] = None,
    ssl_enabled: bool = False,
) -> str:
    """构建 Redis 连接 URL

    根据提供的参数构建符合 Redis 规范的连接 URL，自动处理密码中的特殊字符。

    Args:
        host: Redis 主机地址
        port: Redis 端口
        ***REMOVED***word: Redis 密码（可选）
        db: 数据库编号，默认为 0
        username: Redis 用户名（可选，Redis 6.0+）
        ssl_enabled: 是否启用 SSL/TLS（默认 False）

    Returns:
        格式化的 Redis URL（SSL 使用 rediss://，非 SSL 使用 redis://）

    Examples:
        >>> build_redis_url("localhost", 6379)
        'redis://localhost:6379/0'

        >>> build_redis_url("localhost", 6379, ***REMOVED***word="***REMOVED***")
        'redis://:***REMOVED***@localhost:6379/0'

        >>> build_redis_url("localhost", 6379, ssl_enabled=True)
        'rediss://localhost:6379/0'

        >>> build_redis_url("localhost", 6379, ***REMOVED***word="***REMOVED***", ssl_enabled=True)
        'rediss://:p%40ss%21123@localhost:6379/0'

        >>> build_redis_url("localhost", 6379, username="user", ***REMOVED***word="***REMOVED***", ssl_enabled=True)
        'rediss://user:***REMOVED***@localhost:6379/0'
    """
    # 选择协议：SSL 使用 rediss://，非 SSL 使用 redis://
    protocol = "rediss://" if ssl_enabled else "redis://"

    # 基础 URL
    if ***REMOVED***word:
        # URL 编码密码中的特殊字符
        encoded_***REMOVED***word = quote_plus(***REMOVED***word)

        if username:
            # 有用户名和密码（Redis 6.0+）
            encoded_username = quote_plus(username)
            auth_part = f"{encoded_username}:{encoded_***REMOVED***word}"
        else:
            # 只有密码（Redis 5.x 及以下）
            auth_part = f":{encoded_***REMOVED***word}"

        return f"{protocol}{auth_part}@{host}:{port}/{db}"

    # 无密码
    return f"{protocol}{host}:{port}/{db}"


def validate_redis_config(
    host: Optional[str],
    port: Optional[str],
    db: Optional[str],
) -> Tuple[str, int, int]:
    """验证并规范化 Redis 配置

    验证 Redis 配置参数的有效性，并返回规范化的值。

    Args:
        host: Redis 主机地址
        port: Redis 端口（字符串）
        db: 数据库编号（字符串）

    Returns:
        (host, port, db) 元组，包含规范化的配置值

    Raises:
        ValueError: 当配置无效时抛出

    Examples:
        >>> validate_redis_config("localhost", "6379", "0")
        ('localhost', 6379, 0)

        >>> validate_redis_config("", "6379", "0")
        ValueError: Redis host 不能为空

        >>> validate_redis_config("localhost", "invalid", "0")
        ValueError: Redis port 必须是有效的整数
    """
    # 验证 host
    if not host or not host.strip():
        raise ValueError("Redis host 不能为空")

    # 验证 port
    try:
        port_int = int(port) if port else 6379
        if not (1 <= port_int <= 65535):
            raise ValueError("Redis port 必须在 1-65535 范围内")
    except (ValueError, TypeError) as e:
        if "must be" in str(e) or "范围" in str(e):
            raise
        raise ValueError("Redis port 必须是有效的整数")

    # 验证 db
    try:
        db_int = int(db) if db else 0
        if not (0 <= db_int <= 15):
            raise ValueError("Redis db 必须在 0-15 范围内")
    except (ValueError, TypeError) as e:
        if "must be" in str(e) or "范围" in str(e):
            raise
        raise ValueError("Redis db 必须是有效的整数")

    return host.strip(), port_int, db_int


def mask_sensitive_info(url: str) -> str:
    """脱敏 URL 中的敏感信息

    将 Redis URL 中的密码部分替换为 ***，用于日志记录时保护敏感信息。

    Args:
        url: Redis 连接 URL

    Returns:
        脱敏后的 URL

    Examples:
        >>> mask_sensitive_info("redis://:***REMOVED***@localhost:6379/0")
        'redis://:***@localhost:6379/0'

        >>> mask_sensitive_info("redis://user:***REMOVED***word@localhost:6379/0")
        'redis://user:***@localhost:6379/0'

        >>> mask_sensitive_info("redis://localhost:6379/0")
        'redis://localhost:6379/0'
    """
    # 匹配密码部分: ://[username]:***REMOVED***word@
    # 捕获组: (://[^:]*:) 匹配到冒号, ([^@]+) 匹配密码, (@) 匹配 @
    pattern = r"(://[^:]*:)([^@]+)(@)"
    return re.sub(pattern, r"\1***\3", url)


async def diagnose_connection_error(
    error: Exception,
    redis_url: str,
    host: str,
    port: int,
) -> Dict[str, Any]:
    """诊断 Redis 连接错误

    根据错误类型提供具体的故障排查建议，帮助快速定位和解决 Redis 连接问题。

    Args:
        error: 连接异常对象
        redis_url: 连接 URL（应该已经脱敏）
        host: Redis 主机地址
        port: Redis 端口

    Returns:
        诊断信息字典，包含以下字段：
        - error_type: 错误类型名称
        - error_message: 错误消息
        - suggestions: 故障排查建议列表
        - connection_info: 连接信息字典

    Examples:
        >>> error = ConnectionRefusedError("Connection refused")
        >>> diagnosis = await diagnose_connection_error(
        ...     error, "redis://:***@localhost:6379/0", "localhost", 6379
        ... )
        >>> diagnosis["error_type"]
        'ConnectionRefusedError'
        >>> len(diagnosis["suggestions"]) > 0
        True
    """
    suggestions = []
    error_str = str(error).lower()

    # 根据错误类型提供建议
    if "connection refused" in error_str or "refused" in error_str:
        # 连接被拒绝错误
        suggestions.extend(
            [
                f"检查 Redis 服务是否在 {host}:{port} 上运行",
                f"运行命令验证: redis-cli -h {host} -p {port} ping",
                "检查防火墙设置是否阻止了连接",
                "确认 Redis 配置文件中的 bind 地址设置",
                "检查 Redis 是否正在监听正确的端口",
            ]
        )

    elif "timeout" in error_str or "timed out" in error_str:
        # 超时错误
        suggestions.extend(
            [
                "检查网络连接是否正常",
                f"验证主机 {host} 是否可达: ping {host}",
                "增加连接超时时间配置",
                "检查是否存在网络延迟或丢包",
                "确认 Redis 服务器负载是否过高",
            ]
        )

    elif "authentication" in error_str or "auth" in error_str or "noauth" in error_str:
        # 认证错误
        suggestions.extend(
            [
                "检查 REDIS_PASSWORD 环境变量是否正确",
                "验证 Redis 配置中的 require***REMOVED*** 设置",
                "确认密码中的特殊字符已正确编码",
                "检查是否使用了正确的用户名（Redis 6.0+）",
                "尝试使用 redis-cli 手动连接验证密码",
            ]
        )

    elif "name or service not known" in error_str or "nodename nor servname" in error_str:
        # 主机名解析失败
        suggestions.extend(
            [
                f"主机名 {host} 无法解析",
                "检查 /etc/hosts 文件或 DNS 配置",
                "尝试使用 IP 地址而不是主机名",
                f"运行命令验证: nslookup {host}",
                "确认网络连接正常",
            ]
        )

    elif "max" in error_str and "client" in error_str:
        # 最大连接数错误
        suggestions.extend(
            [
                "Redis 服务器已达到最大客户端连接数",
                "检查 Redis 配置中的 maxclients 设置",
                "关闭不必要的 Redis 连接",
                "考虑增加 maxclients 配置值",
                "检查是否存在连接泄漏",
            ]
        )

    elif "readonly" in error_str or "read only" in error_str:
        # 只读模式错误
        suggestions.extend(
            [
                "Redis 服务器处于只读模式",
                "检查 Redis 是否为从节点（slave/replica）",
                "确认是否需要连接到主节点（master）",
                "检查磁盘空间是否已满",
                "查看 Redis 日志了解只读原因",
            ]
        )

    else:
        # 通用错误处理
        suggestions.extend(
            [
                "检查 Redis 服务状态",
                "查看 Redis 服务器日志: /var/log/redis/redis-server.log",
                "验证网络连接和防火墙配置",
                f"尝试手动连接: redis-cli -h {host} -p {port}",
                "检查 Redis 配置文件是否正确",
            ]
        )

    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "suggestions": suggestions,
        "connection_info": {
            "host": host,
            "port": port,
            "url": redis_url,  # 应该已经脱敏
        },
    }


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
        ssl_ca_certs: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
        ssl_cert_reqs: Optional[str] = None,
        ssl_check_hostname: bool = False,
    ) -> None:
        """连接到Redis服务器

        Args:
            redis_url: Redis连接URL，格式：redis://host:port/db 或 rediss://host:port/db（SSL）
            encoding: 字符编码
            decode_responses: 是否自动解码响应
            max_connections: 最大连接数
            ssl_ca_certs: CA 证书文件路径（可选）
            ssl_certfile: 客户端证书文件路径（可选）
            ssl_keyfile: 客户端私钥文件路径（可选）
            ssl_cert_reqs: SSL 证书验证要求（可选，none/optional/required）
            ssl_check_hostname: 是否验证主机名（默认 False）
        """
        import os
        import ssl

        # 脱敏 URL 用于日志记录
        masked_url = mask_sensitive_info(redis_url)

        # 从 URL 中提取 host 和 port 用于诊断
        # 格式: redis://[auth@]host:port/db 或 rediss://[auth@]host:port/db
        url_pattern = r"rediss?://(?:[^@]+@)?([^:]+):(\d+)"
        match = re.match(url_pattern, redis_url)
        host = match.group(1) if match else "unknown"
        port = int(match.group(2)) if match else 6379

        # ✅ 从环境变量读取 SSL 配置（如果未通过参数提供）
        ssl_enabled = redis_url.startswith("rediss://")
        if ssl_enabled:
            # 如果 URL 使用 rediss://，则启用 SSL
            if not ssl_ca_certs:
                ssl_ca_certs = os.getenv("REDIS_SSL_CA", "")
            if not ssl_certfile:
                ssl_certfile = os.getenv("REDIS_SSL_CERT", "")
            if not ssl_keyfile:
                ssl_keyfile = os.getenv("REDIS_SSL_KEY", "")
            if not ssl_cert_reqs:
                ssl_cert_reqs = os.getenv("REDIS_SSL_VERIFY_CERT", "required")
            ssl_check_hostname = os.getenv("REDIS_SSL_VERIFY_IDENTITY", "false").lower() in ("true", "1", "yes")

        # 构建 SSL 参数字典
        ssl_params = {}
        if ssl_enabled:
            # 创建 SSL 上下文
            ssl_context = ssl.create_default_context()

            # 设置证书验证要求
            if ssl_cert_reqs:
                cert_reqs_map = {
                    "none": ssl.CERT_NONE,
                    "optional": ssl.CERT_OPTIONAL,
                    "required": ssl.CERT_REQUIRED,
                }
                ssl_context.verify_mode = cert_reqs_map.get(ssl_cert_reqs.lower(), ssl.CERT_REQUIRED)
            else:
                ssl_context.verify_mode = ssl.CERT_REQUIRED

            # 设置主机名验证
            ssl_context.check_hostname = ssl_check_hostname

            # 加载 CA 证书
            if ssl_ca_certs:
                try:
                    ssl_context.load_verify_locations(ssl_ca_certs)
                    logger.debug(f"已加载 Redis SSL CA 证书: {ssl_ca_certs}")
                except Exception as e:
                    logger.warning(
                        f"加载 Redis SSL CA 证书失败: {ssl_ca_certs}",
                        extra={"error": str(e)},
                    )

            # 加载客户端证书
            if ssl_certfile and ssl_keyfile:
                try:
                    ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
                    logger.debug(f"已加载 Redis SSL 客户端证书: {ssl_certfile}, {ssl_keyfile}")
                except Exception as e:
                    logger.warning(
                        f"加载 Redis SSL 客户端证书失败: {ssl_certfile}, {ssl_keyfile}",
                        extra={"error": str(e)},
                    )

            # 将 SSL 上下文添加到参数
            ssl_params["ssl"] = ssl_context

            logger.info(
                "Redis SSL 已启用",
                extra={
                    "ssl_enabled": True,
                    "ssl_verify_cert": ssl_cert_reqs != "none",
                    "ssl_verify_identity": ssl_check_hostname,
                },
            )

        try:
            # 记录连接尝试
            logger.info(f"正在连接 Redis: {masked_url}")

            self.client = await redis.from_url(
                redis_url,
                encoding=encoding,
                decode_responses=decode_responses,
                max_connections=max_connections,
                **ssl_params,  # ✅ 传递 SSL 参数
            )

            # 测试连接
            await self.client.ping()

            self._is_connected = True
            logger.info(f"Redis 连接成功: {masked_url}")

        except Exception as e:
            # 记录连接失败错误
            logger.error(f"Redis 连接失败: {masked_url}")
            logger.error(f"错误详情: {type(e).__name__}: {e!s}")

            # 调用诊断函数获取详细的排查建议
            diagnosis = await diagnose_connection_error(
                error=e,
                redis_url=masked_url,
                host=host,
                port=port,
            )

            # 记录错误类型和错误消息
            logger.error(f"错误类型: {diagnosis['error_type']}")
            logger.error(f"错误消息: {diagnosis['error_message']}")

            # 记录所有排查建议
            logger.error("故障排查建议:")
            for i, suggestion in enumerate(diagnosis["suggestions"], 1):
                logger.error(f"  {i}. {suggestion}")

            # 降级到无缓存模式
            self.client = None
            self._is_connected = False
            logger.warning("Redis 不可用，服务已降级到无缓存模式，将继续运行")

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
