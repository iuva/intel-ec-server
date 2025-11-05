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
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailRequest,
        AdminApprHostDetailResponse,
        AdminApprHostListRequest,
        AdminApprHostListResponse,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
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
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailRequest,
        AdminApprHostDetailResponse,
        AdminApprHostListRequest,
        AdminApprHostListResponse,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
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
    - `diff_state`: 参数状态（host_hw_rec 表 diff_state，最新一条记录；1-版本号变化, 2-内容更改, 3-异常）

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


@router.post(
    "/approve",
    response_model=SuccessResponse,
    summary="同意启用待审批 host 主机",
    description="同意启用待审批主机，更新硬件记录和主机状态",
    responses={
        200: {
            "description": "处理成功",
            "model": AdminApprHostApproveResponse,
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "examples": {
                        "host_ids_required": {
                            "summary": "host_ids 必填",
                            "value": {
                                "code": 400,
                                "message": "当 diff_type=2 时，host_ids 为必填参数",
                                "error_code": "HOST_IDS_REQUIRED",
                            },
                        },
                        "diff_type_not_supported": {
                            "summary": "diff_type 不支持",
                            "value": {
                                "code": 400,
                                "message": "diff_type=1（版本号变化）暂不支持",
                                "error_code": "DIFF_TYPE_NOT_SUPPORTED",
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "examples": {
                        "approve_failed": {
                            "summary": "同意启用失败",
                            "value": {
                                "code": 500,
                                "message": "同意启用主机失败: 数据库操作异常",
                                "error_code": "APPROVE_HOST_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def approve_hosts(
    request: AdminApprHostApproveRequest,
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """同意启用待审批主机（管理后台）

    业务逻辑（diff_type = 2 时）：
    - 查询所有 host_hw_rec 表 host_id = id, sync_state = 1 的数据
    - 最新一条数据：sync_state = 2, appr_time = now(), appr_by = token 中的 id
    - 其他数据：sync_state = 4
    - 修改 host_rec 表：appr_state = 1, host_state = 0, hw_id = host_hw_rec 最新一条数据的 id, subm_time = now()
    - TODO: 调用外部 API 同步 host_hw_rec 最新数据的 hw_info

    ## 请求参数
    - `diff_type`: 变更类型（1-版本号变化, 2-内容变化）
    - `host_ids`: 主机ID列表（当 diff_type=2 时必填）

    ## 返回字段
    - `success_count`: 成功处理的主机数量
    - `failed_count`: 失败的主机数量
    - `results`: 处理结果详情（包含成功和失败的记录）

    Args:
        request: 同意启用请求参数
        admin_appr_host_service: 管理后台待审批主机服务实例
        current_user: 当前用户信息（包含 user_id）
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含处理结果和统计信息

    Raises:
        BusinessError: 参数验证失败或业务逻辑错误时
    """
    logger.info(
        "接收管理后台同意启用主机请求",
        extra={
            "diff_type": request.diff_type,
            "host_ids": request.host_ids,
            "host_count": len(request.host_ids or []),
            "user_id": current_user.get("user_id"),
        },
    )

    # 获取当前用户ID
    appr_by = current_user.get("user_id")
    if not appr_by:
        logger.warning(
            "无法获取当前用户ID",
            extra={
                "current_user": current_user,
            },
        )
        appr_by = 0  # 如果无法获取用户ID，使用默认值

    # 调用服务层处理
    result = await admin_appr_host_service.approve_hosts(request, appr_by)

    logger.info(
        "管理后台同意启用主机处理完成",
        extra={
            "diff_type": request.diff_type,
            "success_count": result.success_count,
            "failed_count": result.failed_count,
            "total_count": result.success_count + result.failed_count,
        },
    )

    return SuccessResponse(
        data=result.model_dump(),
        message_key="success.host.approve_completed",
        locale=locale,
    )


@router.post(
    "/maintain-email",
    response_model=SuccessResponse,
    summary="设置维护通知邮箱",
    description="设置维护通知邮箱，多个邮箱以半角逗号分割",
    responses={
        200: {
            "description": "设置成功",
            "model": AdminMaintainEmailResponse,
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "examples": {
                        "email_empty": {
                            "summary": "邮箱地址为空",
                            "value": {
                                "code": 400,
                                "message": "邮箱地址不能为空",
                                "error_code": "EMAIL_EMPTY",
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "examples": {
                        "set_failed": {
                            "summary": "设置失败",
                            "value": {
                                "code": 500,
                                "message": "设置维护通知邮箱失败: 数据库操作异常",
                                "error_code": "SET_MAINTAIN_EMAIL_FAILED",
                            },
                        },
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def set_maintain_email(
    request: AdminMaintainEmailRequest,
    admin_appr_host_service: AdminApprHostService = Depends(get_admin_appr_host_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """设置维护通知邮箱（管理后台）

    业务逻辑：
    1. 格式化邮箱：去除空格，全角逗号转为半角逗号
    2. 查询 sys_conf 表，conf_key = "email"
    3. 如果不存在则插入，如果存在则更新 conf_val

    ## 请求参数
    - `email`: 邮箱地址（多个邮箱以半角逗号分割）

    ## 返回字段
    - `conf_key`: 配置键（固定为 "email"）
    - `conf_val`: 配置值（格式化后的邮箱地址）
    - `message`: 操作结果消息

    Args:
        request: 维护通知邮箱设置请求参数
        admin_appr_host_service: 管理后台待审批主机服务实例
        current_user: 当前用户信息（包含 user_id）
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含设置结果

    Raises:
        BusinessError: 参数验证失败或数据库操作失败时
    """
    logger.info(
        "接收管理后台维护通知邮箱设置请求",
        extra={
            "email": request.email,
            "user_id": current_user.get("user_id"),
        },
    )

    # 获取当前用户ID
    operator_id = current_user.get("user_id")
    if not operator_id:
        logger.warning(
            "无法获取当前用户ID",
            extra={
                "current_user": current_user,
            },
        )
        operator_id = 0  # 如果无法获取用户ID，使用默认值

    # 调用服务层处理
    result = await admin_appr_host_service.set_maintain_email(request, operator_id)

    logger.info(
        "管理后台维护通知邮箱设置完成",
        extra={
            "conf_key": result.conf_key,
            "conf_val": result.conf_val,
            "operator_id": operator_id,
        },
    )

    return SuccessResponse(
        data=result.model_dump(),
        message_key="success.email.set_completed",
        locale=locale,
    )
