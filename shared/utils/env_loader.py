"""Environment Variable Loading Tool

Automatically loads .env files into environment variables,
ensuring that .env configurations can be read during local startup.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    # If python-dotenv is not installed, provide a dummy function
    def load_dotenv(*args, **kwargs) -> bool:
        """Fallback function when python-dotenv is not installed"""
        return False


def is_docker_environment() -> bool:
    """Detect if running in Docker environment

    Detection methods:
    1. Check if /.dockerenv file exists
    2. Check DOCKER_CONTAINER environment variable
    3. Check if /proc/1/cgroup contains docker keyword

    Returns:
        True if running in Docker, False otherwise
    """
    # Method 1: Check /.dockerenv file
    if Path("/.dockerenv").exists():
        return True

    # Method 2: Check environment variable
    if os.getenv("DOCKER_CONTAINER"):
        return True

    # Method 3: Check cgroup (Linux)
    try:
        cgroup_path = Path("/proc/1/cgroup")
        if cgroup_path.exists():
            content = cgroup_path.read_text()
            if "docker" in content or "kubepods" in content:
                return True
    except (OSError, PermissionError):
        ***REMOVED***

    return False


def load_env_file(env_file: Optional[str] = None) -> bool:
    """Load .env file into environment variables

    Search priority for .env files:
    1. Specified env_file path
    2. Automatically select .env.docker or .env.local based on environment
    3. .env file in project root directory (compatible with old config)
    4. .env file in current working directory

    Args:
        env_file: Path to .env file (optional)

    Returns:
        True if .env file is successfully loaded, False otherwise
    """
    env_paths = []

    # 1. If path is specified, use it first
    if env_file:
        env_paths.append(Path(env_file).resolve())

    # 2. Automatically select configuration file based on environment
    is_docker = is_docker_environment()
    auto_env_file = ".env.docker" if is_docker else ".env.local"

    # Search in project root directory (search up 5 levels)
    current_dir = Path.cwd()
    for _ in range(5):
        # Prioritize finding environment-specific config file
        auto_env_path = current_dir / auto_env_file
        if auto_env_path.exists():
            env_paths.append(auto_env_path.resolve())
            break

        # Compatible with old .env file
        env_path = current_dir / ".env"
        if env_path.exists():
            env_paths.append(env_path.resolve())
            break

        parent = current_dir.parent
        if parent == current_dir:  # Reached root directory
            break
        current_dir = parent

    # 3. .env in current directory
    env_paths.append(Path(".env").resolve())

    # Try to load the first existing file
    for env_path in env_paths:
        if env_path.exists() and env_path.is_file():
            try:
                load_dotenv(dotenv_path=env_path, override=False)
                return True
            except Exception:
                continue

    return False


def ensure_env_loaded() -> None:
    """Ensure .env file is loaded

    If there are no critical configurations in environment variables, try to load .env file.
    Only load when environment variables are not set, to avoid overwriting set values.
    """
    # Check if critical environment variables are already set
    key_vars = [
        "MARIADB_HOST",
        "MARIADB_USER",
        "REDIS_HOST",
        "NACOS_SERVER_ADDR",
    ]

    # If all critical variables are set, no need to load .env
    if all(os.getenv(var) for var in key_vars):
        return

    # Try to load .env file
    if load_env_file():
        # Verify if loaded successfully
        if any(os.getenv(var) for var in key_vars):
            return


# Automatically load when module is imported (optional)
# Note: This will load upon import, which may affect performance
# Recommended to explicitly call ensure_env_loaded() at application startup
_AUTO_LOAD = os.getenv("AUTO_LOAD_DOTENV", "false").lower() == "true"

if _AUTO_LOAD:
    ensure_env_loaded()
