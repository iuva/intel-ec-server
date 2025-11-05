"""文件管理 API 端点

提供文件上传、下载和访问等 HTTP API 接口。
"""

import os
import sys

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_file_manage_service, get_current_user
    from app.schemas.host import FileUploadResponse
    from app.services.file_manage_service import FileManageService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_file_manage_service, get_current_user
    from app.schemas.host import FileUploadResponse
    from app.services.file_manage_service import FileManageService

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=SuccessResponse,
    summary="上传文件",
    description="上传文件到服务器指定目录，返回文件访问 URL",
    responses={
        200: {
            "description": "上传成功",
            "model": FileUploadResponse,
        },
    },
)
@handle_api_errors
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    file_manage_service: FileManageService = Depends(get_file_manage_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> SuccessResponse:
    """上传文件（管理后台）

    业务逻辑：
    1. 接收上传的文件
    2. 保存到环境配置的本地指定目录（FILE_UPLOAD_DIR）
    3. 生成唯一文件名（使用 UUID）
    4. 返回文件访问 URL

    ## 文件存储
    - 文件保存目录由环境变量 `FILE_UPLOAD_DIR` 配置，默认为 `/app/uploads`
    - Docker 启动时需要挂载卷到该目录，确保文件不丢失
    - 文件名使用 UUID 生成，避免文件名冲突

    ## 返回字段
    - `file_id`: 文件唯一标识
    - `filename`: 原始文件名
    - `saved_filename`: 保存的文件名
    - `file_url`: 文件访问 URL（可直接通过服务访问）
    - `file_size`: 文件大小（字节）
    - `content_type`: 文件 MIME 类型
    - `upload_time`: 上传时间

    Args:
        file: 上传的文件对象
        file_manage_service: 文件管理服务实例
        current_user: 当前用户信息
        locale: 语言偏好

    Returns:
        SuccessResponse: 包含文件信息和访问 URL
    """
    logger.info(
        "开始上传文件",
        extra={
            "operation": "upload_file",
            "filename": file.filename,
            "content_type": file.content_type,
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
        },
    )

    # 读取文件内容
    file_content = await file.read()

    # 调用服务层上传文件
    file_info = await file_manage_service.upload_file(
        file_content=file_content,
        filename=file.filename or "unknown",
        content_type=file.content_type,
    )

    # 构建响应数据
    response_data = FileUploadResponse(**file_info)

    logger.info(
        "文件上传成功",
        extra={
            "operation": "upload_file",
            "file_id": file_info["file_id"],
            "filename": file_info["filename"],
            "file_size": file_info["file_size"],
        },
    )

    return SuccessResponse(
        data=response_data.model_dump(),
        message="文件上传成功",
    )


@router.get(
    "/{filename}",
    summary="获取文件",
    description="通过文件名获取上传的文件",
    responses={
        200: {
            "description": "文件获取成功",
            "content": {"application/octet-stream": {}},
        },
        404: {
            "description": "文件不存在",
        },
    },
)
@handle_api_errors
async def get_file(
    filename: str,
    file_manage_service: FileManageService = Depends(get_file_manage_service),
    current_user: dict = Depends(get_current_user),
) -> FileResponse:
    """获取上传的文件

    通过保存的文件名获取文件内容，支持直接通过 URL 访问。

    Args:
        filename: 保存的文件名（由上传接口返回的 saved_filename）
        file_manage_service: 文件管理服务实例
        current_user: 当前用户信息

    Returns:
        FileResponse: 文件响应对象

    Raises:
        HTTPException: 文件不存在时返回 404
    """
    logger.info(
        "获取文件",
        extra={
            "operation": "get_file",
            "filename": filename,
            "user_id": current_user.get("user_id"),
        },
    )

    # 获取文件路径
    file_path = file_manage_service.get_file_path(filename)

    # 返回文件响应
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
