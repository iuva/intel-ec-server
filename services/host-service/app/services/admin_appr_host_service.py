"""管理后台待审批主机管理服务

提供管理后台使用的待审批主机查询等核心业务逻辑。

注意：工具函数和邮件服务已拆分到独立模块：
- admin_appr_utils.py: 工具函数（build_host_table, call_hardware_api 等）
- admin_appr_email_service.py: 邮件服务（ApprovalEmailService）
"""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

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
    from app.services.admin_appr_email_service import send_approval_email

    # 从拆分的模块导入
    from app.services.admin_appr_utils import call_hardware_api
    from app.utils.logging_helpers import log_operation_start
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
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
    from app.services.admin_appr_email_service import send_approval_email

    # 从拆分的模块导入
    from app.services.admin_appr_utils import call_hardware_api
    from app.utils.logging_helpers import log_operation_start
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.i18n import t
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
    from shared.utils.pagination import PaginationParams, PaginationResponse

logger = get_logger(__name__)


class AdminApprHostService:
    """管理后台待审批主机管理服务类

    提供待审批主机的查询、搜索等业务逻辑。

    ✅ 优化：缓存会话工厂，避免每次操作都调用 get_session()
    """

    def __init__(self):
        """初始化服务"""
        # ✅ 优化：缓存会话工厂
        self._session_factory = None

    @property
    def session_factory(self):
        """获取会话工厂（延迟初始化，单例模式）

        ✅ 优化：缓存会话工厂，避免重复获取
        - 第一次调用时初始化
        - 后续调用复用缓存的工厂实例
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    async def _validate_and_resolve_host_ids(
        self,
        request: AdminApprHostApproveRequest,
        locale: str = "zh_CN",
    ) -> List[int]:
        """验证参数并解析 host_ids

        Args:
            request: 同意启用请求参数
            locale: 语言偏好

        Returns:
            List[int]: 要处理的主机ID列表，如果未找到则返回空列表

        Raises:
            BusinessError: 参数验证失败时
        """
        if request.diff_type is None or request.diff_type == 2:
            # diff_type 为空或 2 时，host_ids 为必填
            if not request.host_ids or len(request.host_ids) == 0:
                raise BusinessError(
                    message=f"当 diff_type={request.diff_type} 时，host_ids 为必填参数",
                    message_key="error.host.appr_host_ids_required",
                    error_code="HOST_IDS_REQUIRED",
                    code=ServiceErrorCodes.VALIDATION_ERROR,
                    http_status_code=400,
                )
            return request.host_ids

        elif request.diff_type == 1:
            # diff_type = 1 时，如果传入了 host_ids，直接返回
            if request.host_ids and len(request.host_ids) > 0:
                return request.host_ids

            # 如果未传入 host_ids，查询所有符合条件的 host_id
            session_factory = self.session_factory
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
                    return []

                return host_ids_to_process
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

    def _validate_host_exists(
        self,
        host_id: int,
        host_recs_map: Dict[int, HostRec],
        locale: str = "zh_CN",
    ) -> Optional[HostRec]:
        """验证主机是否存在且未删除

        Args:
            host_id: 主机ID
            host_recs_map: 主机记录映射字典
            locale: 语言偏好

        Returns:
            Optional[HostRec]: 主机记录，如果不存在则返回 None
        """
        host_rec = host_recs_map.get(host_id)
        if not host_rec:
            logger.warning(
                "主机不存在或已删除",
                extra={"host_id": host_id},
            )
        return host_rec

    async def _query_hardware_records(
        self,
        session: Any,
        host_ids: List[int],
        sync_state: Optional[int] = SYNC_STATE_WAIT,
        need_latest_only: bool = False,
    ) -> Dict[int, List[HostHwRec]]:
        """查询硬件记录并按 host_id 分组

        Args:
            session: 数据库会话
            host_ids: 主机ID列表
            sync_state: 同步状态（None 表示不限制）
            need_latest_only: 是否只需要最新一条（用于 diff_type is None）

        Returns:
            Dict[int, List[HostHwRec]]: 按 host_id 分组的硬件记录
        """
        if not host_ids:
            return {}

        # 构建查询条件
        conditions = [
            HostHwRec.host_id.in_(host_ids),
            HostHwRec.del_flag == 0,
        ]

        if sync_state is not None:
            conditions.append(HostHwRec.sync_state == sync_state)

        # 查询硬件记录
        hw_stmt = (
            select(HostHwRec)
            .where(and_(*conditions))
            .order_by(HostHwRec.host_id, desc(HostHwRec.created_time), desc(HostHwRec.id))
        )

        hw_result = await session.execute(hw_stmt)
        all_hw_recs = hw_result.scalars().all()

        # 按 host_id 分组
        hw_recs_by_host: Dict[int, List[HostHwRec]] = {}

        if need_latest_only:
            # 只保留每个 host_id 的最新一条
            for hw_rec in all_hw_recs:
                if hw_rec.host_id not in hw_recs_by_host:
                    hw_recs_by_host[hw_rec.host_id] = [hw_rec]
        else:
            # 保留所有记录
            for hw_rec in all_hw_recs:
                if hw_rec.host_id not in hw_recs_by_host:
                    hw_recs_by_host[hw_rec.host_id] = []
                hw_recs_by_host[hw_rec.host_id].append(hw_rec)

        return hw_recs_by_host

    async def _process_manual_enable(
        self,
        host_id: int,
        host_rec: HostRec,
        hw_recs: List[HostHwRec],
        appr_by: int,
        http_request: Any,
        locale: str = "zh_CN",
    ) -> Dict[str, Any]:
        """处理手动启用（diff_type is None）

        Args:
            host_id: 主机ID
            host_rec: 主机记录
            hw_recs: 硬件记录列表
            appr_by: 审批人ID
            http_request: FastAPI Request 对象
            locale: 语言偏好

        Returns:
            Dict[str, Any]: 处理结果，包含 success, host_id, message, hardware_id, host_update
        """
        # 默认更新值
        host_update: Dict[str, Any] = {
            "appr_state": APPR_STATE_ENABLE,
            "host_state": HOST_STATE_FREE,
        }

        # 检查是否需要调用外部接口（host_state 5 or 6）
        if host_rec.host_state in (5, 6):
            latest_hw_rec = hw_recs[0] if hw_recs else None
            if latest_hw_rec and latest_hw_rec.hw_info:
                try:
                    # ✅ 根据 host_state 决定调用新增还是修改接口
                    # host_state = 5（待激活）：新主机，调用新增接口（传递 None）
                    # host_state = 6（硬件改动）：已存在主机，调用修改接口（传递 hardware_id）
                    api_hardware_id: Optional[str] = None
                    if host_rec.host_state == 6:
                        # 硬件改动：使用现有的 hardware_id 调用修改接口
                        # ✅ 检查 hardware_id 是否有效（非 None 且非空字符串）
                        existing_hw_id = host_rec.hardware_id
                        if existing_hw_id and existing_hw_id.strip():
                            api_hardware_id = existing_hw_id
                            api_type = "修改"
                        else:
                            # hardware_id 为空字符串，视为无效，调用新增接口
                            api_hardware_id = None
                            api_type = "新增"
                            logger.warning(
                                "host_state=6 但 hardware_id 为空字符串，强制调用新增接口",
                                extra={
                                    "host_id": host_id,
                                    "host_state": host_rec.host_state,
                                    "existing_hardware_id": existing_hw_id,
                                    "note": "硬件改动状态但 hardware_id 无效，调用新增接口",
                                },
                            )
                    else:
                        # host_state = 5（待激活）：强制调用新增接口，即使 hardware_id 不为空
                        api_hardware_id = None
                        api_type = "新增"
                        existing_hw_id = host_rec.hardware_id
                        if existing_hw_id and existing_hw_id.strip():
                            logger.warning(
                                "host_state=5 但 hardware_id 不为空，强制调用新增接口",
                                extra={
                                    "host_id": host_id,
                                    "host_state": host_rec.host_state,
                                    "existing_hardware_id": existing_hw_id,
                                    "note": "待激活状态应调用新增接口，忽略现有 hardware_id",
                                },
                            )

                    logger.info(
                        f"准备调用外部硬件接口（{api_type}）",
                        extra={
                            "host_id": host_id,
                            "host_state": host_rec.host_state,
                            "api_type": api_type,
                            "api_hardware_id": api_hardware_id,
                            "existing_hardware_id": host_rec.hardware_id,
                        },
                    )

                    api_result = await call_hardware_api(
                        hardware_id=api_hardware_id,
                        hw_info=latest_hw_rec.hw_info,
                        request=http_request,
                        user_id=appr_by,
                        locale=locale,
                        host_id=host_id,
                    )
                    hardware_id = api_result.get("hardware_id")
                    host_name = api_result.get("host_name")

                    if hardware_id:
                        host_update["hardware_id"] = hardware_id
                    # 如果 host_name 存在且不为空，添加到更新字典
                    if host_name and host_name.strip():
                        host_update["host_no"] = host_name.strip()

                    logger.info(
                        "外部硬件接口调用成功 (Empty Diff Type)",
                        extra={
                            "host_id": host_id,
                            "host_state": host_rec.host_state,
                            "api_type": api_type,
                            "hardware_id": hardware_id,
                            "host_name": host_name,
                            "is_new": api_hardware_id is None,
                        },
                    )
                except Exception as e:
                    logger.error(
                        "外部硬件接口调用失败 (Empty Diff Type)",
                        extra={"host_id": host_id, "error": str(e)},
                        exc_info=True,
                    )
                    raise BusinessError(
                        message=f"外部接口调用失败: {str(e)}",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=500,
                    )
            else:
                logger.warning(
                    "状态为 5/6 但未找到硬件记录或 hw_info 为空，跳过外部接口调用",
                    extra={"host_id": host_id, "host_state": host_rec.host_state},
                )

        return {
            "success": True,
            "host_id": host_id,
            "message": t(
                "success.host.manual_enabled",
                locale=locale,
                default="主机启用成功",
            ),
            "hardware_id": host_update.get("hardware_id"),
            "hw_id": None,
            "host_update": host_update,
            "hw_updates": {},
        }

    async def _process_hardware_change_approval(
        self,
        host_id: int,
        host_rec: HostRec,
        hw_recs: List[HostHwRec],
        appr_by: int,
        http_request: Any,
        locale: str = "zh_CN",
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """处理硬件变更审批（diff_type == 1 or 2）

        Args:
            host_id: 主机ID
            host_rec: 主机记录
            hw_recs: 硬件记录列表
            appr_by: 审批人ID
            http_request: FastAPI Request 对象
            locale: 语言偏好
            session: 数据库会话（用于调试查询）

        Returns:
            Dict[str, Any]: 处理结果，包含 success, host_id, message, hardware_id, hw_id, host_update, hw_updates

        Raises:
            BusinessError: 硬件记录不存在或处理失败时
        """
        # 验证硬件记录
        if not hw_recs:
            # 调试：查询该主机的所有硬件记录（不限制 sync_state）以帮助排查问题
            if session:
                debug_hw_stmt = (
                    select(HostHwRec)
                    .where(
                        and_(
                            HostHwRec.host_id == host_id,
                            HostHwRec.del_flag == 0,
                        )
                    )
                    .order_by(desc(HostHwRec.created_time), desc(HostHwRec.id))
                )
                debug_hw_result = await session.execute(debug_hw_stmt)
                debug_hw_recs = debug_hw_result.scalars().all()

                # 统计不同 sync_state 的记录数量
                sync_state_stats = {}
                for hw_rec in debug_hw_recs:
                    sync_state = hw_rec.sync_state
                    if sync_state not in sync_state_stats:
                        sync_state_stats[sync_state] = 0
                    sync_state_stats[sync_state] += 1

                logger.warning(
                    "未找到待审批的硬件记录，跳过审批",
                    extra={
                        "host_id": host_id,
                        "host_exists": True,
                        "debug_info": {
                            "total_hw_recs": len(debug_hw_recs),
                            "sync_state_stats": sync_state_stats,
                            "query_condition": {
                                "sync_state": 1,
                                "del_flag": 0,
                            },
                            "latest_hw_rec": {
                                "id": debug_hw_recs[0].id if debug_hw_recs else None,
                                "sync_state": debug_hw_recs[0].sync_state if debug_hw_recs else None,
                                "del_flag": debug_hw_recs[0].del_flag if debug_hw_recs else None,
                                "created_time": (
                                    debug_hw_recs[0].created_time.isoformat()
                                    if debug_hw_recs and debug_hw_recs[0].created_time
                                    else None
                                ),
                            },
                        },
                    },
                )

            raise BusinessError(
                message=t(
                    "error.host.hardware_not_found",
                    locale=locale,
                    host_id=host_id,
                    default=f"未找到待审批的硬件记录（ID: {host_id}）",
                ),
                message_key="error.host.hardware_not_found",
                error_code="HARDWARE_NOT_FOUND",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=404,
            )

        # 获取最新一条硬件记录
        latest_hw_rec = hw_recs[0]
        latest_hw_id = latest_hw_rec.id

        # 调用外部硬件接口
        hardware_id = None
        if latest_hw_rec.hw_info:
            try:
                # ✅ 根据 host_state 决定调用新增还是修改接口
                # host_state = 5（待激活）：新主机，调用新增接口（传递 None）
                # host_state = 6（硬件改动）：已存在主机，调用修改接口（传递 hardware_id）
                existing_hardware_id = host_rec.hardware_id
                api_hardware_id: Optional[str] = None
                if host_rec.host_state == 6:
                    # 硬件改动：使用现有的 hardware_id 调用修改接口
                    # ✅ 检查 hardware_id 是否有效（非 None 且非空字符串）
                    if existing_hardware_id and existing_hardware_id.strip():
                        api_hardware_id = existing_hardware_id
                        api_type = "修改"
                    else:
                        # hardware_id 为空字符串，视为无效，调用新增接口
                        api_hardware_id = None
                        api_type = "新增"
                        logger.warning(
                            "host_state=6 但 hardware_id 为空字符串，强制调用新增接口（硬件变更审批）",
                            extra={
                                "host_id": host_id,
                                "host_state": host_rec.host_state,
                                "existing_hardware_id": existing_hardware_id,
                                "diff_type": "硬件变更审批",
                                "note": "硬件改动状态但 hardware_id 无效，调用新增接口",
                            },
                        )
                else:
                    # host_state = 5（待激活）：强制调用新增接口，即使 hardware_id 不为空
                    api_hardware_id = None
                    api_type = "新增"
                    if existing_hardware_id and existing_hardware_id.strip():
                        logger.warning(
                            "host_state=5 但 hardware_id 不为空，强制调用新增接口（硬件变更审批）",
                            extra={
                                "host_id": host_id,
                                "host_state": host_rec.host_state,
                                "existing_hardware_id": existing_hardware_id,
                                "diff_type": "硬件变更审批",
                                "note": "待激活状态应调用新增接口，忽略现有 hardware_id",
                            },
                        )

                logger.info(
                    f"准备调用外部硬件接口（{api_type}，硬件变更审批）",
                    extra={
                        "host_id": host_id,
                        "host_state": host_rec.host_state,
                        "api_type": api_type,
                        "api_hardware_id": api_hardware_id,
                        "existing_hardware_id": existing_hardware_id,
                        "diff_type": "硬件变更审批",
                    },
                )

                api_result = await call_hardware_api(
                    hardware_id=api_hardware_id,
                    hw_info=latest_hw_rec.hw_info,
                    request=http_request,
                    user_id=appr_by,
                    locale=locale,
                    host_id=host_id,
                )
                hardware_id = api_result.get("hardware_id")
                host_name = api_result.get("host_name")

                logger.info(
                    "外部硬件接口调用成功（硬件变更审批）",
                    extra={
                        "host_id": host_id,
                        "host_state": host_rec.host_state,
                        "api_type": api_type,
                        "hardware_id": hardware_id,
                        "host_name": host_name,
                        "is_new": api_hardware_id is None,
                    },
                )
            except BusinessError:
                raise
            except Exception as e:
                logger.error(
                    "调用外部硬件接口失败",
                    extra={
                        "host_id": host_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise BusinessError(
                    message=f"调用外部硬件接口失败: {str(e)}",
                    message_key="error.hardware.api_call_failed",
                    error_code="HARDWARE_API_CALL_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "host_id": host_id,
                        "error": str(e),
                    },
                )
        else:
            logger.warning(
                "硬件记录中缺少 hw_info，跳过外部硬件接口调用",
                extra={
                    "host_id": host_id,
                    "hw_rec_id": latest_hw_id,
                },
            )

        # 构建更新数据
        now = datetime.now(timezone.utc)

        # 主机更新数据
        host_update = {
            "appr_state": APPR_STATE_ENABLE,
            "host_state": HOST_STATE_FREE,
            "hw_id": latest_hw_id,
            "subm_time": now,
        }
        if hardware_id:
            host_update["hardware_id"] = hardware_id
        # 如果 host_name 存在且不为空，添加到更新字典
        if host_name and host_name.strip():
            host_update["host_no"] = host_name.strip()

        # 硬件记录更新数据
        hw_updates = {
            latest_hw_id: {
                "sync_state": 2,
                "appr_time": now,
                "appr_by": appr_by,
            }
        }
        if hardware_id:
            hw_updates[latest_hw_id]["hardware_id"] = hardware_id

        # 其他硬件记录更新为 sync_state = 4
        for hw_rec in hw_recs[1:]:
            hw_updates[hw_rec.id] = {"sync_state": 4}

        return {
            "success": True,
            "host_id": host_id,
            "message": t("success.host.approved", locale=locale, default="主机启用成功"),
            "hardware_id": hardware_id,
            "hw_id": latest_hw_id,
            "host_update": host_update,
            "hw_updates": hw_updates,
        }

    async def _bulk_update_host_records(
        self,
        session: Any,
        host_updates: Dict[int, Dict[str, Any]],
    ) -> None:
        """批量更新 host_rec 表（优化：按更新字段分组）

        Args:
            session: 数据库会话
            host_updates: 主机更新数据字典 {host_id: {field: value}}
        """
        if not host_updates:
            return

        # 分离需要更新 host_no 的记录和只更新其他字段的记录
        hosts_with_host_no: Dict[int, Dict[str, Any]] = {}
        hosts_without_host_no: Dict[int, Dict[str, Any]] = {}

        for host_id, update_values in host_updates.items():
            if "host_no" in update_values:
                hosts_with_host_no[host_id] = update_values
            else:
                hosts_without_host_no[host_id] = update_values

        # 批量更新（有 host_no）
        if hosts_with_host_no:
            bulk_update_data = [
                {"id": host_id, **update_values}
                for host_id, update_values in hosts_with_host_no.items()
            ]

            def _bulk_update_with_host_no(sync_session: Any) -> None:
                sync_session.bulk_update_mappings(HostRec, bulk_update_data)

            await session.run_sync(_bulk_update_with_host_no)

            logger.debug(
                "批量更新主机记录（包含 host_no）",
                extra={
                    "count": len(hosts_with_host_no),
                    "host_ids": list(hosts_with_host_no.keys())[:10],  # 只记录前10条
                },
            )

        # 批量更新（无 host_no）
        if hosts_without_host_no:
            bulk_update_data = [
                {"id": host_id, **update_values}
                for host_id, update_values in hosts_without_host_no.items()
            ]

            def _bulk_update_without_host_no(sync_session: Any) -> None:
                sync_session.bulk_update_mappings(HostRec, bulk_update_data)

            await session.run_sync(_bulk_update_without_host_no)

            logger.debug(
                "批量更新主机记录（不包含 host_no）",
                extra={
                    "count": len(hosts_without_host_no),
                },
            )

    async def _bulk_update_hardware_records(
        self,
        session: Any,
        hw_updates: Dict[int, Dict[str, Any]],
        now: datetime,
        appr_by: int,
    ) -> None:
        """批量更新 host_hw_rec 表

        ✅ 优化：使用 CASE WHEN 批量更新，减少 SQL 执行次数
        - 优化前：N 条记录需要 N 次 SQL
        - 优化后：最多 3 次 SQL（有 hardware_id、无 hardware_id、其他）

        Args:
            session: 数据库会话
            hw_updates: 硬件记录更新数据字典 {hw_rec_id: {field: value}}
            now: 当前时间
            appr_by: 审批人ID
        """
        if not hw_updates:
            return

        # 分离需要更新 hardware_id 的记录和普通记录
        latest_hw_ids_with_hardware_id: List[int] = []
        latest_hw_ids_without_hardware_id: List[int] = []
        other_hw_ids: List[int] = []
        hw_rec_hardware_id_map: Dict[int, str] = {}

        for hw_rec_id, update_values in hw_updates.items():
            if "hardware_id" in update_values:
                latest_hw_ids_with_hardware_id.append(hw_rec_id)
                hw_rec_hardware_id_map[hw_rec_id] = update_values["hardware_id"]
            elif update_values.get("sync_state") == 2:
                latest_hw_ids_without_hardware_id.append(hw_rec_id)
            else:
                other_hw_ids.append(hw_rec_id)

        # ✅ 优化：使用 CASE WHEN 批量更新（有 hardware_id）
        # 将 N 条 SQL 合并为 1 条 SQL
        if latest_hw_ids_with_hardware_id:
            from sqlalchemy import case

            # 构建 CASE WHEN 表达式：CASE id WHEN 1 THEN 'hw_id_1' WHEN 2 THEN 'hw_id_2' END
            hardware_id_case = case(
                hw_rec_hardware_id_map,
                value=HostHwRec.id,
            )

            update_stmt = (
                update(HostHwRec)
                .where(HostHwRec.id.in_(latest_hw_ids_with_hardware_id))
                .values(
                    sync_state=2,
                    appr_time=now,
                    appr_by=appr_by,
                    hardware_id=hardware_id_case,
                )
            )
            await session.execute(update_stmt)

            logger.debug(
                "批量更新硬件记录（有 hardware_id）",
                extra={
                    "count": len(latest_hw_ids_with_hardware_id),
                    "hw_ids": latest_hw_ids_with_hardware_id[:10],  # 只记录前10条
                },
            )

        # 批量更新最新硬件记录（无 hardware_id）
        if latest_hw_ids_without_hardware_id:
            update_latest_stmt = (
                update(HostHwRec)
                .where(HostHwRec.id.in_(latest_hw_ids_without_hardware_id))
                .values(
                    sync_state=2,
                    appr_time=now,
                    appr_by=appr_by,
                )
            )
            await session.execute(update_latest_stmt)

            logger.debug(
                "批量更新硬件记录（无 hardware_id）",
                extra={
                    "count": len(latest_hw_ids_without_hardware_id),
                },
            )

        # 批量更新其他硬件记录
        if other_hw_ids:
            update_other_stmt = (
                update(HostHwRec).where(HostHwRec.id.in_(other_hw_ids)).values(sync_state=4)
            )
            await session.execute(update_other_stmt)

            logger.debug(
                "批量更新其他硬件记录",
                extra={
                    "count": len(other_hw_ids),
                },
            )

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
        5. 关联 host_hw_rec 表，获取每个 host_id 对应的最新一条记录的 diff_state
           - 只查询 sync_state = 1（待同步）的记录
           - 按 created_time 倒序排序，取第一条记录的 diff_state
           - 与 get_appr_host_detail 接口的 diff_state 获取逻辑保持一致

        Args:
            request: 查询请求参数（分页、搜索条件）

        Returns:
            Tuple[List[AdminApprHostInfo], PaginationResponse]: 待审批主机列表和分页信息

        Raises:
            BusinessError: 查询失败时
        """
        log_operation_start(
            "查询待审批主机列表",
            extra={
                "page": request.page,
                "page_size": request.page_size,
                "mac": request.mac,
                "mg_id": request.mg_id,
                "host_state": request.host_state,
            },
            logger_instance=logger,
        )

        try:
            session_factory = self.session_factory
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

                # 1. 查询总数
                count_stmt = select(func.count(HostRec.id)).where(and_(*base_conditions))
                count_result = await session.execute(count_stmt)
                total = count_result.scalar() or 0

                # 2. 分页查询：按 created_time 倒序排序，LEFT JOIN 获取 diff_state
                # 优化：直接关联 host_hw_rec 表，无需子查询（假设每个 host 最多只有一条 sync_state=1 的记录）
                pagination_params = PaginationParams(page=request.page, page_size=request.page_size)

                stmt = (
                    select(
                        HostRec.id.label("host_id"),
                        HostRec.mg_id,
                        HostRec.mac_addr,
                        HostRec.host_state,
                        HostRec.subm_time,
                        HostHwRec.diff_state,
                    )
                    .outerjoin(
                        HostHwRec,
                        and_(
                            HostHwRec.host_id == HostRec.id,
                            HostHwRec.sync_state == SYNC_STATE_WAIT,  # sync_state = 1（待同步）
                            HostHwRec.del_flag == 0,
                        ),
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

        session_factory = self.session_factory
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
            diff_state: Optional[int] = None

            for hw_rec in hw_recs:
                hw_info = AdminApprHostHwInfo(
                    created_time=hw_rec.created_time,
                    hw_info=hw_rec.hw_info,
                )
                hw_list.append(hw_info)

            # 获取最新一条硬件记录的 diff_state（已按 created_time 倒序排序，第一条为最新）
            if hw_recs:
                diff_state = hw_recs[0].diff_state

            # 5. 构建响应数据
            detail = AdminApprHostDetailResponse(
                mg_id=host_rec.mg_id,
                mac=host_rec.mac_addr,
                ip=host_rec.host_ip,
                username=host_rec.host_acct,
                ***REMOVED***word=***REMOVED***,
                port=host_rec.host_port,
                host_state=host_rec.host_state,
                diff_state=diff_state,
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
        self, request: AdminApprHostApproveRequest, appr_by: int, locale: str = "zh_CN", http_request=None
    ) -> AdminApprHostApproveResponse:
        """同意启用主机（管理后台）

        业务逻辑：
        - diff_type is None: 手动启用，仅更新本地状态（状态 5/6 时调用外部接口）
        - diff_type == 1 or 2: 硬件变更审批，需要处理硬件记录并调用外部接口

        Args:
            request: 同意启用请求参数（diff_type, host_ids）
            appr_by: 审批人ID（从 token 中获取）
            locale: 语言偏好
            http_request: FastAPI Request 对象

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

        # 1. 验证参数并解析 host_ids
        host_ids_to_process = await self._validate_and_resolve_host_ids(request, locale)

        if not host_ids_to_process:
            return AdminApprHostApproveResponse(
                success_count=0,
                failed_count=0,
                results=[],
            )

        session_factory = self.session_factory
        async with session_factory() as session:
            try:
                success_count = 0
                failed_count = 0
                results: List[Dict[str, Any]] = []
                now = datetime.now(timezone.utc)

                # 2. 批量查询所有主机信息（避免 N+1 查询）
                host_stmt = select(HostRec).where(
                    and_(
                        HostRec.id.in_(host_ids_to_process),
                        HostRec.del_flag == 0,
                    )
                )
                host_result = await session.execute(host_stmt)
                host_recs_map = {host.id: host for host in host_result.scalars().all()}

                # 3. 根据 diff_type 处理
                host_updates: Dict[int, Dict[str, Any]] = {}
                hw_updates: Dict[int, Dict[str, Any]] = {}

                if request.diff_type is None:
                    # 手动启用：处理每个主机
                    # 查询需要硬件记录的主机（状态 5/6）
                    host_ids_need_hw = [
                        host_id
                        for host_id in host_ids_to_process
                        if host_recs_map.get(host_id) and host_recs_map[host_id].host_state in (5, 6)
                    ]

                    # 批量查询硬件记录（仅最新一条）
                    hw_recs_by_host = {}
                    if host_ids_need_hw:
                        hw_recs_by_host = await self._query_hardware_records(
                            session, host_ids_need_hw, sync_state=None, need_latest_only=True
                        )

                    # 处理每个主机
                    for host_id in host_ids_to_process:
                        try:
                            # 验证主机存在
                            host_rec = self._validate_host_exists(host_id, host_recs_map, locale)
                            if not host_rec:
                                error_message = t("error.host.not_found", locale=locale, host_id=host_id)
                                results.append(
                                    {
                                        "host_id": host_id,
                                        "success": False,
                                        "message": error_message,
                                    }
                                )
                                failed_count += 1
                                continue

                            # 处理手动启用
                            hw_recs = hw_recs_by_host.get(host_id, [])
                            process_result = await self._process_manual_enable(
                                host_id, host_rec, hw_recs, appr_by, http_request, locale
                            )

                            host_updates[host_id] = process_result["host_update"]
                            results.append(
                                {
                                    "host_id": process_result["host_id"],
                                    "success": process_result["success"],
                                    "message": process_result["message"],
                                }
                            )
                            success_count += 1

                        except Exception as e:
                            logger.error(
                                "处理主机时发生异常",
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

                    # 批量更新 host_rec 表
                    await self._bulk_update_host_records(session, host_updates)

                    # 提交事务
                    await session.commit()

                    return AdminApprHostApproveResponse(
                        success_count=success_count,
                        failed_count=failed_count,
                        results=results,
                    )

                else:
                    # 硬件变更审批（diff_type == 1 or 2）
                    # 批量查询硬件记录
                    hw_recs_by_host = await self._query_hardware_records(
                        session, host_ids_to_process, sync_state=SYNC_STATE_WAIT, need_latest_only=False
                    )

                    logger.debug(
                        "批量查询硬件记录完成",
                        extra={
                            "host_ids_count": len(host_ids_to_process),
                            "found_hosts_count": len(hw_recs_by_host),
                        },
                    )

                    # 处理每个主机
                    for host_id in host_ids_to_process:
                        try:
                            # 验证主机存在
                            host_rec = self._validate_host_exists(host_id, host_recs_map, locale)
                            if not host_rec:
                                error_message = t("error.host.not_found", locale=locale, host_id=host_id)
                                results.append(
                                    {
                                        "host_id": host_id,
                                        "success": False,
                                        "message": error_message,
                                    }
                                )
                                failed_count += 1
                                continue

                            # 处理硬件变更审批
                            hw_recs = hw_recs_by_host.get(host_id, [])
                            process_result = await self._process_hardware_change_approval(
                                host_id, host_rec, hw_recs, appr_by, http_request, locale, session
                            )

                            host_updates[host_id] = process_result["host_update"]
                            hw_updates.update(process_result["hw_updates"])
                            results.append(
                                {
                                    "host_id": process_result["host_id"],
                                    "success": process_result["success"],
                                    "message": process_result["message"],
                                    "hw_id": process_result["hw_id"],
                                    "hardware_id": process_result["hardware_id"],
                                }
                            )
                            success_count += 1

                        except BusinessError:
                            # 业务错误直接抛出
                            raise
                        except Exception as e:
                            logger.error(
                                "处理主机时发生异常",
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

                    # 批量更新硬件记录
                    await self._bulk_update_hardware_records(session, hw_updates, now, appr_by)

                    # 批量更新主机记录
                    await self._bulk_update_host_records(session, host_updates)

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

                # 邮件通知（仅硬件变更审批时发送）
                email_notification_errors: List[str] = []
                if request.diff_type in (1, 2):
                    email_notification_errors = await send_approval_email(session, results, appr_by, locale)

                # 构建响应
                response_data = AdminApprHostApproveResponse(
                    success_count=success_count,
                    failed_count=failed_count,
                    results=results,
                )

                # 如果有邮件通知错误，添加到响应中（不影响成功状态）
                if email_notification_errors:
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

        session_factory = self.session_factory
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
        log_operation_start(
            "获取维护通知邮箱",
            logger_instance=logger,
        )

        session_factory = self.session_factory
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
