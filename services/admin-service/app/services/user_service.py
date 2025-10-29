"""
用户管理服务

提供用户CRUD操作、搜索和分页功能
"""

import time

from typing import List, Optional, Tuple

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from sqlalchemy import func, select

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import get_***REMOVED***word_hash
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import get_***REMOVED***word_hash

logger = get_logger(__name__)


class UserService:
    """用户管理服务类"""

    @handle_service_errors(error_message="创建用户失败", error_code="USER_CREATE_FAILED")
    @monitor_operation(operation_name="user_create", record_duration=True)
    async def create_user(self, user_data: UserCreate) -> User:
        """创建用户

        Args:
            user_data: 用户创建数据

        Returns:
            创建的用户对象

        Raises:
            BusinessError: 用户账号或邮箱已存在
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as db_session:
            # 检查用户账号是否已存在
            stmt = select(User).where(User.user_account == user_data.username, User.del_flag == 0)
            result = await db_session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise BusinessError(
                    message=f"用户账号已存在: {user_data.username}",
                    error_code="USER_ALREADY_EXISTS",
                )

            # 检查邮箱是否已存在
            if user_data.email:
                stmt = select(User).where(User.email == user_data.email, User.del_flag == 0)
                result = await db_session.execute(stmt)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    raise BusinessError(
                        message=f"邮箱已存在: {user_data.email}",
                        error_code="EMAIL_ALREADY_EXISTS",
                    )

            # 创建新用户
            ***REMOVED***word_hash = get_***REMOVED***word_hash(user_data.***REMOVED***word)

            # 生成新的用户ID（使用雪花算法或其他ID生成策略）

            new_user_id = int(time.time() * 1000)  # 简单的时间戳ID，生产环境应使用雪花算法

            new_user = User(
                id=new_user_id,
                user_account=user_data.username,
                user_name=user_data.username,  # 默认用户名称与账号相同
                email=user_data.email,
                user_pwd=***REMOVED***word_hash,
                state_flag=0 if user_data.is_active else 1,  # 0=启用, 1=停用
                del_flag=0,  # 0=使用中
            )

            db_session.add(new_user)
            await db_session.commit()
            await db_session.refresh(new_user)

            logger.info(
                "用户创建成功",
                extra={
                    "operation": "create_user",
                    "user_id": new_user.id,
                    "user_account": new_user.user_account,
                },
            )
            return new_user

    @handle_service_errors(error_message="获取用户失败", error_code="USER_GET_FAILED")
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            用户对象，如果不存在则返回None
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as db_session:
            stmt = select(User).where(User.id == user_id, User.del_flag == 0)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(
                    "用户不存在",
                    extra={
                        "operation": "get_user_by_id",
                        "user_id": user_id,
                    },
                )
                return None

            logger.info(
                "获取用户成功",
                extra={
                    "operation": "get_user_by_id",
                    "user_id": user_id,
                    "user_account": user.user_account,
                },
            )
            return user

    @handle_service_errors(error_message="更新用户失败", error_code="USER_UPDATE_FAILED")
    @monitor_operation(operation_name="user_update", record_duration=True)
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息

        Args:
            user_id: 用户ID
            user_data: 用户更新数据

        Returns:
            更新后的用户对象，如果不存在则返回None

        Raises:
            BusinessError: 邮箱已被其他用户使用
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as db_session:
            # 获取用户
            stmt = select(User).where(User.id == user_id, User.del_flag == 0)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(
                    "用户不存在",
                    extra={
                        "operation": "update_user",
                        "user_id": user_id,
                    },
                )
                return None

            # 检查邮箱是否被其他用户使用
            if user_data.email and user_data.email != user.email:
                stmt = select(User).where(
                    User.email == user_data.email,
                    User.id != user_id,
                    User.del_flag == 0,
                )
                result = await db_session.execute(stmt)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    raise BusinessError(
                        message=f"邮箱已被使用: {user_data.email}",
                        error_code="EMAIL_ALREADY_EXISTS",
                    )

            # 更新用户信息
            if user_data.email is not None:
                user.email = user_data.email
            if user_data.***REMOVED***word is not None:
                user.user_pwd = get_***REMOVED***word_hash(user_data.***REMOVED***word)
            if user_data.is_active is not None:
                user.state_flag = 0 if user_data.is_active else 1  # 0=启用, 1=停用

            await db_session.commit()
            await db_session.refresh(user)

            logger.info(
                "用户更新成功",
                extra={
                    "operation": "update_user",
                    "user_id": user.id,
                    "user_account": user.user_account,
                },
            )
            return user

    @handle_service_errors(error_message="删除用户失败", error_code="USER_DELETE_FAILED")
    @monitor_operation(operation_name="user_delete", record_duration=True)
    async def delete_user(self, user_id: int) -> bool:
        """删除用户（软删除）

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        session_factory = mariadb_manager.get_session()
        async with session_factory() as db_session:
            # 获取用户
            stmt = select(User).where(User.id == user_id, User.del_flag == 0)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(
                    "用户不存在",
                    extra={
                        "operation": "delete_user",
                        "user_id": user_id,
                    },
                )
                return False

            # 软删除
            user.del_flag = 1  # 1=删除
            await db_session.commit()

            logger.info(
                "用户删除成功",
                extra={
                    "operation": "delete_user",
                    "user_id": user.id,
                    "user_account": user.user_account,
                },
            )
            return True

    @handle_service_errors(error_message="获取用户列表失败", error_code="USER_LIST_FAILED")
    @monitor_operation(operation_name="user_list", record_duration=True)
    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[User], int]:
        """获取用户列表（分页）

        Args:
            page: 页码（从1开始）
            page_size: 每页大小
            search: 搜索关键词（用户账号、用户名称或邮箱）
            is_active: 是否激活状态过滤

        Returns:
            (用户列表, 总数)
        """
        logger.info("开始执行用户列表查询", extra={"page": page, "page_size": page_size})
        session_factory = mariadb_manager.get_session()
        async with session_factory() as db_session:
            # 获取总数
            count_stmt = select(func.count(User.id)).where(User.del_flag == 0)
            count_result = await db_session.execute(count_stmt)
            total = count_result.scalar() or 0
            logger.info(f"总数查询成功: {total}")

            # 主查询 - 只做最基本的查询
            offset_val = (page - 1) * page_size
            stmt = select(User).where(User.del_flag == 0).order_by(User.id.desc()).offset(offset_val).limit(page_size)

            logger.info(f"主查询SQL: {stmt}")

            # 执行查询
            result = await db_session.execute(stmt)
            users = result.scalars().all()

            logger.info(
                "获取用户列表成功",
                extra={
                    "operation": "list_users",
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "user_count": len(users),
                    "search": search,
                    "is_active": is_active,
                },
            )
            return list(users), total


# 全局服务实例
_user_service_instance: Optional[UserService] = None


def get_user_service() -> UserService:
    """获取用户服务实例（单例模式）"""
    global _user_service_instance

    if _user_service_instance is None:
        _user_service_instance = UserService()

    return _user_service_instance
