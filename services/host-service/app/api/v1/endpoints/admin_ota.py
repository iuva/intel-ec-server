"""Admin backend OTA management API endpoints

Provides HTTP API interfaces for OTA configuration management used by admin backend.
"""

import os
import sys

from fastapi import APIRouter, Body, Depends

# Use try-except to handle path imports
try:
    from app.api.v1.dependencies import get_admin_ota_service, get_current_user
    from app.schemas.host import (
        AdminOtaConfigInfo,
        AdminOtaDeployRequest,
        AdminOtaDeployResponse,
        AdminOtaListResponse,
    )
    from app.services.admin_ota_service import AdminOtaService
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_ota_service, get_current_user
    from app.schemas.host import (
        AdminOtaConfigInfo,
        AdminOtaDeployRequest,
        AdminOtaDeployResponse,
        AdminOtaListResponse,
    )
    from app.services.admin_ota_service import AdminOtaService
    from app.utils.response_helpers import create_success_result
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=Result[AdminOtaListResponse],
    summary="Query OTA configuration list",
    description="Query all data from sys_conf table where conf_key = 'ota', state_flag = 0, del_flag = 0",
    responses={
        200: {
            "description": "Query succeeded",
            "model": Result[AdminOtaListResponse],
        },
    },
)
@handle_api_errors
async def list_ota_configs(
    admin_ota_service: AdminOtaService = Depends(get_admin_ota_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminOtaListResponse]:
    """Query OTA configuration list (admin backend)

    Business logic:
    - Query sys_conf table
    - Conditions: conf_key = "ota", state_flag = 0, del_flag = 0
    - Returns: conf_ver, conf_name, conf_url, conf_md5 data list

    ## Return fields
    - `ota_configs`: OTA configuration list, each configuration contains:
        - `id`: Configuration ID (primary key)
        - `conf_ver`: Configuration version number
        - `conf_name`: Configuration name
        - `conf_url`: OTA package download URL
        - `conf_md5`: OTA package MD5 checksum
    - `total`: Total number of configurations

    Args:
        admin_ota_service: Admin backend OTA service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Contains OTA configuration list and total count
    """
    logger.info(
        "Query OTA configuration list",
        extra={
            "operation": "list_ota_configs",
            "user_id": current_user.get("id"),
            "username": current_user.get("username"),
        },
    )

    # Call service layer to query OTA configuration list
    ota_configs_dict = await admin_ota_service.list_ota_configs()

    # Convert dictionary list to Pydantic model object list
    ota_configs = [AdminOtaConfigInfo(**config) for config in ota_configs_dict]

    # Build response data
    response_data = AdminOtaListResponse(
        ota_configs=ota_configs,
        total=len(ota_configs),
    )

    logger.info(
        "OTA configuration list query succeeded",
        extra={
            "operation": "list_ota_configs",
            "total": len(ota_configs),
        },
    )

    return create_success_result(
        data=response_data,
        message_key="success.ota.list_query",
        locale=locale,
        default_message="OTA configuration list query succeeded",
    )


@router.post(
    "/deploy",
    response_model=Result[AdminOtaDeployResponse],
    summary="Deploy OTA configuration",
    description="Deploy OTA configuration to all connected Hosts, update sys_conf table and broadcast message",
    responses={
        200: {
            "description": "Deployment succeeded",
            "model": Result[AdminOtaDeployResponse],
        },
        404: {
            "description": "OTA configuration does not exist",
        },
    },
)
@handle_api_errors
async def deploy_ota_config(
    deploy_data: AdminOtaDeployRequest = Body(..., description="OTA deployment request data"),
    admin_ota_service: AdminOtaService = Depends(get_admin_ota_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminOtaDeployResponse]:
    """Deploy OTA configuration (admin backend)

    Business logic:
    1. Update sys_conf table: Update conf_ver, conf_name, conf_json (contains conf_url and conf_md5) based on id
    2. Broadcast message via websocket: conf_ver, conf_url, conf_md5 to all hosts
    3. Register callback handler: When host websocket callback notification, add record in host_upd table

    ## Request parameters
    - `id`: Configuration ID (primary key, required)
    - `conf_ver`: Configuration version number (required)
    - `conf_name`: Configuration name (required)
    - `conf_url`: OTA package download URL (required)
    - `conf_md5`: OTA package MD5 (optional)

    ## Return fields
    - `id`: Configuration ID (primary key)
    - `conf_ver`: Configuration version number
    - `conf_name`: Configuration name
    - `conf_url`: OTA package download URL
    - `conf_md5`: OTA package MD5
    - `broadcast_count`: Number of hosts that successfully received broadcast message

    Args:
        deploy_data: OTA deployment request data
        admin_ota_service: Admin backend OTA service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Contains deployment result
    """
    logger.info(
        "Deploy OTA configuration",
        extra={
            "operation": "deploy_ota_config",
            "config_id": deploy_data.id,
            "conf_ver": deploy_data.conf_ver,
            "conf_name": deploy_data.conf_name,
            "user_id": current_user.get("id"),
            "username": current_user.get("username"),
        },
    )

    # Get operator ID (from current user information)
    operator_id = None
    user_id = current_user.get("id")
    if user_id:
        try:
            operator_id = int(user_id)
        except (ValueError, TypeError):
            logger.warning("Unable to parse user ID as integer", extra={"user_id": user_id})

    # Call service layer to deploy OTA configuration
    deploy_result = await admin_ota_service.deploy_ota_config(
        config_id=deploy_data.id,
        conf_ver=deploy_data.conf_ver,
        conf_name=deploy_data.conf_name,
        conf_url=str(deploy_data.conf_url),
        conf_md5=deploy_data.conf_md5,  # May be None
        operator_id=operator_id,
    )

    # Build response data
    response_data = AdminOtaDeployResponse(
        id=deploy_result["id"],
        conf_ver=deploy_result["conf_ver"],
        conf_name=deploy_result["conf_name"],
        conf_url=deploy_result["conf_url"],
        conf_md5=deploy_result["conf_md5"],
        broadcast_count=deploy_result["broadcast_count"],
    )

    logger.info(
        "OTA configuration deployment succeeded",
        extra={
            "operation": "deploy_ota_config",
            "config_id": deploy_result["id"],
            "broadcast_count": deploy_result["broadcast_count"],
        },
    )

    return create_success_result(
        data=response_data,
        message_key="success.ota.deploy",
        locale=locale,
        default_message="OTA configuration deployment succeeded",
    )
