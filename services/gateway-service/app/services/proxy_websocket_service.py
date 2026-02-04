"""Proxy service WebSocket module

Provides WebSocket proxy-related utility functions and constant definitions.

Extracted from proxy_service.py to improve code maintainability.

Note: Core WebSocket forwarding logic remains in ProxyService,
as it is tightly coupled with service discovery and connection management.
This module only provides independent utility functions.
"""

import os
import sys
from typing import Any, Dict, Optional

# Use try-except to handle path imports
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


# WebSocket related constants
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
    """Build WebSocket URL

    Args:
        service_url: Service URL (HTTP format)
        path: Request path
        use_wss: Whether to use WSS (secure WebSocket)

    Returns:
        str: WebSocket URL
    """
    # Remove HTTP protocol prefix
    if service_url.startswith("https://"):
        ws_protocol = "wss" if use_wss else "ws"
        ws_url = service_url.replace("https://", f"{ws_protocol}://")
    elif service_url.startswith("http://"):
        ws_protocol = "ws"
        ws_url = service_url.replace("http://", f"{ws_protocol}://")
    else:
        # Assume URL without protocol
        ws_protocol = "wss" if use_wss else "ws"
        ws_url = f"{ws_protocol}://{service_url}"

    # Add path
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
    """Format WebSocket log extra fields

    Args:
        service_name: Service name
        path: Request path
        connection_id: Connection ID
        session_key: Session key
        current_connections: Current connection count
        max_connections: Maximum connection count

    Returns:
        dict: Log extra fields
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
    """Generate WebSocket connection ID

    Args:
        service_name: Service name
        websocket: WebSocket object

    Returns:
        str: Connection ID
    """
    return f"{service_name}_{id(websocket)}"


def should_forward_message(message: Any) -> bool:
    """Determine if message should be forwarded

    Args:
        message: WebSocket message

    Returns:
        bool: Whether message should be forwarded
    """
    # Check message type
    if message is None:
        return False

    # If string or bytes, usually should forward
    if isinstance(message, (str, bytes)):
        return True

    # Other types need special handling
    return False


def get_close_reason(code: int) -> str:
    """Get WebSocket close reason description

    Args:
        code: Close code

    Returns:
        str: Close reason description
    """
    reasons = {
        WEBSOCKET_CLOSE_CODE_NORMAL: "Normal close",
        WEBSOCKET_CLOSE_CODE_GOING_AWAY: "Endpoint going away",
        WEBSOCKET_CLOSE_CODE_PROTOCOL_ERROR: "Protocol error",
        WEBSOCKET_CLOSE_CODE_UNSUPPORTED_DATA: "Unsupported data",
        WEBSOCKET_CLOSE_CODE_ABNORMAL: "Abnormal close",
        WEBSOCKET_CLOSE_CODE_POLICY_VIOLATION: "Policy violation",
    }
    return reasons.get(code, f"Unknown reason ({code})")


def is_connection_active(websocket: Any) -> bool:
    """Check if WebSocket connection is active

    Args:
        websocket: WebSocket object

    Returns:
        bool: Whether connection is active
    """
    try:
        # FastAPI/Starlette WebSocket
        from starlette.websockets import WebSocketState

        if hasattr(websocket, "client_state"):
            return websocket.client_state == WebSocketState.CONNECTED
        if hasattr(websocket, "application_state"):
            return websocket.application_state == WebSocketState.CONNECTED
    except ImportError:
        pass

    # websockets library
    if hasattr(websocket, "open"):
        return websocket.open

    # Default to active
    return True


def extract_session_key_from_path(path: str, pattern: str = r"/ws/(\w+)") -> Optional[str]:
    """Extract session key from path

    Args:
        path: WebSocket path
        pattern: Extraction pattern (regular expression)

    Returns:
        Optional[str]: Session key, returns None if not found
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
    """Build WebSocket request headers

    Args:
        original_headers: Original request headers
        additional_headers: Additional request headers
        excluded_headers: Headers to exclude

    Returns:
        Dict[str, str]: Processed request headers
    """
    if excluded_headers is None:
        excluded_headers = {"host", "connection", "upgrade", "sec-websocket-key", "sec-websocket-version"}

    headers: Dict[str, str] = {}

    # Copy original headers (exclude specific headers)
    if original_headers:
        for key, value in original_headers.items():
            if key.lower() not in excluded_headers:
                headers[key] = value

    # Add additional headers
    if additional_headers:
        headers.update(additional_headers)

    return headers


class WebSocketConnectionTracker:
    """WebSocket connection tracker

    Used to track and manage active WebSocket connections.
    """

    def __init__(self, max_connections: int = DEFAULT_MAX_WEBSOCKET_CONNECTIONS):
        """Initialize tracker

        Args:
            max_connections: Maximum connection count
        """
        self.max_connections = max_connections
        self.active_connections: Dict[str, Dict[str, Any]] = {}

    def can_accept(self) -> bool:
        """Check if new connection can be accepted

        Returns:
            bool: Whether connection can be accepted
        """
        return len(self.active_connections) < self.max_connections

    def register(
        self,
        connection_id: str,
        service_name: str,
        path: str,
    ) -> bool:
        """Register new connection

        Args:
            connection_id: Connection ID
            service_name: Service name
            path: Request path

        Returns:
            bool: Whether registration was successful
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
        """Unregister connection

        Args:
            connection_id: Connection ID

        Returns:
            bool: Whether unregistration was successful
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            return True
        return False

    def get_connection_count(self) -> int:
        """Get current connection count

        Returns:
            int: Current connection count
        """
        return len(self.active_connections)

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information

        Args:
            connection_id: Connection ID

        Returns:
            Optional[Dict[str, Any]]: Connection information, returns None if not found
        """
        return self.active_connections.get(connection_id)
