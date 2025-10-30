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
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


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
                code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 1. 验证主机是否存在
            stmt = select(HostRec).where(
                HostRec.id == host_id_int,
                HostRec.del_flag == 0,
            )
            result = await session.execute(stmt)
            host_rec = result.scalar_one_or_none()

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
                    code=400,
                )

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
                existing_log = log_result.scalar_one_or_none()

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

            return {
                "host_id": vnc_report.host_id,
                "connection_status": vnc_report.connection_status,
                "connection_time": vnc_report.connection_time,
                "message": f"VNC连接结果上报成功，主机已锁定{f'，执行日志已{exec_log_action}' if exec_log_action else ''}",
            }

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
            extra={
                "operation": "get_vnc_connection_info",
                "host_rec_id": host_rec_id,
            },
        )

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
                    "port": (str(cast(int, host_rec.host_port)) if host_rec.host_port else "5900"),
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
