"""管理后台待审批主机管理服务

提供管理后台使用的待审批主机查询等核心业务逻辑。
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import and_, func, select, update

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailResponse,
        AdminApprHostHwInfo,
        AdminApprHostListRequest,
        AdminApprHostInfo,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.pagination import PaginationParams, PaginationResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_hw_rec import HostHwRec
    from app.models.host_rec import HostRec
    from app.models.sys_conf import SysConf
    from app.schemas.host import (
        AdminApprHostApproveRequest,
        AdminApprHostApproveResponse,
        AdminApprHostDetailResponse,
        AdminApprHostHwInfo,
        AdminApprHostListRequest,
        AdminApprHostInfo,
        AdminMaintainEmailRequest,
        AdminMaintainEmailResponse,
    )

    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
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
            max_id_subquery = (
                select(
                    HostHwRec.host_id,
                    func.max(HostHwRec.id).label("max_id"),
                )
                .select_from(
                    HostHwRec.join(
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
            latest_hw_subquery = (
                select(
                    HostHwRec.host_id,
                    HostHwRec.diff_state,
                )
                .select_from(
                    HostHwRec.join(
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
                    diff_state=row.diff_state,
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

    @handle_service_errors(
        error_message="查询待审批主机详情失败",
        error_code="QUERY_APPR_HOST_DETAIL_FAILED",
    )
    async def get_appr_host_detail(self, host_id: int) -> AdminApprHostDetailResponse:
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
            # 1. 查询 host_rec 表基础信息
            host_stmt = select(HostRec).where(
                and_(
                    HostRec.id == host_id,
                    HostRec.del_flag == 0,  # 只查询未删除的记录
                )
            )
            host_result = await session.execute(host_stmt)
            host_rec = host_result.scalar_one_or_none()

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

            # 2. 查询 host_hw_rec 表 sync_state=1 的所有记录（按 created_time 倒序）
            hw_stmt = (
                select(HostHwRec)
                .where(
                    and_(
                        HostHwRec.host_id == host_id,
                        HostHwRec.sync_state == 1,  # sync_state = 1（待同步）
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
        self, request: AdminApprHostApproveRequest, appr_by: int
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

        # 参数验证
        if request.diff_type == 2:
            if not request.host_ids or len(request.host_ids) == 0:
                raise BusinessError(
                    message="当 diff_type=2 时，host_ids 为必填参数",
                    message_key="error.host.appr_host_ids_required",
                    error_code="HOST_IDS_REQUIRED",
                    code=ServiceErrorCodes.VALIDATION_ERROR,
                    http_status_code=400,
                )

        # 如果 diff_type = 1，暂时不支持（后续可扩展）
        if request.diff_type == 1:
            raise BusinessError(
                message="diff_type=1（版本号变化）暂不支持",
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

                # 处理每个主机
                for host_id in request.host_ids or []:
                    try:
                        # 1. 验证主机是否存在且未删除
                        host_stmt = select(HostRec).where(
                            and_(
                                HostRec.id == host_id,
                                HostRec.del_flag == 0,
                            )
                        )
                        host_result = await session.execute(host_stmt)
                        host_rec = host_result.scalar_one_or_none()

                        if not host_rec:
                            results.append(
                                {
                                    "host_id": host_id,
                                    "success": False,
                                    "message": f"主机不存在或已删除（ID: {host_id}）",
                                }
                            )
                            failed_count += 1
                            continue

                        # 2. 查询所有 host_hw_rec 表 host_id = id, sync_state = 1 的数据
                        hw_rec_stmt = (
                            select(HostHwRec)
                            .where(
                                and_(
                                    HostHwRec.host_id == host_id,
                                    HostHwRec.sync_state == 1,
                                    HostHwRec.del_flag == 0,
                                )
                            )
                            .order_by(HostHwRec.created_time.desc(), HostHwRec.id.desc())
                        )
                        hw_rec_result = await session.execute(hw_rec_stmt)
                        hw_recs = hw_rec_result.scalars().all()

                        if not hw_recs:
                            results.append(
                                {
                                    "host_id": host_id,
                                    "success": False,
                                    "message": f"未找到待审批的硬件记录（ID: {host_id}）",
                                }
                            )
                            failed_count += 1
                            continue

                        # 3. 获取最新一条数据
                        latest_hw_rec = hw_recs[0]
                        latest_hw_id = latest_hw_rec.id

                        # 4. 更新最新一条数据：sync_state = 2, appr_time = now(), appr_by = appr_by
                        update_latest_stmt = (
                            update(HostHwRec)
                            .where(HostHwRec.id == latest_hw_id)
                            .values(
                                sync_state=2,
                                appr_time=now,
                                appr_by=appr_by,
                            )
                        )
                        await session.execute(update_latest_stmt)

                        # 5. 更新其他数据：sync_state = 4
                        if len(hw_recs) > 1:
                            other_hw_ids = [hw.id for hw in hw_recs[1:]]
                            update_other_stmt = (
                                update(HostHwRec)
                                .where(HostHwRec.id.in_(other_hw_ids))
                                .values(sync_state=4)
                            )
                            await session.execute(update_other_stmt)

                        # 6. 修改 host_rec 表：appr_state = 1, host_state = 0, hw_id = latest_hw_id, subm_time = now()
                        update_host_stmt = (
                            update(HostRec)
                            .where(HostRec.id == host_id)
                            .values(
                                appr_state=1,
                                host_state=0,
                                hw_id=latest_hw_id,
                                subm_time=now,
                            )
                        )
                        await session.execute(update_host_stmt)

                        # 7. TODO: 调用外部 API 同步 host_hw_rec 最新数据的 hw_info
                        # TODO: 实现外部 API 调用逻辑
                        # 示例：await external_api.sync_hardware_info(latest_hw_rec.hw_info)

                        results.append(
                            {
                                "host_id": host_id,
                                "success": True,
                                "message": "主机启用成功",
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
                                "message": f"处理失败: {str(e)}",
                            }
                        )
                        failed_count += 1
                        continue

                # 提交事务
                await session.commit()

                logger.info(
                    "同意启用主机处理完成",
                    extra={
                        "diff_type": request.diff_type,
                        "total_count": len(request.host_ids or []),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "appr_by": appr_by,
                    },
                )

                return AdminApprHostApproveResponse(
                    success_count=success_count,
                    failed_count=failed_count,
                    results=results,
                )

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
                    details={"diff_type": request.diff_type, "host_ids": request.host_ids},
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
                sys_conf = result.scalar_one_or_none()

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
                    message="维护通知邮箱设置成功",
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
                    details={"email": formatted_email},
                )
