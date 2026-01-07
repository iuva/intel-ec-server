"""代理服务 WebSocket 模块

提供 WebSocket 代理相关的工具函数和常量定义。

从 proxy_service.py 拆分出来，提高代码可维护性。

注意：核心 WebSocket 转发逻辑仍保留在 ProxyService 中，
因为它与服务发现和连接管理紧密耦合。此模块仅提供独立的工具函数。
"""

import os
import sys
from typing import Any, Dict, Optional

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# WebSocket 相关常量
DEFAULT_MAX_WEBSOCKET_CONNECTIONS = 1000
WEBSOCKET_CLOSE_CODE_NORMAL = 1000
WEBSOCKET_CLOSE_CODE_GOING_AWAY = 1001
WEBSOCKET_CLOSE_CODE_PROTOCOL_ERROR = 1002
WEBSOCKET_CLOSE_CODE_UNSUPPORTED_DATA = 1003
WEBSOCKET_CLOSE_CODE_ABNORMAL = 1006
WEBSOCKET_CLOSE_CODE_POLICY_VIOLATION = 1008


def build_websocket_url(
    service_url: str,
    path: str,
    use_wss: bool = False,
) -> str:
    """构建 WebSocket URL

    Args:
        service_url: 服务 URL（HTTP 格式）
        path: 请求路径
        use_wss: 是否使用 WSS（安全 WebSocket）

    Returns:
        str: WebSocket URL
    """
    # 移除 HTTP 协议前缀
    if service_url.startswith("https://"):
        ws_protocol = "wss" if use_wss else "ws"
        ws_url = service_url.replace("https://", f"{ws_protocol}://")
    elif service_url.startswith("http://"):
        ws_protocol = "ws"
        ws_url = service_url.replace("http://", f"{ws_protocol}://")
    else:
        # 假设是没有协议的 URL
        ws_protocol = "wss" if use_wss else "ws"
        ws_url = f"{ws_protocol}://{service_url}"

    # 添加路径
    if not path.startswith("/"):
        path = f"/{path}"

    return f"{ws_url}{path}"


def format_websocket_log_extra(
    service_name: str,
    path: str,
    connection_id: Optional[str] = None,
    session_key: Optional[str] = None,
    current_connections: int = 0,
    max_connections: int = DEFAULT_MAX_WEBSOCKET_CONNECTIONS,
) -> dict:
    """格式化 WebSocket 日志的 extra 字段

    Args:
        service_name: 服务名称
        path: 请求路径
        connection_id: 连接 ID
        session_key: 会话键
        current_connections: 当前连接数
        max_connections: 最大连接数

    Returns:
        dict: 日志 extra 字段
    """
    return {
        "service_name": service_name,
        "path": path,
        "connection_id": connection_id,
        "session_key": session_key,
        "current_connections": current_connections,
        "max_connections": max_connections,
    }


def generate_connection_id(service_name: str, websocket: Any) -> str:
    """生成 WebSocket 连接 ID

    Args:
        service_name: 服务名称
        websocket: WebSocket 对象

    Returns:
        str: 连接 ID
    """
    return f"{service_name}_{id(websocket)}"


def should_forward_message(message: Any) -> bool:
    """判断消息是否应该转发

    Args:
        message: WebSocket 消息

    Returns:
        bool: 是否应该转发
    """
    # 检查消息类型
    if message is None:
        return False

    # 如果是字符串或字节，通常应该转发
    if isinstance(message, (str, bytes)):
        return True

    # 其他类型需要特殊处理
    return False


def get_close_reason(code: int) -> str:
    """获取 WebSocket 关闭原因描述

    Args:
        code: 关闭代码

    Returns:
        str: 关闭原因描述
    """
    reasons = {
        WEBSOCKET_CLOSE_CODE_NORMAL: "正常关闭",
        WEBSOCKET_CLOSE_CODE_GOING_AWAY: "端点离开",
        WEBSOCKET_CLOSE_CODE_PROTOCOL_ERROR: "协议错误",
        WEBSOCKET_CLOSE_CODE_UNSUPPORTED_DATA: "不支持的数据",
        WEBSOCKET_CLOSE_CODE_ABNORMAL: "异常关闭",
        WEBSOCKET_CLOSE_CODE_POLICY_VIOLATION: "策略违规",
    }
    return reasons.get(code, f"未知原因 ({code})")


def is_connection_active(websocket: Any) -> bool:
    """检查 WebSocket 连接是否活跃

    Args:
        websocket: WebSocket 对象

    Returns:
        bool: 是否活跃
    """
    try:
        # FastAPI/Starlette WebSocket
        from starlette.websockets import WebSocketState
        if hasattr(websocket, "client_state"):
            return websocket.client_state == WebSocketState.CONNECTED
        if hasattr(websocket, "application_state"):
            return websocket.application_state == WebSocketState.CONNECTED
    except ImportError:
        ***REMOVED***

    # websockets 库
    if hasattr(websocket, "open"):
        return websocket.open

    # 默认认为活跃
    return True


def extract_session_key_from_path(path: str, pattern: str = r"/ws/(\w+)") -> Optional[str]:
    """从路径中提取会话键

    Args:
        path: WebSocket 路径
        pattern: 提取模式（正则表达式）

    Returns:
        Optional[str]: 会话键，如果未找到则返回 None
    """
    import re

    match = re.search(pattern, path)
    if match:
        return match.group(1)
    return None


def build_websocket_headers(
    original_headers: Optional[Dict[str, str]] = None,
    additional_headers: Optional[Dict[str, str]] = None,
    excluded_headers: Optional[set] = None,
) -> Dict[str, str]:
    """构建 WebSocket 请求头

    Args:
        original_headers: 原始请求头
        additional_headers: 额外请求头
        excluded_headers: 需要排除的请求头

    Returns:
        Dict[str, str]: 处理后的请求头
    """
    if excluded_headers is None:
        excluded_headers = {"host", "connection", "upgrade", "sec-websocket-key", "sec-websocket-version"}

    headers: Dict[str, str] = {}

    # 复制原始请求头（排除特定头）
    if original_headers:
        for key, value in original_headers.items():
            if key.lower() not in excluded_headers:
                headers[key] = value

    # 添加额外请求头
    if additional_headers:
        headers.update(additional_headers)

    return headers


class WebSocketConnectionTracker:
    """WebSocket 连接跟踪器

    用于跟踪和管理活跃的 WebSocket 连接。
    """

    def __init__(self, max_connections: int = DEFAULT_MAX_WEBSOCKET_CONNECTIONS):
        """初始化跟踪器

        Args:
            max_connections: 最大连接数
        """
        self.max_connections = max_connections
        self.active_connections: Dict[str, Dict[str, Any]] = {}

    def can_accept(self) -> bool:
        """检查是否可以接受新连接

        Returns:
            bool: 是否可以接受
        """
        return len(self.active_connections) < self.max_connections

    def register(
        self,
        connection_id: str,
        service_name: str,
        path: str,
    ) -> bool:
        """注册新连接

        Args:
            connection_id: 连接 ID
            service_name: 服务名称
            path: 请求路径

        Returns:
            bool: 是否成功注册
        """
        if not self.can_accept():
            return False

        import asyncio
        self.active_connections[connection_id] = {
            "service_name": service_name,
            "path": path,
            "created_at": asyncio.get_event_loop().time(),
        }
        return True

    def unregister(self, connection_id: str) -> bool:
        """注销连接

        Args:
            connection_id: 连接 ID

        Returns:
            bool: 是否成功注销
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            return True
        return False

    def get_connection_count(self) -> int:
        """获取当前连接数

        Returns:
            int: 当前连接数
        """
        return len(self.active_connections)

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息

        Args:
            connection_id: 连接 ID

        Returns:
            Optional[Dict[str, Any]]: 连接信息，如果不存在则返回 None
        """
        return self.active_connections.get(connection_id)
