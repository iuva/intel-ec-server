"""管理后台待审批主机管理 API 端点

提供管理后台使用的待审批主机管理 HTTP API 接口。
"""

import os
import sys

from fastapi import APIRouter, Depends

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_admin_appr_host_service, get_current_user
    from app.schemas.host import (
        AdminApprHostListRequest,
        AdminApprHostListResponse,
    )
    from app.services.admin_appr_host_service import AdminApprHostService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_appr_host_service, get_current_user
    from app.schemas.host import (
        AdminApprHostListRequest,
        AdminApprHostListResponse,
    )
    from app.services.admin_appr_host_service import AdminApprHostService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=SuccessResponse,
    summary="查询待审批 host 主机列表",
    description="分页查询待审批主机列表，支持多种搜索条件",
    responses={
        200: {
            "description": "查询成功",
            "model": AdminApprHostListResponse,
        },
    },
)
@handle_api_errors
async def list_appr_hosts(
    request: AdminApprHostListRequest = Depends(),
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """查询待审批主机列表（管理后台）

    业务逻辑：
    - 查询 host_rec 表，条件：host_state > 4 且 host_state < 8，appr_state != 1，del_flag = 0
    - 按 created_time 倒序排序

    ## 搜索条件（可选）
    - `mac`: MAC地址（对应 host_rec.mac_addr）
    - `mg_id`: 唯一引导ID（对应 host_rec.mg_id）
    - `host_state`: 主机状态（对应 host_rec.host_state）

    ## 返回字段
    - `host_id`: 主机ID（host_rec 表主键 id）
    - `mg_id`: 唯一引导ID（host_rec 表 mg_id）
    - `mac_addr`: MAC地址（host_rec 表 mac_addr）
    - `host_state`: 主机状态（host_rec 表 host_state）
    - `subm_time`: 申报时间（host_rec 表 subm_time）

    Args:
        request: 查询请求参数（分页、搜索条件）
        admin_appr_host_service: 管理后台待审批主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含待审批主机列表和分页信息
    """
    logger.info(
        "接收管理后台待审批主机列表查询请求",
        extra={
            "page": request.page,
            "page_size": request.page_size,
            "mac": request.mac,
            "mg_id": request.mg_id,
            "host_state": request.host_state,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层查询
    hosts, pagination = await admin_appr_host_service.list_appr_hosts(request)

    # 构建响应数据
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
        "管理后台待审批主机列表查询完成",
        extra={
            "total": pagination.total,
            "returned_count": len(hosts),
            "page": pagination.page,
            "page_size": pagination.page_size,
        },
    )

    return SuccessResponse(
        data=response_data.model_dump(),
        message_key="success.host.appr_list_query",
        locale=locale,
    )
