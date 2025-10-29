"""VNC 连接管理 API 端点

提供 VNC 连接相关的 API 端点，包括：
- POST /vnc/report - 上报 VNC 连接结果
- POST /vnc/connect - 获取 VNC 连接信息
"""

import os
import sys

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

# 使用 try-except 方式处理路径导入
try:
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_api_errors
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

from app.api.v1.dependencies import get_vnc_service
from app.schemas.host import GetVNCConnectionRequest, VNCConnectionInfo, VNCConnectionReport, VNCConnectionResponse
from app.services.vnc_service import VNCService

logger = get_logger(__name__)

router = APIRouter(prefix="/vnc", tags=["VNC连接管理"])


@router.post(
    "/report",
    response_model=SuccessResponse,
    status_code=HTTP_200_OK,
    summary="上报 VNC 连接结果",
    description="处理浏览器插件上报的 VNC 连接结果，更新主机状态为已锁定",
    responses={
        200: {
            "description": "上报成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "操作成功",
                        "data": {
                            "host_id": "123",
                            "connection_status": "success",
                            "connection_time": "2025-10-15T10:00:00Z",
                            "message": "VNC连接结果上报成功，主机已锁定",
                        },
                    }
                }
            },
        },
        400: {
            "description": "主机不存在或请求数据无效",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "主机不存在: 123",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_vnc_connection(
    request: VNCConnectionReport,
    vnc_service: VNCService = Depends(get_vnc_service),
):
    """上报 VNC 连接结果

    处理浏览器插件上报的 VNC 连接结果，记录连接状态和时间，
    并更新主机状态为已锁定。

    ## 请求参数说明
    - `user_id`: 用户ID（必填）
    - `host_id`: 主机ID，对应 host_rec.id（必填）
    - `connection_status`: 连接状态，可选值: success/failed（必填）
    - `connection_time`: VNC 连接时间（可选）

    ## 业务逻辑
    1. 根据 host_id 查询 host_rec 表
    2. 若主机不存在，返回 400 错误
    3. 更新 host_state = 1（已锁定）
    4. 更新 subm_time = 当前时间
    5. 记录详细操作日志

    ## 错误码
    - `HOST_NOT_FOUND`: 主机不存在（400）

    Args:
        request: VNC 连接结果上报数据
        vnc_service: VNC 服务实例

    Returns:
        上报成功响应，包含处理结果信息
    """
    logger.info(
        "接收 VNC 连接结果上报请求",
        extra={
            "user_id": request.user_id,
            "host_id": request.host_id,
            "connection_status": request.connection_status,
        },
    )

    result = await vnc_service.report_vnc_connection(request)

    vnc_response = VNCConnectionResponse(
        host_id=result["host_id"],
        connection_status=result["connection_status"],
        connection_time=result["connection_time"],
        message=result["message"],
    )

    logger.info(
        "VNC 连接结果上报处理完成",
        extra={
            "host_id": request.host_id,
            "connection_status": request.connection_status,
        },
    )

    return SuccessResponse(
        data=vnc_response.model_dump(),
        message="VNC连接结果上报成功",
    )


@router.post(
    "/connect",
    response_model=SuccessResponse,
    status_code=HTTP_200_OK,
    summary="获取 VNC 连接信息",
    description="获取指定主机的 VNC 连接参数，用于建立 VNC 连接",
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
            "description": "请求数据无效或 VNC 信息不完整",
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
            "description": "主机不存在或未启用",
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
    },
)
@handle_api_errors
async def get_vnc_connection(
    request: GetVNCConnectionRequest,
    vnc_service: VNCService = Depends(get_vnc_service),
):
    """获取 VNC 连接信息

    根据主机 ID 查询数据库，返回建立 VNC 连接所需的参数。

    ## 请求参数说明
    - `id`: 主机ID，对应 host_rec.id（必填）

    ## 业务逻辑
    1. 验证主机ID格式
    2. 查询 host_rec 表
    3. 检查主机是否启用且未删除
    4. 检查 VNC 连接信息是否完整
    5. 返回 VNC 连接参数

    ## 返回字段说明
    - `ip`: VNC 服务器 IP 地址
    - `port`: VNC 服务端口
    - `username`: 连接用户名
    - `***REMOVED***word`: 连接密码

    ## 错误码
    - `INVALID_HOST_ID`: 主机ID格式无效（400）
    - `HOST_NOT_FOUND`: 主机不存在或未启用（404）
    - `VNC_INFO_INCOMPLETE`: VNC 连接信息不完整（400）
    - `VNC_GET_FAILED`: 获取失败，服务异常（500）

    Args:
        request: 获取 VNC 连接信息请求
        vnc_service: VNC 服务实例

    Returns:
        包含 VNC 连接信息的响应
    """
    logger.info(
        "接收获取 VNC 连接信息请求",
        extra={"host_rec_id": request.id},
    )

    vnc_info = await vnc_service.get_vnc_connection_info(request.id)

    vnc_connection_info = VNCConnectionInfo(
        ip=vnc_info["ip"],
        port=vnc_info["port"],
        username=vnc_info["username"],
        ***REMOVED***word=vnc_info["***REMOVED***word"],
    )

    logger.info(
        "获取 VNC 连接信息完成",
        extra={
            "host_rec_id": request.id,
            "ip": vnc_info["ip"],
        },
    )

    return SuccessResponse(
        data=vnc_connection_info.model_dump(),
        message="获取 VNC 连接信息成功",
    )
