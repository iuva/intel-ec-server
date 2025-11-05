"""管理后台 OTA 管理服务

提供管理后台使用的 OTA 配置查询等核心业务逻辑。
"""

import os
import sys
from typing import Any, Dict, List

from sqlalchemy import and_, select

# 使用 try-except 方式处理路径导入
try:
    from app.models.sys_conf import SysConf

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.sys_conf import SysConf

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
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
        - 返回：id, conf_ver, conf_name, conf_val, conf_json 数据列表

        Returns:
            List[Dict[str, Any]]: OTA 配置列表，每个配置包含：
                - id: 配置ID（主键）
                - conf_ver: 配置版本号
                - conf_name: 配置名称
                - conf_val: 配置值
                - conf_json: 配置 JSON

        Raises:
            BusinessError: 查询失败时抛出业务异常
        """
        logger.info("开始查询 OTA 配置列表")

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建查询条件
            stmt = select(
                SysConf.id,
                SysConf.conf_ver,
                SysConf.conf_name,
                SysConf.conf_val,
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
                ota_config = {
                    "id": row.id,
                    "conf_ver": row.conf_ver,
                    "conf_name": row.conf_name,
                    "conf_val": row.conf_val,
                    "conf_json": row.conf_json,
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
