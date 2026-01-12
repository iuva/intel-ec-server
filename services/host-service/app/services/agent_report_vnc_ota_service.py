"""Agent VNC/OTA Status Report Service Module

Provides VNC connection status and OTA update status reporting functionality.

Split from agent_report_service.py to improve code maintainability.
"""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select, update

# Use try-except to handle path imports
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
    """Agent VNC/OTA Status Report Service

    Responsible for handling:
    - VNC connection status reporting
    - OTA update status reporting
    - OTA configuration retrieval
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

    async def report_vnc_connection_state(self, host_id: int, vnc_state: int) -> Dict[str, Any]:
        """Agent reports VNC connection state

        Business logic:
        1. Parse host_id from token (already completed in dependency injection)
        2. Update host state based on vnc_state and current host_state:
            - When `vnc_state = 1` (connection succeeded):
                - If `host_state = 1` (locked), change to `host_state = 2` (occupied)
            - When `vnc_state = 2` (connection disconnected):
                - If `host_state = 2` (occupied), change to `host_state = 0` (free)

        Args:
            host_id: Host ID (obtained from token)
            vnc_state: VNC connection state (1=connection succeeded, 2=connection disconnected)

        Returns:
            Update result, containing host_id, host_state, vnc_state and updated fields

        Raises:
            BusinessError: Business logic error
        """
        try:
            logger.info(
                "Starting to process Agent VNC connection state report",
                extra={
                    "host_id": host_id,
                    "vnc_state": vnc_state,
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. Query host_rec table to verify host exists
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
                        "Host does not exist or has been deleted",
                        extra={
                            "host_id": host_id,
                            "vnc_state": vnc_state,
                        },
                    )
                    raise BusinessError(
                        message=f"Host does not exist: {host_id}",
                        error_code="HOST_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_NOT_FOUND,
                        http_status_code=404,
                    )

                # 2. Record state before update
                old_host_state = host_rec.host_state
                current_host_state = host_rec.host_state

                # 3. Determine new state based on vnc_state and current host_state
                new_host_state = None
                updated = False

                if vnc_state == 1:  # Connection succeeded
                    if current_host_state == HOST_STATE_LOCKED:  # 1 = Locked
                        new_host_state = HOST_STATE_OCCUPIED  # 2 = Occupied
                        updated = True
                        logger.info(
                            "VNC connection succeeded, host state updated from locked(1) to occupied(2)",
                            extra={
                                "host_id": host_id,
                                "old_host_state": old_host_state,
                                "new_host_state": new_host_state,
                                "vnc_state": vnc_state,
                            },
                        )
                    else:
                        # When vnc_state = 1 (connection succeeded) but host_state != HOST_STATE_LOCKED,
                        # return explicit exception
                        logger.warning(
                            "VNC connection succeeded but host state mismatch",
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "required_host_state": HOST_STATE_LOCKED,
                                "vnc_state": vnc_state,
                            },
                        )
                        raise BusinessError(
                            message=(
                                f"VNC connection succeeded but host state mismatch. "
                                f"Current state: {current_host_state}, required state: {HOST_STATE_LOCKED} (locked)"
                            ),
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

                elif vnc_state == 2:  # Connection disconnected/failed
                    # Only hosts with business state (< 5) will be reset to free,
                    # avoid affecting hosts in pending/registration state
                    if current_host_state is not None and current_host_state < 5:
                        new_host_state = HOST_STATE_FREE  # 0 = Free
                        updated = True
                        logger.info(
                            "VNC connection disconnected/failed, host state updated to free(0)",
                            extra={
                                "host_id": host_id,
                                "old_host_state": old_host_state,
                                "new_host_state": new_host_state,
                                "vnc_state": vnc_state,
                            },
                        )
                    else:
                        logger.info(
                            (
                                "VNC connection disconnected/failed but host in non-business state (>=5), "
                                "keeping original state"
                            ),
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "vnc_state": vnc_state,
                            },
                        )

                # 4. If update needed, execute update operation
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

                    # 5. Refresh object to get latest state
                    await session.refresh(host_rec)
                    final_host_state = host_rec.host_state
                else:
                    # No update needed, use current state
                    final_host_state = current_host_state

                logger.info(
                    "Agent VNC connection state report processing completed",
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
                "Agent VNC connection state report processing failed",
                extra={
                    "host_id": host_id,
                    "vnc_state": vnc_state,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Agent VNC connection state report processing failed",
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
        """Report OTA update status

        Business logic:
        1. Query host_upd table for latest valid record (del_flag=0) based on host_id, app_name, app_ver
        2. If record not found, create new record (before creating, logically delete other
           valid records to ensure only one valid record)
        3. Update app_state field (1=updating, 2=success, 3=failed)
        4. If biz_state=2 (success):
           - Update host_rec table host_state=0 (free)
           - Update host_rec table agent_ver (new version, if provided)
           - Logically delete current record in host_upd table (del_flag=1)

        Args:
            host_id: Host ID (obtained from token)
            app_name: Application name
            app_ver: Application version
            biz_state: Business state (1=updating, 2=success, 3=failed)
            agent_ver: Agent version (optional, used to update host_rec.agent_ver when update succeeds)

        Returns:
            Update result

        Raises:
            BusinessError: Business logic error
        """
        try:
            logger.info(
                "Starting to process OTA update status report",
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
                # 1. Query latest valid record
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
                    # 2. If record not found, first logically delete other valid records
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

                    # 3. Create new record
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
                        "Created new OTA update record",
                        extra={
                            "record_id": new_record_id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "biz_state": biz_state,
                        },
                    )
                else:
                    # 4. Update existing record
                    update_stmt = update(HostUpd).where(HostUpd.id == host_upd.id).values(app_state=biz_state)
                    await session.execute(update_stmt)

                    logger.info(
                        "Updated OTA update record",
                        extra={
                            "record_id": host_upd.id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "old_state": host_upd.app_state,
                            "new_state": biz_state,
                        },
                    )

                # 5. If update succeeded, perform additional operations
                if biz_state == 2:  # Success
                    # Update host state to free
                    host_update_values: Dict[str, Any] = {"host_state": HOST_STATE_FREE}

                    # If new version provided, also update agent_ver
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

                    # Logically delete current OTA record
                    del_stmt = update(HostUpd).where(HostUpd.id == host_upd.id).values(del_flag=1)
                    await session.execute(del_stmt)

                    logger.info(
                        "OTA update succeeded, host state updated and OTA record deleted",
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
                "OTA update status report failed",
                extra={
                    "host_id": host_id,
                    "app_name": app_name,
                    "app_ver": app_ver,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="OTA update status report processing failed",
                error_code="OTA_UPDATE_STATUS_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_OTA_UPDATE_STATUS_REPORT_FAILED,
                http_status_code=500,
            )

    async def get_latest_ota_configs(self) -> List[Dict[str, Optional[str]]]:
        """Get latest OTA configuration list

        Returns:
            OTA configuration list, each configuration contains app_name and app_ver

        Note:
            Query records in sys_conf table where conf_key='agent_ota'
        """
        try:
            logger.info("Starting to get latest OTA configuration")

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
                                ota_list.append(
                                    {
                                        "app_name": config_data.get("app_name"),
                                        "app_ver": config_data.get("app_ver"),
                                    }
                                )
                        except json.JSONDecodeError:
                            logger.warning(
                                "Failed to parse OTA configuration",
                                extra={"conf_id": conf.id, "conf_val": conf.conf_val},
                            )

                logger.info(
                    "OTA configuration retrieval completed",
                    extra={"count": len(ota_list)},
                )

                return ota_list

        except Exception as e:
            logger.error(
                "Failed to get OTA configuration",
                extra={"error": str(e)},
                exc_info=True,
            )
            return []


# Module-level instance
_vnc_ota_report_service_instance: Optional[AgentVncOtaReportService] = None


def get_vnc_ota_report_service() -> AgentVncOtaReportService:
    """Get VNC/OTA report service instance (singleton pattern)

    Returns:
        AgentVncOtaReportService: VNC/OTA report service instance
    """
    global _vnc_ota_report_service_instance
    if _vnc_ota_report_service_instance is None:
        _vnc_ota_report_service_instance = AgentVncOtaReportService()
    return _vnc_ota_report_service_instance
