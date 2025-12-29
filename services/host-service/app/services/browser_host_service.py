"""浏览器插件主机管理服务

提供浏览器插件使用的主机查询、状态更新等核心业务逻辑。
"""

from datetime import datetime
from typing import List, cast

from app.models.host_exec_log import HostExecLog
from app.models.host_rec import HostRec
from app.schemas.host import HostStatusUpdate, RetryVNCHostInfo
from sqlalchemy import and_, select, update

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.utils.host_validators import validate_host_exists
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.utils.host_validators import validate_host_exists

logger = get_logger(__name__)


class BrowserHostService:
    """浏览器插件主机管理服务类

    负责浏览器插件的主机管理操作，包括查询、状态更新、心跳更新等。
    """

    @handle_service_errors(
        error_message="查询主机信息失败",
        error_code="GET_HOST_FAILED",
    )
    async def get_host_by_id(self, host_id: str) -> dict:
        """根据ID查询主机信息

        Args:
            host_id: 主机ID

        Returns:
            主机信息字典

        Raises:
            BusinessError: 主机不存在时
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 使用工具函数验证主机存在
            host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            logger.info(
                "查询主机信息成功",
                extra={
                    "host_id": host_id,
                    "hardware_id": host.hardware_id,
                },
            )

            return {
                "id": host.id,
                "hardware_id": host.hardware_id,
                "host_acct": host.host_acct,
                "host_ip": host.host_ip,
                "host_port": host.host_port,
                "appr_state": host.appr_state,
                "host_state": host.host_state,
            }

    @handle_service_errors(
        error_message="更新主机状态失败",
        error_code="UPDATE_HOST_STATUS_FAILED",
    )
    async def update_host_status(self, host_id: str, status_update: HostStatusUpdate) -> dict:
        """更新主机状态

        Args:
            host_id: 主机ID
            status_update: 状态更新数据

        Returns:
            更新后的主机信息

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        # ✅ 记录方法调用开始（用于调试）
        status_update_str = (
            status_update.model_dump()
            if hasattr(status_update, "model_dump")
            else str(status_update)
        )
        logger.debug(
            f"开始更新主机状态: {host_id}",
            extra={
                "host_id": host_id,
                "status_update": status_update_str,
            },
        )

        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError) as e:
            logger.error(
                f"主机ID格式无效: {host_id}",
                extra={
                    "host_id": host_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise BusinessError(
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            try:
                # 使用工具函数验证主机存在
                logger.debug(f"验证主机存在: {host_id} (int: {host_id_int})")
                host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")
                logger.debug(
                    f"主机验证成功: {host_id}",
                    extra={
                        "host_id": host_id,
                        "host_found": host is not None,
                        "current_host_state": host.host_state if host else None,
                        "current_appr_state": host.appr_state if host else None,
                    },
                )
            except BusinessError as validate_error:
                # BusinessError 直接重新抛出，但记录详细信息
                logger.error(
                    f"验证主机存在失败（业务异常）: {host_id}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "error_code": validate_error.error_code,
                        "error_message": validate_error.message,
                        "business_code": validate_error.code,
                        "details": validate_error.details,
                    },
                    exc_info=True,
                )
                raise
            except Exception as validate_error:
                # 验证主机存在失败，记录详细错误信息
                logger.error(
                    f"验证主机存在失败（系统异常）: {host_id}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "error_type": type(validate_error).__name__,
                        "error_message": str(validate_error),
                    },
                    exc_info=True,
                )
                raise

            # 记录当前状态（用于调试）
            old_host_state = host.host_state
            old_appr_state = host.appr_state

            # ✅ 更新主机状态
            # 支持两种方式：
            # 1. 直接使用 host_state 和 appr_state（整数）
            # 2. 使用 status 字符串（转换为对应的 host_state）
            state_changed = False
            if status_update.host_state is not None:
                if host.host_state != status_update.host_state:
                    host.host_state = status_update.host_state
                    state_changed = True
            elif hasattr(status_update, "status") and status_update.status:
                # 将字符串状态转换为 host_state
                status_map = {
                    "online": None,  # 在线状态不需要更新 host_state
                    "offline": 4,    # 4 = 离线状态
                    "error": None,   # 错误状态暂不处理
                }
                mapped_state = status_map.get(status_update.status.lower())
                if mapped_state is not None and host.host_state != mapped_state:
                    host.host_state = mapped_state
                    state_changed = True

            if status_update.appr_state is not None:
                if host.appr_state != status_update.appr_state:
                    host.appr_state = status_update.appr_state
                    state_changed = True

            # 记录状态变更信息（用于调试）
            logger.debug(
                f"主机状态更新检查: {host_id}",
                extra={
                    "host_id": host_id,
                    "old_host_state": old_host_state,
                    "new_host_state": host.host_state,
                    "old_appr_state": old_appr_state,
                    "new_appr_state": host.appr_state,
                    "state_changed": state_changed,
                    "status_update": status_update_str,
                },
            )

            # ✅ 只有在状态确实改变时才提交
            if state_changed:
                try:
                    await session.commit()
                    await session.refresh(host)
                    logger.info(
                        "主机状态更新成功",
                        extra={
                            "host_id": host_id,
                            "new_host_state": host.host_state,
                            "new_appr_state": host.appr_state,
                        },
                    )
                except Exception as commit_error:
                    # 提交失败，回滚事务
                    await session.rollback()
                    logger.error(
                        f"主机状态更新提交失败: {host_id}",
                        extra={
                            "host_id": host_id,
                            "error_type": type(commit_error).__name__,
                            "error_message": str(commit_error),
                        },
                        exc_info=True,
                    )
                    raise
            else:
                # 状态没有改变，直接返回当前状态
                logger.debug(
                    f"主机状态未改变，跳过更新: {host_id}",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host.host_state,
                        "current_appr_state": host.appr_state,
                    },
                )
                # ✅ 在会话关闭前保存需要返回的数据
                try:
                    updated_time_str = (
                        cast(datetime, host.updated_time).isoformat()
                        if host.updated_time
                        else None
                    )
                except Exception as attr_error:
                    # 如果访问 updated_time 失败，记录警告但不抛出异常
                    logger.warning(
                        f"访问 host.updated_time 失败: {host_id}",
                        extra={
                            "host_id": host_id,
                            "error_type": type(attr_error).__name__,
                            "error_message": str(attr_error),
                        },
                    )
                    updated_time_str = None

                result = {
                    "id": host.id,
                    "host_state": host.host_state,
                    "appr_state": host.appr_state,
                    "updated_time": updated_time_str,
                }
                logger.info(
                    "主机状态更新成功（状态未改变）",
                    extra={
                        "host_id": host_id,
                        "current_host_state": host.host_state,
                        "current_appr_state": host.appr_state,
                    },
                )
                # ✅ 在会话关闭前返回，避免访问已关闭的会话对象
                return result

            # ✅ 状态已改变，在会话关闭前返回结果
            try:
                updated_time_str = (
                    cast(datetime, host.updated_time).isoformat()
                    if host.updated_time
                    else None
                )
            except Exception as attr_error:
                # 如果访问 updated_time 失败，记录警告但不抛出异常
                logger.warning(
                    f"访问 host.updated_time 失败: {host_id}",
                    extra={
                        "host_id": host_id,
                        "error_type": type(attr_error).__name__,
                        "error_message": str(attr_error),
                    },
                )
                updated_time_str = None

            result = {
                "id": host.id,
                "host_state": host.host_state,
                "appr_state": host.appr_state,
                "updated_time": updated_time_str,
            }
            return result

    @handle_service_errors(
        error_message="更新主机心跳失败",
        error_code="UPDATE_HEARTBEAT_FAILED",
    )
    async def update_heartbeat(self, host_id: str) -> dict:
        """更新主机心跳时间

        Args:
            host_id: 主机ID

        Returns:
            更新后的心跳信息

        Raises:
            BusinessError: 主机不存在或更新失败时
        """
        try:
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            raise BusinessError(
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 使用工具函数验证主机存在
            host = await validate_host_exists(session, HostRec, host_id_int, locale="zh_CN")

            # ✅ WebSocket 更新数据时无需设置 updated_by 更新人
            # ✅ 不手动设置 updated_time，让数据库自动更新（通过 onupdate=func.now()）
            # 只需要提交事务，数据库会自动更新 updated_time

            await session.commit()
            await session.refresh(host)

            logger.info(
                "主机心跳更新成功",
                extra={
                    "host_id": host_id,
                    "updated_time": cast(datetime, host.updated_time).isoformat(),
                },
            )

            return {
                "host_id": host_id,
                "heartbeat_at": cast(datetime, host.updated_time).isoformat(),
            }

    async def update_heartbeat_silent(self, host_id: str) -> bool:
        """静默更新主机心跳时间（用于WebSocket）

        此方法专为 WebSocket 心跳监控设计，失败时不记录 ERROR 日志。
        适用于 host_id 可能不在数据库中的场景。

        Args:
            host_id: 主机ID

        Returns:
            True: 更新成功
            False: 更新失败（主机不存在或ID格式无效）

        Note:
            - 不抛出异常，仅返回成功/失败状态
            - 不记录 ERROR 日志
            - 失败是预期行为，不影响 WebSocket 心跳监控
        """
        try:
            # 验证 ID 格式
            host_id_int = int(host_id)
        except (ValueError, TypeError):
            # ID 格式无效，静默失败
            return False

        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = select(HostRec).where(
                    and_(
                        HostRec.id == host_id_int,
                        HostRec.del_flag == 0,
                    )
                )

                result = await session.execute(stmt)
                host = result.scalar_one_or_none()

                if not host:
                    # 主机不存在，静默失败
                    return False

                # ✅ WebSocket 更新数据时无需设置 updated_by 更新人
                # ✅ 不手动设置 updated_time，让数据库自动更新（通过 onupdate=func.now()）
                # 只需要提交事务，数据库会自动更新 updated_time
                await session.commit()

                return True

        except Exception:
            # 数据库操作失败，静默失败
            return False

    async def update_tcp_state(self, host_id: str, tcp_state: int) -> bool:
        """更新主机TCP连接状态

        Args:
            host_id: 主机ID (对应 HostRec.id 或 mg_id)
            tcp_state: TCP状态码
                - 0: 关闭 (连接断开)
                - 1: 等待 (心跳超时)
                - 2: 监听 (连接建立成功)

        Returns:
            True: 更新成功
            False: 更新失败（主机不存在或ID格式无效）

        Note:
            - 用于 WebSocket 连接生命周期管理
            - 静默失败，不记录 ERROR 日志
        """
        try:
            # 验证 tcp_state 取值范围
            if tcp_state not in (0, 1, 2):
                logger.warning(
                    f"无效的 tcp_state 值: {tcp_state}",
                    extra={"host_id": host_id, "valid_values": [0, 1, 2]},
                )
                return False

            # 尝试将 host_id 转为整数
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                # 如果 host_id 不是整数，尝试通过 mg_id 查询
                session_factory = mariadb_manager.get_session()
                async with session_factory() as session:
                    stmt = select(HostRec).where(
                        and_(
                            HostRec.mg_id == host_id,
                            HostRec.del_flag == 0,
                        )
                    )
                    result = await session.execute(stmt)
                    host = result.scalar_one_or_none()

                    if not host:
                        return False

                    host_id_int = host.id

            # 更新 tcp_state
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                # ✅ 修复：不手动设置 updated_time，让 onupdate=func.now() 自动更新
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(tcp_state=tcp_state)  # 移除手动设置的 updated_time
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"TCP状态已更新: host_id={host_id}, tcp_state={tcp_state}",
                        extra={
                            "host_id": host_id,
                            "tcp_state": tcp_state,
                            "tcp_state_name": {0: "关闭", 1: "等待", 2: "监听"}.get(tcp_state),
                        },
                    )
                    return True
                logger.warning(
                    f"TCP状态更新无匹配行: host_id={host_id}, tcp_state={tcp_state}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "tcp_state": tcp_state,
                        "reason": "记录不存在或已删除",
                    },
                )
                return False

        except Exception as e:
            logger.error(
                f"更新TCP状态失败: host_id={host_id}, tcp_state={tcp_state}, 错误: {e!s}",
                exc_info=True,
            )
            return False

    async def update_agent_version(self, host_id: str, agent_version: str) -> bool:
        """更新 Agent 版本号

        Args:
            host_id: 主机ID（字符串，转换为整数）
            agent_version: Agent 版本号（最大长度10）

        Returns:
            是否更新成功
        """
        try:
            # 验证版本号长度
            if len(agent_version) > 10:
                logger.warning(
                    f"Agent版本号长度超过限制: host_id={host_id}, version={agent_version}, length={len(agent_version)}",
                    extra={
                        "host_id": host_id,
                        "agent_version": agent_version,
                        "version_length": len(agent_version),
                    },
                )
                # 截断到10个字符
                agent_version = agent_version[:10]

            # 转换 host_id 为整数
            try:
                host_id_int = int(host_id)
            except (ValueError, TypeError):
                logger.error(
                    f"Host ID 格式错误: host_id={host_id}",
                    extra={
                        "host_id": host_id,
                        "error": "not a valid integer",
                    },
                )
                return False

            # 更新 agent_ver
            session_factory = mariadb_manager.get_session()
            async with session_factory() as session:
                stmt = (
                    update(HostRec)
                    .where(
                        and_(
                            HostRec.id == host_id_int,
                            HostRec.del_flag == 0,
                        )
                    )
                    .values(agent_ver=agent_version)
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"Agent版本号已更新: host_id={host_id}, agent_version={agent_version}",
                        extra={
                            "host_id": host_id,
                            "agent_version": agent_version,
                        },
                    )
                    return True
                logger.warning(
                    f"Agent版本号更新无匹配行: host_id={host_id}, agent_version={agent_version}",
                    extra={
                        "host_id": host_id,
                        "host_id_int": host_id_int,
                        "agent_version": agent_version,
                        "reason": "记录不存在或已删除",
                    },
                )
                return False

        except Exception as e:
            logger.error(
                f"更新Agent版本号失败: host_id={host_id}, agent_version={agent_version}, 错误: {e!s}",
                exc_info=True,
            )
            return False

    @handle_service_errors(
        error_message="查询重试 VNC 列表失败",
        error_code="GET_RETRY_VNC_LIST_FAILED",
    )
    async def get_retry_vnc_list(self, user_id: str) -> List[RetryVNCHostInfo]:
        """查询需要重试的 VNC 连接列表

        业务逻辑：
        1. 查询 host_exec_log 表，条件：
           - user_id = 入参的user_id
           - case_state != 2（非成功状态）
           - del_flag = 0（未删除）
        2. 获取这些记录的 host_id
        3. 查询 host_rec 表对应的主机信息
        4. 返回 host_id（主机ID）和 host_acct（重命名为 user_name）

        Args:
            user_id: 用户ID

        Returns:
            重试 VNC 主机信息列表
        """
        logger.info(
            "查询重试 VNC 列表",
            extra={
                "user_id": user_id,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # ✅ 优化：使用 JOIN 查询，一次查询获取所有数据，减少数据库往返
            # 合并原来的两次查询为一次 JOIN 查询
            stmt = (
                select(HostRec.id, HostRec.host_ip, HostRec.host_acct)
                .select_from(
                    HostExecLog.__table__.join(
                        HostRec.__table__,
                        HostExecLog.host_id == HostRec.id,
                    )
                )
                .where(
                    and_(
                        HostExecLog.user_id == user_id,
                        HostExecLog.case_state != 2,  # 非成功状态
                        HostExecLog.del_flag == 0,
                        HostRec.del_flag == 0,
                    )
                )
                .distinct()  # 去重，同一个 host_id 可能有多条失败记录
            )

            result = await session.execute(stmt)
            hosts = result.fetchall()

            # 如果没有需要重试的主机，直接返回空列表
            if not hosts:
                logger.info(
                    "没有需要重试的 VNC 连接",
                    extra={
                        "user_id": user_id,
                    },
                )
                return []

            logger.info(
                "查询到需要重试的主机列表（JOIN 查询优化）",
                extra={
                    "user_id": user_id,
                    "host_count": len(hosts),
                },
            )

            # 构建返回结果
            retry_vnc_list = [
                RetryVNCHostInfo(
                    host_id=str(host[0]),  # ✅ 转换为字符串避免精度丢失
                    host_ip=host[1] or "",  # 防止 None 值
                    user_name=host[2] or "",  # host_acct 重命名为 user_name
                )
                for host in hosts
            ]

            logger.info(
                "查询重试 VNC 列表成功",
                extra={
                    "user_id": user_id,
                    "total": len(retry_vnc_list),
                },
            )

            return retry_vnc_list

    @handle_service_errors(
        error_message="释放主机失败",
        error_code="RELEASE_HOSTS_FAILED",
    )
    async def release_hosts(self, user_id: str, host_list: List[str]) -> int:
        """释放主机 - 逻辑删除执行日志记录

        逻辑删除 host_exec_log 表中符合条件的记录（设置 del_flag = 1）：
        - user_id = 入参的 user_id
        - host_id IN (host_list)
        - del_flag = 0（只删除未删除的记录）

        Args:
            user_id: 用户ID
            host_list: 主机ID列表

        Returns:
            更新的记录数
        """
        logger.info(
            "开始释放主机（逻辑删除）",
            extra={
                "user_id": user_id,
                "host_count": len(host_list),
                "host_list": host_list,
            },
        )

        # 将 host_list 中的字符串转换为整数
        try:
            host_ids = [int(host_id) for host_id in host_list]
        except (ValueError, TypeError) as e:
            logger.error(
                "主机ID格式转换失败",
                extra={
                    "user_id": user_id,
                    "host_list": host_list,
                    "error": str(e),
                },
            )
            raise BusinessError(
                message="主机ID格式无效",
                error_code="INVALID_HOST_ID",
                code=400,
            )

        logger.info(
            "主机ID转换完成",
            extra={
                "user_id": user_id,
                "host_ids": host_ids,
            },
        )

        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            # 构建逻辑删除语句（UPDATE del_flag = 1）
            stmt = (
                update(HostExecLog)
                .where(
                    and_(
                        HostExecLog.user_id == user_id,
                        HostExecLog.host_id.in_(host_ids),
                        HostExecLog.del_flag == 0,  # 只更新未删除的记录
                    )
                )
                .values(del_flag=1)  # 设置为已删除
            )

            logger.info(
                "执行逻辑删除操作",
                extra={
                    "user_id": user_id,
                    "host_ids": host_ids,
                    "operation": "UPDATE del_flag = 1",
                },
            )

            # 执行更新
            result = await session.execute(stmt)
            await session.commit()

            updated_count = result.rowcount

            logger.info(
                "释放主机完成（逻辑删除）",
                extra={
                    "user_id": user_id,
                    "host_count": len(host_list),
                    "updated_count": updated_count,
                },
            )

            return updated_count
