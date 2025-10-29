"""WebSocket 连接管理器"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from app.services.browser_host_service import BrowserHostService
from fastapi import WebSocket
from sqlalchemy import and_, select

# 使用 try-except 方式处理路径导入
try:
    from shared.common.loguru_config import get_logger
    from shared.common.database import mariadb_manager
    from app.schemas.host import HostStatusUpdate
    from app.models.host_exec_log import HostExecLog
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.database import mariadb_manager
    from app.schemas.host import HostStatusUpdate
    from app.models.host_exec_log import HostExecLog

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
        # 主机服务实例（共享基础功能）
        self.host_service = BrowserHostService()

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
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # 更新 TCP 状态为 2 (监听/连接建立)
        await self.host_service.update_tcp_state(agent_id, tcp_state=2)

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
                        "timestamp": datetime.utcnow().isoformat(),
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
                    "timestamp": datetime.utcnow().isoformat(),
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
                    "timestamp": datetime.utcnow().isoformat(),
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

            await self.host_service.update_host_status(agent_id, HostStatusUpdate(status=status))

            await self.send_message(
                agent_id,
                {
                    "type": "status_update_ack",
                    "message": "状态更新成功",
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat(),
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

    async def _handle_connection_result(self, agent_id: str, data: dict) -> None:
        """处理 Agent 上报连接结果

        业务逻辑:
        1. 查询 host_exec_log 表: host_id = agent_id, host_state = 1, del_flag = 0
        2. 获取最新一条数据（按 created_at 降序）
        3. 如果数据不存在: 发送错误消息
        4. 如果数据存在:
           - 更新 host_state = 2 (已占用)
           - 提取 tc_id, cycle_name, user_name
           - 下发执行参数给 Agent

        Args:
            agent_id: Agent/Host ID (来自 token)
            data: 消息数据
        """
        try:
            # 转换 agent_id 为整数
            try:
                host_id_int = int(agent_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Agent ID 格式错误: {agent_id}",
                    extra={
                        "agent_id": agent_id,
                        "error": "not a valid integer",
                    },
                )
                await self._send_error_message(agent_id, "Host ID 格式无效")
                return

            logger.info(
                "开始处理 Agent 连接结果上报",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                },
            )

            # 查询 host_exec_log 表
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # 查询条件: host_id = agent_id, host_state = 1, del_flag = 0
                # 按 created_at 降序，获取最新一条
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id_int,
                            HostExecLog.host_state == 1,  # 已锁定
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_at.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                exec_log = result.scalar_one_or_none()

                if not exec_log:
                    # 数据不存在: 发送错误消息
                    logger.warning(
                        "未找到执行日志记录",
                        extra={
                            "agent_id": agent_id,
                            "host_id": host_id_int,
                            "host_state": 1,
                            "del_flag": 0,
                        },
                    )

                    error_msg = {
                        "type": "connection_result_error",
                        "message": "未找到待执行任务，请先通过 VNC 上报连接结果",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await self.send_to_host(agent_id, error_msg)
                    return

                # 数据存在: 更新 host_state = 2
                logger.info(
                    "找到执行日志记录，准备更新状态并下发执行参数",
                    extra={
                        "agent_id": agent_id,
                        "log_id": exec_log.id,
                        "tc_id": exec_log.tc_id,
                        "cycle_name": exec_log.cycle_name,
                        "user_name": exec_log.user_name,
                    },
                )

                # 更新 host_state = 2 (已占用)
                from sqlalchemy import update

                update_stmt = (
                    update(HostExecLog).where(HostExecLog.id == exec_log.id).values(host_state=2)  # 已占用
                )
                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "执行日志状态已更新",
                    extra={
                        "agent_id": agent_id,
                        "log_id": exec_log.id,
                        "old_host_state": 1,
                        "new_host_state": 2,
                    },
                )

                # 提取执行参数
                execute_params = {
                    "type": "execute_params",
                    "tc_id": exec_log.tc_id,
                    "cycle_name": exec_log.cycle_name,
                    "user_name": exec_log.user_name,
                    "message": "执行参数已下发",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # 下发执行参数给 Agent
                await self.send_to_host(agent_id, execute_params)

                logger.info(
                    "执行参数已下发",
                    extra={
                        "agent_id": agent_id,
                        "tc_id": exec_log.tc_id,
                        "cycle_name": exec_log.cycle_name,
                        "user_name": exec_log.user_name,
                    },
                )

        except Exception as e:
            logger.error(
                f"处理 Agent 连接结果失败: {agent_id}, 错误: {e!s}",
                exc_info=True,
            )
            await self._send_error_message(agent_id, "处理连接结果失败")

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
                    time_since_heartbeat = (datetime.utcnow() - host.last_heartbeat).total_seconds()

                    if time_since_heartbeat > self.heartbeat_timeout:
                        logger.warning(f"心跳超时: {agent_id}, " + f"最后心跳: {time_since_heartbeat:.0f}秒前")

                        # 发送超时警告
                        await self.send_message(
                            agent_id,
                            {
                                "type": "heartbeat_timeout_warning",
                                "message": "心跳超时警告",
                                "timeout": self.heartbeat_timeout,
                                "timestamp": datetime.utcnow().isoformat(),
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
