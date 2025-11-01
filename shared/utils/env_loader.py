"""环境变量加载工具

自动加载 .env 文件到环境变量中，确保本地启动时能够读取 .env 配置。
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    # 如果没有安装 python-dotenv，提供空函数
    def load_dotenv(*args, **kwargs):  # type: ignore
        ***REMOVED***


def load_env_file(env_file: Optional[str] = None) -> bool:
    """加载 .env 文件到环境变量

    优先查找以下位置的 .env 文件：
    1. 指定的 env_file 路径
    2. 项目根目录的 .env 文件
    3. 当前工作目录的 .env 文件

    Args:
        env_file: .env 文件路径（可选）

    Returns:
        是否成功加载 .env 文件
    """
    env_paths = []

    # 1. 如果指定了路径，优先使用
    if env_file:
        env_paths.append(Path(env_file).resolve())

    # 2. 查找项目根目录的 .env（向上查找最多 5 层）
    current_dir = Path.cwd()
    for _ in range(5):
        env_path = current_dir / ".env"
        if env_path.exists():
            env_paths.append(env_path.resolve())
            break
        parent = current_dir.parent
        if parent == current_dir:  # 已到达根目录
            break
        current_dir = parent

    # 3. 当前目录的 .env
    env_paths.append(Path(".env").resolve())

    # 尝试加载第一个存在的文件
    for env_path in env_paths:
        if env_path.exists() and env_path.is_file():
            try:
                load_dotenv(dotenv_path=env_path, override=False)
                return True
            except Exception:
                continue

    return False


def ensure_env_loaded() -> None:
    """确保 .env 文件已加载

    如果环境变量中没有关键配置，尝试加载 .env 文件。
    只在未设置环境变量时才加载，避免覆盖已设置的值。
    """
    # 检查是否已设置关键环境变量
    key_vars = [
        "MARIADB_HOST",
        "MARIADB_USER",
        "REDIS_HOST",
        "NACOS_SERVER_ADDR",
    ]

    # 如果所有关键变量都已设置，不需要加载 .env
    if all(os.getenv(var) for var in key_vars):
        return

    # 尝试加载 .env 文件
    if load_env_file():
        # 验证是否成功加载
        if any(os.getenv(var) for var in key_vars):
            return


# 在模块导入时自动加载（可选）
# 注意：这会在导入时就加载，可能会影响性能
# 建议在应用启动时显式调用 ensure_env_loaded()
_AUTO_LOAD = os.getenv("AUTO_LOAD_DOTENV", "false").lower() == "true"

if _AUTO_LOAD:
    ensure_env_loaded()

