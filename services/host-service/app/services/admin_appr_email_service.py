"""Admin Backend Pending Approval Host Management - Email Service Module

Provides approval-related email sending functionality, including email template definitions and sending logic.

Split from admin_appr_host_service.py to improve code maintainability.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Use try-except to handle path imports
try:
    from sqlalchemy import and_, select

    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.models.sys_user import SysUser
    from app.services.admin_appr_utils import build_host_table
    from shared.common.email_sender import send_email
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from sqlalchemy import and_, select

    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.models.sys_user import SysUser
    from app.services.admin_appr_utils import build_host_table
    from shared.common.email_sender import send_email
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class ApprovalEmailService:
    """Approval email service class

    Responsible for handling approval-related email sending logic.
    """

    def __init__(self) -> None:
        """Initialize email service"""

    async def send_approval_email(
        self,
        session: Any,
        results: List[Dict[str, Any]],
        appr_by: int,
        locale: str = "zh_CN",
    ) -> List[str]:
        """Send approval email notification

        Args:
            session: Database session
            results: Processing result list
            appr_by: Approver ID
            locale: Language preference

        Returns:
            List[str]: Error message list (if any)
        """
        email_errors: List[str] = []

        try:
            # Query email configuration
            email_conf_stmt = select(SysConf).where(
                and_(
                    SysConf.conf_key == "email",
                    SysConf.del_flag == 0,
                    SysConf.state_flag == 0,
                )
            )
            email_conf_result = await session.execute(email_conf_stmt)
            email_conf = email_conf_result.scalar_one_or_none()

            if not email_conf or not email_conf.conf_val:
                return email_errors

            # Parse email addresses
            email_list = [e.strip() for e in email_conf.conf_val.strip().split(",") if e.strip()]
            if not email_list:
                return email_errors

            # Get successfully approved host IDs
            successful_host_ids = [r["host_id"] for r in results if r.get("success", False) and r.get("host_id")]
            if not successful_host_ids:
                return email_errors

            # Query host information
            host_info_stmt = select(HostRec).where(
                and_(
                    HostRec.id.in_(successful_host_ids),
                    HostRec.del_flag == 0,
                )
            )
            host_info_result = await session.execute(host_info_stmt)
            host_recs = host_info_result.scalars().all()

            # Query approver information
            user_stmt = select(SysUser).where(
                and_(
                    SysUser.id == appr_by,
                    SysUser.del_flag == 0,
                )
            )
            user_result = await session.execute(user_stmt)
            sys_user = user_result.scalar_one_or_none()

            user_name = sys_user.user_name if sys_user else ""
            user_account = sys_user.user_account if sys_user else ""

            # Build email content
            # ✅ Filter out None and empty string hardware_id
            hardware_ids = [h.hardware_id for h in host_recs if h.hardware_id and h.hardware_id.strip()]
            host_ips = [h.host_ip for h in host_recs if h.host_ip]
            host_table = build_host_table(hardware_ids, host_ips)

            subject = t(
                "email.host.approve.subject",
                locale=locale,
                default="Changed Host Passed Hardware Change Approval",
            )

            content = t(
                "email.host.approve.content",
                locale=locale,
                user_name=user_name,
                user_account=user_account,
                host_table=host_table,
            )

            # Send email
            try:
                email_result = await send_email(
                    to_emails=email_list,
                    subject=subject,
                    content=content,
                    locale=locale,
                )
                if email_result.get("failed_count", 0) > 0:
                    email_errors.extend(email_result.get("errors", []))
                logger.info(
                    "Email notification sent completed",
                    extra={
                        "sent_count": email_result.get("sent_count", 0),
                        "failed_count": email_result.get("failed_count", 0),
                        "recipient_count": len(email_list),
                    },
                )
            except Exception as email_error:
                error_msg = f"Email sending exception: {email_error!s}"
                email_errors.append(error_msg)
                logger.warning(
                    "Email sending exception (does not affect transaction)",
                    extra={
                        "error": str(email_error),
                        "error_type": type(email_error).__name__,
                    },
                    exc_info=True,
                )

        except Exception as e:
            error_msg = f"Email notification processing exception: {e!s}"
            email_errors.append(error_msg)
            logger.warning(
                "Email notification processing exception (does not affect transaction)",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        return email_errors


# Module-level instance for external use
_email_service_instance: Optional[ApprovalEmailService] = None


def get_approval_email_service() -> ApprovalEmailService:
    """Get approval email service instance (singleton pattern)

    Returns:
        ApprovalEmailService: Email service instance
    """
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = ApprovalEmailService()
    return _email_service_instance


async def send_approval_email(
    session: Any,
    results: List[Dict[str, Any]],
    appr_by: int,
    locale: str = "zh_CN",
) -> List[str]:
    """Convenience function to send approval email

    Args:
        session: Database session
        results: Processing result list
        appr_by: Approver ID
        locale: Language preference

    Returns:
        List[str]: Error message list (if any)
    """
    email_service = get_approval_email_service()
    return await email_service.send_approval_email(session, results, appr_by, locale)
