"""Response building helper functions

Provides unified response building utility functions to reduce code duplication.
"""

from typing import Any, Optional

from shared.common.i18n import t
from shared.common.response import Result


def create_success_result(
    data: Any,
    message_key: str,
    locale: str = "zh_CN",
    default_message: Optional[str] = None,
    code: int = 200,
) -> Result[Any]:
    """Create success response result

    Args:
        data: Response data
        message_key: Message key (for internationalization)
        locale: Language preference, default "zh_CN"
        default_message: Default message (used when translation key does not exist)
        code: HTTP status code, default 200

    Returns:
        Result: Success response result
    """
    message = t(message_key, locale=locale, default=default_message or "Operation successful")
    return Result(code=code, message=message, data=data, locale=locale)
