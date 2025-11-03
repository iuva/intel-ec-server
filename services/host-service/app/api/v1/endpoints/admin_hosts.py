"""管理后台主机管理 API 端点

提供管理后台使用的主机管理 HTTP API 接口。
"""

import os
import sys

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostListRequest,
        AdminHostListResponse,
        AdminHostUpdateApprovalRequest,
        AdminHostUpdateApprovalResponse,
    )
    from app.services.admin_host_service import AdminHostService
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostListRequest,
        AdminHostListResponse,
        AdminHostUpdateApprovalRequest,
        AdminHostUpdateApprovalResponse,
    )
    from app.services.admin_host_service import AdminHostService
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=SuccessResponse,
    summary="查询主机列表",
    description="分页查询主机列表，支持多种搜索条件和排序",
    responses={
        200: {
            "description": "查询成功",
            "model": AdminHostListResponse,
        },
    },
)
@handle_api_errors
async def list_hosts(
    request: AdminHostListRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """查询主机列表（管理后台）

    支持分页、多条件搜索和排序功能。

    ## 搜索条件（可选）
    - `mac`: MAC地址
    - `username`: 主机账号（host_acct）
    - `host_state`: 主机状态
    - `mg_id`: 唯一引导ID

    ## 排序规则
    - 默认：按创建时间倒序（created_time DESC）
    - 如果传入 `subm_time_sort`：
      - `0`: 申报时间正序（subm_time ASC）
      - `1`: 申报时间倒序（subm_time DESC）

    Args:
        request: 查询请求参数（分页、搜索条件、排序）
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含主机列表和分页信息
    """
    logger.info(
        "接收管理后台主机列表查询请求",
        extra={
            "page": request.page,
            "page_size": request.page_size,
            "mac": request.mac,
            "username": request.username,
            "host_state": request.host_state,
            "mg_id": request.mg_id,
            "subm_time_sort": request.subm_time_sort,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层查询
    hosts, pagination = await admin_host_service.list_hosts(request)

    # 构建响应数据
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
        "管理后台主机列表查询完成",
        extra={
            "total": pagination.total,
            "returned_count": len(hosts),
            "page": pagination.page,
            "page_size": pagination.page_size,
        },
    )

    return SuccessResponse(
        data=response_data.model_dump(),
        message_key="success.host.list_query",
        locale=locale,
    )


@router.delete(
    "/{host_id}",
    response_model=SuccessResponse,
    status_code=HTTP_200_OK,
    summary="删除主机",
    description="逻辑删除主机（设置 del_flag=1），并通知外部API",
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "主机删除成功",
                        "data": {"id": 123, "message": "主机删除成功"},
                    }
                }
            },
        },
        400: {
            "description": "删除失败（业务错误）",
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
                        "delete_failed": {
                            "summary": "删除失败",
                            "value": {
                                "code": 53002,
                                "message": "主机删除失败，记录可能已被删除（ID: 123）",
                                "error_code": "HOST_DELETE_FAILED",
                            },
                        },
                        "external_api_failed": {
                            "summary": "外部API通知失败",
                            "value": {
                                "code": 53003,
                                "message": "主机删除失败：外部API通知失败（ID: 123）",
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
    host_id: int,
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """删除主机（逻辑删除）

    业务逻辑：
    1. 逻辑删除 host_rec 表数据（设置 del_flag=1）
    2. 删除后同步通知外部API（TODO: 需要实现）
    3. 如果外部API通知失败，回滚数据删除操作
    4. 如果回滚失败或通知失败，返回业务错误码

    Args:
        host_id: 主机ID（host_rec.id）
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 删除成功响应

    Raises:
        BusinessError: 主机不存在、删除失败或外部API通知失败时
    """
    logger.info(
        "接收管理后台主机删除请求",
        extra={
            "host_id": host_id,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层删除
    deleted_id = await admin_host_service.delete_host(host_id)

    logger.info(
        "管理后台主机删除完成",
        extra={
            "host_id": deleted_id,
            "user_id": current_user.get("user_id"),
        },
    )

    return SuccessResponse(
        data=AdminHostDeleteResponse(id=deleted_id).model_dump(),
        message_key="success.host.delete",
        locale=locale,
    )


@router.put(
    "/approval",
    response_model=SuccessResponse,
    summary="更新主机审批状态",
    description="更新主机审批状态（停用/启用），启用前需要检查硬件审核状态",
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "主机审批状态更新成功",
                        "data": {
                            "id": 123,
                            "appr_state": 1,
                            "message": "主机审批状态更新成功",
                        },
                    }
                }
            },
        },
        400: {
            "description": "更新失败（业务错误）",
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
                        "hardware_audit_required": {
                            "summary": "需要先审核硬件",
                            "value": {
                                "code": 53012,
                                "message": "需要先审核变化硬件",
                                "error_code": "HARDWARE_AUDIT_REQUIRED",
                            },
                        },
                        "update_failed": {
                            "summary": "更新失败",
                            "value": {
                                "code": 53004,
                                "message": "主机审批状态更新失败，记录可能已被删除（ID: 123）",
                                "error_code": "HOST_UPDATE_APPROVAL_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def update_host_approval_state(
    request: AdminHostUpdateApprovalRequest,
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """更新主机审批状态（停用/启用）

    业务逻辑：
    1. 根据 host_id 更新 host_rec 表的 appr_state 字段
    2. 如果是启用操作（appr_state=1），需要先检查硬件审核状态：
       - 查询 host_hw_rec 表的最新一条记录
       - 如果 sync_state 为 1（待同步）或 3（异常），返回错误
    3. 如果主机已经是目标状态，返回友好提示

    Args:
        request: 包含主机ID和审批状态的请求对象
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 更新成功响应

    Raises:
        BusinessError: 主机不存在、需要硬件审核或更新失败时
    """
    logger.info(
        "接收管理后台主机审批状态更新请求",
        extra={
            "host_id": request.host_id,
            "appr_state": request.appr_state,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层更新
    result = await admin_host_service.update_host_approval_state(
        request.host_id, request.appr_state
    )

    logger.info(
        "管理后台主机审批状态更新完成",
        extra={
            "host_id": result["id"],
            "appr_state": result["appr_state"],
            "user_id": current_user.get("user_id"),
        },
    )

    # 检查是否已经是目标状态
    message_key = "success.host.update_approval"
    state_name = None
    if "已是" in result["message"] or "already" in result["message"].lower():
        # 提取状态名
        state_name = "启用" if request.appr_state == 1 else "停用"
        message_key = "success.host.already_in_state"
        translated_message = t(message_key, locale=locale, state_name=state_name)
    else:
        translated_message = t(message_key, locale=locale)

    return SuccessResponse(
        data=AdminHostUpdateApprovalResponse(
            id=result["id"],
            appr_state=result["appr_state"],
            message=translated_message,
        ).model_dump(),
        message_key=message_key,
        locale=locale,
        state_name=state_name,
    )
