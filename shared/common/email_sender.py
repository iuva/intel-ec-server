"""Email sending utility module

Provides asynchronous email sending functionality, supporting multiple recipients.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import sys
from typing import Any, Dict, List

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


async def send_email(
    to_emails: List[str],
    subject: str,
    content: str,
    locale: str = "zh_CN",
) -> Dict[str, Any]:
    """Send email

    Args:
        to_emails: List of recipient email addresses
        subject: Email subject
        content: Email content
        locale: Language code (for multilingual support)

    Returns:
        Dictionary containing send results:
        - success: Whether successful
        - sent_count: Number of emails sent successfully
        - failed_count: Number of emails that failed to send
        - errors: List of error messages

    Note:
        Current implementation is a placeholder, SMTP server needs to be configured in actual project
        Email sending failure does not affect business process, only logs
    """
    if not to_emails:
        logger.warning("Recipient list is empty, skipping email sending")
        return {
            "success": False,
            "sent_count": 0,
            "failed_count": 0,
            "errors": ["Recipient list is empty"],
        }

    sent_count = 0
    failed_count = 0
    errors: List[str] = []

    for email in to_emails:
        email = email.strip()
        if not email:
            continue

        try:
            # TODO: Implement actual email sending logic
            # Example: Use smtplib or third-party email service
            msg = MIMEMultipart()
            smtp_from_email = os.getenv("SMTP_FROM_EMAIL")
            if not smtp_from_email:
                raise ValueError("SMTP_FROM_EMAIL environment variable not set")
            msg["From"] = smtp_from_email
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(content, "html", "utf-8"))

            smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_***REMOVED***word = os.getenv("SMTP_PASSWORD")

            if not smtp_user or not smtp_***REMOVED***word:
                raise ValueError("SMTP_USER or SMTP_PASSWORD environment variable not set")

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_***REMOVED***word)
            server.send_message(msg)
            server.quit()

            logger.info(
                "Email sent successfully (simulation)",
                extra={
                    "to": email,
                    "subject": subject,
                    "locale": locale,
                },
            )
            sent_count += 1

        except Exception as e:
            error_msg = f"Email sending failed: {email}, Error: {e!s}"
            logger.warning(
                "Email sending failed",
                extra={
                    "to": email,
                    "subject": subject,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "locale": locale,
                },
                exc_info=True,
            )
            errors.append(error_msg)
            failed_count += 1

    return {
        "success": sent_count > 0,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "errors": errors,
    }
