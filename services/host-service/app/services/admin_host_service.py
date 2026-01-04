"""管理后台主机管理服务

提供管理后台使用的主机查询、搜索等核心业务逻辑。
"""

import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_OFFLINE
    from app.models.host_exec_log import HostExecLog
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.schemas.host import (
        AdminHostExecLogListRequest,
        AdminHostExecLogInfo,
        AdminHostInfo,
        AdminHostListRequest,
    )
    from app.utils.logging_helpers import log_operation_completed, log_operation_start

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_encrypt, aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.constants.host_constants import HOST_STATE_FREE, HOST_STATE_OFFLINE
    from app.models.host_exec_log import HostExecLog
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.schemas.host import (
        AdminHostExecLogListRequest,
        AdminHostExecLogInfo,
        AdminHostInfo,
        AdminHostListRequest,
    )
    from app.utils.logging_helpers import log_operation_completed, log_operation_start

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_encrypt, aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse

logger = get_logger(__name__)


class AdminHostService:
    """管理后台主机管理服务类

    负责管理后台的主机查询、搜索等操作。
    """

    @handle_service_errors(
        error_message="查询主机列表失败",
        error_code="QUERY_HOST_LIST_FAILED",
    )
    async def list_hosts(
        self,
        request: AdminHostListRequest,
    ) -> Tuple[List[AdminHostInfo], PaginationResponse]:
        """查询可用主机列表（分页、搜索）

        业务逻辑：
        1. 查询 host_rec 表，条件：host_state = 0, appr_state = 1, del_flag = 0
        2. 关联 host_exec_log 表，获取每个 host_id 的最新一条记录（按 created_time 倒序）
        3. 支持按 use_by（user_name）过滤
        4. 按 host_rec.created_time 倒序排序

        Args:
            request: 查询请求参数

        Returns:
            Tuple[List[AdminHostInfo], PaginationResponse]: 主机列表和分页信息

        Raises:
            BusinessError: 查询失败时
        """
        log_operation_start(
            "查询可用主机列表",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "username": request.username,
                "host_state": request.host_state,
                "mg_id": request.mg_id,
                "use_by": request.use_by,
            },
            logger_instance=logger,
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建子查询：获取每个 host_id 的最新一条 host_exec_log 记录
            # 方法：先获取每个 host_id 的最大 created_time，如果相同则取 id 最大的
            max_time_subquery = (
                select(
                    HostExecLog.host_id,
                    func.max(HostExecLog.created_time).label("max_created_time"),
                )
                .where(HostExecLog.del_flag == 0)
                .group_by(HostExecLog.host_id)
                .subquery()
            )

            # 获取每个 host_id 的最大 id（当 created_time 相同时）
            # ✅ 修复：使用正确的 SQLAlchemy 2.0 join 语法
            # 使用 select_from() 配合 join() 在表对象上
            max_id_subquery = (
                select(
                    HostExecLog.host_id,
                    func.max(HostExecLog.id).label("max_id"),
                )
                .select_from(
                    HostExecLog.__table__.join(
                        max_time_subquery,
                        and_(
                            HostExecLog.host_id == max_time_subquery.c.host_id,
                            HostExecLog.created_time == max_time_subquery.c.max_created_time,
                            HostExecLog.del_flag == 0,
                        ),
                    )
                )
                .group_by(HostExecLog.host_id)
                .subquery()
            )

            # 获取最新执行日志的完整记录（使用 id 确保唯一性）
            # ✅ 修复：使用正确的 SQLAlchemy 2.0 join 语法
            latest_log_subquery = (
                select(HostExecLog.host_id, HostExecLog.user_name)
                .select_from(
                    HostExecLog.__table__.join(
                        max_id_subquery,
                        HostExecLog.id == max_id_subquery.c.max_id,
                    )
                )
                .subquery()
            )

            # 主查询：JOIN host_rec 和最新的 host_exec_log
            # 基础条件：host_state = 0, appr_state = 1, del_flag = 0
            base_conditions = [
                HostRec.host_state == 0,
                HostRec.appr_state == 1,
                HostRec.del_flag == 0,
            ]

            # 添加搜索条件（过滤空字符串）
            if request.mac and request.mac.strip():
                base_conditions.append(HostRec.mac_addr.like(f"%{request.mac.strip()}%"))

            if request.username and request.username.strip():
                base_conditions.append(HostRec.host_acct.like(f"%{request.username.strip()}%"))

            # 注意：host_state 参数已移除，因为基础条件已固定为 host_state = 0

            if request.mg_id and request.mg_id.strip():
                base_conditions.append(HostRec.mg_id.like(f"%{request.mg_id.strip()}%"))

            # 如果指定了 use_by 过滤条件，需要重新构建子查询并添加过滤
            if request.use_by and request.use_by.strip():
                # 重新获取最大 id，但这次要过滤 user_name
                # ✅ 修复：使用正确的 SQLAlchemy 2.0 join 语法
                max_id_with_filter_subquery = (
                    select(
                        HostExecLog.host_id,
                        func.max(HostExecLog.id).label("max_id"),
                    )
                    .select_from(
                        HostExecLog.__table__.join(
                            max_time_subquery,
                            and_(
                                HostExecLog.host_id == max_time_subquery.c.host_id,
                                HostExecLog.created_time == max_time_subquery.c.max_created_time,
                                HostExecLog.del_flag == 0,
                                HostExecLog.user_name.like(f"%{request.use_by.strip()}%"),
                            ),
                        )
                    )
                    .group_by(HostExecLog.host_id)
                    .subquery()
                )

                # 获取过滤后的最新执行日志
                # ✅ 修复：使用正确的 SQLAlchemy 2.0 join 语法
                latest_log_subquery = (
                    select(HostExecLog.host_id, HostExecLog.user_name)
                    .select_from(
                        HostExecLog.__table__.join(
                            max_id_with_filter_subquery,
                            HostExecLog.id == max_id_with_filter_subquery.c.max_id,
                        )
                    )
                    .subquery()
                )

            # 构建主查询：LEFT JOIN 获取最新的执行日志
            # 如果指定了 use_by，需要过滤掉 user_name 为 None 的记录
            query_conditions = base_conditions.copy()
            if request.use_by and request.use_by.strip():
                # 由于使用了 LEFT JOIN，需要过滤掉 user_name 为 None 的记录
                query_conditions.append(latest_log_subquery.c.user_name.is_not(None))

            base_query = (
                select(
                    HostRec.id.label("host_id"),
                    HostRec.host_acct.label("username"),
                    HostRec.mg_id,
                    HostRec.mac_addr.label("mac"),
                    HostRec.host_state,
                    HostRec.appr_state,
                    latest_log_subquery.c.user_name.label("use_by"),
                )
                .outerjoin(
                    latest_log_subquery,
                    HostRec.id == latest_log_subquery.c.host_id,
                )
                .where(and_(*query_conditions))
            )

            # 1. 查询总数
            count_stmt = select(func.count()).select_from(base_query.subquery())
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 2. 分页查询：按 created_time 倒序排序
            pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

            # 添加排序和分页
            stmt = (
                base_query.order_by(HostRec.created_time.desc())
                .offset(pagination_params.offset)
                .limit(pagination_params.limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            # 3. 构建响应数据
            host_info_list: List[AdminHostInfo] = []
            for row in rows:
                host_info = AdminHostInfo(
                    host_id=str(row.host_id),  # ✅ 转换为字符串避免精度丢失
                    username=row.username,
                    mg_id=row.mg_id,
                    mac=row.mac,
                    use_by=row.use_by,
                    host_state=row.host_state,
                    appr_state=row.appr_state,
                )
                host_info_list.append(host_info)

            # 4. 构建分页响应
            pagination_response = PaginationResponse(
                page=request.page,
                page_size=request.page_size,
                total=total,
            )

            logger.info(
                "查询可用主机列表完成",
                extra={
                    "total": total,
                    "returned_count": len(host_info_list),
                    "page": request.page,
                    "page_size": request.page_size,
                },
            )

            return host_info_list, pagination_response

    @handle_service_errors(
        error_message="删除主机失败",
        error_code="DELETE_HOST_FAILED",
    )
    async def delete_host(
        self, host_id: int, request=None, user_id: Optional[int] = None, locale: str = "zh_CN"
    ) -> str:
        """删除主机（逻辑删除）

        根据主机ID逻辑删除 host_rec 表数据。删除后需要同步通知外部API，
        如果通知失败则回滚删除操作。

        Args:
            host_id: 主机ID（host_rec.id）
            request: FastAPI Request 对象（用于从请求头获取 user_id）
            user_id: 当前登录管理后台用户的ID（可选，如果提供则优先使用）
            locale: 语言偏好，用于错误消息多语言处理

        Returns:
            str: 已删除的主机ID（字符串格式，避免精度丢失）

        Raises:
            BusinessError: 主机不存在或删除失败时
        """
        logger.info(
            "开始删除主机",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 检查主机是否存在且未删除，并获取 host_rec 对象（用于获取 hardware_id）
            host_stmt = select(HostRec).where(
                and_(
                    HostRec.id == host_id,
                    HostRec.del_flag == 0,  # 只查询未删除的记录
                )
            )
            host_result = await session.execute(host_stmt)
            host_rec = host_result.scalar_one_or_none()

            if not host_rec:
                raise BusinessError(
                    message=f"主机不存在或已被删除（ID: {host_id}）",
                    message_key="error.host.not_found",
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=404,
                    details={"host_id": host_id},
                )

            # 2. 执行逻辑删除（设置 del_flag = 1）
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(del_flag=1)  # 设置为已删除
            )

            logger.info(
                "执行逻辑删除操作",
                extra={
                    "host_id": host_id,
                    "operation": "UPDATE del_flag = 1",
                },
            )

            # 执行更新
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "逻辑删除失败，记录可能已被删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机删除失败，记录可能已被删除（ID: {host_id}）",
                    message_key="error.host.delete_failed",
                    error_code="HOST_DELETE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "主机逻辑删除完成",
                extra={
                    "host_id": host_id,
                    "updated_count": updated_count,
                },
            )

            # 3. 通知外部API
            try:
                # 使用统一的外部接口调用客户端
                from app.services.external_api_client import call_external_api

                # 构建通知路径（根据实际外部API接口调整）
                external_api_path = f"/api/v1/hardware/{host_rec.hardware_id}"

                logger.info(
                    "调用外部API通知主机删除",
                    extra={
                        "host_id": host_id,
                        "hardware_id": host_rec.hardware_id,
                        "external_api_path": external_api_path,
                        "user_id": user_id,
                    },
                )

                # 调用外部接口通知主机已删除
                response = await call_external_api(
                    method="DELETE",
                    url_path=external_api_path,
                    request=request,
                    user_id=user_id,
                    locale=locale,
                )

                # 判断请求是否成功：检查响应头 :status 或响应体 code 是否为 200
                response_headers = response.get("headers", {})
                response_body = response.get("body", {})
                status_header = response_headers.get(":status") or response_headers.get("status")
                status_code = response.get("status_code")
                body_code = response_body.get("code") if isinstance(response_body, dict) else None

                # 判断成功：响应头 :status 或 status_code 或响应体 code 等于 200
                is_success = (
                    (status_header and str(status_header) == "200")
                    or (status_code and status_code == 200)
                    or (body_code and body_code == 200)
                )

                if not is_success:
                    error_msg = (
                        response_body.get("message", "未知错误")
                        if isinstance(response_body, dict)
                        else str(response_body)
                    )
                    raise Exception(f"外部API通知失败: {error_msg}")

                logger.info(
                    "外部API通知成功",
                    extra={
                        "host_id": host_id,
                        "status_header": status_header,
                        "status_code": status_code,
                        "body_code": body_code,
                    },
                )

            except Exception as e:
                # 4. 如果外部API通知失败，回滚删除操作
                logger.error(
                    "外部API通知失败，开始回滚删除操作",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

                # 回滚：将 del_flag 改回 0
                rollback_stmt = (
                    update(HostRec).where(HostRec.id == host_id).values(del_flag=0)  # 恢复为未删除状态
                )

                rollback_result = await session.execute(rollback_stmt)
                await session.commit()

                rollback_count = rollback_result.rowcount

                logger.info(
                    "删除操作已回滚",
                    extra={
                        "host_id": host_id,
                        "rollback_count": rollback_count,
                    },
                )

                # 抛出业务异常，返回删除失败
                raise BusinessError(
                    message=f"主机删除失败：外部API通知失败（ID: {host_id}）",
                    message_key="error.host.delete_external_api_failed",
                    error_code="HOST_DELETE_EXTERNAL_API_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "host_id": host_id,
                        "external_api_error": str(e),
                        "rollback_success": rollback_count > 0,
                    },
                )

            # 5. 删除成功
            logger.info(
                "主机删除成功（包含外部API通知）",
                extra={
                    "host_id": host_id,
                },
            )

            return str(host_id)  # ✅ 转换为字符串避免精度丢失

    @handle_service_errors(
        error_message="停用主机失败",
        error_code="DISABLE_HOST_FAILED",
    )
    async def disable_host(self, host_id: int) -> dict:
        """停用主机

        根据主机ID更新 host_rec 表的 appr_state 字段为 0（停用），
        同时设置 host_state 为 7（手动停用）。

        Args:
            host_id: 主机ID（host_rec.id）

        Returns:
            dict: 包含更新后的主机ID、审批状态和主机状态

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        logger.info(
            "开始停用主机",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 检查主机是否存在且未删除（使用工具函数）
            host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. 检查当前状态是否已经是停用状态
            if host_rec.appr_state == 0 and host_rec.host_state == 7:
                logger.info(
                    "主机已是停用状态，无需更新",
                    extra={
                        "host_id": host_id,
                        "current_appr_state": host_rec.appr_state,
                        "current_host_state": host_rec.host_state,
                    },
                )
                return {
                    "id": str(host_id),  # ✅ 转换为字符串避免精度丢失
                    "appr_state": 0,
                    "host_state": 7,
                }

            # 3. 更新审批状态为停用，同时设置 host_state 为 7（手动停用）
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(appr_state=0, host_state=7)
            )

            logger.info(
                "执行停用操作",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": 0,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": 7,
                    "operation": "UPDATE appr_state = 0, host_state = 7",
                },
            )

            # 执行更新
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "主机停用失败，记录可能已被删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机停用失败，记录可能已被删除（ID: {host_id}）",
                    message_key="error.host.disable_failed",
                    error_code="HOST_DISABLE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "主机停用成功",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": 0,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": 7,
                    "updated_count": updated_count,
                },
            )

            return {
                "id": str(host_id),  # ✅ 转换为字符串避免精度丢失
                "appr_state": 0,
                "host_state": 7,
                "message": "主机已停用",
            }

    @handle_service_errors(
        error_message="强制下线主机失败",
        error_code="FORCE_OFFLINE_HOST_FAILED",
    )
    async def force_offline_host(self, host_id: int, locale: str = "zh_CN") -> dict:
        """强制下线主机

        业务逻辑：
        1. 检查主机是否存在且未删除
        2. 检查主机状态是否为 0（空闲状态），只有空闲状态才能下线
        3. 更新 host_rec 表的 host_state 字段为 4（离线状态）

        Args:
            host_id: 主机ID（host_rec.id）
            locale: 语言偏好，用于错误消息多语言处理

        Returns:
            dict: 包含更新后的主机ID和状态

        Raises:
            BusinessError: 主机不存在、主机状态不为空闲或更新失败时
        """
        logger.info(
            "开始强制下线主机",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 检查主机是否存在且未删除（使用工具函数）
            host_rec = await validate_host_exists(session, HostRec, host_id, locale=locale)

            # 2. 检查主机状态是否为 0（空闲状态），只有空闲状态才能下线
            if host_rec.host_state != HOST_STATE_FREE:
                logger.warning(
                    "主机状态不允许强制下线",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "required_host_state": HOST_STATE_FREE,
                    },
                )
                raise BusinessError(
                    message=f"主机状态不允许强制下线，当前状态：{host_rec.host_state}，需要状态：{HOST_STATE_FREE}（空闲）",
                    message_key="error.host.force_offline_state_invalid",
                    error_code="HOST_FORCE_OFFLINE_STATE_INVALID",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={
                        "host_id": host_id,
                        "current_host_state": host_rec.host_state,
                        "required_host_state": HOST_STATE_FREE,
                    },
                )

            # 3. 更新主机状态为离线（host_state = 4）
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                        HostRec.host_state == HOST_STATE_FREE,  # 确保状态仍为 0（防止并发修改）
                    )
                )
                .values(host_state=HOST_STATE_OFFLINE)  # 4 = 离线状态
            )

            logger.info(
                "执行强制下线操作",
                extra={
                    "host_id": host_id,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": HOST_STATE_OFFLINE,
                    "operation": f"UPDATE host_state = {HOST_STATE_OFFLINE}",
                },
            )

            # 执行更新
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "主机强制下线失败，记录可能已被删除或状态已变更",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机强制下线失败，记录可能已被删除或状态已变更（ID: {host_id}）",
                    message_key="error.host.force_offline_failed",
                    error_code="HOST_FORCE_OFFLINE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "主机强制下线成功",
                extra={
                    "host_id": host_id,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": HOST_STATE_OFFLINE,
                    "updated_count": updated_count,
                },
            )

            return {
                "id": str(host_id),  # ✅ 转换为字符串避免精度丢失
                "host_state": HOST_STATE_OFFLINE,
            }

    @handle_service_errors(
        error_message="查询主机详情失败",
        error_code="GET_HOST_DETAIL_FAILED",
    )
    async def get_host_detail(self, host_id: int) -> dict:
        """查询主机详情（主体信息）

        业务逻辑：
        1. 查询 host_rec 表的基础信息
        2. 关联 host_hw_rec 表，获取 sync_state=2 的列表数据，按 updated_time 倒序排序
        3. 返回主机详情（包含硬件信息列表）
        4. 密码字段需要解密（AES加密）

        Args:
            host_id: 主机ID（host_rec.id）

        Returns:
            dict: 包含主机详情信息，包含 hw_list 字段（硬件信息列表）

        Raises:
            BusinessError: 主机不存在时
        """
        logger.info(
            "开始查询主机详情",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 验证主机是否存在且未删除（使用工具函数）
            host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. 查询 host_hw_rec 表 sync_state=2 的列表数据，按 updated_time 倒序排序
            hw_stmt = (
                select(HostHwRec)
                .where(
                    and_(
                        HostHwRec.host_id == host_id,
                        HostHwRec.sync_state == 2,  # sync_state = 2（通过）
                        HostHwRec.del_flag == 0,
                    )
                )
                .order_by(HostHwRec.updated_time.desc())
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
            hw_list = []
            for hw_rec in hw_recs:
                hw_list.append(
                    {
                        "hw_info": hw_rec.hw_info,
                        "appr_time": hw_rec.appr_time,
                    }
                )

            # 5. 构建响应数据
            detail = {
                "mg_id": host_rec.mg_id,
                "mac": host_rec.mac_addr,
                "ip": host_rec.host_ip,
                "username": host_rec.host_acct,
                "***REMOVED***word": ***REMOVED***,
                "port": host_rec.host_port,
                "hw_list": hw_list,
            }

            logger.info(
                "查询主机详情完成",
                extra={
                    "host_id": host_id,
                    "has_hw_rec": host_rec is not None,
                    "has_***REMOVED***word": ***REMOVED*** is not None,
                    "hw_list_count": len(hw_list),
                },
            )

            return detail

    @handle_service_errors(
        error_message="修改主机密码失败",
        error_code="UPDATE_HOST_PASSWORD_FAILED",
    )
    async def update_host_***REMOVED***word(self, host_id: int, ***REMOVED***word: str) -> dict:
        """修改主机密码

        业务逻辑：
        1. 检查主机是否存在且未删除
        2. 对密码进行 AES 加密
        3. 更新 host_rec 表的 host_pwd 字段

        Args:
            host_id: 主机ID（host_rec.id）
            ***REMOVED***word: 明文密码（将进行AES加密）

        Returns:
            dict: 包含更新后的主机ID和操作结果消息

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        logger.info(
            "开始修改主机密码",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 检查主机是否存在且未删除（使用工具函数）
            await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

            # 2. 对密码进行 AES 加密
            try:
                encrypted_***REMOVED***word = aes_encrypt(***REMOVED***word)
                logger.debug(
                    "密码加密成功",
                    extra={
                        "host_id": host_id,
                    },
                )
            except Exception as e:
                logger.error(
                    "密码加密失败",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"密码加密失败（ID: {host_id}）",
                    message_key="error.host.***REMOVED***word_encrypt_failed",
                    error_code="PASSWORD_ENCRYPT_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={"host_id": host_id},
                )

            # 3. 更新主机密码
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(host_pwd=encrypted_***REMOVED***word)
            )

            logger.info(
                "执行密码修改操作",
                extra={
                    "host_id": host_id,
                    "operation": "UPDATE host_pwd",
                },
            )

            # 执行更新
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "主机密码修改失败，记录可能已被删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机密码修改失败，记录可能已被删除（ID: {host_id}）",
                    message_key="error.host.***REMOVED***word_update_failed",
                    error_code="HOST_PASSWORD_UPDATE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            logger.info(
                "主机密码修改成功",
                extra={
                    "host_id": host_id,
                    "updated_count": updated_count,
                },
            )

            return {
                "id": str(host_id),  # ✅ 转换为字符串避免精度丢失
            }

    @handle_service_errors(
        error_message="查询主机执行日志失败",
        error_code="GET_HOST_EXEC_LOG_FAILED",
    )
    async def list_host_exec_logs(
        self,
        request: AdminHostExecLogListRequest,
    ) -> Tuple[List[AdminHostExecLogInfo], PaginationResponse]:
        """查询主机执行日志列表（分页）

        业务逻辑：
        1. 根据 host_id 查询 host_exec_log 表
        2. 条件：del_flag = 0
        3. 按 created_time 倒序排序
        4. 计算 exec_date（begin_time 的日期部分，格式 %Y-%m-%d）
        5. 计算 exec_time（end_time - begin_time，格式 %H:%M:%S，如果 end_time 为空，使用当前时间）

        Args:
            request: 查询请求参数（host_id、分页参数）

        Returns:
            Tuple[List[AdminHostExecLogInfo], PaginationResponse]: 执行日志列表和分页信息

        Raises:
            BusinessError: 查询失败时
        """
        logger.info(
            "开始查询主机执行日志列表",
            extra={
                "host_id": request.host_id,
                "page": request.page,
                "page_size": request.page_size,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建查询条件
            base_conditions = [
                HostExecLog.host_id == request.host_id,
                HostExecLog.del_flag == 0,
            ]

            # 1. 查询总数
            count_stmt = select(func.count(HostExecLog.id)).where(and_(*base_conditions))
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 2. 分页查询：按 created_time 倒序排序
            pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

            stmt = (
                select(HostExecLog)
                .where(and_(*base_conditions))
                .order_by(HostExecLog.created_time.desc())
                .offset(pagination_params.offset)
                .limit(pagination_params.limit)
            )

            result = await session.execute(stmt)
            exec_logs = result.scalars().all()

            # 3. 构建响应数据
            log_info_list: List[AdminHostExecLogInfo] = []
            current_time = datetime.now(timezone.utc)

            for log in exec_logs:
                # 计算 exec_date（begin_time 的日期部分）
                exec_date: Optional[str] = None
                if log.begin_time:
                    try:
                        exec_date = log.begin_time.strftime("%Y-%m-%d")
                    except Exception as e:
                        logger.warning(
                            "格式化执行日期失败",
                            extra={
                                "log_id": log.id,
                                "begin_time": str(log.begin_time),
                                "error": str(e),
                            },
                        )
                        exec_date = None

                # 计算 exec_time（end_time - begin_time，格式 %H:%M:%S）
                exec_time: Optional[str] = None
                if log.begin_time:
                    try:
                        # 确保 begin_time 是 timezone-aware
                        begin_time = log.begin_time
                        if begin_time.tzinfo is None:
                            # 如果是 naive datetime，假设是 UTC
                            begin_time = begin_time.replace(tzinfo=timezone.utc)

                        # 如果 end_time 为空，使用当前时间
                        if log.end_time:
                            end_time = log.end_time
                            # 确保 end_time 是 timezone-aware
                            if end_time.tzinfo is None:
                                end_time = end_time.replace(tzinfo=timezone.utc)
                        else:
                            end_time = current_time

                        # 计算时间差
                        time_diff = end_time - begin_time
                        # 转换为秒（确保非负数）
                        total_seconds = max(0, int(time_diff.total_seconds()))
                        # 计算小时、分钟、秒
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        # 格式化为 %H:%M:%S
                        exec_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    except Exception as e:
                        logger.warning(
                            "计算执行时长失败",
                            extra={
                                "log_id": log.id,
                                "begin_time": str(log.begin_time),
                                "end_time": str(log.end_time) if log.end_time else None,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        exec_time = None

                log_info = AdminHostExecLogInfo(
                    log_id=str(log.id),
                    exec_date=exec_date,
                    exec_time=exec_time,
                    tc_id=log.tc_id,
                    use_by=log.user_name,
                    case_state=log.case_state,
                    result_msg=log.result_msg,
                    log_url=log.log_url,
                )
                log_info_list.append(log_info)

            # 4. 构建分页响应
            pagination_response = PaginationResponse(
                page=request.page,
                page_size=request.page_size,
                total=total,
            )

            log_operation_completed(
                "查询主机执行日志列表",
                extra={
                    "host_id": request.host_id,
                    "total": total,
                    "returned_count": len(log_info_list),
                    "page": request.page,
                    "page_size": request.page_size,
                },
                logger_instance=logger,
            )

            return log_info_list, pagination_response
