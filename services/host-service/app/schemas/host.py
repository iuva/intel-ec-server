"""Host-related Pydantic schemas"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


class HostBase(BaseModel):
    """Host base schema"""

    host_id: str = Field(description="Host unique identifier")
    hostname: str = Field(description="Host name")
    ip_address: str = Field(description="IP address")
    os_type: Optional[str] = Field(default=None, description="Operating system type")
    os_version: Optional[str] = Field(default=None, description="Operating system version")


class HostCreate(HostBase):
    """Create host request schema"""


class HostUpdate(BaseModel):
    """Update host request schema"""

    hostname: Optional[str] = Field(default=None, description="Host name")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    os_type: Optional[str] = Field(default=None, description="Operating system type")
    os_version: Optional[str] = Field(default=None, description="Operating system version")
    status: Optional[str] = Field(default=None, description="Host status")


class HostStatusUpdate(BaseModel):
    """Update host status request schema

    Supports two update methods:
    1. Use status string field (recommended): "online", "offline", "error"
    2. Use host_state and appr_state integer fields (advanced usage)
    """

    status: Optional[str] = Field(default=None, description="Host status (online, offline, error)")
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "Host state code (0-free, 1-locked, 2-occupied, 3-executing, "
            "4-offline, 5-pending activation, 6-hardware changed, 7-manually disabled, 8-updating)"
        ),
    )
    appr_state: Optional[int] = Field(
        default=None, description="Approval state (0-disabled, 1-enabled/new, 2-has changes)"
    )


class HostResponse(HostBase):
    """Host response schema"""

    id: int = Field(description="Primary key ID")
    status: str = Field(description="Host status")
    last_heartbeat: Optional[datetime] = Field(default=None, description="Last heartbeat time")
    created_time: datetime = Field(description="Creation time")
    updated_time: datetime = Field(description="Update time")
    del_flag: bool = Field(description="Whether deleted")

    model_config = {"from_attributes": True}


class HostListResponse(BaseModel):
    """Host list response schema"""

    hosts: List[HostResponse] = Field(description="Host list")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Page size")


class VNCConnectionReport(BaseModel):
    """VNC connection result report - Browser plugin reports VNC connection result"""

    user_id: str = Field(..., description="User ID")
    tc_id: str = Field(..., description="Test execution ID")
    cycle_name: str = Field(..., description="Cycle name")
    user_name: str = Field(..., description="User name")
    host_id: str = Field(..., description="Host ID")
    connection_status: str = Field(..., description="Connection status (success/failed)", pattern=r"^(success|failed)$")
    connection_time: datetime = Field(
        ..., description="Connection time (supports formats: yyyy/MM/dd HH:mm:ss or ISO 8601)"
    )

    model_config = {"from_attributes": True}

    @field_validator("connection_time", mode="before")
    @classmethod
    def parse_connection_time(cls, value: Any) -> datetime:
        """Parse connection time, supports two formats:
        1. yyyy/MM/dd HH:mm:ss (e.g., 2025/01/30 10:00:00)
        2. ISO 8601 format (e.g., 2025-01-30T10:00:00Z)

        Args:
            value: Input value (may be string or datetime object)

        Returns:
            datetime object

        Raises:
            ValueError: Raised when format is incorrect
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Try to parse yyyy/MM/dd HH:mm:ss format
            try:
                # Parse as naive datetime, then add UTC timezone
                dt = datetime.strptime(value, "%Y/%m/%d %H:%M:%S")
                # Assume input time is UTC time, add UTC timezone information
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                # If fails, try ISO 8601 format (Pydantic default support)
                try:
                    # Use datetime.fromisoformat to parse ISO 8601 format
                    # Handle timezone-aware format (e.g., 2025-01-30T10:00:00Z)
                    if value.endswith("Z"):
                        value = value[:-1] + "+00:00"
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    # Ensure timezone information, if not add UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError as e:
                    raise ValueError(
                        (
                            f"Connection time format incorrect, supported formats: "
                            f"yyyy/MM/dd HH:mm:ss (e.g., 2025/01/30 10:00:00) "
                            f"or ISO 8601 (e.g., 2025-01-30T10:00:00Z), current value: {value}"
                        )
                    ) from e

        raise ValueError(f"Connection time must be string or datetime object, current type: {type(value).__name__}")


class VNCConnectionResponse(BaseModel):
    """VNC connection result report response"""

    host_id: str = Field(description="Host ID")
    connection_status: str = Field(description="Connection status")
    connection_time: datetime = Field(description="Connection time")

    model_config = {"from_attributes": True}

    @field_serializer("connection_time")
    def serialize_connection_time(self, value: datetime) -> str:
        """Format connection time as yyyy/MM/dd HH:mm:ss format"""
        if value is None:
            return ""
        # Convert to local time (if needed, can specify timezone)
        # Here use UTC time, format as yyyy/MM/dd HH:mm:ss
        return value.strftime("%Y/%m/%d %H:%M:%S")


class AgentVNCConnectionReportRequest(BaseModel):
    """Agent VNC connection state report request

    vnc_state description:
    - 1: Connection succeeded
    - 2: Connection disconnected
    """

    vnc_state: int = Field(
        ...,
        ge=1,
        le=2,
        description="VNC connection state (1=connection succeeded, 2=connection disconnected)",
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
    """Agent VNC connection state report response"""

    host_id: int = Field(..., description="Host ID")
    host_state: int = Field(..., description="Updated host state (0=free, 1=locked, 2=occupied)")
    vnc_state: int = Field(
        ..., description="Reported VNC connection state (1=connection succeeded, 2=connection disconnected)"
    )
    updated: bool = Field(..., description="Whether update succeeded")

    model_config = {
        "from_attributes": True,
    }


class QueryAvailableHostsRequest(BaseModel):
    """Query available host list request schema - using cursor pagination

    Business description:
    - First request does not provide last_id, start from beginning
    - Subsequent requests provide id of last record from previous page (last_id)
    - System calculates internal offset based on last_id
    - Avoid state pollution issues during multi-user concurrency
    - If email is provided, will directly use this email for external API authentication without querying database
    """

    tc_id: str = Field(description="Test case ID")
    cycle_name: str = Field(description="Test cycle name")
    user_name: str = Field(description="Username")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (1-100)")
    last_id: Optional[str] = Field(
        default=None,
        description=(
            "ID of last record from previous page. null for first request, "
            "subsequent requests need to ***REMOVED*** host_rec_id of last record from previous page"
        ),
    )
    email: Optional[str] = Field(
        default=None,
        description=(
            "User email (optional). If provided, will directly use this email "
            "for external API authentication without querying database"
        ),
    )

    model_config = {"from_attributes": True}


class DMRBoardMetaData(BaseModel):
    """DMR board metadata"""

    board_name: Optional[str] = Field(default=None, description="Board name")
    host_name: Optional[str] = Field(default=None, description="Host name")
    host_ip: Optional[str] = Field(default=None, description="Host IP")

    model_config = {"from_attributes": True}


class DMRBoard(BaseModel):
    """DMR board configuration"""

    board_meta_data: Optional[DMRBoardMetaData] = Field(default=None, description="Board metadata")

    model_config = {"from_attributes": True}


class DMRPlatformMetaData(BaseModel):
    """DMR platform metadata"""

    platform: Optional[str] = Field(default=None, description="Platform type")
    label_plt_cfg: Optional[str] = Field(default=None, description="Platform configuration label")

    model_config = {"from_attributes": True}


class DMRMainboard(BaseModel):
    """DMR mainboard configuration"""

    plt_meta_data: Optional[DMRPlatformMetaData] = Field(default=None, description="Platform metadata")
    board: Optional[DMRBoard] = Field(default=None, description="Board configuration")

    model_config = {"from_attributes": True}


class DMRConfig(BaseModel):
    """DMR configuration"""

    revision: Optional[int] = Field(default=None, description="Revision number")
    mainboard: Optional[DMRMainboard] = Field(default=None, description="Mainboard configuration")

    model_config = {"from_attributes": True}


class HardwareHostData(BaseModel):
    """Host data returned by external hardware API"""

    hardware_id: str = Field(description="Hardware ID")
    name: Optional[str] = Field(default=None, description="Host configuration name")
    dmr_config: Optional[DMRConfig] = Field(default=None, description="DMR configuration")
    updated_time: Optional[str] = Field(default=None, description="Update time (ISO format string)")
    updated_by: Optional[str] = Field(default=None, description="Updated by")
    tags: Optional[List[str]] = Field(default=None, description="Tag list")
    # Compatible with old fields
    ip: Optional[str] = Field(
        default=None,
        description="IP address (compatible field, prefer dmr_config.mainboard.board.board_meta_data.host_ip)",
    )
    hostname: Optional[str] = Field(
        default=None,
        description="Host name (compatible field, prefer dmr_config.mainboard.board.board_meta_data.host_name)",
    )
    query: Optional[str] = Field(default=None, description="Query condition")

    model_config = {"from_attributes": True}


class AvailableHostInfo(BaseModel):
    """Available host information"""

    id: str = Field(description="Host record ID (host_rec.id)", alias="host_rec_id")
    username: str = Field(description="Host number (host_no)", alias="user_name")
    host_ip: str = Field(description="Host IP address (host_ip)")

    model_config = {"from_attributes": True, "populate_by_name": True}


class AvailableHostsListResponse(BaseModel):
    """Query available host list response schema - cursor pagination response

    Field descriptions:
    - hosts: Current page host list
    - total: Total available hosts discovered in this query (not global total)
    - page_size: Page size
    - has_next: Whether there is next page
    - last_id: ID of last record in current page, used for next page request
    """

    hosts: List[AvailableHostInfo] = Field(description="Available host list")
    total: int = Field(description="Total available hosts discovered in this query")
    page_size: int = Field(description="Page size")
    has_next: bool = Field(description="Whether there is next page")
    last_id: Optional[str] = Field(
        default=None, description="ID of last record in current page, used for next page request"
    )

    model_config = {"from_attributes": True}


class GetVNCConnectionRequest(BaseModel):
    """Get VNC connection information request schema"""

    id: str = Field(description="Host ID (host_rec.id)")

    model_config = {"from_attributes": True}


class VNCConnectionInfo(BaseModel):
    """VNC connection information response schema"""

    ip: str = Field(description="VNC server IP address")
    port: str = Field(description="VNC service port")
    username: str = Field(description="Connection username")
    ***REMOVED***word: str = Field(description="Connection ***REMOVED***word")

    model_config = {"from_attributes": True}


class GetRetryVNCListRequest(BaseModel):
    """Get retry VNC list request schema"""

    user_id: str = Field(description="User ID")

    model_config = {"from_attributes": True}


class RetryVNCHostInfo(BaseModel):
    """Retry VNC host information"""

    host_id: str = Field(description="Host ID (host_rec.id)")
    host_ip: str = Field(description="Host IP")
    user_name: str = Field(description="Host number (host_no)")

    model_config = {"from_attributes": True}


class RetryVNCListResponse(BaseModel):
    """Retry VNC list response schema"""

    hosts: List[RetryVNCHostInfo] = Field(description="Retry VNC host list")
    total: int = Field(description="Total host count")

    model_config = {"from_attributes": True}


class ReleaseHostsRequest(BaseModel):
    """Release hosts request schema"""

    user_id: str = Field(description="User ID")
    host_list: List[str] = Field(description="Host ID list")

    model_config = {"from_attributes": True}


class ReleaseHostsResponse(BaseModel):
    """Release hosts response schema"""

    updated_count: int = Field(description="Number of updated records (logical delete)")
    user_id: str = Field(description="User ID")
    host_list: List[str] = Field(description="Host ID list")

    model_config = {"from_attributes": True}


# ==================== Admin Backend Host Management Schema ====================


class AdminHostListRequest(BaseModel):
    """Admin backend host list query request schema"""

    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    mac: Optional[str] = Field(
        default=None, description="MAC address (optional search condition, corresponds to host_rec.mac_addr)"
    )
    username: Optional[str] = Field(
        default=None, description="Host account (optional search condition, corresponds to host_rec.host_acct)"
    )
    host_state: Optional[int] = Field(
        default=None,
        ge=0,
        le=4,
        description=(
            "Host state (optional search condition, corresponds to host_rec.host_state; "
            "supported range: 0-free, 1-locked, 2-occupied, 3-case executing, 4-offline)"
        ),
    )
    mg_id: Optional[str] = Field(
        default=None, description="Unique boot ID (optional search condition, corresponds to host_rec.mg_id)"
    )
    use_by: Optional[str] = Field(
        default=None, description="Used by (optional search condition, corresponds to host_exec_log.user_name)"
    )

    model_config = {"from_attributes": True}


class AdminHostInfo(BaseModel):
    """Admin backend host information response schema"""

    host_id: str = Field(description="Host ID (host_rec table primary key id)")
    username: Optional[str] = Field(default=None, description="Host account (host_rec table host_acct)")
    mg_id: Optional[str] = Field(default=None, description="Unique boot ID (host_rec table mg_id)")
    mac: Optional[str] = Field(default=None, description="MAC address (host_rec table mac_addr)")
    use_by: Optional[str] = Field(default=None, description="Used by (host_exec_log table user_name, latest record)")
    host_state: Optional[int] = Field(default=None, description="Host state (host_rec table host_state)")
    appr_state: Optional[int] = Field(default=None, description="Approval state (host_rec table appr_state)")

    model_config = {"from_attributes": True}


class AdminHostListResponse(BaseModel):
    """Admin backend host list response schema"""

    hosts: List[AdminHostInfo] = Field(description="Host list")
    total: int = Field(description="Total record count")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total page count")
    has_next: bool = Field(description="Whether there is next page")
    has_prev: bool = Field(description="Whether there is previous page")

    model_config = {"from_attributes": True}


class AdminHostDeleteRequest(BaseModel):
    """Admin backend host delete request schema"""

    id: int = Field(..., ge=1, description="Host ID (host_rec.id)")

    model_config = {"from_attributes": True}


class AdminHostDeleteResponse(BaseModel):
    """Admin backend host delete response schema"""

    id: str = Field(description="Deleted host ID")

    model_config = {"from_attributes": True}


class AdminHostDisableRequest(BaseModel):
    """Admin backend host disable request schema"""

    host_id: int = Field(..., ge=1, description="Host ID (host_rec.id)")

    model_config = {"from_attributes": True}


class AdminHostDisableResponse(BaseModel):
    """Admin backend host disable response schema"""

    id: str = Field(description="Host ID")
    appr_state: int = Field(default=0, description="Updated approval state (0=disabled)")
    host_state: int = Field(default=7, description="Updated host state (7=manually disabled)")

    model_config = {"from_attributes": True}


class AdminHostForceOfflineRequest(BaseModel):
    """Admin backend host force offline request schema"""

    host_id: int = Field(..., ge=1, description="Host ID (host_rec.id)")

    model_config = {"from_attributes": True}


class AdminHostForceOfflineResponse(BaseModel):
    """Admin backend host force offline response schema"""

    id: str = Field(description="Host ID")
    host_state: int = Field(default=4, description="Updated host state (4=offline)")

    model_config = {"from_attributes": True}


class AdminHostDetailRequest(BaseModel):
    """Admin backend host detail query request schema"""

    host_id: int = Field(..., ge=1, description="Host ID (host_rec.id)")

    model_config = {"from_attributes": True}


class AdminHostHwDetailInfo(BaseModel):
    """Admin backend host hardware detail information response schema"""

    hw_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Hardware information (host_hw_rec table hw_info)"
    )
    appr_time: Optional[datetime] = Field(default=None, description="Approval time (host_hw_rec table appr_time)")

    model_config = {"from_attributes": True}


class AdminHostDetailResponse(BaseModel):
    """Admin backend host detail response schema"""

    mg_id: Optional[str] = Field(default=None, description="Unique boot ID (host_rec table mg_id)")
    mac: Optional[str] = Field(default=None, description="MAC address (host_rec table mac_addr)")
    ip: Optional[str] = Field(default=None, description="IP address (host_rec table host_ip)")
    username: Optional[str] = Field(default=None, description="Host account (host_rec table host_acct)")
    ***REMOVED***word: Optional[str] = Field(default=None, description="Host ***REMOVED***word (host_rec table host_pwd, decrypted)")
    port: Optional[int] = Field(default=None, description="Port (host_rec table host_port)")
    hw_list: List[AdminHostHwDetailInfo] = Field(
        default_factory=list,
        description=(
            "Hardware information list (host_hw_rec table records with sync_state=2, "
            "sorted by updated_time descending)"
        ),
    )

    model_config = {"from_attributes": True}


class AdminHostUpdatePasswordRequest(BaseModel):
    """Admin backend host ***REMOVED***word update request schema"""

    host_id: int = Field(..., ge=1, description="Host ID (host_rec.id)")
    ***REMOVED***word: str = Field(
        ..., min_length=1, description="New ***REMOVED***word (plaintext, will be AES encrypted before storage)"
    )

    model_config = {"from_attributes": True}


class AdminHostUpdatePasswordResponse(BaseModel):
    """Admin backend host ***REMOVED***word update response schema"""

    id: str = Field(description="Host ID")

    model_config = {"from_attributes": True}


class AdminHostExecLogListRequest(BaseModel):
    """Admin backend host execution log list query request schema"""

    host_id: int = Field(..., ge=1, description="Host ID (host_rec.id)")
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")

    model_config = {"from_attributes": True}


class AdminHostExecLogInfo(BaseModel):
    """Admin backend host execution log information response schema"""

    log_id: Optional[str] = Field(default=None, description="Execution log ID (host_exec_log table id)")
    exec_date: Optional[str] = Field(default=None, description="Execution date (format: %Y-%m-%d)")
    exec_time: Optional[str] = Field(default=None, description="Execution duration (format: %H:%M:%S)")
    tc_id: Optional[str] = Field(default=None, description="Test execution ID (host_exec_log table tc_id)")
    use_by: Optional[str] = Field(default=None, description="Used by (host_exec_log table user_name)")
    case_state: Optional[int] = Field(
        default=None, description="Execution state (0-free, 1-started, 2-success, 3-failed)"
    )
    result_msg: Optional[str] = Field(default=None, description="Execution result (host_exec_log table result_msg)")
    log_url: Optional[str] = Field(default=None, description="Execution log URL (host_exec_log table log_url)")

    model_config = {"from_attributes": True}


class AdminHostExecLogListResponse(BaseModel):
    """Admin backend host execution log list response schema"""

    logs: List[AdminHostExecLogInfo] = Field(default_factory=list, description="Execution log list")
    total: int = Field(description="Total record count")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total page count")
    has_next: bool = Field(description="Whether there is next page")
    has_prev: bool = Field(description="Whether there is previous page")

    model_config = {"from_attributes": True}


class AdminApprHostListRequest(BaseModel):
    """Admin backend pending approval host list query request schema"""

    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    mac: Optional[str] = Field(
        default=None, description="MAC address (optional search condition, corresponds to host_rec.mac_addr)"
    )
    mg_id: Optional[str] = Field(
        default=None, description="Unique boot ID (optional search condition, corresponds to host_rec.mg_id)"
    )
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "Host state (optional search condition, corresponds to host_rec.host_state; "
            "0-free, 1-locked, 2-occupied, 3-case executing, 4-offline, "
            "5-pending activation, 6-hardware changed, 7-manually disabled, 8-updating)"
        ),
    )

    model_config = {"from_attributes": True}


class AdminApprHostInfo(BaseModel):
    """Admin backend pending approval host information response schema"""

    host_id: str = Field(description="Host ID (host_rec table primary key id)")
    mg_id: Optional[str] = Field(default=None, description="Unique boot ID (host_rec table mg_id)")
    mac_addr: Optional[str] = Field(default=None, description="MAC address (host_rec table mac_addr)")
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "Host state (host_rec table host_state; "
            "0-free, 1-locked, 2-occupied, 3-case executing, 4-offline, "
            "5-pending activation, 6-hardware changed, 7-manually disabled, 8-updating)"
        ),
    )
    subm_time: Optional[datetime] = Field(default=None, description="Submission time (host_rec table subm_time)")
    diff_state: Optional[int] = Field(
        default=None,
        description=(
            "Parameter state (host_hw_rec table diff_state, latest record; "
            "1-version changed, 2-content changed, 3-abnormal)"
        ),
    )

    model_config = {"from_attributes": True}


class AdminApprHostListResponse(BaseModel):
    """Admin backend pending approval host list response schema"""

    hosts: List[AdminApprHostInfo] = Field(default_factory=list, description="Pending approval host list")
    total: int = Field(description="Total record count")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total page count")
    has_next: bool = Field(description="Whether there is next page")
    has_prev: bool = Field(description="Whether there is previous page")

    model_config = {"from_attributes": True}


class AdminApprHostDetailRequest(BaseModel):
    """Admin backend pending approval host detail query request schema"""

    host_id: int = Field(..., ge=1, description="Host ID (host_rec table primary key id)")

    model_config = {"from_attributes": True}


class AdminApprHostHwInfo(BaseModel):
    """Admin backend pending approval host hardware information response schema"""

    created_time: Optional[datetime] = Field(default=None, description="Creation time (host_hw_rec table created_time)")
    hw_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Hardware information (host_hw_rec table hw_info)"
    )

    model_config = {"from_attributes": True}


class AdminApprHostDetailResponse(BaseModel):
    """Admin backend pending approval host detail response schema"""

    mg_id: Optional[str] = Field(default=None, description="Unique boot ID (host_rec table mg_id)")
    mac: Optional[str] = Field(default=None, description="MAC address (host_rec table mac_addr)")
    ip: Optional[str] = Field(default=None, description="IP address (host_rec table host_ip)")
    username: Optional[str] = Field(default=None, description="Host account (host_rec table host_acct)")
    ***REMOVED***word: Optional[str] = Field(default=None, description="Host ***REMOVED***word (host_rec table host_pwd, decrypted)")
    port: Optional[int] = Field(default=None, description="Port (host_rec table host_port)")
    host_state: Optional[int] = Field(
        default=None,
        description=(
            "Host state (host_rec table host_state; "
            "0-free, 1-locked, 2-occupied, 3-case executing, 4-offline, "
            "5-pending activation, 6-hardware changed, 7-manually disabled, 8-updating)"
        ),
    )
    diff_state: Optional[int] = Field(
        default=None,
        description=(
            "Parameter state (host_hw_rec table diff_state, latest record; "
            "1-version changed, 2-content changed, 3-abnormal)"
        ),
    )
    hw_list: List[AdminApprHostHwInfo] = Field(
        default_factory=list,
        description=(
            "Hardware information list (host_hw_rec table records with sync_state=1, "
            "sorted by created_time descending)"
        ),
    )

    model_config = {"from_attributes": True}


class AdminApprHostApproveRequest(BaseModel):
    """Admin backend pending approval host approve enable request schema"""

    diff_type: Optional[int] = Field(
        default=None,
        ge=1,
        le=2,
        description="Change type (1-version changed, 2-content changed; empty represents manually disabled data)",
    )
    host_ids: Optional[List[int]] = Field(
        default=None,
        description="Host ID list (host_rec table primary key array; required when diff_type=2)",
    )

    model_config = {"from_attributes": True}


class AdminApprHostApproveResponse(BaseModel):
    """Admin backend pending approval host approve enable response schema"""

    success_count: int = Field(description="Number of successfully processed hosts")
    failed_count: int = Field(description="Number of failed hosts")
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Processing result details (includes both successful and failed records)",
    )

    model_config = {"from_attributes": True}


class AdminMaintainEmailRequest(BaseModel):
    """Admin backend maintenance notification email setting request schema"""

    email: str = Field(..., description="Email address (multiple emails separated by comma)")

    model_config = {"from_attributes": True}


class AdminMaintainEmailResponse(BaseModel):
    """Admin backend maintenance notification email setting response schema"""

    conf_key: str = Field(description="Configuration key (fixed as 'email')")
    conf_val: str = Field(description="Configuration value (formatted email address)")

    model_config = {"from_attributes": True}


class OtaConfigItem(BaseModel):
    """Agent OTA configuration item"""

    conf_name: Optional[str] = Field(default=None, description="Configuration name")
    conf_ver: Optional[str] = Field(default=None, description="Configuration version")
    conf_url: Optional[str] = Field(default=None, description="OTA package download URL")
    conf_md5: Optional[str] = Field(default=None, description="OTA package MD5 checksum")

    model_config = {"from_attributes": True}


class AgentInitConfigItem(BaseModel):
    """Agent initialization configuration item"""

    conf_key: str = Field(..., description="Configuration key")
    conf_val: Optional[str] = Field(default=None, description="Configuration value")
    conf_ver: Optional[str] = Field(default=None, description="Configuration version")
    conf_name: Optional[str] = Field(default=None, description="Configuration name")
    conf_json: Optional[Dict[str, Any]] = Field(default=None, description="Configuration JSON")

    model_config = {"from_attributes": True}


class AgentInitConfigListResponse(BaseModel):
    """Agent initialization configuration list response"""

    configs: List[AgentInitConfigItem] = Field(..., description="Initialization configuration list")
    total: int = Field(..., description="Total number of configurations")

    model_config = {"from_attributes": True}


class AdminOtaConfigInfo(BaseModel):
    """Admin backend OTA configuration information"""

    id: str = Field(description="Configuration ID (primary key)")
    conf_ver: Optional[str] = Field(default=None, description="Configuration version number")
    conf_name: Optional[str] = Field(default=None, description="Configuration name")
    conf_url: Optional[str] = Field(default=None, description="OTA package download address")
    conf_md5: Optional[str] = Field(default=None, description="OTA package MD5 checksum")

    model_config = {"from_attributes": True}


class AdminOtaListResponse(BaseModel):
    """Admin backend OTA configuration list response schema"""

    ota_configs: List[AdminOtaConfigInfo] = Field(description="OTA configuration list")
    total: int = Field(description="Total configuration count")

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    """File upload response schema"""

    file_id: str = Field(description="File unique identifier")
    filename: str = Field(description="Original filename")
    saved_filename: str = Field(description="Saved filename")
    file_url: str = Field(description="File access URL")
    file_size: int = Field(description="File size (bytes)")
    content_type: str = Field(description="File MIME type")
    upload_time: str = Field(description="Upload time")

    model_config = {"from_attributes": True}


class AdminOtaDeployRequest(BaseModel):
    """Admin backend OTA deployment request schema"""

    id: int = Field(..., description="Configuration ID (primary key)", gt=0)
    conf_ver: str = Field(..., description="Configuration version number", min_length=1)
    conf_name: str = Field(..., description="Configuration name", min_length=1)
    conf_url: str = Field(..., description="OTA package download address (string, allows any format)")
    conf_md5: Optional[str] = Field(
        default=None,
        description="OTA package MD5 checksum (32-digit hexadecimal, optional)",
        min_length=32,
        max_length=32,
        pattern=r"^[a-fA-F0-9]{32}$",
    )

    model_config = {"from_attributes": True}


class AdminOtaDeployResponse(BaseModel):
    """Admin backend OTA deployment response schema"""

    id: str = Field(description="Configuration ID (primary key)")
    conf_ver: str = Field(description="Configuration version number")
    conf_name: str = Field(description="Configuration name")
    conf_url: str = Field(description="OTA package download address")
    conf_md5: Optional[str] = Field(default=None, description="OTA package MD5 checksum (optional)")
    broadcast_count: int = Field(description="Number of hosts that successfully received broadcast message")

    model_config = {"from_attributes": True}


class HardwareReportResponse(BaseModel):
    """Hardware report response schema"""

    status: str = Field(description="Status (first_report/hardware_changed/no_change)")
    hw_rec_id: Optional[int] = Field(default=None, description="Hardware record ID")
    diff_state: Optional[int] = Field(
        default=None, description="Difference state (1-version changed, 2-content changed)"
    )
    diff_details: Optional[Dict[str, Any]] = Field(default=None, description="Difference details")
    message: str = Field(description="Response message")

    model_config = {"from_attributes": True}


class AgentOtaUpdateStatusRequest(BaseModel):
    """Agent OTA update status report request schema"""

    app_name: str = Field(..., description="Application name (corresponds to host_upd table app_name)", min_length=1)
    app_ver: str = Field(
        ..., description="Application version number (corresponds to host_upd table app_ver)", min_length=1
    )
    biz_state: int = Field(
        ...,
        ge=1,
        le=3,
        description="Business state (1=updating, 2=success, 3=failed)",
    )
    agent_ver: Optional[str] = Field(
        default=None,
        description="Agent version number (required when update succeeds, used to update host_rec table agent_ver)",
        max_length=10,
    )

    model_config = {"from_attributes": True}


class AgentOtaUpdateStatusResponse(BaseModel):
    """Agent OTA update status report response schema"""

    host_id: int = Field(description="Host ID")
    host_upd_id: int = Field(description="Update record ID (host_upd table primary key)")
    app_state: int = Field(description="Updated state (0=pre-update, 1=updating, 2=success, 3=failed)")
    host_state: Optional[int] = Field(
        default=None,
        description="Updated host state (if update succeeds, then 0=free)",
    )
    agent_ver: Optional[str] = Field(default=None, description="Updated Agent version number")
    updated: bool = Field(description="Whether update succeeded")

    model_config = {"from_attributes": True}


class ResetHostForTestRequest(BaseModel):
    """Test reset host request schema"""

    host_id: str = Field(..., description="Host ID", min_length=1)

    model_config = {"from_attributes": True}


class ResetHostForTestResponse(BaseModel):
    """Test reset host response schema"""

    host_id: str = Field(description="Host ID")
    appr_state: int = Field(description="Approval state (1=enabled)")
    host_state: int = Field(description="Host state (0=free)")
    subm_time: Optional[str] = Field(default=None, description="Submission time (null after reset)")
    deleted_log_count: int = Field(description="Number of deleted execution log records")

    model_config = {"from_attributes": True}
