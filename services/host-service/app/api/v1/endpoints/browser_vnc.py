"""Browser extension VNC connection management API endpoints

Provides VNC connection-related API endpoints used by browser extensions, including:
- POST /vnc/report - Report VNC connection result
- POST /vnc/connect - Get VNC connection information
"""

import os
import sys

from fastapi import APIRouter, Body, Depends
from starlette.status import HTTP_200_OK

# Use try-except to handle path imports
try:
    from app.utils.logging_helpers import log_request_completed, log_request_received
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.utils.logging_helpers import log_request_completed, log_request_received
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result

from app.api.v1.dependencies import get_vnc_service
from app.schemas.host import (
    GetVNCConnectionRequest,
    VNCConnectionInfo,
    VNCConnectionReport,
    VNCConnectionResponse,
)
from app.services.browser_vnc_service import BrowserVNCService

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/report",
    response_model=Result[VNCConnectionResponse],
    status_code=HTTP_200_OK,
    summary="Report VNC connection result",
    description=(
        "Process VNC connection result reported by browser extension, update host status and manage execution logs"
    ),
    responses={
        200: {
            "description": "Report succeeded",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "VNC connection result report succeeded",
                        "data": {
                            "host_id": "123",
                            "connection_status": "success",
                            "connection_time": "2025/10/15 10:00:00",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Host does not exist or request data is invalid",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "Host does not exist: 123",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_vnc_connection(
    request: VNCConnectionReport = Body(..., description="VNC connection result report data"),
    vnc_service: BrowserVNCService = Depends(get_vnc_service),
    locale: str = Depends(get_locale),
):
    """Report VNC connection result

    Process VNC connection result reported by browser extension, record connection status and time,
    and update host status and execution logs.

    ## Request parameter description
    - `user_id`: User ID (required)
    - `tc_id`: Test execution ID (required)
    - `cycle_name`: Cycle name (required)
    - `user_name`: User name (required)
    - `host_id`: Host ID, corresponds to host_rec.id (required)
    - `connection_status`: Connection status, optional values: success/failed (required)
    - `connection_time`: VNC connection time (required), supported formats:
      - `yyyy/MM/dd HH:mm:ss` (e.g., `2025/01/30 10:00:00`)
      - ISO 8601 format (e.g., `2025-01-30T10:00:00Z`)

    ## Business logic
    1. Query host_rec table based on host_id, verify if host exists
    2. If host does not exist, return 400 error
    3. If connection_status = "success":
       - Query host_exec_log table (user_id, tc_id, cycle_name, user_name, host_id, del_flag=0)
       - If old record exists: first logically delete old record (del_flag=1)
       - Whether old record exists or not: add a new record (host_state=1, case_state=0)
    4. Update host_rec table: host_state = 1 (locked), subm_time = current time
    5. Record detailed operation logs

    ## Error codes
    - `HOST_NOT_FOUND`: Host does not exist (400)
    - `INVALID_HOST_ID`: Host ID format is invalid (400)

    Args:
        request: VNC connection result report data
        vnc_service: VNC service instance

    Returns:
        Report success response, contains processing result information
    """
    log_request_received(
        "report_vnc_connection",
        extra={
            "user_id": request.user_id,
            "tc_id": request.tc_id,
            "cycle_name": request.cycle_name,
            "user_name": request.user_name,
            "host_id": request.host_id,
            "connection_status": request.connection_status,
        },
        logger_instance=logger,
    )

    result = await vnc_service.report_vnc_connection(request)

    vnc_response = VNCConnectionResponse(
        host_id=result["host_id"],
        connection_status=result["connection_status"],
        connection_time=result["connection_time"],
    )

    log_request_completed(
        "report_vnc_connection",
        extra={
            "user_id": request.user_id,
            "host_id": request.host_id,
            "connection_status": request.connection_status,
        },
        logger_instance=logger,
    )

    return create_success_result(
        data=vnc_response,
        message_key="success.vnc.report",
        locale=locale,
        default_message="VNC connection result report succeeded",
    )


@router.post(
    "/connect",
    response_model=Result[VNCConnectionInfo],
    status_code=HTTP_200_OK,
    summary="Get VNC connection information",
    description="Get VNC connection parameters for specified host, used to establish VNC connection",
    responses={
        200: {
            "description": "Get succeeded",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Operation succeeded",
                        "data": {
                            "ip": "192.168.101.118",
                            "port": "5900",
                            "username": "neusoft",
                            "password": "********",  # Sensitive data redated
                        },
                    }
                }
            },
        },
        400: {
            "description": "Request data is invalid or VNC information is incomplete",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "Host ID format is invalid",
                        "error_code": "INVALID_HOST_ID",
                    }
                }
            },
        },
        404: {
            "description": "Host does not exist or is not enabled",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53001,
                        "message": "Host does not exist or is not enabled",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_vnc_connection(
    request: GetVNCConnectionRequest = Body(..., description="Get VNC connection information request data"),
    vnc_service: BrowserVNCService = Depends(get_vnc_service),
    locale: str = Depends(get_locale),
) -> Result[VNCConnectionInfo]:
    """Get VNC connection information

    Query database based on host ID, return parameters required to establish VNC connection.

    ## Request parameter description
    - `id`: Host ID, corresponds to host_rec.id (required)

    ## Business logic
    1. Verify host ID format
    2. Query host_rec table
    3. Check if host is enabled and not deleted
    4. Check if VNC connection information is complete
    5. Update host status to locked (host_state = 1)
    6. Return VNC connection parameters

    ## Return field description
    - `ip`: VNC server IP address
    - `port`: VNC service port
    - `username`: Connection username
    - `password`: Connection password

    ## Error codes
    - `INVALID_HOST_ID`: Host ID format is invalid (400)
    - `HOST_NOT_FOUND`: Host does not exist or is not enabled (404)
    - `VNC_INFO_INCOMPLETE`: VNC connection information is incomplete (400)
    - `VNC_GET_FAILED`: Get failed, service exception (500)

    Args:
        request: Get VNC connection information request
        vnc_service: VNC service instance

    Returns:
        Response containing VNC connection information
    """
    logger.info(
        "Received get VNC connection information request",
        extra={"host_rec_id": request.id},
    )

    vnc_info = await vnc_service.get_vnc_connection_info(request.id)

    vnc_connection_info = VNCConnectionInfo(
        ip=vnc_info["ip"],
        port=vnc_info["port"],
        username=vnc_info["username"],
        password=vnc_info["password"],
    )

    logger.info(
        "Get VNC connection information completed",
        extra={
            "host_rec_id": request.id,
            "ip": vnc_info["ip"],
        },
    )

    return create_success_result(
        data=vnc_connection_info,
        message_key="success.vnc.get_connection",
        locale=locale,
        default_message="Get VNC connection information succeeded",
    )
