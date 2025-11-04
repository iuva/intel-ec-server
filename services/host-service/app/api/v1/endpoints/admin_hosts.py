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
        AdminHostDisableRequest,
        AdminHostDisableResponse,
        AdminHostForceOfflineRequest,
        AdminHostForceOfflineResponse,
        AdminHostListRequest,
        AdminHostListResponse,
    )
    from app.services.admin_host_service import AdminHostService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostDisableRequest,
        AdminHostDisableResponse,
        AdminHostForceOfflineRequest,
        AdminHostForceOfflineResponse,
        AdminHostListRequest,
        AdminHostListResponse,
    )
    from app.services.admin_host_service import AdminHostService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=SuccessResponse,
    summary="查询可用 host 主机列表",
    description="分页查询可用主机列表，支持多种搜索条件",
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
    """查询可用主机列表（管理后台）

    业务逻辑：
    - 查询 host_rec 表，条件：host_state < 5, appr_state = 1, del_flag = 0
    - 关联 host_exec_log 表，获取每个 host_id 的最新一条记录（按 created_time 倒序）
    - 按 host_rec.created_time 倒序排序

    ## 搜索条件（可选）
    - `mac`: MAC地址（对应 host_rec.mac_addr）
    - `username`: 主机账号（对应 host_rec.host_acct）
    - `host_state`: 主机状态（对应 host_rec.host_state）
    - `mg_id`: 唯一引导ID（对应 host_rec.mg_id）
    - `use_by`: 使用人（对应 host_exec_log.user_name）

    ## 返回字段
    - `host_id`: 主机ID（host_rec 表主键 id）
    - `username`: 主机账号（host_rec 表 host_acct）
    - `mg_id`: 唯一引导ID（host_rec 表 mg_id）
    - `mac`: MAC地址（host_rec 表 mac_addr）
    - `use_by`: 使用人（host_exec_log 表 user_name，最新一条）
    - `host_state`: 主机状态（host_rec 表 host_state）
    - `appr_state`: 审批状态（host_rec 表 appr_state）

    Args:
        request: 查询请求参数（分页、搜索条件）
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含主机列表和分页信息
    """
    logger.info(
        "接收管理后台可用主机列表查询请求",
        extra={
            "page": request.page,
            "page_size": request.page_size,
            "mac": request.mac,
            "username": request.username,
            "host_state": request.host_state,
            "mg_id": request.mg_id,
            "use_by": request.use_by,
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
        "管理后台可用主机列表查询完成",
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
    "/disable",
    response_model=SuccessResponse,
    summary="停用主机",
    description="停用主机（设置 appr_state=0）",
    responses={
        200: {
            "description": "停用成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "主机停用成功",
                        "data": {
                            "id": 123,
                            "appr_state": 0,
                            "message": "主机已停用",
                        },
                    }
                }
            },
        },
        400: {
            "description": "停用失败（业务错误）",
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
                        "disable_failed": {
                            "summary": "停用失败",
                            "value": {
                                "code": 53004,
                                "message": "主机停用失败，记录可能已被删除（ID: 123）",
                                "error_code": "HOST_DISABLE_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def disable_host(
    request: AdminHostDisableRequest,
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """停用主机

    业务逻辑：
    1. 根据 host_id 更新 host_rec 表的 appr_state 字段为 0（停用）
    2. 如果主机已经是停用状态，返回友好提示

    Args:
        request: 包含主机ID的请求对象
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 停用成功响应

    Raises:
        BusinessError: 主机不存在或停用失败时
    """
    logger.info(
        "接收管理后台主机停用请求",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层停用
    result = await admin_host_service.disable_host(request.host_id)

    logger.info(
        "管理后台主机停用完成",
        extra={
            "host_id": result["id"],
            "appr_state": result["appr_state"],
            "user_id": current_user.get("user_id"),
        },
    )

    # 检查是否已经是停用状态
    message_key = "success.host.disable"
    if "已是" in result["message"]:
        message_key = "success.host.already_disabled"

    return SuccessResponse(
        data=AdminHostDisableResponse(
            id=result["id"],
            appr_state=result["appr_state"],
            message=result["message"],
        ).model_dump(),
        message_key=message_key,
        locale=locale,
    )


@router.post(
    "/force-offline",
    response_model=SuccessResponse,
    summary="强制下线主机",
    description="强制下线主机（设置 host_state=4），并通知WebSocket",
    responses={
        200: {
            "description": "强制下线成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "主机强制下线成功",
                        "data": {
                            "id": 123,
                            "host_state": 4,
                            "websocket_notified": True,
                            "message": "主机已强制下线",
                        },
                    }
                }
            },
        },
        400: {
            "description": "强制下线失败（业务错误）",
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
                        "force_offline_failed": {
                            "summary": "强制下线失败",
                            "value": {
                                "code": 53005,
                                "message": "主机强制下线失败，记录可能已被删除（ID: 123）",
                                "error_code": "HOST_FORCE_OFFLINE_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def force_offline_host(
    request: AdminHostForceOfflineRequest,
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """强制下线主机

    业务逻辑：
    1. 更新 host_rec 表的 host_state 字段为 4（离线状态）
    2. 通过 WebSocket 通知指定 host_id 的 Agent 强制下线
    3. 如果 WebSocket 通知失败，不影响数据库更新，只记录警告

    Args:
        request: 包含主机ID的请求对象
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 强制下线成功响应，包含WebSocket通知结果

    Raises:
        BusinessError: 主机不存在或更新失败时
    """
    logger.info(
        "接收管理后台主机强制下线请求",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层强制下线
    result = await admin_host_service.force_offline_host(request.host_id)

    logger.info(
        "管理后台主机强制下线完成",
        extra={
            "host_id": result["id"],
            "host_state": result["host_state"],
            "websocket_notified": result["websocket_notified"],
            "user_id": current_user.get("user_id"),
        },
    )

    # 根据WebSocket通知结果选择消息键
    message_key = "success.host.force_offline"
    if not result["websocket_notified"]:
        message_key = "success.host.force_offline_no_websocket"

    return SuccessResponse(
        data=AdminHostForceOfflineResponse(
            id=result["id"],
            host_state=result["host_state"],
            websocket_notified=result["websocket_notified"],
            message=result["message"],
        ).model_dump(),
        message_key=message_key,
        locale=locale,
    )
