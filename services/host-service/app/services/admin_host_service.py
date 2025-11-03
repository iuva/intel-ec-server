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
        """查询主机列表（分页、搜索）

        Args:
            request: 查询请求参数

        Returns:
            Tuple[List[AdminHostInfo], PaginationResponse]: 主机列表和分页信息

        Raises:
            BusinessError: 查询失败时
        """
        logger.info(
            "开始查询主机列表",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "username": request.username,
                "host_state": request.host_state,
                "mg_id": request.mg_id,
                "subm_time_sort": request.subm_time_sort,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建基础查询 - 查询 host_rec 表
            base_stmt = select(HostRec).where(HostRec.del_flag == 0)

            # 添加搜索条件
            if request.mac:
                base_stmt = base_stmt.where(HostRec.mac_addr.like(f"%{request.mac}%"))

            if request.username:
                base_stmt = base_stmt.where(HostRec.host_acct.like(f"%{request.username}%"))

            if request.host_state is not None:
                base_stmt = base_stmt.where(HostRec.host_state == request.host_state)

            if request.mg_id:
                base_stmt = base_stmt.where(HostRec.mg_id.like(f"%{request.mg_id}%"))

            # 1. 先查询总数
            count_stmt = select(func.count(HostRec.id)).where(
                and_(
                    HostRec.del_flag == 0,
                    *([] if not request.mac else [HostRec.mac_addr.like(f"%{request.mac}%")]),
                    *([] if not request.username else [HostRec.host_acct.like(f"%{request.username}%")]),
                    *([] if request.host_state is None else [HostRec.host_state == request.host_state]),
                    *([] if not request.mg_id else [HostRec.mg_id.like(f"%{request.mg_id}%")]),
                )
            )

            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 2. 分页查询主机记录 - 根据排序参数选择排序方式
            pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

            # 默认按创建时间倒序，如果传入了申报时间排序参数，则按申报时间排序
            if request.subm_time_sort is not None:
                # 按申报时间排序
                if request.subm_time_sort == 0:
                    # 正序（从早到晚）
                    stmt = (
                        base_stmt.order_by(HostRec.subm_time.asc().nulls_last())
                        .offset(pagination_params.offset)
                        .limit(pagination_params.limit)
                    )
                else:
                    # 倒序（从晚到早）
                    stmt = (
                        base_stmt.order_by(HostRec.subm_time.desc().nulls_last())
                        .offset(pagination_params.offset)
                        .limit(pagination_params.limit)
                    )
            else:
                # 默认按创建时间倒序
                stmt = (
                    base_stmt.order_by(HostRec.created_time.desc())
                    .offset(pagination_params.offset)
                    .limit(pagination_params.limit)
                )

            result = await session.execute(stmt)
            host_recs = result.scalars().all()

            # 3. 为每个主机查询最新的执行日志记录（user_name）
            host_info_list: List[AdminHostInfo] = []

            for host_rec in host_recs:
                # 查询该主机最新的执行日志
                # 条件：case_state > 0 AND host_state > 0 AND del_flag = 0
                log_stmt = (
                    select(HostExecLog)
                    .where(
                        and_(
                            HostExecLog.host_id == host_rec.id,
                            HostExecLog.case_state > 0,
                            HostExecLog.host_state > 0,
                            HostExecLog.del_flag == 0,
                        )
                    )
                    .order_by(HostExecLog.created_time.desc())
                    .limit(1)
                )

                log_result = await session.execute(log_stmt)
                latest_log = log_result.scalar_one_or_none()

                # 构建主机信息
                host_info = AdminHostInfo(
                    hardware_id=host_rec.hardware_id,
                    host_acct=host_rec.host_acct,
                    mg_id=host_rec.mg_id,
                    mac=host_rec.mac_addr,
                    host_state=host_rec.host_state,
                    user_name=latest_log.user_name if latest_log else None,
                )

                host_info_list.append(host_info)

            # 4. 构建分页响应
            pagination_response = PaginationResponse(
                page=request.page,
                page_size=request.page_size,
                total=total,
            )

            logger.info(
                "查询主机列表完成",
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
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=400,
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
                    error_code="HOST_DELETE_FAILED",
                    code=400,
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
                    update(HostRec)
                    .where(HostRec.id == host_id)
                    .values(del_flag=0)  # 恢复为未删除状态
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
        error_message="更新主机审批状态失败",
        error_code="UPDATE_HOST_APPROVAL_STATE_FAILED",
    )
    async def update_host_approval_state(self, host_id: int, appr_state: int) -> dict:
        """更新主机审批状态（停用/启用）

        根据主机ID更新 host_rec 表的 appr_state 字段。

        Args:
            host_id: 主机ID（host_rec.id）
            appr_state: 审批状态（0=停用，1=启用）

        Returns:
            dict: 包含更新后的主机ID和审批状态

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        logger.info(
            "开始更新主机审批状态",
            extra={
                "host_id": host_id,
                "appr_state": appr_state,
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
                    error_code="HOST_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_NOT_FOUND,
                    http_status_code=400,
                )

            # 2. 检查当前状态是否已为目标状态
            if host_rec.appr_state == appr_state:
                state_name = "启用" if appr_state == 1 else "停用"
                logger.info(
                    "主机审批状态已是目标状态，无需更新",
                    extra={
                        "host_id": host_id,
                        "current_appr_state": host_rec.appr_state,
                        "target_appr_state": appr_state,
                    },
                )
                return {
                    "id": host_id,
                    "appr_state": appr_state,
                    "message": f"主机已是{state_name}状态",
                }

            # 3. 更新审批状态
            update_stmt = (
                update(HostRec)
                .where(
                    and_(
                        HostRec.id == host_id,
                        HostRec.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(appr_state=appr_state)
            )

            logger.info(
                "执行审批状态更新操作",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": appr_state,
                    "operation": "UPDATE appr_state",
                },
            )

            # 执行更新
            result = await session.execute(update_stmt)
            await session.commit()

            updated_count = result.rowcount

            if updated_count == 0:
                logger.warning(
                    "审批状态更新失败，记录可能已被删除",
                    extra={
                        "host_id": host_id,
                    },
                )
                raise BusinessError(
                    message=f"主机审批状态更新失败，记录可能已被删除（ID: {host_id}）",
                    error_code="HOST_UPDATE_APPROVAL_STATE_FAILED",
                    code=400,
                )

            # 4. 刷新对象以获取最新数据
            await session.refresh(host_rec)

            state_name = "启用" if appr_state == 1 else "停用"
            logger.info(
                "主机审批状态更新成功",
                extra={
                    "host_id": host_id,
                    "old_appr_state": host_rec.appr_state,
                    "new_appr_state": appr_state,
                    "updated_count": updated_count,
                },
            )

            return {
                "id": host_id,
                "appr_state": appr_state,
                "message": f"主机已{state_name}",
            }
