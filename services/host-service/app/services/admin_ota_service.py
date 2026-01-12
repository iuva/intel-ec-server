"""Admin Backend OTA Management Service

Provides core business logic for OTA configuration queries used by admin backend.
"""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select, update

# Use try-except to handle path imports
try:
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.cache_invalidation import invalidate_ota_config_cache
    from app.utils.logging_helpers import log_operation_start
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_upd import HostUpd
    from app.models.sys_conf import SysConf
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.utils.cache_invalidation import invalidate_ota_config_cache
    from app.utils.logging_helpers import log_operation_start
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class AdminOtaService:
    """Admin Backend OTA Management Service

    ✅ Optimization: Cache session factory to avoid calling get_session() on every operation
    """

    def __init__(self):
        """Initialize service"""
        # ✅ Optimization: Cache session factory
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)

        ✅ Optimization: Cache session factory to avoid repeated retrieval
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    @handle_service_errors(
        error_message="Failed to query OTA configuration list",
        error_code="QUERY_OTA_CONFIG_LIST_FAILED",
    )
    async def list_ota_configs(self) -> List[Dict[str, Any]]:
        """Query OTA configuration list

        Business logic:
        - Query sys_conf table
        - Conditions: conf_key = "ota", state_flag = 0, del_flag = 0
        - Return: id, conf_ver, conf_name, conf_url, conf_md5 data list

        Returns:
            List[Dict[str, Any]]: OTA configuration list, each configuration contains:
                - id: Configuration ID (primary key)
                - conf_ver: Configuration version number
                - conf_name: Configuration name
                - conf_url: OTA package download address
                - conf_md5: OTA package MD5 checksum

        Raises:
            BusinessError: Raises business exception when query fails
        """
        log_operation_start(
            "Query OTA configuration list",
            logger_instance=logger,
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # Build query conditions
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

            # Execute query
            result = await session.execute(stmt)
            rows = result.all()

            # Convert to dictionary list
            ota_configs = []
            for row in rows:
                json_data = row.conf_json or {}
                ota_config = {
                    "id": str(row.id),  # ✅ Convert to string to avoid precision loss
                    "conf_ver": row.conf_ver,
                    "conf_name": row.conf_name,
                    "conf_url": json_data.get("conf_url"),
                    "conf_md5": json_data.get("conf_md5"),
                }
                ota_configs.append(ota_config)

            logger.info(
                "OTA configuration list query succeeded",
                extra={
                    "operation": "list_ota_configs",
                    "count": len(ota_configs),
                },
            )

            return ota_configs

    @handle_service_errors(
        error_message="OTA configuration deployment failed",
        error_code="OTA_DEPLOY_FAILED",
    )
    async def deploy_ota_config(
        self,
        config_id: int,
        conf_ver: str,
        conf_name: str,
        conf_url: str,
        conf_md5: Optional[str] = None,
        operator_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Deploy OTA configuration

        Business logic:
        1. Update sys_conf table: Update conf_ver, conf_name, conf_json based on id
        2. Broadcast message via websocket: conf_ver, conf_url, conf_md5 to all hosts
        3. Register callback handler: When host websocket callback notification, add record in host_upd table

        Args:
            config_id: Configuration ID (primary key)
            conf_ver: Configuration version number
            conf_name: Configuration name
            conf_url: OTA package download address
            conf_md5: OTA package MD5 checksum (optional)
            operator_id: Operator ID (optional)

        Returns:
            Dict[str, Any]: Deployment result, containing:
                - id: Configuration ID
                - conf_ver: Configuration version number
                - conf_name: Configuration name
                - conf_url: Download address
                - conf_md5: Checksum (may be None)
                - broadcast_count: Number of hosts that successfully received broadcast message

        Raises:
            BusinessError: Raises business exception when configuration does not exist or deployment fails
        """
        logger.info(
            "Starting to deploy OTA configuration",
            extra={
                "operation": "deploy_ota_config",
                "config_id": config_id,
                "conf_ver": conf_ver,
                "conf_name": conf_name,
                "operator_id": operator_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Query if configuration exists
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
                    message=f"OTA configuration does not exist: {config_id}",
                    error_code="OTA_CONFIG_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_OTA_CONFIG_NOT_FOUND,
                    http_status_code=404,
                )

            # 2. Update sys_conf table
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
                "OTA configuration updated successfully",
                extra={
                    "operation": "deploy_ota_config",
                    "config_id": config_id,
                    "conf_ver": conf_ver,
                    "conf_name": conf_name,
                },
            )

        # ✅ Optimization: Clear OTA configuration cache to ensure next query gets latest data
        try:
            await invalidate_ota_config_cache()
        except ImportError:
            # Fallback: Directly use redis_manager
            cache_key = "ota_configs:latest"
            try:
                await redis_manager.delete(cache_key)
                logger.info(
                    "OTA configuration cache cleared (fallback mode)",
                    extra={
                        "operation": "deploy_ota_config",
                        "cache_key": cache_key,
                        "config_id": config_id,
                    },
                )
            except Exception as e:
                logger.warning(
                    "Failed to clear OTA configuration cache",
                    extra={
                        "operation": "deploy_ota_config",
                        "cache_key": cache_key,
                        "error": str(e),
                    },
                )

        # 3. Broadcast message via websocket
        ws_manager = get_agent_websocket_manager()

        # Register OTA deployment callback handler (if not yet registered)
        if "ota_deploy_notification" not in ws_manager.message_handlers:
            ws_manager.register_handler("ota_deploy_notification", self._handle_ota_deploy_notification)

        # Build broadcast message
        broadcast_message = {
            "type": "ota_deploy",
            "conf_ver": conf_ver,
            "conf_name": conf_name,
            "conf_url": conf_url,
            "conf_md5": conf_md5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Broadcast message to all connected hosts
        broadcast_count = await ws_manager.broadcast(broadcast_message)

        logger.info(
            "OTA configuration deployment completed",
            extra={
                "operation": "deploy_ota_config",
                "config_id": config_id,
                "conf_ver": conf_ver,
                "conf_name": conf_name,
                "broadcast_count": broadcast_count,
            },
        )

        return {
            "id": str(config_id),  # ✅ Convert to string to avoid precision loss
            "conf_ver": conf_ver,
            "conf_name": conf_name,
            "conf_url": conf_url,
            "conf_md5": conf_md5,
            "broadcast_count": broadcast_count,
        }

    async def _handle_ota_deploy_notification(self, agent_id: str, data: dict) -> None:
        """Handle Host OTA deployment callback notification

        Business logic:
        - When host receives OTA deployment message, it will callback this handler
        - Add a new record in host_upd table:
          - app_state = 0 (pre-update)
          - host_id = host_id (obtained from websocket agent_id)
          - app_name = conf_name (obtained from callback message)
          - app_ver = conf_ver (obtained from callback message)

        Args:
            agent_id: Agent/Host ID (from websocket connection)
            data: Callback message data, should contain:
                - conf_name: Configuration name
                - conf_ver: Configuration version number
        """
        try:
            # Convert agent_id to integer
            try:
                host_id_int = int(agent_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Host ID format error: {agent_id}",
                    extra={
                        "agent_id": agent_id,
                        "error": "not a valid integer",
                    },
                )
                return

            # Get configuration information from callback message
            conf_name = data.get("conf_name")
            conf_ver = data.get("conf_ver")

            if not conf_name or not conf_ver:
                logger.warning(
                    "OTA deployment callback message missing required fields",
                    extra={
                        "agent_id": agent_id,
                        "data": data,
                    },
                )
                return

            logger.info(
                "Starting to process OTA deployment callback notification",
                extra={
                    "operation": "_handle_ota_deploy_notification",
                    "agent_id": agent_id,
                    "host_id": host_id_int,
                    "conf_name": conf_name,
                    "conf_ver": conf_ver,
                },
            )

            # Add new record in host_upd table
            session_factory = self.session_factory
            async with session_factory() as session:
                host_upd = HostUpd(
                    host_id=host_id_int,
                    app_name=conf_name,
                    app_ver=conf_ver,
                    app_state=0,  # Pre-update state
                    created_by=None,  # Can set operator as needed
                )

                session.add(host_upd)
                await session.commit()

                logger.info(
                    "OTA deployment callback record created",
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
                "Failed to process OTA deployment callback notification",
                extra={
                    "operation": "_handle_ota_deploy_notification",
                    "agent_id": agent_id,
                    "error": str(e),
                },
                exc_info=True,
            )
