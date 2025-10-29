"""主机管理 API 端点

提供主机查询相关的 API 端点。
"""

import os
import sys
from typing import Optional

from app.api.v1.dependencies import get_host_discovery_service
from app.schemas.host import AvailableHostsListResponse, QueryAvailableHostsRequest
from fastapi import APIRouter, Depends, Query

# 使用 try-except 方式处理路径导入
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger

from app.services.host_discovery_service import HostDiscoveryService

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/available",
    response_model=AvailableHostsListResponse,
    summary="查询可用主机列表",
    description="查询可用的主机列表，支持游标分页",
    responses={
        200: {
            "description": "查询成功",
            "model": AvailableHostsListResponse,
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
    tc_id: str = Query(..., description="测试用例 ID"),
    cycle_name: str = Query(..., description="测试周期名称"),
    user_name: str = Query(..., description="用户名"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    last_id: Optional[int] = Query(None, description="上一页最后一条记录的 id"),
    host_discovery_service: HostDiscoveryService = Depends(get_host_discovery_service),
):
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
            "tc_id": tc_id,
            "cycle_name": cycle_name,
            "user_name": user_name,
            "page_size": page_size,
            "last_id": last_id,
        },
    )

    result = await host_discovery_service.query_available_hosts(
        QueryAvailableHostsRequest(
            tc_id=tc_id,
            cycle_name=cycle_name,
            user_name=user_name,
            page_size=page_size,
            last_id=last_id,
        )
    )

    logger.info(
        "查询可用主机列表完成",
        extra={
            "tc_id": tc_id,
            "total_available": result.total,
            "page_size": result.page_size,
            "has_next": result.has_next,
            "returned_count": len(result.hosts),
            "last_id": result.last_id,
        },
    )

    return result
