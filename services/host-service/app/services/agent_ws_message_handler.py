"""Agent WebSocket 消息处理器模块

提供 Agent 消息处理的核心业务逻辑，包括：
- 连接结果处理
- 下线通知处理
- 版本更新处理

从 agent_websocket_manager.py 拆分出来，提高代码可维护性。
"""

from datetime import datetime, timezone
import os
import sys
from typing import Callable, Optional

from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.constants.host_constants import HOST_STATE_OFFLINE
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.schemas.websocket_message import MessageType
    from shared.common.database import mariadb_manager
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import HOST_STATE_OFFLINE
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.schemas.websocket_message import MessageType
    from shared.common.database import mariadb_manager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class AgentMessageHandler:
    """Agent 消息处理器

    负责处理各类 Agent 上报的消息，包括：
    - CONNECTION_RESULT: Agent 上报连接结果
    - HOST_OFFLINE_NOTIFICATION: Host 下线通知
    - VERSION_UPDATE: Agent 版本更新
    """

    def __init__(self) -> None:
        """初始化消息处理器"""
        self._session_factory = None

    @property
    def session_factory(self):
        """获取会话工厂（延迟初始化，单例模式）"""
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    async def handle_connection_result(
        self,
        agent_id: str,
        data: dict,
        send_callback: Callable,
        send_error_callback: Callable,
    ) -> None:
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
            send_callback: 发送消息的回调函数
            send_error_callback: 发送错误消息的回调函数
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
                await send_error_callback(agent_id, "Host ID 格式无效")
                return

            logger.info(
                "开始处理 Agent 连接结果上报",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                },
            )

            # 查询 host_exec_log 表
            session_factory = self.session_factory
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
                        "type": MessageType.ERROR,
                        "message": "未找到待执行任务，请先通过 VNC 上报连接结果",
                        "error_code": "CONNECTION_RESULT_NOT_FOUND",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await send_callback(agent_id, error_msg)
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
                update_stmt = (
                    update(HostExecLog).where(HostExecLog.id == exec_log.id).values(host_state=2)
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
                    "type": MessageType.COMMAND,
                    "command": "execute_test_case",
                    "tc_id": exec_log.tc_id,
                    "cycle_name": exec_log.cycle_name,
                    "user_name": exec_log.user_name,
                    "message": "执行参数已下发",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # 下发执行参数给 Agent
                await send_callback(agent_id, execute_params)

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
            await send_error_callback(agent_id, "处理连接结果失败")

    async def handle_host_offline_notification(
        self,
        agent_id: str,
        data: dict,
        send_callback: Callable,
    ) -> None:
        """处理 Host 下线通知

        业务逻辑:
        1. 从消息中获取 host_id
        2. 查询 host_exec_log 表: host_id = data['host_id'], del_flag = 0
        3. 获取最新一条数据（按 created_time 降序）
        4. 如果数据存在:
           - 更新 host_state = 4 (离线)

        Args:
            agent_id: Agent/Host ID (来自 token)
            data: 消息数据，包含 host_id 字段
            send_callback: 发送消息的回调函数
        """
        try:
            # 从消息中获取 host_id
            host_id_str = data.get("host_id")
            if not host_id_str:
                logger.warning(
                    "下线通知缺少 host_id",
                    extra={
                        "agent_id": agent_id,
                        "data": data,
                    },
                )
                return

            # 转换 host_id 为整数
            try:
                host_id_int = int(host_id_str)
            except (ValueError, TypeError):
                logger.error(
                    f"Host ID 格式错误: {host_id_str}",
                    extra={
                        "agent_id": agent_id,
                        "host_id": host_id_str,
                        "error": "not a valid integer",
                    },
                )
                return

            logger.info(
                "开始处理 Host 下线通知",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                },
            )

            # 查询并更新数据库
            session_factory = self.session_factory
            async with session_factory() as session:
                # 查询 host_exec_log 表: host_id = data['host_id'], del_flag = 0
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id_int,
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_at.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                exec_log = result.scalar_one_or_none()

                if exec_log:
                    # 更新 host_state = 4 (离线)
                    update_stmt = (
                        update(HostExecLog)
                        .where(HostExecLog.id == exec_log.id)
                        .values(host_state=4)
                    )
                    await session.execute(update_stmt)
                    await session.commit()

                    logger.info(
                        "执行日志状态已更新为离线",
                        extra={
                            "agent_id": agent_id,
                            "host_id": host_id_int,
                            "log_id": exec_log.id,
                            "old_host_state": exec_log.host_state,
                            "new_host_state": 4,
                        },
                    )
                else:
                    logger.info(
                        "未找到需要更新的执行日志记录",
                        extra={
                            "agent_id": agent_id,
                            "host_id": host_id_int,
                        },
                    )

                # 同时更新 host_rec 表的主机状态为离线
                host_update_stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(host_state=HOST_STATE_OFFLINE)
                )
                await session.execute(host_update_stmt)
                await session.commit()

                logger.info(
                    "主机状态已更新为离线",
                    extra={
                        "host_id": host_id_int,
                        "new_state": HOST_STATE_OFFLINE,
                    },
                )

        except Exception as e:
            logger.error(
                f"处理 Host 下线通知失败: {agent_id}, 错误: {e!s}",
                exc_info=True,
            )

    async def handle_version_update(
        self,
        agent_id: str,
        data: dict,
    ) -> None:
        """处理 Agent 版本更新

        Args:
            agent_id: Agent/Host ID
            data: 消息数据，包含版本信息
        """
        try:
            version = data.get("version")
            if not version:
                logger.warning(
                    "版本更新消息缺少版本号",
                    extra={
                        "agent_id": agent_id,
                        "data": data,
                    },
                )
                return

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
                return

            logger.info(
                "处理 Agent 版本更新",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                    "version": version,
                },
            )

            # 更新数据库中的版本信息
            session_factory = self.session_factory
            async with session_factory() as session:
                update_stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(agent_version=version)
                )
                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "Agent 版本已更新",
                    extra={
                        "host_id": host_id_int,
                        "version": version,
                    },
                )

        except Exception as e:
            logger.error(
                f"处理 Agent 版本更新失败: {agent_id}, 错误: {e!s}",
                exc_info=True,
            )


# 模块级实例
_message_handler_instance: Optional[AgentMessageHandler] = None


def get_agent_message_handler() -> AgentMessageHandler:
    """获取消息处理器实例（单例模式）

    Returns:
        AgentMessageHandler: 消息处理器实例
    """
    global _message_handler_instance
    if _message_handler_instance is None:
        _message_handler_instance = AgentMessageHandler()
    return _message_handler_instance
