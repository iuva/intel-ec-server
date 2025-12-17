"""外部接口调用客户端

提供统一的外部接口调用功能，包括：
1. Token 获取和缓存管理
2. 带认证的外部接口调用
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

# 使用 try-except 方式处理路径导入
try:
    from app.models.sys_user import SysUser

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.http_client import get_http_client
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.models.sys_user import SysUser

    from shared.common.cache import redis_manager
    from shared.common.database import mariadb_manager
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.http_client import get_http_client
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# Token 缓存锁（防止并发请求）
_token_lock = asyncio.Lock()

# Token 缓存键前缀
TOKEN_CACHE_KEY_PREFIX = "external_api_token"


def get_user_id_from_request(request) -> Optional[int]:
    """从请求头获取 user_id（Gateway 传递的）

    支持两种方式：
    1. 从 X-User-Info header 解析（JSON格式，包含 user_id 字段）
    2. 从单独的 id 或 userid header 获取（如果 Gateway 传递了）

    Args:
        request: FastAPI Request 对象

    Returns:
        int: 用户ID，如果未找到返回 None
    """
    # 方式1: 尝试从 X-User-Info header 解析
    user_info_header = request.headers.get("X-User-Info")
    if user_info_header:
        try:
            user_info = json.loads(user_info_header)
            if isinstance(user_info, dict):
                user_id = user_info.get("user_id")
                if user_id:
                    # 确保返回整数类型
                    return int(user_id) if user_id else None
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(
                "解析 X-User-Info header 失败",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    # 方式2: 尝试从单独的 id 或 userid header 获取
    user_id = request.headers.get("id") or request.headers.get("userid") or request.headers.get("X-User-Id")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            logger.warning(
                "解析 user_id header 失败",
                extra={
                    "user_id": user_id,
                },
            )

    return None


async def get_external_api_token(user_id: int, locale: str = "zh_CN") -> Dict[str, Any]:
    """获取外部 API 访问令牌（带缓存和并发控制）

    业务逻辑：
    1. 根据 user_id 查询 sys_user 表获取 email
    2. 先从 Redis 缓存获取 token
    3. 如果缓存为空，使用锁防止并发请求，重新获取 token
    4. 请求 POST {external_api_url}/api/v1/auth/login，body 为 {"email": user_email}
    5. 返回参数 {"access_token": "...", "token_type": "bearer", "expires_in": "15552000"}
    6. 根据 expires_in 的值存入 Redis 缓存

    Args:
        user_id: 当前登录管理后台用户的ID（sys_user.id）
        locale: 语言偏好，用于错误消息多语言处理

    Returns:
        dict: Token 信息，包含：
            - access_token: 访问令牌
            - token_type: Token 类型（如 "bearer"）
            - expires_in: 过期时间（秒）

    Raises:
        BusinessError: 获取 token 失败时
    """
    # 1. 根据 user_id 查询 sys_user 表获取 email
    session_factory = mariadb_manager.get_session()
    async with session_factory() as session:
        from sqlalchemy import select

        user_stmt = select(SysUser).where(
            SysUser.id == user_id,
            SysUser.del_flag == 0,
        )
        user_result = await session.execute(user_stmt)
        sys_user = user_result.scalar_one_or_none()

        if not sys_user:
            raise BusinessError(
                message=f"用户不存在（ID: {user_id}）",
                message_key="error.user.not_found",
                error_code="USER_NOT_FOUND",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=400,
                details={"user_id": user_id},
            )

        if not sys_user.email:
            raise BusinessError(
                message=f"用户邮箱为空（ID: {user_id}）",
                message_key="error.user.email_empty",
                error_code="USER_EMAIL_EMPTY",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=400,
                details={"user_id": user_id},
            )

        user_email = sys_user.email

    # 2. 先从 Redis 缓存获取 token
    cache_key = f"{TOKEN_CACHE_KEY_PREFIX}:{user_email}"
    cached_token_data = await redis_manager.get(cache_key)
    if cached_token_data and isinstance(cached_token_data, dict):
        access_token = cached_token_data.get("access_token")
        if access_token:
            logger.debug(
                "从缓存获取外部 API token",
                extra={
                    "user_id": user_id,
                    "user_email": user_email,
                    "cache_key": cache_key,
                },
            )
            # 返回完整的 token 信息（从缓存中获取）
            return {
                "access_token": access_token,
                "token_type": cached_token_data.get("token_type", "bearer"),
                "expires_in": cached_token_data.get("expires_in"),
            }

    # 3. 缓存为空，使用锁防止并发请求
    async with _token_lock:
        # 双重检查：在获取锁后再次检查缓存（可能其他协程已经获取了 token）
        cached_token_data = await redis_manager.get(cache_key)
        if cached_token_data and isinstance(cached_token_data, dict):
            access_token = cached_token_data.get("access_token")
            if access_token:
                logger.debug(
                    "从缓存获取外部 API token（锁内双重检查）",
                    extra={
                        "user_id": user_id,
                        "user_email": user_email,
                        "cache_key": cache_key,
                    },
                )
                # 返回完整的 token 信息（从缓存中获取）
                return {
                    "access_token": access_token,
                    "token_type": cached_token_data.get("token_type", "bearer"),
                    "expires_in": cached_token_data.get("expires_in"),
                }

        # 4. 请求登录接口获取 token
        external_api_url = os.getenv("EXTERNAL_API_URL", "http://hardware-service:8000")
        login_url = f"{external_api_url}/api/v1/auth/login"
        request_body = {"email": user_email}

        logger.info(
            "请求外部 API token",
            extra={
                "user_id": user_id,
                "user_email": user_email,
                "login_url": login_url,
            },
        )

        http_client = get_http_client()

        try:
            response = await http_client.request("POST", login_url, json=request_body)

            if response["status_code"] not in (200, 201):
                error_msg = (
                    response["body"].get("message", "未知错误")
                    if isinstance(response["body"], dict)
                    else str(response["body"])
                )
                raise BusinessError(
                    message=f"获取外部 API token 失败: {error_msg}",
                    message_key="error.external_api.token_failed",
                    error_code="EXTERNAL_API_TOKEN_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "login_url": login_url,
                        "status_code": response["status_code"],
                        "response": response["body"],
                    },
                )

            # 5. 解析响应数据
            response_body = response["body"]
            if not isinstance(response_body, dict):
                raise BusinessError(
                    message="外部 API token 响应格式错误：响应不是 JSON 格式",
                    message_key="error.external_api.token_invalid_response",
                    error_code="EXTERNAL_API_TOKEN_INVALID_RESPONSE",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                )

            access_token = response_body.get("access_token")
            token_type = response_body.get("token_type", "bearer")
            expires_in = response_body.get("expires_in")

            if not access_token:
                raise BusinessError(
                    message="外部 API token 响应缺少 access_token 字段",
                    message_key="error.external_api.token_missing",
                    error_code="EXTERNAL_API_TOKEN_MISSING",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                )

            # 6. 根据 expires_in 的值存入 Redis 缓存
            # expires_in 可能是字符串或整数，需要转换
            try:
                if isinstance(expires_in, str):
                    expire_seconds = int(expires_in)
                elif isinstance(expires_in, (int, float)):
                    expire_seconds = int(expires_in)
                else:
                    # 默认过期时间：15552000 秒（约 180 天）
                    expire_seconds = 15552000
                    logger.warning(
                        "无法解析 expires_in，使用默认值",
                        extra={
                            "user_id": user_id,
                            "user_email": user_email,
                            "expires_in": expires_in,
                            "default_expire": expire_seconds,
                        },
                    )
            except (ValueError, TypeError) as e:
                # 解析失败，使用默认值
                expire_seconds = 15552000
                logger.warning(
                    "解析 expires_in 失败，使用默认值",
                    extra={
                        "user_id": user_id,
                        "user_email": user_email,
                        "expires_in": expires_in,
                        "default_expire": expire_seconds,
                        "error": str(e),
                    },
                )

            # 存储 token 数据到缓存
            token_data = {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }

            cache_success = await redis_manager.set(cache_key, token_data, expire=expire_seconds)
            if cache_success:
                logger.info(
                    "外部 API token 已缓存",
                    extra={
                        "user_id": user_id,
                        "user_email": user_email,
                        "cache_key": cache_key,
                        "expire_seconds": expire_seconds,
                    },
                )
            else:
                logger.warning(
                    "外部 API token 缓存失败",
                    extra={
                        "user_id": user_id,
                        "user_email": user_email,
                        "cache_key": cache_key,
                    },
                )

            # 返回完整的 token 信息
            return {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }

        except BusinessError:
            raise
        except Exception as e:
            logger.error(
                "获取外部 API token 异常",
                extra={
                    "user_id": user_id,
                    "user_email": user_email,
                    "login_url": login_url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message=f"获取外部 API token 异常: {str(e)}",
                message_key="error.external_api.token_error",
                error_code="EXTERNAL_API_TOKEN_ERROR",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=500,
                details={
                    "user_id": user_id,
                    "error": str(e),
                },
            )


async def call_external_api(
    method: str,
    url_path: str,
    request=None,
    user_id: Optional[int] = None,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    locale: str = "zh_CN",
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """调用外部接口（带认证）

    业务逻辑：
    1. 从请求头获取 user_id（如果未提供）
    2. 获取外部 API token（带缓存）
    3. 添加请求头 Authorization: token_type + 空格 + access_token
    4. 调用外部接口

    Args:
        method: HTTP 方法（GET, POST, PUT, DELETE 等）
        url_path: 请求路径（相对于 external_api_url）
        request: FastAPI Request 对象（用于从请求头获取 user_id）
        user_id: 当前登录管理后台用户的ID（可选，如果提供则优先使用）
        json_data: 请求体 JSON 数据（可选）
        params: 查询参数（可选）
        headers: 额外的请求头（可选）
        locale: 语言偏好，用于错误消息多语言处理
        timeout: 请求超时时间（秒）

    Returns:
        dict: 响应数据，包含 status_code 和 body

    Raises:
        BusinessError: 接口调用失败时
    """
    # 1. 获取 user_id（优先使用参数，否则从请求头获取）
    if user_id is None:
        if request is None:
            raise BusinessError(
                message="无法获取用户ID：未提供 user_id 参数且 request 对象为空",
                message_key="error.external_api.user_id_missing",
                error_code="USER_ID_MISSING",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=400,
            )
        user_id = get_user_id_from_request(request)
        if user_id is None:
            raise BusinessError(
                message="无法从请求头获取用户ID",
                message_key="error.external_api.user_id_not_found",
                error_code="USER_ID_NOT_FOUND",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=400,
            )

    # 2. 获取外部 API token（带缓存），返回完整的 token 信息
    token_info = await get_external_api_token(user_id, locale=locale)
    access_token = token_info["access_token"]
    token_type = token_info.get("token_type", "bearer")

    # 3. 构建请求头（Authorization: token_type + 空格 + access_token）
    full_headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    if headers:
        full_headers.update(headers)

    # 4. 构建完整 URL
    external_api_url = os.getenv("EXTERNAL_API_URL", "http://hardware-service:8000")
    full_url = f"{external_api_url}{url_path}"

    logger.info(
        "调用外部接口",
        extra={
            "method": method,
            "url": full_url,
            "user_id": user_id,
            "has_json_data": json_data is not None,
            "has_params": params is not None,
        },
    )

    http_client = get_http_client()

    try:
        # 5. 调用外部接口
        response = await http_client.request(
            method, full_url, json=json_data, params=params, headers=full_headers, timeout=timeout
        )

        logger.info(
            "外部接口调用完成",
            extra={
                "method": method,
                "url": full_url,
                "status_code": response.get("status_code"),
                "user_id": user_id,
            },
        )

        return response

    except Exception as e:
        logger.error(
            "调用外部接口异常",
            extra={
                "method": method,
                "url": full_url,
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise BusinessError(
            message=f"调用外部接口异常: {str(e)}",
            message_key="error.external_api.call_failed",
            error_code="EXTERNAL_API_CALL_FAILED",
            code=ServiceErrorCodes.HOST_OPERATION_FAILED,
            http_status_code=500,
            details={
                "method": method,
                "url": full_url,
                "error": str(e),
            },
        )
