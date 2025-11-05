"""主机相关的 Pydantic 模式"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    """更新主机状态请求模式"""

    status: str = Field(description="主机状态 (online, offline, error)")


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
    connection_time: datetime = Field(..., description="连接时间")

    model_config = {"from_attributes": True}


class VNCConnectionResponse(BaseModel):
    """VNC 连接结果上报响应"""

    host_id: str = Field(description="主机ID")
    connection_status: str = Field(description="连接状态")
    connection_time: datetime = Field(description="连接时间")
    message: str = Field(description="处理消息")

    model_config = {"from_attributes": True}


class QueryAvailableHostsRequest(BaseModel):
    """查询可用主机列表请求模式 - 使用游标分页

    业务说明：
    - 首次请求不提供 last_id，从头开始
    - 后续请求提供上一页最后一条记录的 id（last_id）
    - 系统根据 last_id 计算内部偏移量
    - 避免多用户并发时的状态污染问题
    """

    tc_id: str = Field(description="测试用例ID")
    cycle_name: str = Field(description="测试周期名称")
    user_name: str = Field(description="用户名")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量（1-100）")
    last_id: Optional[int] = Field(
        default=None,
        description="上一页最后一条记录的 id。首次请求为 null，后续请求需要传入上一页最后一条记录的 host_rec_id",
    )

    model_config = {"from_attributes": True}


class HardwareHostData(BaseModel):
    """外部硬件接口返回的主机数据"""

    hardware_id: str = Field(description="硬件ID")
    ip: str = Field(description="IP地址")
    hostname: str = Field(description="主机名称")
    query: Optional[str] = Field(default=None, description="查询条件")

    model_config = {"from_attributes": True}


class AvailableHostInfo(BaseModel):
    """可用主机信息"""

    host_rec_id: int = Field(description="主机记录ID (host_rec.id)")
    hardware_id: str = Field(description="硬件ID")
    user_name: str = Field(description="用户名 (host_acct)")
    host_ip: str = Field(description="主机IP")
    appr_state: int = Field(description="审批状态")
    host_state: int = Field(description="主机状态")

    model_config = {"from_attributes": True}


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
    last_id: Optional[int] = Field(default=None, description="当前页最后一条记录的 id，用于请求下一页")

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

    host_id: int = Field(description="主机ID (host_rec.id)")
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
    host_state: Optional[int] = Field(default=None, description="主机状态（可选搜索条件，对应 host_rec.host_state）")
    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（可选搜索条件，对应 host_rec.mg_id）")
    use_by: Optional[str] = Field(default=None, description="使用人（可选搜索条件，对应 host_exec_log.user_name）")

    model_config = {"from_attributes": True}


class AdminHostInfo(BaseModel):
    """管理后台主机信息响应模式"""

    host_id: int = Field(description="主机ID（host_rec 表主键 id）")
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

    id: int = Field(description="已删除的主机ID")
    message: str = Field(default="主机删除成功", description="删除结果消息")

    model_config = {"from_attributes": True}


class AdminHostDisableRequest(BaseModel):
    """管理后台主机停用请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostDisableResponse(BaseModel):
    """管理后台主机停用响应模式"""

    id: int = Field(description="主机ID")
    appr_state: int = Field(default=0, description="更新后的审批状态（0=停用）")
    message: str = Field(default="主机已停用", description="操作结果消息")

    model_config = {"from_attributes": True}


class AdminHostForceOfflineRequest(BaseModel):
    """管理后台主机强制下线请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostForceOfflineResponse(BaseModel):
    """管理后台主机强制下线响应模式"""

    id: int = Field(description="主机ID")
    host_state: int = Field(default=4, description="更新后的主机状态（4=离线）")
    websocket_notified: bool = Field(description="是否成功发送WebSocket通知")
    message: str = Field(default="主机已强制下线", description="操作结果消息")

    model_config = {"from_attributes": True}


class AdminHostDetailRequest(BaseModel):
    """管理后台主机详情查询请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")

    model_config = {"from_attributes": True}


class AdminHostDetailResponse(BaseModel):
    """管理后台主机详情响应模式"""

    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（host_rec 表 mg_id）")
    mac: Optional[str] = Field(default=None, description="MAC地址（host_rec 表 mac_addr）")
    ip: Optional[str] = Field(default=None, description="IP地址（host_rec 表 host_ip）")
    username: Optional[str] = Field(default=None, description="主机账号（host_rec 表 host_acct）")
    ***REMOVED***word: Optional[str] = Field(default=None, description="主机密码（host_rec 表 host_pwd，已解密）")
    port: Optional[int] = Field(default=None, description="端口（host_rec 表 host_port）")
    hw_info: Optional[Dict[str, Any]] = Field(
        default=None, description="硬件信息（host_hw_rec 表 hw_info，sync_state=2的最新一条）"
    )
    appr_time: Optional[datetime] = Field(
        default=None, description="审批时间（host_hw_rec 表 appr_time，sync_state=2的最新一条）"
    )

    model_config = {"from_attributes": True}


class AdminHostUpdatePasswordRequest(BaseModel):
    """管理后台主机密码修改请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")
    ***REMOVED***word: str = Field(..., min_length=1, description="新密码（明文，将进行AES加密后存储）")

    model_config = {"from_attributes": True}


class AdminHostUpdatePasswordResponse(BaseModel):
    """管理后台主机密码修改响应模式"""

    id: int = Field(description="主机ID")
    message: str = Field(default="密码修改成功", description="操作结果消息")

    model_config = {"from_attributes": True}


class AdminHostExecLogListRequest(BaseModel):
    """管理后台主机执行日志列表查询请求模式"""

    host_id: int = Field(..., ge=1, description="主机ID（host_rec.id）")
    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小（1-100）")

    model_config = {"from_attributes": True}


class AdminHostExecLogInfo(BaseModel):
    """管理后台主机执行日志信息响应模式"""

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
        description="主机状态（可选搜索条件，对应 host_rec.host_state；0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）",
    )

    model_config = {"from_attributes": True}


class AdminApprHostInfo(BaseModel):
    """管理后台待审批主机信息响应模式"""

    host_id: int = Field(description="主机ID（host_rec 表主键 id）")
    mg_id: Optional[str] = Field(default=None, description="唯一引导ID（host_rec 表 mg_id）")
    mac_addr: Optional[str] = Field(default=None, description="MAC地址（host_rec 表 mac_addr）")
    host_state: Optional[int] = Field(
        default=None,
        description="主机状态（host_rec 表 host_state；0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）",
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
        description="主机状态（host_rec 表 host_state；0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）",
    )
    hw_list: List[AdminApprHostHwInfo] = Field(default_factory=list, description="硬件信息列表（host_hw_rec 表 sync_state=1 的记录，按 created_time 倒序）")

    model_config = {"from_attributes": True}


class AdminApprHostApproveRequest(BaseModel):
    """管理后台待审批主机同意启用请求模式"""

    diff_type: int = Field(..., ge=1, le=2, description="变更类型（1-版本号变化, 2-内容变化）")
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
