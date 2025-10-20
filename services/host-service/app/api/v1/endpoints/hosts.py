"""主机管理 API 端点"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from app.api.v1.dependencies import get_host_service
from app.schemas.host import HostCreate, HostResponse, HostStatusUpdate, HostUpdate
from app.services.host_service import HostService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=SuccessResponse,
    summary="获取主机列表",
    description="分页查询主机列表，支持按状态过滤",
)
@handle_api_errors
async def list_hosts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="主机状态过滤 (online, offline, error)"),
    host_service: HostService = Depends(get_host_service),
):
    """获取主机列表

    Args:
        page: 页码
        page_size: 每页大小
        status: 状态过滤
        host_service: 主机服务实例（依赖注入）

    Returns:
        主机列表响应
    """
    hosts, total = await host_service.list_hosts(page=page, page_size=page_size, status=status)

    # 转换为响应模型
    host_responses = [HostResponse.model_validate(host) for host in hosts]

    return SuccessResponse(
        data={
            "hosts": [host.model_dump() for host in host_responses],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="获取主机列表成功",
    )


@router.post(
    "",
    response_model=SuccessResponse,
    status_code=HTTP_201_CREATED,
    summary="注册主机",
    description="注册新的主机到系统",
)
@handle_api_errors
async def create_host(
    host_data: HostCreate,
    host_service: HostService = Depends(get_host_service),
):
    """注册主机

    Args:
        host_data: 主机创建数据
        host_service: 主机服务实例（依赖注入）

    Returns:
        创建的主机信息
    """
    host = await host_service.create_host(host_data)
    host_response = HostResponse.model_validate(host)

    return SuccessResponse(
        data=host_response.model_dump(),
        message="主机注册成功",
    )


@router.get(
    "/{host_id}",
    response_model=SuccessResponse,
    summary="获取主机详情",
    description="根据主机ID获取主机详细信息",
)
@handle_api_errors
async def get_host(
    host_id: str = Path(..., description="主机ID"),
    host_service: HostService = Depends(get_host_service),
):
    """获取主机详情

    Args:
        host_id: 主机ID
        host_service: 主机服务实例（依赖注入）

    Returns:
        主机详细信息
    """
    host = await host_service.get_host_by_id(host_id)

    if not host:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code=HTTP_404_NOT_FOUND,
                message=f"主机不存在: {host_id}",
                error_code="HOST_NOT_FOUND",
            ).model_dump(),
        )

    host_response = HostResponse.model_validate(host)

    return SuccessResponse(
        data=host_response.model_dump(),
        message="获取主机详情成功",
    )


@router.put(
    "/{host_id}",
    response_model=SuccessResponse,
    summary="更新主机信息",
    description="更新主机的基本信息",
)
@handle_api_errors
async def update_host(
    host_id: str = Path(..., description="主机ID"),
    host_data: HostUpdate = ...,
    host_service: HostService = Depends(get_host_service),
):
    """更新主机信息

    Args:
        host_id: 主机ID
        host_data: 更新数据
        host_service: 主机服务实例（依赖注入）

    Returns:
        更新后的主机信息
    """
    host = await host_service.update_host(host_id, host_data)
    host_response = HostResponse.model_validate(host)

    return SuccessResponse(
        data=host_response.model_dump(),
        message="主机信息更新成功",
    )


@router.patch(
    "/{host_id}/status",
    response_model=SuccessResponse,
    summary="更新主机状态",
    description="更新主机的运行状态",
)
@handle_api_errors
async def update_host_status(
    host_id: str = Path(..., description="主机ID"),
    status_data: HostStatusUpdate = ...,
    host_service: HostService = Depends(get_host_service),
):
    """更新主机状态

    Args:
        host_id: 主机ID
        status_data: 状态更新数据
        host_service: 主机服务实例（依赖注入）

    Returns:
        更新后的主机信息
    """
    host = await host_service.update_host_status(host_id, status_data)
    host_response = HostResponse.model_validate(host)

    return SuccessResponse(
        data=host_response.model_dump(),
        message="主机状态更新成功",
    )


@router.delete(
    "/{host_id}",
    response_model=SuccessResponse,
    summary="删除主机",
    description="删除指定的主机（软删除）",
)
@handle_api_errors
async def delete_host(
    host_id: str = Path(..., description="主机ID"),
    host_service: HostService = Depends(get_host_service),
):
    """删除主机

    Args:
        host_id: 主机ID
        host_service: 主机服务实例（依赖注入）

    Returns:
        删除结果
    """
    success = await host_service.delete_host(host_id)

    return SuccessResponse(
        data={"host_id": host_id, "deleted": success},
        message="主机删除成功",
    )
