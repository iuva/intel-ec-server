"""浏览器插件 VNC 连接管理服务

提供浏览器插件使用的 VNC 连接相关的业务逻辑服务，包括：
- 处理 VNC 连接结果上报
- 获取主机 VNC 连接信息
"""

from datetime import datetime, timezone
from typing import Optional, cast

from sqlalchemy import and_, select, update

from app.models.host_exec_log import HostExecLog
from app.models.host_rec import HostRec
from app.schemas.host import VNCConnectionReport

# 使用 try-except 方式处理路径导入
try:
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.schemas.websocket_message import MessageType
    from app.utils.cache_invalidation import invalidate_available_hosts_cache
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.agent_websocket_manager import get_agent_websocket_manager
    from app.schemas.websocket_message import MessageType
    from app.utils.cache_invalidation import invalidate_available_hosts_cache
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
    from shared.common.security import aes_decrypt
    from shared.utils.host_validators import validate_host_exists

# RealVNC 加密依赖
try:
    from Crypto.Cipher import DES
except ImportError:
    DES = None  # type: ignore

logger = get_logger(__name__)


def _reverse_bits(byte_val: int) -> int:
    """翻转字节中的位顺序

    Args:
        byte_val: 要翻转的字节值 (0-255)

    Returns:
        位翻转后的字节值
    """
    result = 0
    for i in range(8):
        if byte_val & (1 << i):
            result |= 1 << (7 - i)
    return result


def _realvnc_encrypt_***REMOVED***word(***REMOVED***word: str) -> str:
    """RealVNC密码加密算法

    该算法使用固定的DES密钥对密码进行加密，密码被分成多个8字节块：
    1. 第一个块：密码的前8个字符（不足8个用null字节填充）
    2. 第二个块：密码的第9-16个字符（不足8个用null字节填充）
    3. 第三个块：密码的第17-24个字符（不足8个用null字节填充）

    Args:
        ***REMOVED***word: 要加密的密码

    Returns:
        十六进制字符串（长度取决于密码长度）

    Raises:
        BusinessError: 当 DES 加密库未安装时
    """
    if DES is None:
        raise BusinessError(
            message="RealVNC 加密功能需要 pycryptodome 库，请安装: pip install pycryptodome",
            error_code="REALVNC_ENCRYPTION_LIBRARY_MISSING",
            code=ServiceErrorCodes.HOST_REALVNC_ENCRYPTION_LIBRARY_MISSING,
            http_status_code=500,
        )

    # RealVNC使用的固定DES密钥
    REALVNC_DES_KEY = bytes([0x17, 0x52, 0x6B, 0x06, 0x23, 0x4E, 0x58, 0x07])

    # 对固定密钥进行位翻转处理（VNC协议的特殊要求）
    reversed_key = bytes([_reverse_bits(b) for b in REALVNC_DES_KEY])

    # 创建DES加密器
    cipher = DES.new(reversed_key, DES.MODE_ECB)

    # 将密码分成8字节块进行加密
    encrypted_blocks = []

    # 计算需要的块数（至少2个块，最多3个块）
    block_count = max(2, min(3, (len(***REMOVED***word) + 7) // 8))

    for i in range(block_count):
        start_pos = i * 8
        end_pos = start_pos + 8

        # 获取当前块的密码片段
        ***REMOVED***word_chunk = ***REMOVED***word[start_pos:end_pos]

        # 填充到8字节
        block = ***REMOVED***word_chunk.ljust(8, "\x00").encode("ascii")

        # 加密当前块
        encrypted_block = cipher.encrypt(block)
        encrypted_blocks.append(encrypted_block)

    # 连接所有加密结果并转换为十六进制字符串
    result = b"".join(encrypted_blocks).hex().lower()

    return result


class BrowserVNCService:
    """浏览器插件 VNC 连接管理服务类

    负责处理浏览器插件的 VNC 连接相关的业务逻辑，包括连接结果上报和连接信息获取。
    """

    @handle_service_errors(
        error_message="上报 VNC 连接结果失败",
        error_code="REPORT_VNC_FAILED",
    )
    async def report_vnc_connection(self, vnc_report: VNCConnectionReport) -> dict:
        """处理浏览器插件上报的VNC连接结果

        功能描述：
        1. 根据 host_id 验证主机是否存在
        2. 如果 connection_status = "success"：
           - 查询 host_exec_log 表（user_id、tc_id、cycle_name、user_name、host_id、del_flag=0）
           - 如果存在旧记录：先逻辑删除旧记录（del_flag=1）
           - 无论是否存在旧记录：都新增一条新记录（host_state=1, case_state=0）
        3. 更新 host_rec 表：host_state = 1, subm_time = 当前时间

        Args:
            vnc_report: VNC连接结果上报数据
                - user_id: 用户ID
                - tc_id: 执行测试ID
                - cycle_name: 周期名称
                - user_name: 用户名称
                - host_id: 主机ID
                - connection_status: 连接状态 (success/failed)
                - connection_time: 连接时间

        Returns:
            处理结果字典，包含主机ID、连接状态和处理消息

        Raises:
            BusinessError: 主机不存在或处理失败
        """
        # 转换 host_id 为整数
        try:
            host_id_int = int(vnc_report.host_id)
        except (ValueError, TypeError):
            logger.warning(
                "主机ID格式错误",
                extra={
                    "host_id": vnc_report.host_id,
                    "error": "not a valid integer",
                },
            )
            raise BusinessError(
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                http_status_code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 使用工具函数验证主机存在且未删除
            host_rec = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            # 记录更新前的状态
            old_host_state = host_rec.host_state
            old_subm_time = host_rec.subm_time

            # 2. 如果连接状态为 success，处理 host_exec_log 表
            exec_log_action = None  # 记录操作类型：deleted_and_created/created
            if vnc_report.connection_status == "success":
                # 查询 host_exec_log 表
                log_stmt = select(HostExecLog).where(
                    and_(
                        HostExecLog.user_id == vnc_report.user_id,
                        HostExecLog.tc_id == vnc_report.tc_id,
                        HostExecLog.cycle_name == vnc_report.cycle_name,
                        HostExecLog.user_name == vnc_report.user_name,
                        HostExecLog.host_id == host_id_int,
                        HostExecLog.del_flag == 0,
                    )
                )
                log_result = await session.execute(log_stmt)
                logs = log_result.scalars().all()

                if len(logs) > 1:
                    logger.warning(
                        "找到多条执行日志，无法继续",
                        extra={
                            "user_id": vnc_report.user_id,
                            "host_id": vnc_report.host_id,
                            "count": len(logs),
                        },
                    )
                    raise BusinessError(
                        message="存在多条未完成的执行日志，请联系管理员处理",
                        error_code="MULTIPLE_EXEC_LOGS_FOUND",
                        code=ServiceErrorCodes.HOST_MULTIPLE_EXEC_LOGS_FOUND,
                        http_status_code=409,
                    )

                existing_log = logs[0] if logs else None

                if existing_log:
                    # 存在记录：先逻辑删除
                    logger.info(
                        "找到已存在的执行日志，先进行逻辑删除",
                        extra={
                            "log_id": existing_log.id,
                            "user_id": vnc_report.user_id,
                            "host_id": vnc_report.host_id,
                        },
                    )

                    update_stmt = update(HostExecLog).where(HostExecLog.id == existing_log.id).values(del_flag=1)
                    await session.execute(update_stmt)
                    exec_log_action = "deleted_and_created"
                else:
                    logger.info(
                        "未找到已存在的执行日志",
                        extra={
                            "user_id": vnc_report.user_id,
                            "host_id": vnc_report.host_id,
                        },
                    )
                    exec_log_action = "created"

                # 无论是否存在旧记录，都新增一条新记录
                logger.info(
                    "创建新的执行日志记录",
                    extra={
                        "user_id": vnc_report.user_id,
                        "host_id": vnc_report.host_id,
                    },
                )

                new_log = HostExecLog(
                    host_id=host_id_int,
                    user_id=vnc_report.user_id,
                    tc_id=vnc_report.tc_id,
                    cycle_name=vnc_report.cycle_name,
                    user_name=vnc_report.user_name,
                    host_state=1,  # 已锁定
                    case_state=0,  # 空闲
                    begin_time=datetime.now(timezone.utc),
                    del_flag=0,
                )
                session.add(new_log)

            # 3. 更新 host_rec 表
            host_rec.host_state = 1  # 已锁定状态
            host_rec.subm_time = datetime.now(timezone.utc)

            # 提交所有更改
            await session.commit()
            await session.refresh(host_rec)

            # ✅ 优化：如果连接状态为 success，清除可用主机列表缓存
            # 因为主机状态已变为已锁定，不应再出现在可用主机列表中
            if vnc_report.connection_status == "success":
                try:
                    deleted_count = await invalidate_available_hosts_cache()
                    if deleted_count > 0:
                        logger.info(
                            "可用主机列表缓存已清除（VNC连接成功）",
                            extra={
                                "host_id": vnc_report.host_id,
                                "deleted_cache_count": deleted_count,
                            },
                        )
                    else:
                        logger.debug(
                            "未找到需要清除的可用主机列表缓存",
                            extra={"host_id": vnc_report.host_id},
                        )
                except Exception as e:
                    logger.warning(
                        "清除可用主机列表缓存失败",
                        extra={
                            "host_id": vnc_report.host_id,
                            "error": str(e),
                        },
                    )

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
                    "tc_id": vnc_report.tc_id,
                    "cycle_name": vnc_report.cycle_name,
                    "user_name": vnc_report.user_name,
                    "host_id": vnc_report.host_id,
                    "connection_status": vnc_report.connection_status,
                    "connection_time": connection_time_str,
                    "old_host_state": old_host_state,
                    "new_host_state": host_rec.host_state,
                    "old_subm_time": old_subm_time_str,
                    "new_subm_time": new_subm_time_str,
                    "exec_log_action": exec_log_action,
                },
            )

            # ✅ 如果连接状态为 success，通过 WebSocket 通知 Agent 进行日志监控
            # 使用大小写不敏感的比较，确保 "success"、"Success"、"SUCCESS" 都能匹配
            connection_status_lower = vnc_report.connection_status.lower() if vnc_report.connection_status else ""
            if connection_status_lower == "success":
                logger.info(
                    "准备发送 WebSocket 通知给 Agent",
                    extra={
                        "host_id": vnc_report.host_id,
                        "connection_status": vnc_report.connection_status,
                        "user_id": vnc_report.user_id,
                        "tc_id": vnc_report.tc_id,
                    },
                )
                try:
                    ws_manager = get_agent_websocket_manager()
                    host_id_str = str(vnc_report.host_id)

                    # 检查 Agent 是否已连接
                    if not ws_manager.is_connected(host_id_str):
                        logger.warning(
                            "Agent 未连接，无法发送 WebSocket 通知",
                            extra={
                                "host_id": host_id_str,
                                "user_id": vnc_report.user_id,
                                "tc_id": vnc_report.tc_id,
                                "active_connections": ws_manager.get_connection_count(),
                            },
                        )
                    else:
                        # 构建连接通知消息
                        connection_notification = {
                            "type": MessageType.CONNECTION_NOTIFICATION,
                            "host_id": host_id_str,
                            "message": "VNC连接成功，请开始日志监控",
                            "action": "start_log_monitoring",
                            "details": {
                                "user_id": vnc_report.user_id,
                                "tc_id": vnc_report.tc_id,
                                "cycle_name": vnc_report.cycle_name,
                                "user_name": vnc_report.user_name,
                                "connection_time": connection_time_str,
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

                        logger.debug(
                            "准备发送 WebSocket 通知消息",
                            extra={
                                "host_id": host_id_str,
                                "message_type": MessageType.CONNECTION_NOTIFICATION,
                                "message": connection_notification,
                            },
                        )

                        # 发送通知
                        success = await ws_manager.send_to_host(host_id_str, connection_notification)
                        if success:
                            logger.info(
                                "连接通知已发送给 Agent",
                                extra={
                                    "host_id": host_id_str,
                                    "user_id": vnc_report.user_id,
                                    "tc_id": vnc_report.tc_id,
                                    "message_type": MessageType.CONNECTION_NOTIFICATION,
                                },
                            )
                        else:
                            logger.warning(
                                "连接通知发送失败（Agent 可能未连接或发送失败）",
                                extra={
                                    "host_id": host_id_str,
                                    "user_id": vnc_report.user_id,
                                    "tc_id": vnc_report.tc_id,
                                    "message_type": MessageType.CONNECTION_NOTIFICATION,
                                    "is_connected": ws_manager.is_connected(host_id_str),
                                },
                            )
                except Exception as e:
                    # 通知发送失败不影响主流程，只记录警告
                    logger.error(
                        "发送连接通知异常",
                        extra={
                            "host_id": vnc_report.host_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "connection_status": vnc_report.connection_status,
                        },
                        exc_info=True,
                    )
            else:
                logger.debug(
                    "连接状态不是 success，跳过 WebSocket 通知",
                    extra={
                        "host_id": vnc_report.host_id,
                        "connection_status": vnc_report.connection_status,
                        "connection_status_lower": connection_status_lower,
                    },
                )

            return {
                "host_id": vnc_report.host_id,
                "connection_status": vnc_report.connection_status,
                "connection_time": vnc_report.connection_time,
            }

    @handle_service_errors(
        error_message="获取 VNC 连接信息失败",
        error_code="GET_VNC_CONNECTION_FAILED",
    )
    async def get_vnc_connection_info(self, host_rec_id: str) -> dict:
        """获取指定主机的 VNC 连接信息

        业务逻辑：
        1. 如果 host_rec_id = "1111111"，返回模拟数据（不查数据库）
        2. 否则，根据 host_rec_id 查询 host_rec 表
        3. 检查数据有效性（del_flag=0, appr_state=1）
        4. 更新主机状态为已锁定（host_state = 1）
        5. 返回 VNC 连接所需的字段

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
            extra={
                "operation": "get_vnc_connection_info",
                "host_rec_id": host_rec_id,
            },
        )

        # ✅ 如果 host_rec_id = "1111111"，返回模拟数据（不查数据库）
        if host_rec_id == "1111111":
            logger.info(
                "使用模拟数据（测试主机ID: 1111111）",
                extra={
                    "operation": "get_vnc_connection_info",
                    "host_rec_id": host_rec_id,
                    "is_mock_data": True,
                },
            )
            return {
                "ip": "10.239.168.184",
                "port": "5900",
                "username": "ccr\\sys_eval",
                "***REMOVED***word": "***REMOVED***",
            }

        try:
            # 将字符串 ID 转换为整数
            try:
                host_id = int(host_rec_id)
            except (ValueError, TypeError):
                logger.warning(
                    "主机ID格式错误",
                    extra={
                        "host_rec_id": host_rec_id,
                        "error": "not a valid integer",
                    },
                )
                raise BusinessError(
                    message="主机ID格式无效",
                    error_code="INVALID_HOST_ID",
                    code=ServiceErrorCodes.HOST_INVALID_HOST_ID,
                    http_status_code=400,
                )

            # 查询主机记录
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # 使用工具函数验证主机存在且未删除
                host_rec = await validate_host_exists(session, HostRec, host_id, locale="zh_CN")

                # 检查主机是否已启用（appr_state == 1）
                if host_rec.appr_state != 1:
                    logger.warning(
                        "主机未启用",
                        extra={
                            "host_rec_id": host_rec_id,
                            "appr_state": host_rec.appr_state,
                            "error": "host not enabled",
                        },
                    )
                    raise BusinessError(
                        message="主机未启用",
                        message_key="error.host.not_enabled",
                        error_code="HOST_NOT_ENABLED",
                        code=ServiceErrorCodes.HOST_NOT_FOUND,
                        http_status_code=400,
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
                        message="VNC 连接信息不完整，缺少 IP 地址或端口",
                        message_key="error.vnc.info_incomplete",
                        error_code="VNC_INFO_INCOMPLETE",
                        code=ServiceErrorCodes.HOST_VNC_INFO_INCOMPLETE,
                        http_status_code=400,
                    )

                # 处理密码：AES 解密 -> RealVNC 加密
                vnc_***REMOVED***word = ""
                if host_rec.host_pwd:
                    try:
                        # 1. 使用 AES 解密数据库中的密码
                        ***REMOVED*** = aes_decrypt(host_rec.host_pwd)
                        if ***REMOVED***:
                            logger.debug(
                                "密码 AES 解密成功",
                                extra={
                                    "host_rec_id": host_rec_id,
                                },
                            )

                            # 2. 使用 RealVNC 加密算法加密密码
                            vnc_***REMOVED***word = _realvnc_encrypt_***REMOVED***word(***REMOVED***)
                            logger.debug(
                                "密码 RealVNC 加密成功",
                                extra={
                                    "host_rec_id": host_rec_id,
                                    "***REMOVED***word_length": len(***REMOVED***),
                                    "encrypted_length": len(vnc_***REMOVED***word),
                                },
                            )
                        else:
                            logger.warning(
                                "密码 AES 解密返回 None",
                                extra={
                                    "host_rec_id": host_rec_id,
                                    "note": "可能是密码格式不正确或加密方式不匹配",
                                },
                            )
                    except Exception as e:
                        logger.warning(
                            "密码处理异常（AES 解密或 RealVNC 加密）",
                            extra={
                                "host_rec_id": host_rec_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        # 密码处理失败时返回空字符串，而不是抛出异常
                        vnc_***REMOVED***word = ""

                # ✅ 更新主机状态为已锁定（host_state = 1）
                old_host_state = host_rec.host_state
                host_rec.host_state = 1  # 已锁定状态
                host_rec.subm_time = datetime.now(timezone.utc)

                # 提交状态更新
                await session.commit()
                await session.refresh(host_rec)

                logger.info(
                    "主机状态已更新为已锁定",
                    extra={
                        "host_rec_id": host_rec_id,
                        "old_host_state": old_host_state,
                        "new_host_state": host_rec.host_state,
                    },
                )

                # ✅ 优化：清除可用主机列表缓存，因为主机状态已变为已锁定
                # 该主机不应再出现在可用主机列表中，需要清除相关缓存
                try:
                    deleted_count = await invalidate_available_hosts_cache()
                    if deleted_count > 0:
                        logger.info(
                            "可用主机列表缓存已清除（主机状态已锁定）",
                            extra={
                                "host_rec_id": host_rec_id,
                                "deleted_cache_count": deleted_count,
                            },
                        )
                    else:
                        logger.debug(
                            "未找到需要清除的可用主机列表缓存",
                            extra={"host_rec_id": host_rec_id},
                        )
                except Exception as e:
                    logger.warning(
                        "清除可用主机列表缓存失败",
                        extra={
                            "host_rec_id": host_rec_id,
                            "error": str(e),
                        },
                    )

                # 构建响应数据
                vnc_info = {
                    "ip": cast(str, host_rec.host_ip),
                    "port": (str(cast(int, host_rec.host_port)) if host_rec.host_port else "5900"),
                    "username": cast(str, host_rec.host_acct) or "",
                    "***REMOVED***word": vnc_***REMOVED***word,  # 返回 RealVNC 加密后的密码
                }

                logger.info(
                    "VNC 连接信息获取成功",
                    extra={
                        "host_rec_id": host_rec_id,
                        "ip": vnc_info["ip"],
                        "port": vnc_info["port"],
                        "username": vnc_info["username"],
                        "host_state": host_rec.host_state,
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
                code=ServiceErrorCodes.HOST_VNC_GET_FAILED,
                http_status_code=500,
            )
