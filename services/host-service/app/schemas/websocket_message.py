"""WebSocket message protocol definitions

Defines all message types and format specifications
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message type enumeration"""

    # Connection management
    WELCOME = "welcome"  # Connection established welcome message
    HEARTBEAT = "heartbeat"  # Agent heartbeat
    HEARTBEAT_ACK = "heartbeat_ack"  # Heartbeat acknowledgment

    # Status management
    STATUS_UPDATE = "status_update"  # Agent status update
    STATUS_UPDATE_ACK = "status_update_ack"  # Status update acknowledgment

    # Command execution
    COMMAND = "command"  # Execute command
    COMMAND_RESPONSE = "command_response"  # Command response
    CONNECTION_RESULT = "connection_result"  # Agent reports connection result

    # System messages
    NOTIFICATION = "notification"  # System notification
    ERROR = "error"  # Error message
    HEARTBEAT_TIMEOUT_WARNING = "heartbeat_timeout_warning"  # Heartbeat timeout warning
    HOST_OFFLINE_NOTIFICATION = "host_offline_notification"  # Host offline notification
    CONNECTION_NOTIFICATION = "connection_notification"  # Connection notification (notify Agent to start
    # log monitoring when VNC connection succeeds)
    VERSION_UPDATE = "version_update"  # Agent version update


class BaseMessage(BaseModel):
    """Base message format

    All messages must inherit from this class to ensure basic fields are included
    """

    type: MessageType = Field(..., description="Message type")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Message timestamp"
    )
    message_id: Optional[str] = Field(default=None, description="Message ID (for tracking)")

    model_config = {"from_attributes": True}


# ========== Connection management messages ==========


class WelcomeMessage(BaseMessage):
    """Welcome message - Server → Agent"""

    type: MessageType = Field(default=MessageType.WELCOME, description="Message type")
    agent_id: str = Field(..., description="Agent ID")
    message: str = Field(default="WebSocket connection established", description="Welcome message")


class HeartbeatMessage(BaseMessage):
    """Heartbeat message - Agent → Server"""

    type: MessageType = Field(default=MessageType.HEARTBEAT, description="Message type")
    agent_id: str = Field(..., description="Agent ID")


class HeartbeatAckMessage(BaseMessage):
    """Heartbeat acknowledgment - Server → Agent"""

    type: MessageType = Field(default=MessageType.HEARTBEAT_ACK, description="Message type")
    message: str = Field(default="Heartbeat received", description="Acknowledgment message")


# ========== Status management messages ==========


class StatusUpdateMessage(BaseMessage):
    """Status update message - Agent → Server"""

    type: MessageType = Field(default=MessageType.STATUS_UPDATE, description="Message type")
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="New status (online/offline/busy/error)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Status details")


class StatusUpdateAckMessage(BaseMessage):
    """Status update acknowledgment - Server → Agent"""

    type: MessageType = Field(default=MessageType.STATUS_UPDATE_ACK, description="Message type")
    message: str = Field(default="Status update succeeded", description="Acknowledgment message")
    status: str = Field(..., description="Updated status")


# ========== Command execution messages ==========


class CommandMessage(BaseMessage):
    """Command message - Server → Agent

    Used to notify Agent to execute specific command
    """

    type: MessageType = Field(default=MessageType.COMMAND, description="Message type")
    command_id: str = Field(..., description="Command ID (unique identifier)")
    command: str = Field(..., description="Command name")
    args: Optional[Dict[str, Any]] = Field(default=None, description="Command arguments")
    target_agents: Optional[List[str]] = Field(default=None, description="Target Agent list (None means all)")


class CommandResponseMessage(BaseMessage):
    """Command response - Agent → Server

    Result returned by Agent after executing command
    """

    type: MessageType = Field(default=MessageType.COMMAND_RESPONSE, description="Message type")
    agent_id: str = Field(..., description="Agent ID")
    command_id: str = Field(..., description="Corresponding command ID")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Command execution result")
    error: Optional[str] = Field(default=None, description="Error information (if execution failed)")
    success: bool = Field(..., description="Whether command execution succeeded")


# ========== System messages ==========


class NotificationMessage(BaseMessage):
    """System notification - Server → Agent/Broadcast

    Used to send notifications to Agent or all connected Agents
    """

    type: MessageType = Field(default=MessageType.NOTIFICATION, description="Message type")
    title: str = Field(..., description="Notification title")
    content: str = Field(..., description="Notification content")
    level: str = Field(default="info", description="Notification level (info/warning/error/critical)")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")


class ErrorMessage(BaseMessage):
    """Error message - Server → Agent"""

    type: MessageType = Field(default=MessageType.ERROR, description="Message type")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")


class HeartbeatTimeoutWarningMessage(BaseMessage):
    """Heartbeat timeout warning - Server → Agent"""

    type: MessageType = Field(default=MessageType.HEARTBEAT_TIMEOUT_WARNING, description="Message type")
    message: str = Field(default="Heartbeat timeout warning", description="Warning message")
    timeout: int = Field(..., description="Heartbeat timeout time (seconds)")


class HostOfflineNotificationMessage(BaseMessage):
    """Host offline notification - Server → Agent

    Notify Agent that its Host has gone offline, Agent needs to update
    host_exec_log table host_state to 4 after receiving

    """

    type: MessageType = Field(default=MessageType.HOST_OFFLINE_NOTIFICATION, description="Message type")
    host_id: str = Field(..., description="Host ID")
    message: str = Field(default="Host has gone offline", description="Offline message")
    reason: Optional[str] = Field(default=None, description="Offline reason")


class ConnectionNotificationMessage(BaseMessage):
    """Connection notification - Server → Agent

    When browser VNC connection succeeds, notify Agent to start log monitoring
    """

    type: MessageType = Field(default=MessageType.CONNECTION_NOTIFICATION, description="Message type")
    host_id: str = Field(..., description="Host ID")
    message: str = Field(
        default="VNC connection succeeded, please start log monitoring", description="Notification message"
    )
    action: str = Field(default="start_log_monitoring", description="Action type (start_log_monitoring)")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional information (such as user ID, test ID, etc.)"
    )


class VersionUpdateMessage(BaseMessage):
    """Version update message - Agent → Server

    Agent reports current version number, used to update agent_ver field in host_rec table

    Note:
        - agent_id is obtained from token when WebSocket connects, doesn't need to be ***REMOVED***ed in message
        - Message only needs to contain version field
    """

    type: MessageType = Field(default=MessageType.VERSION_UPDATE, description="Message type")
    version: str = Field(..., max_length=10, description="Agent version number")


# Message type mapping
MESSAGE_TYPE_MAP = {
    MessageType.WELCOME: WelcomeMessage,
    MessageType.HEARTBEAT: HeartbeatMessage,
    MessageType.HEARTBEAT_ACK: HeartbeatAckMessage,
    MessageType.STATUS_UPDATE: StatusUpdateMessage,
    MessageType.STATUS_UPDATE_ACK: StatusUpdateAckMessage,
    MessageType.COMMAND: CommandMessage,
    MessageType.COMMAND_RESPONSE: CommandResponseMessage,
    MessageType.NOTIFICATION: NotificationMessage,
    MessageType.ERROR: ErrorMessage,
    MessageType.HEARTBEAT_TIMEOUT_WARNING: HeartbeatTimeoutWarningMessage,
    MessageType.HOST_OFFLINE_NOTIFICATION: HostOfflineNotificationMessage,
    MessageType.CONNECTION_NOTIFICATION: ConnectionNotificationMessage,
    MessageType.VERSION_UPDATE: VersionUpdateMessage,
}


def parse_message(data: Dict[str, Any]) -> Optional[BaseMessage]:
    """Parse JSON data into corresponding message type

    Args:
        data: Raw message data

    Returns:
        Parsed message object, returns None if type is invalid
    """
    try:
        msg_type_str = data.get("type")
        if not msg_type_str:
            return None

        # Try to convert to MessageType enum
        msg_type = MessageType(msg_type_str)

        # Get corresponding message class based on type
        message_class = MESSAGE_TYPE_MAP.get(msg_type)
        if not message_class:
            return None

        # Parse message
        return message_class(**data)

    except (ValueError, KeyError, TypeError):
        return None
