"""
Host Validation Utility Functions

Provides validation and query building functions related to hosts, reducing code duplication.

Note: These functions need to be used internally within services, as they depend on service-specific model classes.
"""

import os
import sys
from typing import Optional, Type, TypeVar

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Use try-except approach to handle path imports
try:
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# Type variable, used to represent the host model class
T = TypeVar("T")


async def validate_host_exists(
    session: AsyncSession,
    host_model: Type[T],
    host_id: int,
    locale: str = "zh_CN",
    raise_on_not_found: bool = True,
) -> Optional[T]:
    """Validate that the host exists and is not deleted

    Args:
        session: Database session
        host_model: Host model class (e.g., HostRec)
        host_id: Host ID
        locale: Language code (for error messages)
        raise_on_not_found: Whether to raise an exception if the host does not exist

    Returns:
        Host record, or None if it does not exist and not raising an exception

    Raises:
        BusinessError: If the host does not exist and raise_on_not_found=True

    Example:
        ```python
        from app.models.host_rec import HostRec

        # Validate host exists (raises exception if not found)
        host_rec = await validate_host_exists(session, HostRec, host_id=123)

        # Validate host exists (returns None if not found)
        host_rec = await validate_host_exists(session, HostRec, host_id=123, raise_on_not_found=False)
        if not host_rec:
            # Handle case where host does not exist
            ***REMOVED***
        ```
    """
    stmt = select(host_model).where(
        and_(
            host_model.id == host_id,
            host_model.del_flag == 0,  # Only check records that are not deleted
        )
    )
    result = await session.execute(stmt)
    host_rec = result.scalar_one_or_none()

    if not host_rec:
        if raise_on_not_found:
            logger.warning(
                "Host does not exist or has been deleted",
                extra={
                    "host_id": host_id,
                },
            )
            raise BusinessError(
                message=t("error.host.not_found", locale=locale, host_id=host_id),
                message_key="error.host.not_found",
                error_code="HOST_NOT_FOUND",
                code=ServiceErrorCodes.HOST_NOT_FOUND,
                http_status_code=400,
                details={"host_id": host_id},
                locale=locale,
            )
        return None

    return host_rec


def build_host_query(
    host_model: Type[T],
    host_id: Optional[int] = None,
    include_deleted: bool = False,
    host_state: Optional[int] = None,
    appr_state: Optional[int] = None,
    mg_id: Optional[str] = None,
    mac_addr: Optional[str] = None,
) -> Select:
    """Build host query statement

    Args:
        host_model: Host model class (e.g., HostRec)
        host_id: Host ID (optional)
        include_deleted: Whether to include deleted records
        host_state: Host state (optional)
        appr_state: Approval state (optional)
        mg_id: Unique boot ID (optional, supports fuzzy matching)
        mac_addr: MAC address (optional, supports fuzzy matching)

    Returns:
        SQLAlchemy Select statement

    Example:
        ```python
        from app.models.host_rec import HostRec

        # Query single host
        stmt = build_host_query(HostRec, host_id=123)
        result = await session.execute(stmt)
        host = result.scalar_one_or_none()

        # Query hosts with specific state
        stmt = build_host_query(HostRec, host_state=0, appr_state=1)
        result = await session.execute(stmt)
        hosts = result.scalars().all()
        ```
    """
    conditions = []

    if host_id is not None:
        conditions.append(host_model.id == host_id)

    if not include_deleted:
        conditions.append(host_model.del_flag == 0)

    if host_state is not None:
        conditions.append(host_model.host_state == host_state)

    if appr_state is not None:
        conditions.append(host_model.appr_state == appr_state)

    if mg_id:
        conditions.append(host_model.mg_id.like(f"%{mg_id}%"))

    if mac_addr:
        conditions.append(host_model.mac_addr.like(f"%{mac_addr}%"))

    stmt = select(host_model)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt


def parse_host_id(
    host_id: str,
    raise_on_error: bool = True,
    error_message: Optional[str] = None,
    error_code: str = "INVALID_HOST_ID",
) -> int:
    """Parse host ID string to integer

    Unified handling of host ID format validation logic, reducing duplicate code.

    Args:
        host_id: Host ID string
        raise_on_error: Whether to raise an exception if the format is invalid
        error_message: Custom error message (uses default message if None)
        error_code: Error code

    Returns:
        Parsed host ID (integer)

    Raises:
        BusinessError: If the format is invalid and raise_on_error=True

    Example:
        ```python
        # Parse host ID (raises exception if invalid)
        host_id_int = parse_host_id("123")

        # Parse host ID (returns None if invalid)
        try:
            host_id_int = parse_host_id("invalid", raise_on_error=True)
        except BusinessError:
            # Handle error
            ***REMOVED***
        ```
    """
    try:
        return int(host_id)
    except (ValueError, TypeError) as e:
        if raise_on_error:
            logger.warning(
                "Invalid host ID format",
                extra={
                    "host_id": host_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise BusinessError(
                message=error_message or "Invalid host ID format",
                error_code=error_code,
                code=400,
                details={"host_id": host_id},
            )
        raise
