"""Agent VNC/OTA 状态上报服务模块

提供 VNC 连接状态和 OTA 更新状态上报功能。

从 agent_report_service.py 拆分出来，提高代码可维护性。
"""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.constants.host_constants import (
        HOST_STATE_FREE,
        HOST_STATE_LOCKED,
        HOST_STATE_OCCUPIED,
    )
    from app.models.host_rec import HostRec
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from shared.common.database import generate_snowflake_id, mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import (
        HOST_STATE_FREE,
        HOST_STATE_LOCKED,
        HOST_STATE_OCCUPIED,
    )
    from app.models.host_rec import HostRec
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from shared.common.database import generate_snowflake_id, mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class AgentVncOtaReportService:
    """Agent VNC/OTA 状态上报服务

    负责处理：
    - VNC 连接状态上报
    - OTA 更新状态上报
    - OTA 配置获取
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
                        # 当 vnc_state = 1（连接成功）但 host_state 不等于 HOST_STATE_LOCKED 时，返回明确的异常
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
                    # 只有业务状态 (< 5) 的主机才会被重置为空闲，避免影响 pending/registration 状态的主机
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
            host_id: 主机ID（从token中获取）
            app_name: 应用名称
            app_ver: 应用版本
            biz_state: 业务状态（1=更新中，2=成功，3=失败）
            agent_ver: Agent 版本（可选，用于更新成功时更新 host_rec.agent_ver）

        Returns:
            更新结果

        Raises:
            BusinessError: 业务逻辑错误
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

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. 查询最新的有效记录
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
                    .order_by(desc(HostUpd.created_time))
                    .limit(1)
                )

                result = await session.execute(stmt)
                host_upd = result.scalar_one_or_none()

                if not host_upd:
                    # 2. 如果未找到记录，先逻辑删除其他有效记录
                    delete_stmt = (
                        update(HostUpd)
                        .where(
                            and_(
                                HostUpd.host_id == host_id,
                                HostUpd.del_flag == 0,
                            )
                        )
                        .values(del_flag=1)
                    )
                    await session.execute(delete_stmt)

                    # 3. 创建新记录
                    new_record_id = generate_snowflake_id()
                    host_upd = HostUpd(
                        id=new_record_id,
                        host_id=host_id,
                        app_name=app_name,
                        app_ver=app_ver,
                        app_state=biz_state,
                        created_time=datetime.now(timezone.utc),
                        del_flag=0,
                    )
                    session.add(host_upd)

                    logger.info(
                        "创建新的 OTA 更新记录",
                        extra={
                            "record_id": new_record_id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "biz_state": biz_state,
                        },
                    )
                else:
                    # 4. 更新现有记录
                    update_stmt = (
                        update(HostUpd)
                        .where(HostUpd.id == host_upd.id)
                        .values(app_state=biz_state)
                    )
                    await session.execute(update_stmt)

                    logger.info(
                        "更新 OTA 更新记录",
                        extra={
                            "record_id": host_upd.id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "old_state": host_upd.app_state,
                            "new_state": biz_state,
                        },
                    )

                # 5. 如果更新成功，执行额外操作
                if biz_state == 2:  # 成功
                    # 更新主机状态为空闲
                    host_update_values: Dict[str, Any] = {"host_state": HOST_STATE_FREE}

                    # 如果提供了新版本号，也更新 agent_ver
                    if agent_ver:
                        host_update_values["agent_ver"] = agent_ver

                    host_update_stmt = (
                        update(HostRec)
                        .where(
                            and_(
                                HostRec.id == host_id,
                                HostRec.del_flag == 0,
                            )
                        )
                        .values(**host_update_values)
                    )
                    await session.execute(host_update_stmt)

                    # 逻辑删除当前 OTA 记录
                    del_stmt = (
                        update(HostUpd)
                        .where(HostUpd.id == host_upd.id)
                        .values(del_flag=1)
                    )
                    await session.execute(del_stmt)

                    logger.info(
                        "OTA 更新成功，已更新主机状态并删除 OTA 记录",
                        extra={
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "agent_ver": agent_ver,
                        },
                    )

                await session.commit()

                return {
                    "host_id": str(host_id),
                    "app_name": app_name,
                    "app_ver": app_ver,
                    "biz_state": biz_state,
                    "agent_ver": agent_ver,
                    "updated": True,
                }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "OTA 更新状态上报失败",
                extra={
                    "host_id": host_id,
                    "app_name": app_name,
                    "app_ver": app_ver,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="OTA 更新状态上报处理失败",
                error_code="OTA_UPDATE_STATUS_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_OTA_UPDATE_STATUS_REPORT_FAILED,
                http_status_code=500,
            )

    async def get_latest_ota_configs(self) -> List[Dict[str, Optional[str]]]:
        """获取最新的 OTA 配置列表

        Returns:
            OTA 配置列表，每个配置包含 app_name 和 app_ver

        Note:
            查询 sys_conf 表中 conf_key='agent_ota' 的记录
        """
        try:
            logger.info("开始获取最新 OTA 配置")

            session_factory = self.session_factory
            async with session_factory() as session:
                stmt = select(SysConf).where(
                    and_(
                        SysConf.conf_key == "agent_ota",
                        SysConf.del_flag == 0,
                        SysConf.state_flag == 0,
                    )
                )

                result = await session.execute(stmt)
                configs = result.scalars().all()

                ota_list: List[Dict[str, Optional[str]]] = []
                for conf in configs:
                    if conf.conf_val:
                        import json
                        try:
                            config_data = json.loads(conf.conf_val)
                            if isinstance(config_data, dict):
                                ota_list.append({
                                    "app_name": config_data.get("app_name"),
                                    "app_ver": config_data.get("app_ver"),
                                })
                        except json.JSONDecodeError:
                            logger.warning(
                                "解析 OTA 配置失败",
                                extra={"conf_id": conf.id, "conf_val": conf.conf_val},
                            )

                logger.info(
                    "获取 OTA 配置完成",
                    extra={"count": len(ota_list)},
                )

                return ota_list

        except Exception as e:
            logger.error(
                "获取 OTA 配置失败",
                extra={"error": str(e)},
                exc_info=True,
            )
            return []


# 模块级实例
_vnc_ota_report_service_instance: Optional[AgentVncOtaReportService] = None


def get_vnc_ota_report_service() -> AgentVncOtaReportService:
    """获取 VNC/OTA 上报服务实例（单例模式）

    Returns:
        AgentVncOtaReportService: VNC/OTA 上报服务实例
    """
    global _vnc_ota_report_service_instance
    if _vnc_ota_report_service_instance is None:
        _vnc_ota_report_service_instance = AgentVncOtaReportService()
    return _vnc_ota_report_service_instance
