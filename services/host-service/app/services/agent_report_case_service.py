"""Agent Test Case Report Service Module

Provides test case execution result reporting and expected time update functionality.

Split from agent_report_service.py to improve code maintainability.
"""

from datetime import datetime, timedelta, timezone
import os
import sys
from typing import Any, Dict, Optional

from sqlalchemy import and_, select, update

# Use try-except to handle path imports
try:
    from app.models.host_exec_log import HostExecLog
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_exec_log import HostExecLog
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class AgentTestCaseReportService:
    """Agent Test Case Report Service

    Responsible for handling:
    - Test case execution result reporting
    - Expected end time updates
    """

    def __init__(self) -> None:
        """Initialize service"""
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)"""
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    async def report_testcase_result(
        self,
        host_id: int,
        tc_id: str,
        state: int,
        result_msg: Optional[str] = None,
        log_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Report test case execution result

        Args:
            host_id: Host ID (obtained from token)
            tc_id: Test case ID
            state: Execution state (0-free, 1-started, 2-success, 3-failed)
            result_msg: Result message
            log_url: Log file URL

        Returns:
            Update result

        Raises:
            BusinessError: Business logic error
        """
        try:
            logger.info(
                "Starting to process test case result report",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "state": state,
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. Query latest execution log record
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id,
                            HostExecLog.tc_id == tc_id,
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_time.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                exec_log = result.scalar_one_or_none()

                if not exec_log:
                    raise BusinessError(
                        message=f"Execution record not found for host {host_id} test case {tc_id}",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "Found execution log record",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "current_state": exec_log.case_state,
                    },
                )

                # 2. Update execution state and result
                update_stmt = (
                    update(HostExecLog)
                    .where(HostExecLog.id == exec_log.id)
                    .values(
                        case_state=state,
                        result_msg=result_msg,
                        log_url=log_url,
                    )
                )

                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "Test case result report succeeded",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "old_state": exec_log.case_state,
                        "new_state": state,
                    },
                )

                return {
                    "host_id": str(host_id),
                    "tc_id": tc_id,
                    "case_state": state,
                    "result_msg": result_msg,
                    "log_url": log_url,
                    "updated": True,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "Test case result report failed",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Test case result report processing failed",
                error_code="TESTCASE_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_TESTCASE_REPORT_FAILED,
                http_status_code=500,
            )

    async def update_due_time(
        self,
        host_id: int,
        tc_id: str,
        due_time_minutes: int,
    ) -> Dict[str, Any]:
        """Update test case expected end time

        Args:
            host_id: Host ID (obtained from token)
            tc_id: Test case ID
            due_time_minutes: Expected end time (time difference in minutes, integer)

        Returns:
            Update result

        Raises:
            BusinessError: Business logic error
        """
        try:
            # Calculate actual expected end time (current time + minutes)
            now = datetime.now(timezone.utc)
            due_time = now + timedelta(minutes=due_time_minutes)

            logger.info(
                "Starting to process expected end time report",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "due_time_minutes": due_time_minutes,
                    "calculated_due_time": due_time.isoformat(),
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. Query latest execution log record
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id,
                            HostExecLog.tc_id == tc_id,
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_time.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                exec_log = result.scalar_one_or_none()

                if not exec_log:
                    raise BusinessError(
                        message=f"Execution record not found for host {host_id} test case {tc_id}",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "Found execution log record",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "current_due_time": exec_log.due_time.isoformat() if exec_log.due_time else None,
                    },
                )

                # 2. Update expected end time
                update_stmt = update(HostExecLog).where(HostExecLog.id == exec_log.id).values(due_time=due_time)

                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "Expected end time report succeeded",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "old_due_time": exec_log.due_time.isoformat() if exec_log.due_time else None,
                        "new_due_time": due_time.isoformat(),
                    },
                )

                return {
                    "host_id": str(host_id),
                    "tc_id": tc_id,
                    "due_time": due_time.isoformat(),
                    "due_time_minutes": due_time_minutes,
                    "updated": True,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "Expected end time report failed",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Expected end time report processing failed",
                error_code="DUE_TIME_UPDATE_FAILED",
                code=ServiceErrorCodes.HOST_DUE_TIME_UPDATE_FAILED,
                http_status_code=500,
            )


# Module-level instance
_testcase_report_service_instance: Optional[AgentTestCaseReportService] = None


def get_testcase_report_service() -> AgentTestCaseReportService:
    """Get test case report service instance (singleton pattern)

    Returns:
        AgentTestCaseReportService: Test case report service instance
    """
    global _testcase_report_service_instance
    if _testcase_report_service_instance is None:
        _testcase_report_service_instance = AgentTestCaseReportService()
    return _testcase_report_service_instance
