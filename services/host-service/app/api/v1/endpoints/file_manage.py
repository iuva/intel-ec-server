"""文件管理 API 端点

提供文件上传、下载和访问等 HTTP API 接口。
"""

import os
import sys
from pathlib import Path as SysPath
from typing import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import Response
from starlette.status import HTTP_206_PARTIAL_CONTENT, HTTP_404_NOT_FOUND

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_file_manage_service, get_current_user
    from app.schemas.host import FileUploadResponse
    from app.services.file_manage_service import FileManageService
    from app.utils.http_helpers import parse_range_header
    from app.utils.response_helpers import create_success_result

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_file_manage_service, get_current_user
    from app.schemas.host import FileUploadResponse
    from app.services.file_manage_service import FileManageService
    from app.utils.http_helpers import parse_range_header
    from app.utils.response_helpers import create_success_result

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=Result[FileUploadResponse],
    summary="上传文件",
    description="上传文件到服务器指定目录，返回文件访问 URL",
    responses={
        200: {
            "description": "上传成功",
            "model": Result[FileUploadResponse],
        },
    },
)
@handle_api_errors
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    file_manage_service: FileManageService = Depends(get_file_manage_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[FileUploadResponse]:
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
            "user_id": current_user.get("id"),
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

    return create_success_result(
        data=response_data,
        message_key="success.file.upload",
        locale=locale,
        default_message="文件上传成功",
    )


def _file_chunk_generator(file_path: SysPath, start: int, end: int, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    """生成器：按 Range 输出文件内容"""

    with open(file_path, "rb") as file_obj:
        file_obj.seek(start)
        bytes_left = end - start + 1

        while bytes_left > 0:
            read_size = min(chunk_size, bytes_left)
            data = file_obj.read(read_size)
            if not data:
                break
            bytes_left -= len(data)
            yield data


@router.get(
    "/{filename}",
    summary="获取文件（支持断点续传）",
    description=(
        "通过 `saved_filename` 获取上传的文件内容，默认返回完整文件。\n\n"
        "### Range 下载说明\n"
        "- 支持标准 HTTP Range 请求头，格式：`Range: bytes=start-end`\n"
        "- 例如：`Range: bytes=0-1048575` 可获取前 1MB，用于断点续传\n"
        "- 响应会携带 `Accept-Ranges: bytes`、`Content-Range`、`Content-Length`\n"
        "- 当 Range 合法时返回 `206 Partial Content`，否则返回 `416`\n"
        "- 未携带 Range 时返回完整文件（200 OK）"
    ),
    responses={
        200: {
            "description": "返回完整文件内容",
            "content": {"application/octet-stream": {}},
        },
        206: {
            "description": "返回部分内容（断点续传），包含 Content-Range 头",
            "content": {"application/octet-stream": {}},
        },
        404: {
            "description": "文件不存在",
        },
        416: {
            "description": "Range 请求范围无效",
        },
    },
)
@handle_api_errors
async def get_file(
    request: Request,
    filename: str = Path(..., description="保存的文件名（由上传接口返回的 saved_filename）"),
    file_manage_service: FileManageService = Depends(get_file_manage_service),
    current_user: dict = Depends(get_current_user),
) -> Response:
    """获取上传的文件，支持 HTTP Range 断点续传

    Args:
        request: FastAPI 请求对象，用于读取 Range 头
        filename: 保存的文件名（由上传接口返回的 saved_filename）
        file_manage_service: 文件管理服务实例
        current_user: 当前用户信息

    Returns:
        Response: 根据是否携带 Range 返回 FileResponse 或 StreamingResponse

    Raises:
        HTTPException: 文件不存在 (404) 或 Range 无效 (416)
    """
    logger.info(
        "获取文件",
        extra={
            "operation": "get_file",
            "filename": filename,
            "user_id": current_user.get("id"),
        },
    )

    # 获取文件路径
    file_path = file_manage_service.get_file_path(filename)

    if not file_path.exists():
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="文件不存在")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    if not range_header:
        full_headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
        }
        full_response = FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/octet-stream",
            headers=full_headers,
        )
        return full_response

    start, end = parse_range_header(range_header, file_size)
    content_length = end - start + 1
    content_range_value = f"bytes {start}-{end}/{file_size}"

    streaming_response = StreamingResponse(
        _file_chunk_generator(file_path, start, end),
        status_code=HTTP_206_PARTIAL_CONTENT,
        media_type="application/octet-stream",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Range": content_range_value,
            "Content-Length": str(content_length),
        },
    )

    return streaming_response
