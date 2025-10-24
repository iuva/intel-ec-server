"""主机管理 API 端点"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_host_service
from app.schemas.host import (
    AvailableHostsListResponse,
    GetVNCConnectionRequest,
    QueryAvailableHostsRequest,
    VNCConnectionReport,
    VNCConnectionResponse,
)
from app.services.host_service import HostService

# 使用 try-except 方式处理路径导入
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/available",
    response_model=AvailableHostsListResponse,
    summary="查询可用主机列表",
    description="查询可用的主机列表，支持分页和智能补全",
    responses={
        200: {"description": "查询成功", "model": AvailableHostsListResponse},
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
    request: QueryAvailableHostsRequest,
    host_service: HostService = Depends(get_host_service),
):
    """查询可用的主机列表 - 游标分页

    ## 请求参数说明
    - `tc_id`: 测试用例 ID（必填）
    - `cycle_name`: 测试周期名称（必填）
    - `user_name`: 用户名（必填）
    - `page_size`: 每页大小，1-100（可选，默认 20）
    - `last_id`: 上一页最后一条记录的 id。首次请求为 null，后续请求需要传入上一页最后一条记录的 host_rec_id（可选）

    ## 游标分页说明
    1. **首次请求**: 不提供 last_id 或传入 null，从头开始查询
    2. **后续请求**: 从响应中获取 last_id，传入下一次请求
    3. **避免并发污染**: 每个用户的请求独立处理，无全局状态污染
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
      - `host_rec_id`: 主机记录 ID
      - `hardware_id`: 硬件 ID
      - `user_name`: 用户名（host_acct）
      - `host_ip`: 主机 IP
      - `appr_state`: 审批状态
      - `host_state`: 主机状态
    - `total`: 本次查询发现的可用主机总数
    - `page_size`: 每页大小
    - `has_next`: 是否有下一页
    - `last_id`: 当前页最后一条记录的 id，用于请求下一页

    ## 使用示例

    ### 首次请求（无 last_id）
    ```json
    {
      "tc_id": "test-001",
      "cycle_name": "cycle-001",
      "user_name": "admin",
      "page_size": 20
    }
    ```

    响应示例：
    ```json
    {
      "code": 200,
      "message": "操作成功",
      "data": {
        "hosts": [...],
        "total": 42,
        "page_size": 20,
        "has_next": true,
        "last_id": 123
      }
    }
    ```

    ### 请求下一页（使用 last_id）
    ```json
    {
      "tc_id": "test-001",
      "cycle_name": "cycle-001",
      "user_name": "admin",
      "page_size": 20,
      "last_id": 123
    }
    ```

    Args:
        request: 查询请求（游标分页）
        host_service: 主机服务实例

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

    result = await host_service.query_available_hosts(request)

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

    return result


@router.post(
    "/plugin/report",
    response_model=SuccessResponse,
    summary="VNC连接结果上报",
    description="浏览器插件上报VNC连接结果到服务端",
    responses={
        200: {"description": "VNC连接结果上报成功", "model": SuccessResponse},
        400: {
            "description": "主机不存在或请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "主机不存在: 1852278641262084097",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "VNC连接结果上报失败",
                        "error_code": "VNC_CONNECTION_REPORT_FAILED",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_vnc_connection(
    vnc_report: VNCConnectionReport,
    host_service: HostService = Depends(get_host_service),
):
    """浏览器插件上报VNC连接结果

    ## 请求参数说明
    - user_id: 用户ID
    - host_id: 主机ID
    - connection_status: 连接状态 (success/failed)
    - connection_time: 连接时间 (ISO 8601 格式)

    ## 业务逻辑
    根据 host_id 更新 host_rec 表：
    - host_rec.id = host_id
    - 更新 host_state = 1 (已锁定)
    - 更新 subm_time = 当前时间
    - 如果数据不存在，返回"主机不存在"

    Args:
        vnc_report: VNC连接结果上报数据
        host_service: 主机服务实例（依赖注入）

    Returns:
        上报结果
    """
    result = await host_service.report_vnc_connection(vnc_report)

    vnc_response = VNCConnectionResponse(
        host_id=result["host_id"],
        connection_status=result["connection_status"],
        connection_time=result["connection_time"],
        message=result["message"],
    )

    return SuccessResponse(
        data=vnc_response.model_dump(),
        message="VNC连接结果上报成功",
    )


@router.post(
    "/vnc/connect",
    response_model=SuccessResponse,
    summary="获取 VNC 连接信息",
    description="获取指定主机的 VNC 连接信息",
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "操作成功",
                        "data": {
                            "ip": "192.168.101.118",
                            "port": "5900",
                            "username": "neusoft",
                            "***REMOVED***word": "***REMOVED***",
                        },
                    }
                }
            },
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
        404: {
            "description": "主机不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "主机不存在或未启用",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "获取 VNC 连接信息失败，请稍后重试",
                        "error_code": "VNC_GET_FAILED",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def get_vnc_connection_info(
    request: GetVNCConnectionRequest,
    host_service: HostService = Depends(get_host_service),
):
    """获取指定主机的 VNC 连接信息

    ## 请求参数说明
    - `id`: 主机ID (host_rec.id)

    ## 业务逻辑
    1. 根据 ID 查询 host_rec 表有效数据
    2. 检查数据有效性（del_flag=0, appr_state=1）
    3. 返回 VNC 连接所需的字段

    ## 返回字段说明
    - `ip`: VNC 服务器 IP 地址
    - `port`: VNC 服务端口
    - `username`: 连接用户名
    - `***REMOVED***word`: 连接密码

    Args:
        request: 包含主机ID的请求字典
        host_service: 主机服务实例（依赖注入）

    Returns:
        包含 VNC 连接信息的响应
    """
    logger.info(
        "接收获取 VNC 连接信息请求",
        extra={"host_rec_id": request.id},
    )

    # 提取主机ID
    host_rec_id = request.id

    if not host_rec_id:
        from shared.common.exceptions import BusinessError

        raise BusinessError(
            message="主机ID不能为空",
            error_code="INVALID_HOST_ID",
            code=400,
        )

    vnc_info = await host_service.get_vnc_connection_info(str(host_rec_id))

    logger.info(
        "获取 VNC 连接信息完成",
        extra={
            "host_rec_id": host_rec_id,
            "ip": vnc_info.get("ip"),
            "port": vnc_info.get("port"),
        },
    )

    return SuccessResponse(
        data=vnc_info,
        message="获取 VNC 连接信息成功",
    )
