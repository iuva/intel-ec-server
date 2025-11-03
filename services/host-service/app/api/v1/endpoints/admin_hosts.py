"""管理后台主机管理 API 端点

提供管理后台使用的主机管理 HTTP API 接口。
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_200_OK

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import AdminHostListRequest, AdminHostListResponse
    from app.services.admin_host_service import AdminHostService
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_admin_host_service, get_current_user
    from app.schemas.host import AdminHostListRequest, AdminHostListResponse
    from app.services.admin_host_service import AdminHostService
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/list",
    response_model=SuccessResponse,
    status_code=HTTP_200_OK,
    summary="查询主机列表",
    description="""
    管理后台主机列表查询接口，支持分页和多种搜索条件。

    ## 功能说明
    1. 支持分页查询（page, page_size）
    2. 支持多条件搜索：
       - MAC地址（mac）
       - 主机账号（username，对应 host_acct）
       - 主机状态（host_state）
       - 唯一引导ID（mg_id）
    3. 关联查询执行日志，获取最新执行用户名称
    4. 支持排序：默认按创建时间倒序，可选择按申报时间排序

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - 需要管理员权限

    ## 查询条件说明
    - 所有搜索条件都是可选的（可以为空）
    - 支持模糊匹配（LIKE查询）
    - 多个条件之间是 AND 关系

    ## 排序说明
    - 默认排序：按创建时间（created_time）倒序
    - 申报时间排序：传入 subm_time_sort 参数
      - `0`: 申报时间正序（从早到晚）
      - `1`: 申报时间倒序（从晚到早）
    - 如果不传入 subm_time_sort，则按创建时间倒序

    ## 返回数据说明
    - `hardware_id`: MongoDB 硬件ID
    - `host_acct`: 主机账号
    - `mg_id`: 唯一引导ID
    - `mac`: MAC地址
    - `host_state`: 主机状态
    - `user_name`: 执行用户名称（来自host_exec_log最新记录，如果存在）

    ## 执行日志关联规则
    - 查询条件：`case_state > 0 AND host_state > 0 AND del_flag = 0`
    - 取最新一条记录的 `user_name`
    - 如果没有匹配的执行日志，`user_name` 为 null
    """,
    responses={
        200: {
            "description": "查询成功",
            "model": SuccessResponse,
        },
        401: {
            "description": "认证失败",
        },
    },
)
@handle_api_errors
async def list_hosts(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小（1-100）"),
    mac: Optional[str] = Query(None, description="MAC地址（可选搜索条件）"),
    username: Optional[str] = Query(None, description="主机账号（可选搜索条件）"),
    host_state: Optional[int] = Query(None, description="主机状态（可选搜索条件）"),
    mg_id: Optional[str] = Query(None, description="唯一引导ID（可选搜索条件）"),
    subm_time_sort: Optional[int] = Query(
        None, ge=0, le=1, description="申报时间排序字段（0=正序，1=倒序，不传则按创建时间倒序）"
    ),
    admin_host_service: AdminHostService = Depends(get_admin_host_service),
    current_user: dict = Depends(get_current_user),
) -> SuccessResponse:
    """查询主机列表（管理后台）

    Args:
        page: 页码（从1开始）
        page_size: 每页大小（1-100）
        mac: MAC地址（可选）
        username: 主机账号（可选）
        host_state: 主机状态（可选）
        mg_id: 唯一引导ID（可选）
        subm_time_sort: 申报时间排序字段（0=正序，1=倒序，不传则按创建时间倒序）
        admin_host_service: 管理后台主机服务实例
        current_user: 当前登录用户信息

    Returns:
        SuccessResponse: 包含主机列表和分页信息
    """
    logger.info(
        "接收管理后台主机列表查询请求",
        extra={
            "page": page,
            "page_size": page_size,
            "mac": mac,
            "username": username,
            "host_state": host_state,
            "mg_id": mg_id,
            "subm_time_sort": subm_time_sort,
            "user_id": current_user.get("user_id"),
        },
    )

    # 构建请求参数
    request = AdminHostListRequest(
        page=page,
        page_size=page_size,
        mac=mac,
        username=username,
        host_state=host_state,
        mg_id=mg_id,
        subm_time_sort=subm_time_sort,
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
        message="查询主机列表成功",
    )
