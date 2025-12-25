"""Agent 信息上报 API 端点

提供 Agent 上报信息的 HTTP API 接口。
"""

import os
import sys
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends
from starlette.status import HTTP_200_OK

# 使用 try-except 方式处理路径导入
try:
    from app.api.v1.dependencies import get_current_agent
    from app.schemas.host import (
        AgentVNCConnectionReportRequest,
        AgentVNCConnectionReportResponse,
        HardwareReportResponse,
        OtaConfigItem,
    )
    from app.schemas.testcase import (
        TestCaseDueTimeRequest,
        TestCaseDueTimeResponse,
        TestCaseReportRequest,
        TestCaseReportResponse,
    )
    from app.services.agent_report_service import AgentReportService, get_agent_report_service

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.api.v1.dependencies import get_current_agent
    from app.schemas.host import (
        AgentVNCConnectionReportRequest,
        AgentVNCConnectionReportResponse,
        HardwareReportResponse,
        OtaConfigItem,
    )
    from app.schemas.testcase import (
        TestCaseDueTimeRequest,
        TestCaseDueTimeResponse,
        TestCaseReportRequest,
        TestCaseReportResponse,
    )
    from app.services.agent_report_service import AgentReportService, get_agent_report_service

    from shared.common.decorators import handle_api_errors
    from shared.common.i18n import t
    from shared.common.i18n_dependencies import get_locale
    from shared.common.loguru_config import get_logger
    from shared.common.response import Result

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/hardware/report",
    response_model=Result[HardwareReportResponse],
    status_code=HTTP_200_OK,
    summary="上报硬件信息",
    description="""
    Agent 上报主机硬件信息，系统会自动检测硬件变更。

    ## 功能说明
    1. 接收 Agent 上报的硬件信息（动态 JSON）
    2. 验证硬件信息必填字段（基于硬件模板）
    3. 对比硬件版本号和内容变化
    4. 根据对比结果更新数据库记录

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - Token 中的 user_id 字段将作为 host_id 使用

    ## 请求参数
    - `dmr_config`: DMR硬件配置（必需），必须包含 `revision` 字段
    - `name`: 配置名称（可选）
    - `updated_by`: 更新者（可选）
    - `tags`: 标签列表（可选）

    ## 业务逻辑
    1. **首次上报**: 直接插入硬件记录，审批状态为通过
    2. **版本号变化**: 标记为版本号变化（diff_state=1），等待审批
    3. **内容变化**: 标记为内容更改（diff_state=2），等待审批
    4. **无变化**: 不更新记录，返回无变化状态

    ## 注意事项
    - `dmr_config.revision` 是必传字段
    - 硬件模板中标记为 `required` 的字段必须提供
    - 硬件变更会触发主机状态更新（appr_state=2, host_state=6）
    """,
    responses={
        200: {
            "description": "上报成功",
            "model": Result[HardwareReportResponse],
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "dmr_config 是必传字段",
                        "error_code": "MISSING_DMR_CONFIG",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "缺少有效的认证令牌",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "硬件信息上报处理失败",
                        "error_code": "HARDWARE_REPORT_FAILED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_hardware(
    hardware_data: Dict[str, Any] = Body(
        ...,
        description="硬件信息（动态JSON）",
        example={
            "name": "Updated Agent Config",
            "dmr_config": {
                "revision": 1,
                "mainboard": {
                    "revision": 1,
                    "plt_meta_data": {"platform": "DMR", "label_plt_cfg": "auto_generated"},
                    "board": {
                        "board_meta_data": {
                            "board_name": "SHMRCDMR",
                            "host_name": "updated-host",
                            "host_ip": "10.239.168.200",
                        },
                        "baseboard": [
                            {
                                "board_id": "board_001",
                                "rework_version": "1.0",
                                "board_ip": "10.239.168.200",
                                "bmc_ip": "10.239.168.171",
                                "fru_id": "fru_001",
                            }
                        ],
                        "lsio": {
                            "usb_disc_installed": True,
                            "network_installed": True,
                            "nvme_installed": False,
                            "keyboard_installed": True,
                            "mouse_installed": False,
                        },
                        "peripheral": {
                            "itp_installed": True,
                            "usb_dbc_installed": False,
                            "controlbox_installed": True,
                            "flash_programmer_installed": True,
                            "display_installed": True,
                            "jumpers": [],
                        },
                    },
                    "misc": {
                        "installed_os": ["Windows", "Linux"],
                        "bmc_version": "2.0.1",
                        "bmc_ip": "10.239.168.171",
                        "cpld_version": "2.1.0",
                    },
                },
                "hsio": [],
                "memory": [],
                "security": {
                    "revision": 1,
                    "security": {
                        "Tpm": [
                            {
                                "tpm_enable": True,
                                "tpm_algorithm": "SHA256",
                                "tmp_family": "2.0",
                                "tpm_interface": "TIS",
                            }
                        ],
                        "CoinBattery": [],
                    },
                },
                "soc": [],
            },
            "updated_by": "agent@intel.com",
            "tags": ["alive", "checked", "updated"],
            "type": 0,
        },
    ),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[HardwareReportResponse]:
    """上报硬件信息

    Args:
        hardware_data: 硬件信息（动态JSON），包含：
            - dmr_config: DMR硬件配置（必需）
            - type: 上报类型（可选，默认为0）
                - 0: 成功，走正常对比逻辑
                - 1: 异常，直接设置 diff_state=3
        agent_info: 当前Agent信息（从token中提取，包含host_id）
        agent_report_service: Agent硬件服务实例

    Returns:
        SuccessResponse: 处理结果

    Raises:
        HTTPException: 业务逻辑错误或系统错误（由 @handle_api_errors 统一处理）
    """
    # ✅ 从 token 中获取 host_id（已通过 get_current_agent 依赖注入验证）
    host_id = agent_info["host_id"]

    # 提取 type 参数（可选，默认为 0）
    report_type = hardware_data.get("type", 0)

    logger.info(
        "收到硬件信息上报请求",
        extra={
            "host_id": host_id,
            "has_dmr_config": "dmr_config" in hardware_data,
            "type": report_type,
        },
    )

    # 调用服务层处理硬件信息上报
    result = await agent_report_service.report_hardware(
        host_id=host_id,
        hardware_data=hardware_data,
        report_type=report_type,
    )

    response_data = HardwareReportResponse(**result)
    return Result(
        code=200,
        message=t("success.hardware.report", locale=locale, default="硬件信息上报成功"),
        data=response_data,
        locale=locale,
    )


@router.post(
    "/testcase/report",
    response_model=Result[TestCaseReportResponse],
    status_code=HTTP_200_OK,
    summary="上报测试用例执行结果",
    description="""
    Agent 上报测试用例执行结果，系统会更新执行日志记录。

    ## 功能说明
    1. 接收 Agent 上报的测试用例执行结果
    2. 从 JWT token 中提取 host_id
    3. 根据 host_id 和 tc_id 查询最新的执行日志记录
    4. 更新执行状态、结果消息和日志URL

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - Token 中的 user_id 字段将作为 host_id 使用

    ## 请求参数
    - `tc_id`: 测试用例ID（必需）
    - `state`: 执行状态（必需）；0-空闲 1-启动 2-成功 3-失败
    - `result_msg`: 结果消息（可选）
    - `log_url`: 日志文件URL（可选）

    ## 业务逻辑
    1. 根据 host_id 和 tc_id 查询 host_exec_log 表最新一条记录
    2. 更新 case_state、result_msg 和 log_url 字段
    3. 返回更新结果

    ## 注意事项
    - tc_id 是必传字段
    - state 必须在 0-3 范围内
    - 如果未找到对应的执行日志记录，返回404错误
    """,
    responses={
        200: {
            "description": "上报成功",
            "model": Result[TestCaseReportResponse],
        },
        400: {
            "description": "请求参数错误或业务逻辑错误（包括：请求参数验证失败、未找到执行日志记录等）",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "请求参数验证失败",
                            "value": {
                                "code": 400,
                                "message": "请求参数验证失败",
                                "error_code": "VALIDATION_ERROR",
                                "details": None,
                                "timestamp": "2025-10-30T10:00:00Z",
                            },
                        },
                        "exec_log_not_found": {
                            "summary": "未找到执行日志记录",
                            "value": {
                                "code": 53012,
                                "message": "未找到主机的测试用例执行记录",
                                "error_code": "EXEC_LOG_NOT_FOUND",
                                "details": None,
                                "timestamp": "2025-10-30T10:00:00Z",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "缺少有效的认证令牌",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-10-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "测试用例结果上报处理失败",
                        "error_code": "TESTCASE_REPORT_FAILED",
                        "details": None,
                        "timestamp": "2025-10-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_testcase_result(
    report_data: TestCaseReportRequest = Body(
        ...,
        description="测试用例执行结果",
    ),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[TestCaseReportResponse]:
    """上报测试用例执行结果

    Args:
        report_data: 测试用例执行结果
        agent_info: 当前Agent信息（从token中提取，包含host_id）
        agent_report_service: Agent硬件服务实例

    Returns:
        SuccessResponse: 处理结果

    Raises:
        HTTPException: 业务逻辑错误或系统错误（由 @handle_api_errors 统一处理）
    """
    # ✅ 从 token 中获取 host_id（已通过 get_current_agent 依赖注入验证）
    host_id = agent_info["host_id"]

    logger.info(
        "收到测试用例结果上报请求",
        extra={
            "host_id": host_id,
            "tc_id": report_data.tc_id,
            "state": report_data.state,
        },
    )

    # 调用服务层处理测试用例结果上报
    result = await agent_report_service.report_testcase_result(
        host_id=host_id,
        tc_id=report_data.tc_id,
        state=report_data.state,
        result_msg=report_data.result_msg,
        log_url=report_data.log_url,
    )

    response_data = TestCaseReportResponse(**result)
    return Result(
        code=200,
        message=t("success.hardware.test_result_report", locale=locale, default="测试用例结果上报成功"),
        data=response_data,
        locale=locale,
    )


@router.put(
    "/testcase/due-time",
    response_model=Result[TestCaseDueTimeResponse],
    status_code=HTTP_200_OK,
    summary="上报测试用例预期结束时间",
    description="""
    Agent 上报测试用例预期结束时间，系统会更新执行日志记录的 due_time 字段。

    ## 功能说明
    1. 接收 Agent 上报的预期结束时间
    2. 从 JWT token 中提取 host_id
    3. 根据 host_id 和 tc_id 查询执行中的最新执行日志记录（case_state=1）
    4. 更新 due_time 字段

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - Token 中的 user_id 字段将作为 host_id 使用

    ## 请求参数
    - `tc_id`: 测试用例ID（必需）
    - `due_time`: 预期结束时间（必需，ISO 8601 格式）

    ## 业务逻辑
    1. 根据 host_id 和 tc_id 查询 host_exec_log 表执行中的最新一条记录（case_state=1）
    2. 更新 due_time 字段
    3. 返回更新结果

    ## 注意事项
    - tc_id 是必传字段
    - due_time 必须是有效的 ISO 8601 格式时间
    - 如果未找到执行中的记录，返回400错误
    """,
    responses={
        200: {
            "description": "上报成功",
            "model": Result[TestCaseDueTimeResponse],
        },
        400: {
            "description": "请求参数错误或业务逻辑错误（包括：请求参数验证失败、未找到执行中的记录等）",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "请求参数验证失败",
                            "value": {
                                "code": 400,
                                "message": "请求参数验证失败",
                                "error_code": "VALIDATION_ERROR",
                                "details": None,
                                "timestamp": "2025-01-30T10:00:00Z",
                            },
                        },
                        "exec_log_not_found": {
                            "summary": "未找到执行中的记录",
                            "value": {
                                "code": 53012,
                                "message": "未找到主机 {host_id} 的测试用例 {tc_id} 执行中的记录",
                                "error_code": "EXEC_LOG_NOT_FOUND",
                                "details": None,
                                "timestamp": "2025-01-30T10:00:00Z",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "缺少有效的认证令牌",
                        "error_code": "UNAUTHORIZED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "预期结束时间上报处理失败",
                        "error_code": "DUE_TIME_UPDATE_FAILED",
                        "details": None,
                        "timestamp": "2025-01-30T10:00:00Z",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_due_time(
    report_data: TestCaseDueTimeRequest = Body(
        ...,
        description="测试用例预期结束时间",
    ),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[TestCaseDueTimeResponse]:
    """上报测试用例预期结束时间

    Args:
        report_data: 测试用例预期结束时间
        agent_info: 当前Agent信息（从token中提取，包含host_id）
        agent_report_service: Agent硬件服务实例

    Returns:
        Result: 处理结果

    Raises:
        HTTPException: 业务逻辑错误或系统错误（由 @handle_api_errors 统一处理）
    """
    # ✅ 从 token 中获取 host_id（已通过 get_current_agent 依赖注入验证）
    host_id = agent_info["host_id"]

    logger.info(
        "收到预期结束时间上报请求",
        extra={
            "host_id": host_id,
            "tc_id": report_data.tc_id,
            "due_time": report_data.due_time.isoformat() if report_data.due_time else None,
        },
    )

    # 调用服务层处理预期结束时间上报
    result = await agent_report_service.update_due_time(
        host_id=host_id,
        tc_id=report_data.tc_id,
        due_time=report_data.due_time,
    )

    response_data = TestCaseDueTimeResponse(**result)
    return Result(
        code=200,
        message=t("success.hardware.due_time_report", locale=locale, default="预期结束时间上报成功"),
        data=response_data,
        locale=locale,
    )


@router.get(
    "/ota/latest",
    response_model=Result[List[OtaConfigItem]],
    status_code=HTTP_200_OK,
    summary="获取最新 OTA 配置信息",
    description="""
    Agent 获取 OTA 版本配置信息。

    ## 功能说明
    1. 查询 `sys_conf` 表中 `conf_key = "ota"` 的有效配置
    2. 返回按更新时间倒序排列的配置列表

    ## 响应说明
    - `conf_name`: 配置名称
    - `conf_ver`: 配置版本号
    - `conf_url`: OTA 包下载地址
    - `conf_md5`: OTA 包 MD5 校验值
    """,
)
@handle_api_errors
async def get_latest_ota_configs(
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[List[OtaConfigItem]]:
    """获取最新 OTA 配置信息"""
    logger.info("收到获取 OTA 配置信息请求")

    configs = await agent_report_service.get_latest_ota_configs()
    ota_items = [OtaConfigItem(**config) for config in configs]

    return Result(
        code=200,
        message=t("success.ota.query", locale=locale, default="获取 OTA 配置成功"),
        data=ota_items,
        locale=locale,
    )


@router.post(
    "/vnc/report",
    response_model=Result[AgentVNCConnectionReportResponse],
    status_code=HTTP_200_OK,
    summary="Agent 上报 VNC 连接成功",
    description="""
    Agent 上报 VNC 连接成功，系统会更新主机状态。

    ## 功能说明
    1. 从 JWT token 中提取 host_id
    2. 更新对应的 host_rec 表的 host_state = 2（已占用）

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - Token 中的 user_id 字段将作为 host_id 使用

    ## 业务逻辑
    1. 从 token 中解析 host_id（通过依赖注入自动完成）
    2. 查询 host_rec 表，验证主机是否存在
    3. 更新 host_rec 表的 host_state = 2（已占用状态）

    ## 返回数据
    - `host_id`: 主机ID
    - `host_state`: 更新后的主机状态（2=已占用）
    - `updated`: 是否成功更新

    ## 错误码
    - `HOST_NOT_FOUND`: 主机不存在或已删除（404）
    - `VNC_CONNECTION_REPORT_FAILED`: 上报处理失败（500）
    """,
    responses={
        200: {
            "description": "上报成功",
            "model": Result[AgentVNCConnectionReportResponse],
        },
        404: {
            "description": "主机不存在或已删除",
            "content": {
                "application/json": {
                    "example": {
                        "code": 404,
                        "message": "主机不存在: 123",
                        "error_code": "HOST_NOT_FOUND",
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 500,
                        "message": "Agent VNC 连接成功上报处理失败",
                        "error_code": "VNC_CONNECTION_REPORT_FAILED",
                    }
                }
            },
        },
    },
)
@handle_api_errors
async def report_vnc_connection_success(
    request: AgentVNCConnectionReportRequest = Body(..., description="Agent VNC 连接成功上报请求（空请求体）"),
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
    locale: str = Depends(get_locale),
) -> Result[AgentVNCConnectionReportResponse]:
    """Agent 上报 VNC 连接成功

    ## 业务逻辑
    1. 从 token 中解析 host_id（已通过 get_current_agent 依赖注入验证）
    2. 更新对应的 host_rec 表的 host_state = 2（已占用）

    Args:
        request: Agent VNC 连接成功上报请求（空请求体）
        agent_info: 当前Agent信息（从token中提取，包含host_id）
        agent_report_service: Agent上报服务实例
        locale: 语言偏好

    Returns:
        SuccessResponse: 统一格式的成功响应，包含更新结果

    Raises:
        HTTPException: 业务逻辑错误或系统错误（由 @handle_api_errors 统一处理）
    """
    # ✅ 从 token 中获取 host_id（已通过 get_current_agent 依赖注入验证）
    host_id = agent_info["host_id"]

    logger.info(
        "收到 Agent VNC 连接成功上报请求",
        extra={
            "host_id": host_id,
        },
    )

    # 调用服务层处理 VNC 连接成功上报
    result = await agent_report_service.report_vnc_connection_success(host_id=host_id)

    response_data = AgentVNCConnectionReportResponse(**result)
    return Result(
        code=200,
        message=t("success.vnc.agent_report", locale=locale, default="Agent VNC 连接成功上报成功"),
        data=response_data,
        locale=locale,
    )
