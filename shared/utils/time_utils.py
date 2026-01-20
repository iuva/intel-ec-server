"""Time and timezone utility functions"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def get_db_timezone() -> timezone:
    """Get database timezone configuration from environment variables

    Reads MARIADB_TIMEZONE environment variable (default: +08:00)
    Returns:
        timezone: Configured timezone object
    """
    tz_str = os.getenv("MARIADB_TIMEZONE", "+08:00")

    try:
        # Default to UTC if not set (should not happen with default)
        if not tz_str:
            return timezone(timedelta(hours=8))

        # Handle sign
        sign = 1
        if tz_str.startswith("-"):
            sign = -1
            tz_str = tz_str[1:]
        elif tz_str.startswith("+"):
            tz_str = tz_str[1:]

        # Parse HH:MM
        if ":" in tz_str:
            hours, minutes = map(int, tz_str.split(":"))
        else:
            hours = int(tz_str)
            minutes = 0

        offset = timedelta(hours=hours * sign, minutes=minutes * sign)
        return timezone(offset)

    except Exception as e:
        logger.warning(f"Failed to parse MARIADB_TIMEZONE='{tz_str}', fallback to UTC+8", extra={"error": str(e)})
        return timezone(timedelta(hours=8))
