"""Agent 测试用例上报服务模块

提供测试用例执行结果上报和预期时间更新功能。

从 agent_report_service.py 拆分出来，提高代码可维护性。
"""

from datetime import datetime, timedelta, timezone
import os
import sys
from typing import Any, Dict, Optional

from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
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
    """Agent 测试用例上报服务

    负责处理：
    - 测试用例执行结果上报
    - 预期结束时间更新
    """

    def __init__(self) -> None:
        """初始化服务"""
        self._session_factory = None

    @property
    def session_factory(self):
        """获取会话工厂（延迟初始化，单例模式）"""
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
        """上报测试用例执行结果

        Args:
            host_id: 主机ID（从token中获取）
            tc_id: 测试用例ID
            state: 执行状态（0-空闲 1-启动 2-成功 3-失败）
            result_msg: 结果消息
            log_url: 日志文件URL

        Returns:
            更新结果

        Raises:
            BusinessError: 业务逻辑错误
        """
        try:
            logger.info(
                "开始处理测试用例结果上报",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "state": state,
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. 查询最新的执行日志记录
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
                        message=f"未找到主机 {host_id} 的测试用例 {tc_id} 执行记录",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "找到执行日志记录",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "current_state": exec_log.case_state,
                    },
                )

                # 2. 更新执行状态和结果
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
                    "测试用例结果上报成功",
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
                "测试用例结果上报失败",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="测试用例结果上报处理失败",
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
        """更新测试用例预期结束时间

        Args:
            host_id: 主机ID（从token中获取）
            tc_id: 测试用例ID
            due_time_minutes: 预期结束时间（分钟时间差，整数）

        Returns:
            更新结果

        Raises:
            BusinessError: 业务逻辑错误
        """
        try:
            # 计算实际的预期结束时间（当前时间 + 分钟数）
            now = datetime.now(timezone.utc)
            due_time = now + timedelta(minutes=due_time_minutes)

            logger.info(
                "开始处理预期结束时间上报",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "due_time_minutes": due_time_minutes,
                    "calculated_due_time": due_time.isoformat(),
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. 查询最新的执行日志记录
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
                        message=f"未找到主机 {host_id} 的测试用例 {tc_id} 执行记录",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "找到执行日志记录",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "current_due_time": exec_log.due_time.isoformat() if exec_log.due_time else None,
                    },
                )

                # 2. 更新预期结束时间
                update_stmt = (
                    update(HostExecLog)
                    .where(HostExecLog.id == exec_log.id)
                    .values(due_time=due_time)
                )

                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "预期结束时间上报成功",
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
                "预期结束时间上报失败",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="预期结束时间上报处理失败",
                error_code="DUE_TIME_UPDATE_FAILED",
                code=ServiceErrorCodes.HOST_DUE_TIME_UPDATE_FAILED,
                http_status_code=500,
            )


# 模块级实例
_testcase_report_service_instance: Optional[AgentTestCaseReportService] = None


def get_testcase_report_service() -> AgentTestCaseReportService:
    """获取测试用例上报服务实例（单例模式）

    Returns:
        AgentTestCaseReportService: 测试用例上报服务实例
    """
    global _testcase_report_service_instance
    if _testcase_report_service_instance is None:
        _testcase_report_service_instance = AgentTestCaseReportService()
    return _testcase_report_service_instance
