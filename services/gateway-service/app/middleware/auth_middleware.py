"""
Authentication middleware module

Responsible for validating JWT tokens in requests, calling Auth Service for token verification.

Uses pure ASGI (no BaseHTTPMiddleware) so all code runs in the same async context
and avoids "no current event loop in thread" in worker threads (e.g. AnyIO).
"""

import json
import os
import sys
from typing import Any, Callable, Dict, Optional

import httpx

try:
    from shared.common.cache import redis_manager
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from shared.common.cache import redis_manager
    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse

logger = get_logger(__name__)


def _get_header(scope: dict, name: str) -> Optional[str]:
    """Get header value from ASGI scope (case-insensitive)."""
    name_lower = name.lower().encode("utf-8")
    for k, v in scope.get("headers", []):
        if k.lower() == name_lower:
            return v.decode("utf-8", errors="replace")
    return None


def _get_locale_from_scope(scope: dict) -> str:
    """Get language preference from ASGI scope."""
    accept_language = _get_header(scope, "Accept-Language")
    return parse_accept_language(accept_language)


async def _send_json_response(send: Callable, status: int, content: Dict[str, Any]) -> None:
    """Send JSON response via ASGI."""
    body = json.dumps(content, ensure_ascii=False).encode("utf-8")
    headers = [(b"content-type", b"application/json; charset=utf-8")]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def _build_error_body(
    scope: dict,
    code: int,
    message: str,
    error_code: str,
    message_key: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build error response body for ASGI send."""
    locale = _get_locale_from_scope(scope)
    r = ErrorResponse(
        code=code,
        message=message,
        message_key=message_key,
        error_code=error_code,
        details=details,
        locale=locale,
    )
    return r.model_dump()


class AuthMiddleware:
    """Authentication middleware (pure ASGI).

    Intercepts all requests and validates JWT token validity.
    Does not inherit BaseHTTPMiddleware; runs in the same async context to avoid event loop issues.
    Sets scope["auth_user"] on success; downstream should use request.scope.get("auth_user").
    """

    # Public path whitelist (no authentication required)
    public_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/test-error",  # For testing
            # Authentication endpoints (public access)
            "/api/v1/auth/admin/login",
            "/api/v1/auth/device/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",  # ✅ Token refresh endpoint
            "/api/v1/auth/auto-refresh",  # ✅ Auto-renewal endpoint
            "/api/v1/auth/introspect",  # Token verification endpoint
            # ⚠️ WebSocket routes need authentication check at route level
        }

    browser_plugin_prefixes = [
        "/api/v1/host/hosts",  # Browser plugin - host management interface (includes /hosts/vnc/*)
    ]

    def __init__(self, app: Any) -> None:
        self.app = app
        from app.core.config import settings

        self.auth_service_url = settings.auth_service_url.rstrip("/")
        self.timeout = httpx.Timeout(
            settings.auth_middleware_timeout,
            connect=settings.auth_middleware_connect_timeout,
        )
        logger.info(
            "Authentication middleware initialization completed",
            extra={"auth_service_url": self.auth_service_url},
        )

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        if _get_header(scope, "X-User-Info"):
            client_host = (scope.get("client") or ("unknown",))[0]
            logger.warning(
                "Detected X-User-Info header from client, removed (security measure)",
                extra={
                    "path": path,
                    "method": method,
                    "client_host": client_host,
                    "hint": "X-User-Info can only be added by Gateway after token verification",
                },
            )

        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        auth_header = _get_header(scope, "Authorization")
        has_token = bool(auth_header)
        is_public = self._is_public_path(path)
        client_host = (scope.get("client") or ("unknown",))[0]

        logger.info(
            "Authentication middleware processing request",
            extra={
                "path": path,
                "method": method,
                "is_public_path": is_public,
                "has_authorization_header": has_token,
                "client_host": client_host,
            },
        )

        if is_public:
            await self.app(scope, receive, send)
            return

        if not auth_header:
            logger.warning(
                "Protected path missing Authorization header",
                extra={"path": path, "method": method, "client_host": client_host},
            )
            body = _build_error_body(
                scope, 401, "Missing authentication token",
                "UNAUTHORIZED", message_key="error.auth.missing_token",
                details={"path": path, "method": method, "hint": "Please add Authorization: Bearer <token>"},
            )
            await _send_json_response(send, 401, body)
            return

        if not auth_header.startswith("Bearer "):
            body = _build_error_body(
                scope, 401, "Invalid authentication token format",
                "UNAUTHORIZED", message_key="error.auth.invalid_token_format",
                details={"path": path, "method": method, "expected_format": "Bearer <token>"},
            )
            await _send_json_response(send, 401, body)
            return

        token = auth_header[7:]
        token_preview = token[:8] + "..." if len(token) > 8 else token
        user_info = await self._verify_token(token, path, method)

        if not user_info:
            body = _build_error_body(
                scope, 401, "Invalid or expired authentication token",
                "UNAUTHORIZED", message_key="error.auth.token_invalid_or_expired",
                details={"path": path, "method": method, "hint": "Please login again to get new token"},
            )
            await _send_json_response(send, 401, body)
            return

        if isinstance(user_info, dict) and "error_type" in user_info:
            error_type = user_info["error_type"]
            if error_type == "timeout":
                body = _build_error_body(
                    scope, 504, "Authentication service response timeout, please try again later",
                    "GATEWAY_TIMEOUT", message_key="error.auth.service_timeout",
                    details={"path": path, "method": method, "service": "auth-service"},
                )
                await _send_json_response(send, 504, body)
                return
            if error_type == "connection_error":
                body = _build_error_body(
                    scope, 503, "Authentication service temporarily unavailable, please try again later",
                    "SERVICE_UNAVAILABLE", message_key="error.auth.service_unavailable",
                    details={"path": path, "method": method, "service": "auth-service"},
                )
                await _send_json_response(send, 503, body)
                return
            if error_type == "request_error":
                body = _build_error_body(
                    scope, 502, "Authentication service request failed",
                    "BAD_GATEWAY", message_key="error.auth.service_error",
                    details={"path": path, "method": method, "service": "auth-service"},
                )
                await _send_json_response(send, 502, body)
                return
            body = _build_error_body(
                scope, 500, "Internal error occurred during authentication",
                "INTERNAL_ERROR", message_key="error.internal",
                details={"path": path, "method": method},
            )
            await _send_json_response(send, 500, body)
            return

        scope["auth_user"] = user_info
        logger.info(
            "Token verification successful, access allowed",
            extra={
                "path": path,
                "method": method,
                "id": user_info.get("id"),
                "username": user_info.get("username"),
                "user_type": user_info.get("user_type"),
            },
        )
        await self.app(scope, receive, send)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public

        Args:
            path: Request path

        Returns:
            Whether path is public
        """
        # Remove query parameters
        clean_path = path.split("?")[0]

        # Remove trailing slash (but keep root path "/")
        if clean_path != "/" and clean_path.endswith("/"):
            clean_path = clean_path.rstrip("/")

        # Check exact match
        if clean_path in self.public_paths:
            return True

        # ✅ Check prefix match (for documentation paths and browser plugin interfaces)
        # Supported prefix match path patterns:
        # - /docs, /redoc, /openapi.json (documentation paths)
        # - /api/v1/host/hosts, /api/v1/host/vnc (browser plugin interfaces)
        prefix_match_paths = {
            "/docs",  # Swagger UI
            "/redoc",  # ReDoc
            "/openapi.json",  # OpenAPI spec
        }

        # Check documentation path prefix match
        for prefix_path in prefix_match_paths:
            if clean_path.startswith(prefix_path):
                return True

        # ✅ Check browser plugin interface prefix match (all browser plugin interfaces do not require authentication)
        for prefix_path in self.browser_plugin_prefixes:
            if clean_path.startswith(prefix_path):
                return True

        return False

    async def _verify_token(
        self, token: str, request_path: str = "", request_method: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Verify JWT token

        Call Auth Service's introspect endpoint to verify token

        Args:
            token: JWT access token
            request_path: Request path (for logging)
            request_method: Request method (for logging)

        Returns:
            User information, returns None if verification fails
            Special case: returns dict with error_type to indicate service error
        """
        token_preview = token[:8] + "..." if len(token) > 8 else token

        try:
            # Call Auth Service's introspect endpoint to verify token
            introspect_url = f"{self.auth_service_url}/api/v1/auth/introspect"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    introspect_url,
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()

                    # Check if token is valid
                    if result.get("code") == 200:
                        data = result.get("data", {})
                        if data.get("active"):
                            # ✅ Use id field uniformly, return None if missing (401)
                            user_id = data.get("id")

                            if not user_id:
                                logger.warning(
                                    "Token verification successful but id is empty",
                                    extra={
                                        "data_keys": list(data.keys()),
                                        "token_preview": token_preview,
                                        "request_path": request_path,
                                        "request_method": request_method,
                                        "reason": "missing_id",
                                        "auth_service_response": {
                                            "code": result.get("code"),
                                            "message": result.get("message"),
                                            "data": data,
                                        },
                                        "hint": "Auth Service returned empty id, token is invalid",
                                    },
                                )
                                return None  # Return None to indicate verification failure

                            # ✅ Check if user/host has been deleted (read from Redis)
                            try:
                                user_type = data.get("user_type", "user")

                                if user_id:
                                    # Determine Redis key prefix based on user_type
                                    if user_type == "device":
                                        # device type represents host
                                        deleted_key = f"deleted:host:{user_id}"
                                    else:
                                        # admin or other types represent user
                                        deleted_key = f"deleted:user:{user_id}"

                                    # Check if deleted marker exists in Redis
                                    is_deleted = await redis_manager.exists(deleted_key)

                                    if is_deleted:
                                        logger.warning(
                                            "User/host corresponding to token has been deleted",
                                            extra={
                                                "id": user_id,
                                                "user_type": user_type,
                                                "deleted_key": deleted_key,
                                                "request_path": request_path,
                                                "request_method": request_method,
                                            },
                                        )
                                        return None  # Return None to indicate verification failure,
                                        # will trigger 401 response
                            except Exception as redis_error:
                                # Log warning when Redis operation fails, but continue verification (degradation)
                                logger.warning(
                                    "Redis deletion check failed, continuing token verification",
                                    extra={
                                        "id": user_id,
                                        "user_type": data.get("user_type"),
                                        "error": str(redis_error),
                                        "error_type": type(redis_error).__name__,
                                        "request_path": request_path,
                                        "hint": (
                                            "When Redis is unavailable, skip deletion check and "
                                            "continue token verification (degradation)"
                                        ),
                                    },
                                )
                                # Continue execution, don't reject all requests due to Redis failure

                            # ✅ Construct user information (use id field uniformly)
                            user_info = {
                                "id": user_id,
                                "username": data.get("username"),
                                "user_type": data.get("user_type"),
                                "active": data.get("active"),
                            }

                            logger.info(
                                "Token verification successful - Auth Service returned valid user information",
                                extra={
                                    "id": user_info.get("id"),
                                    "username": user_info.get("username"),
                                    "user_type": user_info.get("user_type"),
                                    "token_preview": token_preview,
                                    "request_path": request_path,
                                },
                            )
                            return user_info
                        logger.warning(
                            "Token verification failed - token not active",
                            extra={
                                "token_preview": token_preview,
                                "active": data.get("active"),
                                "request_path": request_path,
                                "request_method": request_method,
                                "reason": "token_inactive",
                                "auth_service_response": {
                                    "code": result.get("code"),
                                    "message": result.get("message"),
                                    "data_keys": list(data.keys()) if isinstance(data, dict) else [],
                                },
                                "hint": ("Token may be expired, blacklisted, or malformed"),
                            },
                        )
                    else:
                        logger.warning(
                            "Token verification failed - Auth Service returned error code",
                            extra={
                                "response_code": result.get("code"),
                                "response_message": result.get("message"),
                                "token_preview": token_preview,
                                "request_path": request_path,
                                "request_method": request_method,
                                "reason": "auth_service_error",
                            },
                        )
                else:
                    logger.warning(
                        "Token verification failed - HTTP status code abnormal",
                        extra={
                            "status_code": response.status_code,
                            "response_text": response.text[:200] if response.text else "",
                            "token_preview": token_preview,
                            "request_path": request_path,
                            "request_method": request_method,
                            "reason": "http_error",
                        },
                    )
                return None

        except httpx.TimeoutException as e:
            logger.error(
                "Token verification timeout - Auth Service response timeout",
                extra={
                    "auth_service_url": self.auth_service_url,
                    "timeout_config": str(self.timeout),
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_type": "timeout",
                    "error_detail": str(e),
                },
            )
            # Return special marker to indicate timeout error
            return {"error_type": "timeout"}

        except httpx.ConnectError as e:
            logger.error(
                "Unable to connect to authentication service - network connection failed",
                extra={
                    "auth_service_url": self.auth_service_url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_detail": "connection_refused_or_network_unreachable",
                },
            )
            # Return special marker to indicate connection error
            return {"error_type": "connection_error"}

        except httpx.HTTPStatusError as e:
            logger.error(
                "Auth Service returned HTTP error status",
                extra={
                    "status_code": e.response.status_code,
                    "response_text": e.response.text[:200] if e.response.text else "",
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_type": "http_status_error",
                },
            )
            return None

        except httpx.RequestError as e:
            logger.error(
                "Auth Service request error",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
            )
            return {"error_type": "request_error"}

        except Exception as e:
            logger.error(
                "Token verification exception - unexpected error",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
                exc_info=True,
            )
            return None

