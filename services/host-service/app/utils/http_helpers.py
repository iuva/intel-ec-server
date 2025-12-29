"""HTTP 请求处理辅助函数

提供 HTTP 请求相关的工具函数，如 Range 头解析等。
"""

import re
from typing import Tuple

from fastapi import HTTPException, status


def parse_range_header(range_header: str, file_size: int) -> Tuple[int, int]:
    """解析 Range 头，返回起始和结束字节范围（包含）

    Args:
        range_header: Range 请求头值，格式：bytes=start-end
        file_size: 文件大小（字节）

    Returns:
        Tuple[int, int]: (起始位置, 结束位置)，都是包含的

    Raises:
        HTTPException: Range 格式错误或范围无效时抛出 416 错误
    """
    range_match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not range_match:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range header 格式错误，示例：bytes=0-1023",
        )

    start_str, end_str = range_match.groups()

    if start_str == "" and end_str == "":
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range header 必须包含开始或结束位置",
        )

    if start_str == "":
        # 形如 bytes=-500 表示最后 500 字节
        length = int(end_str)
        if length <= 0:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Range 长度必须大于 0",
            )
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        if end_str == "":
            end = file_size - 1
        else:
            end = int(end_str)

    if start >= file_size or start < 0:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range 起始位置超出文件大小",
        )

    end = min(end, file_size - 1)

    if end < start:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range 结束位置必须大于等于起始位置",
        )

    return start, end
