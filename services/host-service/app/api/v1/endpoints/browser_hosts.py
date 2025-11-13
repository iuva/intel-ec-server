"""浏览器插件主机管理 API 端点

提供浏览器插件使用的主机查询相关的 API 端点。
"""

import os
import sys

from app.api.v1.dependencies import get_host_discovery_service, get_host_service
from app.schemas.host import (
    QueryAvailableHostsRequest,
    ReleaseHostsRequest,
    ReleaseHostsResponse,
    RetryVNCListResponse,
)
from app.services.browser_host_service import BrowserHostService
from fastapi import APIRouter, Body, Depends

# 使用 try-except 方式处理路径导入
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

from app.services.host_discovery_service import HostDiscoveryService

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/available",
    response_model=SuccessResponse,
    summary="查询可用主机列表",
    description="查询可用的主机列表，支持游标分页",
    responses={
        200: {
            "description": "查询成功",
            "model": SuccessResponse,
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "请求参数无效",
                        "error_code": "INVALID_PARAMS",
                    }
                }
            },
        },
        405: {
            "description": "HTTP 方法不允许",
            "content": {
                "application/json": {
                    "example": {
                        "code": 405,
                        "message": "此接口仅支持 POST 方法，请使用 POST 请求",
                        "error_code": "METHOD_NOT_ALLOWED",
                    }
                }
            },
        },
        503: {
            "description": "外部服务不可用",
            "content": {
                "application/json": {
                    "example": {
                        "code": 503,
                        "message": "硬件接口调用失败，请稍后重试",
                        "error_code": "HARDWARE_API_ERROR",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def query_available_hosts(
    request: QueryAvailableHostsRequest = Body(..., description="查询可用主机列表请求参数"),
    host_discovery_service: HostDiscoveryService = Depends(get_host_discovery_service),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """查询可用的主机列表 - 游标分页

    ## 请求参数说明
    - `tc_id`: 测试用例 ID（必填）
    - `cycle_name`: 测试周期名称（必填）
    - `user_name`: 用户名（必填）
    - `page_size`: 每页大小，1-100（可选，默认 20）
    - `last_id`: 上一页最后一条记录的 id（可选）

    ## 游标分页说明
    1. **首次请求**: 不提供 last_id 或传入 null，从头开始查询
    2. **后续请求**: 从响应中获取 last_id，传入下一次请求
    3. **避免并发污染**: 每个用户的请求独立处理
    4. **性能优化**: 使用游标比基于 page 的分页更高效

    ## 业务逻辑
    1. 调用外部硬件接口获取主机列表（分页获取）
    2. 根据 hardware_id 查询本地 host_rec 表
    3. 过滤条件：
       - appr_state = 1（启用状态）
       - host_state = 0（空闲状态）
       - del_flag = 0（未删除）
    4. 根据 last_id 跳过已处理的记录
    5. 收集满足 page_size 数量的结果后返回

    ## 返回数据说明
    - `hosts`: 可用主机列表
    - `total`: 本次查询发现的可用主机总数
    - `page_size`: 每页大小
    - `has_next`: 是否有下一页
    - `last_id`: 当前页最后一条记录的 id，用于请求下一页

    Args:
        request: 查询请求（游标分页）
        host_discovery_service: 主机发现服务实例

    Returns:
        可用主机列表（包含 has_next 和 last_id 用于下一页请求）
    """
    logger.info(
        "接收查询可用主机列表请求",
        extra={
            "tc_id": request.tc_id,
            "cycle_name": request.cycle_name,
            "user_name": request.user_name,
            "page_size": request.page_size,
            "last_id": request.last_id,
        },
    )

    result = await host_discovery_service.query_available_hosts(request)

    logger.info(
        "查询可用主机列表完成",
        extra={
            "tc_id": request.tc_id,
            "total_available": result.total,
            "page_size": result.page_size,
            "has_next": result.has_next,
            "returned_count": len(result.hosts),
            "last_id": result.last_id,
        },
    )

    return SuccessResponse(
        data=result.model_dump(),
        message_key="success.host.available_list_query",
        locale=locale,
    )


@router.post(
    "/retry-vnc",
    response_model=RetryVNCListResponse,
    summary="获取重试 VNC 列表",
    description="查询需要重试的 VNC 连接列表（case_state != 2 的主机）",
    responses={
        200: {
            "description": "查询成功",
            "model": RetryVNCListResponse,
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "请求参数无效",
                        "error_code": "INVALID_PARAMS",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_retry_vnc_list(
    user_id: str = Body(..., embed=True, description="用户ID"),
    host_service: BrowserHostService = Depends(get_host_service),
):
    """获取需要重试的 VNC 连接列表

    ## 业务逻辑
    1. 查询 `host_exec_log` 表:
       - 条件: `user_id = 入参的user_id`
       - `case_state != 2` (非成功状态)
       - `del_flag = 0` (未删除)
    2. 获取这些记录的 `host_id`
    3. 查询 `host_rec` 表对应的主机信息
    4. 返回主机信息列表

    ## 请求参数
    - `user_id`: 用户ID

    ## 返回数据
    - `hosts`: 需要重试的主机列表
      - `host_id`: 主机ID
      - `host_ip`: 主机IP
      - `user_name`: 主机账号 (host_acct)
    - `total`: 主机总数

    Args:
        user_id: 用户ID
        host_service: 主机服务实例

    Returns:
        重试 VNC 列表响应
    """
    logger.info(
        "接收获取重试 VNC 列表请求",
        extra={
            "user_id": user_id,
        },
    )

    retry_vnc_list = await host_service.get_retry_vnc_list(user_id)

    logger.info(
        "获取重试 VNC 列表完成",
        extra={
            "user_id": user_id,
            "total": len(retry_vnc_list),
        },
    )

    return RetryVNCListResponse(
        hosts=retry_vnc_list,
        total=len(retry_vnc_list),
    )


@router.post(
    "/release",
    response_model=ReleaseHostsResponse,
    summary="释放主机",
    description="逻辑删除指定用户的主机执行日志记录（设置 del_flag = 1）",
    responses={
        200: {
            "description": "释放成功",
            "model": ReleaseHostsResponse,
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "主机ID格式无效",
                        "error_code": "INVALID_HOST_ID",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def release_hosts(
    request: ReleaseHostsRequest = Body(..., description="释放主机请求数据"),
    host_service: BrowserHostService = Depends(get_host_service),
):
    """释放主机 - 逻辑删除执行日志记录

    ## 业务逻辑
    1. 逻辑删除 `host_exec_log` 表中的记录（设置 del_flag = 1）
    2. 条件：
       - `user_id = 入参的 user_id`
       - `host_id IN (host_list)`
       - `del_flag = 0`（只删除未删除的记录）

    ## 请求参数
    - `user_id`: 用户ID
    - `host_list`: 主机ID列表

    ## 返回数据
    - `updated_count`: 更新的记录数（逻辑删除）
    - `user_id`: 用户ID
    - `host_list`: 主机ID列表

    Args:
        request: 释放主机请求
        host_service: 主机服务实例

    Returns:
        释放主机响应
    """
    logger.info(
        "接收释放主机请求",
        extra={
            "user_id": request.user_id,
            "host_count": len(request.host_list),
        },
    )

    updated_count = await host_service.release_hosts(
        user_id=request.user_id,
        host_list=request.host_list,
    )

    logger.info(
        "释放主机完成",
        extra={
            "user_id": request.user_id,
            "host_count": len(request.host_list),
            "updated_count": updated_count,
        },
    )

    return ReleaseHostsResponse(
        updated_count=updated_count,
        user_id=request.user_id,
        host_list=request.host_list,
    )
