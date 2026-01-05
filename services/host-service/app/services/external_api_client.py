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

from sqlalchemy import select

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


def _sanitize_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """脱敏响应头中的敏感信息

    Args:
        headers: 原始响应头（可能为 None）

    Returns:
        脱敏后的响应头
    """
    if not headers:
        return {}
    safe_headers = headers.copy()
    # 转换为小写键以便查找
    safe_headers = headers.copy()

    sensitive_keys = ["authorization", "set-cookie", "cookie"]
    for key in list(safe_headers.keys()):
        if key.lower() in sensitive_keys:
            safe_headers[key] = "***（已脱敏）"
    return safe_headers


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
                # ✅ 统一使用 id 字段
                user_id = user_info.get("id")
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


async def get_external_api_token(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    locale: str = "zh_CN",
) -> Dict[str, Any]:
    """获取外部 API 访问令牌（带缓存和并发控制）

    业务逻辑：
    1. **确定 user_email**：
       - 如果提供了 `email` 参数，直接使用该 email，不查询数据库（性能优化）
       - 如果未提供 `email`，根据 `user_id` 查询 sys_user 表获取 email
    2. 先从 Redis 缓存获取 token（缓存键基于 email）
    3. 如果缓存为空，使用锁防止并发请求，重新获取 token
    4. 请求 POST {external_api_url}/api/v1/auth/login，body 为 {"email": user_email}
    5. 返回参数 {"access_token": "...", "token_type": "bearer", "expires_in": "15552000"}
    6. 根据 expires_in 的值存入 Redis 缓存

    性能优化：
    - 如果提供了 `email` 参数，跳过数据库查询，直接使用该 email 获取 token
    - Token 缓存基于 email，避免重复请求外部接口
    - 使用分布式锁防止并发请求导致重复获取 token

    Args:
        user_id: 当前登录管理后台用户的ID（sys_user.id），如果提供了 email 则可以为 None
        email: 用户邮箱（可选）。如果提供，将直接使用该 email，不查询数据库，提高性能
        locale: 语言偏好，用于错误消息多语言处理

    Returns:
        dict: Token 信息，包含：
            - access_token: 访问令牌
            - token_type: Token 类型（如 "bearer"）
            - expires_in: 过期时间（秒）

    Raises:
        BusinessError: 获取 token 失败时，包括：
            - EMAIL_MISSING: 未提供 email 且 user_id 为空
            - USER_NOT_FOUND: 用户不存在（当未提供 email 时）
            - USER_EMAIL_EMPTY: 用户邮箱为空（当未提供 email 时）
            - 外部接口调用失败

    Example:
        ```python
        # 方式1：提供 email，不查询数据库（推荐）
        token_info = await get_external_api_token(email="user@example.com")

        # 方式2：提供 user_id，查询数据库获取 email
        token_info = await get_external_api_token(user_id=123)
        ```
    """
    # 1. 确定 user_email：优先使用提供的 email，否则根据 user_id 查询数据库
    if email:
        # ✅ 如果提供了 email，直接使用，不查询数据库，不验证用户
        user_email = email
        logger.debug(
            "使用提供的 email 进行外部接口认证（跳过数据库验证）",
            extra={
                "email": email,
                "user_id": user_id,
            },
        )
    else:
        # 如果没有提供 email，根据 user_id 查询 sys_user 表获取 email
        if user_id is None:
            raise BusinessError(
                message="无法获取用户邮箱：未提供 email 参数且 user_id 为空",
                message_key="error.external_api.email_missing",
                error_code="EMAIL_MISSING",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=400,
            )

        # ✅ 只有在未提供 email 时才查询数据库
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
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
                return {
                    "access_token": access_token,
                    "token_type": cached_token_data.get("token_type", "bearer"),
                    "expires_in": cached_token_data.get("expires_in"),
                }

        # 4. 请求登录接口获取 token
        external_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
        login_url = f"{external_api_url}/api/v1/auth/login"
        request_body = {"email": user_email}

        # 记录请求参数日志 - 使用 structured logging
        logger.bind(
            method="POST",
            url=login_url,
            user_id=user_id,
            user_email=user_email,
            request_body=request_body,
        ).debug("获取外部 API token - 请求参数")

        http_client = get_http_client()

        # 用于异常处理时记录响应信息
        response = None
        status_code = None

        try:
            response = await http_client.request("POST", login_url, json=request_body)

            # 获取响应信息
            response_headers = response.get("headers") or {}
            response_body = response.get("body")
            status_code = response.get("status_code")
            raw_body = response.get("raw_body")

            safe_response_headers = _sanitize_headers(response_headers)

            # 使用 raw_body 如果 body 为空或处理异常
            body_to_log = response_body if response_body is not None else raw_body

            # 记录响应日志 - 使用 structured logging
            logger.bind(
                method="POST",
                url=login_url,
                status_code=status_code,
                user_id=user_id,
                response_headers=safe_response_headers,
                response_body=body_to_log
            ).debug("获取外部 API token - 响应结果")

            if status_code not in (200, 201):
                # 提取错误消息
                error_msg = "未知错误"
                if response_body and isinstance(response_body, dict):
                    error_msg = response_body.get("message", str(response_body))
                elif response_body:
                    error_msg = str(response_body)
                elif raw_body:
                    error_msg = str(raw_body)
                else:
                    error_msg = f"空响应 (status_code: {status_code})"

                raise BusinessError(
                    message=f"获取外部 API token 失败: {error_msg}",
                    message_key="error.external_api.token_failed",
                    error_code="EXTERNAL_API_TOKEN_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "login_url": login_url,
                        "status_code": status_code,
                        "response_body": body_to_log,
                        "detail": error_msg,  # ✅ 添加 detail 字段供 i18n 使用
                    },
                )

            # 5. 解析响应数据
            if not response_body or not isinstance(response_body, dict):
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
            try:
                if isinstance(expires_in, (int, float)):
                    expire_seconds = int(expires_in)
                elif isinstance(expires_in, str) and expires_in.isdigit():
                    expire_seconds = int(expires_in)
                else:
                    expire_seconds = 15552000
                    logger.warning("无法解析 expires_in，使用默认值", extra={"expires_in": expires_in})
            except Exception:
                expire_seconds = 15552000
                logger.warning("解析 expires_in 失败，使用默认值", extra={"expires_in": expires_in})

            # 存储 token 数据到缓存
            token_data = {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }

            cache_success = await redis_manager.set(cache_key, token_data, expire=expire_seconds)
            if not cache_success:
                logger.warning("外部 API token 缓存失败", extra={"cache_key": cache_key})

            # 返回完整的 token 信息
            return {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }

        except BusinessError:
            raise
        except Exception as e:
            # 记录异常详细信息
            error_details = {
                "user_id": user_id,
                "user_email": user_email,
                "method": "POST",
                "url": login_url,
                "request_body": request_body,
                "error": str(e),
                "error_type": type(e).__name__,
            }

            if response:
                # 获取响应信息（如果已有）
                try:
                    resp_headers = _sanitize_headers(response.get("headers")) or {}
                    resp_body = response.get("body") if response.get("body") is not None else response.get("raw_body")

                    error_details.update({
                        "status_code": response.get("status_code"),
                        "response_headers": resp_headers,
                        "response_body": resp_body,
                    })
                except Exception:
                    ***REMOVED***

            # ✅ 确保 detail 字段存在（供 i18n 使用）
            if "detail" not in error_details:
                error_details["detail"] = str(e)

            logger.error("获取外部 API token 异常", extra=error_details, exc_info=True)

            raise BusinessError(
                message=f"获取外部 API token 异常: {str(e)}",
                message_key="error.external_api.token_error",
                error_code="EXTERNAL_API_TOKEN_ERROR",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=500,
                details=error_details,
            )


async def call_external_api(
    method: str,
    url_path: str,
    request=None,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    locale: str = "zh_CN",
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """调用外部接口（带认证）

    业务逻辑：
    1. **确定认证信息**：
       - 如果提供了 `email` 参数，直接使用该 email 获取 token，不查询数据库（性能优化）
       - 如果未提供 `email`，从请求头获取 user_id，然后查询数据库获取 email
    2. 获取外部 API token（带缓存和并发控制）
    3. 添加请求头 Authorization: token_type + 空格 + access_token
    4. 调用外部接口
    5. 记录请求和响应日志（包含请求参数、响应状态码和响应体）

    性能优化：
    - 如果提供了 `email` 参数，跳过数据库查询，直接使用该 email 获取 token
    - Token 缓存基于 email，避免重复请求外部接口
    - 使用统一的 HTTP 客户端，支持连接池复用和 SSL 配置

    Args:
        method: HTTP 方法（GET, POST, PUT, DELETE 等）
        url_path: 请求路径（相对于 external_api_url，例如 "/api/v1/hardware/hosts"）
        request: FastAPI Request 对象（用于从请求头获取 user_id）
        user_id: 当前登录管理后台用户的ID（可选，如果提供了 email 则可以为 None）
        email: 用户邮箱（可选）。如果提供，将直接使用该 email 获取 token，不查询数据库，提高性能
        json_data: 请求体 JSON 数据（可选）
        params: 查询参数（可选）
        headers: 额外的请求头（可选），会与默认请求头合并
        locale: 语言偏好，用于错误消息多语言处理
        timeout: 请求超时时间（秒），默认 30.0 秒

    Returns:
        dict: 响应数据，包含：
            - status_code: HTTP 状态码
            - body: 响应体（已解析的 JSON 数据）
            - raw_body: 原始响应体（字符串）
            - headers: 响应头

    Raises:
        BusinessError: 接口调用失败时，包括：
            - USER_ID_MISSING: 未提供 user_id 且 request 对象为空（当未提供 email 时）
            - USER_ID_NOT_FOUND: 无法从请求头获取用户ID（当未提供 email 时）
            - 外部接口调用失败（网络错误、超时等）
            - 外部接口返回非 200 状态码

    Example:
        ```python
        # 方式1：提供 email，不查询数据库（推荐）
        response = await call_external_api(
            method="GET",
            url_path="/api/v1/hardware/hosts",
            email="user@example.com",
            params={"tc_id": "123", "skip": 0, "limit": 100}
        )

        # 方式2：提供 user_id，查询数据库获取 email
        response = await call_external_api(
            method="GET",
            url_path="/api/v1/hardware/hosts",
            request=fastapi_request,
            user_id=123,
            params={"tc_id": "123", "skip": 0, "limit": 100}
        )
        ```
    """
    # 1. 获取 user_id（如果未提供 email）
    if email is None:
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

    # 2. 获取外部 API token（如果提供了 email，则不查询数据库）
    token_info = await get_external_api_token(user_id=user_id, email=email, locale=locale)
    access_token = token_info["access_token"]
    token_type = token_info.get("token_type", "bearer")

    # 3. 构建请求头
    full_headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    if headers:
        full_headers.update(headers)

    # 4. 构建完整 URL
    external_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
    full_url = f"{external_api_url}{url_path}"

    # 5. 记录请求参数日志
    safe_headers = _sanitize_headers(full_headers)

    logger.bind(
        method=method,
        url=full_url,
        url_path=url_path,
        user_id=user_id,
        headers=safe_headers,
        params=params,
        json_data=json_data,
        timeout=timeout
    ).debug("调用外部接口 - 请求参数")

    http_client = get_http_client()

    try:
        # 6. 调用外部接口
        response = await http_client.request(
            method, full_url, json=json_data, params=params, headers=full_headers, timeout=timeout
        )

        # 7. 记录响应日志
        response_headers = response.get("headers", {})
        response_body = response.get("body")
        raw_body = response.get("raw_body")
        status_code = response.get("status_code")

        body_to_log = response_body if response_body is not None else raw_body

        safe_response_headers = _sanitize_headers(response_headers)

        logger.bind(
            method=method,
            url=full_url,
            status_code=status_code,
            response_headers=safe_response_headers,
            response_body=body_to_log,
            user_id=user_id
        ).debug("调用外部接口 - 响应结果")

        return response

    except Exception as e:
        logger.error(
            "调用外部接口异常",
            extra={
                "method": method,
                "url": full_url,
                "user_id": user_id,
                "params": params,
                "json_data": json_data,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise
