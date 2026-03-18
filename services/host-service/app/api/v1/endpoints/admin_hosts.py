"""Admin backend host management API endpoints

Provides HTTP API interfaces for host management used by the admin backend.
"""

import os
import sys

from fastapi import APIRouter, Body, Depends, Path, Request
from starlette.status import HTTP_200_OK

# Use try-except to handle path imports
try:
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostDetailRequest,
        AdminHostDetailResponse,
        AdminHostDisableRequest,
        AdminHostDisableResponse,
        AdminHostExecLogListRequest,
        AdminHostExecLogListResponse,
        AdminHostForceOfflineRequest,
        AdminHostForceOfflineResponse,
        AdminHostListRequest,
        AdminHostListResponse,
        AdminHostUpdatePasswordRequest,
        AdminHostUpdatePasswordResponse,
        AdminHostVncCredentialsResponse,
    )
    from app.services.admin_host_service import AdminHostService
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostDetailRequest,
        AdminHostDetailResponse,
        AdminHostDisableRequest,
        AdminHostDisableResponse,
        AdminHostExecLogListRequest,
        AdminHostExecLogListResponse,
        AdminHostForceOfflineRequest,
        AdminHostForceOfflineResponse,
        AdminHostListRequest,
        AdminHostListResponse,
        AdminHostUpdatePasswordRequest,
        AdminHostUpdatePasswordResponse,
        AdminHostVncCredentialsResponse,
    )
    from app.services.admin_host_service import AdminHostService
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=Result[AdminHostListResponse],
    summary="Query available host list",
    description="Paginated query of available host list, supports multiple search conditions",
    responses={
        200: {
            "description": "Query successful",
            "model": Result[AdminHostListResponse],
        },
    },
)
@handle_api_errors
async def list_hosts(
    request: AdminHostListRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostListResponse]:
    """Query available host list (admin backend)

    Business logic:
    - Query host_rec table, conditions: host_state >= 0 and host_state <= 4, appr_state = 1, del_flag = 0
    - Join host_exec_log table to get the latest record for each host_id (ordered by created_time descending)
    - Order by host_rec.created_time descending

    ## Search conditions (optional)
    - `mac`: MAC address (corresponds to host_rec.mac_addr)
    - `username`: Host account (corresponds to host_rec.host_acct)
    - `host_state`: Host state (corresponds to host_rec.host_state; "
        "supported range: 0-free, 1-locked, 2-occupied, 3-case executing, 4-offline)
    - `mg_id`: Unique machine GUID (corresponds to host_rec.mg_id)
    - `use_by`: User name (corresponds to host_exec_log.user_name)

    Note:
    - Base query conditions are fixed to records with `host_state >= 0 and host_state <= 4`
    - If `host_state` parameter is provided, further exact match that state value

    ## Return fields
    - `host_id`: Host ID (host_rec table primary key id)
    - `username`: Host account (host_rec table host_acct)
    - `mg_id`: Unique machine GUID (host_rec table mg_id)
    - `mac`: MAC address (host_rec table mac_addr)
    - `use_by`: User name (host_exec_log table user_name, latest record)
    - `host_state`: Host state (host_rec table host_state)
    - `appr_state`: Approval state (host_rec table appr_state)

    Args:
        request: Query request parameters (pagination, search conditions)
        admin_host_service: Admin backend host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        AdminHostListSuccessResponse: Contains host list and pagination information
    """
    logger.info(
        "Received admin backend available host list query request",
        extra={
            "page": request.page,
            "page_size": request.page_size,
            "mac": request.mac,
            "username": request.username,
            "host_state": request.host_state,
            "mg_id": request.mg_id,
            "use_by": request.use_by,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to query
    hosts, pagination = await admin_host_service.list_hosts(request)

    # Build response data
    response_data = AdminHostListResponse(
        hosts=hosts,
        total=pagination.total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=pagination.total_pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev,
    )

    logger.info(
        "Admin backend available host list query completed",
        extra={
            "total": pagination.total,
            "returned_count": len(hosts),
            "page": pagination.page,
            "page_size": pagination.page_size,
        },
    )

    return create_success_result(
        data=response_data,
        message_key="success.host.list_query",
        locale=locale,
        default_message="Query host list successful",
    )


@router.delete(
    "/{host_id}",
    response_model=SuccessResponse,
    status_code=HTTP_200_OK,
    summary="Delete host",
    description="Logically delete host (set del_flag=1) and notify external API",
    responses={
        200: {
            "description": "Delete successful",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Host deleted successfully",
                        "data": {"id": "123"},
                    }
                }
            },
        },
        400: {
            "description": "Delete failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host not found",
                            "value": {
                                "code": 53001,
                                "message": "Host does not exist or has been deleted (ID: 123)",
                                "error_code": "HOST_NOT_FOUND",
                            },
                        },
                        "delete_failed": {
                            "summary": "Delete failed",
                            "value": {
                                "code": 53002,
                                "message": "Host delete failed, record may have been deleted (ID: 123)",
                                "error_code": "HOST_DELETE_FAILED",
                            },
                        },
                        "external_api_failed": {
                            "summary": "External API notification failed",
                            "value": {
                                "code": 53003,
                                "message": "Host delete failed: External API notification failed (ID: 123)",
                                "error_code": "HOST_DELETE_EXTERNAL_API_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def delete_host(
    host_id: int = Path(..., description="Host ID (host_rec.id)", ge=1),
    request: Request = ...,
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Delete host (logical delete)

    Business logic:
    1. Logically delete host_rec table data (set del_flag=1)
    2. Synchronously notify external API after deletion
    3. If external API notification fails, rollback data deletion operation
    4. If rollback fails or notification fails, return business error code

    Args:
        host_id: Host ID (host_rec.id)
        request: FastAPI Request object (used to get user_id from request headers)
        admin_host_service: Admin backend host service instance
        locale: Language preference

    Returns:
        SuccessResponse: Delete successful response

    Raises:
        BusinessError: When host does not exist, delete fails, or external API notification fails
    """
    logger.info(
        "Received admin backend host delete request",
        extra={
            "host_id": host_id,
        },
    )

    # Call service layer to delete (pass request object to get user_id from request headers)
    deleted_id = await admin_host_service.delete_host(host_id, request=request, locale=locale)

    logger.info(
        "Admin backend host delete completed",
        extra={
            "host_id": deleted_id,
        },
    )

    return SuccessResponse(
        data=AdminHostDeleteResponse(id=deleted_id).model_dump(),
        message_key="success.host.delete",
        locale=locale,
    )


@router.put(
    "/disable",
    response_model=SuccessResponse,
    summary="Disable host",
    description="Disable host (set appr_state=0)",
    responses={
        200: {
            "description": "Disable successful",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Host disabled successfully",
                        "data": {
                            "id": "123",
                            "appr_state": 0,
                            "host_state": 7,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Disable failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host not found",
                            "value": {
                                "code": 53001,
                                "message": "Host does not exist or has been deleted (ID: 123)",
                                "error_code": "HOST_NOT_FOUND",
                            },
                        },
                        "disable_failed": {
                            "summary": "Disable failed",
                            "value": {
                                "code": 53004,
                                "message": "Host disable failed, record may have been deleted (ID: 123)",
                                "error_code": "HOST_DISABLE_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def disable_host(
    request: AdminHostDisableRequest = Body(..., description="Host disable request data"),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Disable host

    Business logic:
    1. Update host_rec table appr_state field to 0 (disabled) based on host_id
    2. If host is already disabled, return friendly prompt

    Args:
        request: Request object containing host ID
        admin_host_service: Admin backend host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Disable successful response

    Raises:
        BusinessError: When host does not exist or disable fails
    """
    logger.info(
        "Received admin backend host disable request",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to disable
    result = await admin_host_service.disable_host(request.host_id)

    logger.info(
        "Admin backend host disable completed",
        extra={
            "host_id": result["id"],
            "appr_state": result["appr_state"],
            "user_id": current_user.get("id"),
        },
    )

    return SuccessResponse(
        data=AdminHostDisableResponse(
            id=result["id"],
            appr_state=result["appr_state"],
            host_state=result["host_state"],
        ).model_dump(),
        message_key="success.host.disable",
        locale=locale,
    )


@router.post(
    "/force-offline",
    response_model=SuccessResponse,
    summary="Force offline host",
    description=(
        "Force offline host (set host_state=4), only hosts in free state (host_state=0) are allowed to go offline"
    ),
    responses={
        200: {
            "description": "Force offline successful",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Host force offline successful",
                        "data": {
                            "id": "123",
                            "host_state": 4,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Force offline failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host not found",
                            "value": {
                                "code": 53001,
                                "message": "Host does not exist or has been deleted (ID: 123)",
                                "error_code": "HOST_NOT_FOUND",
                            },
                        },
                        "state_invalid": {
                            "summary": "Host state does not allow offline",
                            "value": {
                                "code": 53005,
                                "message": (
                                    "Host state does not allow force offline, "
                                    "current state: 2, required state: 0 (free)"
                                ),
                                "error_code": "HOST_FORCE_OFFLINE_STATE_INVALID",
                            },
                        },
                        "force_offline_failed": {
                            "summary": "Force offline failed",
                            "value": {
                                "code": 53005,
                                "message": (
                                    "Host force offline failed, record may have been deleted or state changed (ID: 123)"
                                ),
                                "error_code": "HOST_FORCE_OFFLINE_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def force_offline_host(
    request: AdminHostForceOfflineRequest = Body(..., description="Host force offline request data"),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Force offline host

    Business logic:
    1. Check if host exists and is not deleted
    2. Check if host state is 0 (free state), only free state can go offline
    3. Update host_rec table host_state field to 4 (offline state)

    Args:
        request: Request object containing host ID
        admin_host_service: Admin backend host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Force offline successful response

    Raises:
        BusinessError: When host does not exist, host state is not free, or update fails
    """
    logger.info(
        "Received admin backend host force offline request",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to force offline (pass locale parameter for multilingual error messages)
    result = await admin_host_service.force_offline_host(request.host_id, locale=locale)

    logger.info(
        "Admin backend host force offline completed",
        extra={
            "host_id": result["id"],
            "host_state": result["host_state"],
            "user_id": current_user.get("id"),
        },
    )

    return SuccessResponse(
        data=AdminHostForceOfflineResponse(
            id=result["id"],
            host_state=result["host_state"],
        ).model_dump(),
        message_key="success.host.force_offline",
        locale=locale,
    )


@router.get(
    "/detail",
    response_model=Result[AdminHostDetailResponse],
    summary="Query host detail",
    description="Query detailed information of available host (main information)",
    responses={
        200: {
            "description": "Query successful",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Query host detail successful",
                        "data": {
                            "mg_id": "machine-guid-123",
                            "mac": "00:11:22:33:44:55",
                            "ip": "192.168.1.100",
                            "username": "admin",
                            "password": "********",
                            "port": 5900,
                            "hw_info": {"cpu": "Intel i7", "memory": "16GB"},
                            "appr_time": "2025-01-15T10:00:00Z",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Query failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host not found",
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
async def get_host_detail(
    request: AdminHostDetailRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostDetailResponse]:
    """Query host detail (main information)

    Business logic:
    1. Query basic information from host_rec table
    2. Join host_hw_rec table to get list data with sync_state=2, ordered by updated_time descending
    3. Return host detail (including hardware information list)
    4. Password field needs decryption (AES encrypted)

    ## Return fields
    - `mg_id`: Unique machine GUID (host_rec table mg_id)
    - `mac`: MAC address (host_rec table mac_addr)
    - `ip`: IP address (host_rec table host_ip)
    - `username`: Host account (host_rec table host_acct)
    - `password`: Host password (host_rec table host_pwd, decrypted)
    - `port`: Port (host_rec table host_port)
    - `hw_list`: Hardware information list (host_hw_rec table records with sync_state=2, "
        "ordered by updated_time descending)
      - `hw_info`: Hardware information (host_hw_rec table hw_info)
      - `appr_time`: Approval time (host_hw_rec table appr_time)

    Args:
        request: Request object containing host ID
        admin_host_service: Admin backend host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        AdminHostDetailSuccessResponse: Response containing host detail

    Raises:
        BusinessError: When host does not exist
    """
    logger.info(
        "Received admin backend host detail query request",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to query
    detail = await admin_host_service.get_host_detail(request.host_id)

    logger.info(
        "Admin backend host detail query completed",
        extra={
            "host_id": request.host_id,
            "hw_list_count": len(detail.get("hw_list", [])),
            "user_id": current_user.get("id"),
        },
    )

    # Build response data
    detail_response = AdminHostDetailResponse(
        mg_id=detail.get("mg_id"),
        mac=detail.get("mac"),
        ip=detail.get("ip"),
        username=detail.get("username"),
        password=detail.get("password"),
        port=detail.get("port"),
        hw_list=detail.get("hw_list", []),
    )

    return create_success_result(
        data=detail_response,
        message_key="success.host.detail_query",
        locale=locale,
        default_message="Query host detail successful",
    )


@router.get(
    "/{host_id}/vnc-credentials",
    response_model=Result[AdminHostVncCredentialsResponse],
    summary="Get host VNC credentials",
    description=(
        "Get host_acct and VNC password by host_id. "
        "Password is stored AES-encrypted; returned as RealVNC-encrypted (same algorithm as browser VNC connection)."
    ),
    responses={
        200: {
            "description": "Query successful",
            "model": Result[AdminHostVncCredentialsResponse],
        },
        400: {
            "description": "Host not found or invalid host_id",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53001,
                        "message": "Host does not exist or has been deleted (ID: 123)",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_host_vnc_credentials(
    host_id: int = Path(..., ge=1, description="Host ID (host_rec.id)"),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostVncCredentialsResponse]:
    """Get host account and VNC password (RealVNC encrypted) by host_id.

    Business logic:
    1. Query host_rec by host_id (must exist and not deleted)
    2. Return host_acct (host_rec.host_acct)
    3. Decrypt host_pwd (AES) then convert to RealVNC encrypted password (same as browser VNC flow)

    Returns:
        host_id: Host ID
        ip: Host IP
        host_acct: Host account
        vnc_password: RealVNC-encrypted password (hex string), or None if decrypt/encrypt fails
    """
    logger.info(
        "Received admin backend host VNC credentials request",
        extra={"host_id": host_id, "user_id": current_user.get("id")},
    )

    data = await admin_host_service.get_host_vnc_credentials(host_id)

    logger.info(
        "Admin backend host VNC credentials query completed",
        extra={"host_id": host_id},
    )

    response_data = AdminHostVncCredentialsResponse(
        host_id=data["host_id"],
        ip=data.get("ip"),
        host_acct=data.get("host_acct"),
        vnc_password=data.get("vnc_password"),
    )
    return create_success_result(
        data=response_data,
        message_key="success.host.vnc_credentials_query",
        locale=locale,
        default_message="Query host VNC credentials successful",
    )


@router.put(
    "/password",
    response_model=SuccessResponse,
    summary="Update host password",
    description="Update host password (stored after AES encryption)",
    responses={
        200: {
            "description": "Password update successful",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Host password updated successfully",
                        "data": {
                            "id": "123",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Password update failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host not found",
                            "value": {
                                "code": 53001,
                                "message": "Host does not exist or has been deleted (ID: 123)",
                                "error_code": "HOST_NOT_FOUND",
                            },
                        },
                        "password_update_failed": {
                            "summary": "Password update failed",
                            "value": {
                                "code": 53006,
                                "message": "Host password update failed, record may have been deleted (ID: 123)",
                                "error_code": "HOST_PASSWORD_UPDATE_FAILED",
                            },
                        },
                        "password_encrypt_failed": {
                            "summary": "Password encryption failed",
                            "value": {
                                "code": 53007,
                                "message": "Password encryption failed (ID: 123)",
                                "error_code": "PASSWORD_ENCRYPT_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def update_host_password(
    request: AdminHostUpdatePasswordRequest = Body(..., description="Host password update request data"),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """Update host password

    Business logic:
    1. Check if host exists and is not deleted
    2. Encrypt received plaintext password with AES
    3. Update host_rec table host_pwd field to encrypted password

    Args:
        request: Request object containing host ID and plaintext password
        admin_host_service: Admin backend host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Password update successful response

    Raises:
        BusinessError: When host does not exist, password encryption fails, or update fails
    """
    logger.info(
        "Received admin backend host password update request",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to update password
    result = await admin_host_service.update_host_password(request.host_id, request.password)

    logger.info(
        "Admin backend host password update completed",
        extra={
            "host_id": result["id"],
            "user_id": current_user.get("id"),
        },
    )

    return SuccessResponse(
        data=AdminHostUpdatePasswordResponse(
            id=result["id"],
        ).model_dump(),
        message_key="success.host.password_update",
        locale=locale,
    )


@router.get(
    "/exec-logs",
    response_model=Result[AdminHostExecLogListResponse],
    summary="Query host execution log list",
    description="Paginated query of host execution log list (ordered by creation time descending)",
    responses={
        200: {
            "description": "Query successful",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Query execution log successful",
                        "data": {
                            "logs": [
                                {
                                    "exec_date": "2025-01-15",
                                    "exec_time": "01:30:45",
                                    "tc_id": "test_case_001",
                                    "use_by": "user123",
                                    "case_state": 2,
                                    "result_msg": "Execution successful",
                                    "log_url": "http://example.com/logs/123.log",
                                }
                            ],
                            "total": 100,
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 5,
                            "has_next": True,
                            "has_prev": False,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Query failed (business error)",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "Host not found",
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
async def list_host_exec_logs(
    request: AdminHostExecLogListRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostExecLogListResponse]:
    """Query host execution log list (paginated)

    Business logic:
    1. Query host_exec_log table based on host_id
    2. Condition: del_flag = 0
    3. Order by created_time descending
    4. Calculate exec_date (date part of begin_time, format %Y-%m-%d)
    5. Calculate exec_time (end_time - begin_time, format %H:%M:%S, if end_time is empty, use current time)

    ## Return fields
    - `exec_date`: Execution date (format: %Y-%m-%d)
    - `exec_time`: Execution duration (format: %H:%M:%S)
    - `tc_id`: Test case ID (host_exec_log table tc_id)
    - `use_by`: User name (host_exec_log table user_name)
    - `case_state`: Execution state (0-free, 1-started, 2-success, 3-failed)
    - `result_msg`: Execution result (host_exec_log table result_msg)
    - `log_url`: Execution log URL (host_exec_log table log_url)

    Args:
        request: Query request parameters (host_id, pagination parameters)
        admin_host_service: Admin backend host service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Contains execution log list and pagination information

    Raises:
        BusinessError: When query fails
    """
    logger.info(
        "Received admin backend host execution log list query request",
        extra={
            "host_id": request.host_id,
            "page": request.page,
            "page_size": request.page_size,
            "user_id": current_user.get("id"),
        },
    )

    # Call service layer to query
    logs, pagination = await admin_host_service.list_host_exec_logs(request)

    # Build response data
    response_data = AdminHostExecLogListResponse(
        logs=logs,
        total=pagination.total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=pagination.total_pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev,
    )

    logger.info(
        "Admin backend host execution log list query completed",
        extra={
            "host_id": request.host_id,
            "total": pagination.total,
            "returned_count": len(logs),
            "page": pagination.page,
            "page_size": pagination.page_size,
            "user_id": current_user.get("id"),
        },
    )

    return create_success_result(
        data=response_data,
        message_key="success.host.exec_log_list_query",
        locale=locale,
        default_message="Query execution log list successful",
    )
