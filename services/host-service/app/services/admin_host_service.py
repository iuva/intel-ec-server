"""Admin backend host management service

Provides core business logic for host querying, searching, and other operations used by the admin backend.
"""

from datetime import datetime, timezone
import os
import sys
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select, update

# Use try-except to handle path imports
try:
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_OFFLINE
    from app.models.host_exec_log import HostExecLog
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.schemas.host import (
        AdminHostExecLogInfo,
        AdminHostExecLogListRequest,
        AdminHostInfo,
        AdminHostListRequest,
    )
    from app.schemas.websocket_message import MessageType
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.services.browser_vnc_service import _realvnc_encrypt_password
    from app.services.external_api_client import call_external_api
    from app.utils.logging_helpers import log_operation_completed, log_operation_start
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt, aes_encrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_OFFLINE
    from app.models.host_exec_log import HostExecLog
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.schemas.host import (
        AdminHostExecLogInfo,
        AdminHostExecLogListRequest,
        AdminHostInfo,
        AdminHostListRequest,
    )
    from app.schemas.websocket_message import MessageType
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.services.browser_vnc_service import _realvnc_encrypt_password
    from app.services.external_api_client import call_external_api
    from app.utils.logging_helpers import log_operation_completed, log_operation_start
    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt, aes_encrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse

logger = get_logger(__name__)


class AdminHostService:
    """Admin backend host management service class

    Responsible for host querying, searching, and other operations in the admin backend.

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
        error_message="Failed to query host list",
        error_code="QUERY_HOST_LIST_FAILED",
    )
    async def list_hosts(
        self,
        request: AdminHostListRequest,
    ) -> Tuple[List[AdminHostInfo], PaginationResponse]:
        """Query available host list (paginated, searchable)

        Business logic:
        1. Query host_rec table with conditions: host_state >= 0 and host_state <= 4, appr_state = 1, del_flag = 0
        2. Join host_exec_log table to get the latest record for each host_id (ordered by created_time descending)
        3. Support filtering by use_by (user_name)
        4. Order by host_rec.created_time descending

        Args:
            request: Query request parameters

        Returns:
            Tuple[List[AdminHostInfo], PaginationResponse]: Host list and pagination information

        Raises:
            BusinessError: When query fails
        """
        log_operation_start(
            "Query available host list",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "username": request.username,
                "host_state": request.host_state,
                "mg_id": request.mg_id,
                "use_by": request.use_by,
            },
            logger_instance=logger,
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # Build subquery: Get the latest host_exec_log record for each host_id
            # Method: First get the max created_time for each host_id, if same then take the max id
            max_time_subquery = (
                select(
                    HostExecLog.host_id,
                    func.max(HostExecLog.created_time).label("max_created_time"),
                )
                .where(HostExecLog.del_flag == 0)
                .group_by(HostExecLog.host_id)
                .subquery()
            )

            # Get the max id for each host_id (when created_time is the same)
            # ✅ Fix: Use correct SQLAlchemy 2.0 join syntax
            # Use select_from() with join() on table objects
            max_id_subquery = (
                select(
                    HostExecLog.host_id,
                    func.max(HostExecLog.id).label("max_id"),
                )
                .select_from(
                    HostExecLog.__table__.join(
                        max_time_subquery,
                        and_(
                            HostExecLog.host_id == max_time_subquery.c.host_id,
                            HostExecLog.created_time == max_time_subquery.c.max_created_time,
                            HostExecLog.del_flag == 0,
                        ),
                    )
                )
                .group_by(HostExecLog.host_id)
                .subquery()
            )

            # Get complete record of latest execution log (use id to ensure uniqueness)
            # ✅ Fix: Use correct SQLAlchemy 2.0 join syntax
            latest_log_subquery = (
                select(HostExecLog.host_id, HostExecLog.user_name)
                .select_from(
                    HostExecLog.__table__.join(
                        max_id_subquery,
                        HostExecLog.id == max_id_subquery.c.max_id,
                    )
                )
                .subquery()
            )

            # Main query: JOIN host_rec and latest host_exec_log
            # Base conditions: host_state >= 0 and host_state <= 4, appr_state = 1, del_flag = 0
            base_conditions = [
                HostRec.host_state >= 0,
                HostRec.host_state <= 4,
                HostRec.appr_state == 1,
                HostRec.del_flag == 0,
            ]

            # Add search conditions (filter empty strings)
            if request.mac and request.mac.strip():
                base_conditions.append(HostRec.mac_addr.like(f"%{request.mac.strip()}%"))

            if request.username and request.username.strip():
                base_conditions.append(HostRec.host_acct.like(f"%{request.username.strip()}%"))

            # If host_state filter condition is specified, add exact match
            # Note: Base conditions are fixed as host_state >= 0 and host_state <= 4
            # If host_state parameter is provided, further match that state exactly
            if request.host_state is not None:
                # Validate host_state range (0-4)
                if request.host_state < 0 or request.host_state > 4:
                    raise BusinessError(
                        message=f"host_state parameter value must be in range 0-4, current value: {request.host_state}",
                        message_key="error.host.invalid_host_state",
                        error_code="INVALID_HOST_STATE",
                        code=ServiceErrorCodes.HOST_INVALID_REQUEST,
                        http_status_code=400,
                        details={"host_state": request.host_state},
                    )
                base_conditions.append(HostRec.host_state == request.host_state)

            if request.mg_id and request.mg_id.strip():
                base_conditions.append(HostRec.mg_id.like(f"%{request.mg_id.strip()}%"))

            # If use_by filter condition is specified, need to rebuild subquery and add filter
            if request.use_by and request.use_by.strip():
                # Re-get max id, but this time filter by user_name
                # ✅ Fix: Use correct SQLAlchemy 2.0 join syntax
                max_id_with_filter_subquery = (
                    select(
                        HostExecLog.host_id,
                        func.max(HostExecLog.id).label("max_id"),
                    )
                    .select_from(
                        HostExecLog.__table__.join(
                            max_time_subquery,
                            and_(
                                HostExecLog.host_id == max_time_subquery.c.host_id,
                                HostExecLog.created_time == max_time_subquery.c.max_created_time,
                                HostExecLog.del_flag == 0,
                                HostExecLog.user_name.like(f"%{request.use_by.strip()}%"),
                            ),
                        )
                    )
                    .group_by(HostExecLog.host_id)
                    .subquery()
                )

                # Get filtered latest execution log
                # ✅ Fix: Use correct SQLAlchemy 2.0 join syntax
                latest_log_subquery = (
                    select(HostExecLog.host_id, HostExecLog.user_name)
                    .select_from(
                        HostExecLog.__table__.join(
                            max_id_with_filter_subquery,
                            HostExecLog.id == max_id_with_filter_subquery.c.max_id,
                        )
                    )
                    .subquery()
                )

            # Build main query: LEFT JOIN to get latest execution log
            # If use_by is specified, need to filter out records where user_name is None
            query_conditions = base_conditions.copy()
            if request.use_by and request.use_by.strip():
                # Since LEFT JOIN is used, need to filter out records where user_name is None
                query_conditions.append(latest_log_subquery.c.user_name.is_not(None))

            base_query = (
                select(
                    HostRec.id.label("host_id"),
                    HostRec.host_acct.label("username"),
                    HostRec.mg_id,
                    HostRec.mac_addr.label("mac"),
                    HostRec.host_state,
                    HostRec.appr_state,
                    latest_log_subquery.c.user_name.label("use_by"),
                )
                .outerjoin(
                    latest_log_subquery,
                    HostRec.id == latest_log_subquery.c.host_id,
                )
                .where(and_(*query_conditions))
            )

            # 1. Query total count
            count_stmt = select(func.count()).select_from(base_query.subquery())
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 2. Paginated query: Order by created_time descending
            pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

            # Add sorting and pagination
            stmt = (
                base_query.order_by(HostRec.created_time.desc())
                .offset(pagination_params.offset)
                .limit(pagination_params.limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            # 3. Build response data
            host_info_list: List[AdminHostInfo] = []
            for row in rows:
                host_info = AdminHostInfo(
                    host_id=str(row.host_id),  # ✅ Convert to string to avoid precision loss
                    username=row.username,
                    mg_id=row.mg_id,
                    mac=row.mac,
                    use_by=row.use_by,
                    host_state=row.host_state,
                    appr_state=row.appr_state,
                )
                host_info_list.append(host_info)

            # 4. Build pagination response
            pagination_response = PaginationResponse(
                page=request.page,
                page_size=request.page_size,
                total=total,
            )

            logger.info(
                "Query available host list completed",
                extra={
                    "total": total,
                    "returned_count": len(host_info_list),
                    "page": request.page,
                    "page_size": request.page_size,
                },
            )

            return host_info_list, pagination_response

    @handle_service_errors(
        error_message="Failed to delete host",
        error_code="DELETE_HOST_FAILED",
    )
    async def delete_host(
        self, host_id: int, request=None, user_id: Optional[int] = None, locale: str = "zh_CN"
    ) -> str:
        """Delete host (logical delete)

        Business logic:
        1. Query host record to check existence and get hardware_id
        2. If hardware_id exists, call external API first to delete hardware data
        3. If external API succeeds (or no hardware_id), execute local logical delete
        4. Add host_id to Redis blacklist for token invalidation

        Transaction boundary:
        - External API call is outside the database transaction
        - Local delete (host_rec + host_hw_rec) is within a single transaction
        - If external API fails, local data remains unchanged (no rollback needed)

        Args:
            host_id: Host ID (host_rec.id)
            request: FastAPI Request object (used to get user_id from request headers)
            user_id: ID of currently logged-in admin backend user (optional, if provided will be used preferentially)
            locale: Language preference for error message internationalization

        Returns:
            str: Deleted host ID (string format to avoid precision loss)

        Raises:
            BusinessError: When host does not exist, external API call fails, or deletion fails
        """
        logger.info(
            "Start deleting host",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Check if host exists and is not deleted, and get host_rec object (for getting hardware_id)
            host_stmt = select(HostRec).where(
                and_(
                    HostRec.id == host_id,
                    HostRec.del_flag == 0,  # Only query non-deleted records
                )
            )
            host_result = await session.execute(host_stmt)
            host_rec = host_result.scalar_one_or_none()

            if not host_rec:
                raise BusinessError(
                    message=f"Host does not exist or has been deleted (ID: {host_id})",
                    message_key="error.host.not_found",
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=404,
                    details={"host_id": host_id},
                )

            hardware_id = host_rec.hardware_id

            logger.info(
                "Host record found",
                extra={
                    "host_id": host_id,
                    "hardware_id": hardware_id,
                },
            )

        # 2. Call external API first (if hardware_id exists)
        # This is outside the database transaction to avoid holding transaction during external call
        if hardware_id:
            try:
                external_api_path = f"/api/v1/hardware/{hardware_id}"

                logger.info(
                    "Calling external API to delete hardware",
                    extra={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "external_api_path": external_api_path,
                        "user_id": user_id,
                    },
                )

                response = await call_external_api(
                    method="DELETE",
                    url_path=external_api_path,
                    request=request,
                    user_id=user_id,
                    locale=locale,
                )

                # Determine if request succeeded
                response_headers = response.get("headers", {})
                response_body = response.get("body", {})
                status_header = response_headers.get(":status") or response_headers.get("status")
                status_code = response.get("status_code")
                body_code = response_body.get("code") if isinstance(response_body, dict) else None

                is_success = (
                    (status_header and str(status_header) == "200")
                    or (status_code and status_code == 200)
                    or (body_code and body_code == 200)
                )

                if not is_success:
                    error_msg = (
                        response_body.get("message", "Unknown error")
                        if isinstance(response_body, dict)
                        else str(response_body)
                    )
                    raise BusinessError(
                        message=f"External API deletion failed: {error_msg}",
                        message_key="error.external_api.delete_failed",
                        error_code="EXTERNAL_API_DELETE_FAILED",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=500,
                        details={
                            "host_id": host_id,
                            "hardware_id": hardware_id,
                            "status_code": status_code,
                            "response_body": response_body,
                        },
                    )

                logger.info(
                    "External API deletion succeeded",
                    extra={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "status_header": status_header,
                        "status_code": status_code,
                    },
                )

            except BusinessError:
                raise
            except Exception as e:
                logger.error(
                    "External API call failed",
                    extra={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"Failed to delete hardware from external API (ID: {host_id})",
                    message_key="error.host.delete_external_api_failed",
                    error_code="HOST_DELETE_EXTERNAL_API_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "host_id": host_id,
                        "hardware_id": hardware_id,
                        "external_api_error": str(e),
                    },
                )
        else:
            logger.info(
                "No hardware_id, skipping external API call",
                extra={
                    "host_id": host_id,
                },
            )

        # 3. Execute local logical delete within a transaction
        async with session_factory() as session:
            # 3.1 Delete host_rec
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,
                    )
                )
                .values(del_flag=1)
            )

            result = await session.execute(update_stmt)
            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "Logical delete failed, record may have been deleted",
                    extra={"host_id": host_id},
                )
                raise BusinessError(
                    message=f"Host deletion failed, record may have been deleted (ID: {host_id})",
                    message_key="error.host.delete_failed",
                    error_code="HOST_DELETE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            # 3.2 Delete host_hw_rec (cascade logical delete)
            hw_update_stmt = (
                update(HostHwRec)
                .where(
                    and_(
                        HostHwRec.host_id == host_id,
                        HostHwRec.del_flag == 0,
                    )
                )
                .values(del_flag=1)
            )
            hw_result = await session.execute(hw_update_stmt)
            hw_updated_count = hw_result.rowcount

            # 3.3 Commit transaction
            await session.commit()

            logger.info(
                "Local logical delete completed",
                extra={
                    "host_id": host_id,
                    "host_rec_updated": updated_count,
                    "host_hw_rec_updated": hw_updated_count,
                },
            )

        # 4. Add host_id to Redis blacklist (outside transaction, non-critical)
        try:
            deleted_host_key = f"deleted:host:{host_id}"
            expire_seconds = 24 * 60 * 60  # 24 hours
            await redis_manager.set(deleted_host_key, True, expire=expire_seconds)

            logger.info(
                "Deleted host ID added to Redis blacklist",
                extra={
                    "host_id": host_id,
                    "redis_key": deleted_host_key,
                    "expire_seconds": expire_seconds,
                },
            )
        except Exception as redis_error:
            logger.warning(
                "Failed to add host ID to Redis blacklist",
                extra={
                    "host_id": host_id,
                    "error": str(redis_error),
                    "error_type": type(redis_error).__name__,
                    "hint": (
                        "When Redis is unavailable, deleted host tokens may still be usable until token expires"
                    ),
                },
            )

        logger.info(
            "Host deletion succeeded",
            extra={
                "host_id": host_id,
                "hardware_id": hardware_id,
            },
        )

        return str(host_id)

    @handle_service_errors(
        error_message="Failed to disable host",
        error_code="DISABLE_HOST_FAILED",
    )
    async def disable_host(self, host_id: int) -> dict:
        """Disable host

        Only hosts in FREE state (host_state=0) can be disabled.
        Update host_rec table's appr_state field to 0 (disabled) based on host ID,
        and set host_state to 7 (manually disabled).

        Args:
            host_id: Host ID (host_rec.id)

        Returns:
            dict: Contains updated host ID, approval state, and host state

        Raises:
            BusinessError: When host does not exist, host is not in FREE state, or update fails
        """
        logger.info(
            "Start disabling host",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Check if host exists and is not deleted (using utility function)
            host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. Check if current state is already disabled
            if host_rec.appr_state == 0 and host_rec.host_state == 7:
                logger.info(
                    "Host is already disabled, no update needed",
                    extra={
                        "host_id": host_id,
                        "current_appr_state": host_rec.appr_state,
                        "current_host_state": host_rec.host_state,
                    },
                )
                return {
                    "id": str(host_id),  # ✅ Convert to string to avoid precision loss
                    "appr_state": 0,
                    "host_state": 7,
                }

            # 3. Check if host is in FREE state (host_state=0), only FREE state can be disabled
            if host_rec.host_state != HOST_STATE_FREE:
                logger.warning(
                    "Host state does not allow disable",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "required_host_state": HOST_STATE_FREE,
                    },
                )
                raise BusinessError(
                    message=(
                        f"Host state does not allow disable, current state: {host_rec.host_state}, "
                        f"required state: {HOST_STATE_FREE} (free)"
                    ),
                    message_key="error.host.disable_state_invalid",
                    error_code="HOST_DISABLE_STATE_INVALID",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "required_host_state": HOST_STATE_FREE,
                    },
                )

            # 4. Update approval state to disabled, and set host_state to 7 (manually disabled)
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
                        HostRec.host_state == HOST_STATE_FREE,  # Ensure state is still FREE (prevent concurrent modification)
                    )
                )
                .values(appr_state=0, host_state=7)
            )

            logger.info(
                "Execute disable operation",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": 0,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": 7,
                    "operation": "UPDATE appr_state = 0, host_state = 7",
                },
            )

            # Execute update
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "Host disable failed, record may have been deleted",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"Host disable failed, record may have been deleted (ID: {host_id})",
                    message_key="error.host.disable_failed",
                    error_code="HOST_DISABLE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "Host disable succeeded",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": 0,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": 7,
                    "updated_count": updated_count,
                },
            )

            return {
                "id": str(host_id),  # ✅ Convert to string to avoid precision loss
                "appr_state": 0,
                "host_state": 7,
                "message": "Host has been disabled",
            }

    @handle_service_errors(
        error_message="Failed to force offline host",
        error_code="FORCE_OFFLINE_HOST_FAILED",
    )
    async def force_offline_host(self, host_id: int, locale: str = "zh_CN") -> dict:
        """Force offline host

        Business logic:
        1. Check if host exists and is not deleted
        2. Check if host state is < 4 (business state), only business states can be taken offline
           Business states: 0=FREE, 1=LOCKED, 2=OCCUPIED, 3=EXECUTING
           Non-business states (>=4): 4=OFFLINE, 5=INACTIVE, 6=HW_CHANGE, 7=DISABLED, 8=UPDATING
        3. Update host_rec table's host_state field to 4 (offline state)
        4. Send WebSocket notification to the host

        Args:
            host_id: Host ID (host_rec.id)
            locale: Language preference for error message internationalization

        Returns:
            dict: Contains updated host ID and state

        Raises:
            BusinessError: When host does not exist, host state is not business state, or update fails
        """
        logger.info(
            "Start forcing host offline",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Check if host exists and is not deleted (using utility function)
            host_rec = await validate_host_exists(session, HostRec, host_id, locale=locale)

            # 2. Check if host state is < 4 (business state), only business states can be taken offline
            if host_rec.host_state >= HOST_STATE_OFFLINE:
                logger.warning(
                    "Host state does not allow force offline",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "allowed_states": "0-3 (FREE, LOCKED, OCCUPIED, EXECUTING)",
                    },
                )
                raise BusinessError(
                    message=(
                        f"Host state does not allow force offline, current state: {host_rec.host_state}, "
                        f"allowed states: 0-3 (FREE, LOCKED, OCCUPIED, EXECUTING)"
                    ),
                    message_key="error.host.force_offline_state_invalid",
                    error_code="HOST_FORCE_OFFLINE_STATE_INVALID",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "allowed_states": "0-3 (FREE, LOCKED, OCCUPIED, EXECUTING)",
                    },
                )

            # 3. Update host state to offline (host_state = 4)
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
                        HostRec.host_state < HOST_STATE_OFFLINE,  # Ensure state is still business state (prevent concurrent modification)
                    )
                )
                .values(host_state=HOST_STATE_OFFLINE)  # 4 = offline state
            )

            logger.info(
                "Execute force offline operation",
                extra={
                    "host_id": host_id,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": HOST_STATE_OFFLINE,
                    "operation": f"UPDATE host_state = {HOST_STATE_OFFLINE}",
                },
            )

            # Execute update
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "Host force offline failed, record may have been deleted or state changed",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"Host force offline failed, record may have been deleted or state changed (ID: {host_id})",
                    message_key="error.host.force_offline_failed",
                    error_code="HOST_FORCE_OFFLINE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "Host force offline succeeded",
                extra={
                    "host_id": host_id,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": HOST_STATE_OFFLINE,
                    "updated_count": updated_count,
                },
            )

            # 4. Send WebSocket notification to the host
            try:
                ws_manager = get_agent_websocket_manager()
                host_id_str = str(host_id)

                # Build offline notification message
                offline_notification = {
                    "type": MessageType.HOST_OFFLINE_NOTIFICATION,
                    "host_id": host_id_str,
                    "message": "Host has been force offline by admin",
                    "reason": "admin_force_offline",
                }

                # Check if Agent is connected and send notification
                if ws_manager.is_connected(host_id_str):
                    success = await ws_manager.send_to_host(host_id_str, offline_notification)
                    if success:
                        logger.info(
                            "Force offline notification sent to Agent",
                            extra={
                                "host_id": host_id_str,
                                "message_type": MessageType.HOST_OFFLINE_NOTIFICATION,
                            },
                        )
                    else:
                        logger.warning(
                            "Failed to send force offline notification to Agent",
                            extra={
                                "host_id": host_id_str,
                                "message_type": MessageType.HOST_OFFLINE_NOTIFICATION,
                            },
                        )
                else:
                    logger.info(
                        "Agent not connected, skip sending force offline notification",
                        extra={
                            "host_id": host_id_str,
                        },
                    )
            except Exception as e:
                # Notification send failure does not affect main flow, only log warning
                logger.error(
                    "Error sending force offline notification",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                    },
                )

            return {
                "id": str(host_id),  # ✅ Convert to string to avoid precision loss
                "host_state": HOST_STATE_OFFLINE,
            }

    @handle_service_errors(
        error_message="Failed to query host detail",
        error_code="GET_HOST_DETAIL_FAILED",
    )
    async def get_host_detail(self, host_id: int) -> dict:
        """Query host detail (main information)

        Business logic:
        1. Query basic information from host_rec table
        2. Join host_hw_rec table, get list data with sync_state=2, ordered by updated_time descending
        3. Return host detail (including hardware information list)
        4. Password field needs decryption (AES encrypted)

        Args:
            host_id: Host ID (host_rec.id)

        Returns:
            dict: Contains host detail information, including hw_list field (hardware information list)

        Raises:
            BusinessError: When host does not exist
        """
        logger.info(
            "Start querying host detail",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Verify if host exists and is not deleted (using utility function)
            host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. Query host_hw_rec table for list data with sync_state=2, ordered by updated_time descending
            hw_stmt = (
                select(HostHwRec)
                .where(
                    and_(
                        HostHwRec.host_id == host_id,
                        HostHwRec.sync_state == 2,  # sync_state = 2 (approved)
                        HostHwRec.del_flag == 0,
                    )
                )
                .order_by(HostHwRec.updated_time.desc())
            )
            hw_result = await session.execute(hw_stmt)
            hw_recs = hw_result.scalars().all()

            # 3. Decrypt password (AES encrypted)
            decrypted_password = None
            if host_rec.host_pwd:
                try:
                    decrypted_password = aes_decrypt(host_rec.host_pwd)
                    if decrypted_password:
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
                    decrypted_password = None

            # 4. Build hardware information list
            hw_list = []
            for hw_rec in hw_recs:
                hw_list.append(
                    {
                        "hw_info": hw_rec.hw_info,
                        "appr_time": hw_rec.appr_time,
                    }
                )

            # 5. Build response data
            detail = {
                "mg_id": host_rec.mg_id,
                "mac": host_rec.mac_addr,
                "ip": host_rec.host_ip,
                "username": host_rec.host_acct,
                "password": decrypted_password,
                "port": host_rec.host_port,
                "hw_list": hw_list,
            }

            logger.info(
                "Query host detail completed",
                extra={
                    "host_id": host_id,
                    "has_hw_rec": host_rec is not None,
                    "has_password": decrypted_password is not None,
                    "hw_list_count": len(hw_list),
                },
            )

            return detail

    @handle_service_errors(
        error_message="Failed to get host VNC credentials",
        error_code="GET_HOST_VNC_CREDENTIALS_FAILED",
    )
    async def get_host_vnc_credentials(self, host_id: int) -> dict:
        """Get host account and VNC password by host_id.

        Business logic:
        1. Verify host exists and is not deleted
        2. Read host_acct and host_pwd from host_rec
        3. Decrypt host_pwd with AES
        4. Return decrypted password (same semantics as `/{host_id}/detail` password field)
        5. Return host_acct and vnc_password

        Args:
            host_id: Host ID (host_rec.id)

        Returns:
            dict: {"host_id": str, "ip": str|None, "host_acct": str|None, "vnc_password": str|None}

        Raises:
            BusinessError: When host does not exist
        """
        logger.info(
            "Start getting host VNC credentials",
            extra={"host_id": host_id},
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            vnc_password = None
            if host_rec.host_pwd:
                try:
                    decrypted_password = aes_decrypt(host_rec.host_pwd)
                    if decrypted_password is not None:
                        # For admin usage, return decrypted host password directly.
                        # This matches the "detail" endpoint behavior.
                        vnc_password = decrypted_password
                        logger.debug(
                            "VNC password decrypt succeeded (AES decrypt -> plaintext)",
                            extra={"host_id": host_id},
                        )
                except BusinessError:
                    raise
                except Exception as e:
                    logger.warning(
                        "VNC password decrypt failed (AES decrypt)",
                        extra={
                            "host_id": host_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

            result = {
                "host_id": str(host_id),
                "ip": host_rec.host_ip,
                "host_acct": host_rec.host_acct,
                "vnc_password": vnc_password,
            }
            logger.info(
                "Get host VNC credentials completed",
                extra={
                    "host_id": host_id,
                    "has_host_acct": bool(host_rec.host_acct),
                    "has_vnc_password": vnc_password is not None,
                },
            )
            return result

    @handle_service_errors(
        error_message="Failed to update host password",
        error_code="UPDATE_HOST_PASSWORD_FAILED",
    )
    async def update_host_password(self, host_id: int, password: str) -> dict:
        """Update host password

        Business logic:
        1. Check if host exists and is not deleted
        2. Encrypt password with AES
        3. Update host_rec table's host_pwd field

        Args:
            host_id: Host ID (host_rec.id)
            password: Plaintext password (will be AES encrypted)

        Returns:
            dict: Contains updated host ID and operation result message

        Raises:
            BusinessError: When host does not exist or update fails
        """
        logger.info(
            "Start updating host password",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Check if host exists and is not deleted (using utility function)
            await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. Encrypt password with AES
            try:
                encrypted_password = aes_encrypt(password)
                logger.debug(
                    "Password encryption succeeded",
                    extra={
                        "host_id": host_id,
                    },
                )
            except Exception as e:
                logger.error(
                    "Password encryption failed",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"Password encryption failed (ID: {host_id})",
                    message_key="error.host.password_encrypt_failed",
                    error_code="PASSWORD_ENCRYPT_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={"host_id": host_id},
                )

            # 3. Update host password
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
                    )
                )
                .values(host_pwd=encrypted_password)
            )

            logger.info(
                "Execute password update operation",
                extra={
                    "host_id": host_id,
                    "operation": "UPDATE host_pwd",
                },
            )

            # Execute update
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "Host password update failed, record may have been deleted",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"Host password update failed, record may have been deleted (ID: {host_id})",
                    message_key="error.host.password_update_failed",
                    error_code="HOST_PASSWORD_UPDATE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "Host password update succeeded",
                extra={
                    "host_id": host_id,
                    "updated_count": updated_count,
                },
            )

            return {
                "id": str(host_id),  # ✅ Convert to string to avoid precision loss
            }

    @handle_service_errors(
        error_message="Failed to query host execution logs",
        error_code="GET_HOST_EXEC_LOG_FAILED",
    )
    async def list_host_exec_logs(
        self,
        request: AdminHostExecLogListRequest,
    ) -> Tuple[List[AdminHostExecLogInfo], PaginationResponse]:
        """Query host execution log list (paginated)

        Business logic:
        1. Query host_exec_log table based on host_id
        2. Do not filter by del_flag (query all records, including logically deleted)
        3. Order by created_time descending
        4. Calculate exec_date (date part of begin_time, format %Y-%m-%d)
        5. Calculate exec_time (end_time - begin_time, format %H:%M:%S, if end_time is empty, use current time)

        Args:
            request: Query request parameters (host_id, pagination parameters)

        Returns:
            Tuple[List[AdminHostExecLogInfo], PaginationResponse]: Execution log list and pagination information

        Raises:
            BusinessError: When query fails
        """
        logger.info(
            "Start querying host execution log list",
            extra={
                "host_id": request.host_id,
                "page": request.page,
                "page_size": request.page_size,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # Build query conditions
            base_conditions = [
                HostExecLog.host_id == request.host_id,
            ]

            # 1. Query total count
            count_stmt = select(func.count(HostExecLog.id)).where(and_(*base_conditions))
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 2. Paginated query: Order by created_time descending
            pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

            stmt = (
                select(HostExecLog)
                .where(and_(*base_conditions))
                .order_by(HostExecLog.created_time.desc())
                .offset(pagination_params.offset)
                .limit(pagination_params.limit)
            )

            result = await session.execute(stmt)
            exec_logs = result.scalars().all()

            # 3. Build response data
            log_info_list: List[AdminHostExecLogInfo] = []
            current_time = datetime.now(timezone.utc)

            for log in exec_logs:
                # Calculate exec_date (date part of begin_time)
                exec_date: Optional[str] = None
                if log.begin_time:
                    try:
                        exec_date = log.begin_time.strftime("%Y-%m-%d")
                    except Exception as e:
                        logger.warning(
                            "Failed to format execution date",
                            extra={
                                "log_id": log.id,
                                "begin_time": str(log.begin_time),
                                "error": str(e),
                            },
                        )
                        exec_date = None

                # Calculate exec_time (end_time - begin_time, format %H:%M:%S)
                exec_time: Optional[str] = None
                if log.begin_time:
                    try:
                        # Ensure begin_time is timezone-aware
                        begin_time = log.begin_time
                        if begin_time.tzinfo is None:
                            # If naive datetime, assume UTC
                            begin_time = begin_time.replace(tzinfo=timezone.utc)

                        # If end_time is empty, use current time
                        if log.end_time:
                            end_time = log.end_time
                            # Ensure end_time is timezone-aware
                            if end_time.tzinfo is None:
                                end_time = end_time.replace(tzinfo=timezone.utc)
                        else:
                            end_time = current_time

                        # Calculate time difference
                        time_diff = end_time - begin_time
                        # Convert to seconds (ensure non-negative)
                        total_seconds = max(0, int(time_diff.total_seconds()))
                        # Calculate hours, minutes, seconds
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        # Format as %H:%M:%S
                        exec_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    except Exception as e:
                        logger.warning(
                            "Failed to calculate execution duration",
                            extra={
                                "log_id": log.id,
                                "begin_time": str(log.begin_time),
                                "end_time": str(log.end_time) if log.end_time else None,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        exec_time = None

                log_info = AdminHostExecLogInfo(
                    log_id=str(log.id),
                    exec_date=exec_date,
                    exec_time=exec_time,
                    tc_id=log.tc_id,
                    use_by=log.user_name,
                    case_state=log.case_state,
                    result_msg=log.result_msg,
                    log_url=log.log_url,
                )
                log_info_list.append(log_info)

            # 4. Build pagination response
            pagination_response = PaginationResponse(
                page=request.page,
                page_size=request.page_size,
                total=total,
            )

            log_operation_completed(
                "Query host execution log list",
                extra={
                    "host_id": request.host_id,
                    "total": total,
                    "returned_count": len(log_info_list),
                    "page": request.page,
                    "page_size": request.page_size,
                },
                logger_instance=logger,
            )

            return log_info_list, pagination_response
