"""WebSocket Authentication Utilities"""

import os
import sys
from typing import TYPE_CHECKING, Optional, Tuple

# Handle path imports using try-except
try:
    from fastapi import WebSocket, status
    import httpx
    import jwt

    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import get_service_discovery
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from fastapi import WebSocket, status
    import httpx

    from shared.common.loguru_config import get_logger
    from shared.utils.service_discovery import get_service_discovery

if TYPE_CHECKING:  # pragma: no cover
    from shared.utils.service_discovery import ServiceDiscovery

logger = get_logger(__name__)


async def extract_websocket_token(websocket: WebSocket) -> Optional[str]:
    """Extract token from WebSocket connection

    Supports the following methods:
    1. Query parameter: ?token=xxx
    2. Request header: Authorization: Bearer xxx
    3. Custom header: X-Token: xxx

    Args:
        websocket: WebSocket connection object

    Returns:
        token string or None
    """
    # 1. Extract from query parameters (most common)
    token = websocket.query_params.get("token")
    if token:
        logger.debug("Extract token from query parameter", extra={"method": "query_param"})
        return token

    # 2. Extract from Authorization header
    auth_header = websocket.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        logger.debug("Extract token from Authorization header", extra={"method": "bearer_header"})
        return token

    # 3. Extract from custom X-Token header
    token = websocket.headers.get("X-Token")
    if token:
        logger.debug("Extract token from X-Token header", extra={"method": "custom_header"})
        return token

    logger.warning(
        "No token found",
        extra={
            "query_params": dict(websocket.query_params),
            "headers_keys": list(websocket.headers.keys()),
        },
    )
    return None


async def verify_websocket_token(
    websocket: WebSocket,
    auth_service_url: Optional[str] = None,
) -> Tuple[bool, Optional[dict]]:
    """Verify WebSocket token

    Note:
        Since the gateway layer has already performed token validation, the host-service token
        validation has been disabled. If you need to re-enable validation at the host-service
        layer, you can uncomment the skip_verification below.

    Args:
        websocket: WebSocket connection object
        auth_service_url: Authentication service URL (if None, automatically get from ServiceDiscovery)

    Returns:
        (whether verification is successful, user info dictionary or None)
    """
    # ⚠️ Note: The following validation has been disabled because the gateway has already performed authentication
    # If you need to re-enable validation at the host-service layer, you can delete this code block
    skip_verification = True

    if skip_verification:
        # Even if full validation is disabled, extract basic information from the token (especially host_id)
        token = await extract_websocket_token(websocket)

        logger.info(
            "WebSocket token validation disabled (handled by gateway), extracting host_id from token",
            extra={
                "client": (f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"),
                "path": websocket.url.path,
                "token_exists": bool(token),
            },
        )

        # If there is a token, try to decode it to get user information (especially id)
        user_info = {
            "id": "unknown",
            "username": "unknown",
            "user_type": "device",
            "permissions": [],
            "roles": [],
        }

        if token:
            try:
                # Do not verify signature, only decode to get information
                decoded = jwt.decode(token, options={"verify_signature": False})

                # ✅ Consistently use id field (extract from sub if not present, compatible with old tokens)
                user_id = decoded.get("id") or decoded.get("sub")
                if user_id:
                    user_info["id"] = str(user_id)
                    logger.debug(
                        "Extracted id from token",
                        extra={"id": user_id},
                    )

                # Extract other available information
                if decoded.get("username"):
                    user_info["username"] = decoded.get("username")
                if decoded.get("user_type"):
                    user_info["user_type"] = decoded.get("user_type")
                if decoded.get("mg_id"):
                    user_info["mg_id"] = decoded.get("mg_id")

            except Exception as e:
                logger.debug(
                    "Unable to decode information from token",
                    extra={"error": str(e)},
                )

        # Directly return success, allow connection establishment
        return True, user_info

    # ============================================================================
    # Below is the original token validation logic (disabled)
    # To re-enable, change skip_verification = True above to False
    # ============================================================================

    try:
        # 1. Extract token
        token = await extract_websocket_token(websocket)
        if not token:
            logger.warning(
                "WebSocket connection missing token",
                extra={
                    "client": (f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"),
                    "path": websocket.url.path,
                },
            )
            return False, None

        # 2. Build candidate authentication service URL list (using the same multi-strategy approach
        # as verify_token_string)
        candidate_urls = []

        if auth_service_url:
            candidate_urls.append(auth_service_url)

        env_url = os.getenv("AUTH_SERVICE_BASE_URL")
        if env_url:
            candidate_urls.append(env_url)

        service_discovery_instance: Optional[ServiceDiscovery] = None
        try:
            service_discovery_instance = get_service_discovery()
            discovered_url = await service_discovery_instance.get_service_url("auth-service")
            candidate_urls.append(discovered_url)
        except Exception as discovery_error:
            logger.debug(
                "WebSocket service discovery failed to get auth-service address",
                extra={"error": str(discovery_error)},
            )

        # Use the same fallback address strategy as HTTP services
        if service_discovery_instance:
            try:
                fallback_url = service_discovery_instance._get_fallback_url("auth-service")
                candidate_urls.append(fallback_url)
            except Exception as fallback_error:
                logger.debug(
                    "WebSocket failed to calculate authentication service fallback address",
                    extra={"error": str(fallback_error)},
                )

        # Deduplicate and normalize addresses
        normalized_urls = []
        seen = set()
        for url in candidate_urls:
            if not url:
                continue
            normalized = url.rstrip("/")
            if normalized not in seen:
                seen.add(normalized)
                normalized_urls.append(normalized)

        if not normalized_urls:
            logger.error(
                "WebSocket unable to determine authentication service address",
                extra={
                    "candidate_urls": candidate_urls,
                },
            )
            return False, None

        last_error: Optional[Exception] = None

        # 3. Try using each candidate address to validate token
        for base_url in normalized_urls:
            try:
                logger.debug(
                    "WebSocket starting to validate token",
                    extra={
                        "token_preview": token[:20] + "..." if len(token) > 20 else token,
                        "auth_service_url": base_url,
                    },
                )

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{base_url}/api/v1/auth/introspect",
                        json={"token": token},
                        headers={"Content-Type": "application/json"},
                    )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})

                    logger.debug(
                        "WebSocket received introspect response",
                        extra={
                            "response_data": data,
                            "active": data.get("active"),
                        },
                    )

                    # Check if token is valid
                    if data.get("active", False):
                        # ✅ Consistently use id field, if not present then continue trying other addresses
                        user_id = data.get("id")
                        if not user_id or not str(user_id).strip():
                            logger.warning(
                                "WebSocket token valid but id is empty",
                                extra={
                                    "id": user_id,
                                    "id_type": type(user_id).__name__ if user_id is not None else "None",
                                    "auth_service_url": base_url,
                                    "data_keys": list(data.keys()),
                                },
                            )
                            # Continue trying other addresses
                            continue

                        user_info = {
                            "id": user_id,
                            "username": data.get("username"),
                            "user_type": data.get("user_type"),
                            "permissions": data.get("permissions", []),
                            "roles": data.get("roles", []),
                        }

                        logger.info(
                            "WebSocket token validation successful",
                            extra={
                                "id": user_info["id"],
                                "username": user_info["username"],
                                "user_type": user_info["user_type"],
                                "client": f"{websocket.client.host}:{websocket.client.port}"
                                if websocket.client
                                else "unknown",
                                "path": websocket.url.path,
                            },
                        )
                        return True, user_info
                    logger.warning(
                        "WebSocket token active=False",
                        extra={
                            "data": data,
                            "auth_service_url": base_url,
                        },
                    )
                    # Continue trying other addresses
                    continue
                logger.warning(
                    "WebSocket token validation response error",
                    extra={
                        "status_code": response.status_code,
                        "auth_service_url": base_url,
                    },
                )
                # Continue trying other addresses
                continue

            except httpx.RequestError as e:
                logger.debug(
                    "WebSocket call to authentication service failed",
                    extra={
                        "error": str(e),
                        "auth_service_url": base_url,
                    },
                )
                last_error = e
                # Continue trying other addresses
                continue

        # All addresses failed
        logger.error(
            "WebSocket unable to validate token - All authentication service addresses failed",
            extra={
                "last_error": str(last_error) if last_error else "unknown",
                "tried_urls": normalized_urls,
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown",
            },
            exc_info=last_error,
        )
        return False, None

    except Exception as e:
        logger.error(
            "WebSocket token validation exception",
            extra={"error": str(e)},
            exc_info=True,
        )
        return False, None


async def handle_websocket_auth_error(websocket: WebSocket, message: str = "Authentication failed"):
    """Handle WebSocket authentication error

    Args:
        websocket: WebSocket connection object
        message: Error message
    """
    try:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=message)
        logger.warning(
            "WebSocket connection closed due to authentication failure",
            extra={
                "reason": message,
                "client": (f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"),
            },
        )
    except Exception as e:
        logger.error(
            "Error closing WebSocket connection",
            extra={"error": str(e)},
            exc_info=True,
        )


async def verify_token_string(
    token: str,
    auth_service_url: Optional[str] = None,
) -> Optional[str]:
    """Verify token string and return user_id

    Used for gateway layer token validation (directly validate token string)

    Args:
        token: JWT token string
        auth_service_url: Authentication service URL

    Returns:
        user_id or None (when validation fails)
    """
    # Build candidate authentication service URL list (by priority)
    candidate_urls = []

    if auth_service_url:
        candidate_urls.append(auth_service_url)

    env_url = os.getenv("AUTH_SERVICE_BASE_URL")
    if env_url:
        candidate_urls.append(env_url)

    service_discovery: Optional[ServiceDiscovery] = None
    try:
        service_discovery = get_service_discovery()
        discovered_url = await service_discovery.get_service_url("auth-service")
        candidate_urls.append(discovered_url)
    except Exception as discovery_error:
        logger.debug(
            "Failed to get auth-service address from service discovery, using default address",
            extra={"error": str(discovery_error)},
        )

    # Use the same fallback address strategy as HTTP services
    if service_discovery:
        try:
            fallback_url = service_discovery._get_fallback_url("auth-service")
            candidate_urls.append(fallback_url)
        except Exception as fallback_error:
            logger.debug(
                "Failed to calculate authentication service fallback address",
                extra={"error": str(fallback_error)},
            )

    # Deduplicate and normalize addresses
    normalized_urls = []
    seen = set()
    for url in candidate_urls:
        if not url:
            continue
        normalized = url.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            normalized_urls.append(normalized)

    last_error: Optional[Exception] = None

    for base_url in normalized_urls:
        try:
            logger.debug(
                "Starting to validate Token string",
                extra={
                    "token_preview": token[:20] + "..." if len(token) > 20 else token,
                    "auth_service_url": base_url,
                },
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{base_url}/api/v1/auth/introspect",
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )

            logger.debug(
                "Token validation response received",
                extra={
                    "status_code": response.status_code,
                    "auth_service_url": base_url,
                },
            )

            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {})

                logger.debug(
                    "Token validation response parsed",
                    extra={
                        "active": data.get("active", False),
                        "user_id": data.get("user_id"),
                        "username": data.get("username"),
                        "data_keys": list(data.keys()),
                    },
                )

                if data.get("active", False):
                    # ✅ Consistently use id field, return None if not present
                    user_id = data.get("id")
                    if user_id and str(user_id).strip():
                        logger.info(
                            "Token string validation successful",
                            extra={
                                "id": user_id,
                                "username": data.get("username"),
                                "auth_service_url": base_url,
                            },
                        )
                        return str(user_id)

                    logger.warning(
                        "Token is valid but no valid id retrieved",
                        extra={
                            "auth_service_url": base_url,
                            "id": user_id,
                            "id_type": type(user_id).__name__ if user_id is not None else "None",
                            "data_keys": list(data.keys()),
                        },
                    )
                    return None

                logger.warning(
                    "Token validated but in non-active state",
                    extra={
                        "auth_service_url": base_url,
                        "active": data.get("active", False),
                    },
                )
                continue

            logger.warning(
                "Token string validation failed",
                extra={
                    "auth_service_url": base_url,
                    "status_code": response.status_code,
                },
            )

        except httpx.RequestError as request_error:
            logger.warning(
                "Failed to call authentication service, trying next candidate address",
                extra={
                    "auth_service_url": base_url,
                    "error": str(request_error),
                    "error_type": type(request_error).__name__,
                },
            )
            last_error = request_error
            continue

        except Exception as exc:
            logger.error(
                "Token string validation exception",
                extra={
                    "auth_service_url": base_url,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            last_error = exc
            continue

    if last_error:
        logger.error(
            "All authentication service addresses failed to validate Token",
            extra={"error": str(last_error), "error_type": type(last_error).__name__},
        )
    else:
        logger.warning("No valid authentication service address found, Token validation failed")

    return None
