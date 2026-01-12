"""External API call client

Provides unified external API call functionality, including:
1. Token acquisition and cache management
2. External API calls with authentication
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

from sqlalchemy import select

# Use try-except to handle path imports
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

# Token cache lock (prevent concurrent requests)
_token_lock = asyncio.Lock()

# Token cache key prefix
TOKEN_CACHE_KEY_PREFIX = "external_api_token"

# ✅ Optimization: Module-level session factory cache
_session_factory_cache = None


def _get_session_factory():
    """Get session factory (module-level cache)

    ✅ Optimization: Cache session factory to avoid repeated retrieval
    """
    global _session_factory_cache
    if _session_factory_cache is None:
        _session_factory_cache = mariadb_manager.get_session()
    return _session_factory_cache


def _sanitize_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize sensitive information in response headers

    Args:
        headers: Original response headers (may be None)

    Returns:
        Sanitized response headers
    """
    if not headers:
        return {}
    safe_headers = headers.copy()
    # Convert to lowercase keys for lookup
    safe_headers = headers.copy()

    sensitive_keys = ["authorization", "set-cookie", "cookie"]
    for key in list(safe_headers.keys()):
        if key.lower() in sensitive_keys:
            safe_headers[key] = "*** (sanitized)"
    return safe_headers


def get_user_id_from_request(request) -> Optional[int]:
    """Get user_id from request headers (***REMOVED***ed by Gateway)

    Supports two methods:
    1. Parse from X-User-Info header (JSON format, contains user_id field)
    2. Get from separate id or userid header (if Gateway ***REMOVED***ed it)

    Args:
        request: FastAPI Request object

    Returns:
        int: User ID, returns None if not found
    """
    # Method 1: Try to parse from X-User-Info header
    user_info_header = request.headers.get("X-User-Info")
    if user_info_header:
        try:
            user_info = json.loads(user_info_header)
            if isinstance(user_info, dict):
                # ✅ Unified use of id field
                user_id = user_info.get("id")
                if user_id:
                    # Ensure integer type is returned
                    return int(user_id) if user_id else None
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse X-User-Info header",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    # Method 2: Try to get from separate id or userid header
    user_id = request.headers.get("id") or request.headers.get("userid") or request.headers.get("X-User-Id")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            logger.warning(
                "Failed to parse user_id header",
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
    """Get external API access token (with cache and concurrency control)

    Business logic:
    1. **Determine user_email**:
       - If `email` parameter is provided, use it directly without querying database (performance optimization)
       - If `email` is not provided, query sys_user table based on `user_id` to get email
    2. First get token from Redis cache (cache key based on email)
    3. If cache is empty, use lock to prevent concurrent requests, re-acquire token
    4. Request POST {external_api_url}/api/v1/auth/login, body is {"email": user_email}
    5. Return parameters {"access_token": "...", "token_type": "bearer", "expires_in": "15552000"}
    6. Store in Redis cache based on expires_in value

    Performance optimization:
    - If `email` parameter is provided, skip database query, directly use that email to get token
    - Token cache based on email, avoid repeated external API requests
    - Use distributed lock to prevent concurrent requests causing duplicate token acquisition

    Args:
        user_id: ID of currently logged-in admin backend user (sys_user.id), can be None if email is provided
        email: User email (optional). If provided, will directly use this email without querying
               database, improving performance
        locale: Language preference for error message internationalization

    Returns:
        dict: Token information, contains:
            - access_token: Access token
            - token_type: Token type (e.g., "bearer")
            - expires_in: Expiration time (seconds)

    Raises:
        BusinessError: When token acquisition fails, including:
            - EMAIL_MISSING: Email not provided and user_id is empty
            - USER_NOT_FOUND: User does not exist (when email is not provided)
            - USER_EMAIL_EMPTY: User email is empty (when email is not provided)
            - External API call failed

    Example:
        ```python
        # Method 1: Provide email, no database query (recommended)
        token_info = await get_external_api_token(email="user@example.com")

        # Method 2: Provide user_id, query database to get email
        token_info = await get_external_api_token(user_id=123)
        ```
    """
    # 1. Determine user_email: Prefer provided email, otherwise query database based on user_id
    if email:
        # ✅ If email is provided, use it directly without querying database or validating user
        user_email = email
        logger.debug(
            "Using provided email for external API authentication (skip database validation)",
            extra={
                "email": email,
                "user_id": user_id,
            },
        )
    else:
        # If email is not provided, query sys_user table based on user_id to get email
        if user_id is None:
            raise BusinessError(
                message="Unable to get user email: email parameter not provided and user_id is empty",
                message_key="error.external_api.email_missing",
                error_code="EMAIL_MISSING",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=400,
            )

        # ✅ Only query database when email is not provided (use cached session factory)
        session_factory = _get_session_factory()
        async with session_factory() as session:
            user_stmt = select(SysUser).where(
                SysUser.id == user_id,
                SysUser.del_flag == 0,
            )
            user_result = await session.execute(user_stmt)
            sys_user = user_result.scalar_one_or_none()

            if not sys_user:
                raise BusinessError(
                    message=f"User does not exist (ID: {user_id})",
                    message_key="error.user.not_found",
                    error_code="USER_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"user_id": user_id},
                )

            if not sys_user.email:
                raise BusinessError(
                    message=f"User email is empty (ID: {user_id})",
                    message_key="error.user.email_empty",
                    error_code="USER_EMAIL_EMPTY",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                    details={"user_id": user_id},
                )

            user_email = sys_user.email

    # 2. First get token from Redis cache
    cache_key = f"{TOKEN_CACHE_KEY_PREFIX}:{user_email}"
    cached_token_data = await redis_manager.get(cache_key)
    if cached_token_data and isinstance(cached_token_data, dict):
        access_token = cached_token_data.get("access_token")
        if access_token:
            logger.debug(
                "Get external API token from cache",
                extra={
                    "user_id": user_id,
                    "user_email": user_email,
                    "cache_key": cache_key,
                },
            )
            # Return complete token information (from cache)
            return {
                "access_token": access_token,
                "token_type": cached_token_data.get("token_type", "bearer"),
                "expires_in": cached_token_data.get("expires_in"),
            }

    # 3. Cache is empty, use lock to prevent concurrent requests
    async with _token_lock:
        # Double check: Check cache again after acquiring lock (other coroutine may have acquired token)
        cached_token_data = await redis_manager.get(cache_key)
        if cached_token_data and isinstance(cached_token_data, dict):
            access_token = cached_token_data.get("access_token")
            if access_token:
                logger.debug(
                    "Get external API token from cache (double check within lock)",
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

        # 4. Request login API to get token
        external_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
        login_url = f"{external_api_url}/api/v1/auth/login"
        request_body = {"email": user_email}

        # Log request parameters - use structured logging
        logger.bind(
            method="POST",
            url=login_url,
            user_id=user_id,
            user_email=user_email,
            request_body=request_body,
        ).debug("Get external API token - request parameters")

        http_client = get_http_client()

        # For recording response information in exception handling
        response = None
        status_code = None

        try:
            response = await http_client.request("POST", login_url, json=request_body)

            # Get response information
            response_headers = response.get("headers") or {}
            response_body = response.get("body")
            status_code = response.get("status_code")
            raw_body = response.get("raw_body")

            safe_response_headers = _sanitize_headers(response_headers)

            # Use raw_body if body is empty or processing exception
            body_to_log = response_body if response_body is not None else raw_body

            # Log response - use structured logging
            logger.bind(
                method="POST",
                url=login_url,
                status_code=status_code,
                user_id=user_id,
                response_headers=safe_response_headers,
                response_body=body_to_log,
            ).debug("Get external API token - response result")

            if status_code not in (200, 201):
                # Extract error message
                error_msg = "Unknown error"
                if response_body and isinstance(response_body, dict):
                    error_msg = response_body.get("message", str(response_body))
                elif response_body:
                    error_msg = str(response_body)
                elif raw_body:
                    error_msg = str(raw_body)
                else:
                    error_msg = f"Empty response (status_code: {status_code})"

                raise BusinessError(
                    message=f"Failed to get external API token: {error_msg}",
                    message_key="error.external_api.token_failed",
                    error_code="EXTERNAL_API_TOKEN_FAILED",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                    details={
                        "login_url": login_url,
                        "status_code": status_code,
                        "response_body": body_to_log,
                        "detail": error_msg,  # ✅ Add detail field for i18n use
                    },
                )

            # 5. Parse response data
            if not response_body or not isinstance(response_body, dict):
                raise BusinessError(
                    message="External API token response format error: response is not JSON format",
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
                    message="External API token response missing access_token field",
                    message_key="error.external_api.token_missing",
                    error_code="EXTERNAL_API_TOKEN_MISSING",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=500,
                )

            # 6. Store in Redis cache based on expires_in value
            try:
                if isinstance(expires_in, (int, float)):
                    expire_seconds = int(expires_in)
                elif isinstance(expires_in, str) and expires_in.isdigit():
                    expire_seconds = int(expires_in)
                else:
                    expire_seconds = 15552000
                    logger.warning("Unable to parse expires_in, using default value", extra={"expires_in": expires_in})
            except Exception:
                expire_seconds = 15552000
                logger.warning("Failed to parse expires_in, using default value", extra={"expires_in": expires_in})

            # Store token data to cache
            token_data = {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }

            cache_success = await redis_manager.set(cache_key, token_data, expire=expire_seconds)
            if not cache_success:
                logger.warning("External API token cache failed", extra={"cache_key": cache_key})

            # Return complete token information
            return {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }

        except BusinessError:
            raise
        except Exception as e:
            # Record detailed exception information
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
                # Get response information (if available)
                try:
                    resp_headers = _sanitize_headers(response.get("headers")) or {}
                    resp_body = response.get("body") if response.get("body") is not None else response.get("raw_body")

                    error_details.update(
                        {
                            "status_code": response.get("status_code"),
                            "response_headers": resp_headers,
                            "response_body": resp_body,
                        }
                    )
                except Exception:
                    ***REMOVED***

            # ✅ Ensure detail field exists (for i18n use)
            if "detail" not in error_details:
                error_details["detail"] = str(e)

            logger.error("Exception getting external API token", extra=error_details, exc_info=True)

            raise BusinessError(
                message=f"Exception getting external API token: {str(e)}",
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
    """Call external API (with authentication)

    Business logic:
    1. **Determine authentication information**:
       - If `email` parameter is provided, directly use that email to get token without querying
         database (performance optimization)
       - If `email` is not provided, get user_id from request headers, then query database to get email
    2. Get external API token (with cache and concurrency control)
    3. Add request header Authorization: token_type + space + access_token
    4. Call external API
    5. Log request and response (including request parameters, response status code and response body)

    Performance optimization:
    - If `email` parameter is provided, skip database query, directly use that email to get token
    - Token cache based on email, avoid repeated external API requests
    - Use unified HTTP client, support connection pool reuse and SSL configuration

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url_path: Request path (relative to external_api_url, e.g., "/api/v1/hardware/hosts")
        request: FastAPI Request object (used to get user_id from request headers)
        user_id: ID of currently logged-in admin backend user (optional, can be None if email is provided)
        email: User email (optional). If provided, will directly use this email to get token without
               querying database, improving performance
        json_data: Request body JSON data (optional)
        params: Query parameters (optional)
        headers: Additional request headers (optional), will be merged with default headers
        locale: Language preference for error message internationalization
        timeout: Request timeout (seconds), default 30.0 seconds

    Returns:
        dict: Response data, contains:
            - status_code: HTTP status code
            - body: Response body (parsed JSON data)
            - raw_body: Raw response body (string)
            - headers: Response headers

    Raises:
        BusinessError: When API call fails, including:
            - USER_ID_MISSING: user_id not provided and request object is empty (when email is not provided)
            - USER_ID_NOT_FOUND: Unable to get user ID from request headers (when email is not provided)
            - External API call failed (network error, timeout, etc.)
            - External API returned non-200 status code

    Example:
        ```python
        # Method 1: Provide email, no database query (recommended)
        response = await call_external_api(
            method="GET",
            url_path="/api/v1/hardware/hosts",
            email="user@example.com",
            params={"tc_id": "123", "skip": 0, "limit": 100}
        )

        # Method 2: Provide user_id, query database to get email
        response = await call_external_api(
            method="GET",
            url_path="/api/v1/hardware/hosts",
            request=fastapi_request,
            user_id=123,
            params={"tc_id": "123", "skip": 0, "limit": 100}
        )
        ```
    """
    # 1. Get user_id (if email is not provided)
    if email is None:
        if user_id is None:
            if request is None:
                raise BusinessError(
                    message="Unable to get user ID: user_id parameter not provided and request object is empty",
                    message_key="error.external_api.user_id_missing",
                    error_code="USER_ID_MISSING",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                )
            user_id = get_user_id_from_request(request)
            if user_id is None:
                raise BusinessError(
                    message="Unable to get user ID from request headers",
                    message_key="error.external_api.user_id_not_found",
                    error_code="USER_ID_NOT_FOUND",
                    code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                    http_status_code=400,
                )

    # 2. Get external API token (if email is provided, no database query)
    token_info = await get_external_api_token(user_id=user_id, email=email, locale=locale)
    access_token = token_info["access_token"]
    token_type = token_info.get("token_type", "bearer")

    # 3. Build request headers
    full_headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    if headers:
        full_headers.update(headers)

    # 4. Build complete URL
    external_api_url = os.getenv("HARDWARE_API_URL", "http://hardware-service:8000")
    full_url = f"{external_api_url}{url_path}"

    # 5. Log request parameters
    safe_headers = _sanitize_headers(full_headers)

    logger.bind(
        method=method,
        url=full_url,
        url_path=url_path,
        user_id=user_id,
        headers=safe_headers,
        params=params,
        json_data=json_data,
        timeout=timeout,
    ).debug("Call external API - request parameters")

    http_client = get_http_client()

    try:
        # 6. Call external API
        response = await http_client.request(
            method, full_url, json=json_data, params=params, headers=full_headers, timeout=timeout
        )

        # 7. Log response
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
            user_id=user_id,
        ).debug("Call external API - response result")

        return response

    except Exception as e:
        logger.error(
            "Exception calling external API",
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
