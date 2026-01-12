"""
Redis Cache Management Module

Provides Redis asynchronous connection management, caching operations and decorator functions
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
    """Build Redis Connection URL

    Build a Redis-compliant connection URL according to the provided parameters,
    automatically handling special characters in ***REMOVED***words.

    Args:
        host: Redis host address
        port: Redis port
        ***REMOVED***word: Redis ***REMOVED***word (optional)
        db: Database number, default is 0
        username: Redis username (optional, Redis 6.0+)
        ssl_enabled: Whether to enable SSL/TLS (default False)

    Returns:
        Formatted Redis URL (SSL uses rediss://, non-SSL uses redis://)

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
    # Select protocol: SSL uses rediss://, non-SSL uses redis://
    protocol = "rediss://" if ssl_enabled else "redis://"

    # Base URL
    if ***REMOVED***word:
        # URL encode special characters in ***REMOVED***word
        encoded_***REMOVED***word = quote_plus(***REMOVED***word)

        if username:
            # Username and ***REMOVED***word (Redis 6.0+)
            encoded_username = quote_plus(username)
            auth_part = f"{encoded_username}:{encoded_***REMOVED***word}"
        else:
            # Password only (Redis 5.x and below)
            auth_part = f":{encoded_***REMOVED***word}"

        return f"{protocol}{auth_part}@{host}:{port}/{db}"

    # No ***REMOVED***word
    return f"{protocol}{host}:{port}/{db}"


def validate_redis_config(
    host: Optional[str],
    port: Optional[str],
    db: Optional[str],
) -> Tuple[str, int, int]:
    """Validate and normalize Redis configuration

    Validate the validity of Redis configuration parameters and return normalized values.

    Args:
        host: Redis host address
        port: Redis port (string)
        db: Database number (string)

    Returns:
        (host, port, db) tuple containing normalized configuration values

    Raises:
        ValueError: Raised when configuration is invalid

    Examples:
        >>> validate_redis_config("localhost", "6379", "0")
        ('localhost', 6379, 0)

        >>> validate_redis_config("", "6379", "0")
        ValueError: Redis host cannot be empty

        >>> validate_redis_config("localhost", "invalid", "0")
        ValueError: Redis port must be a valid integer
    """
    # Validate host
    if not host or not host.strip():
        raise ValueError("Redis host cannot be empty")

    # Validate port
    try:
        port_int = int(port) if port else 6379
        if not (1 <= port_int <= 65535):
            raise ValueError("Redis port must be within range 1-65535")
    except (ValueError, TypeError) as e:
        if "must be" in str(e) or "range" in str(e):
            raise
        raise ValueError("Redis port must be a valid integer")

    # Validate db
    try:
        db_int = int(db) if db else 0
        if not (0 <= db_int <= 15):
            raise ValueError("Redis db must be within range 0-15")
    except (ValueError, TypeError) as e:
        if "must be" in str(e) or "range" in str(e):
            raise
        raise ValueError("Redis db must be a valid integer")

    return host.strip(), port_int, db_int


def mask_sensitive_info(url: str) -> str:
    """Mask sensitive information in URL

    Replace the ***REMOVED***word part in Redis URL with ***, to protect sensitive information when logging.

    Args:
        url: Redis connection URL

    Returns:
        Masked URL

    Examples:
        >>> mask_sensitive_info("redis://:***REMOVED***@localhost:6379/0")
        'redis://:***@localhost:6379/0'

        >>> mask_sensitive_info("redis://user:***REMOVED***word@localhost:6379/0")
        'redis://user:***@localhost:6379/0'

        >>> mask_sensitive_info("redis://localhost:6379/0")
        'redis://localhost:6379/0'
    """
    # Match ***REMOVED***word part: ://[username]:***REMOVED***word@
    # Capture group: (://[^:]*:) matches to colon, ([^@]+) matches ***REMOVED***word, (@) matches @
    pattern = r"(://[^:]*:)([^@]+)(@)"
    return re.sub(pattern, r"\1***\3", url)


async def diagnose_connection_error(
    error: Exception,
    redis_url: str,
    host: str,
    port: int,
) -> Dict[str, Any]:
    """Diagnose Redis connection errors

    Provide specific troubleshooting suggestions based on error type,
    to help quickly locate and resolve Redis connection issues.

    Args:
        error: Connection exception object
        redis_url: Connection URL (should already be masked)
        host: Redis host address
        port: Redis port

    Returns:
        Diagnosis information dictionary containing the following fields:
        - error_type: Error type name
        - error_message: Error message
        - suggestions: Troubleshooting suggestions list
        - connection_info: Connection information dictionary

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

    # Provide suggestions based on error type
    if "connection refused" in error_str or "refused" in error_str:
        # Connection refused error
        suggestions.extend(
            [
                f"Check if Redis service is running on {host}:{port}",
                f"Run command to verify: redis-cli -h {host} -p {port} ping",
                "Check if firewall settings are blocking the connection",
                "Confirm bind address setting in Redis configuration file",
                "Check if Redis is listening on the correct port",
            ]
        )

    elif "timeout" in error_str or "timed out" in error_str:
        # Timeout error
        suggestions.extend(
            [
                "Check if network connection is normal",
                f"Verify if host {host} is reachable: ping {host}",
                "Increase connection timeout configuration",
                "Check if there is network delay or packet loss",
                "Confirm if Redis server load is too high",
            ]
        )

    elif "authentication" in error_str or "auth" in error_str or "noauth" in error_str:
        # Authentication error
        suggestions.extend(
            [
                "Check if REDIS_PASSWORD environment variable is correct",
                "Verify require***REMOVED*** setting in Redis configuration",
                "Confirm special characters in ***REMOVED***word are correctly encoded",
                "Check if correct username is used (Redis 6.0+)",
                "Try using redis-cli to manually connect and verify ***REMOVED***word",
            ]
        )

    elif "name or service not known" in error_str or "nodename nor servname" in error_str:
        # Hostname resolution failure
        suggestions.extend(
            [
                f"Hostname {host} cannot be resolved",
                "Check /etc/hosts file or DNS configuration",
                "Try using IP address instead of hostname",
                f"Run command to verify: nslookup {host}",
                "Confirm network connection is normal",
            ]
        )

    elif "max" in error_str and "client" in error_str:
        # Maximum connections error
        suggestions.extend(
            [
                "Redis server has reached maximum client connections",
                "Check maxclients setting in Redis configuration",
                "Close unnecessary Redis connections",
                "Consider increasing maxclients configuration value",
                "Check if there are connection leaks",
            ]
        )

    elif "readonly" in error_str or "read only" in error_str:
        # Read-only mode error
        suggestions.extend(
            [
                "Redis server is in read-only mode",
                "Check if Redis is a slave/replica node",
                "Confirm if need to connect to master node",
                "Check if disk space is full",
                "View Redis logs to understand read-only reason",
            ]
        )

    else:
        # Generic error handling
        suggestions.extend(
            [
                "Check Redis service status",
                "View Redis server logs: /var/log/redis/redis-server.log",
                "Verify network connection and firewall configuration",
                f"Try manual connection: redis-cli -h {host} -p {port}",
                "Check if Redis configuration file is correct",
            ]
        )

    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "suggestions": suggestions,
        "connection_info": {
            "host": host,
            "port": port,
            "url": redis_url,  # Should already be masked
        },
    }


class RedisManager:
    """Redis Cache Manager

    Provides Redis asynchronous connection management and caching operation functions:
    - Connection management
    - Basic cache operations (get/set/delete)
    - Batch operations
    - Pattern matching deletion
    """

    def __init__(self) -> None:
        """Initialize Redis manager"""
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
        """Connect to Redis server

        Args:
            redis_url: Redis connection URL, format: redis://host:port/db or rediss://host:port/db (SSL)
            encoding: Character encoding
            decode_responses: Whether to automatically decode responses
            max_connections: Maximum connections
            ssl_ca_certs: CA certificate file path (optional)
            ssl_certfile: Client certificate file path (optional)
            ssl_keyfile: Client private key file path (optional)
            ssl_cert_reqs: SSL certificate verification requirement (optional, none/optional/required)
            ssl_check_hostname: Whether to verify hostname (default False)
        """
        import os
        import ssl

        # Mask URL for logging
        masked_url = mask_sensitive_info(redis_url)

        # Extract host and port from URL for diagnosis
        # Format: redis://[auth@]host:port/db or rediss://[auth@]host:port/db
        url_pattern = r"rediss?://(?:[^@]+@)?([^:]+):(\d+)"
        match = re.match(url_pattern, redis_url)
        host = match.group(1) if match else "unknown"
        port = int(match.group(2)) if match else 6379

        # ✅ Read SSL configuration from environment variables (if not provided via parameters)
        ssl_enabled = redis_url.startswith("rediss://")
        if ssl_enabled:
            # If URL uses rediss://, enable SSL
            if not ssl_ca_certs:
                ssl_ca_certs = os.getenv("REDIS_SSL_CA", "")
            if not ssl_certfile:
                ssl_certfile = os.getenv("REDIS_SSL_CERT", "")
            if not ssl_keyfile:
                ssl_keyfile = os.getenv("REDIS_SSL_KEY", "")
            if not ssl_cert_reqs:
                ssl_cert_reqs = os.getenv("REDIS_SSL_VERIFY_CERT", "required")
            ssl_check_hostname = os.getenv("REDIS_SSL_VERIFY_IDENTITY", "false").lower() in ("true", "1", "yes")

        # Build SSL parameters dictionary
        ssl_params = {}
        if ssl_enabled:
            # Create SSL context
            ssl_context = ssl.create_default_context()

            # ✅ Fix: Must set check_hostname first, then verify_mode
            # When verify_mode is CERT_NONE, check_hostname must be disabled first
            # Otherwise error: cannot set verify_mode to CERT_NONE when check_hostname is enabled

            # Determine certificate verification requirements
            if ssl_cert_reqs:
                cert_reqs_map = {
                    "none": ssl.CERT_NONE,
                    "optional": ssl.CERT_OPTIONAL,
                    "required": ssl.CERT_REQUIRED,
                }
                verify_mode_value = cert_reqs_map.get(ssl_cert_reqs.lower(), ssl.CERT_REQUIRED)
            else:
                verify_mode_value = ssl.CERT_REQUIRED

            # If verify_mode is CERT_NONE, must disable check_hostname first
            if verify_mode_value == ssl.CERT_NONE:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                # Set verify_mode first, then check_hostname
                ssl_context.verify_mode = verify_mode_value
                ssl_context.check_hostname = ssl_check_hostname

            # Load CA certificate
            if ssl_ca_certs:
                try:
                    ssl_context.load_verify_locations(ssl_ca_certs)
                    logger.debug(f"Loaded Redis SSL CA certificate: {ssl_ca_certs}")
                except Exception as e:
                    logger.warning(
                        f"Failed to load Redis SSL CA certificate: {ssl_ca_certs}",
                        extra={"error": str(e)},
                    )

            # Load client certificate
            if ssl_certfile and ssl_keyfile:
                try:
                    ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
                    logger.debug(f"Loaded Redis SSL client certificate: {ssl_certfile}, {ssl_keyfile}")
                except Exception as e:
                    logger.warning(
                        f"Failed to load Redis SSL client certificate: {ssl_certfile}, {ssl_keyfile}",
                        extra={"error": str(e)},
                    )

            # ✅ Fix: redis.from_url() doesn't accept ssl parameter
            # Since URL uses rediss://, SSL is automatically enabled, no need to ***REMOVED*** ssl=True
            # We only need to ***REMOVED*** certificate file paths (if provided)
            # redis-py supports these parameters: ssl_ca_certs, ssl_certfile, ssl_keyfile, ssl_cert_reqs

            # Pass certificate file paths (if provided)
            if ssl_ca_certs:
                ssl_params["ssl_ca_certs"] = ssl_ca_certs
            if ssl_certfile:
                ssl_params["ssl_certfile"] = ssl_certfile
            if ssl_keyfile:
                ssl_params["ssl_keyfile"] = ssl_keyfile

            # Pass certificate verification requirements
            # redis-py's ssl_cert_reqs accepts ssl.CERT_NONE, ssl.CERT_OPTIONAL, ssl.CERT_REQUIRED
            # or None (means no verification)
            if verify_mode_value == ssl.CERT_NONE:
                ssl_params["ssl_cert_reqs"] = None  # Don't verify certificate
            else:
                ssl_params["ssl_cert_reqs"] = verify_mode_value

            # Pass hostname verification setting
            ssl_params["ssl_check_hostname"] = ssl_check_hostname if verify_mode_value != ssl.CERT_NONE else False

            logger.info(
                "Redis SSL enabled",
                extra={
                    "ssl_enabled": True,
                    "ssl_verify_cert": ssl_cert_reqs != "none",
                    "ssl_verify_identity": ssl_check_hostname,
                },
            )

        try:
            # Log connection attempt
            logger.info(f"Connecting to Redis: {masked_url}")

            self.client = await redis.from_url(
                redis_url,
                encoding=encoding,
                decode_responses=decode_responses,
                max_connections=max_connections,
                **ssl_params,  # ✅ Pass SSL parameters
            )

            # Test connection
            await self.client.ping()

            self._is_connected = True
            logger.info(f"Redis connection successful: {masked_url}")

        except Exception as e:
            # Log connection failure error
            logger.error(f"Redis connection failed: {masked_url}")
            logger.error(f"Error details: {type(e).__name__}: {e!s}")

            # Call diagnosis function to get detailed troubleshooting suggestions
            diagnosis = await diagnose_connection_error(
                error=e,
                redis_url=masked_url,
                host=host,
                port=port,
            )

            # Log error type and error message
            logger.error(f"Error type: {diagnosis['error_type']}")
            logger.error(f"Error message: {diagnosis['error_message']}")

            # Log all troubleshooting suggestions
            logger.error("Troubleshooting suggestions:")
            for i, suggestion in enumerate(diagnosis["suggestions"], 1):
                logger.error(f"  {i}. {suggestion}")

            # Downgrade to no-cache mode
            self.client = None
            self._is_connected = False
            logger.warning("Redis unavailable, service has been downgraded to no-cache mode, will continue running")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self._is_connected = False
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value

        Args:
            key: Cache key

        Returns:
            Cached value, returns None if not exists or connection failed
        """
        if not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache: {key}, Error: {e!s}")
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set cached value

        Args:
            key: Cache key
            value: Cache value
            expire: Expiration time (seconds), default 1 hour

        Returns:
            Whether set was successful
        """
        if not self.client:
            return False

        try:
            await self.client.setex(key, expire, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {key}, Error: {e!s}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete cache

        Args:
            key: Cache key

        Returns:
            Whether deletion was successful
        """
        if not self.client:
            return False

        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache: {key}, Error: {e!s}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Batch delete cache by pattern

        Args:
            pattern: Matching pattern, e.g. "user:*"

        Returns:
            Number of deleted keys
        """
        if not self.client:
            return 0

        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"Batch deleted cache: {pattern}, Count: {deleted}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Failed to batch delete cache: {pattern}, Error: {e!s}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if cache exists

        Args:
            key: Cache key

        Returns:
            Whether exists
        """
        if not self.client:
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check cache existence: {key}, Error: {e!s}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set cache expiration time

        Args:
            key: Cache key
            seconds: Expiration time (seconds)

        Returns:
            Whether set was successful
        """
        if not self.client:
            return False

        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set cache expiration time: {key}, Error: {e!s}")
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining cache expiration time

        Args:
            key: Cache key

        Returns:
            Remaining seconds, -1 means never expires, -2 means doesn't exist
        """
        if not self.client:
            return -2

        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get cache TTL: {key}, Error: {e!s}")
            return -2

    async def acquire_lock(self, key: str, timeout: int = 30, lock_value: Optional[str] = None) -> bool:
        """Acquire distributed lock

        Implement distributed lock using Redis SET NX EX command.

        Args:
            key: Key name of the lock
            timeout: Lock expiration time (seconds), default 30 seconds
            lock_value: Value of the lock (for validation when releasing), if None auto-generate UUID

        Returns:
            Whether lock acquisition was successful
        """
        if not self.client:
            return False

        try:
            import uuid

            if lock_value is None:
                lock_value = str(uuid.uuid4())

            # Use SET NX EX command: set if key doesn't exist, and set expiration time
            result = await self.client.set(key, lock_value, nx=True, ex=timeout)
            return result is True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {key}, Error: {e!s}")
            return False

    async def release_lock(self, key: str, lock_value: str) -> bool:
        """Release distributed lock

        Use Lua script to ensure only the lock holder can release the lock.

        Args:
            key: Key name of the lock
            lock_value: Value of the lock (must match the value when acquiring)

        Returns:
            Whether lock release was successful
        """
        if not self.client:
            return False

        try:
            # Use Lua script to ensure atomicity: only delete when lock value matches
            lua_script = '''
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            '''
            result = await self.client.eval(lua_script, 1, key, lock_value)  # type: ignore
            return result == 1
        except Exception as e:
            logger.error(f"Failed to release lock: {key}, Error: {e!s}")
            return False

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._is_connected


# Global Redis manager instance
redis_manager = RedisManager()


def cache_result(
    expire: int = 3600,
    key_prefix: str = "cache",
    serialize_func: Optional[Callable[[Any], str]] = None,
    deserialize_func: Optional[Callable[[str], Any]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to cache function results

    Args:
        expire: Cache expiration time (seconds)
        key_prefix: Cache key prefix
        serialize_func: Custom serialization function
        deserialize_func: Custom deserialization function

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)

            # Try to get from cache
            cached_value = await redis_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                if deserialize_func:
                    return deserialize_func(cached_value)
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                value_to_cache = serialize_func(result) if serialize_func else result
                await redis_manager.set(cache_key, value_to_cache, expire)
                logger.debug(f"Cache set: {cache_key}")

            return result

        return wrapper

    return decorator


def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate cache key

    Args:
        prefix: Key prefix
        func_name: Function name
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Cache key
    """
    # Convert parameters to string
    args_str = str(args) + str(sorted(kwargs.items()))

    # Generate hash value
    hash_value = hashlib.md5(args_str.encode()).hexdigest()

    return f"{prefix}:{func_name}:{hash_value}"


async def get_cache(key: str, deserialize_func: Optional[Callable[[str], Any]] = None) -> Optional[Any]:
    """Helper function to get cache

    Args:
        key: Cache key
        deserialize_func: Deserialization function

    Returns:
        Cached value
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
    """Helper function to set cache

    Args:
        key: Cache key
        value: Cache value
        expire: Expiration time (seconds)
        serialize_func: Serialization function

    Returns:
        Whether set was successful
    """
    value_to_cache = serialize_func(value) if serialize_func else value
    return await redis_manager.set(key, value_to_cache, expire)
