"""WebSocket 消息处理辅助函数

提供 WebSocket 消息验证等工具函数。
"""

from typing import Dict

from shared.common.exceptions import BusinessError, ServiceErrorCodes


def validate_websocket_message(message: Dict) -> None:
    """验证 WebSocket 消息格式

    Args:
        message: WebSocket 消息字典

    Raises:
        BusinessError: 消息格式错误时抛出（缺少 type 字段）
    """
    if not message.get("type"):
        raise BusinessError(
            message="消息必须包含 type 字段",
            message_key="error.websocket.invalid_message_format",
            error_code="INVALID_MESSAGE_FORMAT",
            code=ServiceErrorCodes.HOST_INVALID_REQUEST,
            http_status_code=400,
        )
