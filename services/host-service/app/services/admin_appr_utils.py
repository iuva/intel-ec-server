"""Admin Backend Pending Approval Host Management - Utility Functions Module

Provides approval-related utility functions, including hardware API calls, table building, etc.

Split from admin_appr_host_service.py to improve code maintainability.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Use try-except to handle path imports
try:
    from app.models.host_rec import HostRec
    from app.services.external_api_client import call_external_api
    from shared.common.cache import redis_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_rec import HostRec
    from app.services.external_api_client import call_external_api
    from shared.common.cache import redis_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def build_host_table(hardware_ids: List[str], host_ips: List[str]) -> str:
    """Build host information table (HTML format)

    Args:
        hardware_ids: Hardware ID list
        host_ips: Host IP list

    Returns:
        HTML table string
    """
    if not hardware_ids and not host_ips:
        return "No changed host information"

    # Ensure both lists have same length (pad with empty strings)
    max_len = max(len(hardware_ids), len(host_ips))
    hardware_ids_padded = hardware_ids + [""] * (max_len - len(hardware_ids))
    host_ips_padded = host_ips + [""] * (max_len - len(host_ips))

    # Build HTML table
    table_rows = []
    cell_style = "padding: 12px; border: 1px solid #ddd; text-align: left;"
    header_style = (
        "padding: 12px; border: 1px solid #ddd; background-color: #4CAF50; "
        "color: white; text-align: left; font-weight: 600;"
    )
    row_style = "background-color: white;"
    alternate_row_style = "background-color: #f9f9f9;"

    for i in range(max_len):
        hw_id = hardware_ids_padded[i] if i < len(hardware_ids) else ""
        host_ip = host_ips_padded[i] if i < len(host_ips) else ""
        row_bg = alternate_row_style if i % 2 == 1 else row_style
        row_html = (
            f"<tr style='{row_bg}'>"
            f"<td style='{cell_style}'>{hw_id or '-'}</td>"
            f"<td style='{cell_style}'>{host_ip or '-'}</td>"
            f"</tr>"
        )
        table_rows.append(row_html)

    table_style = (
        "border-collapse: collapse; width: 100%; margin: 15px 0; "
        "border-radius: 5px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
    )
    return f"""
<table style='{table_style}'>
    <thead>
        <tr>
            <th style='{header_style}'>Hardware ID</th>
            <th style='{header_style}'>Host IP</th>
        </tr>
    </thead>
    <tbody>
        {"".join(table_rows)}
    </tbody>
</table>
"""


async def call_hardware_api(
    hardware_id: Optional[str],
    hw_info: Dict[str, Any],
    request: Optional[Any] = None,
    user_id: Optional[int] = None,
    locale: str = "zh_CN",
    host_id: Optional[int] = None,
) -> Dict[str, Optional[str]]:
    """Call external hardware API (create or update)

    Uses unified external API call client, automatically handles authentication.
    Uses Redis distributed lock to prevent concurrent creation when creating new hardware.

    Args:
        hardware_id: Hardware ID (if None, calls create API, otherwise calls update API)
        hw_info: Hardware information (corresponds to host_hw_rec table hw_info field)
        request: FastAPI Request object (used to get user_id from request headers)
        user_id: Currently logged in admin backend user ID (optional, preferred if provided)
        locale: Language preference
        host_id: Host ID (used to generate distributed lock key, only needed when creating new hardware)

    Returns:
        Dict[str, Optional[str]]: Dictionary containing hardware_id and host_name
            - hardware_id: Hardware ID (required)
            - host_name: Host name (optional, extracted from response body)

    Raises:
        BusinessError: When API call fails
    """
    try:
        # ✅ Determine if hardware_id is valid: None or empty string are considered invalid, call create API
        is_valid_hardware_id = hardware_id is not None and bool(hardware_id and hardware_id.strip())

        if not is_valid_hardware_id:
            # ✅ Create hardware: Use Redis distributed lock to prevent concurrent creation
            lock_key = None
            lock_value = None

            if host_id is not None:
                # Generate lock key: based on host_id, ensure same host won't concurrently create multiple hardware
                lock_key = f"hardware_create_lock:{host_id}"
                import uuid

                lock_value = str(uuid.uuid4())

                # Try to acquire lock (timeout 30 seconds)
                lock_acquired = await redis_manager.acquire_lock(lock_key, timeout=30, lock_value=lock_value)

                if not lock_acquired:
                    # If Redis unavailable, log warning but continue execution (fallback)
                    if not redis_manager.is_connected:
                        logger.warning(
                            "Redis unavailable, cannot acquire distributed lock, continuing execution (fallback)",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
                    else:
                        # Redis available but lock acquisition failed, another instance is processing
                        logger.warning(
                            "Failed to acquire hardware creation lock, another instance may be processing",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
                        raise BusinessError(
                            message=f"Host {host_id} is creating hardware record, please retry later",
                            message_key="error.hardware.creation_in_progress",
                            error_code="HARDWARE_CREATION_IN_PROGRESS",
                            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                            http_status_code=409,  # Conflict
                            details={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )

                logger.info(
                    "Hardware creation lock acquired",
                    extra={
                        "host_id": host_id,
                        "lock_key": lock_key,
                        "lock_value": lock_value[:8] if lock_value else None,
                    },
                )

            try:
                # Create hardware: POST /api/v1/hardware/
                url_path = "/api/v1/hardware/"
                request_body = {
                    "name": "dmr_config_schema",
                    "hardware_config": hw_info.get("hardware_config", hw_info.get("dmr_config", {})),
                    "updated_by": str(user_id) if user_id else "",
                }

                logger.info(
                    "Calling external hardware API (create)",
                    extra={
                        "url_path": url_path,
                        "user_id": user_id,
                        "has_hw_info": bool(hw_info),
                        "host_id": host_id,
                    },
                )

                response = await call_external_api(
                    method="POST",
                    url_path=url_path,
                    request=request,
                    user_id=user_id,
                    json_data=request_body,
                    locale=locale,
                )

                # Determine if request succeeded: check response header :status or response body code is 200
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
                    raise BusinessError(
                        message=f"Hardware API call failed (create): {error_msg}",
                        message_key="error.hardware.create_failed",
                        error_code="HARDWARE_CREATE_FAILED",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=500,
                        details={
                            "url_path": url_path,
                            "status_header": status_header,
                            "status_code": status_code,
                            "body_code": body_code,
                            "response": response_body,
                        },
                    )

                # Extract hardware_id and host_name from response
                # Return format: {"_id": "hardware_id", "host_name": "host_name"}
                if isinstance(response_body, dict):
                    # Directly extract _id field
                    new_hardware_id = response_body.get("_id")
                    if not new_hardware_id:
                        # If _id doesn't exist, try other field names
                        new_hardware_id = response_body.get("hardware_id") or response_body.get("id")

                    if not new_hardware_id:
                        raise BusinessError(
                            message="Hardware API returned data format error: missing _id field",
                            message_key="error.hardware.invalid_response",
                            error_code="HARDWARE_INVALID_RESPONSE",
                            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                            http_status_code=500,
                        )

                    # Extract host_name (at response body top level, same level as _id)
                    host_name = response_body.get("host_name")
                    # Validate host_name is not empty string or None
                    if host_name and isinstance(host_name, str):
                        host_name = host_name.strip() if host_name.strip() else None
                    else:
                        host_name = None

                    logger.info(
                        "Hardware API call succeeded (create)",
                        extra={
                            "hardware_id": new_hardware_id,
                            "host_name": host_name,
                            "host_id": host_id,
                        },
                    )
                    return {"hardware_id": str(new_hardware_id), "host_name": host_name}
                raise BusinessError(
                    message="Hardware API returned data format error: response is not JSON format",
                    message_key="error.hardware.invalid_response",
                    error_code="HARDWARE_INVALID_RESPONSE",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                )
            finally:
                # Release lock
                if lock_key and lock_value:
                    lock_released = await redis_manager.release_lock(lock_key, lock_value)
                    if lock_released:
                        logger.debug(
                            "Hardware creation lock released",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
                    else:
                        logger.warning(
                            "Failed to release hardware creation lock",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )

        else:
            # Update hardware: PUT /api/v1/hardware/{hardware_id}
            # ✅ At this point hardware_id must not be None and not empty string (checked by is_valid_hardware_id)
            assert hardware_id is not None and hardware_id.strip(), "hardware_id must be valid"
            valid_hardware_id: str = hardware_id.strip()

            url_path = f"/api/v1/hardware/{valid_hardware_id}"
            request_body = {
                "hardware_config": hw_info.get("hardware_config", hw_info.get("dmr_config", {})),
                "updated_by": str(user_id) if user_id else "",
            }

            logger.info(
                "Calling external hardware API (update)",
                extra={
                    "url_path": url_path,
                    "hardware_id": valid_hardware_id,
                    "user_id": user_id,
                    "has_hw_info": bool(hw_info),
                },
            )

            response = await call_external_api(
                method="PUT",
                url_path=url_path,
                request=request,
                user_id=user_id,
                json_data=request_body,
                locale=locale,
            )

            # Determine if request succeeded: check response header :status or response body code is 200
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
                raise BusinessError(
                    message=f"Hardware API call failed (update): {error_msg}",
                    message_key="error.hardware.update_failed",
                    error_code="HARDWARE_UPDATE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "url_path": url_path,
                        "hardware_id": valid_hardware_id,
                        "status_header": status_header,
                        "status_code": status_code,
                        "body_code": body_code,
                        "response": response_body,
                    },
                )

            # Extract host_name (if response contains)
            host_name = None
            if isinstance(response_body, dict):
                host_name = response_body.get("host_name")
                # Validate host_name is not empty string or None
                if host_name and isinstance(host_name, str):
                    host_name = host_name.strip() if host_name.strip() else None
                else:
                    host_name = None

            logger.info(
                "Hardware API call succeeded (update)",
                extra={
                    "hardware_id": valid_hardware_id,
                    "host_name": host_name,
                },
            )
            return {"hardware_id": valid_hardware_id, "host_name": host_name}

    except BusinessError:
        raise
    except Exception as e:
        logger.error(
            "Hardware API call exception",
            extra={
                "hardware_id": hardware_id,
                "user_id": user_id,
                "has_hw_info": bool(hw_info),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise BusinessError(
            message=f"Hardware API call exception: {e!s}",
            message_key="error.hardware.api_error",
            error_code="HARDWARE_API_ERROR",
            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
            http_status_code=500,
            details={
                "hardware_id": hardware_id,
                "error": str(e),
            },
        )
