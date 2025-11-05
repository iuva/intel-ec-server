"""管理后台 OTA 管理 API 端点

提供管理后台使用的 OTA 配置管理 HTTP API 接口。
"""

import os
import sys

from fastapi import APIRouter, Depends

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_admin_ota_service, get_current_user
    from app.schemas.host import AdminOtaConfigInfo, AdminOtaListResponse
    from app.services.admin_ota_service import AdminOtaService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_ota_service, get_current_user
    from app.schemas.host import AdminOtaConfigInfo, AdminOtaListResponse
    from app.services.admin_ota_service import AdminOtaService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=SuccessResponse,
    summary="查询 OTA 配置列表",
    description="查询 sys_conf 表中 conf_key = 'ota', state_flag = 0, del_flag = 0 的全部数据",
    responses={
        200: {
            "description": "查询成功",
            "model": AdminOtaListResponse,
        },
    },
)
@handle_api_errors
async def list_ota_configs(
    admin_ota_service: AdminOtaService = Depends(get_admin_ota_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """查询 OTA 配置列表（管理后台）

    业务逻辑：
    - 查询 sys_conf 表
    - 条件：conf_key = "ota", state_flag = 0, del_flag = 0
    - 返回：conf_ver, conf_name, conf_val, conf_json 数据列表

    ## 返回字段
    - `ota_configs`: OTA 配置列表，每个配置包含：
        - `id`: 配置ID（主键）
        - `conf_ver`: 配置版本号
        - `conf_name`: 配置名称
        - `conf_val`: 配置值
        - `conf_json`: 配置 JSON
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
            "user_id": current_user.get("user_id"),
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

    return SuccessResponse(
        data=response_data.model_dump(),
        message="查询 OTA 配置列表成功",
    )
