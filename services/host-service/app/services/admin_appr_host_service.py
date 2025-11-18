"""管理后台待审批主机管理服务

提供管理后台使用的待审批主机查询等核心业务逻辑。
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import and_, desc, func, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.constants.host_constants import (
        APPR_STATE_ENABLE,
        HOST_STATE_FREE,
        SYNC_STATE_WAIT,
    )
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.models.sys_user import SysUser
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailResponse,
        AdminApprHostHwInfo,
        AdminApprHostInfo,
        AdminApprHostListRequest,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.email_sender import send_email
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import (
        APPR_STATE_ENABLE,
        HOST_STATE_FREE,
        SYNC_STATE_WAIT,
    )
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailResponse,
        AdminApprHostHwInfo,
        AdminApprHostInfo,
        AdminApprHostListRequest,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.email_sender import send_email
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse

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


def _build_host_table(hardware_ids: List[str], host_ips: List[str]) -> str:
    """构建主机信息表格（HTML格式）

    Args:
        hardware_ids: Hardware ID 列表
        host_ips: Host IP 列表

    Returns:
        HTML 表格字符串
    """
    if not hardware_ids and not host_ips:
        return "无变更的主机信息"

    # 确保两个列表长度一致（用空字符串填充）
    max_len = max(len(hardware_ids), len(host_ips))
    hardware_ids_padded = hardware_ids + [""] * (max_len - len(hardware_ids))
    host_ips_padded = host_ips + [""] * (max_len - len(host_ips))

    # 构建 HTML 表格
    table_rows = []
    cell_style = "padding: 12px; border: 1px solid #ddd; text-align: left;"
    header_style = (
        "padding: 12px; border: 1px solid #ddd; background-color: #4CAF50; "
        "color: white; text-align: left; font-weight: 600;"
    )
    row_style = "background-color: white;"
    alternate_row_style = "background-color: #f9f9f9;"

    for i in range(max_len):
        hw_id = hardware_ids_padded[i] if i < len(hardware_ids) else ""
        host_ip = host_ips_padded[i] if i < len(host_ips) else ""
        row_bg = alternate_row_style if i % 2 == 1 else row_style
        row_html = (
            f"<tr style='{row_bg}'>"
            f"<td style='{cell_style}'>{hw_id or '-'}</td>"
            f"<td style='{cell_style}'>{host_ip or '-'}</td>"
            f"</tr>"
        )
        table_rows.append(row_html)

    table_style = (
        "border-collapse: collapse; width: 100%; margin: 15px 0; "
        "border-radius: 5px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
    )
    table_html = f"""
<table style='{table_style}'>
    <thead>
        <tr>
            <th style='{header_style}'>Hardware ID</th>
            <th style='{header_style}'>Host IP</th>
        </tr>
    </thead>
    <tbody>
        {"".join(table_rows)}
    </tbody>
</table>
"""

    return table_html


class AdminApprHostService:
    """管理后台待审批主机管理服务类

    提供待审批主机的查询、搜索等业务逻辑。
    """

    @handle_service_errors(
        error_message="查询待审批主机列表失败",
        error_code="QUERY_APPR_HOST_LIST_FAILED",
    )
    async def list_appr_hosts(
        self,
        request: AdminApprHostListRequest,
    ) -> Tuple[List[AdminApprHostInfo], PaginationResponse]:
        """查询待审批主机列表（分页）

        业务逻辑：
        1. 查询 host_rec 表
        2. 条件：host_state > 4 且 host_state < 8，appr_state != 1，del_flag = 0
        3. 支持按 mac、mg_id、host_state 过滤
        4. 按 created_time 倒序排序

        Args:
            request: 查询请求参数（分页、搜索条件）

        Returns:
            Tuple[List[AdminApprHostInfo], PaginationResponse]: 待审批主机列表和分页信息

        Raises:
            BusinessError: 查询失败时
        """
        logger.info(
            "开始查询待审批主机列表",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "mg_id": request.mg_id,
                "host_state": request.host_state,
            },
        )

        try:
            session_factory = mariadb_manager.get_session()
            logger.debug("获取数据库会话工厂成功")
        except Exception as e:
            logger.error(
                "获取数据库会话工厂失败",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

        try:
            async with session_factory() as session:
                logger.debug("数据库会话创建成功")

                # 构建基础查询条件
                # host_state > 4 且 host_state < 8，appr_state != 1，del_flag = 0
                base_conditions = [
                    HostRec.host_state > 4,
                    HostRec.host_state < 8,
                    HostRec.appr_state != 1,
                    HostRec.del_flag == 0,
                ]

                # 添加搜索条件
                if request.mac:
                    base_conditions.append(HostRec.mac_addr.like(f"%{request.mac}%"))

                if request.mg_id:
                    base_conditions.append(HostRec.mg_id.like(f"%{request.mg_id}%"))

                if request.host_state is not None:
                    base_conditions.append(HostRec.host_state == request.host_state)

                # 构建子查询：获取每个 host_id 对应的最新 host_hw_rec 记录的 diff_state
                # 1. 获取每个 host_id 的最大 created_time
                max_time_subquery = (
                    select(
                        HostHwRec.host_id,
                        func.max(HostHwRec.created_time).label("max_created_time"),
                    )
                    .where(HostHwRec.del_flag == 0)
                    .group_by(HostHwRec.host_id)
                    .subquery()
                )

                # 2. 获取每个 host_id 的最大 id（当 created_time 相同时，确保唯一性）
                # ✅ 修复：使用正确的 SQLAlchemy 2.0 join 语法
                # 使用 select_from() 配合 join() 在表对象上
                max_id_subquery = (
                    select(
                        HostHwRec.host_id,
                        func.max(HostHwRec.id).label("max_id"),
                    )
                    .select_from(
                        HostHwRec.__table__.join(
                            max_time_subquery,
                            and_(
                                HostHwRec.host_id == max_time_subquery.c.host_id,
                                HostHwRec.created_time == max_time_subquery.c.max_created_time,
                                HostHwRec.del_flag == 0,
                            ),
                        )
                    )
                    .group_by(HostHwRec.host_id)
                    .subquery()
                )

                # 3. 获取最新硬件记录的 diff_state
                # ✅ 修复：使用正确的 SQLAlchemy 2.0 join 语法
                # 使用 select_from() 配合 join() 在表对象上
                latest_hw_subquery = (
                    select(
                        HostHwRec.host_id,
                        HostHwRec.diff_state,
                    )
                    .select_from(
                        HostHwRec.__table__.join(
                            max_id_subquery,
                            HostHwRec.id == max_id_subquery.c.max_id,
                        )
                    )
                    .subquery()
                )

                # 1. 查询总数
                count_stmt = select(func.count(HostRec.id)).where(and_(*base_conditions))
                count_result = await session.execute(count_stmt)
                total = count_result.scalar() or 0

                # 2. 分页查询：按 created_time 倒序排序，LEFT JOIN 获取 diff_state
                pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

                stmt = (
                    select(
                        HostRec.id.label("host_id"),
                        HostRec.mg_id,
                        HostRec.mac_addr,
                        HostRec.host_state,
                        HostRec.subm_time,
                        latest_hw_subquery.c.diff_state,
                    )
                    .outerjoin(
                        latest_hw_subquery,
                        HostRec.id == latest_hw_subquery.c.host_id,
                    )
                    .where(and_(*base_conditions))
                    .order_by(HostRec.created_time.desc())
                    .offset(pagination_params.offset)
                    .limit(pagination_params.limit)
                )

                try:
                    result = await session.execute(stmt)
                    rows = result.all()
                except Exception as e:
                    logger.error(
                        "执行查询失败",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "sql_preview": str(stmt)[:500] if hasattr(stmt, "__str__") else "N/A",
                        },
                        exc_info=True,
                    )
                    raise

                # 3. 构建响应数据
                host_info_list: List[AdminApprHostInfo] = []
                for row in rows:
                    try:
                        # 安全获取 diff_state，因为 LEFT JOIN 可能返回 None
                        diff_state = getattr(row, "diff_state", None)

                        host_info = AdminApprHostInfo(
                            host_id=str(row.host_id),  # ✅ 转换为字符串避免精度丢失
                            mg_id=row.mg_id,
                            mac_addr=row.mac_addr,
                            host_state=row.host_state,
                            subm_time=row.subm_time,
                            diff_state=diff_state,
                        )
                        host_info_list.append(host_info)
                    except Exception as e:
                        logger.error(
                            "构建 AdminApprHostInfo 对象失败",
                            extra={
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "row_host_id": getattr(row, "host_id", None),
                                "row_mg_id": getattr(row, "mg_id", None),
                                "row_keys": [key for key in dir(row) if not key.startswith("_")],
                            },
                            exc_info=True,
                        )
                        raise

                # 4. 构建分页响应
                pagination_response = PaginationResponse(
                    page=request.page,
                    page_size=request.page_size,
                    total=total,
                )

                logger.info(
                    "查询待审批主机列表完成",
                    extra={
                        "total": total,
                        "returned_count": len(host_info_list),
                        "page": request.page,
                        "page_size": request.page_size,
                    },
                )

                return host_info_list, pagination_response
        except Exception as e:
            logger.error(
                f"数据库操作失败: {type(e).__name__}: {str(e)}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": "list_appr_hosts",
                },
                exc_info=True,
            )
            raise

    @handle_service_errors(
        error_message="查询待审批主机详情失败",
        error_code="QUERY_APPR_HOST_DETAIL_FAILED",
    )
    async def get_appr_host_detail(self, host_id: int, locale: str = "zh_CN") -> AdminApprHostDetailResponse:
        """查询待审批主机详情

        业务逻辑：
        1. 查询 host_rec 表 id = host_id 的数据
        2. 关联 host_hw_rec 表，查询 sync_state = 1 的数据
        3. 按 host_hw_rec.created_time 倒序排序
        4. 密码字段需要 AES 解密

        Args:
            host_id: 主机ID（host_rec.id）

        Returns:
            AdminApprHostDetailResponse: 待审批主机详情信息

        Raises:
            BusinessError: 主机不存在时
        """
        logger.info(
            "开始查询待审批主机详情",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 验证主机是否存在且未删除（使用工具函数）
            host_rec = await validate_host_exists(session, HostRec, host_id, locale=locale)

            # 2. 查询 host_hw_rec 表 sync_state=1 的所有记录（按 created_time 倒序）
            hw_stmt = (
                select(HostHwRec)
                .where(
                    and_(
                        HostHwRec.host_id == host_id,
                        HostHwRec.sync_state == SYNC_STATE_WAIT,  # sync_state = 1（待同步）
                        HostHwRec.del_flag == 0,
                    )
                )
                .order_by(HostHwRec.created_time.desc())
            )
            hw_result = await session.execute(hw_stmt)
            hw_recs = hw_result.scalars().all()

            # 3. 解密密码（AES加密）
            ***REMOVED*** = None
            if host_rec.host_pwd:
                try:
                    ***REMOVED*** = aes_decrypt(host_rec.host_pwd)
                    if ***REMOVED***:
                        logger.debug(
                            "密码解密成功",
                            extra={
                                "host_id": host_id,
                            },
                        )
                    else:
                        logger.warning(
                            "密码解密失败（返回None）",
                            extra={
                                "host_id": host_id,
                                "note": "可能是密码格式不正确或加密方式不匹配",
                            },
                        )
                except Exception as e:
                    logger.warning(
                        "密码解密异常",
                        extra={
                            "host_id": host_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    # 解密失败时返回 None，而不是抛出异常
                    ***REMOVED*** = None

            # 4. 构建硬件信息列表
            hw_list: List[AdminApprHostHwInfo] = []
            for hw_rec in hw_recs:
                hw_info = AdminApprHostHwInfo(
                    created_time=hw_rec.created_time,
                    hw_info=hw_rec.hw_info,
                )
                hw_list.append(hw_info)

            # 5. 构建响应数据
            detail = AdminApprHostDetailResponse(
                mg_id=host_rec.mg_id,
                mac=host_rec.mac_addr,
                ip=host_rec.host_ip,
                username=host_rec.host_acct,
                ***REMOVED***word=***REMOVED***,
                port=host_rec.host_port,
                host_state=host_rec.host_state,
                hw_list=hw_list,
            )

            logger.info(
                "查询待审批主机详情完成",
                extra={
                    "host_id": host_id,
                    "hw_list_count": len(hw_list),
                    "has_***REMOVED***word": ***REMOVED*** is not None,
                },
            )

            return detail

    @handle_service_errors(
        error_message="同意启用主机失败",
        error_code="APPROVE_HOST_FAILED",
    )
    async def approve_hosts(
        self, request: AdminApprHostApproveRequest, appr_by: int, locale: str = "zh_CN"
    ) -> AdminApprHostApproveResponse:
        """同意启用主机（管理后台）

        业务逻辑（diff_type = 2 时）：
        1. 根据传入的 host_ids，查询所有 host_hw_rec 表 host_id = id, sync_state = 1 的数据
        2. 最新一条数据：sync_state = 2, appr_time = now(), appr_by = appr_by
        3. 其他数据：sync_state = 4
        4. 修改 host_rec 表：appr_state = 1, host_state = 0, hw_id = host_hw_rec 最新一条数据的 id, subm_time = now()
        5. TODO: 调用外部 API 同步 host_hw_rec 最新数据的 hw_info

        Args:
            request: 同意启用请求参数（diff_type, host_ids）
            appr_by: 审批人ID（从 token 中获取）

        Returns:
            AdminApprHostApproveResponse: 包含处理结果和统计信息

        Raises:
            BusinessError: 参数验证失败或业务逻辑错误时
        """
        logger.info(
            "开始同意启用主机",
            extra={
                "diff_type": request.diff_type,
                "host_ids": request.host_ids,
                "appr_by": appr_by,
            },
        )

        # 参数验证和 host_ids 处理
        host_ids_to_process: List[int] = []

        if request.diff_type == 2:
            # diff_type = 2 时，host_ids 为必填
            if not request.host_ids or len(request.host_ids) == 0:
                raise BusinessError(
                    message="当 diff_type=2 时，host_ids 为必填参数",
                    message_key="error.host.appr_host_ids_required",
                    error_code="HOST_IDS_REQUIRED",
                    code=ServiceErrorCodes.VALIDATION_ERROR,
                    http_status_code=400,
                )
            host_ids_to_process = request.host_ids

        elif request.diff_type == 1:
            # diff_type = 1 时，如果传入了 host_ids，逻辑与 diff_type = 2 相同
            if request.host_ids and len(request.host_ids) > 0:
                host_ids_to_process = request.host_ids
            else:
                # 如果未传入 host_ids，需要查询所有 host_hw_rec 表 sync_state = 1, diff_state = 1 数据的 host_id
                session_factory = mariadb_manager.get_session()
                async with session_factory() as temp_session:
                    hw_query_stmt = (
                        select(HostHwRec.host_id)
                        .where(
                            and_(
                                HostHwRec.sync_state == 1,
                                HostHwRec.diff_state == 1,
                                HostHwRec.del_flag == 0,
                            )
                        )
                        .distinct()
                    )
                    hw_query_result = await temp_session.execute(hw_query_stmt)
                    host_ids_raw = hw_query_result.scalars().all()
                    host_ids_to_process = [hid for hid in set(host_ids_raw) if hid is not None]

                if not host_ids_to_process:
                    logger.info(
                        "未找到符合条件的主机（diff_type=1, sync_state=1, diff_state=1）",
                        extra={"diff_type": request.diff_type},
                    )
                    return AdminApprHostApproveResponse(
                        success_count=0,
                        failed_count=0,
                        results=[],
                    )
        else:
            raise BusinessError(
                message=t(
                    "error.host.diff_type_not_supported",
                    locale=locale,
                    diff_type=request.diff_type,
                    default=f"不支持的 diff_type: {request.diff_type}",
                ),
                message_key="error.host.diff_type_not_supported",
                error_code="DIFF_TYPE_NOT_SUPPORTED",
                code=ServiceErrorCodes.VALIDATION_ERROR,
                http_status_code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            try:
                success_count = 0
                failed_count = 0
                results: List[Dict[str, Any]] = []

                now = datetime.now(timezone.utc)

                # 优化：批量查询所有主机信息（避免 N+1 查询）
                host_stmt = select(HostRec).where(
                    and_(
                        HostRec.id.in_(host_ids_to_process),
                        HostRec.del_flag == 0,
                    )
                )
                host_result = await session.execute(host_stmt)
                host_recs_map = {host.id: host for host in host_result.scalars().all()}

                # 优化：批量查询所有硬件记录（避免 N+1 查询）
                # 查询所有符合条件的硬件记录（包括最新和其他）
                hw_rec_stmt = (
                    select(HostHwRec)
                    .where(
                        and_(
                            HostHwRec.host_id.in_(host_ids_to_process),
                            HostHwRec.sync_state == 1,
                            HostHwRec.del_flag == 0,
                        )
                    )
                    .order_by(HostHwRec.host_id, desc(HostHwRec.created_time), desc(HostHwRec.id))
                )
                hw_rec_result = await session.execute(hw_rec_stmt)
                all_hw_recs = hw_rec_result.scalars().all()

                # 按 host_id 组织硬件记录
                hw_recs_by_host: Dict[int, List[HostHwRec]] = {}
                for hw_rec in all_hw_recs:
                    if hw_rec.host_id not in hw_recs_by_host:
                        hw_recs_by_host[hw_rec.host_id] = []
                    hw_recs_by_host[hw_rec.host_id].append(hw_rec)

                # 准备批量更新的数据
                latest_hw_ids_to_update: List[int] = []
                other_hw_ids_to_update: List[int] = []
                host_updates: Dict[int, Dict[str, Any]] = {}

                # 处理每个主机
                for host_id in host_ids_to_process:
                    try:
                        # 1. 验证主机是否存在且未删除
                        host_rec = host_recs_map.get(host_id)
                        if not host_rec:
                            results.append(
                                {
                                    "host_id": host_id,
                                    "success": False,
                                    "message": t("error.host.not_found", locale=locale, host_id=host_id),
                                }
                            )
                            failed_count += 1
                            continue

                        # 2. 获取该主机的硬件记录
                        hw_recs = hw_recs_by_host.get(host_id, [])

                        if not hw_recs:
                            results.append(
                                {
                                    "host_id": host_id,
                                    "success": False,
                                    "message": t(
                                        "error.host.hardware_not_found",
                                        locale=locale,
                                        host_id=host_id,
                                        default=f"未找到待审批的硬件记录（ID: {host_id}）",
                                    ),
                                }
                            )
                            failed_count += 1
                            continue

                        # 3. 获取最新一条数据（已按时间倒序排列）
                        latest_hw_rec = hw_recs[0]
                        latest_hw_id = latest_hw_rec.id

                        # 4. 收集需要更新的数据
                        latest_hw_ids_to_update.append(latest_hw_id)

                        # 5. 收集其他需要更新的硬件记录ID
                        if len(hw_recs) > 1:
                            other_hw_ids_to_update.extend([hw.id for hw in hw_recs[1:]])

                        # 6. 收集主机更新信息
                        host_updates[host_id] = {
                            "appr_state": APPR_STATE_ENABLE,
                            "host_state": HOST_STATE_FREE,
                            "hw_id": latest_hw_id,
                            "subm_time": now,
                        }

                        # 7. TODO: 调用外部 API 同步 host_hw_rec 最新数据的 hw_info
                        # TODO: 实现外部 API 调用逻辑
                        # 示例：await external_api.sync_hardware_info(latest_hw_rec.hw_info)

                        results.append(
                            {
                                "host_id": host_id,
                                "success": True,
                                "message": t("success.host.approved", locale=locale, default="主机启用成功"),
                                "hw_id": latest_hw_id,
                            }
                        )
                        success_count += 1

                    except Exception as e:
                        logger.error(
                            f"处理主机 {host_id} 时发生异常",
                            extra={
                                "host_id": host_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        results.append(
                            {
                                "host_id": host_id,
                                "success": False,
                                "message": t(
                                    "error.host.process_failed",
                                    locale=locale,
                                    host_id=host_id,
                                    error=str(e),
                                    default=f"处理失败: {str(e)}",
                                ),
                            }
                        )
                        failed_count += 1
                        continue

                # 批量更新操作
                if latest_hw_ids_to_update:
                    # 批量更新最新硬件记录
                    update_latest_stmt = (
                        update(HostHwRec)
                        .where(HostHwRec.id.in_(latest_hw_ids_to_update))
                        .values(
                            sync_state=2,
                            appr_time=now,
                            appr_by=appr_by,
                        )
                    )
                    await session.execute(update_latest_stmt)

                if other_hw_ids_to_update:
                    # 批量更新其他硬件记录
                    update_other_stmt = (
                        update(HostHwRec).where(HostHwRec.id.in_(other_hw_ids_to_update)).values(sync_state=4)
                    )
                    await session.execute(update_other_stmt)

                if host_updates:
                    bulk_update_data = [
                        {"id": host_id, **update_values} for host_id, update_values in host_updates.items()
                    ]
                    # 使用同步会话的 bulk_update_mappings 进行批量更新

                    def _bulk_update(sync_session: Any) -> None:
                        sync_session.bulk_update_mappings(HostRec, bulk_update_data)

                    await session.run_sync(_bulk_update)

                # 提交事务
                await session.commit()

                logger.info(
                    "同意启用主机处理完成",
                    extra={
                        "diff_type": request.diff_type,
                        "total_count": len(host_ids_to_process),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "appr_by": appr_by,
                    },
                )

                # 邮件通知逻辑（在所有数据处理完毕后）
                email_notification_errors: List[str] = []
                try:
                    # 1. 查询 sys_conf 表 conf_key = "email" 的 conf_val
                    email_conf_stmt = select(SysConf).where(
                        and_(
                            SysConf.conf_key == "email",
                            SysConf.del_flag == 0,
                            SysConf.state_flag == 0,  # 启用状态
                        )
                    )
                    email_conf_result = await session.execute(email_conf_stmt)
                    email_conf = email_conf_result.scalar_one_or_none()

                    if email_conf and email_conf.conf_val:
                        email_str = email_conf.conf_val.strip()
                        if email_str:
                            # 2. 分割邮箱地址（支持逗号分隔）
                            email_list = [e.strip() for e in email_str.split(",") if e.strip()]

                            if email_list:
                                # 3. 查询 host_rec 表 id in (host_ids) 的数据，获取 hardware_id 和 host_ip
                                successful_host_ids = [
                                    r["host_id"] for r in results if r.get("success", False) and r.get("host_id")
                                ]

                                if successful_host_ids:
                                    host_info_stmt = select(HostRec).where(
                                        and_(
                                            HostRec.id.in_(successful_host_ids),
                                            HostRec.del_flag == 0,
                                        )
                                    )
                                    host_info_result = await session.execute(host_info_stmt)
                                    host_recs = host_info_result.scalars().all()

                                    # 4. 查询 sys_user 表 id = appr_by 的数据，获取 user_name 和 user_account
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

                                    # 5. 构建邮件内容
                                    hardware_ids = [h.hardware_id for h in host_recs if h.hardware_id]
                                    host_ips = [h.host_ip for h in host_recs if h.host_ip]

                                    # 构建主机信息表格
                                    host_table = _build_host_table(hardware_ids, host_ips)

                                    # 使用多语言支持（从参数传入）
                                    subject = t(
                                        "email.host.approve.subject",
                                        locale=locale,
                                        default="变更 Host 通过硬件变更审核",
                                    )

                                    # 构建邮件正文（使用常量模板）
                                    content = t(
                                        "email.host.approve.content",
                                        locale=locale,
                                        default=EMAIL_HOST_APPROVE_CONTENT_TEMPLATE,
                                        user_name=user_name,
                                        user_account=user_account,
                                        host_table=host_table,
                                    )

                                    # 6. 发送邮件（失败不影响全局事务）
                                    try:
                                        email_result = await send_email(
                                            to_emails=email_list,
                                            subject=subject,
                                            content=content,
                                            locale=locale,
                                        )
                                        if email_result.get("failed_count", 0) > 0:
                                            email_notification_errors.extend(email_result.get("errors", []))
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
                                        email_notification_errors.append(error_msg)
                                        logger.warning(
                                            "邮件发送异常（不影响事务）",
                                            extra={
                                                "error": str(email_error),
                                                "error_type": type(email_error).__name__,
                                            },
                                            exc_info=True,
                                        )

                except Exception as email_query_error:
                    # 邮件查询或发送失败不影响全局事务
                    error_msg = f"邮件通知处理异常: {str(email_query_error)}"
                    email_notification_errors.append(error_msg)
                    logger.warning(
                        "邮件通知处理异常（不影响事务）",
                        extra={
                            "error": str(email_query_error),
                            "error_type": type(email_query_error).__name__,
                        },
                        exc_info=True,
                    )

                # 构建响应，包含邮件通知错误信息（如果有）
                response_data = AdminApprHostApproveResponse(
                    success_count=success_count,
                    failed_count=failed_count,
                    results=results,
                )

                # 如果有邮件通知错误，添加到响应中（不影响成功状态）
                if email_notification_errors:
                    # 在 results 中添加邮件通知错误信息
                    response_data.results.append(
                        {
                            "type": "email_notification",
                            "success": False,
                            "message": "; ".join(email_notification_errors),
                        }
                    )

                return response_data

            except Exception as e:
                # 回滚事务
                await session.rollback()
                logger.error(
                    "同意启用主机事务回滚",
                    extra={
                        "diff_type": request.diff_type,
                        "host_ids": request.host_ids,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"同意启用主机失败: {str(e)}",
                    message_key="error.host.approve_failed",
                    error_code="APPROVE_HOST_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "diff_type": request.diff_type,
                        "host_ids": request.host_ids,
                        "error": str(e),  # ✅ 添加 error 字段用于翻译格式化
                    },
                )

    @handle_service_errors(
        error_message="设置维护通知邮箱失败",
        error_code="SET_MAINTAIN_EMAIL_FAILED",
    )
    async def set_maintain_email(
        self, request: AdminMaintainEmailRequest, operator_id: int
    ) -> AdminMaintainEmailResponse:
        """设置维护通知邮箱（管理后台）

        业务逻辑：
        1. 格式化邮箱：去除空格，全角逗号转为半角逗号
        2. 查询 sys_conf 表，conf_key = "email"
        3. 如果不存在则插入，如果存在则更新 conf_val

        Args:
            request: 维护通知邮箱设置请求参数
            operator_id: 操作人ID（从 token 中获取）

        Returns:
            AdminMaintainEmailResponse: 包含设置结果

        Raises:
            BusinessError: 参数验证失败或数据库操作失败时
        """
        logger.info(
            "开始设置维护通知邮箱",
            extra={
                "email": request.email,
                "operator_id": operator_id,
            },
        )

        # 1. 格式化邮箱：去除空格，全角逗号转为半角逗号
        formatted_email = request.email.strip()
        # 去除所有空格
        formatted_email = "".join(formatted_email.split())
        # 全角逗号（，）转为半角逗号（,）
        formatted_email = formatted_email.replace("，", ",")
        # 去除多余逗号（连续逗号）
        while ",," in formatted_email:
            formatted_email = formatted_email.replace(",,", ",")
        # 去除首尾逗号
        formatted_email = formatted_email.strip(",")

        if not formatted_email:
            raise BusinessError(
                message="邮箱地址不能为空",
                message_key="error.email.empty",
                error_code="EMAIL_EMPTY",
                code=ServiceErrorCodes.VALIDATION_ERROR,
                http_status_code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            try:
                # 2. 查询 sys_conf 表，conf_key = "email"
                stmt = select(SysConf).where(
                    and_(
                        SysConf.conf_key == "email",
                        SysConf.del_flag == 0,
                    )
                )
                result = await session.execute(stmt)
                sys_conf_rows = result.scalars().all()
                sys_conf = sys_conf_rows[0] if sys_conf_rows else None
                duplicate_ids = [conf.id for conf in sys_conf_rows[1:]]
                if duplicate_ids:
                    logger.warning(
                        "检测到重复的维护通知邮箱配置，自动清理多余记录",
                        extra={"duplicate_ids": duplicate_ids},
                    )
                    cleanup_stmt = (
                        update(SysConf)
                        .where(SysConf.id.in_(duplicate_ids))
                        .values(del_flag=1, updated_by=operator_id)
                    )
                    await session.execute(cleanup_stmt)

                if sys_conf:
                    # 3. 如果存在则更新
                    update_stmt = (
                        update(SysConf)
                        .where(SysConf.id == sys_conf.id)
                        .values(
                            conf_val=formatted_email,
                            updated_by=operator_id,
                        )
                    )
                    await session.execute(update_stmt)
                    logger.info(
                        "维护通知邮箱已更新",
                        extra={
                            "conf_id": sys_conf.id,
                            "old_email": sys_conf.conf_val,
                            "new_email": formatted_email,
                            "operator_id": operator_id,
                        },
                    )
                else:
                    # 4. 如果不存在则插入
                    new_sys_conf = SysConf(
                        conf_key="email",
                        conf_val=formatted_email,
                        conf_name="维护通知邮箱",
                        state_flag=0,  # 启用状态
                        created_by=operator_id,
                        updated_by=operator_id,
                    )
                    session.add(new_sys_conf)
                    logger.info(
                        "维护通知邮箱已创建",
                        extra={
                            "conf_key": "email",
                            "conf_val": formatted_email,
                            "operator_id": operator_id,
                        },
                    )

                # 提交事务
                await session.commit()

                logger.info(
                    "设置维护通知邮箱完成",
                    extra={
                        "conf_key": "email",
                        "conf_val": formatted_email,
                        "operator_id": operator_id,
                        "operation": "updated" if sys_conf else "created",
                    },
                )

                return AdminMaintainEmailResponse(
                    conf_key="email",
                    conf_val=formatted_email,
                )

            except Exception as e:
                # 回滚事务
                await session.rollback()
                logger.error(
                    "设置维护通知邮箱事务回滚",
                    extra={
                        "email": formatted_email,
                        "operator_id": operator_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"设置维护通知邮箱失败: {str(e)}",
                    message_key="error.email.set_failed",
                    error_code="SET_MAINTAIN_EMAIL_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "email": formatted_email,
                        "error": str(e),
                    },
                )

    @handle_service_errors(
        error_message="获取维护通知邮箱失败",
        error_code="GET_MAINTAIN_EMAIL_FAILED",
    )
    async def get_maintain_email(self) -> AdminMaintainEmailResponse:
        """获取维护通知邮箱（管理后台）

        业务逻辑：
        1. 查询 sys_conf 表，conf_key = "email", state_flag = 0, del_flag = 0
        2. 返回 conf_val 值

        Returns:
            AdminMaintainEmailResponse: 包含邮箱配置信息

        Raises:
            BusinessError: 数据库操作失败时
        """
        logger.info("开始获取维护通知邮箱")

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            try:
                # 查询 sys_conf 表
                stmt = (
                    select(SysConf)
                    .where(
                        and_(
                            SysConf.conf_key == "email",
                            SysConf.state_flag == 0,
                            SysConf.del_flag == 0,
                        )
                    )
                    .limit(1)
                )

                result = await session.execute(stmt)
                sys_conf = result.scalar_one_or_none()

                if not sys_conf:
                    # 如果不存在，返回空字符串
                    logger.info("维护通知邮箱配置不存在，返回空值")
                    return AdminMaintainEmailResponse(
                        conf_key="email",
                        conf_val="",
                    )

                # 返回配置值
                conf_val = sys_conf.conf_val or ""
                logger.info(
                    "获取维护通知邮箱成功",
                    extra={
                        "conf_key": sys_conf.conf_key,
                        "conf_val_length": len(conf_val),
                    },
                )

                return AdminMaintainEmailResponse(
                    conf_key="email",
                    conf_val=conf_val,
                )

            except Exception as e:
                logger.error(
                    "获取维护通知邮箱失败",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"获取维护通知邮箱失败: {str(e)}",
                    message_key="error.email.get_failed",
                    error_code="GET_MAINTAIN_EMAIL_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                )
