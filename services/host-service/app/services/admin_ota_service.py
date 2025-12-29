"""管理后台 OTA 管理服务

提供管理后台使用的 OTA 配置查询等核心业务逻辑。
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.logging_helpers import log_operation_start

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.logging_helpers import log_operation_start

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class AdminOtaService:
    """管理后台 OTA 管理服务"""

    @handle_service_errors(
        error_message="查询 OTA 配置列表失败",
        error_code="QUERY_OTA_CONFIG_LIST_FAILED",
    )
    async def list_ota_configs(self) -> List[Dict[str, Any]]:
        """查询 OTA 配置列表

        业务逻辑：
        - 查询 sys_conf 表
        - 条件：conf_key = "ota", state_flag = 0, del_flag = 0
        - 返回：id, conf_ver, conf_name, conf_url, conf_md5 数据列表

        Returns:
            List[Dict[str, Any]]: OTA 配置列表，每个配置包含：
                - id: 配置ID（主键）
                - conf_ver: 配置版本号
                - conf_name: 配置名称
                - conf_url: OTA 包下载地址
                - conf_md5: OTA 包 MD5 校验值

        Raises:
            BusinessError: 查询失败时抛出业务异常
        """
        log_operation_start(
            "查询 OTA 配置列表",
            logger_instance=logger,
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建查询条件
            stmt = select(
                SysConf.id,
                SysConf.conf_ver,
                SysConf.conf_name,
                SysConf.conf_json,
            ).where(
                and_(
                    SysConf.conf_key == "ota",
                    SysConf.state_flag == 0,
                    SysConf.del_flag == 0,
                )
            )

            # 执行查询
            result = await session.execute(stmt)
            rows = result.all()

            # 转换为字典列表
            ota_configs = []
            for row in rows:
                json_data = row.conf_json or {}
                ota_config = {
                    "id": str(row.id),  # ✅ 转换为字符串避免精度丢失
                    "conf_ver": row.conf_ver,
                    "conf_name": row.conf_name,
                    "conf_url": json_data.get("conf_url"),
                    "conf_md5": json_data.get("conf_md5"),
                }
                ota_configs.append(ota_config)

            logger.info(
                "OTA 配置列表查询成功",
                extra={
                    "operation": "list_ota_configs",
                    "count": len(ota_configs),
                },
            )

            return ota_configs

    @handle_service_errors(
        error_message="OTA 配置下发失败",
        error_code="OTA_DEPLOY_FAILED",
    )
    async def deploy_ota_config(
        self,
        config_id: int,
        conf_ver: str,
        conf_name: str,
        conf_url: str,
        conf_md5: str,
        operator_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """下发 OTA 配置

        业务逻辑：
        1. 更新 sys_conf 表：根据 id 更新 conf_ver, conf_name, conf_json
        2. 通过 websocket 广播消息：conf_ver、conf_url、conf_md5 到所有 host
        3. 注册回调处理器：当 host websocket 回调通知时，在 host_upd 表新增记录

        Args:
            config_id: 配置ID（主键）
            conf_ver: 配置版本号
            conf_name: 配置名称
            conf_url: OTA 包下载地址
            conf_md5: OTA 包 MD5 校验值
            operator_id: 操作人ID（可选）

        Returns:
            Dict[str, Any]: 下发结果，包含：
                - id: 配置ID
                - conf_ver: 配置版本号
                - conf_name: 配置名称
                - conf_url: 下载地址
                - conf_md5: 校验值
                - broadcast_count: 广播消息成功发送的主机数量

        Raises:
            BusinessError: 配置不存在或下发失败时抛出业务异常
        """
        logger.info(
            "开始下发 OTA 配置",
            extra={
                "operation": "deploy_ota_config",
                "config_id": config_id,
                "conf_ver": conf_ver,
                "conf_name": conf_name,
                "operator_id": operator_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 查询配置是否存在
            stmt = select(SysConf).where(
                and_(
                    SysConf.id == config_id,
                    SysConf.del_flag == 0,
                )
            )
            result = await session.execute(stmt)
            sys_conf = result.scalar_one_or_none()

            if not sys_conf:
                raise BusinessError(
                    message=f"OTA 配置不存在: {config_id}",
                    error_code="OTA_CONFIG_NOT_FOUND",
                    code=404,
                )

            # 2. 更新 sys_conf 表
            update_stmt = (
                update(SysConf)
                .where(SysConf.id == config_id)
                .values(
                    conf_ver=conf_ver,
                    conf_name=conf_name,
                    conf_val=None,
                    conf_json={
                        "conf_url": conf_url,
                        "conf_md5": conf_md5,
                    },
                    updated_by=operator_id,
                )
            )
            await session.execute(update_stmt)
            await session.commit()

            logger.info(
                "OTA 配置更新成功",
                extra={
                    "operation": "deploy_ota_config",
                    "config_id": config_id,
                    "conf_ver": conf_ver,
                    "conf_name": conf_name,
                },
            )

        # ✅ 优化：清除 OTA 配置缓存，确保下次查询获取最新数据
        try:
            from app.utils.cache_invalidation import invalidate_ota_config_cache

            await invalidate_ota_config_cache()
        except ImportError:
            # 降级处理：直接使用 redis_manager
            cache_key = "ota_configs:latest"
            try:
                await redis_manager.delete(cache_key)
                logger.info(
                    "OTA 配置缓存已清除（降级模式）",
                    extra={
                        "operation": "deploy_ota_config",
                        "cache_key": cache_key,
                        "config_id": config_id,
                    },
                )
            except Exception as e:
                logger.warning(
                    "清除 OTA 配置缓存失败",
                    extra={
                        "operation": "deploy_ota_config",
                        "cache_key": cache_key,
                        "error": str(e),
                    },
                )

        # 3. 通过 websocket 广播消息
        ws_manager = get_agent_websocket_manager()

        # 注册 OTA 下发回调处理器（如果尚未注册）
        if "ota_deploy_notification" not in ws_manager.message_handlers:
            ws_manager.register_handler("ota_deploy_notification", self._handle_ota_deploy_notification)

        # 构建广播消息
        broadcast_message = {
            "type": "ota_deploy",
            "conf_ver": conf_ver,
            "conf_name": conf_name,
            "conf_url": conf_url,
            "conf_md5": conf_md5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 广播消息给所有连接的 hosts
        broadcast_count = await ws_manager.broadcast(broadcast_message)

        logger.info(
            "OTA 配置下发完成",
            extra={
                "operation": "deploy_ota_config",
                "config_id": config_id,
                "conf_ver": conf_ver,
                "conf_name": conf_name,
                "broadcast_count": broadcast_count,
            },
        )

        return {
            "id": str(config_id),  # ✅ 转换为字符串避免精度丢失
            "conf_ver": conf_ver,
            "conf_name": conf_name,
            "conf_url": conf_url,
            "conf_md5": conf_md5,
            "broadcast_count": broadcast_count,
        }

    async def _handle_ota_deploy_notification(self, agent_id: str, data: dict) -> None:
        """处理 Host OTA 下发回调通知

        业务逻辑：
        - 当 host 收到 OTA 下发消息后，会回调此处理器
        - 在 host_upd 表中新增一条记录：
          - app_state = 0 (预更新)
          - host_id = host_id (从 websocket agent_id 获取)
          - app_name = conf_name (从回调消息中获取)
          - app_ver = conf_ver (从回调消息中获取)

        Args:
            agent_id: Agent/Host ID (来自 websocket 连接)
            data: 回调消息数据，应包含：
                - conf_name: 配置名称
                - conf_ver: 配置版本号
        """
        try:
            # 转换 agent_id 为整数
            try:
                host_id_int = int(agent_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Host ID 格式错误: {agent_id}",
                    extra={
                        "agent_id": agent_id,
                        "error": "not a valid integer",
                    },
                )
                return

            # 从回调消息中获取配置信息
            conf_name = data.get("conf_name")
            conf_ver = data.get("conf_ver")

            if not conf_name or not conf_ver:
                logger.warning(
                    "OTA 下发回调消息缺少必要字段",
                    extra={
                        "agent_id": agent_id,
                        "data": data,
                    },
                )
                return

            logger.info(
                "开始处理 OTA 下发回调通知",
                extra={
                    "operation": "_handle_ota_deploy_notification",
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                    "conf_name": conf_name,
                    "conf_ver": conf_ver,
                },
            )

            # 在 host_upd 表中新增记录
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                host_upd = HostUpd(
                    host_id=host_id_int,
                    app_name=conf_name,
                    app_ver=conf_ver,
                    app_state=0,  # 预更新状态
                    created_by=None,  # 可以根据需要设置操作人
                )

                session.add(host_upd)
                await session.commit()

                logger.info(
                    "OTA 下发回调记录已创建",
                    extra={
                        "operation": "_handle_ota_deploy_notification",
                        "agent_id": agent_id,
                        "host_id": host_id_int,
                        "host_upd_id": host_upd.id,
                        "conf_name": conf_name,
                        "conf_ver": conf_ver,
                    },
                )

        except Exception as e:
            logger.error(
                "处理 OTA 下发回调通知失败",
                extra={
                    "operation": "_handle_ota_deploy_notification",
                    "agent_id": agent_id,
                    "error": str(e),
                },
                exc_info=True,
            )
