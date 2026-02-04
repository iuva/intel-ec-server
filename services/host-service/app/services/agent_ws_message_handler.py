"""Agent WebSocket message handler module

Provides core business logic for Agent message processing, including:
- Connection result processing
- Offline notification processing
- Version update processing

Extracted from agent_websocket_manager.py to improve code maintainability.
"""

from datetime import datetime, timezone
import os
import sys
from typing import Callable, Optional

from sqlalchemy import and_, select, update

# Use try-except to handle path imports
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
    """Agent message handler

    Responsible for processing various messages reported by Agent, including:
    - CONNECTION_RESULT: Agent reports connection result
    - HOST_OFFLINE_NOTIFICATION: Host offline notification
    - VERSION_UPDATE: Agent version update
    """

    def __init__(self) -> None:
        """Initialize message handler"""
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)"""
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
        """Handle Agent reported connection result

        Business logic:
        1. Query host_exec_log table: host_id = agent_id, host_state = 1, del_flag = 0
        2. Get latest record (ordered by created_at desc)
        3. If record does not exist: send error message
        4. If record exists:
           - Update host_state = 2 (occupied)
           - Extract tc_id, cycle_name, user_name
           - Send execution parameters to Agent

        Args:
            agent_id: Agent/Host ID (from token)
            data: Message data
            send_callback: Callback function to send message
            send_error_callback: Callback function to send error message
        """
        try:
            # Convert agent_id to integer
            try:
                host_id_int = int(agent_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Agent ID format error: {agent_id}",
                    extra={
                        "agent_id": agent_id,
                        "error": "not a valid integer",
                    },
                )
                await send_error_callback(agent_id, "Host ID format invalid")
                return

            logger.info(
                "Start processing Agent connection result report",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                },
            )

            # Query host_exec_log table
            session_factory = self.session_factory
            async with session_factory() as session:
                # Query conditions: host_id = agent_id, host_state = 1, del_flag = 0
                # Order by created_at desc, get latest one
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id_int,
                            HostExecLog.host_state == 1,  # Locked
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_time.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                exec_log = result.scalar_one_or_none()

                if not exec_log:
                    # Record does not exist: send error message
                    logger.warning(
                        "Execution log record not found",
                        extra={
                            "agent_id": agent_id,
                            "host_id": host_id_int,
                            "host_state": 1,
                            "del_flag": 0,
                        },
                    )

                    error_msg = {
                        "type": MessageType.ERROR,
                        "message": "Pending execution task not found, please report connection result via VNC first",
                        "error_code": "CONNECTION_RESULT_NOT_FOUND",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await send_callback(agent_id, error_msg)
                    return

                # Record exists: update host_state = 2
                logger.info(
                    "Execution log record found, preparing to update state and send execution parameters",
                    extra={
                        "agent_id": agent_id,
                        "log_id": exec_log.id,
                        "tc_id": exec_log.tc_id,
                        "cycle_name": exec_log.cycle_name,
                        "user_name": exec_log.user_name,
                    },
                )

                # Update host_state = 2 (occupied)
                update_stmt = update(HostExecLog).where(HostExecLog.id == exec_log.id).values(host_state=2)
                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "Execution log state updated",
                    extra={
                        "agent_id": agent_id,
                        "log_id": exec_log.id,
                        "old_host_state": 1,
                        "new_host_state": 2,
                    },
                )

                # Extract execution parameters
                execute_params = {
                    "type": MessageType.COMMAND,
                    "command": "execute_test_case",
                    "tc_id": exec_log.tc_id,
                    "cycle_name": exec_log.cycle_name,
                    "user_name": exec_log.user_name,
                    "message": "Execution parameters sent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # Send execution parameters to Agent
                await send_callback(agent_id, execute_params)

                logger.info(
                    "Execution parameters sent",
                    extra={
                        "agent_id": agent_id,
                        "tc_id": exec_log.tc_id,
                        "cycle_name": exec_log.cycle_name,
                        "user_name": exec_log.user_name,
                    },
                )

        except Exception as e:
            logger.error(
                f"Failed to process Agent connection result: {agent_id}, error: {e!s}",
                exc_info=True,
            )
            await send_error_callback(agent_id, "Failed to process connection result")

    async def handle_host_offline_notification(
        self,
        agent_id: str,
        data: dict,
        send_callback: Callable,
    ) -> None:
        """Handle Host offline notification

        Business logic:
        1. Get host_id from message
        2. Query host_exec_log table: host_id = data['host_id'], del_flag = 0
        3. Get latest record (ordered by created_time desc)
        4. If record exists:
           - Update host_state = 4 (offline)

        Args:
            agent_id: Agent/Host ID (from token)
            data: Message data, contains host_id field
            send_callback: Callback function to send message
        """
        try:
            # Get host_id from message
            host_id_str = data.get("host_id")
            if not host_id_str:
                logger.warning(
                    "Offline notification missing host_id",
                    extra={
                        "agent_id": agent_id,
                        "data": data,
                    },
                )
                return

            # Convert host_id to integer
            try:
                host_id_int = int(host_id_str)
            except (ValueError, TypeError):
                logger.error(
                    f"Host ID format error: {host_id_str}",
                    extra={
                        "agent_id": agent_id,
                        "host_id": host_id_str,
                        "error": "not a valid integer",
                    },
                )
                return

            logger.info(
                "Start processing Host offline notification",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                },
            )

            # Query and update database
            session_factory = self.session_factory
            async with session_factory() as session:
                # Query host_exec_log table: host_id = data['host_id'], del_flag = 0
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id_int,
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_time.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                exec_log = result.scalar_one_or_none()

                if exec_log:
                    # Update host_state = 4 (offline)
                    update_stmt = update(HostExecLog).where(HostExecLog.id == exec_log.id).values(host_state=4)
                    await session.execute(update_stmt)
                    await session.commit()

                    logger.info(
                        "Execution log state updated to offline",
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
                        "Execution log record not found for update",
                        extra={
                            "agent_id": agent_id,
                            "host_id": host_id_int,
                        },
                    )

                # Also update host_rec table host state to offline
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
                    "Host state updated to offline",
                    extra={
                        "host_id": host_id_int,
                        "new_state": HOST_STATE_OFFLINE,
                    },
                )

        except Exception as e:
            logger.error(
                f"Failed to process Host offline notification: {agent_id}, error: {e!s}",
                exc_info=True,
            )

    async def handle_version_update(
        self,
        agent_id: str,
        data: dict,
    ) -> None:
        """Handle Agent version update

        Args:
            agent_id: Agent/Host ID
            data: Message data, contains version information
        """
        try:
            version = data.get("version")
            if not version:
                logger.warning(
                    "Version update message missing version number",
                    extra={
                        "agent_id": agent_id,
                        "data": data,
                    },
                )
                return

            # Convert agent_id to integer
            try:
                host_id_int = int(agent_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Agent ID format error: {agent_id}",
                    extra={
                        "agent_id": agent_id,
                        "error": "not a valid integer",
                    },
                )
                return

            logger.info(
                "Processing Agent version update",
                extra={
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                    "version": version,
                },
            )

            # Update version information in database
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
                    "Agent version updated",
                    extra={
                        "host_id": host_id_int,
                        "version": version,
                    },
                )

        except Exception as e:
            logger.error(
                f"Failed to process Agent version update: {agent_id}, error: {e!s}",
                exc_info=True,
            )


# Module-level instance
_message_handler_instance: Optional[AgentMessageHandler] = None


def get_agent_message_handler() -> AgentMessageHandler:
    """Get message handler instance (singleton pattern)

    Returns:
        AgentMessageHandler: Message handler instance
    """
    global _message_handler_instance
    if _message_handler_instance is None:
        _message_handler_instance = AgentMessageHandler()
    return _message_handler_instance
