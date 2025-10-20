"""
用户管理 API 端点
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.user_service import UserService, get_user_service

# 使用 try-except 方式处理路径导入
try:
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse, SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=SuccessResponse, status_code=HTTP_200_OK)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    search: Optional[str] = Query(None, description="搜索关键词（用户账号、用户名称或邮箱）"),
    is_active: Optional[bool] = Query(None, description="是否激活状态过滤"),
    user_service: UserService = Depends(get_user_service),
):
    """获取用户列表（分页）

    Args:
        request: 请求对象
        page: 页码（从1开始）
        page_size: 每页大小（1-100）
        search: 搜索关键词（用户账号、用户名称或邮箱）
        is_active: 是否激活状态过滤
        user_service: 用户服务实例

    Returns:
        用户列表和分页信息
    """
    try:
        users, total = await user_service.list_users(
            page=page, page_size=page_size, search=search, is_active=is_active
        )

        # 构建响应数据
        user_list = [UserResponse.model_validate(user) for user in users]

        response_data = UserListResponse(users=user_list, total=total, page=page, page_size=page_size)

        return SuccessResponse(data=response_data.model_dump(), message="获取用户列表成功")

    except BusinessError as e:
        logger.error(f"获取用户列表失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message=e.message,
                error_code=e.error_code,
            ).model_dump(),
        )
    except (ValueError, TypeError) as e:
        logger.error(f"获取用户列表异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="获取用户列表失败",
                error_code="USER_LIST_FAILED",
            ).model_dump(),
        )


@router.post("", response_model=SuccessResponse, status_code=HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    """创建用户

    Args:
        user_data: 用户创建数据
        user_service: 用户服务实例

    Returns:
        创建的用户信息
    """
    try:
        user = await user_service.create_user(user_data)
        user_response = UserResponse.model_validate(user)

        return SuccessResponse(data=user_response.model_dump(), message="用户创建成功")

    except BusinessError as e:
        logger.error(f"创建用户失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message=e.message,
                error_code=e.error_code,
            ).model_dump(),
        )
    except (ValueError, TypeError) as e:
        logger.error(f"创建用户异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="创建用户失败",
                error_code="USER_CREATE_FAILED",
            ).model_dump(),
        )


@router.get("/{user_id}", response_model=SuccessResponse, status_code=HTTP_200_OK)
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
):
    """获取用户详情

    Args:
        user_id: 用户ID
        user_service: 用户服务实例

    Returns:
        用户详细信息
    """
    try:
        user = await user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    code=HTTP_404_NOT_FOUND,
                    message=f"用户不存在: ID={user_id}",
                    error_code="USER_NOT_FOUND",
                ).model_dump(),
            )

        user_response = UserResponse.model_validate(user)
        return SuccessResponse(data=user_response.model_dump(), message="获取用户成功")

    except HTTPException:
        raise
    except BusinessError as e:
        logger.error(f"获取用户失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message=e.message,
                error_code=e.error_code,
            ).model_dump(),
        )
    except (ValueError, TypeError) as e:
        logger.error(f"获取用户异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="获取用户失败",
                error_code="USER_GET_FAILED",
            ).model_dump(),
        )


@router.put("/{user_id}", response_model=SuccessResponse, status_code=HTTP_200_OK)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
):
    """更新用户信息

    Args:
        user_id: 用户ID
        user_data: 用户更新数据
        user_service: 用户服务实例

    Returns:
        更新后的用户信息
    """
    try:
        user = await user_service.update_user(user_id, user_data)

        if not user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    code=HTTP_404_NOT_FOUND,
                    message=f"用户不存在: ID={user_id}",
                    error_code="USER_NOT_FOUND",
                ).model_dump(),
            )

        user_response = UserResponse.model_validate(user)
        return SuccessResponse(data=user_response.model_dump(), message="用户更新成功")

    except HTTPException:
        raise
    except BusinessError as e:
        logger.error(f"更新用户失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message=e.message,
                error_code=e.error_code,
            ).model_dump(),
        )
    except (ValueError, TypeError) as e:
        logger.error(f"更新用户异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="更新用户失败",
                error_code="USER_UPDATE_FAILED",
            ).model_dump(),
        )


@router.delete("/{user_id}", response_model=SuccessResponse, status_code=HTTP_200_OK)
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
):
    """删除用户（软删除）

    Args:
        user_id: 用户ID
        user_service: 用户服务实例

    Returns:
        删除结果
    """
    try:
        success = await user_service.delete_user(user_id)

        if not success:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    code=HTTP_404_NOT_FOUND,
                    message=f"用户不存在: ID={user_id}",
                    error_code="USER_NOT_FOUND",
                ).model_dump(),
            )

        return SuccessResponse(data={"user_id": user_id}, message="用户删除成功")

    except HTTPException:
        raise
    except BusinessError as e:
        logger.error(f"删除用户失败: {e.message}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message=e.message,
                error_code=e.error_code,
            ).model_dump(),
        )
    except (ValueError, TypeError) as e:
        logger.error(f"删除用户异常: {e!s}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code=HTTP_400_BAD_REQUEST,
                message="删除用户失败",
                error_code="USER_DELETE_FAILED",
            ).model_dump(),
        )


# 注意：异常处理器需要在 FastAPI 应用层面添加，而不是路由器层面
# 在 main.py 中的 create_app() 函数中添加以下代码：
#
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     """处理请求验证错误，提供详细的错误信息"""
#     # 记录详细的验证错误信息
#     logger.warning(
#         "请求验证失败",
#         extra={
#             "operation": "request_validation",
#             "method": request.method,
#             "url": str(request.url),
#             "client_ip": request.client.host if request.client else "unknown",
#             "user_agent": request.headers.get("user-agent", "unknown"),
#             "validation_errors": [
#                 {
#                     "field": ".".join(str(loc) for loc in error["loc"]),
#                     "message": error["msg"],
#                     "error_type": error["type"],
#                     "input_value": str(error.get("input", ""))[:100]  # 限制输入值长度
#                 }
#                 for error in exc.errors()
#             ],
#             "error_count": len(exc.errors())
#         }
#     )
#
#     # 构建详细的错误响应
#     field_errors = [
#         {
#             "field": ".".join(str(loc) for loc in error["loc"]),
#             "message": error["msg"],
#             "error_type": error["type"]
#         }
#         for error in exc.errors()
#     ]
#
#     error_response = ErrorResponse(
#         code=HTTP_422_UNPROCESSABLE_ENTITY,
#         message="请求参数验证失败",
#         error_code="VALIDATION_ERROR",
#         details={
#             "field_errors": field_errors,
#             "total_errors": len(field_errors)
#         }
#     )
#
#     return JSONResponse(
#         status_code=HTTP_422_UNPROCESSABLE_ENTITY,
#         content=error_response.model_dump()
#     )
