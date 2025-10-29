"""WebSocket 连接管理器

核心功能:
1. 管理WebSocket连接池 (通过agent_id/host_id)
2. 根据消息类型进行路由和处理
3. 支持指定host通知和广播通知
4. 心跳检测和连接管理
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

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
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger
    from shared.common.database import mariadb_manager
    from app.schemas.host import HostStatusUpdate
    from app.models.host_exec_log import HostExecLog

logger = get_logger(__name__)


# 全局 WebSocket 管理器实例（单例）
_ws_manager_instance: Optional["WebSocketManager"] = None


def get_websocket_manager() -> "WebSocketManager":
    """获取 WebSocket 管理器单例

    Returns:
        WebSocketManager 实例

    Note:
        - 使用单例模式，确保全局只有一个管理器实例
        - 所有模块应该通过此函数获取管理器，而不是直接实例化
    """
    global _ws_manager_instance

    if _ws_manager_instance is None:
        _ws_manager_instance = WebSocketManager()
        logger.info("✅ WebSocket 管理器实例已创建")

    return _ws_manager_instance


class WebSocketManager:
    """WebSocket 连接管理器

    负责：
    1. 管理Agent WebSocket连接
    2. 根据消息类型进行路由处理
    3. 支持单播（指定host）和广播
    4. 心跳检测
    """

    def __init__(self):
        """初始化 WebSocket 管理器"""
        # 存储活跃连接: {agent_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储心跳任务: {agent_id: Task}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        # 存储心跳时间戳: {agent_id: datetime}
        self.heartbeat_timestamps: Dict[str, datetime] = {}
        # 消息处理器映射: {message_type: handler_func}
        self.message_handlers: Dict[str, Callable] = {}
        # 心跳超时时间（秒）
        self.heartbeat_timeout = 60
        # 主机服务实例（共享基础功能）
        self.host_service = BrowserHostService()

        # 注册默认的消息处理器
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认的消息处理器"""
        self.message_handlers = {
            "heartbeat": self._handle_heartbeat,
            "status_update": self._handle_status_update,
            "command_response": self._handle_command_response,
            "connection_result": self._handle_connection_result,  # Agent 上报连接结果
        }

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """注册自定义消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数 async def handler(agent_id: str, data: dict) -> None
        """
        self.message_handlers[message_type] = handler
        logger.info(f"消息处理器已注册: {message_type}")

    async def connect(self, agent_id: str, websocket: WebSocket) -> None:
        """建立 WebSocket 连接

        Args:
            agent_id: Agent/Host ID
            websocket: WebSocket 连接对象
        """
        self.active_connections[agent_id] = websocket

        logger.info(
            "WebSocket 连接已建立",
            extra={
                "agent_id": agent_id,
                "total_connections": len(self.active_connections),
            },
        )

        # 发送欢迎消息
        await self._send_welcome_message(agent_id)

        # 更新 TCP 状态为 2 (监听/连接建立)
        await self.host_service.update_tcp_state(agent_id, tcp_state=2)

        # 启动心跳检测任务
        self.heartbeat_tasks[agent_id] = asyncio.create_task(self._heartbeat_monitor(agent_id))

    async def disconnect(self, agent_id: str) -> None:
        """断开 WebSocket 连接

        Args:
            agent_id: Agent/Host ID
        """
        # 取消心跳检测任务
        if agent_id in self.heartbeat_tasks:
            self.heartbeat_tasks[agent_id].cancel()
            del self.heartbeat_tasks[agent_id]

        # 移除连接
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]

        # 清理心跳时间戳
        if agent_id in self.heartbeat_timestamps:
            del self.heartbeat_timestamps[agent_id]

        # 更新 TCP 状态为 0 (关闭/连接断开)
        await self.host_service.update_tcp_state(agent_id, tcp_state=0)

        # 更新主机状态为离线
        try:
            await self.host_service.update_host_status(agent_id, HostStatusUpdate(status="offline"))
        except Exception as e:
            logger.error(f"更新主机状态失败: {agent_id}, 错误: {e!s}")

        logger.info(
            "WebSocket 连接已断开",
            extra={
                "agent_id": agent_id,
                "total_connections": len(self.active_connections),
            },
        )

    async def handle_message(self, agent_id: str, data: dict) -> None:
        """处理接收到的消息

        根据消息类型调用对应的处理器

        Args:
            agent_id: Agent/Host ID
            data: 消息数据
        """
        message_type = data.get("type", "unknown")

        # 📥 日志：接收到消息 (详细报文内容)

        logger.info(
            f"📥 接收消息 | Agent: {agent_id} | 类型: {message_type} | 内容: {json.dumps(data, ensure_ascii=False)}",
        )

        try:
            # 查找对应的消息处理器
            handler = self.message_handlers.get(message_type)

            if handler:
                # 调用处理器
                await handler(agent_id, data)
            else:
                # 未知消息类型
                logger.warning(f"未知消息类型: {message_type}, Agent: {agent_id}")
                await self._send_error_message(agent_id, f"未知消息类型: {message_type}")

        except Exception as e:
            logger.error(
                f"消息处理失败: {agent_id}",
                extra={
                    "message_type": message_type,
                    "error": str(e),
                },
                exc_info=True,
            )
            await self._send_error_message(agent_id, "消息处理失败")

    # ========== 单播：发送给指定Host ==========

    async def send_to_host(self, host_id: str, message: dict) -> bool:
        """发送消息给指定Host

        Args:
            host_id: Host ID
            message: 消息内容

        Returns:
            是否发送成功
        """
        if host_id not in self.active_connections:
            logger.warning(f"Host 未连接: {host_id}")
            return False

        try:
            # 📤 日志：发送消息 (详细报文内容)

            message_type = message.get("type", "unknown")
            logger.info(
                f"📤 发送消息 | Host: {host_id} | 类型: {message_type} | 内容: {json.dumps(message, ensure_ascii=False)}",
            )

            websocket = self.active_connections[host_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(
                f"❌ 发送消息失败 | Host: {host_id} | 类型: {message.get('type')} | 错误: {str(e)}",
            )
            await self.disconnect(host_id)
            return False

    async def send_to_hosts(self, host_ids: List[str], message: dict) -> int:
        """发送消息给指定的多个Hosts

        Args:
            host_ids: Host ID 列表
            message: 消息内容

        Returns:
            成功发送的数量
        """
        success_count = 0
        failed_hosts = []

        for host_id in host_ids:
            if await self.send_to_host(host_id, message):
                success_count += 1
            else:
                failed_hosts.append(host_id)

        if failed_hosts:
            logger.warning(f"发送失败的Host: {failed_hosts}")

        logger.info(
            f"多播完成: 成功 {success_count}/{len(host_ids)}",
            extra={
                "message_type": message.get("type"),
            },
        )
        return success_count

    # ========== 广播：发送给所有Hosts ==========

    async def broadcast(self, message: dict, exclude: Optional[str] = None) -> int:
        """广播消息给所有连接的Hosts

        Args:
            message: 消息内容
            exclude: 排除的 Host ID

        Returns:
            成功发送的数量
        """
        # 📢 日志：开始广播

        target_hosts = [host_id for host_id in self.active_connections.keys() if not exclude or host_id != exclude]
        message_type = message.get("type", "unknown")

        message_json = json.dumps(message, ensure_ascii=False)
        logger.info(
            f"📢 开始广播消息 | 类型: {message_type} | 目标数量: {len(target_hosts)} | 排除: {exclude} | 内容: {message_json}",
        )

        success_count = 0
        failed_hosts = []

        for host_id in target_hosts:
            if await self.send_to_host(host_id, message):
                success_count += 1
            else:
                failed_hosts.append(host_id)

        if failed_hosts:
            logger.warning(f"广播失败的Host: {failed_hosts}")

        logger.info(
            f"✅ 广播完成: 成功 {success_count}/{len(target_hosts)}",
            extra={
                "message_type": message.get("type"),
                "success_count": success_count,
                "failed_count": len(failed_hosts),
            },
        )
        return success_count

    # ========== 内部方法 ==========

    async def _send_welcome_message(self, agent_id: str) -> None:
        """发送欢迎消息"""
        welcome_msg = {
            "type": "welcome",
            "agent_id": agent_id,
            "message": "WebSocket 连接已建立",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.send_to_host(agent_id, welcome_msg)

    async def _send_error_message(self, agent_id: str, error_msg: str) -> None:
        """发送错误消息"""
        error_msg_obj = {
            "type": "error",
            "message": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.send_to_host(agent_id, error_msg_obj)

    async def _handle_heartbeat(self, agent_id: str, data: dict) -> None:
        """处理心跳消息

        Note:
            - agent_id 是连接时从 token 获取的 host_id
            - data 中的 agent_id 字段会被忽略（客户端可以不传）
        """
        try:
            # 更新内存中的心跳时间戳
            self.heartbeat_timestamps[agent_id] = datetime.now(timezone.utc)
            logger.debug(f"心跳时间戳已更新: {agent_id}")

            # 尝试更新数据库中的心跳时间（如果host在数据库中存在）
            # 使用静默方法，失败时不记录 ERROR 日志
            success = await self.host_service.update_heartbeat_silent(agent_id)
            if success:
                logger.debug(f"✅ 数据库心跳已更新: {agent_id}")
            else:
                logger.debug(f"⚠️ 数据库心跳更新跳过: {agent_id} (主机不存在或ID格式无效)")

            # 发送心跳确认
            ack_msg = {
                "type": "heartbeat_ack",
                "message": "心跳已接收",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.send_to_host(agent_id, ack_msg)
            logger.debug(f"✅ 心跳处理完成: {agent_id}")
        except Exception as e:
            logger.error(
                f"❌ 心跳处理失败: {agent_id}, 错误: {e!s}",
                exc_info=True,
            )

    async def _handle_status_update(self, agent_id: str, data: dict) -> None:
        """处理状态更新消息"""
        try:
            status = data.get("status", "online")

            await self.host_service.update_host_status(agent_id, HostStatusUpdate(status=status))

            ack_msg = {
                "type": "status_update_ack",
                "message": "状态更新成功",
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.send_to_host(agent_id, ack_msg)
            logger.info(f"状态已更新: {agent_id} -> {status}")
        except Exception as e:
            logger.error(f"状态更新失败: {agent_id}, 错误: {e!s}")

    async def _handle_command_response(self, agent_id: str, data: dict) -> None:
        """处理命令响应消息"""
        command_id = data.get("command_id")
        success = data.get("success", False)
        result = data.get("result")
        error = data.get("error")

        logger.info(
            "命令响应已接收",
            extra={
                "agent_id": agent_id,
                "command_id": command_id,
                "success": success,
                "result": result,
                "error": error,
            },
        )

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
                    update(HostExecLog)
                    .where(HostExecLog.id == exec_log.id)
                    .values(host_state=2)  # 已占用
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

        定期检查Host的心跳状态

        Note:
            - 如果无法从数据库查询主机信息，将跳过心跳检查
            - 主要依赖内存中的 heartbeat_timestamps 进行监控
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_timeout)

                # 优先检查内存中的心跳时间戳
                if agent_id in self.heartbeat_timestamps:
                    last_heartbeat_time = self.heartbeat_timestamps[agent_id]
                    time_since_heartbeat = (datetime.now(timezone.utc) - last_heartbeat_time).total_seconds()

                    if time_since_heartbeat > self.heartbeat_timeout:
                        logger.warning(
                            f"心跳超时: {agent_id}",
                            extra={
                                "last_heartbeat_seconds_ago": time_since_heartbeat,
                                "timeout_threshold": self.heartbeat_timeout,
                            },
                        )

                        # 更新 TCP 状态为 1 (等待/心跳超时)
                        await self.host_service.update_tcp_state(agent_id, tcp_state=1)

                        # 发送超时警告
                        timeout_msg = {
                            "type": "heartbeat_timeout_warning",
                            "message": "心跳超时警告",
                            "timeout": self.heartbeat_timeout,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        await self.send_to_host(agent_id, timeout_msg)
                else:
                    logger.debug(f"心跳监控: 未找到心跳记录 - {agent_id}")

        except asyncio.CancelledError:
            logger.debug(f"心跳监控已取消: {agent_id}")
        except Exception as e:
            logger.error(f"心跳监控异常: {agent_id}, 错误: {e!s}")

    # ========== 查询方法 ==========

    def get_active_hosts(self) -> List[str]:
        """获取所有活跃连接的Host ID

        Returns:
            Host ID 列表
        """
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """获取当前连接数

        Returns:
            连接数
        """
        return len(self.active_connections)

    def is_connected(self, host_id: str) -> bool:
        """检查Host是否已连接

        Args:
            host_id: Host ID

        Returns:
            是否已连接
        """
        return host_id in self.active_connections
