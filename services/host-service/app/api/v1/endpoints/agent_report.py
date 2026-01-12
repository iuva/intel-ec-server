"""Agent information reporting API endpoints

Provides HTTP API interfaces for Agent information reporting.
"""

import os
import sys
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends
from starlette.status import HTTP_200_OK

# Use try-except to handle path imports
try:
    from app.api.v1.dependencies import get_current_agent
    from app.schemas.host import (
        AgentInitConfigItem,
        AgentInitConfigListResponse,
        AgentOtaUpdateStatusRequest,
        AgentOtaUpdateStatusResponse,
        AgentVNCConnectionReportRequest,
        AgentVNCConnectionReportResponse,
        HardwareReportResponse,
        OtaConfigItem,
    )
    from app.schemas.testcase import (
        TestCaseDueTimeRequest,
        TestCaseDueTimeResponse,
        TestCaseReportRequest,
        TestCaseReportResponse,
    )
    from app.services.agent_report_service import AgentReportService, get_agent_report_service
    from app.utils.logging_helpers import log_request_received
    from app.utils.response_helpers import create_success_result

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_current_agent
    from app.schemas.host import (
        AgentInitConfigItem,
        AgentInitConfigListResponse,
        AgentOtaUpdateStatusRequest,
        AgentOtaUpdateStatusResponse,
        AgentVNCConnectionReportRequest,
        AgentVNCConnectionReportResponse,
        HardwareReportResponse,
        OtaConfigItem,
    )
    from app.schemas.testcase import (
        TestCaseDueTimeRequest,
        TestCaseDueTimeResponse,
        TestCaseReportRequest,
        TestCaseReportResponse,
    )
    from app.services.agent_report_service import AgentReportService, get_agent_report_service
    from app.utils.logging_helpers import log_request_received
    from app.utils.response_helpers import create_success_result

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/hardware/report",
    response_model=Result[HardwareReportResponse],
    status_code=HTTP_200_OK,
    summary="Report hardware information",
    description="""
    Agent reports host hardware information, system will automatically detect hardware changes.

    ## Function description
    1. Receive hardware information reported by Agent (dynamic JSON)
    2. Validate required fields in hardware information (based on hardware template)
    3. Compare hardware version number and content changes
    4. Update database records based on comparison results

    ## Authentication requirements
    - Need to provide valid JWT token in Authorization header
    - Token format: `Bearer <token>`
    - id in token (extracted from user_id or sub field) will be used as host_id

    ## Request parameters
    - `dmr_config`: DMR hardware configuration (required), must include `revision` field
    - `name`: Configuration name (optional)
    - `updated_by`: Updater (optional)
    - `tags`: Tag list (optional)

    ## Business logic
    1. **First report**: Directly insert hardware record, approval status is ***REMOVED***ed
    2. **Version change**: Mark as version change (diff_state=1), waiting for approval
    3. **Content change**: Mark as content change (diff_state=2), waiting for approval
    4. **No change**: Do not update record, return no change status

    ## Notes
    - `dmr_config.revision` is a required field
    - Fields marked as `required` in hardware template must be provided
    - Hardware changes will trigger host status update (appr_state=2, host_state=6)
    """,
    responses={
        200: {
            "description": "Report succeeded",
            "model": Result[HardwareReportResponse],
        },
        400: {
            "description": "Request parameter error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53024,
                        "message": "dmr_config is a required field",
                        "error_code": "MISSING_DMR_CONFIG",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "Missing valid authentication token",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53027,
                        "message": "Hardware information report processing failed",
                        "error_code": "HARDWARE_REPORT_FAILED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_hardware(
    hardware_data: Dict[str, Any] = Body(
        ...,
        description="Hardware information (dynamic JSON)",
        example={
            "name": "Updated Agent Config",
            "dmr_config": {
                "revision": 1,
                "mainboard": {
                    "revision": 1,
                    "plt_meta_data": {"platform": "DMR", "label_plt_cfg": "auto_generated"},
                    "board": {
                        "board_meta_data": {
                            "board_name": "SHMRCDMR",
                            "host_name": "updated-host",
                            "host_ip": "10.239.168.200",
                        },
                        "baseboard": [
                            {
                                "board_id": "board_001",
                                "rework_version": "1.0",
                                "board_ip": "10.239.168.200",
                                "bmc_ip": "10.239.168.171",
                                "fru_id": "fru_001",
                            }
                        ],
                        "lsio": {
                            "usb_disc_installed": True,
                            "network_installed": True,
                            "nvme_installed": False,
                            "keyboard_installed": True,
                            "mouse_installed": False,
                        },
                        "peripheral": {
                            "itp_installed": True,
                            "usb_dbc_installed": False,
                            "controlbox_installed": True,
                            "flash_programmer_installed": True,
                            "display_installed": True,
                            "jumpers": [],
                        },
                    },
                    "misc": {
                        "installed_os": ["Windows", "Linux"],
                        "bmc_version": "2.0.1",
                        "bmc_ip": "10.239.168.171",
                        "cpld_version": "2.1.0",
                    },
                },
                "hsio": [],
                "memory": [],
                "security": {
                    "revision": 1,
                    "security": {
                        "Tpm": [
                            {
                                "tpm_enable": True,
                                "tpm_algorithm": "SHA256",
                                "tmp_family": "2.0",
                                "tpm_interface": "TIS",
                            }
                        ],
                        "CoinBattery": [],
                    },
                },
                "soc": [],
            },
            "updated_by": "agent@intel.com",
            "tags": ["alive", "checked", "updated"],
            "type": 0,
        },
    ),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[HardwareReportResponse]:
    """Report hardware information

    Args:
        hardware_data: Hardware information (dynamic JSON), contains:
            - dmr_config: DMR hardware configuration (required)
            - type: Report type (optional, default 0)
                - 0: Success, follow normal comparison logic
                - 1: Abnormal, directly set diff_state=3
        agent_info: Current Agent information (extracted from token, contains id)
        agent_report_service: Agent hardware service instance

    Returns:
        SuccessResponse: Processing result

    Raises:
        HTTPException: Business logic error or system error (handled uniformly by @handle_api_errors)
    """
    # ✅ Get id from token (already validated by get_current_agent dependency injection)
    host_id = agent_info["id"]

    # Extract type parameter (optional, default 0)
    report_type = hardware_data.get("type", 0)

    log_request_received(
        "report_hardware",
        extra={
            "host_id": host_id,
            "has_dmr_config": "dmr_config" in hardware_data,
            "type": report_type,
        },
        logger_instance=logger,
    )

    # Call service layer to process hardware information report
    result = await agent_report_service.report_hardware(
        host_id=host_id,
        hardware_data=hardware_data,
        report_type=report_type,
    )

    response_data = HardwareReportResponse(**result)
    return create_success_result(
        data=response_data,
        message_key="success.hardware.report",
        locale=locale,
        default_message="Hardware information report succeeded",
    )


@router.post(
    "/testcase/report",
    response_model=Result[TestCaseReportResponse],
    status_code=HTTP_200_OK,
    summary="Report test case execution result",
    description="""
    Agent reports test case execution result, system will update execution log records.

    ## Function description
    1. Receive test case execution result reported by Agent
    2. Extract host_id from JWT token
    3. Query latest execution log record based on host_id and tc_id
    4. Update execution status, result message and log URL

    ## Authentication requirements
    - Need to provide valid JWT token in Authorization header
    - Token format: `Bearer <token>`
    - id in token (extracted from user_id or sub field) will be used as host_id

    ## Request parameters
    - `tc_id`: Test case ID (required)
    - `state`: Execution status (required); 0-idle 1-started 2-success 3-failed
    - `result_msg`: Result message (optional)
    - `log_url`: Log file URL (optional)

    ## Business logic
    1. Query latest record in host_exec_log table based on host_id and tc_id
    2. Update case_state, result_msg and log_url fields
    3. Return update result

    ## Notes
    - tc_id is a required field
    - state must be in range 0-3
    - If corresponding execution log record is not found, return 404 error
    """,
    responses={
        200: {
            "description": "Report succeeded",
            "model": Result[TestCaseReportResponse],
        },
        400: {
            "description": (
                "Request parameter error or business logic error "
                "(including: request parameter validation failed, execution log record not found, etc.)"
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Request parameter validation failed",
                            "value": {
                                "code": 400,
                                "message": "Request parameter validation failed",
                                "error_code": "VALIDATION_ERROR",
                                "details": None,
                                "timestamp": "2025-10-30T10:00:00Z",
                            },
                        },
                        "exec_log_not_found": {
                            "summary": "Execution log record not found",
                            "value": {
                                "code": 53012,
                                "message": "Test case execution record for host not found",
                                "error_code": "EXEC_LOG_NOT_FOUND",
                                "details": None,
                                "timestamp": "2025-10-30T10:00:00Z",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "Missing valid authentication token",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-10-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53029,
                        "message": "Test case result report processing failed",
                        "error_code": "TESTCASE_REPORT_FAILED",
                        "details": None,
                        "timestamp": "2025-10-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_testcase_result(
    report_data: TestCaseReportRequest = Body(
        ...,
        description="Test case execution result",
    ),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[TestCaseReportResponse]:
    """Report test case execution result

    Args:
        report_data: Test case execution result
        agent_info: Current Agent information (extracted from token, contains id)
        agent_report_service: Agent hardware service instance

    Returns:
        SuccessResponse: Processing result

    Raises:
        HTTPException: Business logic error or system error (handled uniformly by @handle_api_errors)
    """
    # ✅ Get id from token (already validated by get_current_agent dependency injection)
    host_id = agent_info["id"]

    logger.info(
        "Received test case result report request",
        extra={
            "host_id": host_id,
            "tc_id": report_data.tc_id,
            "state": report_data.state,
        },
    )

    # Call service layer to process test case result report
    result = await agent_report_service.report_testcase_result(
        host_id=host_id,
        tc_id=report_data.tc_id,
        state=report_data.state,
        result_msg=report_data.result_msg,
        log_url=report_data.log_url,
    )

    response_data = TestCaseReportResponse(**result)
    return create_success_result(
        data=response_data,
        message_key="success.hardware.test_result_report",
        locale=locale,
        default_message="Test case result report succeeded",
    )


@router.put(
    "/testcase/due-time",
    response_model=Result[TestCaseDueTimeResponse],
    status_code=HTTP_200_OK,
    summary="Report test case expected end time",
    description="""
    Agent reports test case expected end time, system will update due_time field in execution log records.

    ## Function description
    1. Receive expected end time reported by Agent
    2. Extract host_id from JWT token
    3. Query latest execution log record in execution (case_state=1) based on host_id and tc_id
    4. Update due_time field

    ## Authentication requirements
    - Need to provide valid JWT token in Authorization header
    - Token format: `Bearer <token>`
    - id in token (extracted from user_id or sub field) will be used as host_id

    ## Request parameters
    - `tc_id`: Test case ID (required)
    - `due_time`: Expected end time (required, minutes difference, integer, calculated from current time)

    ## Business logic
    1. Server calculates actual expected end time based on current time and `due_time` (minutes)
    2. Query latest record in execution (case_state=1) in host_exec_log table based on host_id and tc_id
    3. Update due_time field
    4. Return update result

    ## Notes
    - tc_id is a required field
    - due_time must be an integer greater than or equal to 0 (represents minutes)
    - Server will automatically calculate: expected end time = current time + due_time minutes
    - If record in execution is not found, return 400 error
    """,
    responses={
        200: {
            "description": "Report succeeded",
            "model": Result[TestCaseDueTimeResponse],
        },
        400: {
            "description": (
                "Request parameter error or business logic error "
                "(including: request parameter validation failed, record in execution not found, etc.)"
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Request parameter validation failed",
                            "value": {
                                "code": 400,
                                "message": "Request parameter validation failed",
                                "error_code": "VALIDATION_ERROR",
                                "details": None,
                                "timestamp": "2025-01-30T10:00:00Z",
                            },
                        },
                        "exec_log_not_found": {
                            "summary": "Record in execution not found",
                            "value": {
                                "code": 53012,
                                "message": "Test case {tc_id} execution record for host {host_id} not found",
                                "error_code": "EXEC_LOG_NOT_FOUND",
                                "details": None,
                                "timestamp": "2025-01-30T10:00:00Z",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "Missing valid authentication token",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53030,
                        "message": "Expected end time report processing failed",
                        "error_code": "DUE_TIME_UPDATE_FAILED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_due_time(
    report_data: TestCaseDueTimeRequest = Body(
        ...,
        description="Test case expected end time",
    ),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[TestCaseDueTimeResponse]:
    """Report test case expected end time

    Args:
        report_data: Test case expected end time
        agent_info: Current Agent information (extracted from token, contains id)
        agent_report_service: Agent hardware service instance

    Returns:
        Result: Processing result

    Raises:
        HTTPException: Business logic error or system error (handled uniformly by @handle_api_errors)
    """
    # ✅ Get id from token (already validated by get_current_agent dependency injection)
    host_id = agent_info["id"]

    logger.info(
        "Received expected end time report request",
        extra={
            "host_id": host_id,
            "tc_id": report_data.tc_id,
            "due_time_minutes": report_data.due_time,
        },
    )

    # Call service layer to process expected end time report (server calculates actual time)
    result = await agent_report_service.update_due_time(
        host_id=host_id,
        tc_id=report_data.tc_id,
        due_time_minutes=report_data.due_time,
    )

    response_data = TestCaseDueTimeResponse(**result)
    return create_success_result(
        data=response_data,
        message_key="success.hardware.due_time_report",
        locale=locale,
        default_message="Expected end time report succeeded",
    )


@router.get(
    "/ota/latest",
    response_model=Result[List[OtaConfigItem]],
    status_code=HTTP_200_OK,
    summary="Get latest OTA configuration information",
    description="""
    Agent gets OTA version configuration information.

    ## Function description
    1. Query valid configurations in `sys_conf` table where `conf_key = "ota"`
    2. Return configuration list sorted by update time descending

    ## Response description
    - `conf_name`: Configuration name
    - `conf_ver`: Configuration version number
    - `conf_url`: OTA package download URL
    - `conf_md5`: OTA package MD5 checksum
    """,
)
@handle_api_errors
async def get_latest_ota_configs(
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[List[OtaConfigItem]]:
    """Get latest OTA configuration information"""
    log_request_received(
        "get_latest_ota_configs",
        logger_instance=logger,
    )

    configs = await agent_report_service.get_latest_ota_configs()
    ota_items = [OtaConfigItem(**config) for config in configs]

    return create_success_result(
        data=ota_items,
        message_key="success.ota.query",
        locale=locale,
        default_message="Get OTA configuration succeeded",
    )


@router.post(
    "/vnc/report",
    response_model=Result[AgentVNCConnectionReportResponse],
    status_code=HTTP_200_OK,
    summary="Agent reports VNC connection status",
    description="""
    Agent reports VNC connection status, system will update host status based on status.

    ## Function description
    1. Extract host_id from JWT token
    2. Update host status based on vnc_state and current host_state

    ## Authentication requirements
    - Need to provide valid JWT token in Authorization header
    - Token format: `Bearer <token>`
    - id in token (extracted from user_id or sub field) will be used as host_id

    ## Request parameters
    - `vnc_state`: VNC connection status (required)
        - `1`: Connection succeeded
        - `2`: Connection disconnected

    ## Business logic
    1. Parse host_id from token (automatically completed through dependency injection)
    2. Query host_rec table, verify if host exists
    3. Update status based on vnc_state and current host_state:
        - When `vnc_state = 1` (connection succeeded):
            - If `host_state = 1` (locked), change to `host_state = 2` (occupied)
            - If `host_state` is not equal to 1, return `VNC_STATE_MISMATCH` error
        - When `vnc_state = 2` (connection disconnected/failed):
            - No need to check status, directly change to `host_state = 0` (idle)
            - Simultaneously logically delete valid data for corresponding host in "
                "`host_exec_log` table (`del_flag = 1`)

    ## Return data
    - `host_id`: Host ID
    - `host_state`: Updated host status (0=idle, 1=locked, 2=occupied)
    - `vnc_state`: Reported VNC connection status (1=connection succeeded, 2=connection disconnected)
    - `updated`: Whether update succeeded

    ## Error codes
    - `HOST_NOT_FOUND`: Host does not exist or has been deleted (404, error code: 53001)
    - `VNC_STATE_MISMATCH`: VNC connection succeeded but host status does not match (400, error code: 53016)
        - When `vnc_state = 1` (connection succeeded), requires `host_state = 1` (locked)
        - If `host_state` is not equal to 1, this error will be returned
    - `VNC_CONNECTION_REPORT_FAILED`: Report processing failed (500, error code: 53020)
    """,
    responses={
        200: {
            "description": "Report succeeded",
            "model": Result[AgentVNCConnectionReportResponse],
        },
        400: {
            "description": "Request parameter error or business logic error",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Request parameter validation failed",
                            "value": {
                                "code": 400,
                                "message": "Request parameter validation failed",
                                "error_code": "VALIDATION_ERROR",
                                "details": {
                                    "errors": [
                                        {
                                            "loc": ["body", "vnc_state"],
                                            "msg": "ensure this value is greater than or equal to 1",
                                            "type": "value_error.number.not_ge",
                                        }
                                    ]
                                },
                            },
                        },
                        "vnc_state_mismatch": {
                            "summary": "VNC connection succeeded but host status does not match",
                            "value": {
                                "code": 53016,
                                "message": (
                                    "VNC connection succeeded, but host status does not match. "
                                    "Current status: 0, required status: 1 (locked)"
                                ),
                                "error_code": "VNC_STATE_MISMATCH",
                                "http_status_code": 400,
                                "details": {
                                    "host_id": 123,
                                    "vnc_state": 1,
                                    "current_host_state": 0,
                                    "required_host_state": 1,
                                },
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "Host does not exist or has been deleted",
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
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 53020,
                        "message": "Agent VNC connection status report processing failed",
                        "error_code": "VNC_CONNECTION_REPORT_FAILED",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_vnc_connection_state(
    request: AgentVNCConnectionReportRequest = Body(..., description="Agent VNC connection status report request"),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[AgentVNCConnectionReportResponse]:
    """Agent reports VNC connection status

    ## Business logic
    1. Parse host_id from token (already validated by get_current_agent dependency injection)
    2. Update host status based on vnc_state and current host_state:
        - `vnc_state = 1` (connection succeeded) and `host_state = 1` (locked) → update to `host_state = 2` (occupied)
            - If `host_state` is not equal to 1, return `VNC_STATE_MISMATCH` error
        - `vnc_state = 2` (connection disconnected/failed) → directly update to `host_state = 0` (idle)
            - No need to check status
            - Simultaneously logically delete valid data for corresponding host in "
                "`host_exec_log` table (`del_flag = 1`)

    Args:
        request: Agent VNC connection status report request (contains vnc_state field)
        agent_info: Current Agent information (extracted from token, contains id)
        agent_report_service: Agent reporting service instance
        locale: Language preference

    Returns:
        Result: Unified format success response, contains update result

    Raises:
        HTTPException: Business logic error or system error (handled uniformly by @handle_api_errors)
    """
    # ✅ Get id from token (already validated by get_current_agent dependency injection)
    host_id = agent_info["id"]
    vnc_state = request.vnc_state

    logger.info(
        "Received Agent VNC connection status report request",
        extra={
            "host_id": host_id,
            "vnc_state": vnc_state,
        },
    )

    # Call service layer to process VNC connection status report
    result = await agent_report_service.report_vnc_connection_state(host_id=host_id, vnc_state=vnc_state)

    response_data = AgentVNCConnectionReportResponse(**result)
    return create_success_result(
        data=response_data,
        message_key="success.vnc.agent_report",
        locale=locale,
        default_message="Agent VNC connection status report succeeded",
    )


@router.post(
    "/ota/update-status",
    response_model=Result[AgentOtaUpdateStatusResponse],
    status_code=HTTP_200_OK,
    summary="Agent reports OTA update status",
    description="""
    Agent reports OTA update status, system will update host_upd table and host_rec table based on status.

    ## Function description
    1. Extract host_id from JWT token
    2. Query latest valid record (del_flag=0) in host_upd table based on host_id, app_name, app_ver
    3. If record not found, create new record (before creating, logically delete other "
        "valid records to ensure only one valid record exists)
    4. Update app_state field in host_upd table (1=updating, 2=success, 3=failed)
    5. If biz_state=2 (success):
       - Update host_state=0 (free) in host_rec table
       - Update agent_ver (new version) in host_rec table
       - Logically delete current record in host_upd table (del_flag=1)

    ## Authentication requirements
    - Need to provide valid JWT token in Authorization header
    - Token format: `Bearer <token>`
    - id in token (extracted from user_id or sub field) will be used as host_id

    ## Request parameters
    - `app_name`: Application name (required, corresponds to app_name in host_upd table)
    - `app_ver`: Application version number (required, corresponds to app_ver in host_upd table)
    - `biz_state`: Business status (required)
        - `1`: Updating
        - `2`: Success
        - `3`: Failed
    - `agent_ver`: Agent version number (required when update succeeds, used to update agent_ver in host_rec table)

    ## Business logic
    1. Parse host_id from token (automatically completed through dependency injection)
    2. Query latest valid record (del_flag=0) in host_upd table
    3. If record not found:
       - Logically delete all valid records for this host_id and app_name (ensure only one valid record exists)
       - Create new record, set app_state to biz_state
    4. If record found:
       - Update app_state field in host_upd table
    5. If biz_state=2 (success):
       - Update host_state=0 (free) in host_rec table
       - Update agent_ver (new version) in host_rec table
       - Logically delete current record in host_upd table (del_flag=1)

    ## Return data
    - `host_id`: Host ID
    - `host_upd_id`: Update record ID (host_upd table primary key)
    - `app_state`: Updated status (0=pre-update, 1=updating, 2=success, 3=failed)
    - `host_state`: Updated host status (if update succeeds, then 0=idle)
    - `agent_ver`: Updated Agent version number
    - `updated`: Whether update succeeded

    ## Error codes
    - `AGENT_VER_REQUIRED`: agent_ver field is required when update succeeds (400, error code: 53022)
    - `OTA_UPDATE_STATUS_REPORT_FAILED`: Report processing failed (500, error code: 53021)
    """,
    responses={
        200: {
            "description": "Report succeeded",
            "model": Result[AgentOtaUpdateStatusResponse],
        },
        400: {
            "description": "Request parameter error or business logic error",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Request parameter validation failed",
                            "value": {
                                "code": 400,
                                "message": "Request parameter validation failed",
                                "error_code": "VALIDATION_ERROR",
                                "details": {
                                    "errors": [
                                        {
                                            "loc": ["body", "biz_state"],
                                            "msg": "ensure this value is greater than or equal to 1",
                                            "type": "value_error.number.not_ge",
                                        }
                                    ]
                                },
                            },
                        },
                        "agent_ver_required": {
                            "summary": "agent_ver field is required when update succeeds",
                            "value": {
                                "code": 53022,
                                "message": "agent_ver field is required when update succeeds",
                                "error_code": "AGENT_VER_REQUIRED",
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
                    "example": {
                        "code": 53021,
                        "message": "OTA update status report processing failed",
                        "error_code": "OTA_UPDATE_STATUS_REPORT_FAILED",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_ota_update_status(
    request: AgentOtaUpdateStatusRequest = Body(..., description="Agent OTA update status report request"),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[AgentOtaUpdateStatusResponse]:
    """Agent reports OTA update status

    ## Business logic
    1. Parse host_id from token (already validated by get_current_agent dependency injection)
    2. Query latest valid record (del_flag=0) in host_upd table based on host_id, app_name, app_ver
    3. If record not found:
       - Logically delete all valid records for this host_id and app_name (ensure only one valid record exists)
       - Create new record, set app_state to biz_state
    4. If record found:
       - Update app_state field in host_upd table
    5. If biz_state=2 (success):
       - Update host_state=0 (free) in host_rec table
       - Update agent_ver (new version) in host_rec table
       - Logically delete current record in host_upd table (del_flag=1)

    Args:
        request: Agent OTA update status report request (contains app_name, app_ver, biz_state, agent_ver fields)
        agent_info: Current Agent information (extracted from token, contains id)
        agent_report_service: Agent reporting service instance
        locale: Language preference

    Returns:
        Result: Unified format success response, contains update result

    Raises:
        HTTPException: Business logic error or system error (handled uniformly by @handle_api_errors)
    """
    # ✅ Get id from token (already validated by get_current_agent dependency injection)
    host_id = agent_info["id"]

    logger.info(
        "Received Agent OTA update status report request",
        extra={
            "host_id": host_id,
            "app_name": request.app_name,
            "app_ver": request.app_ver,
            "biz_state": request.biz_state,
            "agent_ver": request.agent_ver,
        },
    )

    # Call service layer to process OTA update status report
    result = await agent_report_service.report_ota_update_status(
        host_id=host_id,
        app_name=request.app_name,
        app_ver=request.app_ver,
        biz_state=request.biz_state,
        agent_ver=request.agent_ver,
    )

    response_data = AgentOtaUpdateStatusResponse(**result)
    return create_success_result(
        data=response_data,
        message_key="success.ota.update_status",
        locale=locale,
        default_message="OTA update status report succeeded",
    )


@router.get(
    "/init",
    response_model=Result[AgentInitConfigListResponse],
    status_code=HTTP_200_OK,
    summary="Get agent initialization configurations",
    description="""
    Agent gets initialization configuration information.

    ## Function description
    1. Query sys_conf table for records where conf_key starts with 'agent_init_'
    2. Filter by state_flag = 0 (enabled) and del_flag = 0 (not deleted)
    3. Return configuration list sorted by update time descending

    ## Authentication requirements
    - Need to provide valid JWT token in Authorization header
    - Token format: `Bearer <token>`

    ## Response description
    - `configs`: List of initialization configurations, each containing:
        - `conf_key`: Configuration key (starts with 'agent_init_')
        - `conf_val`: Configuration value
        - `conf_ver`: Configuration version
        - `conf_name`: Configuration name
        - `conf_json`: Configuration JSON
    - `total`: Total number of configurations
    """,
    responses={
        200: {
            "description": "Query succeeded",
            "model": Result[AgentInitConfigListResponse],
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "Missing valid authentication token",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "Failed to get agent initialization configurations",
                        "error_code": "GET_AGENT_INIT_CONFIG_FAILED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_agent_init_configs(
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[AgentInitConfigListResponse]:
    """Get agent initialization configurations

    Query sys_conf table for records where conf_key starts with 'agent_init_',
    state_flag = 0 (enabled), and del_flag = 0 (not deleted).

    Args:
        agent_report_service: Agent reporting service instance
        locale: Language preference

    Returns:
        Result: Unified format success response, contains initialization configuration list

    Raises:
        HTTPException: Business logic error or system error (handled uniformly by @handle_api_errors)
    """
    log_request_received(
        "get_agent_init_configs",
        logger_instance=logger,
    )

    configs = await agent_report_service.get_agent_init_configs()
    init_items = [AgentInitConfigItem(**config) for config in configs]

    response_data = AgentInitConfigListResponse(
        configs=init_items,
        total=len(init_items),
    )

    return create_success_result(
        data=response_data,
        message_key="success.agent.init_config_query",
        locale=locale,
        default_message="Get agent initialization configurations succeeded",
    )
