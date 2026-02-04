"""Browser extension host management API endpoints

Provides API endpoints for host querying used by browser extensions.
"""

import os
import sys

from fastapi import APIRouter, Body, Depends, Request

from app.api.v1.dependencies import get_host_discovery_service, get_host_service
from app.schemas.host import (
    AvailableHostsListResponse,
    QueryAvailableHostsRequest,
    ReleaseHostsRequest,
    ReleaseHostsResponse,
    ResetHostForTestRequest,
    ResetHostForTestResponse,
    RetryVNCListResponse,
)
from app.services.browser_host_service import BrowserHostService

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

from app.services.host_discovery_service import HostDiscoveryService

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/available",
    response_model=Result[AvailableHostsListResponse],
    summary="Query available host list",
    description="Query available host list, supports cursor pagination",
    responses={
        200: {
            "description": "Query succeeded",
            "model": Result[AvailableHostsListResponse],
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "Request parameters invalid",
                        "error_code": "INVALID_PARAMS",
                    }
                }
            },
        },
        405: {
            "description": "HTTP method not allowed",
            "content": {
                "application/json": {
                    "example": {
                        "code": 405,
                        "message": "This interface only supports POST method, please use POST request",
                        "error_code": "METHOD_NOT_ALLOWED",
                    }
                }
            },
        },
        503: {
            "description": "External service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "code": 503,
                        "message": "Hardware interface call failed, please try again later",
                        "error_code": "HARDWARE_API_ERROR",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def query_available_hosts(
    request: QueryAvailableHostsRequest = Body(..., description="Query available host list request parameters"),
    fastapi_request: Request = ...,  # FastAPI Request object (used to get user_id)
    host_discovery_service: HostDiscoveryService = Depends(get_host_discovery_service),
    locale: str = Depends(get_locale),
) -> Result[AvailableHostsListResponse]:
    """Query available host list - cursor pagination

    ## Request parameter description
    - `tc_id`: Test case ID (required)
    - `cycle_name`: Test cycle name (required)
    - `user_name`: User name (required)
    - `page_size`: Page size, 1-100 (optional, default 20)
    - `last_id`: ID of last record from previous page (optional)
    - `email`: User email (optional). If provided, will directly use this email for external
      interface authentication, skip database query, improve performance

    ## Cursor pagination description
    1. **First request**: Do not provide last_id or pass null, start query from beginning
    2. **Subsequent requests**: Get last_id from response, pass to next request
    3. **Avoid concurrency pollution**: Each user's request is processed independently
    4. **Performance optimization**: Using cursor is more efficient than page-based pagination

    ## Business logic
    1. Call external hardware interface to get host list (paginated)
       - If `email` parameter is provided, directly use this email for external interface authentication,
         skip database query
       - If `email` is not provided, system will query database to get email based on `user_id`
         (obtained from request header)
    2. Query local host_rec table based on hardware_id
    3. Filter conditions:
       - appr_state = 1 (enabled status)
       - host_state = 0 (idle status)
       - tcp_state = 2 (listening/connection normal)
       - del_flag = 0 (not deleted)
    4. Skip processed records based on last_id
    5. Collect results that meet page_size and return

    ## Authentication description
    - **Method 1 (recommended)**: Provide `email` parameter, system directly uses this email to get
      external interface token, skip database query, better performance
    - **Method 2**: Do not provide `email` parameter, system gets `user_id` from request header
      `X-User-Info`, then queries database to get email

    ## Return data description
    - `hosts`: Available host list
    - `total`: Total number of available hosts discovered in this query
    - `page_size`: Page size
    - `has_next`: Whether there is next page
    - `last_id`: ID of last record on current page, used for requesting next page

    Args:
        request: Query request (cursor pagination), contains fields like tc_id, cycle_name, user_name,
          page_size, last_id, email
        fastapi_request: FastAPI Request object (used to get user_id from request header)
        host_discovery_service: Host discovery service instance
        locale: Language preference settings

    Returns:
        Available host list (contains has_next and last_id for next page request)

    Example:
        ```json
        {
            "tc_id": "test_case_123",
            "cycle_name": "cycle_1",
            "user_name": "test_user",
            "page_size": 20,
            "email": "user@example.com"  // Optional, skip database query if provided
        }
        ```
    """
    log_request_received(
        "query_available_hosts",
        extra={
            "tc_id": request.tc_id,
            "cycle_name": request.cycle_name,
            "user_name": request.user_name,
            "page_size": request.page_size,
            "last_id": request.last_id,
            "email": request.email,  # ✅ Record email (if provided)
        },
        logger_instance=logger,
    )

    # ✅ Pass FastAPI Request object, used to get user_id and call authenticated external interface
    result = await host_discovery_service.query_available_hosts(
        request=request,
        fastapi_request=fastapi_request,
    )

    log_request_completed(
        "query_available_hosts",
        extra={
            "tc_id": request.tc_id,
            "total_available": result.total,
            "page_size": result.page_size,
            "has_next": result.has_next,
            "returned_count": len(result.hosts),
            "last_id": result.last_id,
        },
        logger_instance=logger,
    )

    return create_success_result(
        data=result,
        message_key="success.host.available_list_query",
        locale=locale,
        default_message="Query available host list succeeded",
    )


@router.post(
    "/retry-vnc",
    response_model=Result[RetryVNCListResponse],
    summary="Get retry VNC list",
    description="Query VNC connection list that needs retry (hosts with case_state != 2)",
    responses={
        200: {
            "description": "Query succeeded",
            "model": Result[RetryVNCListResponse],
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "Request parameters invalid",
                        "error_code": "INVALID_PARAMS",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_retry_vnc_list(
    user_id: str = Body(..., embed=True, description="User ID"),
    host_service: BrowserHostService = Depends(get_host_service),
    locale: str = Depends(get_locale),
) -> Result[RetryVNCListResponse]:
    """Get VNC connection list that needs retry

    ## Business logic
    1. Query `host_exec_log` table:
       - Condition: `user_id = input user_id`
       - `case_state != 2` (non-success status)
       - `del_flag = 0` (not deleted)
    2. Get `host_id` from these records
    3. Query corresponding host information from `host_rec` table
    4. Return host information list

    ## Request parameters
    - `user_id`: User ID

    ## Return data
    - `hosts`: Host list that needs retry
      - `host_id`: Host ID
      - `host_ip`: Host IP
      - `user_name`: Host account (host_acct)
    - `total`: Total number of hosts

    Args:
        user_id: User ID
        host_service: Host service instance

    Returns:
        RetryVNCListSuccessResponse: Retry VNC list response
    """
    logger.info(
        "Received get retry VNC list request",
        extra={
            "user_id": user_id,
        },
    )

    retry_vnc_list = await host_service.get_retry_vnc_list(user_id)

    logger.info(
        "Get retry VNC list completed",
        extra={
            "user_id": user_id,
            "total": len(retry_vnc_list),
        },
    )

    # Build response data
    response_data = RetryVNCListResponse(
        hosts=retry_vnc_list,
        total=len(retry_vnc_list),
    )

    return create_success_result(
        data=response_data,
        message_key="success.host.retry_vnc_list_query",
        locale=locale,
        default_message="Query retry VNC list succeeded",
    )


@router.post(
    "/release",
    response_model=Result[ReleaseHostsResponse],
    summary="Release hosts",
    description=(
        "Logically delete host execution log records for specified user and update host status "
        "(set del_flag = 1, host_state = 0)"
    ),
    responses={
        200: {
            "description": "Release succeeded",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "Host release succeeded",
                        "data": {
                            "updated_count": 3,
                            "user_id": "user123",
                            "host_list": ["host1", "host2", "host3"],
                        },
                    }
                }
            },
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "Host ID format invalid",
                        "error_code": "INVALID_HOST_ID",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def release_hosts(
    request: ReleaseHostsRequest = Body(..., description="Release hosts request data"),
    host_service: BrowserHostService = Depends(get_host_service),
    locale: str = Depends(get_locale),
) -> Result[ReleaseHostsResponse]:
    """Release hosts - logically delete execution log records and update host status

    ## Business logic
    1. Logically delete records in `host_exec_log` table (set del_flag = 1)
    2. Update `host_state = 0` (idle status) for corresponding hosts in `host_rec` table
    3. Notify specified agent via WebSocket
    4. Conditions:
       - `user_id = input user_id`
       - `host_id IN (host_list)`
       - `del_flag = 0` (only delete non-deleted records)

    ## Request parameters
    - `user_id`: User ID
    - `host_list`: Host ID list

    ## Return data
    - `updated_count`: Number of updated records (logically deleted)
    - `user_id`: User ID
    - `host_list`: Host ID list

    Args:
        request: Release hosts request
        host_service: Host service instance
        locale: Language preference

    Returns:
        SuccessResponse: Unified format success response, contains release result data
    """
    logger.info(
        "Received release hosts request",
        extra={
            "user_id": request.user_id,
            "host_count": len(request.host_list),
        },
    )

    updated_count = await host_service.release_hosts(
        user_id=request.user_id,
        host_list=request.host_list,
    )

    logger.info(
        "Release hosts completed",
        extra={
            "user_id": request.user_id,
            "host_count": len(request.host_list),
            "updated_count": updated_count,
        },
    )

    response_data = ReleaseHostsResponse(
        updated_count=updated_count,
        user_id=request.user_id,
        host_list=request.host_list,
    )

    return create_success_result(
        data=response_data,
        message_key="success.host.release",
        locale=locale,
        default_message="Host release succeeded",
    )


@router.post(
    "/reset",
    response_model=Result[ResetHostForTestResponse],
    summary="Reset host for test",
    description="Reset host status to valid status and delete execution logs (for testing)",
    responses={
        200: {
            "description": "Reset succeeded",
            "model": Result[ResetHostForTestResponse],
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "Host ID format invalid",
                        "error_code": "INVALID_HOST_ID",
                    }
                }
            },
        },
        404: {
            "description": "Host does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53001,
                        "message": "Host does not exist: 123",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def reset_host_for_test(
    request: ResetHostForTestRequest = Body(..., description="Reset host for test request parameters"),
    host_service: BrowserHostService = Depends(get_host_service),
    locale: str = Depends(get_locale),
) -> Result[ResetHostForTestResponse]:
    """Reset host for test - reset host status and delete execution logs

    ## Business logic
    1. Verify host ID format and existence
    2. Update host_rec table:
       - `appr_state = 1` (enabled status)
       - `host_state = 0` (idle status)
       - `subm_time = null` (clear submission time)
    3. Logically delete corresponding records in host_exec_log table (`del_flag = 1`)
    4. Execute all operations in the same transaction

    ## Request parameters
    - `host_id`: Host ID (required)

    ## Return data
    - `host_id`: Host ID
    - `appr_state`: Approval status (1=enabled)
    - `host_state`: Host status (0=idle)
    - `subm_time`: Submission time (null after reset)
    - `deleted_log_count`: Number of deleted execution log records

    ## Notes
    - This interface is for test environment, resets host status to initial state
    - Will logically delete all execution log records for this host
    - All operations are executed in the same transaction to ensure data consistency

    Args:
        request: Reset host for test request
        host_service: Host service instance
        locale: Language preference

    Returns:
        Result[ResetHostForTestResponse]: Unified format success response, contains reset result data
    """
    logger.info(
        "Received reset host for test request",
        extra={
            "host_id": request.host_id,
        },
    )

    result = await host_service.reset_host_for_test(request.host_id)

    logger.info(
        "Reset host for test completed",
        extra={
            "host_id": request.host_id,
            "appr_state": result["appr_state"],
            "host_state": result["host_state"],
            "deleted_log_count": result["deleted_log_count"],
        },
    )

    response_data = ResetHostForTestResponse(
        host_id=result["host_id"],
        appr_state=result["appr_state"],
        host_state=result["host_state"],
        subm_time=result["subm_time"],
        deleted_log_count=result["deleted_log_count"],
    )

    return create_success_result(
        data=response_data,
        message_key="success.host.reset_for_test",
        locale=locale,
        default_message="Reset host for test succeeded",
    )
