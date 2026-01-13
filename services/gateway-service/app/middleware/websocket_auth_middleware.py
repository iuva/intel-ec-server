"""
WebSocket authentication middleware

Provides token authentication and authorization functionality for WebSocket connections
"""

import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from fastapi import WebSocket, WebSocketException

# Use try-except to handle path imports
try:
    from shared.common.exceptions import AuthorizationError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.exceptions import AuthorizationError
    from shared.common.loguru_config import get_logger
    from shared.common.security import JWTManager

logger = get_logger(__name__)


class WebSocketAuthMiddleware:
    """WebSocket authentication middleware

    Provides the following functionality:
    - JWT token verification
    - Permission checking
    - Session management
    - Authentication failure handling
    """

    def __init__(self, jwt_manager: Optional[JWTManager] = None):
        """Initialize authentication middleware

        Args:
            jwt_manager: JWT manager instance, if None then authentication is disabled
        """
        self.jwt_manager = jwt_manager
        self.logger = logger

    async def authenticate(self, websocket: WebSocket, require_auth: bool = False) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket connection

        Args:
            websocket: WebSocket connection object
            require_auth: Whether authentication is required (True means must provide valid token)

        Returns:
            Returns user information dict on successful authentication, None on failure or when optional

        Raises:
            WebSocketException: Raises exception when authentication fails
        """
        try:
            # Extract token
            token = self._extract_token(websocket)

            if not token:
                if require_auth:
                    self.logger.warning(
                        "WebSocket connection missing authentication token",
                        extra={
                            "client": websocket.client.host if websocket.client else "unknown",
                            "path": websocket.url.path,
                        },
                    )
                    raise WebSocketException(code=1008, reason="Missing authentication token")

                # Return None when authentication is optional
                self.logger.debug(
                    "WebSocket connection did not provide token, allowing continuation (authentication optional)",
                    extra={"client": websocket.client.host if websocket.client else "unknown"},
                )
                return None

            # Verify token
            if not self.jwt_manager:
                self.logger.warning("JWT manager not configured, cannot verify token")
                return None

            user_info = await self._verify_token(token)
            if not user_info:
                self.logger.warning(
                    "WebSocket connection provided invalid token",
                    extra={"client": websocket.client.host if websocket.client else "unknown"},
                )
                raise WebSocketException(code=1008, reason="Invalid token")

            # Log successful authentication
            self.logger.info(
                "WebSocket connection authenticated",
                extra={
                    "client": websocket.client.host if websocket.client else "unknown",
                    "id": user_info.get("id"),
                    "username": user_info.get("username"),
                },
            )

            return user_info

        except WebSocketException:
            raise
        except Exception as e:
            self.logger.error(
                f"WebSocket authentication exception: {e!s}",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            raise WebSocketException(code=1011, reason="Authentication service error")

    def _extract_token(self, websocket: WebSocket) -> Optional[str]:
        """Extract token from WebSocket connection

        Supports multiple token provision methods:
        1. Authorization query parameter: ?token=<token>
        2. Authorization request header: Authorization: Bearer <token>

        Args:
            websocket: WebSocket connection object

        Returns:
            Token string, returns None if not found
        """
        # Method 1: Query parameter
        query_params = parse_qs(urlparse(str(websocket.url)).query)
        if "token" in query_params:
            token = query_params["token"][0]
            self.logger.debug("Extracted token from query parameter")
            return token

        # Method 2: Authorization request header
        auth_header = websocket.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            self.logger.debug("Extracted token from Authorization header")
            return token

        return None

    async def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Returns user information dict if token is valid, None if invalid
        """
        if not self.jwt_manager:
            return None

        try:
            user_info = self.jwt_manager.verify_token(token)
            if user_info:
                # ✅ Use id field uniformly (extract from sub if not present, compatible with old tokens)
                user_id = user_info.get("id") or user_info.get("sub")
                # If original user_info doesn't have id field, add it (compatible with old tokens)
                if "id" not in user_info and user_id:
                    user_info["id"] = user_id
                if not user_id:
                    self.logger.warning(
                        "Token verification successful but id is empty", extra={"payload_keys": list(user_info.keys())}
                    )
                    return None
                self.logger.debug("Token verification successful", extra={"id": user_id})
            return user_info

        except Exception as e:
            self.logger.debug("Token verification failed", extra={"error": str(e)})
            return None

    async def check_permissions(
        self,
        user_info: Optional[Dict[str, Any]],
        required_permissions: Optional[list] = None,
    ) -> bool:
        """Check user permissions

        Args:
            user_info: User information dict
            required_permissions: Required permissions list

        Returns:
            Returns True if permission check ***REMOVED***es, False otherwise

        Raises:
            AuthorizationError: Raises exception when permissions are insufficient
        """
        if not required_permissions:
            # No permission requirements, allow access
            return True

        if not user_info:
            raise AuthorizationError("Unauthenticated user has no access")

        user_permissions = set(user_info.get("permissions", []))
        required_perms = set(required_permissions)

        if not required_perms.issubset(user_permissions):
            missing_perms = required_perms - user_permissions
            self.logger.warning(
                "User has insufficient permissions",
                extra={
                    "id": user_info.get("id"),
                    "required": list(required_perms),
                    "missing": list(missing_perms),
                },
            )
            raise AuthorizationError(f"Missing permissions: {', '.join(missing_perms)}")

        return True
