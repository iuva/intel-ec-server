"""Docker Environment Detection Tool

Automatically detect if running inside a Docker container,
used for configuring database and service connection addresses.
"""

import logging
import os
import platform
import socket
from pathlib import Path

logger = logging.getLogger(__name__)


def is_running_in_docker() -> bool:
    """Detect if running inside a Docker container

    Returns:
        True if in Docker container, otherwise False

    Detection methods:
    1. Check if the /.dockerenv file exists
    2. Check if /proc/self/cgroup contains docker
    3. Check if environment variable CONTAINER exists
    """
    # Method 1: Check for /.dockerenv file (Docker standard method)
    if Path("/.dockerenv").exists():
        return True

    # Method 2: Check /proc/self/cgroup (Linux)
    cgroup_path = Path("/proc/self/cgroup")
    if cgroup_path.exists():
        try:
            cgroup_content = cgroup_path.read_text()
            if "docker" in cgroup_content or "containerd" in cgroup_content:
                return True
        except Exception:
            ***REMOVED***

    # Method 3: Check environment variables
    if os.getenv("CONTAINER") or os.getenv("DOCKER_CONTAINER"):
        return True

    return False


def get_docker_host_for_database() -> str:
    """Get host address for connecting to database in Docker

    Used when connecting from local environment to database in Docker container.

    Returns:
        Host address
        - macOS/Windows: host.docker.internal
        - Linux: 172.17.0.1 (Docker default gateway)
    """
    system = platform.system().lower()
    if system in ("darwin", "windows"):
        return "host.docker.internal"
    else:
        # Linux
        return "172.17.0.1"


def resolve_mariadb_host(default_in_docker: str = "mariadb") -> str:
    """Resolve MariaDB host address

    Automatically select appropriate host address based on runtime environment:
    - Inside Docker container: use container name (e.g., mariadb)
    - In local environment: prioritize environment variables, if not set and database is in Docker,
      automatically use host.docker.internal

    Args:
        default_in_docker: Default hostname when in Docker container

    Returns:
        MariaDB host address
    """
    # If environment variable is set, use it directly
    env_host = os.getenv("MARIADB_HOST")
    if env_host:
        return env_host

    # Detect if in Docker container
    if is_running_in_docker():
        return default_in_docker
    else:
        # Local environment
        # Try to detect if Docker container is running (via docker ps or checking common ports)
        # If Docker database container is detected, use host.docker.internal
        # Otherwise use localhost

        # Prefer to try host.docker.internal (suitable for macOS/Windows)
        # If user needs to connect to database in Docker, should explicitly set MARIADB_HOST
        # Here provide a reasonable default: if possible, try host.docker.internal

        # For macOS/Windows, if database is in Docker, recommend using host.docker.internal
        # But here we are conservative, default to localhost, let user explicitly specify via environment variable
        # This supports both:
        # 1. Database is local (not Docker): use localhost
        # 2. Database is in Docker: user sets MARIADB_HOST=host.docker.internal (macOS/Windows) or 172.17.0.1 (Linux)
        return "localhost"


def resolve_redis_host(default_in_docker: str = "redis") -> str:
    """Resolve Redis host address

    Automatically select appropriate host address based on runtime environment.

    Args:
        default_in_docker: Default hostname when in Docker container

    Returns:
        Redis host address
    """
    # If environment variable is set, use it directly
    env_host = os.getenv("REDIS_HOST")
    if env_host:
        return env_host

    # Detect if in Docker container
    if is_running_in_docker():
        return default_in_docker
    else:
        # Local environment, default to localhost
        # If Redis is in Docker, user should set REDIS_HOST=host.docker.internal (macOS/Windows) or 172.17.0.1 (Linux)
        return "localhost"


def resolve_nacos_host() -> str:
    """Resolve Nacos host address

    Automatically select appropriate host address based on runtime environment.
    Nacos is exposed on the host machine through port mapping, so use localhost when starting locally.

    Returns:
        Nacos host address
    """
    # If environment variable is set, extract host part
    env_host = os.getenv("NACOS_SERVER_ADDR")
    if env_host:
        # Extract host part (if there's a complete URL)
        if env_host.startswith("http://"):
            return env_host.replace("http://", "").split(":")[0]
        if ":" in env_host:
            return env_host.split(":")[0]
        return env_host

    # Detect if in Docker container
    if is_running_in_docker():
        return "nacos"
    else:
        # Local environment, Nacos in Docker, use localhost (port mapped to host)
        return "localhost"


def resolve_service_ip() -> str:
    """Resolve service's own IP address (for registration with Nacos)

    Automatically select appropriate host address based on runtime environment:
    - Docker environment: automatically get container IP (prefer from environment variables or network interface)
    - Local environment: use 127.0.0.1

    Returns:
        Service IP address

    Note:
        Priority:
        1. Environment variable SERVICE_IP (if set, use directly)
        2. Docker environment: try to get from network interface, if fails use environment variable or default
        3. Local environment: 127.0.0.1
    """
    # If environment variable is set, use it directly (highest priority)
    env_ip = os.getenv("SERVICE_IP")
    if env_ip:
        return env_ip

    # Detect if in Docker container
    if is_running_in_docker():
        # Docker environment: try to get container IP from network interface
        try:
            # Method 1: Connect to external address to get local IP (recommended method)
            # Connect to external address (e.g., 8.8.8.8) to get local IP used for routing
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # No need to actually connect, just get the local IP used for routing
            try:
                s.connect(("8.8.8.8", 80))
                container_ip = s.getsockname()[0]
                s.close()

                # Verify if IP is a Docker network IP (172.20.0.x, 172.17.x.x or other Docker networks)
                # These are common Docker network segments
                if (
                    container_ip.startswith("172.20.0.")
                    or container_ip.startswith("172.17.")
                    or container_ip.startswith("172.18.")
                    or container_ip.startswith("172.19.")
                    or container_ip.startswith("10.0.")
                    or container_ip.startswith("192.168.")
                ):
                    logger.info(
                        f"Auto-detected container IP: {container_ip}",
                        extra={"detection_method": "socket_connect"},
                    )
                    return container_ip
            except Exception:
                s.close()

            # Method 2: Try to get from environment variable HOSTNAME (some Docker configs set this)
            # But this usually returns hostname instead of IP, so not used as primary method

        except Exception as e:
            # If acquisition fails, log warning but continue with default value
            logger.debug(f"Auto-detection of container IP failed: {str(e)}")

        # Docker environment: if auto-detection fails, recommend configuration via environment variable
        # Note: In Docker Compose, the most reliable way is through ipv4_address configuration
        # and ***REMOVED***ing via environment variable SERVICE_IP
        logger.warning(
            (
                "Unable to auto-detect Docker container IP, "
                "recommend configuring SERVICE_IP environment variable in docker-compose.yml. "
                "Will now use 127.0.0.1 (may affect service discovery)"
            ),
            extra={"suggestion": "Add to docker-compose.yml: SERVICE_IP: ${SERVICE_IP:-auto-detect-failed}"},
        )
        # Return a reasonable default value (not ideal but won't fail)
        return "127.0.0.1"
    else:
        # Local environment: use localhost
        return "127.0.0.1"
