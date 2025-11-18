"""管理后台主机管理 API 端点

提供管理后台使用的主机管理 HTTP API 接口。
"""

import os
import sys

from fastapi import APIRouter, Body, Depends, Path
from starlette.status import HTTP_200_OK

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostDetailRequest,
        AdminHostDetailResponse,
        AdminHostDisableRequest,
        AdminHostDisableResponse,
        AdminHostExecLogListRequest,
        AdminHostExecLogListResponse,
        AdminHostForceOfflineRequest,
        AdminHostForceOfflineResponse,
        AdminHostListRequest,
        AdminHostListResponse,
        AdminHostUpdatePasswordRequest,
        AdminHostUpdatePasswordResponse,
    )
    from app.services.admin_host_service import AdminHostService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import (
        AdminHostDeleteResponse,
        AdminHostDetailRequest,
        AdminHostDetailResponse,
        AdminHostDisableRequest,
        AdminHostDisableResponse,
        AdminHostExecLogListRequest,
        AdminHostExecLogListResponse,
        AdminHostForceOfflineRequest,
        AdminHostForceOfflineResponse,
        AdminHostListRequest,
        AdminHostListResponse,
        AdminHostUpdatePasswordRequest,
        AdminHostUpdatePasswordResponse,
    )
    from app.services.admin_host_service import AdminHostService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=Result[AdminHostListResponse],
    summary="查询可用 host 主机列表",
    description="分页查询可用主机列表，支持多种搜索条件",
    responses={
        200: {
            "description": "查询成功",
            "model": Result[AdminHostListResponse],
        },
    },
)
@handle_api_errors
async def list_hosts(
    request: AdminHostListRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostListResponse]:
    """查询可用主机列表（管理后台）

    业务逻辑：
    - 查询 host_rec 表，条件：host_state = 0, appr_state = 1, del_flag = 0
    - 关联 host_exec_log 表，获取每个 host_id 的最新一条记录（按 created_time 倒序）
    - 按 host_rec.created_time 倒序排序

    ## 搜索条件（可选）
    - `mac`: MAC地址（对应 host_rec.mac_addr）
    - `username`: 主机账号（对应 host_rec.host_acct）
    - `mg_id`: 唯一引导ID（对应 host_rec.mg_id）
    - `use_by`: 使用人（对应 host_exec_log.user_name）

    注意：此接口固定查询 `host_state = 0` 的记录，不支持通过参数修改

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
        AdminHostListSuccessResponse: 包含主机列表和分页信息
    """
    logger.info(
        "接收管理后台可用主机列表查询请求",
        extra={
            "page": request.page,
            "page_size": request.page_size,
            "mac": request.mac,
            "username": request.username,
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

    # 使用包装响应模型，确保 Swagger 文档能正确展示 Schema
    message = t(
        "success.host.list_query",
        locale=locale,
        default="查询主机列表成功",
    )

    return Result(
        code=200,
        message=message,
        data=response_data,
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
                        "data": {"id": "123"},
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
    host_id: int = Path(..., description="主机ID（host_rec.id）", ge=1),
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
                            "id": "123",
                            "appr_state": 0,
                            "host_state": 7,
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
    request: AdminHostDisableRequest = Body(..., description="主机停用请求数据"),
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

    return SuccessResponse(
        data=AdminHostDisableResponse(
            id=result["id"],
            appr_state=result["appr_state"],
            host_state=result["host_state"],
        ).model_dump(),
        message_key="success.host.disable",
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
                            "id": "123",
                            "host_state": 4,
                            "websocket_notified": True,
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
    request: AdminHostForceOfflineRequest = Body(..., description="主机强制下线请求数据"),
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

    return SuccessResponse(
        data=AdminHostForceOfflineResponse(
            id=result["id"],
            host_state=result["host_state"],
            websocket_notified=result["websocket_notified"],
        ).model_dump(),
        message_key="success.host.force_offline",
        locale=locale,
    )


@router.get(
    "/detail",
    response_model=Result[AdminHostDetailResponse],
    summary="查询主机详情",
    description="查询可用主机的详细信息（主体信息）",
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "查询主机详情成功",
                        "data": {
                            "mg_id": "machine-guid-123",
                            "mac": "00:11:22:33:44:55",
                            "ip": "192.168.1.100",
                            "username": "admin",
                            "***REMOVED***word": "***REMOVED***",
                            "port": 5900,
                            "hw_info": {"cpu": "Intel i7", "memory": "16GB"},
                            "appr_time": "2025-01-15T10:00:00Z",
                        },
                    }
                }
            },
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
async def get_host_detail(
    request: AdminHostDetailRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostDetailResponse]:
    """查询主机详情（主体信息）

    业务逻辑：
    1. 查询 host_rec 表的基础信息
    2. 关联 host_hw_rec 表，获取 sync_state=2 的列表数据，按 updated_time 倒序排序
    3. 返回主机详情（包含硬件信息列表）
    4. 密码字段需要解密（AES加密）

    ## 返回字段
    - `mg_id`: 唯一引导ID（host_rec 表 mg_id）
    - `mac`: MAC地址（host_rec 表 mac_addr）
    - `ip`: IP地址（host_rec 表 host_ip）
    - `username`: 主机账号（host_rec 表 host_acct）
    - `***REMOVED***word`: 主机密码（host_rec 表 host_pwd，已解密）
    - `port`: 端口（host_rec 表 host_port）
    - `hw_list`: 硬件信息列表（host_hw_rec 表 sync_state=2 的记录，按 updated_time 倒序）
      - `hw_info`: 硬件信息（host_hw_rec 表 hw_info）
      - `appr_time`: 审批时间（host_hw_rec 表 appr_time）

    Args:
        request: 包含主机ID的请求对象
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        AdminHostDetailSuccessResponse: 包含主机详情的响应

    Raises:
        BusinessError: 主机不存在时
    """
    logger.info(
        "接收管理后台主机详情查询请求",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层查询
    detail = await admin_host_service.get_host_detail(request.host_id)

    logger.info(
        "管理后台主机详情查询完成",
        extra={
            "host_id": request.host_id,
            "hw_list_count": len(detail.get("hw_list", [])),
            "user_id": current_user.get("user_id"),
        },
    )

    # 构建响应数据
    detail_response = AdminHostDetailResponse(
        mg_id=detail.get("mg_id"),
        mac=detail.get("mac"),
        ip=detail.get("ip"),
        username=detail.get("username"),
        ***REMOVED***word=detail.get("***REMOVED***word"),
        port=detail.get("port"),
        hw_list=detail.get("hw_list", []),
    )

    # 使用包装响应模型，确保 Swagger 文档能正确展示 Schema
    message = t(
        "success.host.detail_query",
        locale=locale,
        default="查询主机详情成功",
    )

    return Result(
        code=200,
        message=message,
        data=detail_response,
        locale=locale,
    )


@router.put(
    "/***REMOVED***word",
    response_model=SuccessResponse,
    summary="修改主机密码",
    description="修改主机密码（AES加密后存储）",
    responses={
        200: {
            "description": "密码修改成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "主机密码修改成功",
                        "data": {
                            "id": "123",
                        },
                    }
                }
            },
        },
        400: {
            "description": "密码修改失败（业务错误）",
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
                        "***REMOVED***word_update_failed": {
                            "summary": "密码修改失败",
                            "value": {
                                "code": 53006,
                                "message": "主机密码修改失败，记录可能已被删除（ID: 123）",
                                "error_code": "HOST_PASSWORD_UPDATE_FAILED",
                            },
                        },
                        "***REMOVED***word_encrypt_failed": {
                            "summary": "密码加密失败",
                            "value": {
                                "code": 53007,
                                "message": "密码加密失败（ID: 123）",
                                "error_code": "PASSWORD_ENCRYPT_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def update_host_***REMOVED***word(
    request: AdminHostUpdatePasswordRequest = Body(..., description="主机密码修改请求数据"),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """修改主机密码

    业务逻辑：
    1. 检查主机是否存在且未删除
    2. 对接收到的明文密码进行 AES 加密
    3. 更新 host_rec 表的 host_pwd 字段为加密后的密码

    Args:
        request: 包含主机ID和明文密码的请求对象
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 密码修改成功响应

    Raises:
        BusinessError: 主机不存在、密码加密失败或更新失败时
    """
    logger.info(
        "接收管理后台主机密码修改请求",
        extra={
            "host_id": request.host_id,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层修改密码
    result = await admin_host_service.update_host_***REMOVED***word(request.host_id, request.***REMOVED***word)

    logger.info(
        "管理后台主机密码修改完成",
        extra={
            "host_id": result["id"],
            "user_id": current_user.get("user_id"),
        },
    )

    return SuccessResponse(
        data=AdminHostUpdatePasswordResponse(
            id=result["id"],
        ).model_dump(),
        message_key="success.host.***REMOVED***word_update",
        locale=locale,
    )


@router.get(
    "/exec-logs",
    response_model=Result[AdminHostExecLogListResponse],
    summary="查询主机执行日志列表",
    description="分页查询主机执行日志列表（按创建时间倒序）",
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "查询执行日志成功",
                        "data": {
                            "logs": [
                                {
                                    "exec_date": "2025-01-15",
                                    "exec_time": "01:30:45",
                                    "tc_id": "test_case_001",
                                    "use_by": "user123",
                                    "case_state": 2,
                                    "result_msg": "执行成功",
                                    "log_url": "http://example.com/logs/123.log",
                                }
                            ],
                            "total": 100,
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 5,
                            "has_next": True,
                            "has_prev": False,
                        },
                    }
                }
            },
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
async def list_host_exec_logs(
    request: AdminHostExecLogListRequest = Depends(),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[AdminHostExecLogListResponse]:
    """查询主机执行日志列表（分页）

    业务逻辑：
    1. 根据 host_id 查询 host_exec_log 表
    2. 条件：del_flag = 0
    3. 按 created_time 倒序排序
    4. 计算 exec_date（begin_time 的日期部分，格式 %Y-%m-%d）
    5. 计算 exec_time（end_time - begin_time，格式 %H:%M:%S，如果 end_time 为空，使用当前时间）

    ## 返回字段
    - `exec_date`: 执行日期（格式：%Y-%m-%d）
    - `exec_time`: 执行时长（格式：%H:%M:%S）
    - `tc_id`: 执行测试ID（host_exec_log 表 tc_id）
    - `use_by`: 使用人（host_exec_log 表 user_name）
    - `case_state`: 执行状态（0-空闲, 1-启动, 2-成功, 3-失败）
    - `result_msg`: 执行结果（host_exec_log 表 result_msg）
    - `log_url`: 执行日志地址（host_exec_log 表 log_url）

    Args:
        request: 查询请求参数（host_id、分页参数）
        admin_host_service: 管理后台主机服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含执行日志列表和分页信息

    Raises:
        BusinessError: 查询失败时
    """
    logger.info(
        "接收管理后台主机执行日志列表查询请求",
        extra={
            "host_id": request.host_id,
            "page": request.page,
            "page_size": request.page_size,
            "user_id": current_user.get("user_id"),
        },
    )

    # 调用服务层查询
    logs, pagination = await admin_host_service.list_host_exec_logs(request)

    # 构建响应数据
    response_data = AdminHostExecLogListResponse(
        logs=logs,
        total=pagination.total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=pagination.total_pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev,
    )

    logger.info(
        "管理后台主机执行日志列表查询完成",
        extra={
            "host_id": request.host_id,
            "total": pagination.total,
            "returned_count": len(logs),
            "page": pagination.page,
            "page_size": pagination.page_size,
            "user_id": current_user.get("user_id"),
        },
    )

    return Result(
        code=200,
        message=t("success.host.exec_log_list_query", locale=locale, default="查询执行日志列表成功"),
        data=response_data,
        locale=locale,
    )
