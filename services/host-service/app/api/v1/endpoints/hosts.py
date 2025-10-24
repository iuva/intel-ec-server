"""主机管理 API 端点"""

from app.api.v1.dependencies import get_host_service
from app.schemas.host import (VNCConnectionReport, VNCConnectionResponse)
from app.services.host_service import HostService
from fastapi import APIRouter, Depends

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
    "/plugin/report",
    response_model=SuccessResponse,
    summary="VNC连接结果上报",
    description="浏览器插件上报VNC连接结果到服务端",
    responses={
        200: {
            "description": "VNC连接结果上报成功",
            "model": SuccessResponse
        },
        400: {
            "description": "主机不存在或请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "主机不存在: 1852278641262084097",
                        "error_code": "HOST_NOT_FOUND"
                    }
                }
            }
        },
        500: {
            "description": "服务器错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "VNC连接结果上报失败",
                        "error_code": "VNC_CONNECTION_REPORT_FAILED"
                    }
                }
            }
        }
    }
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
