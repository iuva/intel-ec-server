"""主机发现服务

提供主机发现和查询相关的业务逻辑服务，包括：
- 查询可用主机列表（游标分页）
- 调用外部硬件接口获取主机信息
- 本地数据库过滤和查询
"""

import asyncio
import hashlib
import os
import time
from typing import List, Optional, TYPE_CHECKING, cast

import httpx
from app.constants.host_constants import (
    APPR_STATE_ENABLE,
    HOST_STATE_FREE,
    TCP_STATE_LISTEN,
)
from app.models.host_rec import HostRec
from app.schemas.host import AvailableHostInfo, AvailableHostsListResponse, HardwareHostData, QueryAvailableHostsRequest
from sqlalchemy import and_, select
from sqlalchemy.exc import OperationalError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# 全局 HTTP 客户端连接池（复用连接，提高性能）
_http_client: Optional["httpx.AsyncClient"] = None

# 使用 try-except 方式处理路径导入
try:
    from app.services.external_api_client import call_external_api

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.external_api_client import call_external_api

    from shared.common.cache import redis_manager
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
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端连接池（单例模式）

        ⚠️ 已废弃：请使用 external_api_client.call_external_api 方法，它支持统一的 SSL 配置和认证

        Returns:
            httpx.AsyncClient: HTTP 客户端实例
        """
        global _http_client
        if _http_client is None:
            # ✅ 从环境变量读取 SSL 验证配置（与其他外部接口保持一致）
            verify_ssl_env = os.getenv("HTTP_CLIENT_VERIFY_SSL", "true").lower()
            verify_ssl = verify_ssl_env in ("true", "1", "yes", "on", "enabled")

            # 创建带连接池的 HTTP 客户端，优化高并发性能
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),  # 总超时10秒，连接超时5秒
                limits=httpx.Limits(
                    max_keepalive_connections=50,  # 保持连接数
                    max_connections=200,  # 最大连接数
                ),
                verify=verify_ssl,  # ✅ 支持 SSL 配置
            )
        return _http_client

    @monitor_operation("query_available_hosts", record_duration=True)
    @handle_service_errors(error_message="查询可用主机列表失败", error_code="QUERY_HOSTS_FAILED")
    async def query_available_hosts(
        self,
        request: QueryAvailableHostsRequest,
        fastapi_request=None,  # FastAPI Request 对象（用于获取 user_id）
        user_id: Optional[int] = None,  # 用户ID（可选，如果提供了 email 则可以为 None）
    ) -> AvailableHostsListResponse:
        """查询可用的主机列表，支持游标分页

        业务逻辑：
        1. 根据 last_id 计算初始偏移量（用于从外部接口查询）
        2. 调用外部硬件接口分页获取主机列表（带认证）
           - 如果 request.email 存在，直接使用该 email 进行外部接口认证，不查询数据库
           - 如果 request.email 不存在，根据 user_id 查询数据库获取 email
        3. 根据 hardware_id 查询 host_rec 表进行过滤
        4. 过滤条件：appr_state=1（启用）, host_state=0（空闲），tcp_state=2（监听/连接正常），del_flag=0（未删除）
        5. 收集满足分页大小的结果后返回
        6. 每个用户独立处理，无全局状态污染

        游标分页说明：
        - 首次请求: last_id = None，从 skip=0 开始
        - 后续请求: 传入上一页的 last_id，系统自动计算 skip
        - 避免并发用户相互干扰

        认证优化说明：
        - 如果提供了 request.email，系统直接使用该 email 获取外部接口 token，跳过数据库查询，提高性能
        - 如果未提供 request.email，系统会根据 user_id（从 fastapi_request 或参数获取）查询数据库获取 email

        Args:
            request: 查询请求参数，包含：
                - tc_id: 测试用例 ID
                - cycle_name: 测试周期名称
                - user_name: 用户名
                - page_size: 每页大小（1-100）
                - last_id: 上一页最后一条记录的 id（可选）
                - email: 用户邮箱（可选）。如果提供，将直接使用该 email 进行外部接口认证，不查询数据库
            fastapi_request: FastAPI Request 对象（用于从请求头获取 user_id）
            user_id: 用户ID（可选，如果提供了 request.email 则可以为 None）

        Returns:
            包含可用主机列表的分页响应

        Raises:
            BusinessError: 当外部接口调用失败或数据查询失败时
        """
        operation_start_time = time.time()

        logger.info(
            "开始查询可用主机列表",
            extra={
                "operation": "query_available_hosts",
                "tc_id": request.tc_id,
                "cycle_name": request.cycle_name,
                "user_name": request.user_name,
                "page_size": request.page_size,
                "last_id": request.last_id,
                "email": request.email,  # ✅ 记录 email 参数（如果提供）
            },
        )

        # ✅ 优化：对首次查询（last_id=None）添加短期缓存，减少外部接口调用
        # 注意：只缓存首次查询，后续分页查询不缓存（因为 last_id 不同）
        cache_key = None
        if request.last_id is None:
            # 生成缓存键（包含关键查询参数）
            cache_params = f"{request.tc_id}:{request.cycle_name}:{request.page_size}"
            cache_hash = hashlib.md5(cache_params.encode()).hexdigest()
            cache_key = f"available_hosts:first_page:{cache_hash}"

            # 尝试从缓存获取
            try:
                cached_result = await redis_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(
                        "从缓存获取可用主机列表（首次查询）",
                        extra={
                            "cache_key": cache_key,
                            "count": len(cached_result.get("hosts", [])) if isinstance(cached_result, dict) else 0,
                        },
                    )
                    # 转换为响应对象
                    return AvailableHostsListResponse(**cached_result)
            except Exception as e:
                logger.warning(
                    "从缓存获取可用主机列表失败，将查询数据库",
                    extra={"cache_key": cache_key, "error": str(e)},
                )

        # 步骤 1: 根据 last_id 计算外部接口的初始偏移量
        initial_skip = 0
        if request.last_id is not None:
            # 需要从头遍历，但会通过 seen_ids 跳过
            initial_skip = 0

        # 缓存在本次查询中已处理的 host_rec_id，确保不重复
        # 这个缓存仅在单次请求中有效，不会跨越请求
        seen_ids: set[str] = set()
        all_available_hosts: List[AvailableHostInfo] = []

        # 外部接口分页参数
        skip = initial_skip
        # limit = 100  # 每次请求 100 条
        limit = 10  # 每次请求 10 条
        max_iterations = 100  # 最多迭代 100 次，防止无限循环

        # ✅ 死循环检测：记录连续无进展的迭代次数
        no_progress_count = 0  # 连续无进展的迭代次数
        max_no_progress = 5  # 最多允许 5 次无进展迭代
        last_available_count = 0  # 上一次迭代后的可用主机数量
        seen_hardware_ids: set[str] = set()  # 已处理过的 hardware_id 集合（用于检测重复数据）

        # 优化：在循环外创建数据库会话，复用连接，减少连接池压力
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 记录连接池状态（连接获取前）
            pool_status_before = mariadb_manager.get_pool_status()
            if pool_status_before["usage_percent"] >= 80:
                logger.warning(
                    "数据库连接池使用率较高，开始查询",
                    extra={
                        "usage_percent": pool_status_before["usage_percent"],
                        "checked_out": pool_status_before["checked_out"],
                        "max_connections": pool_status_before["max_connections"],
                    },
                )

            # 循环获取外部接口数据并过滤，直到满足分页要求
            for iteration in range(max_iterations):
                # 如果已经收集到足够的数据，提前退出循环
                if len(all_available_hosts) >= request.page_size:
                    logger.info(
                        "已获得足够的数据用于分页，提前退出循环",
                        extra={
                            "iteration": iteration,
                            "required_size": request.page_size,
                            "actual_count": len(all_available_hosts),
                            "skip": skip,
                        },
                    )
                    break

                # ✅ 死循环检测：如果连续多次迭代都没有新增任何记录，退出循环
                if iteration > 0 and len(all_available_hosts) == last_available_count:
                    no_progress_count += 1
                    if no_progress_count >= max_no_progress:
                        logger.warning(
                            "检测到死循环风险，连续多次迭代无进展，退出循环",
                            extra={
                                "iteration": iteration,
                                "no_progress_count": no_progress_count,
                                "current_available_count": len(all_available_hosts),
                                "required_size": request.page_size,
                                "skip": skip,
                            },
                        )
                        break
                else:
                    # 有进展，重置无进展计数
                    no_progress_count = 0

                # 只在第一次或每10次迭代时记录详细日志，减少日志量
                if iteration == 0 or iteration % 10 == 0:
                    logger.debug(
                        "调用外部接口获取硬件主机列表",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "limit": limit,
                            "current_available_count": len(all_available_hosts),
                            "no_progress_count": no_progress_count,
                        },
                    )

                # 步骤 2: 调用外部硬件接口获取主机列表（带认证）
                hardware_hosts = await self._fetch_hardware_hosts(
                    tc_id=request.tc_id,
                    skip=skip,
                    limit=limit,
                    request=fastapi_request,
                    user_id=user_id,
                    email=request.email,  # ✅ 传递 email 参数
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

                # ✅ 死循环检测：检查是否返回了重复的 hardware_id（说明外部接口不支持真正的分页）
                current_hardware_ids = {host.hardware_id for host in hardware_hosts if host.hardware_id}
                if current_hardware_ids.issubset(seen_hardware_ids):
                    logger.warning(
                        "检测到外部接口返回重复数据，可能不支持真正的分页，退出循环",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "current_hardware_ids_count": len(current_hardware_ids),
                            "seen_hardware_ids_count": len(seen_hardware_ids),
                            "current_available_count": len(all_available_hosts),
                        },
                    )
                    break

                # 更新已处理的 hardware_id 集合
                seen_hardware_ids.update(current_hardware_ids)

                # 步骤 3: 提取硬件 ID 列表用于查询本地数据库
                hardware_ids = [host.hardware_id for host in hardware_hosts if host.hardware_id]

                # 步骤 4: 查询 host_rec 表，获取可用的主机（优化：复用会话，减少连接占用）
                query_start_time = time.time()
                available_hosts = await self._filter_available_hosts_in_session(session, hardware_ids)
                query_duration = time.time() - query_start_time

                # 记录查询性能（如果查询时间超过阈值）
                if query_duration > 0.5:  # 超过500ms记录警告
                    logger.warning(
                        "数据库查询耗时较长",
                        extra={
                            "iteration": iteration,
                            "query_duration_ms": round(query_duration * 1000, 2),
                            "hardware_ids_count": len(hardware_ids),
                            "available_count": len(available_hosts),
                        },
                    )

                logger.debug(
                    "本轮过滤完成",
                    extra={
                        "iteration": iteration,
                        "fetched_hardware_count": len(hardware_hosts),
                        "available_count": len(available_hosts),
                        "total_available_before": len(all_available_hosts),
                        "query_duration_ms": round(query_duration * 1000, 2),
                    },
                )

                # 记录本次迭代前的可用主机数量（用于无进展检测）
                last_available_count = len(all_available_hosts)

                # 步骤 5: 添加新数据，同时跳过在 last_id 之后的数据
                added_count = 0  # 本次迭代新增的记录数
                for host in available_hosts:
                    # 如果指定了 last_id，跳过所有 ID 小于等于 last_id 的记录
                    # 注意：由于 ID 是字符串，需要转换为整数进行比较
                    # ✅ 使用实际的字段名 id（而不是 alias host_rec_id）
                    if request.last_id is not None:
                        try:
                            host_id_int = int(host.id)
                            last_id_int = int(request.last_id)
                            if host_id_int <= last_id_int:
                                continue
                        except (ValueError, TypeError):
                            # 如果转换失败，使用字符串比较（降级方案）
                            if host.id <= request.last_id:
                                continue

                    # 检查是否已经添加过（本次查询中的去重）
                    if host.id in seen_ids:
                        continue

                    all_available_hosts.append(host)
                    seen_ids.add(host.id)
                    added_count += 1

                    # 如果已经达到要求的数量，可以提前退出内层循环
                    if len(all_available_hosts) >= request.page_size:
                        break

                # ✅ 记录本次迭代新增的记录数（用于调试）
                if added_count == 0:
                    logger.debug(
                        "本轮迭代未新增任何记录",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "available_hosts_count": len(available_hosts),
                            "current_total": len(all_available_hosts),
                            "no_progress_count": no_progress_count + 1,
                        },
                    )

                # 准备下一页请求（在检查是否提前退出之前）
                skip += limit

            # 记录连接池状态（连接释放后）
            pool_status_after = mariadb_manager.get_pool_status()
            if pool_status_after["usage_percent"] >= 80:
                logger.warning(
                    "数据库连接池使用率较高，查询完成",
                    extra={
                        "usage_percent": pool_status_after["usage_percent"],
                        "checked_out": pool_status_after["checked_out"],
                        "max_connections": pool_status_after["max_connections"],
                    },
                )

        # 步骤 7: 进行分页切片 - 返回前 page_size 条数据
        paginated_hosts = all_available_hosts[: request.page_size]

        # ✅ 如果返回为空，查询数据库里的有效数据
        if not paginated_hosts:
            logger.info(
                "查询结果为空，降级查询数据库有效数据",
                extra={
                    "tc_id": request.tc_id,
                    "cycle_name": request.cycle_name,
                },
            )

            # 从本地数据库查询有效主机
            # 条件：host_state=0(空闲), appr_state=1(启用), del_flag=0(未删除), tcp_state=2(监听)
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                fallback_stmt = (
                    select(HostRec)
                    .where(
                        and_(
                            HostRec.host_state == HOST_STATE_FREE,
                            HostRec.appr_state == APPR_STATE_ENABLE,
                            HostRec.del_flag == 0,
                            HostRec.tcp_state == TCP_STATE_LISTEN,
                        )
                    )
                    .limit(request.page_size)  # 获取一页数据
                )

                fallback_result = await session.execute(fallback_stmt)
                fallback_hosts: List[HostRec] = fallback_result.scalars().all()

                if fallback_hosts:
                    paginated_hosts = [
                        AvailableHostInfo(
                            host_rec_id=str(h.id),  # 使用 alias host_rec_id
                            user_name=h.host_acct or "",  # 使用 alias user_name
                            host_ip=h.host_ip or "",
                        )
                        for h in fallback_hosts
                    ]
                    # 更新总数
                    all_available_hosts = paginated_hosts

                    logger.info(
                        "降级查询成功，获取到有效主机",
                        extra={
                            "count": len(paginated_hosts),
                            "first_host_id": paginated_hosts[0].id if paginated_hosts else None
                        },
                    )
                else:
                    logger.warning(
                        "降级查询未找到有效主机",
                        extra={
                            "tc_id": request.tc_id,
                        },
                    )

        # 步骤 8: 确定是否有下一页
        has_next = len(all_available_hosts) > request.page_size

        # 确定下一页的 last_id
        last_id: Optional[str] = None
        if paginated_hosts:
            # ✅ 使用实际的字段名 id（而不是 alias host_rec_id）
            last_id = paginated_hosts[-1].id

        operation_duration = time.time() - operation_start_time

        # 记录操作总耗时
        logger.info(
            "查询可用主机列表完成",
            extra={
                "tc_id": request.tc_id,
                "total_available_in_query": len(all_available_hosts),
                "page_size": request.page_size,
                "returned_count": len(paginated_hosts),
                "has_next": has_next,
                "last_id": last_id,
                "operation_duration_ms": round(operation_duration * 1000, 2),
                "is_test_data": len(paginated_hosts) == 1 and paginated_hosts[0].id == "1111111",
            },
        )

        # 如果操作耗时超过2秒，记录警告
        if operation_duration > 2.0:
            logger.warning(
                "查询可用主机列表耗时较长",
                extra={
                    "operation_duration_ms": round(operation_duration * 1000, 2),
                    "returned_count": len(paginated_hosts),
                    "page_size": request.page_size,
                },
            )

        # 构建响应对象
        response = AvailableHostsListResponse(
            hosts=paginated_hosts,
            total=len(all_available_hosts),  # 本次查询中发现的总数
            page_size=request.page_size,
            has_next=has_next,
            last_id=last_id,
        )

        # ✅ 优化：缓存首次查询结果（30秒），减少外部接口调用
        if cache_key is not None:
            try:
                # 将响应对象转换为字典以便缓存
                cache_data = {
                    "hosts": [host.model_dump() for host in paginated_hosts],
                    "total": len(all_available_hosts),
                    "page_size": request.page_size,
                    "has_next": has_next,
                    "last_id": last_id,
                }
                await redis_manager.set(cache_key, cache_data, expire=30)
                logger.debug(
                    "可用主机列表已缓存（首次查询）",
                    extra={"cache_key": cache_key, "expire_seconds": 30},
                )
            except Exception as e:
                logger.warning("缓存可用主机列表失败", extra={"error": str(e)})

        return response

    def _get_mock_hardware_hosts(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HardwareHostData]:
        """获取 Mock 硬件主机数据

        Args:
            skip: 跳过条数
            limit: 返回数量

        Returns:
            Mock 硬件主机列表
        """
        # Mock 数据：基于用户提供的格式
        # 注意：前两条数据对应数据库中的记录，需要确保数据库中的 hardware_id 字段已更新
        # 第一条：id=1846557388006625421, mg_id='test', host_ip='127.0.0.1', mac_addr='123'
        # 第二条：id=1847395771312739675, mg_id='test123', host_ip='192.168.1.1', mac_addr='234'
        mock_data = [
            {
                "hardware_id": "test-hardware-1",
                "name": "Test Host 1 (127.0.0.1)",
                "dmr_config": {
                    "revision": 1,
                    "mainboard": {
                        "plt_meta_data": {
                            "platform": "DMR",
                            "label_plt_cfg": "test_config",
                        },
                        "board": {
                            "board_meta_data": {
                                "board_name": "SHMRCDMR",
                                "host_name": "test-host-1",
                                "host_ip": "127.0.0.1",
                            },
                        },
                    },
                },
                "updated_time": "2025-10-21T02:39:14Z",
                "updated_by": "test@intel.com",
                "tags": ["test", "dmr"],
            },
            {
                "hardware_id": "test-hardware-2",
                "name": "Test Host 2 (192.168.1.1)",
                "dmr_config": {
                    "revision": 1,
                    "mainboard": {
                        "plt_meta_data": {
                            "platform": "DMR",
                            "label_plt_cfg": "test123_config",
                        },
                        "board": {
                            "board_meta_data": {
                                "board_name": "SHMRCDMR",
                                "host_name": "test-host-2",
                                "host_ip": "192.168.1.1",
                            },
                        },
                    },
                },
                "updated_time": "2025-10-30T08:44:59Z",
                "updated_by": "test@intel.com",
                "tags": ["test", "dmr"],
            },
            {
                "hardware_id": "abc123",
                "name": "Test Server Config",
                "dmr_config": {
                    "revision": 1,
                    "mainboard": {
                        "plt_meta_data": {
                            "platform": "DMR",
                            "label_plt_cfg": "config_label",
                        },
                        "board": {
                            "board_meta_data": {
                                "board_name": "SHMRCDMR",
                                "host_name": "test-host",
                                "host_ip": "10.239.168.169",
                            },
                        },
                    },
                },
                "updated_time": "2025-09-17T10:00:00Z",
                "updated_by": "user@intel.com",
                "tags": ["test", "dmr"],
            },
            {
                "hardware_id": "def456",
                "name": "Test Server Config 2",
                "dmr_config": {
                    "revision": 1,
                    "mainboard": {
                        "plt_meta_data": {
                            "platform": "DMR",
                            "label_plt_cfg": "config_label_2",
                        },
                        "board": {
                            "board_meta_data": {
                                "board_name": "SHMRCDMR",
                                "host_name": "test-host-2",
                                "host_ip": "10.239.168.170",
                            },
                        },
                    },
                },
                "updated_time": "2025-09-17T11:00:00Z",
                "updated_by": "user2@intel.com",
                "tags": ["test", "dmr", "production"],
            },
            {
                "hardware_id": "ghi789",
                "name": "Test Server Config 3",
                "dmr_config": {
                    "revision": 2,
                    "mainboard": {
                        "plt_meta_data": {
                            "platform": "DMR",
                            "label_plt_cfg": "config_label_3",
                        },
                        "board": {
                            "board_meta_data": {
                                "board_name": "SHMRCDMR",
                                "host_name": "test-host-3",
                                "host_ip": "10.239.168.171",
                            },
                        },
                    },
                },
                "updated_time": "2025-09-17T12:00:00Z",
                "updated_by": "user3@intel.com",
                "tags": ["test"],
            },
        ]

        # 应用分页
        paginated_data = mock_data[skip:skip + limit]
        return [HardwareHostData(**item) for item in paginated_data]

    async def _fetch_hardware_hosts(
        self,
        tc_id: str,
        skip: int = 0,
        limit: int = 100,
        request=None,  # FastAPI Request 对象（用于获取 user_id）
        user_id: Optional[int] = None,  # 用户ID（可选，如果提供了 email 则可以为 None）
        email: Optional[str] = None,  # 用户邮箱（可选）。如果提供，将直接使用该 email 获取 token，不查询数据库
    ) -> List[HardwareHostData]:
        """调用外部硬件接口获取主机列表（带认证）

        使用统一的外部接口调用客户端，自动处理认证和 SSL 配置。

        认证方式：
        - **方式1（推荐）**: 如果提供了 `email` 参数，直接使用该 email 获取外部接口 token，跳过数据库查询，性能更优
        - **方式2**: 如果未提供 `email`，系统会根据 `user_id`（从 request 或参数获取）查询数据库获取 email

        Args:
            tc_id: 测试用例 ID
            skip: 跳过条数（用于分页）
            limit: 返回数量（每次请求的最大数量）
            request: FastAPI Request 对象（用于从请求头获取 user_id）
            user_id: 当前登录管理后台用户的ID（可选，如果提供了 email 则可以为 None）
            email: 用户邮箱（可选）。如果提供，将直接使用该 email 获取 token，不查询数据库，提高性能

        Returns:
            硬件主机列表（HardwareHostData 对象列表）

        Raises:
            BusinessError: 当接口调用失败时，包括：
                - 外部接口调用失败（网络错误、超时等）
                - 外部接口返回非 200 状态码
                - 响应数据格式不符合预期

        Note:
            - 如果 USE_HARDWARE_MOCK 环境变量设置为 true，将返回模拟数据
            - Token 获取支持 Redis 缓存，避免重复请求
            - SSL 验证配置通过 HTTP_CLIENT_VERIFY_SSL 环境变量控制
        """
        # ✅ 检查是否使用 Mock 数据（通过环境变量控制）
        use_mock = os.getenv("USE_HARDWARE_MOCK", "false").lower() in ("true", "1", "yes")

        if use_mock:
            # 减少Mock日志频率：只在第一次调用或每10次调用时记录
            # 使用模块级变量跟踪调用次数（简单方案，生产环境可考虑更优雅的实现）
            if not hasattr(self, "_mock_call_count"):
                self._mock_call_count = 0
            self._mock_call_count += 1

            # 只在第一次或每10次调用时记录日志
            if self._mock_call_count == 1 or self._mock_call_count % 10 == 0:
                logger.debug(
                    "使用 Mock 硬件接口数据",
                    extra={
                        "tc_id": tc_id,
                        "skip": skip,
                        "limit": limit,
                        "call_count": self._mock_call_count,
                    },
                )
            return self._get_mock_hardware_hosts(skip=skip, limit=limit)

        try:
            # ✅ 使用统一的外部接口调用客户端（支持认证和 SSL 配置）
            # url_path = "/api/v1/hardware/hosts"
            url_path = "/api/v1/hardware/mock_hosts"
            params = {
                "tc_id": tc_id,
                "skip": skip,
                "limit": limit,
            }

            logger.debug(
                "调用硬件接口（带认证）",
                extra={
                    "url_path": url_path,
                    "params": params,
                    "user_id": user_id,
                    "email": email,
                },
            )

            # ✅ 使用统一的外部接口调用方法（自动处理 token 获取和认证）
            # 如果提供了 email，将直接使用该 email 获取 token，不查询数据库
            # ✅ 优化：将超时时间从 30s 降低到 10s，快速失败避免阻塞
            response = await call_external_api(
                method="GET",
                url_path=url_path,
                request=request,
                user_id=user_id,
                email=email,  # ✅ 传递 email 参数
                params=params,
                timeout=10.0,  # ✅ 优化：从 30.0 降低到 10.0
            )

            status_code = response.get("status_code")
            response_body = response.get("body")

            if status_code != 200:
                error_msg = (
                    response_body.get("message", "未知错误")
                    if isinstance(response_body, dict)
                    else str(response_body)
                )
                raise BusinessError(
                    message=f"硬件接口调用失败: {error_msg}",
                    error_code="HOST_HARDWARE_API_ERROR",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=status_code or 500,
                )

            # 解析响应数据
            data = response_body if response_body else {}
            hardware_hosts: List[HardwareHostData] = []
            skipped_count = 0  # 记录跳过的无效记录数

            if isinstance(data, list):
                # 响应格式：直接数组
                for item in data:
                    # ✅ 过滤掉 hardware_id 为 None 或空字符串的记录
                    hardware_id = item.get("hardware_id") if isinstance(item, dict) else None
                    if not hardware_id or (isinstance(hardware_id, str) and not hardware_id.strip()):
                        skipped_count += 1
                        logger.debug(
                            "跳过无效的硬件记录（hardware_id 为空）",
                            extra={
                                "tc_id": tc_id,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
                        continue

                    try:
                        hardware_hosts.append(HardwareHostData(**item))
                    except Exception as e:
                        # ✅ 捕获 Pydantic 验证错误，记录详细信息并跳过该记录
                        skipped_count += 1
                        logger.warning(
                            "硬件记录验证失败，跳过该记录",
                            extra={
                                "tc_id": tc_id,
                                "hardware_id": hardware_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
            elif isinstance(data, dict) and "data" in data:
                # 响应格式：{ "data": [...] }
                for item in data["data"]:
                    # ✅ 过滤掉 hardware_id 为 None 或空字符串的记录
                    hardware_id = item.get("hardware_id") if isinstance(item, dict) else None
                    if not hardware_id or (isinstance(hardware_id, str) and not hardware_id.strip()):
                        skipped_count += 1
                        logger.debug(
                            "跳过无效的硬件记录（hardware_id 为空）",
                            extra={
                                "tc_id": tc_id,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
                        continue

                    try:
                        hardware_hosts.append(HardwareHostData(**item))
                    except Exception as e:
                        # ✅ 捕获 Pydantic 验证错误，记录详细信息并跳过该记录
                        skipped_count += 1
                        logger.warning(
                            "硬件记录验证失败，跳过该记录",
                            extra={
                                "tc_id": tc_id,
                                "hardware_id": hardware_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
            else:
                logger.warning(
                    "硬件接口返回数据格式不符合预期",
                    extra={
                        "response_type": type(data).__name__,
                        "response_keys": (list(data.keys()) if isinstance(data, dict) else "N/A"),
                    },
                )

            # ✅ 记录解析结果统计
            if skipped_count > 0:
                logger.warning(
                    "硬件接口返回了无效记录，已跳过",
                    extra={
                        "tc_id": tc_id,
                        "skipped_count": skipped_count,
                        "valid_count": len(hardware_hosts),
                        "total_count": skipped_count + len(hardware_hosts),
                    },
                )
            else:
                logger.debug(
                    "硬件接口数据解析完成",
                    extra={
                        "tc_id": tc_id,
                        "valid_count": len(hardware_hosts),
                    },
                )

            return hardware_hosts

        except BusinessError:
            # ✅ 重新抛出业务异常（call_external_api 已经处理了异常并转换为 BusinessError）
            raise
        except Exception as e:
            # ✅ 捕获其他未预期的异常
            logger.error(
                "硬件接口调用异常",
                extra={
                    "tc_id": tc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="硬件接口调用异常，请稍后重试",
                error_code="HOST_HARDWARE_API_ERROR",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=500,
            )

    async def _filter_available_hosts_in_session(
        self,
        session: "AsyncSession",
        hardware_ids: List[str],
    ) -> List[AvailableHostInfo]:
        """根据条件过滤可用的主机（使用已有会话，优化连接池使用）

        这是 _filter_available_hosts 的优化版本，接受已有会话参数，
        避免在循环中重复创建数据库连接。

        Args:
            session: 数据库会话（已创建）
            hardware_ids: 硬件 ID 列表

        Returns:
            可用主机列表
        """
        if not hardware_ids:
            return []

        # 批量查询优化：如果 hardware_ids 太多，分批查询
        batch_size = 500
        all_available_hosts: List[AvailableHostInfo] = []

        try:
            total_query_time = 0.0

            # 分批处理 hardware_ids
            for i in range(0, len(hardware_ids), batch_size):
                batch_ids = hardware_ids[i:i + batch_size]
                batch_start_time = time.time()

                # 构建查询条件（使用索引优化）
                # 使用复合索引：ix_host_rec_hardware_id_state (hardware_id, host_state, appr_state, tcp_state, del_flag)
                stmt = select(HostRec).where(
                    and_(
                        HostRec.hardware_id.in_(batch_ids),
                        HostRec.appr_state == 1,  # 启用状态
                        HostRec.host_state == 0,  # 空闲状态
                        HostRec.tcp_state == 2,  # 监听/连接正常
                        HostRec.del_flag == 0,  # 未删除
                    )
                ).limit(1000)  # 限制单次查询结果数量

                result = await session.execute(stmt)
                host_recs = result.scalars().all()
                batch_duration = time.time() - batch_start_time
                total_query_time += batch_duration

                # 记录慢查询（单批次超过200ms）
                if batch_duration > 0.2:
                    logger.warning(
                        "数据库批次查询耗时较长",
                        extra={
                            "batch_index": i // batch_size + 1,
                            "batch_size": len(batch_ids),
                            "batch_duration_ms": round(batch_duration * 1000, 2),
                            "result_count": len(host_recs),
                        },
                    )

                # 转换为响应格式
                batch_hosts: List[AvailableHostInfo] = [
                    AvailableHostInfo(
                        host_rec_id=str(host_rec.id),
                        user_name=host_rec.host_acct or "",
                        host_ip=cast(str, host_rec.host_ip) if host_rec.host_ip else "",
                    )
                    for host_rec in host_recs
                    if host_rec.hardware_id  # 确保 hardware_id 不为空
                ]

                all_available_hosts.extend(batch_hosts)

            logger.debug(
                "host_rec 表查询完成（复用会话）",
                extra={
                    "requested_hardware_ids": len(hardware_ids),
                    "available_hosts": len(all_available_hosts),
                    "batches": (len(hardware_ids) + batch_size - 1) // batch_size,
                    "total_query_duration_ms": round(total_query_time * 1000, 2),
                    "avg_query_duration_ms": round(
                        (total_query_time / max(1, (len(hardware_ids) + batch_size - 1) // batch_size)) * 1000,
                        2,
                    ),
                },
            )

            return all_available_hosts

        except Exception as e:
            logger.error(
                "数据库查询失败",
                extra={
                    "requested_hardware_ids": len(hardware_ids),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise

    async def _filter_available_hosts(
        self,
        hardware_ids: List[str],
    ) -> List[AvailableHostInfo]:
        """根据条件过滤可用的主机（批量查询优化）

        过滤条件：
        - hardware_id 在指定列表中
        - appr_state = 1（启用状态）
        - host_state = 0（空闲状态）
        - tcp_state = 2（监听/连接正常）
        - del_flag = 0（未删除）

        性能优化：
        - 使用 hardware_id 索引加速查询
        - 批量查询，减少数据库往返次数
        - 限制查询结果数量，避免内存溢出
        - 添加数据库连接重试机制，处理连接丢失问题

        Args:
            hardware_ids: 硬件 ID 列表

        Returns:
            可用主机列表
        """
        if not hardware_ids:
            return []

        # 批量查询优化：如果 hardware_ids 太多，分批查询
        # 避免 SQL IN 子句过长（MySQL/MariaDB 限制）
        batch_size = 500
        all_available_hosts: List[AvailableHostInfo] = []

        # 重试配置
        max_retries = 3
        retry_delay = 1.0  # 初始重试延迟（秒）

        for attempt in range(max_retries):
            try:
                session_factory = mariadb_manager.get_session()
                async with session_factory() as session:
                    # 分批处理 hardware_ids
                    for i in range(0, len(hardware_ids), batch_size):
                        batch_ids = hardware_ids[i:i + batch_size]

                        # 构建查询条件（使用索引优化）
                        stmt = select(HostRec).where(
                            and_(
                                HostRec.hardware_id.in_(batch_ids),
                                HostRec.appr_state == 1,  # 启用状态
                                HostRec.host_state == 0,  # 空闲状态
                                HostRec.tcp_state == 2,  # 监听/连接正常
                                HostRec.del_flag == 0,  # 未删除
                            )
                        ).limit(1000)  # 限制单次查询结果数量

                        result = await session.execute(stmt)
                        host_recs = result.scalars().all()

                        # 转换为响应格式
                        batch_hosts: List[AvailableHostInfo] = [
                            AvailableHostInfo(
                                host_rec_id=str(host_rec.id),  # ✅ 转换为字符串避免精度丢失
                                user_name=host_rec.host_acct or "",
                                host_ip=cast(str, host_rec.host_ip) if host_rec.host_ip else "",
                            )
                            for host_rec in host_recs
                            if host_rec.hardware_id  # 确保 hardware_id 不为空
                        ]

                        all_available_hosts.extend(batch_hosts)

                    logger.debug(
                        "host_rec 表查询完成",
                        extra={
                            "requested_hardware_ids": len(hardware_ids),
                            "available_hosts": len(all_available_hosts),
                            "batches": (len(hardware_ids) + batch_size - 1) // batch_size,
                            "attempt": attempt + 1,
                        },
                    )

                    return all_available_hosts

            except OperationalError as e:
                # 数据库连接错误，尝试重试
                error_code = getattr(e.orig, "args", [None])[0] if hasattr(e, "orig") else None
                is_connection_lost = (
                    error_code == 2013  # Lost connection to MySQL server during query
                    or "Lost connection" in str(e)
                    or "Connection lost" in str(e)
                )

                if is_connection_lost and attempt < max_retries - 1:
                    # 计算指数退避延迟
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        "数据库连接丢失，准备重试",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay_seconds": delay,
                            "error_code": error_code,
                            "error_message": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                    # 清空已收集的结果，重新开始查询
                    all_available_hosts = []
                    continue
                else:
                    # 重试次数已用完或不是连接丢失错误，重新抛出异常
                    logger.error(
                        "数据库查询失败，无法重试",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "error_code": error_code,
                            "error_message": str(e),
                            "is_connection_lost": is_connection_lost,
                        },
                        exc_info=True,
                    )
                    raise

        # 如果所有重试都失败，返回空列表（不应该到达这里，因为会抛出异常）
        logger.error(
            "数据库查询失败，所有重试均失败",
            extra={
                "requested_hardware_ids": len(hardware_ids),
                "max_retries": max_retries,
            },
        )
        return []
