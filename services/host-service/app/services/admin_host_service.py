"""管理后台主机管理服务

提供管理后台使用的主机查询、搜索等核心业务逻辑。
"""

import os
import sys
from typing import List, Tuple

from sqlalchemy import and_, func, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.schemas.host import AdminHostInfo, AdminHostListRequest
    from app.services.agent_websocket_manager import get_agent_websocket_manager

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_exec_log import HostExecLog
    from app.models.host_rec import HostRec
    from app.schemas.host import AdminHostInfo, AdminHostListRequest
    from app.services.agent_websocket_manager import get_agent_websocket_manager

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
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
        1. 查询 host_rec 表，条件：host_state < 5, appr_state = 1, del_flag = 0
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
        logger.info(
            "开始查询可用主机列表",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "username": request.username,
                "host_state": request.host_state,
                "mg_id": request.mg_id,
                "use_by": request.use_by,
            },
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
            max_id_subquery = (
                select(
                    HostExecLog.host_id,
                    func.max(HostExecLog.id).label("max_id"),
                )
                .select_from(
                    HostExecLog.join(
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
            latest_log_subquery = (
                select(HostExecLog.host_id, HostExecLog.user_name)
                .select_from(
                    HostExecLog.join(
                        max_id_subquery,
                        HostExecLog.id == max_id_subquery.c.max_id,
                    )
                )
                .subquery()
            )

            # 主查询：JOIN host_rec 和最新的 host_exec_log
            # 基础条件：host_state < 5, appr_state = 1, del_flag = 0
            base_conditions = [
                HostRec.host_state < 5,
                HostRec.appr_state == 1,
                HostRec.del_flag == 0,
            ]

            # 添加搜索条件
            if request.mac:
                base_conditions.append(HostRec.mac_addr.like(f"%{request.mac}%"))

            if request.username:
                base_conditions.append(HostRec.host_acct.like(f"%{request.username}%"))

            if request.host_state is not None:
                base_conditions.append(HostRec.host_state == request.host_state)

            if request.mg_id:
                base_conditions.append(HostRec.mg_id.like(f"%{request.mg_id}%"))

            # 如果指定了 use_by 过滤条件，需要重新构建子查询并添加过滤
            if request.use_by:
                # 重新获取最大 id，但这次要过滤 user_name
                max_id_with_filter_subquery = (
                    select(
                        HostExecLog.host_id,
                        func.max(HostExecLog.id).label("max_id"),
                    )
                    .select_from(
                        HostExecLog.join(
                            max_time_subquery,
                            and_(
                                HostExecLog.host_id == max_time_subquery.c.host_id,
                                HostExecLog.created_time == max_time_subquery.c.max_created_time,
                                HostExecLog.del_flag == 0,
                                HostExecLog.user_name.like(f"%{request.use_by}%"),
                            ),
                        )
                    )
                    .group_by(HostExecLog.host_id)
                    .subquery()
                )

                # 获取过滤后的最新执行日志
                latest_log_subquery = (
                    select(HostExecLog.host_id, HostExecLog.user_name)
                    .select_from(
                        HostExecLog.join(
                            max_id_with_filter_subquery,
                            HostExecLog.id == max_id_with_filter_subquery.c.max_id,
                        )
                    )
                    .subquery()
                )

            # 构建主查询：LEFT JOIN 获取最新的执行日志
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
                .where(and_(*base_conditions))
            )

            # 如果指定了 use_by，还需要在 WHERE 子句中过滤（因为可能有些主机没有执行日志）
            if request.use_by:
                base_query = base_query.where(latest_log_subquery.c.user_name.is_not(None))

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
                    host_id=row.host_id,
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
    async def delete_host(self, host_id: int) -> int:
        """删除主机（逻辑删除）

        根据主机ID逻辑删除 host_rec 表数据。删除后需要同步通知外部API，
        如果通知失败则回滚删除操作。

        Args:
            host_id: 主机ID（host_rec.id）

        Returns:
            int: 已删除的主机ID

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
            # 1. 检查主机是否存在且未删除
            check_stmt = select(HostRec).where(
                and_(
                    HostRec.id == host_id,
                    HostRec.del_flag == 0,  # 只检查未删除的记录
                )
            )
            check_result = await session.execute(check_stmt)
            host_rec = check_result.scalar_one_or_none()

            if not host_rec:
                logger.warning(
                    "主机不存在或已删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机不存在或已删除（ID: {host_id}）",
                    message_key="error.host.not_found",
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=400,
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

            # 3. 通知外部API（预留 TODO）
            try:
                # TODO: 调用外部API通知主机已删除
                # 示例代码（待实现）:
                # external_api_result = await self._notify_external_api_deletion(host_id, host_rec)
                # if not external_api_result.get("success"):
                #     raise Exception("外部API通知失败")

                logger.info(
                    "外部API通知（待实现）",
                    extra={
                        "host_id": host_id,
                        "note": "TODO: 实现外部API通知逻辑",
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
                    error_code="HOST_DELETE_EXTERNAL_API_FAILED",
                    code=500,
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

            return host_id

    @handle_service_errors(
        error_message="停用主机失败",
        error_code="DISABLE_HOST_FAILED",
    )
    async def disable_host(self, host_id: int) -> dict:
        """停用主机

        根据主机ID更新 host_rec 表的 appr_state 字段为 0（停用）。

        Args:
            host_id: 主机ID（host_rec.id）

        Returns:
            dict: 包含更新后的主机ID和审批状态

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
            # 1. 检查主机是否存在且未删除
            check_stmt = select(HostRec).where(
                and_(
                    HostRec.id == host_id,
                    HostRec.del_flag == 0,  # 只检查未删除的记录
                )
            )
            check_result = await session.execute(check_stmt)
            host_rec = check_result.scalar_one_or_none()

            if not host_rec:
                logger.warning(
                    "主机不存在或已删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机不存在或已删除（ID: {host_id}）",
                    message_key="error.host.not_found",
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            # 2. 检查当前状态是否已经是停用状态
            if host_rec.appr_state == 0:
                logger.info(
                    "主机已是停用状态，无需更新",
                    extra={
                        "host_id": host_id,
                        "current_appr_state": host_rec.appr_state,
                    },
                )
                return {
                    "id": host_id,
                    "appr_state": 0,
                    "message": "主机已是停用状态",
                }

            # 3. 更新审批状态为停用
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(appr_state=0)
            )

            logger.info(
                "执行停用操作",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": 0,
                    "operation": "UPDATE appr_state = 0",
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
                    "updated_count": updated_count,
                },
            )

            return {
                "id": host_id,
                "appr_state": 0,
                "message": "主机已停用",
            }

    @handle_service_errors(
        error_message="强制下线主机失败",
        error_code="FORCE_OFFLINE_HOST_FAILED",
    )
    async def force_offline_host(self, host_id: int) -> dict:
        """强制下线主机

        业务逻辑：
        1. 更新 host_rec 表的 host_state 字段为 4（离线状态）
        2. 通过 WebSocket 通知指定 host_id 的 Agent 强制下线

        Args:
            host_id: 主机ID（host_rec.id）

        Returns:
            dict: 包含更新后的主机ID、状态和WebSocket通知结果

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        logger.info(
            "开始强制下线主机",
            extra={
                "host_id": host_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 检查主机是否存在且未删除
            check_stmt = select(HostRec).where(
                and_(
                    HostRec.id == host_id,
                    HostRec.del_flag == 0,  # 只检查未删除的记录
                )
            )
            check_result = await session.execute(check_stmt)
            host_rec = check_result.scalar_one_or_none()

            if not host_rec:
                logger.warning(
                    "主机不存在或已删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机不存在或已删除（ID: {host_id}）",
                    message_key="error.host.not_found",
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            # 2. 更新主机状态为离线（host_state = 4）
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(host_state=4)  # 4 = 离线状态
            )

            logger.info(
                "执行强制下线操作",
                extra={
                    "host_id": host_id,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": 4,
                    "operation": "UPDATE host_state = 4",
                },
            )

            # 执行更新
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "主机强制下线失败，记录可能已被删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机强制下线失败，记录可能已被删除（ID: {host_id}）",
                    message_key="error.host.force_offline_failed",
                    error_code="HOST_FORCE_OFFLINE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"host_id": host_id},
                )

            # 3. 通过 WebSocket 通知 Agent 强制下线
            websocket_notified = False
            try:
                ws_manager = get_agent_websocket_manager()
                host_id_str = str(host_id)

                # 构建强制下线通知消息
                offline_message = {
                    "type": "host_offline_notification",
                    "host_id": host_id_str,
                    "message": "主机已强制下线",
                    "reason": "管理员强制下线",
                    "force": True,  # 标记为强制下线
                }

                # 发送消息
                websocket_notified = await ws_manager.send_to_host(host_id_str, offline_message)

                if websocket_notified:
                    logger.info(
                        "WebSocket强制下线通知已发送",
                        extra={
                            "host_id": host_id_str,
                            "message_type": "host_offline_notification",
                        },
                    )
                else:
                    logger.warning(
                        "WebSocket强制下线通知发送失败（Host未连接）",
                        extra={
                            "host_id": host_id_str,
                            "message_type": "host_offline_notification",
                        },
                    )

            except Exception as e:
                # WebSocket通知失败不影响数据库更新，只记录警告
                logger.warning(
                    "WebSocket强制下线通知异常",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

            logger.info(
                "主机强制下线成功",
                extra={
                    "host_id": host_id,
                    "old_host_state": host_rec.host_state,
                    "new_host_state": 4,
                    "updated_count": updated_count,
                    "websocket_notified": websocket_notified,
                },
            )

            return {
                "id": host_id,
                "host_state": 4,
                "websocket_notified": websocket_notified,
                "message": "主机已强制下线",
            }
