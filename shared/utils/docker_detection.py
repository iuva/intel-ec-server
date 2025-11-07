"""Docker 环境检测工具

自动检测是否运行在 Docker 容器内，用于配置数据库和服务连接地址。
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def is_running_in_docker() -> bool:
    """检测是否运行在 Docker 容器内

    Returns:
        如果在 Docker 容器内返回 True，否则返回 False

    检测方法：
    1. 检查 /.dockerenv 文件是否存在
    2. 检查 /proc/self/cgroup 是否包含 docker
    3. 检查环境变量 CONTAINER 是否存在
    """
    # 方法 1: 检查 /.dockerenv 文件（Docker 标准方法）
    if Path("/.dockerenv").exists():
        return True

    # 方法 2: 检查 /proc/self/cgroup（Linux）
    cgroup_path = Path("/proc/self/cgroup")
    if cgroup_path.exists():
        try:
            cgroup_content = cgroup_path.read_text()
            if "docker" in cgroup_content or "containerd" in cgroup_content:
                return True
        except Exception:
            ***REMOVED***

    # 方法 3: 检查环境变量
    if os.getenv("CONTAINER") or os.getenv("DOCKER_CONTAINER"):
        return True

    return False


def get_docker_host_for_database() -> str:
    """获取用于连接 Docker 中数据库的主机地址

    从本地环境连接到 Docker 容器中的数据库时使用。

    Returns:
        主机地址
        - macOS/Windows: host.docker.internal
        - Linux: 172.17.0.1 (Docker 默认网关)
    """
    import platform

    system = platform.system().lower()
    if system in ("darwin", "windows"):
        return "host.docker.internal"
    else:
        # Linux
        return "172.17.0.1"


def resolve_mariadb_host(default_in_docker: str = "mariadb") -> str:
    """解析 MariaDB 主机地址

    根据运行环境自动选择合适的主机地址：
    - 在 Docker 容器内：使用容器名（如 mariadb）
    - 在本地环境：优先使用环境变量，如果未设置且数据库在 Docker 中，自动使用 host.docker.internal

    Args:
        default_in_docker: 在 Docker 容器内时的默认主机名

    Returns:
        MariaDB 主机地址
    """
    # 如果环境变量已设置，直接使用
    env_host = os.getenv("MARIADB_HOST")
    if env_host:
        return env_host

    # 检测是否在 Docker 容器内
    if is_running_in_docker():
        return default_in_docker
    else:
        # 本地环境
        # 尝试检测 Docker 容器是否运行（通过 docker ps 或检查常见端口）
        # 如果检测到 Docker 数据库容器，使用 host.docker.internal
        # 否则使用 localhost

        # 优先尝试使用 host.docker.internal（适用于 macOS/Windows）
        # 如果用户需要连接到 Docker 中的数据库，应该显式设置 MARIADB_HOST
        # 这里提供一个合理的默认值：如果可能，尝试 host.docker.internal

        # 对于 macOS/Windows，如果数据库在 Docker 中，建议使用 host.docker.internal
        # 但这里我们保守一点，默认使用 localhost，让用户通过环境变量明确指定
        # 这样可以同时支持：
        # 1. 数据库在本地（非 Docker）：使用 localhost
        # 2. 数据库在 Docker 中：用户设置 MARIADB_HOST=host.docker.internal（macOS/Windows）或 172.17.0.1（Linux）
        return "localhost"


def resolve_redis_host(default_in_docker: str = "redis") -> str:
    """解析 Redis 主机地址

    根据运行环境自动选择合适的主机地址。

    Args:
        default_in_docker: 在 Docker 容器内时的默认主机名

    Returns:
        Redis 主机地址
    """
    # 如果环境变量已设置，直接使用
    env_host = os.getenv("REDIS_HOST")
    if env_host:
        return env_host

    # 检测是否在 Docker 容器内
    if is_running_in_docker():
        return default_in_docker
    else:
        # 本地环境，默认使用 localhost
        # 如果 Redis 在 Docker 中，用户应该设置 REDIS_HOST=host.docker.internal（macOS/Windows）或 172.17.0.1（Linux）
        return "localhost"


def resolve_nacos_host() -> str:
    """解析 Nacos 主机地址

    根据运行环境自动选择合适的主机地址。
    Nacos 通过端口映射暴露在宿主机上，所以本地启动时使用 localhost。

    Returns:
        Nacos 主机地址
    """
    # 如果环境变量已设置，提取主机部分
    env_host = os.getenv("NACOS_SERVER_ADDR")
    if env_host:
        # 提取主机部分（如果有完整的 URL）
        if env_host.startswith("http://"):
            return env_host.replace("http://", "").split(":")[0]
        if ":" in env_host:
            return env_host.split(":")[0]
        return env_host

    # 检测是否在 Docker 容器内
    if is_running_in_docker():
        return "nacos"
    else:
        # 本地环境，Nacos 在 Docker 中，使用 localhost（端口映射到宿主机）
        return "localhost"


def resolve_service_ip() -> str:
    """解析服务自身 IP 地址（用于向 Nacos 注册）

    根据运行环境自动选择合适的主机地址：
    - Docker 环境：自动获取容器 IP（优先从环境变量或网络接口）
    - 本地环境：使用 127.0.0.1

    Returns:
        服务 IP 地址

    Note:
        优先级：
        1. 环境变量 SERVICE_IP（如果设置了，直接使用）
        2. Docker 环境：尝试从网络接口获取，失败则使用环境变量或默认值
        3. 本地环境：127.0.0.1
    """
    # 如果环境变量已设置，直接使用（最高优先级）
    env_ip = os.getenv("SERVICE_IP")
    if env_ip:
        return env_ip

    # 检测是否在 Docker 容器内
    if is_running_in_docker():
        # Docker 环境：尝试从网络接口获取容器 IP
        try:
            import socket

            # 方法1: 连接到外部地址以获取本地 IP（推荐方法）
            # 连接到外部地址（如 8.8.8.8）以获取路由使用的本地 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 不需要真正连接，只是获取路由使用的本地 IP
            try:
                s.connect(("8.8.8.8", 80))
                container_ip = s.getsockname()[0]
                s.close()

                # 验证 IP 是否为 Docker 网络 IP（172.20.0.x、172.17.x.x 或其他 Docker 网络）
                # 这些是常见的 Docker 网络网段
                if (
                    container_ip.startswith("172.20.0.")
                    or container_ip.startswith("172.17.")
                    or container_ip.startswith("172.18.")
                    or container_ip.startswith("172.19.")
                    or container_ip.startswith("10.0.")
                    or container_ip.startswith("192.168.")
                ):
                    logger.info(
                        f"自动检测到容器 IP: {container_ip}",
                        extra={"detection_method": "socket_connect"},
                    )
                    return container_ip
            except Exception:
                s.close()

            # 方法2: 尝试从环境变量 HOSTNAME 获取（某些 Docker 配置会设置）
            # 但这通常返回主机名而非 IP，所以不作为主要方法

        except Exception as e:
            # 如果获取失败，记录警告但继续使用默认值
            logger.debug(f"自动检测容器 IP 失败: {str(e)}")

        # Docker 环境：如果自动检测失败，建议通过环境变量配置
        # 注意：在 Docker Compose 中，最可靠的方式是通过 ipv4_address 配置
        # 并通过环境变量 SERVICE_IP 传递
        logger.warning(
            (
                "无法自动检测 Docker 容器 IP，建议在 docker-compose.yml 中配置 SERVICE_IP 环境变量。"
                "当前将使用 127.0.0.1（可能影响服务发现）"
            ),
            extra={"suggestion": "在 docker-compose.yml 中添加: SERVICE_IP: ${SERVICE_IP:-auto-detect-failed}"},
        )
        # 返回一个合理的默认值（虽然不理想，但至少不会失败）
        return "127.0.0.1"
    else:
        # 本地环境：使用 localhost
        return "127.0.0.1"
