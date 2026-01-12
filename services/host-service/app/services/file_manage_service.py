"""File management service

Provides core business logic for file upload, storage, and access.
"""

from datetime import datetime
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional
import uuid

# Use try-except to handle path imports
try:
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ErrorCode, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ErrorCode, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class FileManageService:
    """File management service"""

    def __init__(self, upload_dir: Optional[str] = None):
        """Initialize file management service

        Args:
            upload_dir: File upload directory, if None then get from environment variable
        """
        # Get upload directory from environment variable, default to /app/uploads
        self.upload_dir = upload_dir or os.getenv("FILE_UPLOAD_DIR", "/app/uploads")

        # Ensure upload directory exists
        self._ensure_upload_dir()

    def _ensure_upload_dir(self) -> None:
        """Ensure upload directory exists and is writable"""
        try:
            upload_path = Path(self.upload_dir)
            # Create directory (if it doesn't exist)
            upload_path.mkdir(parents=True, exist_ok=True)

            # Check if directory is writable
            if not os.access(upload_path, os.W_OK):
                logger.warning(
                    f"File upload directory is not writable: {self.upload_dir}, attempting to fix permissions",
                    extra={
                        "upload_dir": self.upload_dir,
                        "current_permissions": oct(upload_path.stat().st_mode)[-3:],
                    },
                )
                # Try to set permissions (may fail if volume is mounted with restricted permissions)
                try:
                    upload_path.chmod(0o755)
                except PermissionError:
                    logger.warning(
                        (
                            "Cannot modify file upload directory permissions, please ensure "
                            "Docker volume mount permissions are correct"
                        ),
                        extra={"upload_dir": self.upload_dir},
                    )

            logger.info(
                f"File upload directory prepared: {self.upload_dir}",
                extra={
                    "upload_dir": self.upload_dir,
                    "exists": upload_path.exists(),
                    "writable": os.access(upload_path, os.W_OK),
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to create upload directory: {self.upload_dir}, error: {str(e)}",
                extra={"upload_dir": self.upload_dir, "error_type": type(e).__name__},
                exc_info=True,
            )
            raise BusinessError(
                message="File upload directory initialization failed",
                error_code=ServiceErrorCodes.FILE_UPLOAD_FAILED,
            )

    @handle_service_errors(
        error_message="File upload failed",
        error_code="FILE_UPLOAD_FAILED",
    )
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file

        Business logic:
        1. Generate unique filename (using UUID to avoid filename conflicts)
        2. Save file to configured upload directory
        3. Return file access URL

        Args:
            file_content: File content (bytes)
            filename: Original filename
            content_type: File MIME type

        Returns:
            Dict[str, Any]: File information, containing:
                - file_id: File unique identifier
                - filename: Original filename
                - saved_filename: Saved filename
                - file_url: File access URL
                - file_size: File size (bytes)
                - content_type: File MIME type
                - upload_time: Upload time

        Raises:
            BusinessError: Raises business exception when file upload fails
        """
        try:
            # Generate unique filename
            file_extension = Path(filename).suffix
            file_id = str(uuid.uuid4())
            saved_filename = f"{file_id}{file_extension}"

            # Build file save path
            file_path = Path(self.upload_dir) / saved_filename

            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Get file size
            file_size = len(file_content)

            # Build file access URL
            # Use /api/v1/host/file/ as file access path prefix
            file_url = f"/api/v1/host/file/{saved_filename}"

            file_info = {
                "file_id": file_id,
                "filename": filename,
                "saved_filename": saved_filename,
                "file_url": file_url,
                "file_size": file_size,
                "content_type": content_type or "application/octet-stream",
                "upload_time": datetime.utcnow().isoformat(),
            }

            logger.info(
                "File upload succeeded",
                extra={
                    "operation": "upload_file",
                    "file_id": file_id,
                    "filename": filename,
                    "saved_filename": saved_filename,
                    "file_size": file_size,
                },
            )

            return file_info

        except Exception as e:
            logger.error(
                "File upload failed",
                extra={
                    "operation": "upload_file",
                    "filename": filename,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message=f"File upload failed: {str(e)}",
                error_code=ServiceErrorCodes.FILE_UPLOAD_FAILED,
            )

    def get_file_path(self, saved_filename: str) -> Path:
        """Get file path

        Args:
            saved_filename: Saved filename

        Returns:
            Path: File full path

        Raises:
            BusinessError: Raises business exception when file does not exist
        """
        file_path = Path(self.upload_dir) / saved_filename

        if not file_path.exists():
            raise BusinessError(
                message="File does not exist",
                error_code=ErrorCode.FILE_NOT_FOUND,
                code=ServiceErrorCodes.FILE_NOT_FOUND,
                http_status_code=404,
                details={"filename": saved_filename},
            )

        return file_path
