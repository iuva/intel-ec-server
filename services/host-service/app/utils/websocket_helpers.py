"""WebSocket message processing helper functions

Provides WebSocket message validation and other utility functions.
"""

from typing import Dict

from shared.common.exceptions import BusinessError, ServiceErrorCodes


def validate_websocket_message(message: Dict) -> None:
    """Validate WebSocket message format

    Args:
        message: WebSocket message dictionary

    Raises:
        BusinessError: Raises when message format is invalid (missing type field)
    """
    if not message.get("type"):
        raise BusinessError(
            message="Message must contain type field",
            message_key="error.websocket.invalid_message_format",
            error_code="INVALID_MESSAGE_FORMAT",
            code=ServiceErrorCodes.HOST_INVALID_REQUEST,
            http_status_code=400,
        )
