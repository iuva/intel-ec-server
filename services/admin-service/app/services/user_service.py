"""
用户管理服务

提供用户CRUD操作、搜索和分页功能
"""

from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import get_***REMOVED***word_hash
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.security import get_***REMOVED***word_hash

logger = get_logger(__name__)


class UserService:
    """用户管理服务类"""

    async def create_user(self, user_data: UserCreate) -> User:
        """创建用户

        Args:
            user_data: 用户创建数据

        Returns:
            创建的用户对象

        Raises:
            BusinessError: 用户名或邮箱已存在
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 检查用户名是否已存在
                stmt = select(User).where(User.username == user_data.username, User.is_deleted.is_(False))
                result = await db_session.execute(stmt)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    raise BusinessError(
                        message=f"用户名已存在: {user_data.username}",
                        error_code="USER_ALREADY_EXISTS",
                    )

                # 检查邮箱是否已存在
                stmt = select(User).where(User.email == user_data.email, User.is_deleted.is_(False))
                result = await db_session.execute(stmt)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    raise BusinessError(
                        message=f"邮箱已存在: {user_data.email}",
                        error_code="EMAIL_ALREADY_EXISTS",
                    )

                # 创建新用户
                ***REMOVED***word_hash = get_***REMOVED***word_hash(user_data.***REMOVED***word)
                new_user = User(
                    username=user_data.username,
                    email=user_data.email,
                    ***REMOVED***word_hash=***REMOVED***word_hash,
                    is_active=user_data.is_active,
                    is_superuser=user_data.is_superuser,
                )

                db_session.add(new_user)
                await db_session.commit()
                await db_session.refresh(new_user)

                logger.info(f"用户创建成功: {new_user.username} (ID: {new_user.id})")
                return new_user

        except BusinessError:
            raise
        except (ValueError, TypeError, OSError) as e:
            logger.error(f"创建用户失败: {e!s}")
            raise BusinessError(message="创建用户失败", error_code="USER_CREATE_FAILED")

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            用户对象，如果不存在则返回None
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                stmt = select(User).where(User.id == user_id, User.is_deleted.is_(False))
                result = await db_session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在: ID={user_id}")
                    return None

                return user

        except (ValueError, TypeError, OSError) as e:
            logger.error(f"获取用户失败: {e!s}")
            raise BusinessError(message="获取用户失败", error_code="USER_GET_FAILED")

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
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 获取用户
                stmt = select(User).where(User.id == user_id, User.is_deleted.is_(False))
                result = await db_session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在: ID={user_id}")
                    return None

                # 检查邮箱是否被其他用户使用
                if user_data.email and user_data.email != user.email:
                    stmt = select(User).where(
                        User.email == user_data.email,
                        User.id != user_id,
                        User.is_deleted.is_(False),
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
                    user.***REMOVED***word_hash = get_***REMOVED***word_hash(user_data.***REMOVED***word)
                if user_data.is_active is not None:
                    user.is_active = user_data.is_active
                if user_data.is_superuser is not None:
                    user.is_superuser = user_data.is_superuser

                await db_session.commit()
                await db_session.refresh(user)

                logger.info(f"用户更新成功: {user.username} (ID: {user.id})")
                return user

        except BusinessError:
            raise
        except (ValueError, TypeError, OSError) as e:
            logger.error(f"更新用户失败: {e!s}")
            raise BusinessError(message="更新用户失败", error_code="USER_UPDATE_FAILED")

    async def delete_user(self, user_id: int) -> bool:
        """删除用户（软删除）

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 获取用户
                stmt = select(User).where(User.id == user_id, User.is_deleted.is_(False))
                result = await db_session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在: ID={user_id}")
                    return False

                # 软删除
                user.is_deleted = True
                await db_session.commit()

                logger.info(f"用户删除成功: {user.username} (ID: {user.id})")
                return True

        except (ValueError, TypeError, OSError) as e:
            logger.error(f"删除用户失败: {e!s}")
            raise BusinessError(message="删除用户失败", error_code="USER_DELETE_FAILED")

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
            search: 搜索关键词（用户名或邮箱）
            is_active: 是否激活状态过滤

        Returns:
            (用户列表, 总数)
        """
        try:
            session_factory = mariadb_manager.get_session()
            async with session_factory() as db_session:
                # 构建查询
                stmt = select(User).where(User.is_deleted.is_(False))

                # 搜索过滤
                if search:
                    stmt = stmt.where(
                        or_(
                            User.username.like(f"%{search}%"),
                            User.email.like(f"%{search}%"),
                        )
                    )

                # 状态过滤
                if is_active is not None:
                    stmt = stmt.where(User.is_active == is_active)

                # 获取总数
                count_stmt = select(func.count()).select_from(stmt.subquery())
                result = await db_session.execute(count_stmt)
                total = result.scalar_one()

                # 分页
                offset = (page - 1) * page_size
                stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)

                # 执行查询
                result = await db_session.execute(stmt)
                users = result.scalars().all()

                logger.info(f"获取用户列表成功: page={page}, page_size={page_size}, total={total}")
                return list(users), total

        except (ValueError, TypeError, OSError) as e:
            logger.error(f"获取用户列表失败: {e!s}")
            raise BusinessError(message="获取用户列表失败", error_code="USER_LIST_FAILED")


# 全局服务实例
_user_service_instance: Optional[UserService] = None


def get_user_service() -> UserService:
    """获取用户服务实例（单例模式）"""
    global _user_service_instance

    if _user_service_instance is None:
        _user_service_instance = UserService()

    return _user_service_instance
