"""File management API endpoints

Provides HTTP API interfaces for file upload, download, and access.
"""

import os
import sys
from pathlib import Path as SysPath
from typing import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import Response
from starlette.status import HTTP_206_PARTIAL_CONTENT, HTTP_404_NOT_FOUND

# Use try-except to handle path imports
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
    summary="Upload file",
    description="Upload file to server specified directory, return file access URL",
    responses={
        200: {
            "description": "Upload succeeded",
            "model": Result[FileUploadResponse],
        },
    },
)
@handle_api_errors
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    file_manage_service: FileManageService = Depends(get_file_manage_service),
    current_user: dict = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Result[FileUploadResponse]:
    """Upload file (admin backend)

    Business logic:
    1. Receive uploaded file
    2. Save to locally specified directory configured by environment (FILE_UPLOAD_DIR)
    3. Generate unique filename (using UUID)
    4. Return file access URL

    ## File storage
    - File save directory is configured by environment variable `FILE_UPLOAD_DIR`, default is `/app/uploads`
    - Docker startup needs to mount volume to this directory to ensure files are not lost
    - Filename uses UUID generation to avoid filename conflicts

    ## Return fields
    - `file_id`: File unique identifier
    - `filename`: Original filename
    - `saved_filename`: Saved filename
    - `file_url`: File access URL (can be accessed directly through service)
    - `file_size`: File size (bytes)
    - `content_type`: File MIME type
    - `upload_time`: Upload time

    Args:
        file: Uploaded file object
        file_manage_service: File management service instance
        current_user: Current user information
        locale: Language preference

    Returns:
        SuccessResponse: Contains file information and access URL
    """
    logger.info(
        "Start uploading file",
        extra={
            "operation": "upload_file",
            "filename": file.filename,
            "content_type": file.content_type,
            "user_id": current_user.get("id"),
            "username": current_user.get("username"),
        },
    )

    # Read file content
    file_content = await file.read()

    # Call service layer to upload file
    file_info = await file_manage_service.upload_file(
        file_content=file_content,
        filename=file.filename or "unknown",
        content_type=file.content_type,
    )

    # Build response data
    response_data = FileUploadResponse(**file_info)

    logger.info(
        "File upload succeeded",
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
        default_message="File upload succeeded",
    )


def _file_chunk_generator(file_path: SysPath, start: int, end: int, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    """Generator: Output file content by Range"""

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
    summary="Get file (supports resumable download)",
    description=(
        "Get uploaded file content through `saved_filename`, returns complete file by default.\n\n"
        "### Range download description\n"
        "- Supports standard HTTP Range request header, format: `Range: bytes=start-end`\n"
        "- Example: `Range: bytes=0-1048575` can get first 1MB, used for resumable download\n"
        "- Response will include `Accept-Ranges: bytes`, `Content-Range`, `Content-Length`\n"
        "- Returns `206 Partial Content` when Range is valid, otherwise returns `416`\n"
        "- Returns complete file (200 OK) when Range is not included"
    ),
    responses={
        200: {
            "description": "Returns complete file content",
            "content": {"application/octet-stream": {}},
        },
        206: {
            "description": "Returns partial content (resumable download), includes Content-Range header",
            "content": {"application/octet-stream": {}},
        },
        404: {
            "description": "File does not exist",
        },
        416: {
            "description": "Range request range is invalid",
        },
    },
)
@handle_api_errors
async def get_file(
    request: Request,
    filename: str = Path(..., description="Saved filename (saved_filename returned by upload interface)"),
    file_manage_service: FileManageService = Depends(get_file_manage_service),
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Get uploaded file, supports HTTP Range resumable download

    Args:
        request: FastAPI request object, used to read Range header
        filename: Saved filename (saved_filename returned by upload interface)
        file_manage_service: File management service instance
        current_user: Current user information

    Returns:
        Response: Returns FileResponse or StreamingResponse based on whether Range is included

    Raises:
        HTTPException: File does not exist (404) or Range is invalid (416)
    """
    logger.info(
        "Get file",
        extra={
            "operation": "get_file",
            "filename": filename,
            "user_id": current_user.get("id"),
        },
    )

    # Get file path
    file_path = file_manage_service.get_file_path(filename)

    if not file_path.exists():
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="File does not exist")

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
