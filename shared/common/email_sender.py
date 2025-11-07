"""邮件发送工具模块

提供异步邮件发送功能，支持多收件人。
"""

import os
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
    """发送邮件

    Args:
        to_emails: 收件人邮箱列表
        subject: 邮件主题
        content: 邮件内容
        locale: 语言代码（用于多语言支持）

    Returns:
        包含发送结果的字典：
        - success: 是否成功
        - sent_count: 成功发送的邮件数量
        - failed_count: 失败的邮件数量
        - errors: 错误信息列表

    Note:
        当前实现为占位符，实际项目中需要配置 SMTP 服务器
        邮件发送失败不影响业务流程，只记录日志
    """
    if not to_emails:
        logger.warning("收件人列表为空，跳过邮件发送")
        return {
            "success": False,
            "sent_count": 0,
            "failed_count": 0,
            "errors": ["收件人列表为空"],
        }

    sent_count = 0
    failed_count = 0
    errors: List[str] = []

    for email in to_emails:
        email = email.strip()
        if not email:
            continue

        try:
            # TODO: 实现实际的邮件发送逻辑
            # 示例：使用 smtplib 或第三方邮件服务
            # import smtplib
            # from email.mime.text import MIMEText
            # from email.mime.multipart import MIMEMultipart
            #
            # msg = MIMEMultipart()
            # msg['From'] = os.getenv("SMTP_FROM_EMAIL")
            # msg['To'] = email
            # msg['Subject'] = subject
            # msg.attach(MIMEText(content, 'html', 'utf-8'))
            #
            # smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
            # smtp_port = int(os.getenv("SMTP_PORT", "587"))
            # smtp_user = os.getenv("SMTP_USER")
            # smtp_***REMOVED***word = os.getenv("SMTP_PASSWORD")
            #
            # server = smtplib.SMTP(smtp_server, smtp_port)
            # server.starttls()
            # server.login(smtp_user, smtp_***REMOVED***word)
            # server.send_message(msg)
            # server.quit()

            logger.info(
                "邮件发送成功（模拟）",
                extra={
                    "to": email,
                    "subject": subject,
                    "locale": locale,
                },
            )
            sent_count += 1

        except Exception as e:
            error_msg = f"邮件发送失败: {email}, 错误: {str(e)}"
            logger.warning(
                "邮件发送失败",
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
