"""Case 超时检测定时任务服务

定期检测执行超时的测试用例，并通过邮件通知相关人员。

功能：
1. 每 10 分钟执行一次超时检测
2. 从 sys_conf 表查询 case_timeout 配置（缓存 1 小时）
3. 查询超时的 host_exec_log 记录（优先使用 due_time，否则使用 case_timeout）
4. 只查询 notify_state = 0（未通知）的记录，避免重复通知
5. 通过邮件通知相关人员（发送 hardware_id, host_ip, begin_time, due_time）
6. 邮件发送成功后，更新 notify_state = 1（已通知），标记为已通知
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, or_, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.i18n import t
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
                        (
                            "case_timeout 配置无效或未设置，跳过检测。请在 sys_conf 表中插入配置："
                            "INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag) "
                            "VALUES ('case_timeout', '30', 'Case超时时间(分钟)', 0, 0);"
                        ),
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

            # 2. 查询超时的 host_exec_log 记录（优先使用 due_time，否则使用 case_timeout）
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

            # 3. 发送邮件通知
            success_count = 0
            failed_count = 0

            for exec_log in timeout_cases:
                if not exec_log.host_id:
                    logger.warning(
                        "执行日志记录缺少 host_id，跳过",
                        extra={"log_id": exec_log.id},
                    )
                    failed_count += 1
                    continue

                # 发送邮件通知
                success = await self._send_timeout_email_notification(exec_log)

                if success:
                    success_count += 1
                    logger.info(
                        "超时邮件通知已发送",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                            "tc_id": exec_log.tc_id,
                        },
                    )
                else:
                    failed_count += 1
                    logger.error(
                        "超时邮件通知发送失败",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )

            logger.info(
                "超时检测完成",
                extra={
                    "total": len(timeout_cases),
                    "success": success_count,
                    "failed": failed_count,
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
                        logger.warning("缓存中的 case_timeout 配置格式无效，将从数据库重新获取")
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

    async def _query_timeout_cases(self, timeout_minutes: int) -> List[HostExecLog]:
        """查询超时的 host_exec_log 记录

        超时判断逻辑：
        1. 如果存在 due_time，则判断 due_time < 当前时间
        2. 如果不存在 due_time，则判断 begin_time < 当前时间 - timeout_minutes
        3. 只查询 notify_state = 0（未通知）的记录，避免重复通知

        Args:
            timeout_minutes: 超时时间（分钟，当 due_time 不存在时使用）

        Returns:
            超时的执行日志记录列表（仅包含未通知的记录）
        """
        try:
            now = datetime.now(timezone.utc)
            timeout_threshold = now - timedelta(minutes=timeout_minutes)

            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # 查询条件：
                # - host_state in (2, 3)  # 已占用或case执行中
                # - case_state = 1        # 启动
                # - del_flag = 0          # 未删除
                # - notify_state = 0      # 未通知
                # - (due_time IS NOT NULL AND due_time < 当前时间) OR
                #   (due_time IS NULL AND begin_time < 当前时间 - timeout_minutes)
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_state.in_([2, 3]),
                            HostExecLog.case_state == 1,
                            HostExecLog.del_flag == 0,
                            HostExecLog.notify_state == 0,  # 只查询未通知的记录
                            or_(
                                and_(
                                    HostExecLog.due_time.is_not(None),
                                    HostExecLog.due_time < now,
                                ),
                                and_(
                                    HostExecLog.due_time.is_(None),
                                    HostExecLog.begin_time < timeout_threshold,
                                ),
                            ),
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
                        "now": now.isoformat(),
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

    async def _send_timeout_email_notification(self, exec_log: HostExecLog) -> bool:
        """发送任务超时邮件通知

        发送邮件成功后，会自动更新 notify_state = 1（已通知），
        确保同一条记录不会被重复通知。

        Args:
            exec_log: 执行日志记录

        Returns:
            是否通知成功（成功时会更新 notify_state = 1）
        """
        try:
            # 1. 查询 host_rec 表获取 hardware_id 和 host_ip
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                host_stmt = select(HostRec).where(
                    and_(
                        HostRec.id == exec_log.host_id,
                        HostRec.del_flag == 0,
                    )
                )
                host_result = await session.execute(host_stmt)
                host_rec = host_result.scalar_one_or_none()

                if not host_rec:
                    logger.warning(
                        "未找到主机记录，跳过邮件通知",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )
                    return False

                hardware_id = host_rec.hardware_id or "-"
                host_ip = host_rec.host_ip or "-"

                # 2. 查询 sys_conf 表获取邮箱配置
                email_stmt = (
                    select(SysConf)
                    .where(
                        and_(
                            SysConf.conf_key == "email",
                            SysConf.state_flag == 0,
                            SysConf.del_flag == 0,
                        )
                    )
                    .order_by(SysConf.updated_time.desc())
                    .limit(1)
                )
                email_result = await session.execute(email_stmt)
                email_conf = email_result.scalar_one_or_none()

                if not email_conf or not email_conf.conf_val:
                    logger.warning(
                        "未找到邮箱配置，跳过邮件通知",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )
                    return False

                # 3. 解析邮箱列表
                email_str = email_conf.conf_val.strip()
                email_list = [e.strip() for e in email_str.split(",") if e.strip()]

                if not email_list:
                    logger.warning(
                        "邮箱列表为空，跳过邮件通知",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                        },
                    )
                    return False

                # 4. 构建邮件内容
                begin_time_str = exec_log.begin_time.isoformat() if exec_log.begin_time else "-"
                due_time_str = exec_log.due_time.isoformat() if exec_log.due_time else "-"

                subject = t(
                    "email.case.timeout.subject",
                    locale="zh_CN",
                    default="测试用例执行超时通知",
                )

                content = self._build_timeout_email_content(
                    hardware_id=hardware_id,
                    host_ip=host_ip,
                    begin_time=begin_time_str,
                    due_time=due_time_str,
                    tc_id=exec_log.tc_id or "-",
                    log_id=exec_log.id,
                )

                # 5. 发送邮件
                email_result = await send_email(
                    to_emails=email_list,
                    subject=subject,
                    content=content,
                    locale="zh_CN",
                )

                if email_result.get("sent_count", 0) > 0:
                    # 6. 邮件发送成功后，更新 notify_state = 1（已通知）
                    update_stmt = (
                        update(HostExecLog)
                        .where(HostExecLog.id == exec_log.id)
                        .values(notify_state=1)
                    )
                    await session.execute(update_stmt)
                    await session.commit()

                    logger.info(
                        "超时邮件通知发送成功，已更新通知状态",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                            "sent_count": email_result.get("sent_count", 0),
                            "recipient_count": len(email_list),
                            "notify_state": 1,
                        },
                    )
                    return True
                else:
                    logger.error(
                        "超时邮件通知发送失败",
                        extra={
                            "host_id": exec_log.host_id,
                            "log_id": exec_log.id,
                            "errors": email_result.get("errors", []),
                        },
                    )
                    return False

        except Exception as e:
            logger.error(
                "发送超时邮件通知异常",
                extra={
                    "host_id": exec_log.host_id,
                    "log_id": exec_log.id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return False

    def _build_timeout_email_content(
        self,
        hardware_id: str,
        host_ip: str,
        begin_time: str,
        due_time: str,
        tc_id: str,
        log_id: int,
    ) -> str:
        """构建超时邮件内容

        Args:
            hardware_id: 硬件ID
            host_ip: 主机IP
            begin_time: 开始时间
            due_time: 预期结束时间
            tc_id: 测试用例ID
            log_id: 执行日志ID

        Returns:
            HTML格式的邮件内容
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #FF6B6B;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
            margin-bottom: 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 5px 5px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #FF6B6B;
        }}
        .info-item {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}
        .info-item::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #FF6B6B;
            font-weight: bold;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
        }}
        .info-value {{
            color: #333;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #888;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">测试用例执行超时通知</h2>
    </div>
    <div class="content">
        <p style="font-size: 16px; margin-top: 0;">尊敬的维护人员：</p>

        <p style="font-size: 15px; color: #2c3e50; margin: 20px 0;">
            检测到测试用例执行超时，请及时关注。
        </p>

        <div class="section">
            <div class="section-title">超时任务信息</div>
            <div class="info-item">
                <span class="info-label">Hardware ID：</span>
                <span class="info-value">{hardware_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Host IP：</span>
                <span class="info-value">{host_ip}</span>
            </div>
            <div class="info-item">
                <span class="info-label">测试用例ID：</span>
                <span class="info-value">{tc_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">执行日志ID：</span>
                <span class="info-value">{log_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">开始时间：</span>
                <span class="info-value">{begin_time}</span>
            </div>
            <div class="info-item">
                <span class="info-label">预期结束时间：</span>
                <span class="info-value">{due_time}</span>
            </div>
        </div>

        <p style="margin-top: 25px; color: #555;">
            请及时关注相关任务执行情况。
        </p>

        <div class="footer">
            此邮件由系统自动发送，请勿回复。
        </div>
    </div>
</body>
</html>
"""


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
