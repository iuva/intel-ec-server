"""文件管理服务

提供文件上传、存储和访问等核心业务逻辑。
"""

from datetime import datetime
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional
import uuid

# 使用 try-except 方式处理路径导入
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
    """文件管理服务"""

    def __init__(self, upload_dir: Optional[str] = None):
        """初始化文件管理服务

        Args:
            upload_dir: 文件上传目录，如果为 None 则从环境变量获取
        """
        # 从环境变量获取上传目录，默认为 /app/uploads
        self.upload_dir = upload_dir or os.getenv("FILE_UPLOAD_DIR", "/app/uploads")

        # 确保上传目录存在
        self._ensure_upload_dir()

    def _ensure_upload_dir(self) -> None:
        """确保上传目录存在且可写"""
        try:
            upload_path = Path(self.upload_dir)
            # 创建目录（如果不存在）
            upload_path.mkdir(parents=True, exist_ok=True)

            # 检查目录是否可写
            if not os.access(upload_path, os.W_OK):
                logger.warning(
                    f"文件上传目录不可写: {self.upload_dir}，尝试修复权限",
                    extra={
                        "upload_dir": self.upload_dir,
                        "current_permissions": oct(upload_path.stat().st_mode)[-3:],
                    },
                )
                # 尝试设置权限（可能失败，如果是卷挂载且权限受限）
                try:
                    upload_path.chmod(0o755)
                except PermissionError:
                    logger.warning(
                        "无法修改文件上传目录权限，请确保 Docker 卷挂载权限正确",
                        extra={"upload_dir": self.upload_dir},
                    )

            logger.info(
                f"文件上传目录已准备: {self.upload_dir}",
                extra={
                    "upload_dir": self.upload_dir,
                    "exists": upload_path.exists(),
                    "writable": os.access(upload_path, os.W_OK),
                },
            )
        except Exception as e:
            logger.error(
                f"创建上传目录失败: {self.upload_dir}, 错误: {str(e)}",
                extra={"upload_dir": self.upload_dir, "error_type": type(e).__name__},
                exc_info=True,
            )
            raise BusinessError(
                message="文件上传目录初始化失败",
                error_code=ServiceErrorCodes.FILE_UPLOAD_FAILED,
            )

    @handle_service_errors(
        error_message="文件上传失败",
        error_code="FILE_UPLOAD_FAILED",
    )
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """上传文件

        业务逻辑：
        1. 生成唯一文件名（使用 UUID 避免文件名冲突）
        2. 保存文件到配置的上传目录
        3. 返回文件访问 URL

        Args:
            file_content: 文件内容（字节）
            filename: 原始文件名
            content_type: 文件 MIME 类型

        Returns:
            Dict[str, Any]: 文件信息，包含：
                - file_id: 文件唯一标识
                - filename: 原始文件名
                - saved_filename: 保存的文件名
                - file_url: 文件访问 URL
                - file_size: 文件大小（字节）
                - content_type: 文件 MIME 类型
                - upload_time: 上传时间

        Raises:
            BusinessError: 文件上传失败时抛出业务异常
        """
        try:
            # 生成唯一文件名
            file_extension = Path(filename).suffix
            file_id = str(uuid.uuid4())
            saved_filename = f"{file_id}{file_extension}"

            # 构建文件保存路径
            file_path = Path(self.upload_dir) / saved_filename

            # 保存文件
            with open(file_path, "wb") as f:
                f.write(file_content)

            # 获取文件大小
            file_size = len(file_content)

            # 构建文件访问 URL
            # 使用 /api/v1/host/file/ 作为文件访问路径前缀
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
                "文件上传成功",
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
                "文件上传失败",
                extra={
                    "operation": "upload_file",
                    "filename": filename,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message=f"文件上传失败: {str(e)}",
                error_code=ServiceErrorCodes.FILE_UPLOAD_FAILED,
            )

    def get_file_path(self, saved_filename: str) -> Path:
        """获取文件路径

        Args:
            saved_filename: 保存的文件名

        Returns:
            Path: 文件完整路径

        Raises:
            BusinessError: 文件不存在时抛出业务异常
        """
        file_path = Path(self.upload_dir) / saved_filename

        if not file_path.exists():
            raise BusinessError(
                message="文件不存在",
                error_code=ErrorCode.FILE_NOT_FOUND,
                code=ServiceErrorCodes.FILE_NOT_FOUND,
                http_status_code=404,
                details={"filename": saved_filename},
            )

        return file_path
