"""管理后台待审批主机管理 - 邮件服务模块

提供审批相关的邮件发送功能，包括邮件模板定义和发送逻辑。

从 admin_appr_host_service.py 拆分出来，提高代码可维护性。
"""

import os
import sys
from typing import Any, Dict, List, Optional

# 使用 try-except 方式处理路径导入
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

# 邮件内容模板常量
EMAIL_HOST_APPROVE_CONTENT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
            margin-bottom: 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 5px 5px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #4CAF50;
        }}
        .info-item {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}
        .info-item::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #4CAF50;
            font-weight: bold;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
        }}
        .info-value {{
            color: #333;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #888;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">硬件变更审核通知</h2>
    </div>
    <div class="content">
        <p style="font-size: 16px; margin-top: 0;">尊敬的维护人员：</p>

        <p style="font-size: 15px; color: #2c3e50; margin: 20px 0;">
            变更的 Host 已通过硬件变更审核。
        </p>

        <div class="section">
            <div class="section-title">审批人信息</div>
            <div class="info-item">
                <span class="info-label">用户名称：</span>
                <span class="info-value">{user_name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">登录账号：</span>
                <span class="info-value">{user_account}</span>
            </div>
        </div>

        <div class="section">
            <div class="section-title">变更的主机信息</div>
            {host_table}
        </div>

        <p style="margin-top: 25px; color: #555;">
            请及时关注相关变更。
        </p>

        <div class="footer">
            此邮件由系统自动发送，请勿回复。
        </div>
    </div>
</body>
</html>
"""


class ApprovalEmailService:
    """审批邮件服务类

    负责处理审批相关的邮件发送逻辑。
    """

    def __init__(self) -> None:
        """初始化邮件服务"""
        ***REMOVED***

    async def send_approval_email(
        self,
        session: Any,
        results: List[Dict[str, Any]],
        appr_by: int,
        locale: str = "zh_CN",
    ) -> List[str]:
        """发送审批邮件通知

        Args:
            session: 数据库会话
            results: 处理结果列表
            appr_by: 审批人ID
            locale: 语言偏好

        Returns:
            List[str]: 错误信息列表（如果有）
        """
        email_errors: List[str] = []

        try:
            # 查询邮件配置
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

            # 解析邮箱地址
            email_list = [e.strip() for e in email_conf.conf_val.strip().split(",") if e.strip()]
            if not email_list:
                return email_errors

            # 获取成功审批的主机ID
            successful_host_ids = [
                r["host_id"] for r in results if r.get("success", False) and r.get("host_id")
            ]
            if not successful_host_ids:
                return email_errors

            # 查询主机信息
            host_info_stmt = select(HostRec).where(
                and_(
                    HostRec.id.in_(successful_host_ids),
                    HostRec.del_flag == 0,
                )
            )
            host_info_result = await session.execute(host_info_stmt)
            host_recs = host_info_result.scalars().all()

            # 查询审批人信息
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

            # 构建邮件内容
            # ✅ 过滤掉 None 和空字符串的 hardware_id
            hardware_ids = [
                h.hardware_id
                for h in host_recs
                if h.hardware_id and h.hardware_id.strip()
            ]
            host_ips = [h.host_ip for h in host_recs if h.host_ip]
            host_table = build_host_table(hardware_ids, host_ips)

            subject = t(
                "email.host.approve.subject",
                locale=locale,
                default="变更 Host 通过硬件变更审核",
            )

            content = t(
                "email.host.approve.content",
                locale=locale,
                default=EMAIL_HOST_APPROVE_CONTENT_TEMPLATE,
                user_name=user_name,
                user_account=user_account,
                host_table=host_table,
            )

            # 发送邮件
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
                    "邮件通知发送完成",
                    extra={
                        "sent_count": email_result.get("sent_count", 0),
                        "failed_count": email_result.get("failed_count", 0),
                        "recipient_count": len(email_list),
                    },
                )
            except Exception as email_error:
                error_msg = f"邮件发送异常: {str(email_error)}"
                email_errors.append(error_msg)
                logger.warning(
                    "邮件发送异常（不影响事务）",
                    extra={
                        "error": str(email_error),
                        "error_type": type(email_error).__name__,
                    },
                    exc_info=True,
                )

        except Exception as e:
            error_msg = f"邮件通知处理异常: {str(e)}"
            email_errors.append(error_msg)
            logger.warning(
                "邮件通知处理异常（不影响事务）",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        return email_errors


# 模块级实例，供外部使用
_email_service_instance: Optional[ApprovalEmailService] = None


def get_approval_email_service() -> ApprovalEmailService:
    """获取审批邮件服务实例（单例模式）

    Returns:
        ApprovalEmailService: 邮件服务实例
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
    """发送审批邮件的便捷函数

    Args:
        session: 数据库会话
        results: 处理结果列表
        appr_by: 审批人ID
        locale: 语言偏好

    Returns:
        List[str]: 错误信息列表（如果有）
    """
    email_service = get_approval_email_service()
    return await email_service.send_approval_email(session, results, appr_by, locale)
