"""WebSocket 连接管理器"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.services.host_service import HostService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        """初始化 WebSocket 管理器"""
        # 存储活跃连接: {agent_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储心跳任务: {agent_id: Task}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        # 心跳超时时间（秒）
        self.heartbeat_timeout = 60
        # 主机服务实例
        self.host_service = HostService()

    async def connect(self, agent_id: str, websocket: WebSocket) -> None:
        """建立 WebSocket 连接

        Args:
            agent_id: Agent ID
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.active_connections[agent_id] = websocket

        logger.info(f"Agent 连接成功: {agent_id}, 当前连接数: {len(self.active_connections)}")

        # 发送欢迎消息
        await self.send_message(
            agent_id,
            {
                "type": "welcome",
                "message": "WebSocket 连接已建立",
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # 启动心跳检测任务
        self.heartbeat_tasks[agent_id] = asyncio.create_task(self._heartbeat_monitor(agent_id))

    async def disconnect(self, agent_id: str) -> None:
        """断开 WebSocket 连接

        Args:
            agent_id: Agent ID
        """
        # 取消心跳检测任务
        if agent_id in self.heartbeat_tasks:
            self.heartbeat_tasks[agent_id].cancel()
            del self.heartbeat_tasks[agent_id]

        # 移除连接
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]

        # 更新主机状态为离线
        try:
            from app.schemas.host import HostStatusUpdate

            await self.host_service.update_host_status(agent_id, HostStatusUpdate(status="offline"))
        except Exception as e:
            logger.error(f"更新主机状态失败: {agent_id}, 错误: {e!s}")

        logger.info(f"Agent 断开连接: {agent_id}, 当前连接数: {len(self.active_connections)}")

    async def send_message(self, agent_id: str, message: dict) -> bool:
        """发送消息给指定 Agent

        Args:
            agent_id: Agent ID
            message: 消息内容（字典）

        Returns:
            是否发送成功
        """
        if agent_id not in self.active_connections:
            logger.warning(f"Agent 未连接: {agent_id}")
            return False

        try:
            websocket = self.active_connections[agent_id]
            await websocket.send_json(message)
            logger.debug(f"消息发送成功: {agent_id}, 类型: {message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"消息发送失败: {agent_id}, 错误: {e!s}")
            await self.disconnect(agent_id)
            return False

    async def broadcast(self, message: dict, exclude: Optional[str] = None) -> int:
        """广播消息给所有连接的 Agent

        Args:
            message: 消息内容（字典）
            exclude: 排除的 Agent ID

        Returns:
            成功发送的数量
        """
        success_count = 0
        failed_agents = []

        for agent_id in list(self.active_connections.keys()):
            if exclude and agent_id == exclude:
                continue

            if await self.send_message(agent_id, message):
                success_count += 1
            else:
                failed_agents.append(agent_id)

        if failed_agents:
            logger.warning(f"广播失败的 Agent: {failed_agents}")

        logger.info(f"消息广播完成: 成功 {success_count}/{len(self.active_connections)}")
        return success_count

    async def handle_message(self, agent_id: str, data: dict) -> None:
        """处理接收到的消息

        Args:
            agent_id: Agent ID
            data: 消息数据
        """
        message_type = data.get("type", "unknown")
        logger.debug(f"收到消息: {agent_id}, 类型: {message_type}")

        try:
            if message_type == "heartbeat":
                await self._handle_heartbeat(agent_id, data)
            elif message_type == "status_update":
                await self._handle_status_update(agent_id, data)
            elif message_type == "command_response":
                await self._handle_command_response(agent_id, data)
            else:
                logger.warning(f"未知消息类型: {message_type}, Agent: {agent_id}")
                await self.send_message(
                    agent_id,
                    {
                        "type": "error",
                        "message": f"未知消息类型: {message_type}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception as e:
            logger.error(f"处理消息异常: {agent_id}, 错误: {e!s}")
            await self.send_message(
                agent_id,
                {
                    "type": "error",
                    "message": "消息处理失败",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    async def _handle_heartbeat(self, agent_id: str, data: dict) -> None:
        """处理心跳消息

        Args:
            agent_id: Agent ID
            data: 心跳数据
        """
        try:
            # 更新主机心跳时间
            await self.host_service.update_heartbeat(agent_id)

            # 发送心跳响应
            await self.send_message(
                agent_id,
                {
                    "type": "heartbeat_ack",
                    "message": "心跳已接收",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.debug(f"心跳处理成功: {agent_id}")
        except Exception as e:
            logger.error(f"心跳处理失败: {agent_id}, 错误: {e!s}")

    async def _handle_status_update(self, agent_id: str, data: dict) -> None:
        """处理状态更新消息

        Args:
            agent_id: Agent ID
            data: 状态数据
        """
        try:
            status = data.get("status", "online")
            from app.schemas.host import HostStatusUpdate

            await self.host_service.update_host_status(agent_id, HostStatusUpdate(status=status))

            await self.send_message(
                agent_id,
                {
                    "type": "status_update_ack",
                    "message": "状态更新成功",
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(f"状态更新成功: {agent_id} -> {status}")
        except Exception as e:
            logger.error(f"状态更新失败: {agent_id}, 错误: {e!s}")

    async def _handle_command_response(self, agent_id: str, data: dict) -> None:
        """处理命令响应消息

        Args:
            agent_id: Agent ID
            data: 命令响应数据
        """
        command_id = data.get("command_id")
        result = data.get("result")
        error = data.get("error")

        logger.info(f"命令响应: {agent_id}, command_id: {command_id}, " + f"result: {result}, error: {error}")

        # 这里可以添加命令响应的处理逻辑
        # 例如：更新命令执行状态、通知其他服务等

    async def _heartbeat_monitor(self, agent_id: str) -> None:
        """心跳监控任务

        Args:
            agent_id: Agent ID
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_timeout)

                # 检查主机最后心跳时间
                host = await self.host_service.get_host_by_id(agent_id)
                if host and host.last_heartbeat:
                    time_since_heartbeat = (datetime.now(timezone.utc) - host.last_heartbeat).total_seconds()

                    if time_since_heartbeat > self.heartbeat_timeout:
                        logger.warning(f"心跳超时: {agent_id}, " + f"最后心跳: {time_since_heartbeat:.0f}秒前")

                        # 发送超时警告
                        await self.send_message(
                            agent_id,
                            {
                                "type": "heartbeat_timeout_warning",
                                "message": "心跳超时警告",
                                "timeout": self.heartbeat_timeout,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )

        except asyncio.CancelledError:
            logger.debug(f"心跳监控任务已取消: {agent_id}")
        except Exception as e:
            logger.error(f"心跳监控异常: {agent_id}, 错误: {e!s}")

    def get_active_connections(self) -> List[str]:
        """获取所有活跃连接的 Agent ID

        Returns:
            Agent ID 列表
        """
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """获取当前连接数

        Returns:
            连接数
        """
        return len(self.active_connections)

    def is_connected(self, agent_id: str) -> bool:
        """检查 Agent 是否已连接

        Args:
            agent_id: Agent ID

        Returns:
            是否已连接
        """
        return agent_id in self.active_connections
