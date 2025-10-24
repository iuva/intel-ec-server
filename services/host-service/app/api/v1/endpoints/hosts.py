"""主机管理 API 端点

提供主机查询相关的 API 端点。
"""

import os
import sys

from app.api.v1.dependencies import get_host_service
from app.schemas.host import VNCConnectionReport, VNCConnectionResponse
from app.services.host_service import HostService
from fastapi import APIRouter, Depends

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
