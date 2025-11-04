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
        AdminApprHostDetailRequest,
        AdminApprHostDetailResponse,
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
        AdminApprHostDetailRequest,
        AdminApprHostDetailResponse,
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


@router.get(
    "/detail",
    response_model=SuccessResponse,
    summary="查询待审批 host 主机详情",
    description="查询待审批主机的详细信息",
    responses={
        200: {
            "description": "查询成功",
            "model": AdminApprHostDetailResponse,
        },
        400: {
            "description": "查询失败（业务错误）",
            "content": {
                "application/json": {
                    "examples": {
                        "host_not_found": {
                            "summary": "主机不存在",
                            "value": {
                                "code": 53001,
                                "message": "主机不存在或已删除（ID: 123）",
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
) -> SuccessResponse:
    """查询待审批主机详情（管理后台）

    业务逻辑：
    - 查询 host_rec 表 id = host_id 的数据
    - 关联 host_hw_rec 表，查询 sync_state = 1 的数据
    - 按 host_hw_rec.created_time 倒序排序
    - 密码字段需要 AES 解密

    ## 返回字段
    - `mg_id`: 唯一引导ID（host_rec 表 mg_id）
    - `mac`: MAC地址（host_rec 表 mac_addr）
    - `ip`: IP地址（host_rec 表 host_ip）
    - `username`: 主机账号（host_rec 表 host_acct）
    - `***REMOVED***word`: 主机密码（host_rec 表 host_pwd，已解密）
    - `port`: 端口（host_rec 表 host_port）
    - `host_state`: 主机状态（host_rec 表 host_state）
    - `hw_list`: 硬件信息列表（host_hw_rec 表 sync_state=1 的记录，按 created_time 倒序）
      - `created_time`: 创建时间（host_hw_rec 表 created_time）
      - `hw_info`: 硬件信息（host_hw_rec 表 hw_info）

    Args:
        request: 包含主机ID的请求对象
        admin_appr_host_service: 管理后台待审批主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含待审批主机详情的响应

    Raises:
        BusinessError: 主机不存在时
    """
    logger.info(
        "接收管理后台待审批主机详情查询请求",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层查询
    detail = await admin_appr_host_service.get_appr_host_detail(request.host_id)

    logger.info(
        "管理后台待审批主机详情查询完成",
        extra={
            "host_id": request.host_id,
            "hw_list_count": len(detail.hw_list),
        },
    )

    return SuccessResponse(
        data=detail.model_dump(),
        message_key="success.host.appr_detail_query",
        locale=locale,
    )
