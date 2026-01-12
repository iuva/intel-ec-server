"""Admin backend pending approval host management service

Provides core business logic for pending approval host querying and other operations used by the admin backend.

Note: Utility functions and email service have been split into separate modules:
- admin_appr_utils.py: Utility functions (build_host_table, call_hardware_api, etc.)
- admin_appr_email_service.py: Email service (ApprovalEmailService)
"""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select, update

# Use try-except to handle path imports
try:
    from app.constants.host_constants import (
        APPR_STATE_ENABLE,
        HOST_STATE_FREE,
        SYNC_STATE_WAIT,
    )
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailResponse,
        AdminApprHostHwInfo,
        AdminApprHostInfo,
        AdminApprHostListRequest,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )
    from app.services.admin_appr_email_service import send_approval_email

    # Import from split modules
    from app.services.admin_appr_utils import call_hardware_api
    from app.utils.logging_helpers import log_operation_start
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import (
        APPR_STATE_ENABLE,
        HOST_STATE_FREE,
        SYNC_STATE_WAIT,
    )
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailResponse,
        AdminApprHostHwInfo,
        AdminApprHostInfo,
        AdminApprHostListRequest,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )
    from app.services.admin_appr_email_service import send_approval_email

    # Import from split modules
    from app.services.admin_appr_utils import call_hardware_api
    from app.utils.logging_helpers import log_operation_start
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse

logger = get_logger(__name__)


class AdminApprHostService:
    """Admin backend pending approval host management service class

    Provides business logic for querying, searching, and other operations on pending approval hosts.

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
        - Initialize on first call
        - Reuse cached factory instance on subsequent calls
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    async def _validate_and_resolve_host_ids(
        self,
        request: AdminApprHostApproveRequest,
        locale: str = "zh_CN",
    ) -> List[int]:
        """Validate parameters and resolve host_ids

        Args:
            request: Approve enable request parameters
            locale: Language preference

        Returns:
            List[int]: List of host IDs to process, returns empty list if not found

        Raises:
            BusinessError: When parameter validation fails
        """
        if request.diff_type is None or request.diff_type == 2:
            # When diff_type is None or 2, host_ids is required
            if not request.host_ids or len(request.host_ids) == 0:
                raise BusinessError(
                    message=f"When diff_type={request.diff_type}, host_ids is a required parameter",
                    message_key="error.host.appr_host_ids_required",
                    error_code="HOST_IDS_REQUIRED",
                    code=ServiceErrorCodes.VALIDATION_ERROR,
                    http_status_code=400,
                )
            return request.host_ids

        elif request.diff_type == 1:
            # When diff_type = 1, if host_ids is provided, return directly
            if request.host_ids and len(request.host_ids) > 0:
                return request.host_ids

            # If host_ids is not provided, query all matching host_ids
            session_factory = self.session_factory
            async with session_factory() as temp_session:
                hw_query_stmt = (
                    select(HostHwRec.host_id)
                    .where(
                        and_(
                            HostHwRec.sync_state == 1,
                            HostHwRec.diff_state == 1,
                            HostHwRec.del_flag == 0,
                        )
                    )
                    .distinct()
                )
                hw_query_result = await temp_session.execute(hw_query_stmt)
                host_ids_raw = hw_query_result.scalars().all()
                host_ids_to_process = [hid for hid in set(host_ids_raw) if hid is not None]

                if not host_ids_to_process:
                    logger.info(
                        "No matching hosts found (diff_type=1, sync_state=1, diff_state=1)",
                        extra={"diff_type": request.diff_type},
                    )
                    return []

                return host_ids_to_process
        else:
            raise BusinessError(
                message=t(
                    "error.host.diff_type_not_supported",
                    locale=locale,
                    diff_type=request.diff_type,
                    default=f"Unsupported diff_type: {request.diff_type}",
                ),
                message_key="error.host.diff_type_not_supported",
                error_code="DIFF_TYPE_NOT_SUPPORTED",
                code=ServiceErrorCodes.VALIDATION_ERROR,
                http_status_code=400,
            )

    def _validate_host_exists(
        self,
        host_id: int,
        host_recs_map: Dict[int, HostRec],
        locale: str = "zh_CN",
    ) -> Optional[HostRec]:
        """Validate if host exists and is not deleted

        Args:
            host_id: Host ID
            host_recs_map: Host record mapping dictionary
            locale: Language preference

        Returns:
            Optional[HostRec]: Host record, returns None if not exists
        """
        host_rec = host_recs_map.get(host_id)
        if not host_rec:
            logger.warning(
                "Host does not exist or has been deleted",
                extra={"host_id": host_id},
            )
        return host_rec

    async def _query_hardware_records(
        self,
        session: Any,
        host_ids: List[int],
        sync_state: Optional[int] = SYNC_STATE_WAIT,
        need_latest_only: bool = False,
    ) -> Dict[int, List[HostHwRec]]:
        """Query hardware records and group by host_id

        Args:
            session: Database session
            host_ids: List of host IDs
            sync_state: Sync state (None means no restriction)
            need_latest_only: Whether to only need the latest one (for diff_type is None)

        Returns:
            Dict[int, List[HostHwRec]]: Hardware records grouped by host_id
        """
        if not host_ids:
            return {}

        # Build query conditions
        conditions = [
            HostHwRec.host_id.in_(host_ids),
            HostHwRec.del_flag == 0,
        ]

        if sync_state is not None:
            conditions.append(HostHwRec.sync_state == sync_state)

        # Query hardware records
        hw_stmt = (
            select(HostHwRec)
            .where(and_(*conditions))
            .order_by(HostHwRec.host_id, desc(HostHwRec.created_time), desc(HostHwRec.id))
        )

        hw_result = await session.execute(hw_stmt)
        all_hw_recs = hw_result.scalars().all()

        # Group by host_id
        hw_recs_by_host: Dict[int, List[HostHwRec]] = {}

        if need_latest_only:
            # Only keep the latest one for each host_id
            for hw_rec in all_hw_recs:
                if hw_rec.host_id not in hw_recs_by_host:
                    hw_recs_by_host[hw_rec.host_id] = [hw_rec]
        else:
            # Keep all records
            for hw_rec in all_hw_recs:
                if hw_rec.host_id not in hw_recs_by_host:
                    hw_recs_by_host[hw_rec.host_id] = []
                hw_recs_by_host[hw_rec.host_id].append(hw_rec)

        return hw_recs_by_host

    async def _process_manual_enable(
        self,
        host_id: int,
        host_rec: HostRec,
        hw_recs: List[HostHwRec],
        appr_by: int,
        http_request: Any,
        locale: str = "zh_CN",
    ) -> Dict[str, Any]:
        """Process manual enable (diff_type is None)

        Args:
            host_id: Host ID
            host_rec: Host record
            hw_recs: Hardware record list
            appr_by: Approver ID
            http_request: FastAPI Request object
            locale: Language preference

        Returns:
            Dict[str, Any]: Processing result, contains success, host_id, message, hardware_id, host_update
        """
        # Default update values
        host_update: Dict[str, Any] = {
            "appr_state": APPR_STATE_ENABLE,
            "host_state": HOST_STATE_FREE,
        }

        # Check if external API call is needed (host_state 5 or 6)
        if host_rec.host_state in (5, 6):
            latest_hw_rec = hw_recs[0] if hw_recs else None
            if latest_hw_rec and latest_hw_rec.hw_info:
                try:
                    # ✅ Determine whether to call create or update API based on host_state
                    # host_state = 5 (pending activation): New host, call create API (***REMOVED*** None)
                    # host_state = 6 (hardware changed): Existing host, call update API (***REMOVED*** hardware_id)
                    api_hardware_id: Optional[str] = None
                    if host_rec.host_state == 6:
                        # Hardware changed: Use existing hardware_id to call update API
                        # ✅ Check if hardware_id is valid (not None and not empty string)
                        existing_hw_id = host_rec.hardware_id
                        if existing_hw_id and existing_hw_id.strip():
                            api_hardware_id = existing_hw_id
                            api_type = "update"
                        else:
                            # hardware_id is empty string, treat as invalid, call create API
                            api_hardware_id = None
                            api_type = "create"
                            logger.warning(
                                "host_state=6 but hardware_id is empty string, forcing create API call",
                                extra={
                                    "host_id": host_id,
                                    "host_state": host_rec.host_state,
                                    "existing_hardware_id": existing_hw_id,
                                    "note": "Hardware changed state but hardware_id is invalid, calling create API",
                                },
                            )
                    else:
                        # host_state = 5 (pending activation): Force create API call, even if hardware_id is not empty
                        api_hardware_id = None
                        api_type = "create"
                        existing_hw_id = host_rec.hardware_id
                        if existing_hw_id and existing_hw_id.strip():
                            logger.warning(
                                "host_state=5 but hardware_id is not empty, forcing create API call",
                                extra={
                                    "host_id": host_id,
                                    "host_state": host_rec.host_state,
                                    "existing_hardware_id": existing_hw_id,
                                    "note": (
                                        "Pending activation state should call create API, "
                                        "ignoring existing hardware_id"
                                    ),
                                },
                            )

                    logger.info(
                        f"Preparing to call external hardware API ({api_type})",
                        extra={
                            "host_id": host_id,
                            "host_state": host_rec.host_state,
                            "api_type": api_type,
                            "api_hardware_id": api_hardware_id,
                            "existing_hardware_id": host_rec.hardware_id,
                        },
                    )

                    api_result = await call_hardware_api(
                        hardware_id=api_hardware_id,
                        hw_info=latest_hw_rec.hw_info,
                        request=http_request,
                        user_id=appr_by,
                        locale=locale,
                        host_id=host_id,
                    )
                    hardware_id = api_result.get("hardware_id")
                    host_name = api_result.get("host_name")

                    if hardware_id:
                        host_update["hardware_id"] = hardware_id
                    # If host_name exists and is not empty, add to update dictionary
                    if host_name and host_name.strip():
                        host_update["host_no"] = host_name.strip()

                    logger.info(
                        "External hardware API call succeeded (Empty Diff Type)",
                        extra={
                            "host_id": host_id,
                            "host_state": host_rec.host_state,
                            "api_type": api_type,
                            "hardware_id": hardware_id,
                            "host_name": host_name,
                            "is_new": api_hardware_id is None,
                        },
                    )
                except Exception as e:
                    logger.error(
                        "External hardware API call failed (Empty Diff Type)",
                        extra={"host_id": host_id, "error": str(e)},
                        exc_info=True,
                    )
                    raise BusinessError(
                        message=f"External API call failed: {str(e)}",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=500,
                    )
            else:
                logger.warning(
                    "State is 5/6 but hardware record not found or hw_info is empty, skipping external API call",
                    extra={"host_id": host_id, "host_state": host_rec.host_state},
                )

        return {
            "success": True,
            "host_id": host_id,
            "message": t(
                "success.host.manual_enabled",
                locale=locale,
                default="Host enabled successfully",
            ),
            "hardware_id": host_update.get("hardware_id"),
            "hw_id": None,
            "host_update": host_update,
            "hw_updates": {},
        }

    async def _process_hardware_change_approval(
        self,
        host_id: int,
        host_rec: HostRec,
        hw_recs: List[HostHwRec],
        appr_by: int,
        http_request: Any,
        locale: str = "zh_CN",
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Process hardware change approval (diff_type == 1 or 2)

        Args:
            host_id: Host ID
            host_rec: Host record
            hw_recs: Hardware record list
            appr_by: Approver ID
            http_request: FastAPI Request object
            locale: Language preference
            session: Database session (for debug queries)

        Returns:
            Dict[str, Any]: Processing result, contains success, host_id, message,
                           hardware_id, hw_id, host_update, hw_updates

        Raises:
            BusinessError: When hardware record does not exist or processing fails
        """
        # Validate hardware records
        if not hw_recs:
            # Debug: Query all hardware records for this host (no sync_state restriction) to help troubleshoot
            if session:
                debug_hw_stmt = (
                    select(HostHwRec)
                    .where(
                        and_(
                            HostHwRec.host_id == host_id,
                            HostHwRec.del_flag == 0,
                        )
                    )
                    .order_by(desc(HostHwRec.created_time), desc(HostHwRec.id))
                )
                debug_hw_result = await session.execute(debug_hw_stmt)
                debug_hw_recs = debug_hw_result.scalars().all()

                # Count records with different sync_state
                sync_state_stats = {}
                for hw_rec in debug_hw_recs:
                    sync_state = hw_rec.sync_state
                    if sync_state not in sync_state_stats:
                        sync_state_stats[sync_state] = 0
                    sync_state_stats[sync_state] += 1

                logger.warning(
                    "No pending approval hardware records found, skipping approval",
                    extra={
                        "host_id": host_id,
                        "host_exists": True,
                        "debug_info": {
                            "total_hw_recs": len(debug_hw_recs),
                            "sync_state_stats": sync_state_stats,
                            "query_condition": {
                                "sync_state": 1,
                                "del_flag": 0,
                            },
                            "latest_hw_rec": {
                                "id": debug_hw_recs[0].id if debug_hw_recs else None,
                                "sync_state": debug_hw_recs[0].sync_state if debug_hw_recs else None,
                                "del_flag": debug_hw_recs[0].del_flag if debug_hw_recs else None,
                                "created_time": (
                                    debug_hw_recs[0].created_time.isoformat()
                                    if debug_hw_recs and debug_hw_recs[0].created_time
                                    else None
                                ),
                            },
                        },
                    },
                )

            raise BusinessError(
                message=t(
                    "error.host.hardware_not_found",
                    locale=locale,
                    host_id=host_id,
                    default=f"No pending approval hardware records found (ID: {host_id})",
                ),
                message_key="error.host.hardware_not_found",
                error_code="HARDWARE_NOT_FOUND",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=404,
            )

        # Get the latest hardware record
        latest_hw_rec = hw_recs[0]
        latest_hw_id = latest_hw_rec.id

        # Call external hardware API
        hardware_id = None
        if latest_hw_rec.hw_info:
            try:
                # ✅ Determine whether to call create or update API based on host_state
                # host_state = 5 (pending activation): New host, call create API (***REMOVED*** None)
                # host_state = 6 (hardware changed): Existing host, call update API (***REMOVED*** hardware_id)
                existing_hardware_id = host_rec.hardware_id
                api_hardware_id: Optional[str] = None
                if host_rec.host_state == 6:
                    # Hardware changed: Use existing hardware_id to call update API
                    # ✅ Check if hardware_id is valid (not None and not empty string)
                    if existing_hardware_id and existing_hardware_id.strip():
                        api_hardware_id = existing_hardware_id
                        api_type = "update"
                    else:
                        # hardware_id is empty string, treat as invalid, call create API
                        api_hardware_id = None
                        api_type = "create"
                        logger.warning(
                            (
                                "host_state=6 but hardware_id is empty string, "
                                "forcing create API call (hardware change approval)"
                            ),
                            extra={
                                "host_id": host_id,
                                "host_state": host_rec.host_state,
                                "existing_hardware_id": existing_hardware_id,
                                "diff_type": "hardware_change_approval",
                                "note": "Hardware changed state but hardware_id is invalid, calling create API",
                            },
                        )
                else:
                    # host_state = 5 (pending activation): Force create API call, even if hardware_id is not empty
                    api_hardware_id = None
                    api_type = "create"
                    if existing_hardware_id and existing_hardware_id.strip():
                        logger.warning(
                            (
                                "host_state=5 but hardware_id is not empty, "
                                "forcing create API call (hardware change approval)"
                            ),
                            extra={
                                "host_id": host_id,
                                "host_state": host_rec.host_state,
                                "existing_hardware_id": existing_hardware_id,
                                "diff_type": "hardware_change_approval",
                                "note": (
                                    "Pending activation state should call create API, "
                                    "ignoring existing hardware_id"
                                ),
                            },
                        )

                logger.info(
                    f"Preparing to call external hardware API ({api_type}, hardware change approval)",
                    extra={
                        "host_id": host_id,
                        "host_state": host_rec.host_state,
                        "api_type": api_type,
                        "api_hardware_id": api_hardware_id,
                        "existing_hardware_id": existing_hardware_id,
                        "diff_type": "hardware_change_approval",
                    },
                )

                api_result = await call_hardware_api(
                    hardware_id=api_hardware_id,
                    hw_info=latest_hw_rec.hw_info,
                    request=http_request,
                    user_id=appr_by,
                    locale=locale,
                    host_id=host_id,
                )
                hardware_id = api_result.get("hardware_id")
                host_name = api_result.get("host_name")

                logger.info(
                    "External hardware API call succeeded (hardware change approval)",
                    extra={
                        "host_id": host_id,
                        "host_state": host_rec.host_state,
                        "api_type": api_type,
                        "hardware_id": hardware_id,
                        "host_name": host_name,
                        "is_new": api_hardware_id is None,
                    },
                )
            except BusinessError:
                raise
            except Exception as e:
                logger.error(
                    "Failed to call external hardware API",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"Failed to call external hardware API: {str(e)}",
                    message_key="error.hardware.api_call_failed",
                    error_code="HARDWARE_API_CALL_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "host_id": host_id,
                        "error": str(e),
                    },
                )
        else:
            logger.warning(
                "Hardware record missing hw_info, skipping external hardware API call",
                extra={
                    "host_id": host_id,
                    "hw_rec_id": latest_hw_id,
                },
            )

        # Build update data
        now = datetime.now(timezone.utc)

        # Host update data
        host_update = {
            "appr_state": APPR_STATE_ENABLE,
            "host_state": HOST_STATE_FREE,
            "hw_id": latest_hw_id,
            "subm_time": now,
        }
        if hardware_id:
            host_update["hardware_id"] = hardware_id
        # If host_name exists and is not empty, add to update dictionary
        if host_name and host_name.strip():
            host_update["host_no"] = host_name.strip()

        # Hardware record update data
        hw_updates = {
            latest_hw_id: {
                "sync_state": 2,
                "appr_time": now,
                "appr_by": appr_by,
            }
        }
        if hardware_id:
            hw_updates[latest_hw_id]["hardware_id"] = hardware_id

        # Update other hardware records to sync_state = 4
        for hw_rec in hw_recs[1:]:
            hw_updates[hw_rec.id] = {"sync_state": 4}

        return {
            "success": True,
            "host_id": host_id,
            "message": t("success.host.approved", locale=locale, default="Host enabled successfully"),
            "hardware_id": hardware_id,
            "hw_id": latest_hw_id,
            "host_update": host_update,
            "hw_updates": hw_updates,
        }

    async def _bulk_update_host_records(
        self,
        session: Any,
        host_updates: Dict[int, Dict[str, Any]],
    ) -> None:
        """Bulk update host_rec table (optimization: group by update fields)

        Args:
            session: Database session
            host_updates: Host update data dictionary {host_id: {field: value}}
        """
        if not host_updates:
            return

        # Separate records that need host_no update and records that only update other fields
        hosts_with_host_no: Dict[int, Dict[str, Any]] = {}
        hosts_without_host_no: Dict[int, Dict[str, Any]] = {}

        for host_id, update_values in host_updates.items():
            if "host_no" in update_values:
                hosts_with_host_no[host_id] = update_values
            else:
                hosts_without_host_no[host_id] = update_values

        # Bulk update (with host_no)
        if hosts_with_host_no:
            bulk_update_data = [
                {"id": host_id, **update_values} for host_id, update_values in hosts_with_host_no.items()
            ]

            def _bulk_update_with_host_no(sync_session: Any) -> None:
                sync_session.bulk_update_mappings(HostRec, bulk_update_data)

            await session.run_sync(_bulk_update_with_host_no)

            logger.debug(
                "Bulk update host records (including host_no)",
                extra={
                    "count": len(hosts_with_host_no),
                    "host_ids": list(hosts_with_host_no.keys())[:10],  # Only log first 10
                },
            )

        # Bulk update (without host_no)
        if hosts_without_host_no:
            bulk_update_data = [
                {"id": host_id, **update_values} for host_id, update_values in hosts_without_host_no.items()
            ]

            def _bulk_update_without_host_no(sync_session: Any) -> None:
                sync_session.bulk_update_mappings(HostRec, bulk_update_data)

            await session.run_sync(_bulk_update_without_host_no)

            logger.debug(
                "Bulk update host records (excluding host_no)",
                extra={
                    "count": len(hosts_without_host_no),
                },
            )

    async def _bulk_update_hardware_records(
        self,
        session: Any,
        hw_updates: Dict[int, Dict[str, Any]],
        now: datetime,
        appr_by: int,
    ) -> None:
        """Bulk update host_hw_rec table

        ✅ Optimization: Use CASE WHEN for bulk update to reduce SQL execution count
        - Before optimization: N records require N SQL executions
        - After optimization: At most 3 SQL executions (with hardware_id, without hardware_id, others)

        Args:
            session: Database session
            hw_updates: Hardware record update data dictionary {hw_rec_id: {field: value}}
            now: Current time
            appr_by: Approver ID
        """
        if not hw_updates:
            return

        # Separate records that need hardware_id update and regular records
        latest_hw_ids_with_hardware_id: List[int] = []
        latest_hw_ids_without_hardware_id: List[int] = []
        other_hw_ids: List[int] = []
        hw_rec_hardware_id_map: Dict[int, str] = {}

        for hw_rec_id, update_values in hw_updates.items():
            if "hardware_id" in update_values:
                latest_hw_ids_with_hardware_id.append(hw_rec_id)
                hw_rec_hardware_id_map[hw_rec_id] = update_values["hardware_id"]
            elif update_values.get("sync_state") == 2:
                latest_hw_ids_without_hardware_id.append(hw_rec_id)
            else:
                other_hw_ids.append(hw_rec_id)

        # ✅ Optimization: Use CASE WHEN for bulk update (with hardware_id)
        # Merge N SQL statements into 1 SQL statement
        if latest_hw_ids_with_hardware_id:
            from sqlalchemy import case

            # Build CASE WHEN expression: CASE id WHEN 1 THEN 'hw_id_1' WHEN 2 THEN 'hw_id_2' END
            hardware_id_case = case(
                hw_rec_hardware_id_map,
                value=HostHwRec.id,
            )

            update_stmt = (
                update(HostHwRec)
                .where(HostHwRec.id.in_(latest_hw_ids_with_hardware_id))
                .values(
                    sync_state=2,
                    appr_time=now,
                    appr_by=appr_by,
                    hardware_id=hardware_id_case,
                )
            )
            await session.execute(update_stmt)

            logger.debug(
                "Bulk update hardware records (with hardware_id)",
                extra={
                    "count": len(latest_hw_ids_with_hardware_id),
                    "hw_ids": latest_hw_ids_with_hardware_id[:10],  # Only log first 10
                },
            )

        # Bulk update latest hardware records (without hardware_id)
        if latest_hw_ids_without_hardware_id:
            update_latest_stmt = (
                update(HostHwRec)
                .where(HostHwRec.id.in_(latest_hw_ids_without_hardware_id))
                .values(
                    sync_state=2,
                    appr_time=now,
                    appr_by=appr_by,
                )
            )
            await session.execute(update_latest_stmt)

            logger.debug(
                "Bulk update hardware records (without hardware_id)",
                extra={
                    "count": len(latest_hw_ids_without_hardware_id),
                },
            )

        # Bulk update other hardware records
        if other_hw_ids:
            update_other_stmt = update(HostHwRec).where(HostHwRec.id.in_(other_hw_ids)).values(sync_state=4)
            await session.execute(update_other_stmt)

            logger.debug(
                "Bulk update other hardware records",
                extra={
                    "count": len(other_hw_ids),
                },
            )

    @handle_service_errors(
        error_message="Failed to query pending approval host list",
        error_code="QUERY_APPR_HOST_LIST_FAILED",
    )
    async def list_appr_hosts(
        self,
        request: AdminApprHostListRequest,
    ) -> Tuple[List[AdminApprHostInfo], PaginationResponse]:
        """Query pending approval host list (paginated)

        Business logic:
        1. Query host_rec table
        2. Conditions: host_state > 4 and host_state < 8, appr_state != 1, del_flag = 0
        3. Support filtering by mac, mg_id, host_state
        4. Order by created_time descending
        5. Join host_hw_rec table to get diff_state of the latest record for each host_id
           - Only query records with sync_state = 1 (pending sync)
           - Order by created_time descending, take diff_state of first record
           - Keep consistent with diff_state retrieval logic of get_appr_host_detail interface

        Args:
            request: Query request parameters (pagination, search conditions)

        Returns:
            Tuple[List[AdminApprHostInfo], PaginationResponse]: Pending approval host list and pagination information

        Raises:
            BusinessError: When query fails
        """
        log_operation_start(
            "Query pending approval host list",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "mg_id": request.mg_id,
                "host_state": request.host_state,
            },
            logger_instance=logger,
        )

        try:
            session_factory = self.session_factory
            logger.debug("Successfully obtained database session factory")
        except Exception as e:
            logger.error(
                "Failed to obtain database session factory",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

        try:
            async with session_factory() as session:
                logger.debug("Database session created successfully")

                # Build base query conditions
                # host_state > 4 and host_state < 8, appr_state != 1, del_flag = 0
                base_conditions = [
                    HostRec.host_state > 4,
                    HostRec.host_state < 8,
                    HostRec.appr_state != 1,
                    HostRec.del_flag == 0,
                ]

                # Add search conditions
                if request.mac:
                    base_conditions.append(HostRec.mac_addr.like(f"%{request.mac}%"))

                if request.mg_id:
                    base_conditions.append(HostRec.mg_id.like(f"%{request.mg_id}%"))

                if request.host_state is not None:
                    base_conditions.append(HostRec.host_state == request.host_state)

                # 1. Query total count
                count_stmt = select(func.count(HostRec.id)).where(and_(*base_conditions))
                count_result = await session.execute(count_stmt)
                total = count_result.scalar() or 0

                # 2. Paginated query: Order by created_time descending, LEFT JOIN to get diff_state
                # Optimization: Directly join host_hw_rec table, no subquery needed
                # (assuming each host has at most one sync_state=1 record)
                pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

                stmt = (
                    select(
                        HostRec.id.label("host_id"),
                        HostRec.mg_id,
                        HostRec.mac_addr,
                        HostRec.host_state,
                        HostRec.subm_time,
                        HostHwRec.diff_state,
                    )
                    .outerjoin(
                        HostHwRec,
                        and_(
                            HostHwRec.host_id == HostRec.id,
                            HostHwRec.sync_state == SYNC_STATE_WAIT,  # sync_state = 1 (pending sync)
                            HostHwRec.del_flag == 0,
                        ),
                    )
                    .where(and_(*base_conditions))
                    .order_by(HostRec.created_time.desc())
                    .offset(pagination_params.offset)
                    .limit(pagination_params.limit)
                )

                try:
                    result = await session.execute(stmt)
                    rows = result.all()
                except Exception as e:
                    logger.error(
                        "Query execution failed",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "sql_preview": str(stmt)[:500] if hasattr(stmt, "__str__") else "N/A",
                        },
                        exc_info=True,
                    )
                    raise

                # 3. Build response data
                host_info_list: List[AdminApprHostInfo] = []
                for row in rows:
                    try:
                        # Safely get diff_state, as LEFT JOIN may return None
                        diff_state = getattr(row, "diff_state", None)

                        host_info = AdminApprHostInfo(
                            host_id=str(row.host_id),  # ✅ Convert to string to avoid precision loss
                            mg_id=row.mg_id,
                            mac_addr=row.mac_addr,
                            host_state=row.host_state,
                            subm_time=row.subm_time,
                            diff_state=diff_state,
                        )
                        host_info_list.append(host_info)
                    except Exception as e:
                        logger.error(
                            "Failed to build AdminApprHostInfo object",
                            extra={
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "row_host_id": getattr(row, "host_id", None),
                                "row_mg_id": getattr(row, "mg_id", None),
                                "row_keys": [key for key in dir(row) if not key.startswith("_")],
                            },
                            exc_info=True,
                        )
                        raise

                # 4. Build pagination response
                pagination_response = PaginationResponse(
                    page=request.page,
                    page_size=request.page_size,
                    total=total,
                )

                logger.info(
                    "Query pending approval host list completed",
                    extra={
                        "total": total,
                        "returned_count": len(host_info_list),
                        "page": request.page,
                        "page_size": request.page_size,
                    },
                )

                return host_info_list, pagination_response
        except Exception as e:
            logger.error(
                f"Database operation failed: {type(e).__name__}: {str(e)}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": "list_appr_hosts",
                },
                exc_info=True,
            )
            raise

    @handle_service_errors(
        error_message="Failed to query pending approval host detail",
        error_code="QUERY_APPR_HOST_DETAIL_FAILED",
    )
    async def get_appr_host_detail(self, host_id: int, locale: str = "zh_CN") -> AdminApprHostDetailResponse:
        """Query pending approval host detail

        Business logic:
        1. Query host_rec table data where id = host_id
        2. Join host_hw_rec table, query data with sync_state = 1
        3. Order by host_hw_rec.created_time descending
        4. Password field needs AES decryption

        Args:
            host_id: Host ID (host_rec.id)

        Returns:
            AdminApprHostDetailResponse: Pending approval host detail information

        Raises:
            BusinessError: When host does not exist
        """
        logger.info(
            "Start querying pending approval host detail",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Verify if host exists and is not deleted (using utility function)
            host_rec = await validate_host_exists(session, HostRec, host_id, locale=locale)

            # 2. Query all records from host_hw_rec table with sync_state=1 (ordered by created_time descending)
            hw_stmt = (
                select(HostHwRec)
                .where(
                    and_(
                        HostHwRec.host_id == host_id,
                        HostHwRec.sync_state == SYNC_STATE_WAIT,  # sync_state = 1 (pending sync)
                        HostHwRec.del_flag == 0,
                    )
                )
                .order_by(HostHwRec.created_time.desc())
            )
            hw_result = await session.execute(hw_stmt)
            hw_recs = hw_result.scalars().all()

            # 3. Decrypt ***REMOVED***word (AES encrypted)
            ***REMOVED*** = None
            if host_rec.host_pwd:
                try:
                    ***REMOVED*** = aes_decrypt(host_rec.host_pwd)
                    if ***REMOVED***:
                        logger.debug(
                            "Password decryption succeeded",
                            extra={
                                "host_id": host_id,
                            },
                        )
                    else:
                        logger.warning(
                            "Password decryption failed (returned None)",
                            extra={
                                "host_id": host_id,
                                "note": "Password format may be incorrect or encryption method mismatch",
                            },
                        )
                except Exception as e:
                    logger.warning(
                        "Password decryption exception",
                        extra={
                            "host_id": host_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    # Return None when decryption fails, instead of raising exception
                    ***REMOVED*** = None

            # 4. Build hardware information list
            hw_list: List[AdminApprHostHwInfo] = []
            diff_state: Optional[int] = None

            for hw_rec in hw_recs:
                hw_info = AdminApprHostHwInfo(
                    created_time=hw_rec.created_time,
                    hw_info=hw_rec.hw_info,
                )
                hw_list.append(hw_info)

            # Get diff_state of the latest hardware record
            # (already ordered by created_time descending, first one is latest)
            if hw_recs:
                diff_state = hw_recs[0].diff_state

            # 5. Build response data
            detail = AdminApprHostDetailResponse(
                mg_id=host_rec.mg_id,
                mac=host_rec.mac_addr,
                ip=host_rec.host_ip,
                username=host_rec.host_acct,
                ***REMOVED***word=***REMOVED***,
                port=host_rec.host_port,
                host_state=host_rec.host_state,
                diff_state=diff_state,
                hw_list=hw_list,
            )

            logger.info(
                "Query pending approval host detail completed",
                extra={
                    "host_id": host_id,
                    "hw_list_count": len(hw_list),
                    "has_***REMOVED***word": ***REMOVED*** is not None,
                },
            )

            return detail

    @handle_service_errors(
        error_message="Failed to approve hosts",
        error_code="APPROVE_HOST_FAILED",
    )
    async def approve_hosts(
        self, request: AdminApprHostApproveRequest, appr_by: int, locale: str = "zh_CN", http_request=None
    ) -> AdminApprHostApproveResponse:
        """Approve hosts (admin backend)

        Business logic:
        - diff_type is None: Manual enable, only update local state (call external API when state is 5/6)
        - diff_type == 1 or 2: Hardware change approval, need to process hardware records and call external API

        Args:
            request: Approve enable request parameters (diff_type, host_ids)
            appr_by: Approver ID (obtained from token)
            locale: Language preference
            http_request: FastAPI Request object

        Returns:
            AdminApprHostApproveResponse: Contains processing results and statistics

        Raises:
            BusinessError: When parameter validation fails or business logic error occurs
        """
        logger.info(
            "Start approving hosts",
            extra={
                "diff_type": request.diff_type,
                "host_ids": request.host_ids,
                "appr_by": appr_by,
            },
        )

        # 1. Validate parameters and resolve host_ids
        host_ids_to_process = await self._validate_and_resolve_host_ids(request, locale)

        if not host_ids_to_process:
            return AdminApprHostApproveResponse(
                success_count=0,
                failed_count=0,
                results=[],
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            try:
                success_count = 0
                failed_count = 0
                results: List[Dict[str, Any]] = []
                now = datetime.now(timezone.utc)

                # 2. Batch query all host information (avoid N+1 queries)
                host_stmt = select(HostRec).where(
                    and_(
                        HostRec.id.in_(host_ids_to_process),
                        HostRec.del_flag == 0,
                    )
                )
                host_result = await session.execute(host_stmt)
                host_recs_map = {host.id: host for host in host_result.scalars().all()}

                # 3. Process based on diff_type
                host_updates: Dict[int, Dict[str, Any]] = {}
                hw_updates: Dict[int, Dict[str, Any]] = {}

                if request.diff_type is None:
                    # Manual enable: Process each host
                    # Query hosts that need hardware records (state 5/6)
                    host_ids_need_hw = [
                        host_id
                        for host_id in host_ids_to_process
                        if host_recs_map.get(host_id) and host_recs_map[host_id].host_state in (5, 6)
                    ]

                    # Batch query hardware records (only latest one)
                    hw_recs_by_host = {}
                    if host_ids_need_hw:
                        hw_recs_by_host = await self._query_hardware_records(
                            session, host_ids_need_hw, sync_state=None, need_latest_only=True
                        )

                    # Process each host
                    for host_id in host_ids_to_process:
                        try:
                            # Validate host exists
                            host_rec = self._validate_host_exists(host_id, host_recs_map, locale)
                            if not host_rec:
                                error_message = t("error.host.not_found", locale=locale, host_id=host_id)
                                results.append(
                                    {
                                        "host_id": host_id,
                                        "success": False,
                                        "message": error_message,
                                    }
                                )
                                failed_count += 1
                                continue

                            # Process manual enable
                            hw_recs = hw_recs_by_host.get(host_id, [])
                            process_result = await self._process_manual_enable(
                                host_id, host_rec, hw_recs, appr_by, http_request, locale
                            )

                            host_updates[host_id] = process_result["host_update"]
                            results.append(
                                {
                                    "host_id": process_result["host_id"],
                                    "success": process_result["success"],
                                    "message": process_result["message"],
                                }
                            )
                            success_count += 1

                        except Exception as e:
                            logger.error(
                                "Exception occurred while processing host",
                                extra={
                                    "host_id": host_id,
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                },
                                exc_info=True,
                            )
                            results.append(
                                {
                                    "host_id": host_id,
                                    "success": False,
                                    "message": f"Processing failed: {str(e)}",
                                }
                            )
                            failed_count += 1
                            continue

                    # Bulk update host_rec table
                    await self._bulk_update_host_records(session, host_updates)

                    # Commit transaction
                    await session.commit()

                    return AdminApprHostApproveResponse(
                        success_count=success_count,
                        failed_count=failed_count,
                        results=results,
                    )

                else:
                    # Hardware change approval (diff_type == 1 or 2)
                    # Batch query hardware records
                    hw_recs_by_host = await self._query_hardware_records(
                        session, host_ids_to_process, sync_state=SYNC_STATE_WAIT, need_latest_only=False
                    )

                    logger.debug(
                        "Batch query hardware records completed",
                        extra={
                            "host_ids_count": len(host_ids_to_process),
                            "found_hosts_count": len(hw_recs_by_host),
                        },
                    )

                    # Process each host
                    for host_id in host_ids_to_process:
                        try:
                            # Validate host exists
                            host_rec = self._validate_host_exists(host_id, host_recs_map, locale)
                            if not host_rec:
                                error_message = t("error.host.not_found", locale=locale, host_id=host_id)
                                results.append(
                                    {
                                        "host_id": host_id,
                                        "success": False,
                                        "message": error_message,
                                    }
                                )
                                failed_count += 1
                                continue

                            # Process hardware change approval
                            hw_recs = hw_recs_by_host.get(host_id, [])
                            process_result = await self._process_hardware_change_approval(
                                host_id, host_rec, hw_recs, appr_by, http_request, locale, session
                            )

                            host_updates[host_id] = process_result["host_update"]
                            hw_updates.update(process_result["hw_updates"])
                            results.append(
                                {
                                    "host_id": process_result["host_id"],
                                    "success": process_result["success"],
                                    "message": process_result["message"],
                                    "hw_id": process_result["hw_id"],
                                    "hardware_id": process_result["hardware_id"],
                                }
                            )
                            success_count += 1

                        except BusinessError:
                            # Business errors are raised directly
                            raise
                        except Exception as e:
                            logger.error(
                                "Exception occurred while processing host",
                                extra={
                                    "host_id": host_id,
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                },
                                exc_info=True,
                            )
                            results.append(
                                {
                                    "host_id": host_id,
                                    "success": False,
                                    "message": t(
                                        "error.host.process_failed",
                                        locale=locale,
                                        host_id=host_id,
                                        error=str(e),
                                        default=f"Processing failed: {str(e)}",
                                    ),
                                }
                            )
                            failed_count += 1
                            continue

                    # Bulk update hardware records
                    await self._bulk_update_hardware_records(session, hw_updates, now, appr_by)

                    # Bulk update host records
                    await self._bulk_update_host_records(session, host_updates)

                # Commit transaction
                await session.commit()

                logger.info(
                    "Approve hosts processing completed",
                    extra={
                        "diff_type": request.diff_type,
                        "total_count": len(host_ids_to_process),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "appr_by": appr_by,
                    },
                )

                # Email notification (only sent for hardware change approval)
                email_notification_errors: List[str] = []
                if request.diff_type in (1, 2):
                    email_notification_errors = await send_approval_email(session, results, appr_by, locale)

                # Build response
                response_data = AdminApprHostApproveResponse(
                    success_count=success_count,
                    failed_count=failed_count,
                    results=results,
                )

                # If there are email notification errors, add to response (does not affect success status)
                if email_notification_errors:
                    response_data.results.append(
                        {
                            "type": "email_notification",
                            "success": False,
                            "message": "; ".join(email_notification_errors),
                        }
                    )

                return response_data

            except Exception as e:
                # Rollback transaction
                await session.rollback()
                logger.error(
                    "Approve hosts transaction rolled back",
                    extra={
                        "diff_type": request.diff_type,
                        "host_ids": request.host_ids,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"Failed to approve hosts: {str(e)}",
                    message_key="error.host.approve_failed",
                    error_code="APPROVE_HOST_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "diff_type": request.diff_type,
                        "host_ids": request.host_ids,
                        "error": str(e),  # ✅ Add error field for translation formatting
                    },
                )

    @handle_service_errors(
        error_message="Failed to set maintain email",
        error_code="SET_MAINTAIN_EMAIL_FAILED",
    )
    async def set_maintain_email(
        self, request: AdminMaintainEmailRequest, operator_id: int
    ) -> AdminMaintainEmailResponse:
        """Set maintain notification email (admin backend)

        Business logic:
        1. Format email: Remove spaces, convert full-width comma to half-width comma
        2. Query sys_conf table, conf_key = "email"
        3. Insert if not exists, update conf_val if exists

        Args:
            request: Maintain notification email setting request parameters
            operator_id: Operator ID (obtained from token)

        Returns:
            AdminMaintainEmailResponse: Contains setting result

        Raises:
            BusinessError: When parameter validation fails or database operation fails
        """
        logger.info(
            "Start setting maintain notification email",
            extra={
                "email": request.email,
                "operator_id": operator_id,
            },
        )

        # 1. Format email: Remove spaces, convert full-width comma to half-width comma
        formatted_email = request.email.strip()
        # Remove all spaces
        formatted_email = "".join(formatted_email.split())
        # Convert full-width comma (，) to half-width comma (,)
        formatted_email = formatted_email.replace("，", ",")
        # Remove redundant commas (consecutive commas)
        while ",," in formatted_email:
            formatted_email = formatted_email.replace(",,", ",")
        # Remove leading and trailing commas
        formatted_email = formatted_email.strip(",")

        if not formatted_email:
            raise BusinessError(
                message="Email address cannot be empty",
                message_key="error.email.empty",
                error_code="EMAIL_EMPTY",
                code=ServiceErrorCodes.VALIDATION_ERROR,
                http_status_code=400,
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            try:
                # 2. Query sys_conf table, conf_key = "email"
                stmt = select(SysConf).where(
                    and_(
                        SysConf.conf_key == "email",
                        SysConf.del_flag == 0,
                    )
                )
                result = await session.execute(stmt)
                sys_conf_rows = result.scalars().all()
                sys_conf = sys_conf_rows[0] if sys_conf_rows else None
                duplicate_ids = [conf.id for conf in sys_conf_rows[1:]]
                if duplicate_ids:
                    logger.warning(
                        (
                            "Duplicate maintain notification email configurations detected, "
                            "automatically cleaning up redundant records"
                        ),
                        extra={"duplicate_ids": duplicate_ids},
                    )
                    cleanup_stmt = (
                        update(SysConf).where(SysConf.id.in_(duplicate_ids)).values(del_flag=1, updated_by=operator_id)
                    )
                    await session.execute(cleanup_stmt)

                if sys_conf:
                    # 3. Update if exists
                    update_stmt = (
                        update(SysConf)
                        .where(SysConf.id == sys_conf.id)
                        .values(
                            conf_val=formatted_email,
                            updated_by=operator_id,
                        )
                    )
                    await session.execute(update_stmt)
                    logger.info(
                        "Maintain notification email updated",
                        extra={
                            "conf_id": sys_conf.id,
                            "old_email": sys_conf.conf_val,
                            "new_email": formatted_email,
                            "operator_id": operator_id,
                        },
                    )
                else:
                    # 4. Insert if not exists
                    new_sys_conf = SysConf(
                        conf_key="email",
                        conf_val=formatted_email,
                        conf_name="Maintain Notification Email",
                        state_flag=0,  # Enabled state
                        created_by=operator_id,
                        updated_by=operator_id,
                    )
                    session.add(new_sys_conf)
                    logger.info(
                        "Maintain notification email created",
                        extra={
                            "conf_key": "email",
                            "conf_val": formatted_email,
                            "operator_id": operator_id,
                        },
                    )

                # Commit transaction
                await session.commit()

                logger.info(
                    "Set maintain notification email completed",
                    extra={
                        "conf_key": "email",
                        "conf_val": formatted_email,
                        "operator_id": operator_id,
                        "operation": "updated" if sys_conf else "created",
                    },
                )

                return AdminMaintainEmailResponse(
                    conf_key="email",
                    conf_val=formatted_email,
                )

            except Exception as e:
                # Rollback transaction
                await session.rollback()
                logger.error(
                    "Set maintain notification email transaction rolled back",
                    extra={
                        "email": formatted_email,
                        "operator_id": operator_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"Failed to set maintain notification email: {str(e)}",
                    message_key="error.email.set_failed",
                    error_code="SET_MAINTAIN_EMAIL_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "email": formatted_email,
                        "error": str(e),
                    },
                )

    @handle_service_errors(
        error_message="Failed to get maintain email",
        error_code="GET_MAINTAIN_EMAIL_FAILED",
    )
    async def get_maintain_email(self) -> AdminMaintainEmailResponse:
        """Get maintain notification email (admin backend)

        Business logic:
        1. Query sys_conf table, conf_key = "email", state_flag = 0, del_flag = 0
        2. Return conf_val value

        Returns:
            AdminMaintainEmailResponse: Contains email configuration information

        Raises:
            BusinessError: When database operation fails
        """
        log_operation_start(
            "Get maintain notification email",
            logger_instance=logger,
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            try:
                # Query sys_conf table
                stmt = (
                    select(SysConf)
                    .where(
                        and_(
                            SysConf.conf_key == "email",
                            SysConf.state_flag == 0,
                            SysConf.del_flag == 0,
                        )
                    )
                    .limit(1)
                )

                result = await session.execute(stmt)
                sys_conf = result.scalar_one_or_none()

                if not sys_conf:
                    # If not exists, return empty string
                    logger.info("Maintain notification email configuration does not exist, returning empty value")
                    return AdminMaintainEmailResponse(
                        conf_key="email",
                        conf_val="",
                    )

                # Return configuration value
                conf_val = sys_conf.conf_val or ""
                logger.info(
                    "Get maintain notification email succeeded",
                    extra={
                        "conf_key": sys_conf.conf_key,
                        "conf_val_length": len(conf_val),
                    },
                )

                return AdminMaintainEmailResponse(
                    conf_key="email",
                    conf_val=conf_val,
                )

            except Exception as e:
                logger.error(
                    "Failed to get maintain notification email",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"Failed to get maintain notification email: {str(e)}",
                    message_key="error.email.get_failed",
                    error_code="GET_MAINTAIN_EMAIL_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                )
