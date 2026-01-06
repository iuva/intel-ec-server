"""主机相关的 Pydantic 模式"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


class HostBase(BaseModel):
    """主机基础模式"""

    host_id: str = Field(description="主机唯一标识")
    hostname: str = Field(description="主机名称")
    ip_address: str = Field(description="IP地址")
    os_type: Optional[str] = Field(default=None, description="操作系统类型")
    os_version: Optional[str] = Field(default=None, description="操作系统版本")


class HostCreate(HostBase):
    """创建主机请求模式"""


class HostUpdate(BaseModel):
    """更新主机请求模式"""

    hostname: Optional[str] = Field(default=None, description="主机名称")
    ip_address: Optional[str] = Field(default=None, description="IP地址")
    os_type: Optional[str] = Field(default=None, description="操作系统类型")
    os_version: Optional[str] = Field(default=None, description="操作系统版本")
    status: Optional[str] = Field(default=None, description="主机状态")


class HostStatusUpdate(BaseModel):
    """更新主机状态请求模式

    支持两种更新方式：
    1. 使用 status 字符串字段（推荐）："online", "offline", "error"
    2. 使用 host_state 和 appr_state 整数字段（高级用法）
    """

    status: Optional[str] = Field(
        default=None, description="主机状态 (online, offline, error)"
    )
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "主机状态码 (0-空闲, 1-已锁定, 2-已占用, 3-执行中, "
            "4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中)"
        ),
    )
    appr_state: Optional[int] = Field(
        default=None, description="审批状态 (0-停用, 1-启用/新增, 2-存在改动)"
    )


class HostResponse(HostBase):
    """主机响应模式"""

    id: int = Field(description="主键ID")
    status: str = Field(description="主机状态")
    last_heartbeat: Optional[datetime] = Field(default=None, description="最后心跳时间")
    created_time: datetime = Field(description="创建时间")
    updated_time: datetime = Field(description="更新时间")
    del_flag: bool = Field(description="是否已删除")

    model_config = {"from_attributes": True}


class HostListResponse(BaseModel):
    """主机列表响应模式"""

    hosts: List[HostResponse] = Field(description="主机列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")


class VNCConnectionReport(BaseModel):
    """VNC 连接结果上报 - 浏览器插件上报VNC连接结果"""

    user_id: str = Field(..., description="用户ID")
    tc_id: str = Field(..., description="执行测试ID")
    cycle_name: str = Field(..., description="周期名称")
    user_name: str = Field(..., description="用户名称")
    host_id: str = Field(..., description="主机ID")
    connection_status: str = Field(..., description="连接状态 (success/failed)", pattern=r"^(success|failed)$")
    connection_time: datetime = Field(..., description="连接时间（支持格式：yyyy/MM/dd HH:mm:ss 或 ISO 8601）")

    model_config = {"from_attributes": True}

    @field_validator("connection_time", mode="before")
    @classmethod
    def parse_connection_time(cls, value: Any) -> datetime:
        """解析连接时间，支持两种格式：
        1. yyyy/MM/dd HH:mm:ss（如：2025/01/30 10:00:00）
        2. ISO 8601 格式（如：2025-01-30T10:00:00Z）

        Args:
            value: 输入值（可能是字符串或 datetime 对象）

        Returns:
            datetime 对象

        Raises:
            ValueError: 格式不正确时抛出
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # 尝试解析 yyyy/MM/dd HH:mm:ss 格式
            try:
                # 解析为 naive datetime，然后添加 UTC 时区
                dt = datetime.strptime(value, "%Y/%m/%d %H:%M:%S")
                # 假设输入时间是 UTC 时间，添加 UTC 时区信息
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                # 如果失败，尝试 ISO 8601 格式（Pydantic 默认支持）
                try:
                    # 使用 datetime.fromisoformat 解析 ISO 8601 格式
                    # 处理带时区的格式（如 2025-01-30T10:00:00Z）
                    if value.endswith("Z"):
                        value = value[:-1] + "+00:00"
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    # 确保有时区信息，如果没有则添加 UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError as e:
                    raise ValueError(
                        (
                            f"连接时间格式不正确，支持格式：yyyy/MM/dd HH:mm:ss（如：2025/01/30 10:00:00）"
                            f"或 ISO 8601（如：2025-01-30T10:00:00Z），当前值：{value}"
                        )
                    ) from e

        raise ValueError(f"连接时间必须是字符串或 datetime 对象，当前类型：{type(value).__name__}")


class VNCConnectionResponse(BaseModel):
    """VNC 连接结果上报响应"""

    host_id: str = Field(description="主机ID")
    connection_status: str = Field(description="连接状态")
    connection_time: datetime = Field(description="连接时间")

    model_config = {"from_attributes": True}

    @field_serializer("connection_time")
    def serialize_connection_time(self, value: datetime) -> str:
        """格式化连接时间为 yyyy/MM/dd HH:mm:ss 格式"""
        if value is None:
            return ""
        # 转换为本地时间（如果需要，可以指定时区）
        # 这里使用 UTC 时间，格式化为 yyyy/MM/dd HH:mm:ss
        return value.strftime("%Y/%m/%d %H:%M:%S")


class AgentVNCConnectionReportRequest(BaseModel):
    """Agent VNC 连接状态上报请求

    vnc_state 说明：
    - 1: 连接成功
    - 2: 连接断开
    """

    vnc_state: int = Field(
        ...,
        ge=1,
        le=2,
        description="VNC连接状态（1=连接成功，2=连接断开）",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "vnc_state": 1,
            },
        },
    }


class AgentVNCConnectionReportResponse(BaseModel):
    """Agent VNC 连接状态上报响应"""

    host_id: int = Field(..., description="主机ID")
    host_state: int = Field(..., description="更新后的主机状态（0=空闲，1=已锁定，2=已占用）")
    vnc_state: int = Field(..., description="上报的VNC连接状态（1=连接成功，2=连接断开）")
    updated: bool = Field(..., description="是否成功更新")

    model_config = {
        "from_attributes": True,
    }


class QueryAvailableHostsRequest(BaseModel):
    """查询可用主机列表请求模式 - 使用游标分页

    业务说明：
    - 首次请求不提供 last_id，从头开始
    - 后续请求提供上一页最后一条记录的 id（last_id）
    - 系统根据 last_id 计算内部偏移量
    - 避免多用户并发时的状态污染问题
    - 如果提供了 email，将直接使用该 email 进行外部接口认证，不查询数据库
    """

    tc_id: str = Field(description="测试用例ID")
    cycle_name: str = Field(description="测试周期名称")
    user_name: str = Field(description="用户名")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量（1-100）")
    last_id: Optional[str] = Field(
        default=None,
        description="上一页最后一条记录的 id。首次请求为 null，后续请求需要传入上一页最后一条记录的 host_rec_id",
    )
    email: Optional[str] = Field(
        default=None,
        description="用户邮箱（可选）。如果提供，将直接使用该 email 进行外部接口认证，不查询数据库",
    )

    model_config = {"from_attributes": True}


class DMRBoardMetaData(BaseModel):
    """DMR 板卡元数据"""

    board_name: Optional[str] = Field(default=None, description="板卡名称")
    host_name: Optional[str] = Field(default=None, description="主机名称")
    host_ip: Optional[str] = Field(default=None, description="主机IP")

    model_config = {"from_attributes": True}


class DMRBoard(BaseModel):
    """DMR 板卡配置"""

    board_meta_data: Optional[DMRBoardMetaData] = Field(default=None, description="板卡元数据")

    model_config = {"from_attributes": True}


class DMRPlatformMetaData(BaseModel):
    """DMR 平台元数据"""

    platform: Optional[str] = Field(default=None, description="平台类型")
    label_plt_cfg: Optional[str] = Field(default=None, description="平台配置标签")

    model_config = {"from_attributes": True}


class DMRMainboard(BaseModel):
    """DMR 主板配置"""

    plt_meta_data: Optional[DMRPlatformMetaData] = Field(default=None, description="平台元数据")
    board: Optional[DMRBoard] = Field(default=None, description="板卡配置")

    model_config = {"from_attributes": True}


class DMRConfig(BaseModel):
    """DMR 配置"""

    revision: Optional[int] = Field(default=None, description="版本号")
    mainboard: Optional[DMRMainboard] = Field(default=None, description="主板配置")

    model_config = {"from_attributes": True}


class HardwareHostData(BaseModel):
    """外部硬件接口返回的主机数据"""

    hardware_id: str = Field(description="硬件ID")
    name: Optional[str] = Field(default=None, description="主机配置名称")
    dmr_config: Optional[DMRConfig] = Field(default=None, description="DMR配置")
    updated_time: Optional[str] = Field(default=None, description="更新时间（ISO格式字符串）")
    updated_by: Optional[str] = Field(default=None, description="更新人")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    # 兼容旧字段
    ip: Optional[str] = Field(
        default=None,
        description="IP地址（兼容字段，优先使用 dmr_config.mainboard.board.board_meta_data.host_ip）",
    )
    hostname: Optional[str] = Field(
        default=None,
        description="主机名称（兼容字段，优先使用 dmr_config.mainboard.board.board_meta_data.host_name）",
    )
    query: Optional[str] = Field(default=None, description="查询条件")

    model_config = {"from_attributes": True}


class AvailableHostInfo(BaseModel):
    """可用主机信息"""

    id: str = Field(description="主机记录ID (host_rec.id)", alias="host_rec_id")
    username: str = Field(description="用户名 (host_acct)", alias="user_name")
    host_ip: str = Field(description="主机IP地址 (host_ip)")

    model_config = {"from_attributes": True, "populate_by_name": True}


class AvailableHostsListResponse(BaseModel):
    """查询可用主机列表响应模式 - 游标分页响应

    字段说明：
    - hosts: 当前页的主机列表
    - total: 本次查询过程中发现的可用主机总数（不是全局总数）
    - page_size: 每页大小
    - has_next: 是否还有下一页
    - last_id: 当前页最后一条记录的 id，用于下一页请求
    """

    hosts: List[AvailableHostInfo] = Field(description="可用主机列表")
    total: int = Field(description="本次查询发现的可用主机总数")
    page_size: int = Field(description="每页大小")
    has_next: bool = Field(description="是否有下一页")
    last_id: Optional[str] = Field(default=None, description="当前页最后一条记录的 id，用于请求下一页")

    model_config = {"from_attributes": True}


class GetVNCConnectionRequest(BaseModel):
    """获取 VNC 连接信息请求模式"""

    id: str = Field(description="主机ID (host_rec.id)")

    model_config = {"from_attributes": True}


class VNCConnectionInfo(BaseModel):
    """VNC 连接信息响应模式"""

    ip: str = Field(description="VNC服务器IP地址")
    port: str = Field(description="VNC服务端口")
    username: str = Field(description="连接用户名")
    ***REMOVED***word: str = Field(description="连接密码")

    model_config = {"from_attributes": True}


class GetRetryVNCListRequest(BaseModel):
    """获取重试 VNC 列表请求模式"""

    user_id: str = Field(description="用户ID")

    model_config = {"from_attributes": True}


class RetryVNCHostInfo(BaseModel):
    """重试 VNC 主机信息"""

    host_id: str = Field(description="主机ID (host_rec.id)")
    host_ip: str = Field(description="主机IP")
    user_name: str = Field(description="主机账号 (host_acct)")

    model_config = {"from_attributes": True}


class RetryVNCListResponse(BaseModel):
    """重试 VNC 列表响应模式"""

    hosts: List[RetryVNCHostInfo] = Field(description="重试 VNC 主机列表")
    total: int = Field(description="主机总数")

    model_config = {"from_attributes": True}


class ReleaseHostsRequest(BaseModel):
    """释放主机请求模式"""

    user_id: str = Field(description="用户ID")
    host_list: List[str] = Field(description="主机ID列表")

    model_config = {"from_attributes": True}


class ReleaseHostsResponse(BaseModel):
    """释放主机响应模式"""

    updated_count: int = Field(description="更新的记录数（逻辑删除）")
    user_id: str = Field(description="用户ID")
    host_list: List[str] = Field(description="主机ID列表")

    model_config = {"from_attributes": True}


# ==================== 管理后台主机管理 Schema ====================


class AdminHostListRequest(BaseModel):
    """管理后台主机列表查询请求模式"""

    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小（1-100）")
    mac: Optional[str] = Field(default=None, description="MAC地址（可选搜索条件，对应 host_rec.mac_addr）")
    username: Optional[str] = Field(default=None, description="主机账号（可选搜索条件，对应 host_rec.host_acct）")
    host_state: Optional[int] = Field(
        default=None,
        ge=0,
        le=4,
        description=(
            "主机状态（可选搜索条件，对应 host_rec.host_state；"
            "支持范围：0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线）"
        ),
    )
    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（可选搜索条件，对应 host_rec.mg_id）")
    use_by: Optional[str] = Field(default=None, description="使用人（可选搜索条件，对应 host_exec_log.user_name）")

    model_config = {"from_attributes": True}


class AdminHostInfo(BaseModel):
    """管理后台主机信息响应模式"""

    host_id: str = Field(description="主机ID（host_rec 表主键 id）")
    username: Optional[str] = Field(default=None, description="主机账号（host_rec 表 host_acct）")
    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（host_rec 表 mg_id）")
    mac: Optional[str] = Field(default=None, description="MAC地址（host_rec 表 mac_addr）")
    use_by: Optional[str] = Field(default=None, description="使用人（host_exec_log 表 user_name，最新一条）")
    host_state: Optional[int] = Field(default=None, description="主机状态（host_rec 表 host_state）")
    appr_state: Optional[int] = Field(default=None, description="审批状态（host_rec 表 appr_state）")

    model_config = {"from_attributes": True}


class AdminHostListResponse(BaseModel):
    """管理后台主机列表响应模式"""

    hosts: List[AdminHostInfo] = Field(description="主机列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")

    model_config = {"from_attributes": True}


class AdminHostDeleteRequest(BaseModel):
    """管理后台主机删除请求模式"""

    id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostDeleteResponse(BaseModel):
    """管理后台主机删除响应模式"""

    id: str = Field(description="已删除的主机ID")

    model_config = {"from_attributes": True}


class AdminHostDisableRequest(BaseModel):
    """管理后台主机停用请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostDisableResponse(BaseModel):
    """管理后台主机停用响应模式"""

    id: str = Field(description="主机ID")
    appr_state: int = Field(default=0, description="更新后的审批状态（0=停用）")
    host_state: int = Field(default=7, description="更新后的主机状态（7=手动停用）")

    model_config = {"from_attributes": True}


class AdminHostForceOfflineRequest(BaseModel):
    """管理后台主机强制下线请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostForceOfflineResponse(BaseModel):
    """管理后台主机强制下线响应模式"""

    id: str = Field(description="主机ID")
    host_state: int = Field(default=4, description="更新后的主机状态（4=离线）")

    model_config = {"from_attributes": True}


class AdminHostDetailRequest(BaseModel):
    """管理后台主机详情查询请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostHwDetailInfo(BaseModel):
    """管理后台主机硬件详情信息响应模式"""

    hw_info: Optional[Dict[str, Any]] = Field(default=None, description="硬件信息（host_hw_rec 表 hw_info）")
    appr_time: Optional[datetime] = Field(default=None, description="审批时间（host_hw_rec 表 appr_time）")

    model_config = {"from_attributes": True}


class AdminHostDetailResponse(BaseModel):
    """管理后台主机详情响应模式"""

    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（host_rec 表 mg_id）")
    mac: Optional[str] = Field(default=None, description="MAC地址（host_rec 表 mac_addr）")
    ip: Optional[str] = Field(default=None, description="IP地址（host_rec 表 host_ip）")
    username: Optional[str] = Field(default=None, description="主机账号（host_rec 表 host_acct）")
    ***REMOVED***word: Optional[str] = Field(default=None, description="主机密码（host_rec 表 host_pwd，已解密）")
    port: Optional[int] = Field(default=None, description="端口（host_rec 表 host_port）")
    hw_list: List[AdminHostHwDetailInfo] = Field(
        default_factory=list,
        description="硬件信息列表（host_hw_rec 表 sync_state=2 的记录，按 updated_time 倒序）",
    )

    model_config = {"from_attributes": True}


class AdminHostUpdatePasswordRequest(BaseModel):
    """管理后台主机密码修改请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")
    ***REMOVED***word: str = Field(..., min_length=1, description="新密码（明文，将进行AES加密后存储）")

    model_config = {"from_attributes": True}


class AdminHostUpdatePasswordResponse(BaseModel):
    """管理后台主机密码修改响应模式"""

    id: str = Field(description="主机ID")

    model_config = {"from_attributes": True}


class AdminHostExecLogListRequest(BaseModel):
    """管理后台主机执行日志列表查询请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")
    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小（1-100）")

    model_config = {"from_attributes": True}


class AdminHostExecLogInfo(BaseModel):
    """管理后台主机执行日志信息响应模式"""

    log_id: Optional[str] = Field(default=None, description="执行日志ID（host_exec_log 表 id）")
    exec_date: Optional[str] = Field(default=None, description="执行日期（格式：%Y-%m-%d）")
    exec_time: Optional[str] = Field(default=None, description="执行时长（格式：%H:%M:%S）")
    tc_id: Optional[str] = Field(default=None, description="执行测试ID（host_exec_log 表 tc_id）")
    use_by: Optional[str] = Field(default=None, description="使用人（host_exec_log 表 user_name）")
    case_state: Optional[int] = Field(default=None, description="执行状态（0-空闲, 1-启动, 2-成功, 3-失败）")
    result_msg: Optional[str] = Field(default=None, description="执行结果（host_exec_log 表 result_msg）")
    log_url: Optional[str] = Field(default=None, description="执行日志地址（host_exec_log 表 log_url）")

    model_config = {"from_attributes": True}


class AdminHostExecLogListResponse(BaseModel):
    """管理后台主机执行日志列表响应模式"""

    logs: List[AdminHostExecLogInfo] = Field(default_factory=list, description="执行日志列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")

    model_config = {"from_attributes": True}


class AdminApprHostListRequest(BaseModel):
    """管理后台待审批主机列表查询请求模式"""

    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小（1-100）")
    mac: Optional[str] = Field(default=None, description="MAC地址（可选搜索条件，对应 host_rec.mac_addr）")
    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（可选搜索条件，对应 host_rec.mg_id）")
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "主机状态（可选搜索条件，对应 host_rec.host_state；"
            "0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, "
            "5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）"
        ),
    )

    model_config = {"from_attributes": True}


class AdminApprHostInfo(BaseModel):
    """管理后台待审批主机信息响应模式"""

    host_id: str = Field(description="主机ID（host_rec 表主键 id）")
    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（host_rec 表 mg_id）")
    mac_addr: Optional[str] = Field(default=None, description="MAC地址（host_rec 表 mac_addr）")
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "主机状态（host_rec 表 host_state；"
            "0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, "
            "5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）"
        ),
    )
    subm_time: Optional[datetime] = Field(default=None, description="申报时间（host_rec 表 subm_time）")
    diff_state: Optional[int] = Field(
        default=None,
        description="参数状态（host_hw_rec 表 diff_state，最新一条记录；1-版本号变化, 2-内容更改, 3-异常）",
    )

    model_config = {"from_attributes": True}


class AdminApprHostListResponse(BaseModel):
    """管理后台待审批主机列表响应模式"""

    hosts: List[AdminApprHostInfo] = Field(default_factory=list, description="待审批主机列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")

    model_config = {"from_attributes": True}


class AdminApprHostDetailRequest(BaseModel):
    """管理后台待审批主机详情查询请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec 表主键 id）")

    model_config = {"from_attributes": True}


class AdminApprHostHwInfo(BaseModel):
    """管理后台待审批主机硬件信息响应模式"""

    created_time: Optional[datetime] = Field(default=None, description="创建时间（host_hw_rec 表 created_time）")
    hw_info: Optional[Dict[str, Any]] = Field(default=None, description="硬件信息（host_hw_rec 表 hw_info）")

    model_config = {"from_attributes": True}


class AdminApprHostDetailResponse(BaseModel):
    """管理后台待审批主机详情响应模式"""

    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（host_rec 表 mg_id）")
    mac: Optional[str] = Field(default=None, description="MAC地址（host_rec 表 mac_addr）")
    ip: Optional[str] = Field(default=None, description="IP地址（host_rec 表 host_ip）")
    username: Optional[str] = Field(default=None, description="主机账号（host_rec 表 host_acct）")
    ***REMOVED***word: Optional[str] = Field(default=None, description="主机密码（host_rec 表 host_pwd，已解密）")
    port: Optional[int] = Field(default=None, description="端口（host_rec 表 host_port）")
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "主机状态（host_rec 表 host_state；"
            "0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, "
            "5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）"
        ),
    )
    diff_state: Optional[int] = Field(
        default=None,
        description="参数状态（host_hw_rec 表 diff_state，最新一条记录；1-版本号变化, 2-内容更改, 3-异常）",
    )
    hw_list: List[AdminApprHostHwInfo] = Field(
        default_factory=list,
        description="硬件信息列表（host_hw_rec 表 sync_state=1 的记录，按 created_time 倒序）",
    )

    model_config = {"from_attributes": True}


class AdminApprHostApproveRequest(BaseModel):
    """管理后台待审批主机同意启用请求模式"""

    diff_type: Optional[int] = Field(
        default=None,
        ge=1,
        le=2,
        description="变更类型（1-版本号变化, 2-内容变化；为空时代表手动停用数据）",
    )
    host_ids: Optional[List[int]] = Field(
        default=None,
        description="主机ID列表（host_rec 表主键数组；当 diff_type=2 时必填）",
    )

    model_config = {"from_attributes": True}


class AdminApprHostApproveResponse(BaseModel):
    """管理后台待审批主机同意启用响应模式"""

    success_count: int = Field(description="成功处理的主机数量")
    failed_count: int = Field(description="失败的主机数量")
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="处理结果详情（包含成功和失败的记录）",
    )

    model_config = {"from_attributes": True}


class AdminMaintainEmailRequest(BaseModel):
    """管理后台维护通知邮箱设置请求模式"""

    email: str = Field(..., description="邮箱地址（多个邮箱以半角逗号分割）")

    model_config = {"from_attributes": True}


class AdminMaintainEmailResponse(BaseModel):
    """管理后台维护通知邮箱设置响应模式"""

    conf_key: str = Field(description="配置键（固定为 'email'）")
    conf_val: str = Field(description="配置值（格式化后的邮箱地址）")

    model_config = {"from_attributes": True}


class OtaConfigItem(BaseModel):
    """Agent 获取 OTA 配置项"""

    conf_name: Optional[str] = Field(default=None, description="配置名称")
    conf_ver: Optional[str] = Field(default=None, description="配置版本")
    conf_url: Optional[str] = Field(default=None, description="OTA 包下载 URL")
    conf_md5: Optional[str] = Field(default=None, description="OTA 包 MD5 校验值")

    model_config = {"from_attributes": True}


class AdminOtaConfigInfo(BaseModel):
    """管理后台 OTA 配置信息"""

    id: str = Field(description="配置ID（主键）")
    conf_ver: Optional[str] = Field(default=None, description="配置版本号")
    conf_name: Optional[str] = Field(default=None, description="配置名称")
    conf_url: Optional[str] = Field(default=None, description="OTA 包下载地址")
    conf_md5: Optional[str] = Field(default=None, description="OTA 包 MD5 校验值")

    model_config = {"from_attributes": True}


class AdminOtaListResponse(BaseModel):
    """管理后台 OTA 配置列表响应模式"""

    ota_configs: List[AdminOtaConfigInfo] = Field(description="OTA 配置列表")
    total: int = Field(description="配置总数")

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    """文件上传响应模式"""

    file_id: str = Field(description="文件唯一标识")
    filename: str = Field(description="原始文件名")
    saved_filename: str = Field(description="保存的文件名")
    file_url: str = Field(description="文件访问 URL")
    file_size: int = Field(description="文件大小（字节）")
    content_type: str = Field(description="文件 MIME 类型")
    upload_time: str = Field(description="上传时间")

    model_config = {"from_attributes": True}


class AdminOtaDeployRequest(BaseModel):
    """管理后台 OTA 下发请求模式"""

    id: int = Field(..., description="配置ID（主键）", gt=0)
    conf_ver: str = Field(..., description="配置版本号", min_length=1)
    conf_name: str = Field(..., description="配置名称", min_length=1)
    conf_url: str = Field(..., description="OTA 包下载地址（字符串，允许任意格式）")
    conf_md5: Optional[str] = Field(
        default=None,
        description="OTA 包 MD5 校验值（32位十六进制，可选）",
        min_length=32,
        max_length=32,
        pattern=r"^[a-fA-F0-9]{32}$",
    )

    model_config = {"from_attributes": True}


class AdminOtaDeployResponse(BaseModel):
    """管理后台 OTA 下发响应模式"""

    id: str = Field(description="配置ID（主键）")
    conf_ver: str = Field(description="配置版本号")
    conf_name: str = Field(description="配置名称")
    conf_url: str = Field(description="OTA 包下载地址")
    conf_md5: Optional[str] = Field(default=None, description="OTA 包 MD5 校验值（可选）")
    broadcast_count: int = Field(description="广播消息成功发送的主机数量")

    model_config = {"from_attributes": True}


class HardwareReportResponse(BaseModel):
    """硬件上报响应模式"""

    status: str = Field(description="状态 (first_report/hardware_changed/no_change)")
    hw_rec_id: Optional[int] = Field(default=None, description="硬件记录ID")
    diff_state: Optional[int] = Field(default=None, description="差异状态 (1-版本号变化, 2-内容更改)")
    diff_details: Optional[Dict[str, Any]] = Field(default=None, description="差异详情")
    message: str = Field(description="响应消息")

    model_config = {"from_attributes": True}


class AgentOtaUpdateStatusRequest(BaseModel):
    """Agent OTA 更新状态上报请求模式"""

    app_name: str = Field(..., description="应用名称（对应 host_upd 表的 app_name）", min_length=1)
    app_ver: str = Field(..., description="应用版本号（对应 host_upd 表的 app_ver）", min_length=1)
    biz_state: int = Field(
        ...,
        ge=1,
        le=3,
        description="业务状态（1=更新中，2=成功，3=失败）",
    )
    agent_ver: Optional[str] = Field(
        default=None,
        description="Agent 版本号（更新成功时必填，用于更新 host_rec 表的 agent_ver）",
        max_length=10,
    )

    model_config = {"from_attributes": True}


class AgentOtaUpdateStatusResponse(BaseModel):
    """Agent OTA 更新状态上报响应模式"""

    host_id: int = Field(description="主机ID")
    host_upd_id: int = Field(description="更新记录ID（host_upd 表主键）")
    app_state: int = Field(description="更新后的状态（0=预更新，1=更新中，2=成功，3=失败）")
    host_state: Optional[int] = Field(
        default=None,
        description="更新后的主机状态（如果更新成功，则为 0=空闲）",
    )
    agent_ver: Optional[str] = Field(default=None, description="更新后的 Agent 版本号")
    updated: bool = Field(description="是否成功更新")

    model_config = {"from_attributes": True}


class ResetHostForTestRequest(BaseModel):
    """测试重置主机请求模式"""

    host_id: str = Field(..., description="主机ID", min_length=1)

    model_config = {"from_attributes": True}


class ResetHostForTestResponse(BaseModel):
    """测试重置主机响应模式"""

    host_id: str = Field(description="主机ID")
    appr_state: int = Field(description="审批状态（1=启用）")
    host_state: int = Field(description="主机状态（0=空闲）")
    subm_time: Optional[str] = Field(default=None, description="申报时间（重置后为 null）")
    deleted_log_count: int = Field(description="删除的执行日志记录数")

    model_config = {"from_attributes": True}
