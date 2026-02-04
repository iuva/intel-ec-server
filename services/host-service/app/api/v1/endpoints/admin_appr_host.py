"""Admin backend pending approval host management API endpoints

Provides HTTP API interfaces for pending approval host management used by admin backend.
"""

import os
import sys

from fastapi import APIRouter, Body, Depends, Request

# Use try-except to handle path imports
try:
    from app.api.v1.dependencies import get_admin_appr_host_service, get_current_user
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailRequest,
        AdminApprHostDetailResponse,
        AdminApprHostListRequest,
        AdminApprHostListResponse,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )
    from app.services.admin_appr_host_service import AdminApprHostService
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_appr_host_service, get_current_user
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailRequest,
        AdminApprHostDetailResponse,
        AdminApprHostListRequest,
        AdminApprHostListResponse,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )
    from app.services.admin_appr_host_service import AdminApprHostService
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=Result[AdminApprHostListResponse],
    summary="Query pending approval host list",
    description="Query pending approval host list with pagination, supports multiple search conditions",
    responses={
        200: {
            "description": "Query succeeded",
            "model": Result[AdminApprHostListResponse],
        },
    },
)
@handle_api_errors
async def list_appr_hosts(
    request: AdminApprHostListRequest = Depends(),
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminApprHostListResponse]:
    """Query pending approval host list (admin backend)

    Business logic:
    - Query host_rec table, conditions: host_state > 4 and host_state < 8, appr_state != 1, del_flag = 0
    - Sort by created_time descending
    - Join host_hw_rec table, get diff_state of latest record for each host_id
      - Only query records with sync_state = 1 (pending sync)
      - Sort by created_time descending, take diff_state of first record
      - Keep consistent with diff_state retrieval logic of get_appr_host_detail interface

    ## Search conditions (optional)
    - `mac`: MAC address (corresponds to host_rec.mac_addr)
    - `mg_id`: Unique boot ID (corresponds to host_rec.mg_id)
    - `host_state`: Host status (corresponds to host_rec.host_state)

    ## Return fields
    - `host_id`: Host ID (host_rec table primary key id)
    - `mg_id`: Unique boot ID (host_rec table mg_id)
    - `mac_addr`: MAC address (host_rec table mac_addr)
    - `host_state`: Host status (host_rec table host_state)
    - `subm_time`: Submission time (host_rec table subm_time)
    - `diff_state`: Parameter status (host_hw_rec table diff_state, latest record with sync_state=1; 1-version change,
      2-content change, 3-abnormal)

    Args:
        request: Query request parameters (pagination, search conditions)
        admin_appr_host_service: Admin backend pending approval host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        AdminApprHostListSuccessResponse: Contains pending approval host list and pagination information
    """
    logger.info(
        "Received admin backend pending approval host list query request",
        extra={
            "page": request.page,
            "page_size": request.page_size,
            "mac": request.mac,
            "mg_id": request.mg_id,
            "host_state": request.host_state,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to query
    hosts, pagination = await admin_appr_host_service.list_appr_hosts(request)

    # Build response data
    response_data = AdminApprHostListResponse(
        hosts=hosts,
        total=pagination.total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=pagination.total_pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev,
    )

    logger.info(
        "Admin backend pending approval host list query completed",
        extra={
            "total": pagination.total,
            "returned_count": len(hosts),
            "page": pagination.page,
            "page_size": pagination.page_size,
        },
    )

    return create_success_result(
        data=response_data,
        message_key="success.host.appr_list_query",
        locale=locale,
        default_message="Query pending approval host list succeeded",
    )


@router.get(
    "/detail",
    response_model=Result[AdminApprHostDetailResponse],
    summary="Query pending approval host detail",
    description="Query detailed information of pending approval host",
    responses={
        200: {
            "description": "Query succeeded",
            "model": Result[AdminApprHostDetailResponse],
        },
        400: {
            "description": "Query failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host does not exist",
                            "value": {
                                "code": 53001,
                                "message": "Host does not exist or has been deleted (ID: 123)",
                                "error_code": "HOST_NOT_FOUND",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_appr_host_detail(
    request: AdminApprHostDetailRequest = Depends(),
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminApprHostDetailResponse]:
    """Query pending approval host detail (admin backend)

    Business logic:
    - Query host_rec table where id = host_id
    - Join host_hw_rec table, query data with sync_state = 1
    - Sort by host_hw_rec.created_time descending
    - Password field needs AES decryption

    ## Return fields
    - `mg_id`: Unique boot ID (host_rec table mg_id)
    - `mac`: MAC address (host_rec table mac_addr)
    - `ip`: IP address (host_rec table host_ip)
    - `username`: Host account (host_rec table host_acct)
    - `password`: Host password (host_rec table host_pwd, decrypted)
    - `port`: Port (host_rec table host_port)
    - `host_state`: Host status (host_rec table host_state)
    - `diff_state`: Parameter status (host_hw_rec table diff_state, latest record; 1-version change,
      2-content change, 3-abnormal)
    - `hw_list`: Hardware information list (host_hw_rec table records with sync_state=1, sorted by
      created_time descending)
      - `created_time`: Creation time (host_hw_rec table created_time)
      - `hw_info`: Hardware information (host_hw_rec table hw_info)

    Args:
        request: Request object containing host ID
        admin_appr_host_service: Admin backend pending approval host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        AdminApprHostDetailSuccessResponse: Response containing pending approval host detail

    Raises:
        BusinessError: When host does not exist
    """
    logger.info(
        "Received admin backend pending approval host detail query request",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to query
    detail = await admin_appr_host_service.get_appr_host_detail(request.host_id)

    logger.info(
        "Admin backend pending approval host detail query completed",
        extra={
            "host_id": request.host_id,
            "hw_list_count": len(detail.hw_list),
        },
    )

    return create_success_result(
        data=detail,
        message_key="success.host.appr_detail_query",
        locale=locale,
        default_message="Query pending approval host detail succeeded",
    )


@router.post(
    "/approve",
    response_model=SuccessResponse,
    summary="Approve pending approval host",
    description="Approve pending approval host, update hardware records and host status",
    responses={
        200: {
            "description": "Processing succeeded",
            "model": AdminApprHostApproveResponse,
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "examples": {
                        "host_ids_required": {
                            "summary": "host_ids required",
                            "value": {
                                "code": 400,
                                "message": "When diff_type=2, host_ids is a required parameter",
                                "error_code": "HOST_IDS_REQUIRED",
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "approve_failed": {
                            "summary": "Approve failed",
                            "value": {
                                "code": 500,
                                "message": "Approve host failed: database operation exception",
                                "error_code": "APPROVE_HOST_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def approve_hosts(
    request: AdminApprHostApproveRequest = Body(..., description="Approve pending approval host request data"),
    http_request: Request = ...,
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Approve pending approval host (admin backend)

    Business logic:
    - **diff_type is empty** (manually disabled data):
      - host_ids is required
      - Update host_rec table: appr_state = 1, host_state = 0
      - Do not process hardware records (host_hw_rec)
    - **diff_type = 1** (version change):
      - If host_ids is provided, logic is same as diff_type = 2
      - If host_ids is not provided, automatically query all host_id from host_hw_rec table where
        sync_state = 1, diff_state = 1
    - **diff_type = 2** (content change):
      - Query all data from host_hw_rec table where host_id = id, sync_state = 1
      - Latest record: sync_state = 2, appr_time = now(), appr_by = id from token
      - Other records: sync_state = 4
      - Update host_rec table: appr_state = 1, host_state = 0, hw_id = id of latest record in
        host_hw_rec, subm_time = now()
    - **Email notification** (when diff_type = 1 or 2, after all data processing completed):
      - Query sys_conf table where conf_key = "email" for conf_val
      - If configuration is not empty, send notification email to each email address
      - Email content includes: approver information (user_name, user_account), changed host
        information (hardware_id, host_ip)
      - Email sending failure does not affect global transaction

    ## Request parameters
    - `diff_type`: Change type (1-version change, 2-content change; empty represents manually disabled data)
    - `host_ids`: Host ID list (required when diff_type is empty or diff_type=2; optional when
      diff_type=1, auto-query if not provided)

    ## Return fields
    - `success_count`: Number of successfully processed hosts
    - `failed_count`: Number of failed hosts
    - `results`: Processing result details (includes successful and failed records, and email
      notification error information)

    Args:
        request: Approve request parameters
        admin_appr_host_service: Admin backend pending approval host service instance
        current_user: Current user information (contains user_id)
        locale: Language preference

    Returns:
        SuccessResponse: Contains processing results and statistics

    Raises:
        BusinessError: When parameter validation fails or business logic error occurs
    """
    logger.info(
        "Received admin backend approve host request",
        extra={
            "diff_type": request.diff_type,
            "host_ids": request.host_ids,
            "host_count": len(request.host_ids or []),
        },
    )

    # Get user ID from request header (passed by Gateway)
    from app.services.external_api_client import get_user_id_from_request

    appr_by = get_user_id_from_request(http_request)
    if not appr_by:
        logger.warning(
            "Unable to get user ID from request header",
            extra={
                "path": http_request.url.path,
            },
        )
        appr_by = 0  # If unable to get user ID, use default value

    # Call service layer to process (pass locale parameter and http_request object)
    result = await admin_appr_host_service.approve_hosts(request, appr_by, locale=locale, http_request=http_request)

    logger.info(
        "Admin backend approve host processing completed",
        extra={
            "diff_type": request.diff_type,
            "success_count": result.success_count,
            "failed_count": result.failed_count,
            "total_count": result.success_count + result.failed_count,
        },
    )

    return SuccessResponse(
        data=result.model_dump(),
        message_key="success.host.approve_completed",
        locale=locale,
    )


@router.get(
    "/maintain-email",
    response_model=SuccessResponse,
    summary="Get maintenance notification email",
    description="Query sys_conf table, get maintenance notification email configuration",
    responses={
        200: {
            "description": "Query succeeded",
            "model": AdminMaintainEmailResponse,
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "get_failed": {
                            "summary": "Get failed",
                            "value": {
                                "code": 500,
                                "message": "Get maintenance notification email failed: database operation exception",
                                "error_code": "GET_MAINTAIN_EMAIL_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_maintain_email(
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Get maintenance notification email (admin backend)

    Business logic:
    1. Query sys_conf table, conf_key = "email", state_flag = 0, del_flag = 0
    2. Return conf_val value

    ## Return fields
    - `conf_key`: Configuration key (fixed as "email")
    - `conf_val`: Configuration value (email addresses, multiple emails separated by half-width commas)
    - `message`: Operation result message

    Args:
        admin_appr_host_service: Admin backend pending approval host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Contains maintenance notification email configuration information

    Raises:
        BusinessError: When database operation fails
    """
    logger.info(
        "Received admin backend get maintenance notification email request",
        extra={
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to query
    result = await admin_appr_host_service.get_maintain_email()

    logger.info(
        "Admin backend get maintenance notification email completed",
        extra={
            "conf_key": result.conf_key,
            "conf_val_length": len(result.conf_val),
        },
    )

    return SuccessResponse(
        data=result.model_dump(),
        message_key="success.email.get_completed",
        locale=locale,
    )


@router.post(
    "/maintain-email",
    response_model=SuccessResponse,
    summary="Set maintenance notification email",
    description="Set maintenance notification email, multiple emails separated by half-width commas",
    responses={
        200: {
            "description": "Set succeeded",
            "model": AdminMaintainEmailResponse,
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "examples": {
                        "email_empty": {
                            "summary": "Email address is empty",
                            "value": {
                                "code": 400,
                                "message": "Email address cannot be empty",
                                "error_code": "EMAIL_EMPTY",
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "set_failed": {
                            "summary": "Set failed",
                            "value": {
                                "code": 500,
                                "message": "Set maintenance notification email failed: database operation exception",
                                "error_code": "SET_MAINTAIN_EMAIL_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def set_maintain_email(
    request: AdminMaintainEmailRequest = Body(..., description="Set maintenance notification email request data"),
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Set maintenance notification email (admin backend)

    Business logic:
    1. Format email: remove spaces, convert full-width commas to half-width commas
    2. Query sys_conf table, conf_key = "email"
    3. Insert if not exists, update conf_val if exists

    ## Request parameters
    - `email`: Email address (multiple emails separated by half-width commas)

    ## Return fields
    - `conf_key`: Configuration key (fixed as "email")
    - `conf_val`: Configuration value (formatted email address)
    - `message`: Operation result message

    Args:
        request: Maintenance notification email setting request parameters
        admin_appr_host_service: Admin backend pending approval host service instance
        current_user: Current user information (contains user_id)
        locale: Language preference

    Returns:
        SuccessResponse: Contains setting result

    Raises:
        BusinessError: When parameter validation fails or database operation fails
    """
    logger.info(
        "Received admin backend maintenance notification email setting request",
        extra={
            "email": request.email,
            "user_id": current_user.get("id"),
        },
    )

    # Get current user ID
    operator_id = current_user.get("id")
    if not operator_id:
        logger.warning(
            "Unable to get current user ID",
            extra={
                "current_user": current_user,
            },
        )
        operator_id = 0  # If unable to get user ID, use default value

    # Call service layer to process
    result = await admin_appr_host_service.set_maintain_email(request, operator_id)

    logger.info(
        "Admin backend maintenance notification email setting completed",
        extra={
            "conf_key": result.conf_key,
            "conf_val": result.conf_val,
            "operator_id": operator_id,
        },
    )

    return SuccessResponse(
        data=result.model_dump(),
        message_key="success.email.set_completed",
        locale=locale,
    )
