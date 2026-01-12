"""HTTP request processing helper functions

Provides HTTP request-related utility functions, such as Range header parsing, etc.
"""

import re
from typing import Tuple

from fastapi import HTTPException, status


def parse_range_header(range_header: str, file_size: int) -> Tuple[int, int]:
    """Parse Range header, return start and end byte range (inclusive)

    Args:
        range_header: Range request header value, format: bytes=start-end
        file_size: File size (bytes)

    Returns:
        Tuple[int, int]: (start position, end position), both inclusive

    Raises:
        HTTPException: Raises 416 error when Range format is invalid or range is invalid
    """
    range_match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not range_match:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range header format error, example: bytes=0-1023",
        )

    start_str, end_str = range_match.groups()

    if start_str == "" and end_str == "":
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range header must include start or end position",
        )

    if start_str == "":
        # Format like bytes=-500 means last 500 bytes
        length = int(end_str)
        if length <= 0:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Range length must be greater than 0",
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
            detail="Range start position exceeds file size",
        )

    end = min(end, file_size - 1)

    if end < start:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range end position must be greater than or equal to start position",
        )

    return start, end
