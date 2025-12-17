"""Agent 信息上报服务

处理 Agent 上报的信息，包括：
1. 硬件模板验证
2. 版本号对比
3. 硬件内容深度对比
4. 数据库记录更新
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.models.host_exec_log import HostExecLog

    from shared.common.database import generate_snowflake_id, mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.json_comparator import JSONComparator
    from shared.utils.template_validator import TemplateValidator
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.models.host_exec_log import HostExecLog

    from shared.common.database import generate_snowflake_id, mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.json_comparator import JSONComparator
    from shared.utils.template_validator import TemplateValidator

logger = get_logger(__name__)


class AgentReportService:
    """Agent 信息上报服务"""

    # 硬件差异状态
    DIFF_STATE_VERSION = 1  # 版本号变化
    DIFF_STATE_CONTENT = 2  # 内容更改
    DIFF_STATE_FAILED = 3  # 异常

    # 同步状态
    SYNC_STATE_EMPTY = 0  # 空状态
    SYNC_STATE_WAIT = 1  # 待同步
    SYNC_STATE_SUCCESS = 2  # 通过
    SYNC_STATE_FAILED = 3  # 异常

    # 审批状态
    APPR_STATE_ENABLE = 1  # 启用
    APPR_STATE_CHANGE = 2  # 存在改动

    # 主机状态
    HOST_STATE_HW_CHANGE = 6  # 存在潜在的硬件改动

    def __init__(self):
        """初始化服务"""
        # 初始化JSON对比工具
        self.json_comparator = JSONComparator()
        # 初始化模板验证器
        self.template_validator = TemplateValidator()

    async def report_hardware(
        self,
        host_id: int,
        hardware_data: Dict[str, Any],
        report_type: int = 0,
    ) -> Dict[str, Any]:
        """上报硬件信息

        Args:
            host_id: 主机ID（从token中获取）
            hardware_data: 硬件信息（动态JSON）
            report_type: 上报类型（0-成功，1-异常）

        Returns:
            处理结果

        Raises:
            BusinessError: 业务逻辑错误
        """
        try:
            logger.info(
                "开始处理硬件信息上报",
                extra={
                    "host_id": host_id,
                    "hardware_keys": list(hardware_data.keys()),
                    "report_type": report_type,
                },
            )

            # 1. 提取 dmr_config（必传）
            dmr_config = hardware_data.get("dmr_config")
            if not dmr_config:
                raise BusinessError(
                    message="dmr_config 是必传字段",
                    error_code="MISSING_DMR_CONFIG",
                    code=400,
                )

            # 2. 提取版本号（必传）
            current_revision = dmr_config.get("revision")
            if current_revision is None:
                raise BusinessError(
                    message="dmr_config.revision 是必传字段",
                    error_code="MISSING_REVISION",
                    code=400,
                )

            # 3. 获取当前生效的硬件记录
            current_hw_rec = await self._get_current_hardware_record(host_id)

            # 4. 根据 report_type 决定处理逻辑
            if report_type == 1:
                # 异常类型：直接设置 diff_state=3，跳过对比逻辑
                logger.info(
                    "硬件信息上报类型为异常，直接设置 diff_state=3",
                    extra={
                        "host_id": host_id,
                        "report_type": report_type,
                    },
                )

                diff_state = self.DIFF_STATE_FAILED  # 3
                diff_details = {"report_type": "异常", "reason": "Agent 上报异常类型"}

                # 更新数据库记录
                result = await self._update_hardware_records(
                    host_id=host_id,
                    hardware_data=hardware_data,
                    dmr_config=dmr_config,
                    current_revision=current_revision,
                    diff_state=diff_state,
                    diff_details=diff_details,
                    current_hw_rec=current_hw_rec,
                )

                logger.info(
                    "硬件信息异常上报处理完成",
                    extra={
                        "host_id": host_id,
                        "diff_state": diff_state,
                        "result": result,
                    },
                )

                return result

            # 5. 正常类型（report_type=0）：走原来的对比逻辑
            # 获取硬件模板
            hw_template = await self._get_hardware_template()
            if not hw_template:
                raise BusinessError(
                    message="未找到硬件模板配置",
                    error_code="HARDWARE_TEMPLATE_NOT_FOUND",
                    code=500,
                )

            # 6. 验证硬件信息必填字段
            self._validate_required_fields(dmr_config, hw_template)

            # 7. 对比硬件信息
            diff_state, diff_details = await self._compare_hardware(
                current_revision=current_revision,
                current_dmr_config=dmr_config,
                current_hw_rec=current_hw_rec,
                hw_template=hw_template,
            )

            # 8. 更新数据库记录
            result = await self._update_hardware_records(
                host_id=host_id,
                hardware_data=hardware_data,
                dmr_config=dmr_config,
                current_revision=current_revision,
                diff_state=diff_state,
                diff_details=diff_details if diff_details else {},
                current_hw_rec=current_hw_rec,
            )

            logger.info(
                "硬件信息上报处理完成",
                extra={
                    "host_id": host_id,
                    "diff_state": diff_state,
                    "result": result,
                },
            )

            return result

        except BusinessError:
            raise
        except Exception as e:
            logger.error(f"硬件信息上报异常: {e!s}", exc_info=True)
            raise BusinessError(
                message="硬件信息上报处理失败",
                error_code="HARDWARE_REPORT_FAILED",
                code=500,
            )

    async def get_latest_ota_configs(self) -> List[Dict[str, Optional[str]]]:
        """获取最新 OTA 配置信息列表"""
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            stmt = (
                select(SysConf)
                .where(
                    and_(
                        SysConf.conf_key == "ota",
                        SysConf.state_flag == 0,
                        SysConf.del_flag == 0,
                    )
                )
                .order_by(SysConf.updated_time.desc(), SysConf.id.desc())
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                logger.info("未查询到 OTA 配置，返回空列表")
                return []

            logger.info(
                "获取 OTA 配置成功",
                extra={
                    "count": len(records),
                },
            )

            ota_configs = []
            for record in records:
                conf_data = record.conf_json or {}
                ota_configs.append(
                    {
                        "conf_name": record.conf_name,
                        "conf_ver": record.conf_ver,
                        "conf_url": conf_data.get("conf_url"),
                        "conf_md5": conf_data.get("conf_md5"),
                    }
                )
            return ota_configs

    async def _get_hardware_template(self) -> Optional[Dict[str, Any]]:
        """获取硬件模板配置

        从 sys_conf 表查询 conf_key='hw_temp', state_flag=0, del_flag=0 的配置

        Returns:
            硬件模板配置（conf_json 字段）
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = select(SysConf).where(
                    and_(
                        SysConf.conf_key == "hw_temp",
                        SysConf.state_flag == 0,
                        SysConf.del_flag == 0,
                    )
                )

                result = await session.execute(stmt)
                conf = result.scalar_one_or_none()

                if not conf:
                    logger.warning("未找到硬件模板配置（conf_key='hw_temp'）")
                    return None

                return conf.conf_json

        except Exception as e:
            logger.error(f"获取硬件模板配置失败: {e!s}", exc_info=True)
            return None

    def _validate_required_fields(self, dmr_config: Dict[str, Any], hw_template: Dict[str, Any]) -> None:
        """验证硬件信息必填字段

        遍历硬件模板，检查值为 'required' 的字段是否在上报数据中存在

        Args:
            dmr_config: Agent 上报的硬件配置
            hw_template: 硬件模板配置

        Raises:
            BusinessError: 缺少必填字段时抛出
        """
        # 使用模板验证器工具类进行验证
        self.template_validator.validate_required_fields(dmr_config, hw_template)
        logger.info("硬件信息必填字段验证通过")

    async def _get_current_hardware_record(self, host_id: int) -> Optional[HostHwRec]:
        """获取当前生效的硬件记录

        查询 host_hw_rec 表中最新的硬件记录

        Args:
            host_id: 主机ID

        Returns:
            最新的硬件记录，如果不存在则返回None
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = (
                    select(HostHwRec)
                    .where(
                        and_(
                            HostHwRec.host_id == host_id,
                            HostHwRec.del_flag == 0,
                        )
                    )
                    .order_by(HostHwRec.id.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取当前硬件记录失败: {e!s}", exc_info=True)
            return None

    async def _compare_hardware(
        self,
        current_revision: int,
        current_dmr_config: Dict[str, Any],
        current_hw_rec: Optional[HostHwRec],
        hw_template: Dict[str, Any],
    ) -> Tuple[Optional[int], Dict[str, Any]]:
        """对比硬件信息

        Args:
            current_revision: 当前上报的版本号
            current_dmr_config: 当前上报的硬件配置
            current_hw_rec: 当前生效的硬件记录
            hw_template: 硬件模板

        Returns:
            (差异状态, 差异详情)
            - 差异状态: DIFF_STATE_VERSION | DIFF_STATE_CONTENT | None
            - 差异详情: 差异信息字典
        """
        try:
            # 如果没有历史记录，说明是第一次上报（不需要对比）
            if not current_hw_rec or not current_hw_rec.hw_info:
                logger.info("主机首次上报硬件信息，无需对比")
                return None, {}

            previous_hw_info = current_hw_rec.hw_info
            previous_revision = previous_hw_info.get("dmr_config", {}).get("revision")

            # 1. 对比版本号
            if previous_revision is not None and current_revision != previous_revision:
                logger.info(
                    "硬件版本号变化",
                    extra={
                        "previous": previous_revision,
                        "current": current_revision,
                    },
                )
                return self.DIFF_STATE_VERSION, {
                    "previous_revision": previous_revision,
                    "current_revision": current_revision,
                }

            # 2. 对比内容（深度JSON对比，使用工具类）
            content_diff = self.json_comparator.compare(
                previous_hw_info.get("dmr_config", {}),
                current_dmr_config,
            )

            if content_diff:
                logger.info(
                    "硬件内容发生变化",
                    extra={
                        "diff_count": len(content_diff),
                        "changed_fields": list(content_diff.keys()),
                    },
                )
                return self.DIFF_STATE_CONTENT, content_diff

            # 3. 无变化
            logger.info("硬件信息无变化")
            return None, {}

        except Exception as e:
            logger.error(f"硬件信息对比异常: {e!s}", exc_info=True)
            return self.DIFF_STATE_FAILED, {"error": str(e)}

    async def _update_hardware_records(
        self,
        host_id: int,
        hardware_data: Dict[str, Any],
        dmr_config: Dict[str, Any],
        current_revision: int,
        diff_state: Optional[int],
        diff_details: Dict[str, Any],
        current_hw_rec: Optional[HostHwRec],
    ) -> Dict[str, Any]:
        """更新硬件记录

        根据对比结果更新 host_rec 和 host_hw_rec 表

        Args:
            host_id: 主机ID
            hardware_data: 完整硬件数据
            dmr_config: DMR配置
            current_revision: 当前版本号
            diff_state: 差异状态
            diff_details: 差异详情
            current_hw_rec: 当前硬件记录

        Returns:
            更新结果
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # 如果有差异，需要更新 host_rec 和插入新的 host_hw_rec
                if diff_state:
                    # 1. 查询 host_rec 获取 hardware_id 和 host_ip（用于邮件通知）
                    host_rec_stmt = select(HostRec).where(
                        and_(
                            HostRec.id == host_id,
                            HostRec.del_flag == 0,
                        )
                    )
                    host_rec_result = await session.execute(host_rec_stmt)
                    host_rec = host_rec_result.scalar_one_or_none()

                    # 2. 更新 host_rec 表
                    await self._update_host_rec(session, host_id)

                    # 3. 插入新的 host_hw_rec 记录
                    new_hw_rec = await self._insert_hardware_record(
                        session=session,
                        host_id=host_id,
                        hardware_data=hardware_data,
                        hw_ver=str(current_revision),
                        diff_state=diff_state,
                    )

                    await session.commit()

                    # 4. 发送硬件变更邮件通知（异步，不阻塞主流程）
                    if host_rec:
                        asyncio.create_task(
                            self._send_hardware_change_notification(
                                host_id=host_id,
                                hardware_id=host_rec.hardware_id or "未知",
                                host_ip=host_rec.host_ip or "未知",
                                diff_state=diff_state,
                                hw_rec_id=new_hw_rec.id,
                            )
                        )

                    return {
                        "status": "hardware_changed",
                        "diff_state": diff_state,
                        "diff_details": diff_details,
                        "hw_rec_id": new_hw_rec.id,
                        "message": "硬件信息已更新，等待审批",
                    }

                # 如果是首次上报（无历史记录）
                if not current_hw_rec:
                    # 插入第一条硬件记录（appr_state=1, 等待审批）
                    new_hw_rec = await self._insert_hardware_record(
                        session=session,
                        host_id=host_id,
                        hardware_data=hardware_data,
                        hw_ver=str(current_revision),
                        diff_state=None,
                        sync_state=self.SYNC_STATE_WAIT,  # 等待审批
                    )

                    await session.commit()

                    return {
                        "status": "first_report",
                        "hw_rec_id": new_hw_rec.id,
                        "message": "硬件信息首次上报成功",
                    }

                # 无变化
                return {
                    "status": "no_change",
                    "message": "硬件信息无变化",
                }

        except Exception as e:
            logger.error(f"更新硬件记录失败: {e!s}", exc_info=True)
            raise BusinessError(
                message="更新硬件记录失败",
                error_code="UPDATE_HARDWARE_FAILED",
                code=500,
            )

    async def _update_host_rec(self, session, host_id: int) -> None:
        """更新 host_rec 表

        设置 appr_state=2（存在改动），host_state=6（存在潜在的硬件改动）

        Args:
            session: 数据库会话
            host_id: 主机ID
        """
        try:
            stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,
                    )
                )
                .values(
                    appr_state=self.APPR_STATE_CHANGE,
                    host_state=self.HOST_STATE_HW_CHANGE,
                )
            )

            await session.execute(stmt)

            logger.info(f"更新 host_rec 成功: host_id={host_id}")

        except Exception as e:
            logger.error(f"更新 host_rec 失败: {e!s}", exc_info=True)
            raise

    async def _insert_hardware_record(
        self,
        session,
        host_id: int,
        hardware_data: Dict[str, Any],
        hw_ver: str,
        diff_state: Optional[int],
        sync_state: int = SYNC_STATE_WAIT,
    ) -> HostHwRec:
        """插入新的硬件记录

        Args:
            session: 数据库会话
            host_id: 主机ID
            hardware_data: 完整硬件数据
            hw_ver: 硬件版本号
            diff_state: 差异状态
            sync_state: 同步状态

        Returns:
            新创建的硬件记录
        """
        try:
            # 生成雪花ID
            new_id = generate_snowflake_id()

            new_hw_rec = HostHwRec(
                id=new_id,  # 显式设置雪花ID
                host_id=host_id,
                hw_info=hardware_data,  # 存储完整的硬件数据
                hw_ver=hw_ver,
                diff_state=diff_state,
                sync_state=sync_state,
            )

            session.add(new_hw_rec)
            await session.flush()  # 确保数据已写入

            logger.info(f"插入新硬件记录成功: hw_rec_id={new_hw_rec.id}, host_id={host_id}")

            return new_hw_rec

        except Exception as e:
            logger.error(f"插入硬件记录失败: {e!s}", exc_info=True)
            raise

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

            session_factory = mariadb_manager.get_session()
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
                    f"找到执行日志记录: log_id={exec_log.id}, 当前状态={exec_log.case_state}",
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
                    "host_id": str(host_id),  # ✅ 转换为字符串避免精度丢失
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
                f"测试用例结果上报失败: {e!s}",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="测试用例结果上报处理失败",
                error_code="TESTCASE_REPORT_FAILED",
                code=500,
            )

    async def _send_hardware_change_notification(
        self,
        host_id: int,
        hardware_id: str,
        host_ip: str,
        diff_state: int,
        hw_rec_id: int,
    ) -> None:
        """发送硬件变更邮件通知

        Args:
            host_id: 主机ID
            hardware_id: 硬件ID
            host_ip: 主机IP
            diff_state: 变更类型（1=版本号变化，2=内容更改）
            hw_rec_id: 硬件记录ID
        """
        try:
            # 1. 获取收件人邮箱列表（从系统配置中获取）
            maintain_emails = await self._get_maintain_emails()
            if not maintain_emails:
                logger.warning("未配置维护人员邮箱，跳过硬件变更邮件通知")
                return

            # 2. 确定变更类型
            change_type_map = {
                self.DIFF_STATE_VERSION: "版本号变化",
                self.DIFF_STATE_CONTENT: "内容更改",
            }
            change_type = change_type_map.get(diff_state, "未知变更")

            # 3. 构建邮件主题和内容
            subject = f"硬件变更通知 - Host ID: {host_id}"
            content = self._build_hardware_change_email_content(
                host_id=host_id,
                hardware_id=hardware_id,
                host_ip=host_ip,
                change_type=change_type,
                hw_rec_id=hw_rec_id,
            )

            # 4. 发送邮件
            result = await send_email(
                to_emails=maintain_emails,
                subject=subject,
                content=content,
                locale="zh_CN",
            )

            if result.get("success"):
                logger.info(
                    "硬件变更邮件通知发送成功",
                    extra={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "host_ip": host_ip,
                        "change_type": change_type,
                        "sent_count": result.get("sent_count", 0),
                    },
                )
            else:
                logger.warning(
                    "硬件变更邮件通知发送失败",
                    extra={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "host_ip": host_ip,
                        "change_type": change_type,
                        "errors": result.get("errors", []),
                    },
                )

        except Exception as e:
            # 邮件发送失败不影响主流程，只记录日志
            logger.error(
                f"发送硬件变更邮件通知异常: {e!s}",
                extra={
                    "host_id": host_id,
                    "hardware_id": hardware_id,
                    "host_ip": host_ip,
                    "diff_state": diff_state,
                },
                exc_info=True,
            )

    async def _get_maintain_emails(self) -> List[str]:
        """获取维护人员邮箱列表

        从 sys_conf 表查询 conf_key='maintain_email' 的配置

        Returns:
            维护人员邮箱列表
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = select(SysConf).where(
                    and_(
                        SysConf.conf_key == "maintain_email",
                        SysConf.state_flag == 0,
                        SysConf.del_flag == 0,
                    )
                )

                result = await session.execute(stmt)
                conf = result.scalar_one_or_none()

                if not conf or not conf.conf_json:
                    logger.warning("未找到维护人员邮箱配置（conf_key='maintain_email'）")
                    return []

                # conf_json 可能是字符串列表或逗号分隔的字符串
                emails = conf.conf_json
                if isinstance(emails, str):
                    # 如果是字符串，按逗号分割
                    emails = [email.strip() for email in emails.split(",") if email.strip()]
                elif isinstance(emails, list):
                    # 如果是列表，直接使用
                    emails = [str(email).strip() for email in emails if email]
                else:
                    logger.warning(f"维护人员邮箱配置格式不正确: {type(emails)}")
                    return []

                return emails

        except Exception as e:
            logger.error(f"获取维护人员邮箱列表失败: {e!s}", exc_info=True)
            return []

    def _build_hardware_change_email_content(
        self,
        host_id: int,
        hardware_id: str,
        host_ip: str,
        change_type: str,
        hw_rec_id: int,
    ) -> str:
        """构建硬件变更邮件内容（HTML格式）

        Args:
            host_id: 主机ID
            hardware_id: 硬件ID
            host_ip: 主机IP
            change_type: 变更类型
            hw_rec_id: 硬件记录ID

        Returns:
            HTML格式的邮件内容
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border: 1px solid #ddd;
            border-top: none;
        }}
        .section {{
            margin: 20px 0;
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            color: #4CAF50;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #4CAF50;
        }}
        .info-item {{
            margin: 10px 0;
            padding: 8px;
            background-color: #f5f5f5;
            border-radius: 3px;
        }}
        .info-label {{
            font-weight: bold;
            color: #555;
            display: inline-block;
            width: 120px;
        }}
        .info-value {{
            color: #333;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #888;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">硬件变更通知</h2>
    </div>
    <div class="content">
        <p style="font-size: 16px; margin-top: 0;">尊敬的维护人员：</p>

        <p style="font-size: 15px; color: #2c3e50; margin: 20px 0;">
            检测到主机硬件信息发生变化，请及时关注。
        </p>

        <div class="section">
            <div class="section-title">变更信息</div>
            <div class="info-item">
                <span class="info-label">主机ID：</span>
                <span class="info-value">{host_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">硬件ID：</span>
                <span class="info-value">{hardware_id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">主机IP：</span>
                <span class="info-value">{host_ip}</span>
            </div>
            <div class="info-item">
                <span class="info-label">变更类型：</span>
                <span class="info-value">{change_type}</span>
            </div>
            <div class="info-item">
                <span class="info-label">硬件记录ID：</span>
                <span class="info-value">{hw_rec_id}</span>
            </div>
        </div>

        <p style="margin-top: 25px; color: #555;">
            请登录系统查看详细信息并进行审批。
        </p>

        <div class="footer">
            此邮件由系统自动发送，请勿回复。
        </div>
    </div>
</body>
</html>
"""


# 全局服务实例（单例模式）
_agent_report_service_instance: Optional[AgentReportService] = None


def get_agent_report_service() -> AgentReportService:
    """获取Agent硬件服务实例（单例模式）"""
    global _agent_report_service_instance

    if _agent_report_service_instance is None:
        _agent_report_service_instance = AgentReportService()

    return _agent_report_service_instance
