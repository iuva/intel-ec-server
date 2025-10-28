"""WebSocket 消息协议定义

定义所有消息类型和格式规范
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """消息类型枚举"""

    # 连接管理
    WELCOME = "welcome"  # 连接建立欢迎消息
    HEARTBEAT = "heartbeat"  # Agent心跳
    HEARTBEAT_ACK = "heartbeat_ack"  # 心跳确认

    # 状态管理
    STATUS_UPDATE = "status_update"  # Agent状态更新
    STATUS_UPDATE_ACK = "status_update_ack"  # 状态更新确认

    # 命令执行
    COMMAND = "command"  # 执行命令
    COMMAND_RESPONSE = "command_response"  # 命令响应

    # 系统消息
    NOTIFICATION = "notification"  # 系统通知
    ERROR = "error"  # 错误消息
    HEARTBEAT_TIMEOUT_WARNING = "heartbeat_timeout_warning"  # 心跳超时警告


class BaseMessage(BaseModel):
    """基础消息格式

    所有消息都必须继承此类，确保包含基本字段
    """

    type: MessageType = Field(..., description="消息类型")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="消息时间戳"
    )
    message_id: Optional[str] = Field(default=None, description="消息ID（用于追踪）")

    model_config = {"from_attributes": True}


# ========== 连接管理消息 ==========


class WelcomeMessage(BaseMessage):
    """欢迎消息 - Server → Agent"""

    type: MessageType = Field(default=MessageType.WELCOME, description="消息类型")
    agent_id: str = Field(..., description="Agent ID")
    message: str = Field(default="WebSocket 连接已建立", description="欢迎消息")


class HeartbeatMessage(BaseMessage):
    """心跳消息 - Agent → Server"""

    type: MessageType = Field(default=MessageType.HEARTBEAT, description="消息类型")
    agent_id: str = Field(..., description="Agent ID")


class HeartbeatAckMessage(BaseMessage):
    """心跳确认 - Server → Agent"""

    type: MessageType = Field(default=MessageType.HEARTBEAT_ACK, description="消息类型")
    message: str = Field(default="心跳已接收", description="确认消息")


# ========== 状态管理消息 ==========


class StatusUpdateMessage(BaseMessage):
    """状态更新消息 - Agent → Server"""

    type: MessageType = Field(default=MessageType.STATUS_UPDATE, description="消息类型")
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="新状态 (online/offline/busy/error)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="状态详情")


class StatusUpdateAckMessage(BaseMessage):
    """状态更新确认 - Server → Agent"""

    type: MessageType = Field(default=MessageType.STATUS_UPDATE_ACK, description="消息类型")
    message: str = Field(default="状态更新成功", description="确认消息")
    status: str = Field(..., description="更新后的状态")


# ========== 命令执行消息 ==========


class CommandMessage(BaseMessage):
    """命令消息 - Server → Agent

    用于通知Agent执行特定命令
    """

    type: MessageType = Field(default=MessageType.COMMAND, description="消息类型")
    command_id: str = Field(..., description="命令ID（唯一标识）")
    command: str = Field(..., description="命令名称")
    args: Optional[Dict[str, Any]] = Field(default=None, description="命令参数")
    target_agents: Optional[list[str]] = Field(default=None, description="目标Agent列表（None表示所有）")


class CommandResponseMessage(BaseMessage):
    """命令响应 - Agent → Server

    Agent执行命令后返回的结果
    """

    type: MessageType = Field(default=MessageType.COMMAND_RESPONSE, description="消息类型")
    agent_id: str = Field(..., description="Agent ID")
    command_id: str = Field(..., description="对应的命令ID")
    result: Optional[Dict[str, Any]] = Field(default=None, description="命令执行结果")
    error: Optional[str] = Field(default=None, description="错误信息（如果执行失败）")
    success: bool = Field(..., description="命令是否执行成功")


# ========== 系统消息 ==========


class NotificationMessage(BaseMessage):
    """系统通知 - Server → Agent/Broadcast

    用于向Agent或所有连接的Agents发送通知
    """

    type: MessageType = Field(default=MessageType.NOTIFICATION, description="消息类型")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    level: str = Field(default="info", description="通知级别 (info/warning/error/critical)")
    data: Optional[Dict[str, Any]] = Field(default=None, description="附加数据")


class ErrorMessage(BaseMessage):
    """错误消息 - Server → Agent"""

    type: MessageType = Field(default=MessageType.ERROR, description="消息类型")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误码")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")


class HeartbeatTimeoutWarningMessage(BaseMessage):
    """心跳超时警告 - Server → Agent"""

    type: MessageType = Field(default=MessageType.HEARTBEAT_TIMEOUT_WARNING, description="消息类型")
    message: str = Field(default="心跳超时警告", description="警告消息")
    timeout: int = Field(..., description="心跳超时时间（秒）")


# 消息类型映射
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
}


def parse_message(data: Dict[str, Any]) -> Optional[BaseMessage]:
    """解析JSON数据为对应的消息类型

    Args:
        data: 原始消息数据

    Returns:
        解析后的消息对象，如果类型无效则返回None
    """
    try:
        msg_type_str = data.get("type")
        if not msg_type_str:
            return None

        # 尝试转换为MessageType枚举
        msg_type = MessageType(msg_type_str)

        # 根据类型获取对应的消息类
        message_class = MESSAGE_TYPE_MAP.get(msg_type)
        if not message_class:
            return None

        # 解析消息
        return message_class(**data)

    except (ValueError, KeyError, TypeError):
        return None
