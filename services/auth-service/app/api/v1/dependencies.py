"""
API Dependency Injection

Provide dependency injection functions for service instances
"""

import os
import sys
from typing import Any, Dict, Optional

from fastapi import Request

from app.services.auth_service import AuthService

# Use try-except approach to handle path imports
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# Global service instance cache
_auth_service_instance: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get authentication service instance (singleton pattern)

    Returns:
        AuthService: Authentication service instance
    """
    global _auth_service_instance

    if _auth_service_instance is None:
        _auth_service_instance = AuthService()

    return _auth_service_instance


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user information (from X-User-Info header passed by Gateway)

    ✅ Architecture Notes:
    - All token validation is completed in Gateway, Gateway calls auth-service to validate token
    - After Gateway validation succeeds, user information is passed to backend services via X-User-Info header
    - Backend services no longer validate token, only read user information from X-User-Info header
    - If no X-User-Info header, return None (allowing optional authentication scenarios)

    ✅ Notes:
    - Use `id` field consistently
    - Support optional authentication (some endpoints allow unauthenticated access, such as device_login for auditing)
    - If X-User-Info header is missing, return None instead of error (optional authentication)

    Args:
        request: FastAPI request object

    Returns:
        Optional[Dict[str, Any]]: User information dictionary, containing:
            - id: User ID (consistent field)
            - username: Username
            - user_type: User type (admin/device/user)
            - permissions: Permission list
            - roles: Role list
        If no X-User-Info header, return None (optional authentication)

    Example:
        >>> @router.post("/device/login")
        >>> async def device_login(
        >>>     current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
        >>> ):
        >>>     if current_user:
        >>>         user_id = current_user.get("id")
    """
    try:
        import json

        # ✅ Get user information only from X-User-Info header passed by Gateway
        # Gateway has already validated the token in the authentication middleware
        # and stored user information in the X-User-Info header
        user_info_header = request.headers.get("X-User-Info")

        if not user_info_header:
            # ✅ If no X-User-Info header, return None (allowing optional authentication)
            logger.debug(
                "Request does not contain X-User-Info header (optional authentication)",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": (
                        "Request should be forwarded through Gateway, "
                        "Gateway will pass X-User-Info header after authentication"
                    ),
                },
            )
            return None

        # Parse user information JSON
        try:
            user_info = json.loads(user_info_header)

            # ✅ Use id field consistently
            user_id = user_info.get("id")
            if not user_id:
                logger.warning(
                    "Missing id field in X-User-Info header",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "user_info_keys": list(user_info.keys()),
                        "hint": "Gateway should ensure X-User-Info header contains id field",
                    },
                )
                # Even if id is missing, return user information (optional authentication)
                # Let business layer decide how to handle

            # ✅ Build unified user information dictionary
            result: Dict[str, Any] = {
                "id": str(user_id) if user_id else None,
                "username": user_info.get("username"),
                "user_type": user_info.get("user_type", "user"),
                "permissions": user_info.get("permissions", []),
                "roles": user_info.get("roles", []),
            }

            # ✅ Keep sub field for backward compatibility with old code
            if user_info.get("sub"):
                result["sub"] = user_info["sub"]

            logger.debug(
                "Successfully obtained user information from Gateway",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "user_id": result["id"],
                    "username": result["username"],
                    "user_type": result["user_type"],
                },
            )

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Failed to parse X-User-Info header",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "header_preview": (
                        user_info_header[:100] + "..." if len(user_info_header) > 100 else user_info_header
                    ),
                    "hint": "Format error in X-User-Info header passed by Gateway",
                },
                exc_info=True,
            )
            # Parsing failed, return None (optional authentication)
            return None

    except Exception as e:
        logger.error(
            "Failed to get current user",
            extra={
                "path": request.url.path,
                "method": request.method,
                "operation": "get_current_user",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # Return None on exception, allowing optional authentication endpoints to continue processing
        return None
