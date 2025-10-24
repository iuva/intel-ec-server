"""主机管理服务"""

from datetime import datetime, timezone
from typing import List, Optional, cast

import httpx
from sqlalchemy import and_, select

from app.models.host import Host
from app.models.host_rec import HostRec
from app.schemas.host import (
    AvailableHostInfo,
    AvailableHostsListResponse,
    HardwareHostData,
    HostStatusUpdate,
    QueryAvailableHostsRequest,
    VNCConnectionReport,
)

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HostService:
    """主机管理服务类"""

    def __init__(self, hardware_api_url: Optional[str] = None):
        """初始化主机服务

        Args:
            hardware_api_url: 硬件接口基础 URL。如果不提供，将使用默认值 http://hardware-service:8000
        """
        self.hardware_api_url = hardware_api_url or "http://hardware-service:8000"

    @handle_service_errors(error_message="获取主机失败", error_code="HOST_GET_FAILED")
    async def get_host_by_id(self, host_id: str) -> Optional[Host]:
        """根据 host_id 获取主机

        Args:
            host_id: 主机ID

        Returns:
            主机对象，如果不存在则返回 None
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            stmt = select(Host).where(Host.host_id == host_id, Host.del_flag.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if host:
                logger.debug(
                    "查询主机成功",
                    extra={
                        "operation": "get_host_by_id",
                        "host_id": host_id,
                        "status": host.status,
                    },
                )
            else:
                logger.warning(
                    "主机不存在",
                    extra={
                        "operation": "get_host_by_id",
                        "host_id": host_id,
                    },
                )

            return host

    @monitor_operation("host_status_update", record_duration=True)
    @handle_service_errors(error_message="更新主机状态失败", error_code="HOST_STATUS_UPDATE_FAILED")
    async def update_host_status(self, host_id: str, status_data: HostStatusUpdate) -> Host:
        """更新主机状态

        Args:
            host_id: 主机ID
            status_data: 状态更新数据

        Returns:
            更新后的主机对象

        Raises:
            BusinessError: 主机不存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 查询主机
            stmt = select(Host).where(Host.host_id == host_id, Host.del_flag.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                logger.warning(
                    "主机不存在",
                    extra={
                        "operation": "update_host_status",
                        "host_id": host_id,
                        "error_code": "HOST_NOT_FOUND",
                    },
                )
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新状态和心跳时间
            old_status = host.status
            host.status = status_data.status
            host.last_heartbeat = datetime.now(timezone.utc)
            host.updated_time = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(host)

            logger.info(
                "主机状态更新成功",
                extra={
                    "operation": "update_host_status",
                    "host_id": host_id,
                    "old_status": old_status,
                    "new_status": status_data.status,
                },
            )
            return host

    @handle_service_errors(error_message="更新主机心跳失败", error_code="HOST_HEARTBEAT_UPDATE_FAILED")
    async def update_heartbeat(self, host_id: str) -> Host:
        """更新主机心跳时间

        Args:
            host_id: 主机ID

        Returns:
            更新后的主机对象

        Raises:
            BusinessError: 主机不存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 查询主机
            stmt = select(Host).where(Host.host_id == host_id, Host.del_flag.is_(False))
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()

            if not host:
                logger.warning(
                    "主机不存在",
                    extra={
                        "operation": "update_heartbeat",
                        "host_id": host_id,
                        "error_code": "HOST_NOT_FOUND",
                    },
                )
                raise BusinessError(message=f"主机不存在: {host_id}", error_code="HOST_NOT_FOUND")

            # 更新心跳时间和状态
            old_status = host.status
            host.last_heartbeat = datetime.now(timezone.utc)
            if host.status != "online":
                host.status = "online"
            host.updated_time = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(host)

            logger.debug(
                "主机心跳更新",
                extra={
                    "operation": "update_heartbeat",
                    "host_id": host_id,
                    "old_status": old_status,
                    "new_status": host.status,
                },
            )
            return host

    @monitor_operation("vnc_connection_report", record_duration=True)
    @handle_service_errors(error_message="VNC连接结果上报失败", error_code="VNC_CONNECTION_REPORT_FAILED")
    async def report_vnc_connection(self, vnc_report: VNCConnectionReport) -> dict:
        """处理浏览器插件上报的VNC连接结果

        功能描述：根据 host_id 更新 host_rec 表，设置 host_state = 1（已锁定），
                 subm_time = 当前时间。如果数据不存在，直接返回"主机不存在"。

        Args:
            vnc_report: VNC连接结果上报数据
                - user_id: 用户ID
                - host_id: 主机ID
                - connection_status: 连接状态 (success/failed)
                - connection_time: 连接时间

        Returns:
            处理结果字典，包含主机ID、连接状态和处理消息

        Raises:
            BusinessError: 主机不存在或处理失败
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 根据 host_id 查询 host_rec 表
            # 注意：host_id 是字符串类型的 ID，对应 host_rec 表的 id 字段
            stmt = select(HostRec).where(
                HostRec.id == int(vnc_report.host_id),
                HostRec.del_flag == 0,  # 未删除的记录
            )
            result = await session.execute(stmt)
            host_rec = result.scalar_one_or_none()

            # 如果主机不存在，返回错误
            if not host_rec:
                logger.warning(
                    "主机记录不存在",
                    extra={
                        "operation": "report_vnc_connection",
                        "host_id": vnc_report.host_id,
                        "user_id": vnc_report.user_id,
                        "error_code": "HOST_NOT_FOUND",
                    },
                )
                raise BusinessError(
                    message=f"主机不存在: {vnc_report.host_id}",
                    error_code="HOST_NOT_FOUND",
                    code=400,  # 改为 400 而不是 404
                )

            # 记录更新前的状态
            old_host_state = host_rec.host_state
            old_subm_time = host_rec.subm_time

            # 根据连接状态更新 host_rec 表
            # 设置 host_state = 1（已锁定），subm_time = 当前时间
            host_rec.host_state = 1  # 已锁定状态
            host_rec.subm_time = datetime.now(timezone.utc)

            # 提交更新
            await session.commit()
            await session.refresh(host_rec)

            # 格式化时间戳用于日志记录
            new_subm_time_str: Optional[str] = None
            if host_rec.subm_time is not None:
                new_subm_time_str = cast(datetime, host_rec.subm_time).isoformat()

            old_subm_time_str: Optional[str] = None
            if old_subm_time is not None:
                old_subm_time_str = cast(datetime, old_subm_time).isoformat()

            connection_time_str: Optional[str] = None
            if vnc_report.connection_time is not None:
                connection_time_str = cast(datetime, vnc_report.connection_time).isoformat()

            logger.info(
                "VNC连接结果上报处理成功",
                extra={
                    "operation": "report_vnc_connection",
                    "user_id": vnc_report.user_id,
                    "host_id": vnc_report.host_id,
                    "connection_status": vnc_report.connection_status,
                    "connection_time": connection_time_str,
                    "old_host_state": old_host_state,
                    "new_host_state": host_rec.host_state,
                    "old_subm_time": old_subm_time_str,
                    "new_subm_time": new_subm_time_str,
                },
            )

            return {
                "host_id": vnc_report.host_id,
                "connection_status": vnc_report.connection_status,
                "connection_time": vnc_report.connection_time,
                "message": "VNC连接结果上报成功，主机已锁定",
            }

    @monitor_operation("query_available_hosts", record_duration=True)
    @handle_service_errors(error_message="查询可用主机列表失败", error_code="QUERY_HOSTS_FAILED")
    async def query_available_hosts(
        self,
        request: QueryAvailableHostsRequest,
    ) -> AvailableHostsListResponse:
        """查询可用的主机列表，支持游标分页

        业务逻辑：
        1. 根据 last_id 计算初始偏移量（用于从外部接口查询）
        2. 调用外部硬件接口分页获取主机列表
        3. 根据 hardware_id 查询 host_rec 表进行过滤
        4. 过滤条件：appr_state=1（启用）, host_state=0（空闲），del_flag=0（未删除）
        5. 收集满足分页大小的结果后返回
        6. 每个用户独立处理，无全局状态污染

        游标分页说明：
        - 首次请求: last_id = None，从 skip=0 开始
        - 后续请求: 传入上一页的 last_id，系统自动计算 skip
        - 避免并发用户相互干扰

        Args:
            request: 查询请求参数（tc_id, cycle_name, user_name, page_size, last_id）
            hardware_api_url: 外部硬件接口基础 URL

        Returns:
            包含可用主机列表的分页响应

        Raises:
            BusinessError: 当外部接口调用失败或数据查询失败时
        """
        logger.info(
            "开始查询可用主机列表",
            extra={
                "operation": "query_available_hosts",
                "tc_id": request.tc_id,
                "cycle_name": request.cycle_name,
                "user_name": request.user_name,
                "page_size": request.page_size,
                "last_id": request.last_id,
            },
        )

        # 步骤 1: 根据 last_id 计算外部接口的初始偏移量
        # 如果 last_id 存在，说明需要从该 ID 之后的记录开始查询
        initial_skip = 0
        if request.last_id is not None:
            # 需要通过查询数据库找到该 last_id 对应的在外部接口的偏移量
            # 但由于外部接口没有提供按 ID 查询的方式，我们使用启发式方法：
            # 假设每个请求的数据量相对稳定，可以估算跳过的数量
            # 实际上，更好的方式是在每次迭代时记录已处理的硬件数量
            initial_skip = 0  # 需要从头遍历，但会通过 seen_ids 跳过

        # 缓存在本次查询中已处理的 host_rec_id，确保不重复
        # 这个缓存仅在单次请求中有效，不会跨越请求
        seen_ids: set[int] = set()
        all_available_hosts: List[AvailableHostInfo] = []

        # 外部接口分页参数
        skip = initial_skip
        limit = 100  # 每次请求 100 条
        max_iterations = 100  # 最多迭代 100 次，防止无限循环

        # 循环获取外部接口数据并过滤，直到满足分页要求
        for iteration in range(max_iterations):
            logger.debug(
                "调用外部接口获取硬件主机列表",
                extra={
                    "iteration": iteration,
                    "skip": skip,
                    "limit": limit,
                    "current_available_count": len(all_available_hosts),
                },
            )

            # 步骤 2: 调用外部硬件接口获取主机列表
            hardware_hosts = await self._fetch_hardware_hosts(
                request.tc_id,
                self.hardware_api_url,
                skip,
                limit,
            )

            # 如果外部接口返回空，停止循环
            if not hardware_hosts:
                logger.info(
                    "外部接口返回数据为空或已到达末尾",
                    extra={
                        "iteration": iteration,
                        "skip": skip,
                        "total_available": len(all_available_hosts),
                    },
                )
                break

            # 步骤 3: 提取硬件 ID 列表用于查询本地数据库
            hardware_ids = [host.hardware_id for host in hardware_hosts]

            # 步骤 4: 查询 host_rec 表，获取可用的主机
            available_hosts = await self._filter_available_hosts(hardware_ids)

            logger.debug(
                "本轮过滤完成",
                extra={
                    "iteration": iteration,
                    "fetched_hardware_count": len(hardware_hosts),
                    "available_count": len(available_hosts),
                    "total_available": len(all_available_hosts) + len(available_hosts),
                },
            )

            # 步骤 5: 添加新数据，同时跳过在 last_id 之后的数据
            for host in available_hosts:
                # 如果指定了 last_id，跳过所有 ID 小于等于 last_id 的记录
                if request.last_id is not None and host.host_rec_id <= request.last_id:
                    logger.debug(
                        "跳过已处理的记录",
                        extra={
                            "host_rec_id": host.host_rec_id,
                            "last_id": request.last_id,
                        },
                    )
                    continue

                # 检查是否已经添加过（本次查询中的去重）
                if host.host_rec_id in seen_ids:
                    logger.debug("跳过重复的记录", extra={"host_rec_id": host.host_rec_id})
                    continue

                all_available_hosts.append(host)
                seen_ids.add(host.host_rec_id)

                # 如果已经达到要求的数量，可以提前退出
                if len(all_available_hosts) >= request.page_size:
                    logger.info(
                        "已获得足够的数据用于分页",
                        extra={
                            "iteration": iteration,
                            "required_size": request.page_size,
                            "actual_count": len(all_available_hosts),
                        },
                    )
                    break

            # 如果已经收集到足够的数据，停止循环
            if len(all_available_hosts) >= request.page_size:
                break

            # 准备下一页请求
            skip += limit

        # 步骤 6: 进行分页切片 - 返回前 page_size 条数据
        paginated_hosts = all_available_hosts[: request.page_size]

        # 步骤 7: 确定是否有下一页
        # 如果我们获取到了超过 page_size 的数据，说明有下一页
        has_next = len(all_available_hosts) > request.page_size

        # 确定下一页的 last_id
        last_id: Optional[int] = None
        if paginated_hosts:
            last_id = paginated_hosts[-1].host_rec_id

        logger.info(
            "查询可用主机列表完成",
            extra={
                "tc_id": request.tc_id,
                "total_available_in_query": len(all_available_hosts),
                "page_size": request.page_size,
                "returned_count": len(paginated_hosts),
                "has_next": has_next,
                "last_id": last_id,
            },
        )

        return AvailableHostsListResponse(
            hosts=paginated_hosts,
            total=len(all_available_hosts),  # 本次查询中发现的总数
            page_size=request.page_size,
            has_next=has_next,
            last_id=last_id,
        )

    async def _fetch_hardware_hosts(
        self,
        tc_id: str,
        hardware_api_url: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HardwareHostData]:
        """调用外部硬件接口获取主机列表

        Args:
            tc_id: 测试用例 ID
            hardware_api_url: 硬件接口基础 URL
            skip: 跳过条数
            limit: 返回数量

        Returns:
            硬件主机列表

        Raises:
            BusinessError: 当接口调用失败时
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{hardware_api_url}/api/v1/hardware/hosts"
                params = {
                    "tc_id": tc_id,
                    "skip": skip,
                    "limit": limit,
                }

                logger.debug(
                    "调用硬件接口",
                    extra={
                        "url": url,
                        "params": params,
                    },
                )

                response = await client.get(url, params=params)
                response.raise_for_status()

                # 解析响应数据
                data = response.json()
                hardware_hosts: List[HardwareHostData] = []

                if isinstance(data, list):
                    # 响应格式：直接数组
                    hardware_hosts = [HardwareHostData(**item) for item in data]
                elif isinstance(data, dict) and "data" in data:
                    # 响应格式：{ "data": [...] }
                    hardware_hosts = [HardwareHostData(**item) for item in data["data"]]
                else:
                    logger.warning(
                        "硬件接口返回数据格式不符合预期",
                        extra={
                            "response_type": type(data).__name__,
                            "response_keys": (list(data.keys()) if isinstance(data, dict) else "N/A"),
                        },
                    )

                return hardware_hosts

        except httpx.TimeoutException as e:
            logger.error(
                "硬件接口调用超时",
                extra={
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="硬件接口调用超时，请稍后重试",
                error_code="HARDWARE_API_TIMEOUT",
                code=408,
            )

        except httpx.HTTPError as e:
            logger.error(
                "硬件接口调用失败",
                extra={
                    "tc_id": tc_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="硬件接口调用失败，请稍后重试",
                error_code="HARDWARE_API_ERROR",
                code=503,
            )

    async def _filter_available_hosts(
        self,
        hardware_ids: List[str],
    ) -> List[AvailableHostInfo]:
        """根据条件过滤可用的主机

        过滤条件：
        - hardware_id 在指定列表中
        - appr_state = 1（启用状态）
        - host_state = 0（空闲状态）
        - del_flag = 0（未删除）

        Args:
            hardware_ids: 硬件 ID 列表

        Returns:
            可用主机列表
        """
        if not hardware_ids:
            return []

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建查询条件
            stmt = select(HostRec).where(
                and_(
                    HostRec.hardware_id.in_(hardware_ids),
                    HostRec.appr_state == 1,  # 启用状态
                    HostRec.host_state == 0,  # 空闲状态
                    HostRec.del_flag == 0,  # 未删除
                )
            )

            result = await session.execute(stmt)
            host_recs = result.scalars().all()

            # 转换为响应格式
            available_hosts: List[AvailableHostInfo] = [
                AvailableHostInfo(
                    host_rec_id=host_rec.id,
                    hardware_id=cast(str, host_rec.hardware_id),
                    user_name=host_rec.host_acct or "",
                    host_ip=cast(str, host_rec.host_ip),
                    appr_state=cast(int, host_rec.appr_state or 0),
                    host_state=cast(int, host_rec.host_state or 0),
                )
                for host_rec in host_recs
                if host_rec.hardware_id  # 确保 hardware_id 不为空
            ]

            logger.debug(
                "host_rec 表查询完成",
                extra={
                    "requested_hardware_ids": len(hardware_ids),
                    "available_hosts": len(available_hosts),
                },
            )

            return available_hosts

    @handle_service_errors(
        error_message="获取 VNC 连接信息失败",
        error_code="GET_VNC_CONNECTION_FAILED",
    )
    async def get_vnc_connection_info(self, host_rec_id: str) -> dict:
        """获取指定主机的 VNC 连接信息

        业务逻辑：
        1. 根据 host_rec_id 查询 host_rec 表
        2. 检查数据有效性（del_flag=0, appr_state=1）
        3. 返回 VNC 连接所需的字段

        Args:
            host_rec_id: 主机记录 ID

        Returns:
            包含 VNC 连接信息的字典
            {
                "ip": "192.168.101.118",
                "port": "5900",
                "username": "neusoft",
                "***REMOVED***word": "***REMOVED***"
            }

        Raises:
            BusinessError: 当主机不存在或数据无效时
        """
        logger.info(
            "开始获取 VNC 连接信息",
            extra={"operation": "get_vnc_connection_info", "host_rec_id": host_rec_id},
        )

        try:
            # 将字符串 ID 转换为整数
            try:
                host_id = int(host_rec_id)
            except (ValueError, TypeError):
                logger.warning(
                    "主机ID格式错误",
                    extra={"host_rec_id": host_rec_id, "error": "not a valid integer"},
                )
                raise BusinessError(
                    message="主机ID格式无效",
                    error_code="INVALID_HOST_ID",
                    code=400,
                )

            # 查询主机记录
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # 查询条件：ID 匹配、已启用、未删除
                stmt = select(HostRec).where(
                    and_(
                        HostRec.id == host_id,  # 主机ID 匹配
                        HostRec.appr_state == 1,  # 启用状态
                        HostRec.del_flag == 0,  # 未删除
                    )
                )

                result = await session.execute(stmt)
                host_rec = result.scalar_one_or_none()

                # 检查主机是否存在
                if not host_rec:
                    logger.warning(
                        "主机不存在或无效",
                        extra={
                            "host_rec_id": host_rec_id,
                            "error": "host not found or inactive",
                        },
                    )
                    raise BusinessError(
                        message="主机不存在或未启用",
                        error_code="HOST_NOT_FOUND",
                        code=404,
                    )

                # 检查 VNC 连接信息是否完整
                if not host_rec.host_ip or not host_rec.host_port:
                    logger.warning(
                        "VNC 连接信息不完整",
                        extra={
                            "host_rec_id": host_rec_id,
                            "has_ip": bool(host_rec.host_ip),
                            "has_port": bool(host_rec.host_port),
                        },
                    )
                    raise BusinessError(
                        message="VNC 连接信息不完整",
                        error_code="VNC_INFO_INCOMPLETE",
                        code=400,
                    )

                # 构建响应数据
                vnc_info = {
                    "ip": cast(str, host_rec.host_ip),
                    "port": str(cast(int, host_rec.host_port)) if host_rec.host_port else "5900",
                    "username": cast(str, host_rec.host_acct) or "",
                    "***REMOVED***word": cast(str, host_rec.host_pwd) or "",
                }

                logger.info(
                    "VNC 连接信息获取成功",
                    extra={
                        "host_rec_id": host_rec_id,
                        "ip": vnc_info["ip"],
                        "port": vnc_info["port"],
                        "username": vnc_info["username"],
                    },
                )

                return vnc_info

        except BusinessError:
            # 重新抛出业务异常
            raise

        except Exception as e:
            logger.error(
                "获取 VNC 连接信息系统异常",
                extra={
                    "host_rec_id": host_rec_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise BusinessError(
                message="获取 VNC 连接信息失败，请稍后重试",
                error_code="VNC_GET_FAILED",
                code=500,
            )
