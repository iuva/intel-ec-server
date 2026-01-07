"""管理后台待审批主机管理 - 工具函数模块

提供审批相关的工具函数，包括硬件接口调用、表格构建等。

从 admin_appr_host_service.py 拆分出来，提高代码可维护性。
"""

import os
import sys
from typing import Any, Dict, List, Optional

# 使用 try-except 方式处理路径导入
try:
    from app.models.host_rec import HostRec
    from app.services.external_api_client import call_external_api
    from shared.common.cache import redis_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.host_rec import HostRec
    from app.services.external_api_client import call_external_api
    from shared.common.cache import redis_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def build_host_table(hardware_ids: List[str], host_ips: List[str]) -> str:
    """构建主机信息表格（HTML格式）

    Args:
        hardware_ids: Hardware ID 列表
        host_ips: Host IP 列表

    Returns:
        HTML 表格字符串
    """
    if not hardware_ids and not host_ips:
        return "无变更的主机信息"

    # 确保两个列表长度一致（用空字符串填充）
    max_len = max(len(hardware_ids), len(host_ips))
    hardware_ids_padded = hardware_ids + [""] * (max_len - len(hardware_ids))
    host_ips_padded = host_ips + [""] * (max_len - len(host_ips))

    # 构建 HTML 表格
    table_rows = []
    cell_style = "padding: 12px; border: 1px solid #ddd; text-align: left;"
    header_style = (
        "padding: 12px; border: 1px solid #ddd; background-color: #4CAF50; "
        "color: white; text-align: left; font-weight: 600;"
    )
    row_style = "background-color: white;"
    alternate_row_style = "background-color: #f9f9f9;"

    for i in range(max_len):
        hw_id = hardware_ids_padded[i] if i < len(hardware_ids) else ""
        host_ip = host_ips_padded[i] if i < len(host_ips) else ""
        row_bg = alternate_row_style if i % 2 == 1 else row_style
        row_html = (
            f"<tr style='{row_bg}'>"
            f"<td style='{cell_style}'>{hw_id or '-'}</td>"
            f"<td style='{cell_style}'>{host_ip or '-'}</td>"
            f"</tr>"
        )
        table_rows.append(row_html)

    table_style = (
        "border-collapse: collapse; width: 100%; margin: 15px 0; "
        "border-radius: 5px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
    )
    table_html = f"""
<table style='{table_style}'>
    <thead>
        <tr>
            <th style='{header_style}'>Hardware ID</th>
            <th style='{header_style}'>Host IP</th>
        </tr>
    </thead>
    <tbody>
        {"".join(table_rows)}
    </tbody>
</table>
"""

    return table_html


def get_hardware_name_from_hw_info(hw_info: Dict[str, Any], host_rec: HostRec) -> str:
    """从硬件信息中提取配置名称

    Args:
        hw_info: 硬件信息字典（包含 dmr_config）
        host_rec: 主机记录对象

    Returns:
        配置名称字符串
    """
    # 优先从 dmr_config 中提取 host_name
    try:
        dmr_config = hw_info.get("dmr_config", {})
        mainboard = dmr_config.get("mainboard", {})
        board = mainboard.get("board", {})
        board_meta_data = board.get("board_meta_data", {})
        host_name = board_meta_data.get("host_name")
        if host_name:
            return host_name
    except Exception:
        ***REMOVED***

    # 如果无法从 dmr_config 提取，使用 host_rec 的字段
    if host_rec.host_ip:
        return f"Host-{host_rec.host_ip}"
    elif host_rec.mg_id:
        return f"Host-{host_rec.mg_id}"
    else:
        return f"Host-{host_rec.id}"


def build_hardware_head() -> Dict[str, str]:
    """构建硬件接口 Head 参数（Mock 数据）

    Returns:
        Head 参数字典
    """
    return {
        "ConfigName": "DMR-sample-1",
        "Component": "bios.playform",
        "Owner": "zeyichen",
        "Project": "bios.oakstream_diamondrapids",
        "Environment": "silicon",
        "Milestone": "Alpha",
        "SubComponent": "",
        "Type": "hardware",
        "Tag": "",
    }


async def call_hardware_api(
    hardware_id: Optional[str],
    hw_info: Dict[str, Any],
    request: Optional[Any] = None,
    user_id: Optional[int] = None,
    locale: str = "zh_CN",
    host_id: Optional[int] = None,
) -> Dict[str, Optional[str]]:
    """调用外部硬件接口（新增或修改）

    使用统一的外部接口调用客户端，自动处理认证。
    新增硬件时使用 Redis 分布式锁防止并发创建。

    Args:
        hardware_id: 硬件ID（如果为 None 则调用新增接口，否则调用修改接口）
        hw_info: 硬件信息（对应 host_hw_rec 表的 hw_info 字段）
        request: FastAPI Request 对象（用于从请求头获取 user_id）
        user_id: 当前登录管理后台用户的ID（可选，如果提供则优先使用）
        locale: 语言偏好
        host_id: 主机ID（用于生成分布式锁的键，仅在新增硬件时需要）

    Returns:
        Dict[str, Optional[str]]: 包含 hardware_id 和 host_name 的字典
            - hardware_id: 硬件ID（必填）
            - host_name: 主机名称（可选，从响应体中提取）

    Raises:
        BusinessError: 接口调用失败时
    """
    # 检查是否使用 Mock 数据
    use_mock = os.getenv("USE_HARDWARE_MOCK", "false").lower() in ("true", "1", "yes")

    if use_mock:
        logger.info(
            "使用 Mock 硬件接口数据",
            extra={
                "hardware_id": hardware_id,
                "is_new": hardware_id is None,
            },
        )
        # 返回模拟的 hardware_id 和 host_name
        if hardware_id:
            return {"hardware_id": hardware_id, "host_name": None}
        else:
            # 生成模拟的 hardware_id
            import uuid
            mock_id = f"mock-hardware-{uuid.uuid4().hex[:8]}"
            return {"hardware_id": mock_id, "host_name": None}

        # 使用统一的外部接口调用客户端
    try:
        # 构建 Head 参数（Mock 数据）
        head_data = build_hardware_head()

        # ✅ 判断 hardware_id 是否有效：None 或空字符串都视为无效，调用新增接口
        is_valid_hardware_id = hardware_id is not None and bool(hardware_id and hardware_id.strip())

        if not is_valid_hardware_id:
            # ✅ 新增硬件：使用 Redis 分布式锁防止并发创建
            lock_key = None
            lock_value = None

            if host_id is not None:
                # 生成锁的键：基于 host_id，确保同一主机不会并发创建多个 hardware
                lock_key = f"hardware_create_lock:{host_id}"
                import uuid

                lock_value = str(uuid.uuid4())

                # 尝试获取锁（超时时间 30 秒）
                lock_acquired = await redis_manager.acquire_lock(lock_key, timeout=30, lock_value=lock_value)

                if not lock_acquired:
                    # 如果 Redis 不可用，记录警告但继续执行（降级处理）
                    if not redis_manager.is_connected:
                        logger.warning(
                            "Redis 不可用，无法获取分布式锁，继续执行（降级处理）",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
                    else:
                        # Redis 可用但获取锁失败，说明其他实例正在处理
                        logger.warning(
                            "获取硬件创建锁失败，可能其他实例正在处理",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
                        raise BusinessError(
                            message=f"主机 {host_id} 正在创建硬件记录，请稍后重试",
                            message_key="error.hardware.creation_in_progress",
                            error_code="HARDWARE_CREATION_IN_PROGRESS",
                            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                            http_status_code=409,  # Conflict
                            details={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )

                logger.info(
                    "已获取硬件创建锁",
                    extra={
                        "host_id": host_id,
                        "lock_key": lock_key,
                        "lock_value": lock_value[:8] if lock_value else None,
                    },
                )

            try:
                # 新增硬件：POST /api/v1/hardware/
                url_path = "/api/v1/hardware/"
                request_body = {
                    "Head": head_data,
                    "Payload": hw_info,
                }

                logger.info(
                    "调用外部硬件接口（新增）",
                    extra={
                        "url_path": url_path,
                        "user_id": user_id,
                        "has_hw_info": bool(hw_info),
                        "host_id": host_id,
                    },
                )

                response = await call_external_api(
                    method="POST",
                    url_path=url_path,
                    request=request,
                    user_id=user_id,
                    json_data=request_body,
                    locale=locale,
                )

                # 判断请求是否成功：检查响应头 :status 或响应体 code 是否为 200
                response_headers = response.get("headers", {})
                response_body = response.get("body", {})
                status_header = response_headers.get(":status") or response_headers.get("status")
                status_code = response.get("status_code")
                body_code = response_body.get("code") if isinstance(response_body, dict) else None

                # 判断成功：响应头 :status 或 status_code 或响应体 code 等于 200
                is_success = (
                    (status_header and str(status_header) == "200")
                    or (status_code and status_code == 200)
                    or (body_code and body_code == 200)
                )

                if not is_success:
                    error_msg = (
                        response_body.get("message", "未知错误")
                        if isinstance(response_body, dict)
                        else str(response_body)
                    )
                    raise BusinessError(
                        message=f"调用硬件接口失败（新增）: {error_msg}",
                        message_key="error.hardware.create_failed",
                        error_code="HARDWARE_CREATE_FAILED",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=500,
                        details={
                            "url_path": url_path,
                            "status_header": status_header,
                            "status_code": status_code,
                            "body_code": body_code,
                            "response": response_body,
                        },
                    )

                # 从响应中提取 hardware_id 和 host_name
                # 返回格式：{"_id": "hardware_id", "host_name": "host_name"}
                if isinstance(response_body, dict):
                    # 直接提取 _id 字段
                    new_hardware_id = response_body.get("_id")
                    if not new_hardware_id:
                        # 如果 _id 不存在，尝试其他字段名
                        new_hardware_id = response_body.get("hardware_id") or response_body.get("id")

                    if not new_hardware_id:
                        raise BusinessError(
                            message="硬件接口返回数据格式错误：缺少 _id 字段",
                            message_key="error.hardware.invalid_response",
                            error_code="HARDWARE_INVALID_RESPONSE",
                            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                            http_status_code=500,
                        )

                    # 提取 host_name（在响应体顶层，与 _id 同级）
                    host_name = response_body.get("host_name")
                    # 验证 host_name 不为空字符串或 None
                    if host_name and isinstance(host_name, str):
                        host_name = host_name.strip() if host_name.strip() else None
                    else:
                        host_name = None

                    logger.info(
                        "硬件接口调用成功（新增）",
                        extra={
                            "hardware_id": new_hardware_id,
                            "host_name": host_name,
                            "host_id": host_id,
                        },
                    )
                    return {"hardware_id": str(new_hardware_id), "host_name": host_name}
                else:
                    raise BusinessError(
                        message="硬件接口返回数据格式错误：响应不是 JSON 格式",
                        message_key="error.hardware.invalid_response",
                        error_code="HARDWARE_INVALID_RESPONSE",
                        code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                        http_status_code=500,
                    )
            finally:
                # 释放锁
                if lock_key and lock_value:
                    lock_released = await redis_manager.release_lock(lock_key, lock_value)
                    if lock_released:
                        logger.debug(
                            "已释放硬件创建锁",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
                    else:
                        logger.warning(
                            "释放硬件创建锁失败",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )

        else:
            # 修改硬件：PUT /api/v1/hardware/{hardware_id}
            # ✅ 此时 hardware_id 一定不是 None 且不是空字符串（已通过 is_valid_hardware_id 检查）
            assert hardware_id is not None and hardware_id.strip(), "hardware_id 必须有效"
            valid_hardware_id: str = hardware_id.strip()

            url_path = f"/api/v1/hardware/{valid_hardware_id}"
            request_body = {
                "_id": {"$oid": valid_hardware_id},
                "Head": head_data,
                "Payload": hw_info,
            }

            logger.info(
                "调用外部硬件接口（修改）",
                extra={
                    "url_path": url_path,
                    "hardware_id": valid_hardware_id,
                    "user_id": user_id,
                    "has_hw_info": bool(hw_info),
                },
            )

            response = await call_external_api(
                method="PUT",
                url_path=url_path,
                request=request,
                user_id=user_id,
                json_data=request_body,
                locale=locale,
            )

            # 判断请求是否成功：检查响应头 :status 或响应体 code 是否为 200
            response_headers = response.get("headers", {})
            response_body = response.get("body", {})
            status_header = response_headers.get(":status") or response_headers.get("status")
            status_code = response.get("status_code")
            body_code = response_body.get("code") if isinstance(response_body, dict) else None

            # 判断成功：响应头 :status 或 status_code 或响应体 code 等于 200
            is_success = (
                (status_header and str(status_header) == "200")
                or (status_code and status_code == 200)
                or (body_code and body_code == 200)
            )

            if not is_success:
                error_msg = (
                    response_body.get("message", "未知错误")
                    if isinstance(response_body, dict)
                    else str(response_body)
                )
                raise BusinessError(
                    message=f"调用硬件接口失败（修改）: {error_msg}",
                    message_key="error.hardware.update_failed",
                    error_code="HARDWARE_UPDATE_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "url_path": url_path,
                        "hardware_id": valid_hardware_id,
                        "status_header": status_header,
                        "status_code": status_code,
                        "body_code": body_code,
                        "response": response_body,
                    },
                )

            # 提取 host_name（如果响应包含）
            host_name = None
            if isinstance(response_body, dict):
                host_name = response_body.get("host_name")
                # 验证 host_name 不为空字符串或 None
                if host_name and isinstance(host_name, str):
                    host_name = host_name.strip() if host_name.strip() else None
                else:
                    host_name = None

            logger.info(
                "硬件接口调用成功（修改）",
                extra={
                    "hardware_id": valid_hardware_id,
                    "host_name": host_name,
                },
            )
            return {"hardware_id": valid_hardware_id, "host_name": host_name}

    except BusinessError:
        raise
    except Exception as e:
        logger.error(
            "调用硬件接口异常",
            extra={
                "hardware_id": hardware_id,
                "user_id": user_id,
                "has_hw_info": bool(hw_info),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise BusinessError(
            message=f"调用硬件接口异常: {str(e)}",
            message_key="error.hardware.api_error",
            error_code="HARDWARE_API_ERROR",
            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
            http_status_code=500,
            details={
                "hardware_id": hardware_id,
                "error": str(e),
            },
        )
