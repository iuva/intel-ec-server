"""Agent 信息上报服务

处理 Agent 上报的信息，包括：
1. 硬件模板验证
2. 版本号对比
3. 硬件内容深度对比
4. 数据库记录更新
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.constants.host_constants import (
        HOST_STATE_FREE,
        HOST_STATE_LOCKED,
        HOST_STATE_OCCUPIED,
    )
    from app.models.host_exec_log import HostExecLog
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from shared.common.cache import redis_manager
    from shared.common.database import generate_snowflake_id, mariadb_manager
    from shared.common.email_sender import send_email
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.json_comparator import JSONComparator
    from shared.utils.template_validator import TemplateValidator
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import (
        HOST_STATE_FREE,
        HOST_STATE_LOCKED,
        HOST_STATE_OCCUPIED,
    )
    from app.models.host_exec_log import HostExecLog
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from shared.common.cache import redis_manager
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
        # ✅ 优化：缓存会话工厂，避免每次操作都调用 get_session()
        self._session_factory = None

    @property
    def session_factory(self):
        """获取会话工厂（延迟初始化，单例模式）

        ✅ 优化：缓存会话工厂，避免重复获取
        - 第一次调用时初始化
        - 后续调用复用缓存的工厂实例
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

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
                    code=ServiceErrorCodes.HOST_MISSING_DMR_CONFIG,
                    http_status_code=400,
                )

            # 2. 提取版本号（必传）
            current_revision = dmr_config.get("revision")
            if current_revision is None:
                raise BusinessError(
                    message="dmr_config.revision 是必传字段",
                    error_code="MISSING_REVISION",
                    code=ServiceErrorCodes.HOST_MISSING_REVISION,
                    http_status_code=400,
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
                    code=ServiceErrorCodes.HOST_HARDWARE_TEMPLATE_NOT_FOUND,
                    http_status_code=500,
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
            logger.error(
                "硬件信息上报异常",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise BusinessError(
                message="硬件信息上报处理失败",
                error_code="HARDWARE_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_HARDWARE_REPORT_FAILED,
                http_status_code=500,
            )

    async def get_latest_ota_configs(self) -> List[Dict[str, Optional[str]]]:
        """获取最新 OTA 配置信息列表（带缓存）

        使用 Redis 缓存 OTA 配置，缓存时间 5 分钟，减少数据库查询压力。
        """
        # 缓存键
        cache_key = "ota_configs:latest"

        # 尝试从缓存获取
        try:
            cached_configs = await redis_manager.get(cache_key)
            if cached_configs is not None:
                logger.debug(
                    "从缓存获取 OTA 配置",
                    extra={
                        "cache_key": cache_key,
                        "count": len(cached_configs) if isinstance(cached_configs, list) else 0,
                    },
                )
                return cached_configs
        except Exception as e:
            logger.warning(
                "从缓存获取 OTA 配置失败，将查询数据库",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # 缓存未命中，查询数据库
        session_factory = self.session_factory
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
                # 缓存空结果，避免频繁查询（缓存时间缩短为 1 分钟）
                try:
                    await redis_manager.set(cache_key, [], expire=60)
                except Exception as e:
                    logger.warning(
                        "缓存空结果失败",
                        extra={"cache_key": cache_key, "error": str(e)},
                    )
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

            # 存入缓存，5 分钟过期
            try:
                await redis_manager.set(cache_key, ota_configs, expire=300)
                logger.debug(
                    "OTA 配置已缓存",
                    extra={"cache_key": cache_key, "count": len(ota_configs), "expire_seconds": 300},
                )
            except Exception as e:
                logger.warning(
                    "缓存 OTA 配置失败",
                    extra={"cache_key": cache_key, "error": str(e)},
                )

            return ota_configs

    async def _get_hardware_template(self) -> Optional[Dict[str, Any]]:
        """获取硬件模板配置（带缓存）

        从 sys_conf 表查询 conf_key='hw_temp', state_flag=0, del_flag=0 的配置。
        使用 Redis 缓存模板数据，缓存时间 5 分钟，减少数据库查询压力。

        Returns:
            硬件模板配置（conf_json 字段）
        """
        # 缓存键
        cache_key = "hardware_template"

        # 尝试从缓存获取
        try:
            cached_template = await redis_manager.get(cache_key)
            if cached_template is not None:
                logger.debug(
                    "从缓存获取硬件模板",
                    extra={"cache_key": cache_key},
                )
                return cached_template
        except Exception as e:
            logger.warning(
                "从缓存获取硬件模板失败，将查询数据库",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # 缓存未命中，查询数据库
        try:
            session_factory = self.session_factory
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
                    # 缓存 None 结果，避免频繁查询（缓存时间缩短为 1 分钟）
                    try:
                        await redis_manager.set(cache_key, None, expire=60)
                    except Exception as e:
                        logger.warning(
                            "缓存空结果失败",
                            extra={"cache_key": cache_key, "error": str(e)},
                        )
                    return None

                template = conf.conf_json

                # 存入缓存，5 分钟过期
                try:
                    await redis_manager.set(cache_key, template, expire=300)
                    logger.debug(
                        "硬件模板已缓存",
                        extra={"cache_key": cache_key, "expire_seconds": 300},
                    )
                except Exception as e:
                    logger.warning(
                        "缓存硬件模板失败",
                        extra={"cache_key": cache_key, "error": str(e)},
                    )

                return template

        except Exception as e:
            logger.error(
                "获取硬件模板配置失败",
                extra={"error": str(e)},
                exc_info=True,
            )
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

    async def _get_current_hardware_record(
        self, host_id: int, session: Optional[Any] = None
    ) -> Optional[HostHwRec]:
        """获取当前生效的硬件记录

        查询 host_hw_rec 表中最新的硬件记录

        ✅ 优化：支持传入外部会话，避免创建新会话

        Args:
            host_id: 主机ID
            session: 可选的外部会话（如果不传则创建新会话）

        Returns:
            最新的硬件记录，如果不存在则返回None
        """
        try:
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

            # ✅ 优化：如果传入了会话则直接使用，否则创建新会话
            if session:
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            else:
                session_factory = self.session_factory
                async with session_factory() as new_session:
                    result = await new_session.execute(stmt)
                    return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "获取当前硬件记录失败",
                extra={"host_id": host_id, "error": str(e)},
                exc_info=True,
            )
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
            logger.error(
                "硬件信息对比异常",
                extra={"error": str(e)},
                exc_info=True,
            )
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
            session_factory = self.session_factory
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
            logger.error(
                "更新硬件记录失败",
                extra={"host_id": host_id, "error": str(e)},
                exc_info=True,
            )
            raise BusinessError(
                message="更新硬件记录失败",
                error_code="UPDATE_HARDWARE_FAILED",
                code=ServiceErrorCodes.HOST_UPDATE_HARDWARE_FAILED,
                http_status_code=500,
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

            logger.info(
                "更新 host_rec 成功",
                extra={"host_id": host_id},
            )

        except Exception as e:
            logger.error(
                "更新 host_rec 失败",
                extra={"host_id": host_id, "error": str(e)},
                exc_info=True,
            )
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

            logger.info(
                "插入新硬件记录成功",
                extra={
                    "hw_rec_id": new_hw_rec.id,
                    "host_id": host_id,
                },
            )

            return new_hw_rec

        except Exception as e:
            logger.error(
                "插入硬件记录失败",
                extra={"host_id": host_id, "error": str(e)},
                exc_info=True,
            )
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
                    "current_time": now.isoformat(),
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. 查询执行中的最新执行日志记录
                # 查询条件：host_id, tc_id, case_state=1（启动状态）, del_flag=0
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id,
                            HostExecLog.tc_id == tc_id,
                            HostExecLog.case_state == 1,  # 启动状态（执行中）
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
                        message=f"未找到主机 {host_id} 的测试用例 {tc_id} 执行中的记录",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "找到执行中的日志记录",
                    extra={
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "log_id": exec_log.id,
                        "current_due_time": exec_log.due_time.isoformat() if exec_log.due_time else None,
                    },
                )

                # 2. 更新 due_time
                update_stmt = (
                    update(HostExecLog)
                    .where(HostExecLog.id == exec_log.id)
                    .values(due_time=due_time)
                )

                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "预期结束时间更新完成",
                    extra={
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "log_id": exec_log.id,
                        "due_time": due_time.isoformat(),
                    },
                )

                return {
                    "host_id": str(host_id),
                    "tc_id": tc_id,
                    "due_time": due_time,
                    "updated": True,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "预期结束时间上报处理异常",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="预期结束时间上报处理失败",
                error_code="DUE_TIME_UPDATE_FAILED",
                code=ServiceErrorCodes.HOST_DUE_TIME_UPDATE_FAILED,
                http_status_code=500,
            )

    async def report_vnc_connection_state(
        self, host_id: int, vnc_state: int
    ) -> Dict[str, Any]:
        """Agent 上报 VNC 连接状态

        业务逻辑：
        1. 从 token 中解析 host_id（已在依赖注入中完成）
        2. 根据 vnc_state 和当前 host_state 更新主机状态：
            - 当 `vnc_state = 1`（连接成功）时：
                - 如果 `host_state = 1`（已锁定），则修改为 `host_state = 2`（已占用）
            - 当 `vnc_state = 2`（连接断开）时：
                - 如果 `host_state = 2`（已占用），则修改为 `host_state = 0`（空闲）

        Args:
            host_id: 主机ID（从token中获取）
            vnc_state: VNC连接状态（1=连接成功，2=连接断开）

        Returns:
            更新结果，包含 host_id、host_state、vnc_state 和 updated 字段

        Raises:
            BusinessError: 业务逻辑错误
        """
        try:
            logger.info(
                "开始处理 Agent VNC 连接状态上报",
                extra={
                    "host_id": host_id,
                    "vnc_state": vnc_state,
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. 查询 host_rec 表，验证主机是否存在
                stmt = select(HostRec).where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,
                    )
                )
                result = await session.execute(stmt)
                host_rec = result.scalar_one_or_none()

                if not host_rec:
                    logger.warning(
                        "主机不存在或已删除",
                        extra={
                            "host_id": host_id,
                            "vnc_state": vnc_state,
                        },
                    )
                    raise BusinessError(
                        message=f"主机不存在: {host_id}",
                        error_code="HOST_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_NOT_FOUND,
                        http_status_code=404,
                    )

                # 2. 记录更新前的状态
                old_host_state = host_rec.host_state
                current_host_state = host_rec.host_state

                # 3. 根据 vnc_state 和当前 host_state 确定新状态
                new_host_state = None
                updated = False

                if vnc_state == 1:  # 连接成功
                    if current_host_state == HOST_STATE_LOCKED:  # 1 = 已锁定
                        new_host_state = HOST_STATE_OCCUPIED  # 2 = 已占用
                        updated = True
                        logger.info(
                            "VNC连接成功，主机状态从已锁定(1)更新为已占用(2)",
                            extra={
                                "host_id": host_id,
                                "old_host_state": old_host_state,
                                "new_host_state": new_host_state,
                                "vnc_state": vnc_state,
                            },
                        )
                    else:
                        # ✅ 当 vnc_state = 1（连接成功）但 host_state 不等于 HOST_STATE_LOCKED 时，返回明确的异常
                        logger.warning(
                            "VNC连接成功，但主机状态不匹配",
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "required_host_state": HOST_STATE_LOCKED,
                                "vnc_state": vnc_state,
                            },
                        )
                        raise BusinessError(
                            message=f"VNC连接成功，但主机状态不匹配。当前状态：{current_host_state}，需要状态：{HOST_STATE_LOCKED}（已锁定）",
                            error_code="VNC_STATE_MISMATCH",
                            code=ServiceErrorCodes.HOST_VNC_STATE_MISMATCH,
                            http_status_code=400,
                            details={
                                "host_id": host_id,
                                "vnc_state": vnc_state,
                                "current_host_state": current_host_state,
                                "required_host_state": HOST_STATE_LOCKED,
                            },
                        )

                elif vnc_state == 2:  # 连接断开/失败
                    # ✅ 只有业务状态 (< 5) 的主机才会被重置为空闲，避免影响 pending/registration 状态的主机
                    if current_host_state is not None and current_host_state < 5:
                        new_host_state = HOST_STATE_FREE  # 0 = 空闲
                        updated = True
                        logger.info(
                            "VNC连接断开/失败，主机状态更新为空闲(0)",
                            extra={
                                "host_id": host_id,
                                "old_host_state": old_host_state,
                                "new_host_state": new_host_state,
                                "vnc_state": vnc_state,
                            },
                        )
                    else:
                        logger.info(
                            "VNC连接断开/失败，但主机处于非业务状态(>=5)，保持原状态",
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "vnc_state": vnc_state,
                            },
                        )

                # 4. 如果需要更新，执行更新操作
                if updated and new_host_state is not None:
                    update_stmt = (
                        update(HostRec)
                        .where(
                            and_(
                                HostRec.id == host_id,
                                HostRec.del_flag == 0,
                            )
                        )
                        .values(host_state=new_host_state)
                    )

                    await session.execute(update_stmt)
                    await session.commit()

                    # 5. 刷新对象以获取最新状态
                    await session.refresh(host_rec)
                    final_host_state = host_rec.host_state
                else:
                    # 不需要更新，使用当前状态
                    final_host_state = current_host_state

                logger.info(
                    "Agent VNC 连接状态上报处理完成",
                    extra={
                        "host_id": host_id,
                        "vnc_state": vnc_state,
                        "old_host_state": old_host_state,
                        "new_host_state": final_host_state,
                        "updated": updated,
                    },
                )

                return {
                    "host_id": host_id,
                    "host_state": final_host_state,
                    "vnc_state": vnc_state,
                    "updated": updated,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "Agent VNC 连接状态上报处理失败",
                extra={
                    "host_id": host_id,
                    "vnc_state": vnc_state,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Agent VNC 连接状态上报处理失败",
                error_code="VNC_CONNECTION_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_VNC_CONNECTION_REPORT_FAILED,
                http_status_code=500,
            )

    async def report_ota_update_status(
        self,
        host_id: int,
        app_name: str,
        app_ver: str,
        biz_state: int,
        agent_ver: Optional[str] = None,
    ) -> Dict[str, Any]:
        """上报 OTA 更新状态

        业务逻辑：
        1. 根据 host_id、app_name、app_ver 查询 host_upd 表的最新有效记录（del_flag=0）
        2. 如果未找到记录，创建新记录（在创建前，逻辑删除其他有效记录，保证有效数据只有一条）
        3. 更新 app_state 字段（1=更新中，2=成功，3=失败）
        4. 如果 biz_state=2（成功）：
           - 更新 host_rec 表的 host_state=0（free）
           - 更新 host_rec 表的 agent_ver（新版本，如果提供）
           - 逻辑删除 host_upd 表的当前记录（del_flag=1）

        Args:
            host_id: 主机ID
            app_name: 应用名称
            app_ver: 应用版本号
            biz_state: 业务状态（1=更新中，2=成功，3=失败）
            agent_ver: Agent 版本号（更新成功时必填）

        Returns:
            Dict[str, Any]: 包含更新结果的字典

        Raises:
            BusinessError: 更新失败或业务逻辑错误时抛出
        """
        try:
            logger.info(
                "开始处理 OTA 更新状态上报",
                extra={
                    "host_id": host_id,
                    "app_name": app_name,
                    "app_ver": app_ver,
                    "biz_state": biz_state,
                    "agent_ver": agent_ver,
                },
            )

            # 验证 biz_state=2 时 agent_ver 必填
            if biz_state == 2 and not agent_ver:
                raise BusinessError(
                    message="更新成功时，agent_ver 字段必填",
                    error_code="AGENT_VER_REQUIRED",
                    code=ServiceErrorCodes.HOST_AGENT_VER_REQUIRED,
                    http_status_code=400,
                )

            # 映射 biz_state 到 app_state（1=更新中，2=成功，3=失败）
            app_state = biz_state

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. 查询 host_upd 表的最新有效记录
                stmt = (
                    select(HostUpd)
                    .where(
                        and_(
                            HostUpd.host_id == host_id,
                            HostUpd.app_name == app_name,
                            HostUpd.app_ver == app_ver,
                            HostUpd.del_flag == 0,
                        )
                    )
                    .order_by(HostUpd.created_time.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                host_upd = result.scalar_one_or_none()

                is_new_record = False
                if not host_upd:
                    # 2. 如果未找到记录，先逻辑删除其他有效记录（保证有效数据只有一条）
                    logger.info(
                        "未找到 OTA 更新记录，准备创建新记录",
                        extra={
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                        },
                    )

                    # 逻辑删除该 host_id 的所有有效记录（保证有效数据只有一条）
                    delete_other_stmt = (
                        update(HostUpd)
                        .where(
                            and_(
                                HostUpd.host_id == host_id,
                                HostUpd.app_name == app_name,
                                HostUpd.del_flag == 0,
                            )
                        )
                        .values(del_flag=1)
                    )
                    deleted_result = await session.execute(delete_other_stmt)
                    deleted_count = deleted_result.rowcount

                    if deleted_count > 0:
                        logger.info(
                            "已逻辑删除其他有效记录，保证有效数据只有一条",
                            extra={
                                "host_id": host_id,
                                "app_name": app_name,
                                "deleted_count": deleted_count,
                            },
                        )

                    # 创建新记录
                    host_upd = HostUpd(
                        host_id=host_id,
                        app_name=app_name,
                        app_ver=app_ver,
                        app_state=app_state,
                        created_by=None,
                        updated_by=None,
                    )
                    session.add(host_upd)
                    await session.flush()  # 刷新以获取生成的 ID
                    is_new_record = True

                    logger.info(
                        "已创建新的 OTA 更新记录",
                        extra={
                            "host_upd_id": host_upd.id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "app_state": app_state,
                        },
                    )
                else:
                    # 3. 如果找到记录，更新 app_state
                    old_app_state = host_upd.app_state
                    update_host_upd_stmt = (
                        update(HostUpd)
                        .where(HostUpd.id == host_upd.id)
                        .values(app_state=app_state)
                    )
                    await session.execute(update_host_upd_stmt)

                    logger.info(
                        "host_upd 表状态已更新",
                        extra={
                            "host_upd_id": host_upd.id,
                            "host_id": host_id,
                            "old_app_state": old_app_state,
                            "new_app_state": app_state,
                        },
                    )

                # 4. 如果 biz_state=2（成功），更新 host_rec 表并逻辑删除 host_upd 记录
                new_host_state = None
                if biz_state == 2:
                    # 4.1 查询并更新 host_rec 表
                    host_rec_stmt = select(HostRec).where(
                        and_(
                            HostRec.id == host_id,
                            HostRec.del_flag == 0,
                        )
                    )
                    host_rec_result = await session.execute(host_rec_stmt)
                    host_rec = host_rec_result.scalar_one_or_none()

                    if not host_rec:
                        logger.warning(
                            "未找到主机记录，跳过 host_rec 表更新",
                            extra={
                                "host_id": host_id,
                                "host_upd_id": host_upd.id,
                            },
                        )
                    else:
                        # 更新 host_state=0（free）和 agent_ver
                        old_host_state = host_rec.host_state
                        old_agent_ver = host_rec.agent_ver

                        update_values: Dict[str, Any] = {}

                        # ✅ 只有业务状态 (< 5) 的主机才会被重置为空闲，避免影响 pending/registration 状态的主机
                        if old_host_state < 5:
                            update_values["host_state"] = HOST_STATE_FREE
                        else:
                            logger.info(
                                "主机处于非业务状态(>=5)，OTA 更新成功后不重置为空闲状态",
                                extra={
                                    "host_id": host_id,
                                    "host_state": old_host_state,
                                },
                            )
                        if agent_ver:
                            # 限制 agent_ver 长度为 10
                            update_values["agent_ver"] = agent_ver[:10] if len(agent_ver) > 10 else agent_ver

                        update_host_rec_stmt = (
                            update(HostRec)
                            .where(HostRec.id == host_id)
                            .values(**update_values)
                        )
                        await session.execute(update_host_rec_stmt)

                        new_host_state = HOST_STATE_FREE

                        logger.info(
                            "host_rec 表已更新（OTA 更新成功）",
                            extra={
                                "host_id": host_id,
                                "old_host_state": old_host_state,
                                "new_host_state": new_host_state,
                                "old_agent_ver": old_agent_ver,
                                "new_agent_ver": update_values.get("agent_ver"),
                            },
                        )

                    # 4.2 逻辑删除 host_upd 表的当前记录（更新完成）
                    delete_host_upd_stmt = (
                        update(HostUpd)
                        .where(HostUpd.id == host_upd.id)
                        .values(del_flag=1)
                    )
                    await session.execute(delete_host_upd_stmt)

                    logger.info(
                        "host_upd 记录已逻辑删除（OTA 更新成功）",
                        extra={
                            "host_upd_id": host_upd.id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                        },
                    )

                # 提交事务
                await session.commit()

                # 刷新 host_upd 对象以获取最新状态（如果记录未被删除）
                if biz_state != 2:
                    await session.refresh(host_upd)

                logger.info(
                    "OTA 更新状态上报处理完成",
                    extra={
                        "host_id": host_id,
                        "host_upd_id": host_upd.id,
                        "app_state": app_state,
                        "host_state": new_host_state,
                        "agent_ver": agent_ver,
                        "is_new_record": is_new_record,
                        "is_deleted": biz_state == 2,
                    },
                )

                return {
                    "host_id": host_id,
                    "host_upd_id": host_upd.id,
                    "app_state": app_state,
                    "host_state": new_host_state,
                    "agent_ver": agent_ver[:10] if agent_ver and len(agent_ver) > 10 else agent_ver,
                    "updated": True,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "OTA 更新状态上报处理失败",
                extra={
                    "host_id": host_id,
                    "app_name": app_name,
                    "app_ver": app_ver,
                    "biz_state": biz_state,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="OTA 更新状态上报处理失败",
                error_code="OTA_UPDATE_STATUS_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_OTA_UPDATE_STATUS_REPORT_FAILED,
                http_status_code=500,
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
            session_factory = self.session_factory
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
                    logger.warning(
                        "维护人员邮箱配置格式不正确",
                        extra={"email_type": type(emails).__name__},
                    )
                    return []

                return emails

        except Exception as e:
            logger.error(
                "获取维护人员邮箱列表失败",
                extra={"error": str(e)},
                exc_info=True,
            )
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
