"""Case 超时检测定时任务服务

定期检测执行超时的测试用例，并通过 WebSocket 通知对应的 Host 结束任务。

功能：
1. 每 10 分钟执行一次超时检测
2. 从 sys_conf 表查询 case_timeout 配置（缓存 1 小时）
3. 查询超时的 host_exec_log 记录
4. 通过 WebSocket 通知对应的 Host 结束任务
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, select

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_exec_log import HostExecLog
    from app.models.sys_conf import SysConf
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_exec_log import HostExecLog
    from app.models.sys_conf import SysConf
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# 缓存键
CACHE_KEY_CASE_TIMEOUT = "sys_conf:case_timeout"
# 缓存过期时间：1小时（3600秒）
CACHE_EXPIRE_CASE_TIMEOUT = 3600


class CaseTimeoutTaskService:
    """Case 超时检测定时任务服务"""

    def __init__(self):
        """初始化定时任务服务"""
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        # 任务执行间隔：10分钟（600秒）
        self.interval: int = 600
        # 记录是否已经警告过配置缺失（避免重复警告）
        self._has_warned_missing_config: bool = False

    async def start(self) -> None:
        """启动定时任务"""
        if self._running:
            logger.warning("定时任务已在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Case 超时检测定时任务已启动",
            extra={
                "interval_seconds": self.interval,
                "interval_minutes": self.interval // 60,
            },
        )

    async def stop(self) -> None:
        """停止定时任务"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                ***REMOVED***

        logger.info("Case 超时检测定时任务已停止")

    async def _run_loop(self) -> None:
        """定时任务循环"""
        # ✅ 服务启动时延迟首次检查，避免立即检查历史数据产生大量警告
        # 等待 60 秒后再执行第一次检查，给服务一些时间建立连接
        await asyncio.sleep(60)

        while self._running:
            try:
                # 执行超时检测
                await self._check_timeout_cases()

                # 等待指定间隔
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info("定时任务循环已取消")
                break
            except Exception as e:
                logger.error(
                    "定时任务执行异常",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                    exc_info=True,
                )
                # 异常后等待一段时间再继续
                await asyncio.sleep(60)

    async def _check_timeout_cases(self) -> None:
        """检查超时的测试用例"""
        try:
            logger.info("开始检测超时的测试用例")

            # 1. 获取 case_timeout 配置（带缓存）
            timeout_minutes = await self._get_case_timeout_config()
            if timeout_minutes is None or timeout_minutes <= 0:
                # 只在第一次检测时记录警告，避免重复日志
                if not self._has_warned_missing_config:
                    logger.warning(
                        "case_timeout 配置无效或未设置，跳过检测。请在 sys_conf 表中插入配置："
                        "INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag) "
                        "VALUES ('case_timeout', '30', 'Case超时时间(分钟)', 0, 0);",
                        extra={"timeout_minutes": timeout_minutes},
                    )
                    self._has_warned_missing_config = True
                else:
                    logger.debug(
                        "case_timeout 配置无效或未设置，跳过检测",
                        extra={"timeout_minutes": timeout_minutes},
                    )
                return
            
            # 如果配置存在，重置警告标志（配置可能刚被添加）
            if self._has_warned_missing_config:
                self._has_warned_missing_config = False

            logger.debug(
                "获取到 case_timeout 配置",
                extra={"timeout_minutes": timeout_minutes},
            )

            # 如果配置存在，重置警告标志（配置可能刚被添加）
            if self._has_warned_missing_config:
                self._has_warned_missing_config = False
                logger.info("case_timeout 配置已生效", extra={"timeout_minutes": timeout_minutes})

            # 2. 查询超时的 host_exec_log 记录
            timeout_cases = await self._query_timeout_cases(timeout_minutes)
            if not timeout_cases:
                logger.debug("未发现超时的测试用例")
                return

            logger.info(
                "发现超时的测试用例",
                extra={
                    "count": len(timeout_cases),
                    "timeout_minutes": timeout_minutes,
                },
            )

            # 3. 通知对应的 Host 结束任务
            ws_manager = get_agent_websocket_manager()
            success_count = 0
            failed_count = 0

            for exec_log in timeout_cases:
                host_id = str(exec_log.host_id) if exec_log.host_id else None
                if not host_id:
                    logger.warning(
                        "执行日志记录缺少 host_id，跳过",
                        extra={"log_id": exec_log.id},
                    )
                    failed_count += 1
                    continue

                # 检查 Host 是否在线
                if not ws_manager.is_connected(host_id):
                    # ✅ 对于 Host 不在线的情况，使用 DEBUG 级别而不是 WARNING
                    # 因为这些超时记录可能是历史数据，Host 不在线是正常情况
                    logger.debug(
                        "Host 未连接，无法发送超时通知（可能是历史超时记录）",
                        extra={
                            "host_id": host_id,
                            "log_id": exec_log.id,
                            "begin_time": exec_log.begin_time.isoformat() if exec_log.begin_time else None,
                        },
                    )
                    failed_count += 1
                    continue

                # 发送超时通知
                success = await self._notify_case_timeout(
                    ws_manager, host_id, exec_log, timeout_minutes
                )

                if success:
                    success_count += 1
                    logger.info(
                        "超时通知已发送",
                        extra={
                            "host_id": host_id,
                            "log_id": exec_log.id,
                            "tc_id": exec_log.tc_id,
                            "timeout_minutes": timeout_minutes,
                        },
                    )
                else:
                    failed_count += 1
                    logger.error(
                        "超时通知发送失败",
                        extra={
                            "host_id": host_id,
                            "log_id": exec_log.id,
                        },
                    )

            logger.info(
                "超时检测完成",
                extra={
                    "total": len(timeout_cases),
                    "success": success_count,
                    "failed": failed_count,
                    "timeout_minutes": timeout_minutes,
                },
            )

        except Exception as e:
            logger.error(
                "检测超时测试用例异常",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

    async def _get_case_timeout_config(self) -> Optional[int]:
        """获取 case_timeout 配置值（带缓存）

        Returns:
            超时时间（分钟），如果未找到或无效则返回 None
        """
        try:
            # 1. 先从缓存获取
            cached_value = await redis_manager.get(CACHE_KEY_CASE_TIMEOUT)
            if cached_value is not None:
                # JSON 解析后可能是整数或字符串，统一转换为整数
                if isinstance(cached_value, int):
                    timeout_minutes = cached_value
                elif isinstance(cached_value, str):
                    try:
                        timeout_minutes = int(cached_value)
                    except (ValueError, TypeError):
                        logger.warning(
                            "缓存中的 case_timeout 配置格式无效，将从数据库重新获取"
                        )
                        timeout_minutes = None
                else:
                    logger.warning(
                        "缓存中的 case_timeout 配置类型无效，将从数据库重新获取",
                        extra={"cached_type": type(cached_value).__name__},
                    )
                    timeout_minutes = None

                if timeout_minutes is not None:
                    logger.debug(
                        "从缓存获取 case_timeout 配置",
                        extra={"timeout_minutes": timeout_minutes},
                    )
                    return timeout_minutes

            # 2. 从数据库查询
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = (
                    select(SysConf)
                    .where(
                        and_(
                            SysConf.conf_key == "case_timeout",
                            SysConf.del_flag == 0,
                            SysConf.state_flag == 0,  # 启用状态
                        )
                    )
                    .limit(1)
                )

                result = await session.execute(stmt)
                sys_conf = result.scalar_one_or_none()

                if not sys_conf or not sys_conf.conf_val:
                    # 日志级别降低，避免每次定时任务都记录警告
                    # 具体警告已在 _check_timeout_cases 中处理
                    logger.debug("未找到 case_timeout 配置")
                    return None

                # 3. 解析配置值
                try:
                    timeout_minutes = int(sys_conf.conf_val)
                    logger.info(
                        "从数据库获取 case_timeout 配置",
                        extra={"timeout_minutes": timeout_minutes},
                    )

                    # 4. 存入缓存（1小时过期）
                    await redis_manager.set(
                        CACHE_KEY_CASE_TIMEOUT,
                        timeout_minutes,
                        expire=CACHE_EXPIRE_CASE_TIMEOUT,
                    )
                    logger.debug(
                        "case_timeout 配置已缓存",
                        extra={
                            "timeout_minutes": timeout_minutes,
                            "expire_seconds": CACHE_EXPIRE_CASE_TIMEOUT,
                        },
                    )

                    return timeout_minutes

                except (ValueError, TypeError):
                    logger.error(
                        "case_timeout 配置值格式无效（应为整数）",
                        extra={"conf_val": sys_conf.conf_val},
                    )
                    return None

        except Exception as e:
            logger.error(
                "获取 case_timeout 配置异常",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return None

    async def _query_timeout_cases(
        self, timeout_minutes: int
    ) -> List[HostExecLog]:
        """查询超时的 host_exec_log 记录

        Args:
            timeout_minutes: 超时时间（分钟）

        Returns:
            超时的执行日志记录列表
        """
        try:
            # 计算超时时间点
            timeout_threshold = datetime.now(timezone.utc) - timedelta(
                minutes=timeout_minutes
            )

            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # 查询条件：
                # - host_state in (2, 3)  # 已占用或case执行中
                # - case_state = 1        # 启动
                # - del_flag = 0          # 未删除
                # - begin_time < 当前时间 - timeout_minutes
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_state.in_([2, 3]),
                            HostExecLog.case_state == 1,
                            HostExecLog.del_flag == 0,
                            HostExecLog.begin_time < timeout_threshold,
                        )
                    )
                    .order_by(HostExecLog.begin_time.asc())
                )

                result = await session.execute(stmt)
                exec_logs = result.scalars().all()

                logger.debug(
                    "查询超时的执行日志",
                    extra={
                        "timeout_minutes": timeout_minutes,
                        "timeout_threshold": timeout_threshold.isoformat(),
                        "count": len(exec_logs),
                    },
                )

                return list(exec_logs)

        except Exception as e:
            logger.error(
                "查询超时执行日志异常",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timeout_minutes": timeout_minutes,
                },
                exc_info=True,
            )
            return []

    async def _notify_case_timeout(
        self,
        ws_manager,
        host_id: str,
        exec_log: HostExecLog,
        timeout_minutes: int,
    ) -> bool:
        """通知 Host 结束超时任务

        Args:
            ws_manager: WebSocket 管理器实例
            host_id: Host ID
            exec_log: 执行日志记录
            timeout_minutes: 超时时间（分钟）

        Returns:
            是否通知成功
        """
        try:
            # 构建超时通知消息
            timeout_message = {
                "type": "case_timeout_notification",
                "host_id": host_id,
                "log_id": exec_log.id,
                "tc_id": exec_log.tc_id,
                "message": f"测试用例执行超时（超过 {timeout_minutes} 分钟），请结束任务",
                "timeout_minutes": timeout_minutes,
                "begin_time": exec_log.begin_time.isoformat() if exec_log.begin_time else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 发送消息
            success = await ws_manager.send_to_host(host_id, timeout_message)

            return success

        except Exception as e:
            logger.error(
                "发送超时通知异常",
                extra={
                    "host_id": host_id,
                    "log_id": exec_log.id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return False


# 全局定时任务服务实例（单例）
_case_timeout_task_instance: Optional[CaseTimeoutTaskService] = None


def get_case_timeout_task_service() -> CaseTimeoutTaskService:
    """获取 Case 超时检测定时任务服务实例（单例）

    Returns:
        CaseTimeoutTaskService 实例
    """
    global _case_timeout_task_instance

    if _case_timeout_task_instance is None:
        _case_timeout_task_instance = CaseTimeoutTaskService()
        logger.info("Case 超时检测定时任务服务实例已创建")

    return _case_timeout_task_instance

