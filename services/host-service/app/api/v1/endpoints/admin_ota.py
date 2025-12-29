"""管理后台 OTA 管理 API 端点

提供管理后台使用的 OTA 配置管理 HTTP API 接口。
"""

import os
import sys

from fastapi import APIRouter, Body, Depends

# 使用 try-except 方式处理路径导入
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
    summary="查询 OTA 配置列表",
    description="查询 sys_conf 表中 conf_key = 'ota', state_flag = 0, del_flag = 0 的全部数据",
    responses={
        200: {
            "description": "查询成功",
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
    """查询 OTA 配置列表（管理后台）

    业务逻辑：
    - 查询 sys_conf 表
    - 条件：conf_key = "ota", state_flag = 0, del_flag = 0
    - 返回：conf_ver, conf_name, conf_url, conf_md5 数据列表

    ## 返回字段
    - `ota_configs`: OTA 配置列表，每个配置包含：
        - `id`: 配置ID（主键）
        - `conf_ver`: 配置版本号
        - `conf_name`: 配置名称
        - `conf_url`: OTA 包下载地址
        - `conf_md5`: OTA 包 MD5 校验值
    - `total`: 配置总数

    Args:
        admin_ota_service: 管理后台 OTA 服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含 OTA 配置列表和总数
    """
    logger.info(
        "查询 OTA 配置列表",
        extra={
            "operation": "list_ota_configs",
            "user_id": current_user.get("id"),
            "username": current_user.get("username"),
        },
    )

    # 调用服务层查询 OTA 配置列表
    ota_configs_dict = await admin_ota_service.list_ota_configs()

    # 将字典列表转换为 Pydantic 模型对象列表
    ota_configs = [AdminOtaConfigInfo(**config) for config in ota_configs_dict]

    # 构建响应数据
    response_data = AdminOtaListResponse(
        ota_configs=ota_configs,
        total=len(ota_configs),
    )

    logger.info(
        "OTA 配置列表查询成功",
        extra={
            "operation": "list_ota_configs",
            "total": len(ota_configs),
        },
    )

    return create_success_result(
        data=response_data,
        message_key="success.ota.list_query",
        locale=locale,
        default_message="查询OTA配置列表成功",
    )


@router.post(
    "/deploy",
    response_model=Result[AdminOtaDeployResponse],
    summary="下发 OTA 配置",
    description="下发 OTA 配置到所有连接的 Host，更新 sys_conf 表并广播消息",
    responses={
        200: {
            "description": "下发成功",
            "model": Result[AdminOtaDeployResponse],
        },
        404: {
            "description": "OTA 配置不存在",
        },
    },
)
@handle_api_errors
async def deploy_ota_config(
    deploy_data: AdminOtaDeployRequest = Body(..., description="OTA 下发请求数据"),
    admin_ota_service: AdminOtaService = Depends(get_admin_ota_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminOtaDeployResponse]:
    """下发 OTA 配置（管理后台）

    业务逻辑：
    1. 更新 sys_conf 表：根据 id 更新 conf_ver, conf_name, conf_json（包含 conf_url 和 conf_md5）
    2. 通过 websocket 广播消息：conf_ver、conf_url、conf_md5 到所有 host
    3. 注册回调处理器：当 host websocket 回调通知时，在 host_upd 表新增记录

    ## 请求参数
    - `id`: 配置ID（主键，必填）
    - `conf_ver`: 配置版本号（必填）
    - `conf_name`: 配置名称（必填）
    - `conf_url`: OTA 包下载地址（必填）
    - `conf_md5`: OTA 包 MD5（必填）

    ## 返回字段
    - `id`: 配置ID（主键）
    - `conf_ver`: 配置版本号
    - `conf_name`: 配置名称
    - `conf_url`: OTA 包下载地址
    - `conf_md5`: OTA 包 MD5
    - `broadcast_count`: 广播消息成功发送的主机数量

    Args:
        deploy_data: OTA 下发请求数据
        admin_ota_service: 管理后台 OTA 服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含下发结果
    """
    logger.info(
        "下发 OTA 配置",
        extra={
            "operation": "deploy_ota_config",
            "config_id": deploy_data.id,
            "conf_ver": deploy_data.conf_ver,
            "conf_name": deploy_data.conf_name,
            "user_id": current_user.get("id"),
            "username": current_user.get("username"),
        },
    )

    # 获取操作人ID（从当前用户信息中获取）
    operator_id = None
    user_id = current_user.get("id")
    if user_id:
        try:
            operator_id = int(user_id)
        except (ValueError, TypeError):
            logger.warning(f"无法解析用户ID为整数: {user_id}")

    # 调用服务层下发 OTA 配置
    deploy_result = await admin_ota_service.deploy_ota_config(
        config_id=deploy_data.id,
        conf_ver=deploy_data.conf_ver,
        conf_name=deploy_data.conf_name,
        conf_url=str(deploy_data.conf_url),
        conf_md5=deploy_data.conf_md5,
        operator_id=operator_id,
    )

    # 构建响应数据
    response_data = AdminOtaDeployResponse(
        id=deploy_result["id"],
        conf_ver=deploy_result["conf_ver"],
        conf_name=deploy_result["conf_name"],
        conf_url=deploy_result["conf_url"],
        conf_md5=deploy_result["conf_md5"],
        broadcast_count=deploy_result["broadcast_count"],
    )

    logger.info(
        "OTA 配置下发成功",
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
        default_message="OTA配置下发成功",
    )
