"""Agent information reporting service

Processes information reported by Agent, including:
1. Hardware template validation
2. Version number comparison
3. Hardware content deep comparison
4. Database record updates
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select, update

# Use try-except to handle path imports
try:
    from app.constants.host_constants import (
        CASE_STATE_SUCCESS,
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
    from shared.common.i18n import t
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.json_comparator import JSONComparator
    from shared.utils.template_validator import TemplateValidator
    from shared.utils.time_utils import get_db_timezone
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import (
        CASE_STATE_SUCCESS,
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
    from shared.utils.time_utils import get_db_timezone

logger = get_logger(__name__)


class AgentReportService:
    """Agent information reporting service"""

    # Hardware difference states
    DIFF_STATE_VERSION = 1  # Version number changed
    DIFF_STATE_CONTENT = 2  # Content changed
    DIFF_STATE_FAILED = 3  # Exception

    # Sync states
    SYNC_STATE_EMPTY = 0  # Empty state
    SYNC_STATE_WAIT = 1  # Pending sync
    SYNC_STATE_SUCCESS = 2  # Passed
    SYNC_STATE_FAILED = 3  # Exception

    # Approval states
    APPR_STATE_ENABLE = 1  # Enabled
    APPR_STATE_CHANGE = 2  # Has changes

    # Host states
    HOST_STATE_HW_CHANGE = 6  # Has potential hardware changes

    def __init__(self):
        """Initialize service"""
        # Initialize JSON comparator tool
        self.json_comparator = JSONComparator()
        # Initialize template validator
        # Initialize template validator
        self.template_validator = TemplateValidator()
        # Keep track of background tasks to prevent GC
        self._background_tasks = set()
        # ✅ Optimization: Cache session factory to avoid calling get_session() on every operation
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)

        ✅ Optimization: Cache session factory to avoid repeated retrieval
        - Initialize on first call
        - Reuse cached factory instance on subsequent calls
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
        """Report hardware information

        Args:
            host_id: Host ID (obtained from token)
            hardware_data: Hardware information (dynamic JSON)
            report_type: Report type (0-success, 1-exception)

        Returns:
            Processing result

        Raises:
            BusinessError: Business logic error
        """
        try:
            logger.info(
                "Start processing hardware information report",
                extra={
                    "host_id": host_id,
                    "hardware_keys": list(hardware_data.keys()),
                    "report_type": report_type,
                },
            )

            # 1. Extract dmr_config (required)
            dmr_config = hardware_data.get("dmr_config")
            if not dmr_config:
                raise BusinessError(
                    message="dmr_config is a required field",
                    error_code="MISSING_DMR_CONFIG",
                    code=ServiceErrorCodes.HOST_MISSING_DMR_CONFIG,
                    http_status_code=400,
                )

            # 2. Extract revision number (required)
            current_revision = dmr_config.get("revision")
            if current_revision is None:
                raise BusinessError(
                    message="dmr_config.revision is a required field",
                    error_code="MISSING_REVISION",
                    code=ServiceErrorCodes.HOST_MISSING_REVISION,
                    http_status_code=400,
                )

            # 3. Get current effective hardware record
            current_hw_rec = await self._get_current_hardware_record(host_id)

            # 4. Determine processing logic based on report_type
            if report_type == 1:
                # Exception type: directly set diff_state=3, skip comparison logic
                logger.info(
                    "Hardware information report type is exception, directly set diff_state=3",
                    extra={
                        "host_id": host_id,
                        "report_type": report_type,
                    },
                )

                diff_state = self.DIFF_STATE_FAILED  # 3
                diff_details = {"report_type": "exception", "reason": "Agent reported exception type"}

                # Update database record
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
                    "Hardware information exception report processing completed",
                    extra={
                        "host_id": host_id,
                        "diff_state": diff_state,
                        "result": result,
                    },
                )

                return result

            # 5. Normal type (report_type=0): follow original comparison logic
            # Get hardware template
            hw_template = await self._get_hardware_template()
            if not hw_template:
                raise BusinessError(
                    message="Hardware template configuration not found",
                    error_code="HARDWARE_TEMPLATE_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_HARDWARE_TEMPLATE_NOT_FOUND,
                    http_status_code=500,
                )

            # 6. Validate hardware information required fields
            self._validate_required_fields(dmr_config, hw_template)

            # 7. Compare hardware information
            diff_state, diff_details = await self._compare_hardware(
                current_revision=current_revision,
                current_dmr_config=dmr_config,
                current_hw_rec=current_hw_rec,
                hw_template=hw_template,
            )

            # 8. Update database records
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
                "Hardware information report processing completed",
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
                "Hardware information report exception",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise BusinessError(
                message="Hardware information report processing failed",
                error_code="HARDWARE_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_HARDWARE_REPORT_FAILED,
                http_status_code=500,
            )

    async def get_latest_ota_configs(self) -> List[Dict[str, Optional[str]]]:
        """Get latest OTA configuration information list (with cache)

        Uses Redis to cache OTA configurations, cache time 5 minutes, reduces database query pressure.
        """
        # Cache key
        cache_key = "ota_configs:latest"

        # Try to get from cache
        try:
            cached_configs = await redis_manager.get(cache_key)
            if cached_configs is not None:
                logger.debug(
                    "Retrieved OTA configuration from cache",
                    extra={
                        "cache_key": cache_key,
                        "count": len(cached_configs) if isinstance(cached_configs, list) else 0,
                    },
                )
                return cached_configs
        except Exception as e:
            logger.warning(
                "Failed to retrieve OTA configuration from cache, will query database",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss, query database
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
                logger.info("No OTA configuration found, returning empty list")
                # Cache empty result to avoid frequent queries (cache time shortened to 1 minute)
                try:
                    await redis_manager.set(cache_key, [], expire=60)
                except Exception as e:
                    logger.warning(
                        "Failed to cache empty result",
                        extra={"cache_key": cache_key, "error": str(e)},
                    )
                return []

            logger.info(
                "Retrieved OTA configuration successfully",
                extra={
                    "count": len(records),
                },
            )

            ota_configs = [
                {
                    "conf_name": record.conf_name,
                    "conf_ver": record.conf_ver,
                    "conf_url": (record.conf_json or {}).get("conf_url"),
                    "conf_md5": (record.conf_json or {}).get("conf_md5"),
                }
                for record in records
            ]

            # Store in cache, expires in 5 minutes
            try:
                await redis_manager.set(cache_key, ota_configs, expire=300)
                logger.debug(
                    "OTA configuration cached",
                    extra={"cache_key": cache_key, "count": len(ota_configs), "expire_seconds": 300},
                )
            except Exception as e:
                logger.warning(
                    "Failed to cache OTA configuration",
                    extra={"cache_key": cache_key, "error": str(e)},
                )

            return ota_configs

    async def get_agent_init_configs(self) -> List[Dict[str, Any]]:
        """Get agent initialization configurations

        Query sys_conf table for records where:
        - conf_key starts with 'agent_init_'
        - state_flag = 0 (enabled)
        - del_flag = 0 (not deleted)

        Returns:
            List of initialization configurations, each containing:
            - conf_key: Configuration key
            - conf_val: Configuration value
            - conf_ver: Configuration version
            - conf_name: Configuration name
            - conf_json: Configuration JSON
        """
        session_factory = self.session_factory
        async with session_factory() as session:
            stmt = (
                select(SysConf)
                .where(
                    and_(
                        SysConf.conf_key.like("agent_init_%"),
                        SysConf.state_flag == 0,
                        SysConf.del_flag == 0,
                    )
                )
                .order_by(SysConf.updated_time.desc(), SysConf.id.desc())
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                logger.info("No agent initialization configuration found, returning empty list")
                return []

            logger.info(
                "Retrieved agent initialization configuration successfully",
                extra={
                    "count": len(records),
                },
            )

            init_configs = []
            for record in records:
                init_configs.append(
                    {
                        "conf_key": record.conf_key,
                        "conf_val": record.conf_val,
                        "conf_ver": record.conf_ver,
                        "conf_name": record.conf_name,
                        "conf_json": record.conf_json,
                    }
                )

            return init_configs

    async def _get_hardware_template(self) -> Optional[Dict[str, Any]]:
        """Get hardware template configuration (with cache)

        Query configuration from sys_conf table where conf_key='hw_temp', state_flag=0, del_flag=0.
        Uses Redis to cache template data, cache time 5 minutes, reduces database query pressure.

        Returns:
            Hardware template configuration (conf_json field)
        """
        # Cache key
        cache_key = "hardware_template"

        # Try to get from cache
        try:
            cached_template = await redis_manager.get(cache_key)
            if cached_template is not None:
                logger.debug(
                    "Retrieved hardware template from cache",
                    extra={"cache_key": cache_key},
                )
                return cached_template
        except Exception as e:
            logger.warning(
                "Failed to retrieve hardware template from cache, will query database",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss, query database
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
                    logger.warning("Hardware template configuration not found (conf_key='hw_temp')")
                    # Cache None result to avoid frequent queries (cache time shortened to 1 minute)
                    try:
                        await redis_manager.set(cache_key, None, expire=60)
                    except Exception as e:
                        logger.warning(
                            "Failed to cache empty result",
                            extra={"cache_key": cache_key, "error": str(e)},
                        )
                    return None

                template = conf.conf_json

                # Store in cache, expires in 5 minutes
                try:
                    await redis_manager.set(cache_key, template, expire=300)
                    logger.debug(
                        "Hardware template cached",
                        extra={"cache_key": cache_key, "expire_seconds": 300},
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to cache hardware template",
                        extra={"cache_key": cache_key, "error": str(e)},
                    )

                return template

        except Exception as e:
            logger.error(
                "Failed to get hardware template configuration",
                extra={"error": str(e)},
                exc_info=True,
            )
            return None

    def _validate_required_fields(self, dmr_config: Dict[str, Any], hw_template: Dict[str, Any]) -> None:
        """Validate hardware information required fields

        Iterate through hardware template, check if fields with value 'required' exist in reported data

        Args:
            dmr_config: Hardware configuration reported by Agent
            hw_template: Hardware template configuration

        Raises:
            BusinessError: Raises when required fields are missing
        """
        # Use template validator utility class for validation
        self.template_validator.validate_required_fields(dmr_config, hw_template)
        logger.info("Hardware information required fields validation ***REMOVED***ed")

    async def _get_current_hardware_record(self, host_id: int, session: Optional[Any] = None) -> Optional[HostHwRec]:
        """Get current effective hardware record

        Query the latest hardware record from host_hw_rec table

        ✅ Optimization: Support ***REMOVED***ing external session to avoid creating new session

        Args:
            host_id: Host ID
            session: Optional external session (if not provided, create new session)

        Returns:
            Latest hardware record, returns None if not exists
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

            # ✅ Optimization: If session is ***REMOVED***ed, use it directly, otherwise create new session
            if session:
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            session_factory = self.session_factory
            async with session_factory() as new_session:
                result = await new_session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get current hardware record",
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
        """Compare hardware information

        Args:
            current_revision: Currently reported revision number
            current_dmr_config: Currently reported hardware configuration
            current_hw_rec: Current effective hardware record
            hw_template: Hardware template

        Returns:
            (Difference state, difference details)
            - Difference state: DIFF_STATE_VERSION | DIFF_STATE_CONTENT | None
            - Difference details: Difference information dictionary
        """
        try:
            # If no historical record, this is the first report (no need to compare)
            if not current_hw_rec or not current_hw_rec.hw_info:
                logger.info("Host first hardware information report, no need to compare")
                return None, {}

            previous_hw_info = current_hw_rec.hw_info
            previous_revision = previous_hw_info.get("dmr_config", {}).get("revision")

            # 1. Compare revision numbers
            if previous_revision is not None and current_revision != previous_revision:
                logger.info(
                    "Hardware revision number changed",
                    extra={
                        "previous": previous_revision,
                        "current": current_revision,
                    },
                )
                return self.DIFF_STATE_VERSION, {
                    "previous_revision": previous_revision,
                    "current_revision": current_revision,
                }

            # 2. Compare content (deep JSON comparison, using utility class)
            content_diff = self.json_comparator.compare(
                previous_hw_info.get("dmr_config", {}),
                current_dmr_config,
            )

            if content_diff:
                logger.info(
                    "Hardware content changed",
                    extra={
                        "diff_count": len(content_diff),
                        "changed_fields": list(content_diff.keys()),
                    },
                )
                return self.DIFF_STATE_CONTENT, content_diff

            # 3. No changes
            logger.info("Hardware information unchanged")
            return None, {}

        except Exception as e:
            logger.error(
                "Exception comparing hardware information",
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
        """Update hardware records

        Update host_rec and host_hw_rec tables based on comparison results

        Args:
            host_id: Host ID
            hardware_data: Complete hardware data
            dmr_config: DMR configuration
            current_revision: Current revision number
            diff_state: Difference state
            diff_details: Difference details
            current_hw_rec: Current hardware record

        Returns:
            Update result
        """
        try:
            session_factory = self.session_factory
            async with session_factory() as session:
                # If there are differences, need to update host_rec and insert new host_hw_rec
                if diff_state:
                    # 1. Query host_rec to get hardware_id and host_ip (for email notification)
                    host_rec_stmt = select(HostRec).where(
                        and_(
                            HostRec.id == host_id,
                            HostRec.del_flag == 0,
                        )
                    )
                    host_rec_result = await session.execute(host_rec_stmt)
                    host_rec = host_rec_result.scalar_one_or_none()

                    # 2. Update host_rec table
                    await self._update_host_rec(session, host_id)

                    # 3. Insert new host_hw_rec record
                    new_hw_rec = await self._insert_hardware_record(
                        session=session,
                        host_id=host_id,
                        hardware_data=hardware_data,
                        hw_ver=str(current_revision),
                        diff_state=diff_state,
                    )

                    await session.commit()

                    # 4. Send hardware change email notification (async, non-blocking main flow)
                    if host_rec:
                        task = asyncio.create_task(
                            self._send_hardware_change_notification(
                                host_id=host_id,
                                hardware_id=host_rec.hardware_id or "Unknown",
                                host_ip=host_rec.host_ip or "Unknown",
                                diff_state=diff_state,
                                hw_rec_id=new_hw_rec.id,
                            )
                        )
                        # Save reference to avoid GC
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)

                    return {
                        "status": "hardware_changed",
                        "diff_state": diff_state,
                        "diff_details": diff_details,
                        "hw_rec_id": new_hw_rec.id,
                        "message": "Hardware information updated, awaiting approval",
                    }

                # If this is the first report (no historical record)
                if not current_hw_rec:
                    # Insert first hardware record (appr_state=1, awaiting approval)
                    new_hw_rec = await self._insert_hardware_record(
                        session=session,
                        host_id=host_id,
                        hardware_data=hardware_data,
                        hw_ver=str(current_revision),
                        diff_state=self.DIFF_STATE_CONTENT,
                        sync_state=self.SYNC_STATE_WAIT,  # Awaiting approval
                    )

                    await session.commit()

                    return {
                        "status": "first_report",
                        "hw_rec_id": new_hw_rec.id,
                        "message": "Hardware information first report succeeded",
                    }

                # No changes
                return {
                    "status": "no_change",
                    "message": "Hardware information unchanged",
                }

        except Exception as e:
            logger.error(
                "Failed to update hardware record",
                extra={"host_id": host_id, "error": str(e)},
                exc_info=True,
            )
            raise BusinessError(
                message="Failed to update hardware record",
                error_code="UPDATE_HARDWARE_FAILED",
                code=ServiceErrorCodes.HOST_UPDATE_HARDWARE_FAILED,
                http_status_code=500,
            )

    async def _update_host_rec(self, session, host_id: int) -> None:
        """Update host_rec table

        Set appr_state=2 (has changes), host_state=6 (has potential hardware changes)

        Args:
            session: Database session
            host_id: Host ID
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
                "Updated host_rec successfully",
                extra={"host_id": host_id},
            )

        except Exception as e:
            logger.error(
                "Failed to update host_rec",
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
        """Insert new hardware record

        Args:
            session: Database session
            host_id: Host ID
            hardware_data: Complete hardware data
            hw_ver: Hardware version number
            diff_state: Difference state
            sync_state: Sync state

        Returns:
            Newly created hardware record
        """
        try:
            # Generate snowflake ID
            new_id = generate_snowflake_id()

            new_hw_rec = HostHwRec(
                id=new_id,  # Explicitly set snowflake ID
                host_id=host_id,
                hw_info=hardware_data,  # Store complete hardware data
                hw_ver=hw_ver,
                diff_state=diff_state,
                sync_state=sync_state,
            )

            session.add(new_hw_rec)
            await session.flush()  # Ensure data is written

            logger.info(
                "Inserted new hardware record successfully",
                extra={
                    "hw_rec_id": new_hw_rec.id,
                    "host_id": host_id,
                },
            )

            return new_hw_rec

        except Exception as e:
            logger.error(
                "Failed to insert hardware record",
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
        """Report test case execution result

        Args:
            host_id: Host ID (obtained from token)
            tc_id: Test case ID
            state: Execution state (0-free 1-started 2-success 3-failed)
            result_msg: Result message
            log_url: Log file URL

        Returns:
            Update result

        Raises:
            BusinessError: Business logic error
        """
        try:
            logger.info(
                "Start processing test case result report",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "state": state,
                },
            )

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. Query latest execution log record
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
                        message=f"Execution record not found for host {host_id} test case {tc_id}",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "Found execution log record",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "current_state": exec_log.case_state,
                    },
                )

                # 2. Update execution state and result
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
                    "Test case result report succeeded",
                    extra={
                        "log_id": exec_log.id,
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "old_state": exec_log.case_state,
                        "new_state": state,
                    },
                )

                return {
                    "host_id": str(host_id),  # ✅ Convert to string to avoid precision loss
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
                "Test case result report failed",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Test case result report processing failed",
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
        """Update test case expected end time

        Args:
            host_id: Host ID (obtained from token)
            tc_id: Test case ID
            due_time_minutes: Expected end time (minutes difference, integer)

        Returns:
            Update result

        Raises:
            BusinessError: Business logic error
        """
        try:
            # Calculate actual expected end time (current time + minutes)
            # ✅ Use configured database timezone matching timeout task logic
            now = datetime.now(get_db_timezone())
            due_time = now + timedelta(minutes=due_time_minutes)

            logger.info(
                "Start processing expected end time report",
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
                # 1. Query latest execution log record that is executing
                # Query conditions: host_id, tc_id, case_state=1 (started state), del_flag=0
                stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_id,
                            HostExecLog.tc_id == tc_id,
                            HostExecLog.case_state == 1,  # Started state (executing)
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
                        message=f"Execution record not found for host {host_id} test case {tc_id}",
                        message_key="error.host.exec_log_not_found",
                        error_code="EXEC_LOG_NOT_FOUND",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=400,
                        details={"host_id": host_id, "tc_id": tc_id},
                    )

                logger.info(
                    "Found executing log record",
                    extra={
                        "host_id": host_id,
                        "tc_id": tc_id,
                        "log_id": exec_log.id,
                        "current_due_time": exec_log.due_time.isoformat() if exec_log.due_time else None,
                    },
                )

                # 2. Update due_time
                update_stmt = update(HostExecLog).where(HostExecLog.id == exec_log.id).values(due_time=due_time)

                await session.execute(update_stmt)
                await session.commit()

                logger.info(
                    "Expected end time update completed",
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
                "Exception processing expected end time report",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Expected end time report processing failed",
                error_code="DUE_TIME_UPDATE_FAILED",
                code=ServiceErrorCodes.HOST_DUE_TIME_UPDATE_FAILED,
                http_status_code=500,
            )

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
            Update result, containing host_id, host_state, vnc_state, and updated fields

        Raises:
            BusinessError: Business logic error
        """
        try:
            logger.info(
                "Start processing Agent VNC connection state report",
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
                        # ✅ When vnc_state = 1 (connection succeeded) but host_state is not "
                        # HOST_STATE_LOCKED, return explicit exception
                        logger.warning(
                            "VNC connection succeeded, but host state does not match",
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "required_host_state": HOST_STATE_LOCKED,
                                "vnc_state": vnc_state,
                            },
                        )
                        raise BusinessError(
                            message=(
                                f"VNC connection succeeded, but host state does not match. "
                                f"Current state: {current_host_state}, "
                                f"required state: {HOST_STATE_LOCKED} (locked)"
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
                    # ✅ Check if there are any execution logs for this host
                    # If there are valid execution logs (del_flag=0), do NOT reset host state
                    exec_log_stmt = (
                        select(HostExecLog)
                        .where(
                            and_(
                                HostExecLog.host_id == host_id,
                                HostExecLog.case_state < CASE_STATE_SUCCESS,
                                HostExecLog.del_flag == 0,
                            )
                        )
                        .limit(1)
                    )
                    exec_log_result = await session.execute(exec_log_stmt)
                    has_exec_log = exec_log_result.scalar_one_or_none()

                    if has_exec_log:
                        logger.info(
                            "VNC connection disconnected/failed, but host has execution logs, keep original state",
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "vnc_state": vnc_state,
                                "exec_log_id": has_exec_log.id,
                            },
                        )
                    # ✅ Only hosts in business state (< 5) will be reset to free, "
                    # avoid affecting hosts in pending/registration state
                    elif current_host_state is not None and current_host_state < 5:
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
                                "VNC connection disconnected/failed, "
                                "but host is in non-business state (>=5), keep original state"
                            ),
                            extra={
                                "host_id": host_id,
                                "current_host_state": current_host_state,
                                "vnc_state": vnc_state,
                            },
                        )

                # 4. If update is needed, execute update operation
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
        1. Query latest valid record (del_flag=0) from host_upd table based on host_id, app_name, app_ver
        2. If record not found, create new record (before creating, logically delete other "
        "valid records to ensure only one valid record)
        3. Update app_state field (1=updating, 2=success, 3=failed)
        4. If biz_state=2 (success):
           - Update host_rec table host_state=0 (free)
           - Update host_rec table agent_ver (new version, if provided)
           - Logically delete current record in host_upd table (del_flag=1)

        Args:
            host_id: Host ID
            app_name: Application name
            app_ver: Application version number
            biz_state: Business state (1=updating, 2=success, 3=failed)
            agent_ver: Agent version number (required when update succeeds)

        Returns:
            Dict[str, Any]: Dictionary containing update result

        Raises:
            BusinessError: Raises when update fails or business logic error
        """
        try:
            logger.info(
                "Start processing OTA update status report",
                extra={
                    "host_id": host_id,
                    "app_name": app_name,
                    "app_ver": app_ver,
                    "biz_state": biz_state,
                    "agent_ver": agent_ver,
                },
            )

            # Validate agent_ver is required when biz_state=2
            if biz_state == 2 and not agent_ver:
                raise BusinessError(
                    message="agent_ver field is required when update succeeds",
                    error_code="AGENT_VER_REQUIRED",
                    code=ServiceErrorCodes.HOST_AGENT_VER_REQUIRED,
                    http_status_code=400,
                )

            # Map biz_state to app_state (1=updating, 2=success, 3=failed)
            app_state = biz_state

            session_factory = self.session_factory
            async with session_factory() as session:
                # 1. Query latest valid record from host_upd table
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
                    # 2. If record not found, first logically delete other valid records (ensure only one valid record)
                    logger.info(
                        "OTA update record not found, preparing to create new record",
                        extra={
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                        },
                    )

                    # Logically delete all valid records for this host_id (ensure only one valid record)
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
                            "Logically deleted other valid records to ensure only one valid record",
                            extra={
                                "host_id": host_id,
                                "app_name": app_name,
                                "deleted_count": deleted_count,
                            },
                        )

                    # Create new record
                    host_upd = HostUpd(
                        host_id=host_id,
                        app_name=app_name,
                        app_ver=app_ver,
                        app_state=app_state,
                        created_by=None,
                        updated_by=None,
                    )
                    session.add(host_upd)
                    await session.flush()  # Flush to get generated ID
                    is_new_record = True

                    logger.info(
                        "Created new OTA update record",
                        extra={
                            "host_upd_id": host_upd.id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                            "app_state": app_state,
                        },
                    )
                else:
                    # 3. If record found, update app_state
                    old_app_state = host_upd.app_state
                    update_host_upd_stmt = update(HostUpd).where(HostUpd.id == host_upd.id).values(app_state=app_state)
                    await session.execute(update_host_upd_stmt)

                    logger.info(
                        "host_upd table state updated",
                        extra={
                            "host_upd_id": host_upd.id,
                            "host_id": host_id,
                            "old_app_state": old_app_state,
                            "new_app_state": app_state,
                        },
                    )

                # 4. If biz_state=2 (success), update host_rec table and logically delete host_upd record
                new_host_state = None
                if biz_state == 2:
                    # 4.1 Query and update host_rec table
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
                            "Host record not found, skipping host_rec table update",
                            extra={
                                "host_id": host_id,
                                "host_upd_id": host_upd.id,
                            },
                        )
                    else:
                        # Update host_state=0 (free) and agent_ver
                        old_host_state = host_rec.host_state
                        old_agent_ver = host_rec.agent_ver

                        update_values: Dict[str, Any] = {}

                        # ✅ Only hosts in business state (< 5) will be reset to free, "
                        # avoid affecting hosts in pending/registration state
                        if old_host_state < 5:
                            update_values["host_state"] = HOST_STATE_FREE
                        else:
                            logger.info(
                                (
                                    "Host is in non-business state (>=5), "
                                    "do not reset to free state after OTA update succeeds"
                                ),
                                extra={
                                    "host_id": host_id,
                                    "host_state": old_host_state,
                                },
                            )
                        if agent_ver:
                            # Limit agent_ver length to 10
                            update_values["agent_ver"] = agent_ver[:10] if len(agent_ver) > 10 else agent_ver

                        update_host_rec_stmt = update(HostRec).where(HostRec.id == host_id).values(**update_values)
                        await session.execute(update_host_rec_stmt)

                        new_host_state = HOST_STATE_FREE

                        logger.info(
                            "host_rec table updated (OTA update succeeded)",
                            extra={
                                "host_id": host_id,
                                "old_host_state": old_host_state,
                                "new_host_state": new_host_state,
                                "old_agent_ver": old_agent_ver,
                                "new_agent_ver": update_values.get("agent_ver"),
                            },
                        )

                    # 4.2 Logically delete current record in host_upd table (update completed)
                    delete_host_upd_stmt = update(HostUpd).where(HostUpd.id == host_upd.id).values(del_flag=1)
                    await session.execute(delete_host_upd_stmt)

                    logger.info(
                        "host_upd record logically deleted (OTA update succeeded)",
                        extra={
                            "host_upd_id": host_upd.id,
                            "host_id": host_id,
                            "app_name": app_name,
                            "app_ver": app_ver,
                        },
                    )

                # Commit transaction
                await session.commit()

                # Refresh host_upd object to get latest state (if record was not deleted)
                if biz_state != 2:
                    await session.refresh(host_upd)

                logger.info(
                    "OTA update status report processing completed",
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
                "OTA update status report processing failed",
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
                message="OTA update status report processing failed",
                error_code="OTA_UPDATE_STATUS_REPORT_FAILED",
                code=ServiceErrorCodes.HOST_OTA_UPDATE_STATUS_REPORT_FAILED,
                http_status_code=500,
            )

    async def update_due_time(
        self,
        host_id: int,
        tc_id: str,
        due_time: datetime,
    ) -> Dict[str, Any]:
        """更新测试用例预期结束时间

        Args:
            host_id: 主机ID（从token中获取）
            tc_id: 测试用例ID
            due_time: 预期结束时间

        Returns:
            更新结果

        Raises:
            BusinessError: 业务逻辑错误
        """
        try:
            logger.info(
                "开始处理预期结束时间上报",
                extra={
                    "host_id": host_id,
                    "tc_id": tc_id,
                    "due_time": due_time.isoformat() if due_time else None,
                },
            )

            session_factory = mariadb_manager.get_session()
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
        """Send hardware change email notification

        Args:
            host_id: Host ID
            hardware_id: Hardware ID
            host_ip: Host IP
            diff_state: Change type (1=revision changed, 2=content changed)
            hw_rec_id: Hardware record ID
        """
        try:
            # 1. Get recipient email list (from system configuration)
            maintain_emails = await self._get_maintain_emails()
            if not maintain_emails:
                logger.warning(
                    "Maintenance personnel email not configured, skipping hardware change email notification"
                )
                return

            # 2. Determine change type
            change_type_map = {
                self.DIFF_STATE_VERSION: "Revision changed",
                self.DIFF_STATE_CONTENT: "Content changed",
            }
            change_type = change_type_map.get(diff_state, "Unknown change")

            # 3. Build email subject and content
            # Externalize email subject and content using i18n
            subject = t("email.hardware.change.subject", locale="zh_CN", host_id=host_id)

            content = t(
                "email.hardware.change.content",
                locale="zh_CN",
                host_id=host_id,
                hardware_id=hardware_id,
                host_ip=host_ip,
                change_type=change_type,
                hw_rec_id=hw_rec_id,
            )

            # 4. Send email
            result = await send_email(
                to_emails=maintain_emails,
                subject=subject,
                content=content,
                locale="zh_CN",
            )

            if result.get("success"):
                logger.info(
                    "Hardware change email notification sent successfully",
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
                    "Hardware change email notification failed",
                    extra={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "host_ip": host_ip,
                        "change_type": change_type,
                        "errors": result.get("errors", []),
                    },
                )

        except Exception as e:
            # Email sending failure does not affect main flow, only log
            logger.error(
                f"Exception sending hardware change email notification: {e!s}",
                extra={
                    "host_id": host_id,
                    "hardware_id": hardware_id,
                    "host_ip": host_ip,
                    "diff_state": diff_state,
                },
                exc_info=True,
            )

    async def _get_maintain_emails(self) -> List[str]:
        """Get maintenance personnel email list

        Query configuration from sys_conf table where conf_key='maintain_email'

        Returns:
            Maintenance personnel email list
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
                    logger.warning("Maintenance personnel email configuration not found (conf_key='maintain_email')")
                    return []

                # conf_json may be a string list or comma-separated string
                emails = conf.conf_json
                if isinstance(emails, str):
                    # If it's a string, split by comma
                    emails = [email.strip() for email in emails.split(",") if email.strip()]
                elif isinstance(emails, list):
                    # If it's a list, use directly
                    emails = [str(email).strip() for email in emails if email]
                else:
                    logger.warning(
                        "Maintenance personnel email configuration format is incorrect",
                        extra={"email_type": type(emails).__name__},
                    )
                    return []

                return emails

        except Exception as e:
            logger.error(
                "Failed to get maintenance personnel email list",
                extra={"error": str(e)},
                exc_info=True,
            )
            return []


# Global service instance (singleton pattern)
_agent_report_service_instance: Optional[AgentReportService] = None


def get_agent_report_service() -> AgentReportService:
    """Get Agent hardware service instance (singleton pattern)"""
    global _agent_report_service_instance

    if _agent_report_service_instance is None:
        _agent_report_service_instance = AgentReportService()

    return _agent_report_service_instance
