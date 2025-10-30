"""主机发现服务

提供主机发现和查询相关的业务逻辑服务，包括：
- 查询可用主机列表（游标分页）
- 调用外部硬件接口获取主机信息
- 本地数据库过滤和查询
"""

from typing import List, Optional, cast

import httpx
from sqlalchemy import and_, select

from app.models.host_rec import HostRec
from app.schemas.host import AvailableHostInfo, AvailableHostsListResponse, HardwareHostData, QueryAvailableHostsRequest

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HostDiscoveryService:
    """主机发现服务类

    负责主机发现、查询和过滤相关的业务逻辑，支持游标分页和外部接口集成。
    """

    def __init__(self, hardware_api_url: Optional[str] = None):
        """初始化主机发现服务

        Args:
            hardware_api_url: 硬件接口基础 URL。如果不提供，将使用默认值
        """
        self.hardware_api_url = hardware_api_url or "http://hardware-service:8000"

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
        initial_skip = 0
        if request.last_id is not None:
            # 需要从头遍历，但会通过 seen_ids 跳过
            initial_skip = 0

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
                    logger.debug(
                        "跳过重复的记录",
                        extra={"host_rec_id": host.host_rec_id},
                    )
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
        skip: int = 0,
        limit: int = 100,
    ) -> List[HardwareHostData]:
        """调用外部硬件接口获取主机列表

        Args:
            tc_id: 测试用例 ID
            skip: 跳过条数
            limit: 返回数量

        Returns:
            硬件主机列表

        Raises:
            BusinessError: 当接口调用失败时
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.hardware_api_url}/api/v1/hardware/hosts"
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
                error_code="HOST_HARDWARE_API_TIMEOUT",
                code=ServiceErrorCodes.HOST_OPERATION_TIMEOUT,
                http_status_code=408,  # Request Timeout
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
                error_code="HOST_HARDWARE_API_ERROR",
                code=ServiceErrorCodes.HOST_HARDWARE_API_ERROR,
                http_status_code=502,  # Bad Gateway
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
