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

        Logically delete host_rec table data based on host ID. After deletion,
        need to synchronously notify external API.
        If notification fails, rollback the delete operation.

        Args:
            host_id: Host ID (host_rec.id)
            request: FastAPI Request object (used to get user_id from request headers)
            user_id: ID of currently logged-in admin backend user (optional, if provided will be used preferentially)
            locale: Language preference for error message internationalization

        Returns:
            str: Deleted host ID (string format to avoid precision loss)

        Raises:
            BusinessError: When host does not exist or deletion fails
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

            # 2. Execute logical delete (set del_flag = 1)
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
                    )
                )
                .values(del_flag=1)  # Set as deleted
            )

            logger.info(
                "Execute logical delete operation",
                extra={
                    "host_id": host_id,
                    "operation": "UPDATE del_flag = 1",
                },
            )

            # Execute update
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "Logical delete failed, record may have been deleted",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"Host deletion failed, record may have been deleted (ID: {host_id})",
                    message_key="error.host.delete_failed",
                    error_code="HOST_DELETE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "Host logical delete completed",
                extra={
                    "host_id": host_id,
                    "updated_count": updated_count,
                },
            )

            # 3. After successful deletion, add host_id to Redis blacklist
            try:
                deleted_host_key = f"deleted:host:{host_id}"
                # Expiration time: 24 hours (consistent with token expiration time)
                expire_seconds = 24 * 60 * 60
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
                # Log warning when Redis operation fails, but don't affect delete operation
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

            # 4. Notify external API
            try:
                # Build notification path (adjust according to actual external API interface)
                external_api_path = f"/api/v1/hardware/{host_rec.hardware_id}"

                logger.info(
                    "Call external API to notify host deletion",
                    extra={
                        "host_id": host_id,
                        "hardware_id": host_rec.hardware_id,
                        "external_api_path": external_api_path,
                        "user_id": user_id,
                    },
                )

                # Call external API to notify host has been deleted
                response = await call_external_api(
                    method="DELETE",
                    url_path=external_api_path,
                    request=request,
                    user_id=user_id,
                    locale=locale,
                )

                # Determine if request succeeded: Check if response header :status or response body code is 200
                response_headers = response.get("headers", {})
                response_body = response.get("body", {})
                status_header = response_headers.get(":status") or response_headers.get("status")
                status_code = response.get("status_code")
                body_code = response_body.get("code") if isinstance(response_body, dict) else None

                # Determine success: response header :status or status_code or response body code equals 200
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
                    raise Exception(f"External API notification failed: {error_msg}")

                logger.info(
                    "External API notification succeeded",
                    extra={
                        "host_id": host_id,
                        "status_header": status_header,
                        "status_code": status_code,
                        "body_code": body_code,
                    },
                )

            except Exception as e:
                # 4. If external API notification fails, rollback delete operation
                logger.error(
                    "External API notification failed, starting rollback of delete operation",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

                # Rollback: Change del_flag back to 0
                rollback_stmt = (
                    update(HostRec).where(HostRec.id == host_id).values(del_flag=0)  # Restore to non-deleted state
                )

                rollback_result = await session.execute(rollback_stmt)
                await session.commit()

                rollback_count = rollback_result.rowcount

                logger.info(
                    "Delete operation rolled back",
                    extra={
                        "host_id": host_id,
                        "rollback_count": rollback_count,
                    },
                )

                # Raise business exception, return deletion failure
                raise BusinessError(
                    message=f"Host deletion failed: External API notification failed (ID: {host_id})",
                    message_key="error.host.delete_external_api_failed",
                    error_code="HOST_DELETE_EXTERNAL_API_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "host_id": host_id,
                        "external_api_error": str(e),
                        "rollback_success": rollback_count > 0,
                    },
                )

            # 5. Deletion succeeded
            logger.info(
                "Host deletion succeeded (including external API notification)",
                extra={
                    "host_id": host_id,
                },
            )

            return str(host_id)  # ✅ Convert to string to avoid precision loss

    @handle_service_errors(
        error_message="Failed to disable host",
        error_code="DISABLE_HOST_FAILED",
    )
    async def disable_host(self, host_id: int) -> dict:
        """Disable host

        Update host_rec table's appr_state field to 0 (disabled) based on host ID,
        and set host_state to 7 (manually disabled).

        Args:
            host_id: Host ID (host_rec.id)

        Returns:
            dict: Contains updated host ID, approval state, and host state

        Raises:
            BusinessError: When host does not exist or update fails
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

            # 3. Update approval state to disabled, and set host_state to 7 (manually disabled)
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
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
        2. Check if host state is 0 (free state), only free state can be taken offline
        3. Update host_rec table's host_state field to 4 (offline state)

        Args:
            host_id: Host ID (host_rec.id)
            locale: Language preference for error message internationalization

        Returns:
            dict: Contains updated host ID and state

        Raises:
            BusinessError: When host does not exist, host state is not free, or update fails
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

            # 2. Check if host state is 0 (free state), only free state can be taken offline
            if host_rec.host_state != HOST_STATE_FREE:
                logger.warning(
                    "Host state does not allow force offline",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "required_host_state": HOST_STATE_FREE,
                    },
                )
                raise BusinessError(
                    message=(
                        f"Host state does not allow force offline, current state: {host_rec.host_state}, "
                        f"required state: {HOST_STATE_FREE} (free)"
                    ),
                    message_key="error.host.force_offline_state_invalid",
                    error_code="HOST_FORCE_OFFLINE_STATE_INVALID",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "required_host_state": HOST_STATE_FREE,
                    },
                )

            # 3. Update host state to offline (host_state = 4)
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
                        HostRec.host_state
                        == HOST_STATE_FREE,  # Ensure state is still 0 (prevent concurrent modification)
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
                "***REMOVED***word": ***REMOVED***,
                "port": host_rec.host_port,
                "hw_list": hw_list,
            }

            logger.info(
                "Query host detail completed",
                extra={
                    "host_id": host_id,
                    "has_hw_rec": host_rec is not None,
                    "has_***REMOVED***word": ***REMOVED*** is not None,
                    "hw_list_count": len(hw_list),
                },
            )

            return detail

    @handle_service_errors(
        error_message="Failed to update host ***REMOVED***word",
        error_code="UPDATE_HOST_PASSWORD_FAILED",
    )
    async def update_host_***REMOVED***word(self, host_id: int, ***REMOVED***word: str) -> dict:
        """Update host ***REMOVED***word

        Business logic:
        1. Check if host exists and is not deleted
        2. Encrypt ***REMOVED***word with AES
        3. Update host_rec table's host_pwd field

        Args:
            host_id: Host ID (host_rec.id)
            ***REMOVED***word: Plaintext ***REMOVED***word (will be AES encrypted)

        Returns:
            dict: Contains updated host ID and operation result message

        Raises:
            BusinessError: When host does not exist or update fails
        """
        logger.info(
            "Start updating host ***REMOVED***word",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = self.session_factory
        async with session_factory() as session:
            # 1. Check if host exists and is not deleted (using utility function)
            await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. Encrypt ***REMOVED***word with AES
            try:
                encrypted_***REMOVED***word = aes_encrypt(***REMOVED***word)
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
                    message_key="error.host.***REMOVED***word_encrypt_failed",
                    error_code="PASSWORD_ENCRYPT_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={"host_id": host_id},
                )

            # 3. Update host ***REMOVED***word
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # Only update non-deleted records
                    )
                )
                .values(host_pwd=encrypted_***REMOVED***word)
            )

            logger.info(
                "Execute ***REMOVED***word update operation",
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
                    "Host ***REMOVED***word update failed, record may have been deleted",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"Host ***REMOVED***word update failed, record may have been deleted (ID: {host_id})",
                    message_key="error.host.***REMOVED***word_update_failed",
                    error_code="HOST_PASSWORD_UPDATE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "Host ***REMOVED***word update succeeded",
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
        2. Condition: del_flag = 0
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
