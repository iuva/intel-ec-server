"""Agent WebSocket management HTTP API endpoints

Provides HTTP interfaces for Agent WebSocket connection management and message sending
"""

import os
import sys
from typing import Dict, List

from fastapi import APIRouter, Depends, Path, Query

# Use try-except to handle path imports
try:
    from app.utils.websocket_helpers import validate_websocket_message

    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.utils.websocket_helpers import validate_websocket_message

    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

from app.services.agent_websocket_manager import get_agent_websocket_manager

logger = get_logger(__name__)

router = APIRouter()


# ========== Connection management endpoints ==========


@router.get("/ws/hosts")
async def get_active_hosts(locale: str = Depends(get_locale)):
    """Get all actively connected Host IDs

    Returns:
        Active Host list and total count

    Example:
        ```
        GET /api/v1/ws/hosts
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "Get active Hosts succeeded",
            "data": {
                "hosts": ["1846486359367955051", "1846486359367955052"],
                "count": 2
            }
        }
        ```
    """
    ws_manager = get_agent_websocket_manager()
    hosts = ws_manager.get_active_hosts()

    logger.info("Query active Host list", extra={"host_count": len(hosts)})

    return SuccessResponse(
        data={"hosts": hosts, "count": len(hosts)},
        message_key="success.websocket.get_active_hosts",
        locale=locale,
    )


@router.get("/ws/status/{host_id}")
async def get_host_status(
    host_id: str = Path(..., description="Host ID (host_rec.id)"),
    locale: str = Depends(get_locale),
):
    """Check Host connection status

    Args:
        host_id: Host ID

    Returns:
        Connection status information

    Example:
        ```
        GET /api/v1/ws/status/1846486359367955051
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "Get Host status succeeded",
            "data": {
                "host_id": "1846486359367955051",
                "connected": true
            }
        }
        ```
    """
    ws_manager = get_agent_websocket_manager()
    is_connected = ws_manager.is_connected(host_id)

    logger.debug("Query Host connection status", extra={"host_id": host_id, "is_connected": is_connected})

    return SuccessResponse(
        data={"host_id": host_id, "connected": is_connected},
        message_key="success.websocket.get_host_status",
        locale=locale,
    )


# ========== Message sending endpoints ==========


@router.post("/ws/send/{host_id}")
async def send_message_to_host(
    host_id: str = Path(..., description="Host ID (host_rec.id)"),
    message: Dict = ...,
    locale: str = Depends(get_locale),
):
    """Send message to specified Host

    Args:
        host_id: Target Host ID
        message: Message content (must include type field)

    Returns:
        Send result

    Raises:
        BusinessError: Message format error (missing type field)

    Example:
        ```
        POST /api/v1/ws/send/1846486359367955051
        {
            "type": "command",
            "command_id": "cmd_123",
            "command": "restart",
            "args": {"service": "nginx"}
        }
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "Message sent successfully",
            "data": {
                "host_id": "1846486359367955051",
                "success": true
            }
        }
        ```
    """
    # Validate message format
    validate_websocket_message(message)

    ws_manager = get_agent_websocket_manager()
    success = await ws_manager.send_to_host(host_id, message)

    if success:
        logger.info("Message sent to Host", extra={"host_id": host_id, "message_type": message.get("type")})
    else:
        logger.warning("Message send failed (Host not connected)", extra={"host_id": host_id})

    if success:
        return SuccessResponse(
            data={"host_id": host_id, "success": success},
            message_key="success.websocket.message_sent",
            locale=locale,
        )
    else:
        return SuccessResponse(
            data={"host_id": host_id, "success": success},
            message_key="error.websocket.host_not_connected",
            locale=locale,
        )


@router.post("/ws/send-to-hosts")
async def send_message_to_hosts(
    host_ids: List[str],
    message: Dict,
    locale: str = Depends(get_locale),
):
    """Send message to specified multiple Hosts (multicast)

    Args:
        host_ids: Target Host ID list
        message: Message content (must include type field)

    Returns:
        Send result statistics

    Raises:
        BusinessError: Message format error (missing type field)

    Example:
        ```
        POST /api/v1/ws/send-to-hosts
        {
            "host_ids": ["1846486359367955051", "1846486359367955052"],
            "message": {
                "type": "notification",
                "message": "System maintenance notification",
                "data": {"maintenance_time": "2025-10-28 22:00:00"}
            }
        }
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "Message sending completed (2/2 succeeded)",
            "data": {
                "target_count": 2,
                "success_count": 2,
                "failed_count": 0
            }
        }
        ```
    """
    # Validate message format
    validate_websocket_message(message)

    ws_manager = get_agent_websocket_manager()
    success_count = await ws_manager.send_to_hosts(host_ids, message)

    logger.info(
        "Multicast message completed",
        extra={
            "target_count": len(host_ids),
            "success_count": success_count,
            "message_type": message.get("type"),
        },
    )

    return SuccessResponse(
        data={
            "target_count": len(host_ids),
            "success_count": success_count,
            "failed_count": len(host_ids) - success_count,
        },
        message_key="success.websocket.broadcast_complete",
        locale=locale,
        success_count=success_count,
        target_count=len(host_ids),
    )


@router.post("/ws/broadcast")
async def broadcast_message(
    message: Dict,
    exclude_host_id: str = Query(None, description="Excluded Host ID"),
    locale: str = Depends(get_locale),
):
    """Broadcast message to all connected Hosts

    Args:
        message: Message content (must include type field)
        exclude_host_id: Excluded Host ID (optional)

    Returns:
        Broadcast result statistics

    Raises:
        BusinessError: Message format error (missing type field)

    Example:
        ```
        POST /api/v1/ws/broadcast?exclude_host_id=1846486359367955051
        {
            "type": "notification",
            "message": "System update notification",
            "data": {"version": "2.0.0"}
        }
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "Broadcast completed (99/100 succeeded)",
            "data": {
                "total_count": 100,
                "success_count": 99,
                "failed_count": 1
            }
        }
        ```
    """
    # Validate message format
    validate_websocket_message(message)

    ws_manager = get_agent_websocket_manager()
    success_count = await ws_manager.broadcast(message, exclude=exclude_host_id)
    total_count = ws_manager.get_connection_count()

    logger.info(
        "Broadcast message completed",
        extra={
            "target_count": total_count,
            "success_count": success_count,
            "exclude_host_id": exclude_host_id or "None",
            "message_type": message.get("type"),
        },
    )

    return SuccessResponse(
        data={
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": total_count - success_count,
            "exclude_host_id": exclude_host_id,
        },
        message_key="success.websocket.broadcast_complete",
        locale=locale,
        success_count=success_count,
        total_count=total_count,
    )


# ========== Host offline notification endpoints ==========


@router.post("/ws/notify-offline/{host_id}")
async def notify_host_offline(
    host_id: str = Path(..., description="Host ID (host_rec.id)"),
    reason: str = Query(None, description="Offline reason"),
    locale: str = Depends(get_locale),
):
    """Notify specified Host to go offline

    Server actively notifies Agent that its Host has gone offline, after Agent receives:
    1. Query the latest record in host_exec_log table (del_flag=0)
    2. Update host_state to 4 (offline status)

    Args:
        host_id: Target Host ID
        reason: Offline reason (optional)

    Returns:
        Notification send result

    Raises:
        BusinessError: Host not connected

    Example:
        ```
        POST /api/v1/ws/notify-offline/1846486359367955051?reason=System maintenance
        ```

    Response:
        ```json
        {
            "code": 200,
            "message": "Host offline notification sent",
            "data": {
                "host_id": "1846486359367955051",
                "success": true,
                "reason": "System maintenance"
            }
        }
        ```
    """
    ws_manager = get_agent_websocket_manager()

    # Check if Host is connected
    if not ws_manager.is_connected(host_id):
        logger.warning("Host not connected, cannot send offline notification", extra={"host_id": host_id})
        raise BusinessError(
            message=f"Host not connected: {host_id}",
            message_key="error.host.not_connected",
            error_code="HOST_NOT_CONNECTED",
            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
            http_status_code=400,
            details={"host_id": host_id},
        )

    # Build offline notification message
    offline_message = {
        "type": "host_offline_notification",
        "host_id": host_id,
        "message": "Host has gone offline",
        "reason": reason or "Reason not specified",
    }

    # Send message
    success = await ws_manager.send_to_host(host_id, offline_message)

    if success:
        logger.info(
            "Host offline notification sent",
            extra={"host_id": host_id, "reason": reason or "Reason not specified"}
        )
    else:
        logger.warning("Host offline notification send failed", extra={"host_id": host_id})
        raise BusinessError(
            message=f"Send offline notification failed: {host_id}",
            error_code="SEND_NOTIFICATION_FAILED",
            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
            http_status_code=500,
        )

    return SuccessResponse(
        data={"host_id": host_id, "success": success, "reason": reason or "Reason not specified"},
        message_key="success.websocket.offline_notification_sent",
        locale=locale,
    )
