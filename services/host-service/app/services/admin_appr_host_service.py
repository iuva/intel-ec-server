"""管理后台待审批主机管理服务

提供管理后台使用的待审批主机查询等核心业务逻辑。
"""

import os
import sys
from typing import List, Tuple

from sqlalchemy import and_, func, select

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_rec import HostRec
    from app.schemas.host import (
        AdminApprHostListRequest,
        AdminApprHostInfo,
    )

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.loguru_config import get_logger
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_rec import HostRec
    from app.schemas.host import (
        AdminApprHostListRequest,
        AdminApprHostInfo,
    )

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.loguru_config import get_logger
    from shared.utils.pagination import PaginationParams, PaginationResponse

logger = get_logger(__name__)


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

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
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

            # 1. 查询总数
            count_stmt = select(func.count(HostRec.id)).where(and_(*base_conditions))
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 2. 分页查询：按 created_time 倒序排序
            pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

            stmt = (
                select(
                    HostRec.id.label("host_id"),
                    HostRec.mg_id,
                    HostRec.mac_addr,
                    HostRec.host_state,
                    HostRec.subm_time,
                )
                .where(and_(*base_conditions))
                .order_by(HostRec.created_time.desc())
                .offset(pagination_params.offset)
                .limit(pagination_params.limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            # 3. 构建响应数据
            host_info_list: List[AdminApprHostInfo] = []
            for row in rows:
                host_info = AdminApprHostInfo(
                    host_id=row.host_id,
                    mg_id=row.mg_id,
                    mac_addr=row.mac_addr,
                    host_state=row.host_state,
                    subm_time=row.subm_time,
                )
                host_info_list.append(host_info)

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

