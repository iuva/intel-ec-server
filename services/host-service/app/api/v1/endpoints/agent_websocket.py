"""Agent WebSocket connection endpoint

Provides WebSocket connection interface for Agent
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Use try-except to handle path imports
try:
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import handle_websocket_auth_error, verify_websocket_token
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.websocket_auth import handle_websocket_auth_error, verify_websocket_token

from app.services.agent_websocket_manager import get_agent_websocket_manager

logger = get_logger(__name__)

router = APIRouter()


async def _handle_websocket_connection(websocket: WebSocket, path_host_id: Optional[str] = None):
    """WebSocket connection handling core logic

    Args:
        websocket: WebSocket connection object
        path_host_id: host_id from path (compatible with old API, actually not used)

    Note:
        - host_id is first obtained from query parameters (gateway verified)
        - Otherwise obtained from user_id/sub field in token (compatible with direct connection)
        - Authentication failure will return directly without establishing connection
        - Welcome message will be sent automatically after connection is established
    """
    ws_manager = get_agent_websocket_manager()
    logger.info(
        "WebSocket connection request",
        extra={
            "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            "path": websocket.url.path,
        },
    )

    # ✅ Step 1: Try to get host_id from query parameters (gateway verified case)
    host_id = websocket.query_params.get("host_id")
    user_info = None  # Initialize user_info

    if host_id:
        # ✅ Gateway has verified token, directly use host_id ***REMOVED***ed by gateway
        logger.info(
            "WebSocket connection using host_id ***REMOVED***ed by gateway",
            extra={
                "host_id": host_id,
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
        )
    else:
        # ✅ Compatible with direct connection: verify and extract host_id from token
        logger.info(
            "WebSocket connection direct connection, need to verify from token",
            extra={
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
        )

        is_valid, user_info = await verify_websocket_token(websocket)

        if not is_valid or not user_info:
            logger.warning("WebSocket authentication failed")
            await handle_websocket_auth_error(websocket, "Missing valid authentication token")
            return

        # ✅ Unified use of id field, return error if not present
        host_id = user_info.get("id")

        if not host_id:
            logger.warning("WebSocket token missing id")
            await handle_websocket_auth_error(websocket, "Token missing id")
            return

    # Convert to string (ensure type consistency)
    host_id = str(host_id)

    # ✅ Build log information (compatible with two authentication methods)
    log_extra = {
        "host_id": host_id,
        "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
    }

    # If user_info exists, add additional information
    if user_info:
        log_extra["user_type"] = user_info.get("user_type")
        log_extra["mg_id"] = user_info.get("mg_id")

    logger.info(
        "WebSocket authentication succeeded",
        extra=log_extra,
    )

    # ✅ Authentication succeeded, accept connection
    await websocket.accept()

    # ✅ Register connection
    # Record state before connection
    current_connections = ws_manager.get_connection_count()
    current_hosts = ws_manager.get_active_hosts()

    logger.info(
        "Preparing to register WebSocket connection",
        extra={
            "host_id": host_id,
            "current_connection_count": current_connections,
            "current_active_hosts": current_hosts,
            "is_already_connected": ws_manager.is_connected(host_id),
        },
    )

    await ws_manager.connect(host_id, websocket)

    # Record state after connection
    logger.info(
        "WebSocket connection registration completed",
        extra={
            "host_id": host_id,
            "new_connection_count": ws_manager.get_connection_count(),
            "new_active_hosts": ws_manager.get_active_hosts(),
        },
    )

    try:
        # ✅ Message loop - receive and process messages
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(host_id, data)

    except WebSocketDisconnect:
        logger.info("WebSocket normal disconnect", extra={"host_id": host_id})
        # ✅ Check if connection still exists to avoid duplicate disconnection
        if host_id in ws_manager.active_connections:
            await ws_manager.disconnect(host_id)
        else:
            logger.debug(
                "Connection already disconnected, skipping duplicate disconnect operation",
                extra={"host_id": host_id}
            )

    except Exception as e:
        logger.error(
            "WebSocket exception",
            extra={"host_id": host_id, "error": str(e)},
            exc_info=True,
        )
        # ✅ Check if connection still exists to avoid duplicate disconnection
        if host_id in ws_manager.active_connections:
            await ws_manager.disconnect(host_id)
        else:
            logger.debug(
                "Connection already disconnected, skipping duplicate disconnect operation",
                extra={"host_id": host_id}
            )


@router.websocket("/ws/host")
async def websocket_endpoint_new(websocket: WebSocket):
    """Host WebSocket connection endpoint (new version - recommended)

    Establish WebSocket connection, supports two authentication methods:
    1. Query parameter: ?token=xxx
    2. Request header: Authorization: Bearer xxx

    Note:
        - host_id is obtained from sub field in JWT token (host_rec.id stored during device login)
        - No longer need to ***REMOVED*** host_id through path parameters

    Args:
        websocket: WebSocket connection object
    """
    await _handle_websocket_connection(websocket)
