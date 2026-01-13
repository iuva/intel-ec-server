"""
Token Extraction and Verification Utility Class

Provides unified HTTP/WebSocket token extraction and verification functionality.
"""

import os
import sys
from typing import Any, Dict, Optional, Tuple

# Use try-except to handle path imports
try:
    from fastapi import Request
    import httpx

    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from fastapi import Request
    import httpx

    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class TokenExtractor:
    """Token Extraction and Verification Utility Class

    Provides functionality to extract tokens from HTTP Requests and verify them with auth-service.

    Example:
        >>> extractor = TokenExtractor()
        >>> token = extractor.extract_token_from_request(request)
        >>> is_valid, payload = await extractor.verify_token(token)
        >>> if is_valid:
        >>>     user_id = payload.get("user_id")
    """

    def __init__(self, auth_service_url: str = "http://auth-service:8001", service_discovery=None):
        """Initialize Token Extractor

        Args:
            auth_service_url: Authentication service URL (static configuration,
                              used when service_discovery is not provided)
            service_discovery: ServiceDiscovery instance (optional),
                               used to dynamically get service addresses
        """
        self.auth_service_url = auth_service_url
        self.service_discovery = service_discovery

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract token from HTTP Request

        Supports the following methods:
        1. Authorization header: Bearer token
        2. Query parameter: ?token=xxx
        3. Custom header: X-Token: xxx

        Args:
            request: FastAPI Request object

        Returns:
            token string or None

        Example:
            >>> extractor = TokenExtractor()
            >>> token = extractor.extract_token_from_request(request)
        """
        # 1. Extract from Authorization header (recommended method)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug("Extracted token from Authorization header", extra={"method": "bearer_header"})
            return token

        # 2. Extract from query parameters (compatibility)
        token = request.query_params.get("token")
        if token:
            logger.debug("Extracted token from query parameters", extra={"method": "query_param"})
            return token

        # 3. Extract from custom X-Token header (compatibility)
        token = request.headers.get("X-Token")
        if token:
            logger.debug("Extracted token from X-Token header", extra={"method": "custom_header"})
            return token

        logger.warning(
            "No token found",
            extra={
                "path": request.url.path,
                "query_params": dict(request.query_params),
            },
        )
        return None

    async def verify_token(self, token: str, timeout: float = 10.0) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify token validity

        Calls auth-service's introspect endpoint to verify the token.

        Args:
            token: JWT token string
            timeout: Request timeout (seconds)

        Returns:
            (is_valid, user information dictionary or None)

        Example:
            >>> extractor = TokenExtractor()
            >>> is_valid, payload = await extractor.verify_token(token)
            >>> if is_valid:
            >>>     print(payload["user_id"])
        """
        if not token:
            logger.warning("Token is empty")
            return False, None

        try:
            # Get auth-service address (dynamic or static)
            if self.service_discovery:
                auth_service_url = await self.service_discovery.get_service_url("auth-service")
            else:
                auth_service_url = self.auth_service_url

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{auth_service_url}/api/v1/auth/introspect",
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    logger.debug(
                        "Received introspect response",
                        extra={
                            "active": data.get("active"),
                            "id": data.get("id"),
                        },
                    )

                    # Check if token is valid
                    if data.get("active", False):
                        # ✅ Use id field uniformly, return False if not present
                        user_id = data.get("id")
                        if not user_id:
                            logger.warning(
                                "Token verification successful but id is empty",
                                extra={
                                    "data_keys": list(data.keys()),
                                    "active": data.get("active"),
                                },
                            )
                            return False, None
                        # Build user information
                        user_info = {
                            "id": user_id,
                            "username": data.get("username"),
                            "user_type": data.get("user_type"),
                            "permissions": data.get("permissions", []),
                            "roles": data.get("roles", []),
                            "mg_id": data.get("mg_id"),  # Management group ID (if available)
                        }

                        logger.info(
                            "Token verification successful",
                            extra={
                                "id": user_info["id"],
                                "username": user_info["username"],
                                "user_type": user_info["user_type"],
                            },
                        )
                        return True, user_info
                    logger.warning("Token is expired or invalid")
                    return False, None
                logger.warning(
                    f"Token verification request failed: {response.status_code}",
                    extra={"status_code": response.status_code},
                )
                return False, None

        except httpx.TimeoutException:
            logger.error("Token verification timeout: auth-service not responding")
            return False, None

        except Exception as e:
            logger.error(f"Token verification exception: {e!s}", exc_info=True)
            return False, None

    async def extract_and_verify(self, request: Request) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """One-stop: extract and verify token

        Extract token from Request and verify with auth-service.

        Args:
            request: FastAPI Request object

        Returns:
            (is_valid, user information dictionary or None)

        Example:
            >>> extractor = TokenExtractor()
            >>> is_valid, user_info = await extractor.extract_and_verify(request)
            >>> if is_valid:
            >>>     id = user_info["id"]
        """
        # Extract token
        token = self.extract_token_from_request(request)

        if not token:
            logger.warning("No token found in request")
            return False, None

        # Verify token
        return await self.verify_token(token)


# Global singleton instance
_token_extractor_instance: Optional[TokenExtractor] = None


def get_token_extractor() -> TokenExtractor:
    """Get Token Extractor singleton instance

    Returns:
        TokenExtractor: Token Extractor instance

    Example:
        >>> extractor = get_token_extractor()
        >>> token = extractor.extract_token_from_request(request)
    """
    global _token_extractor_instance

    if _token_extractor_instance is None:
        _token_extractor_instance = TokenExtractor()

    return _token_extractor_instance
