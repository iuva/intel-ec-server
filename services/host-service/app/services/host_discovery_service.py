"""Host Discovery Service

Provides host discovery and query related business logic services, including:
- Query available host list (cursor pagination)
- Call external hardware API to get host information
- Local database filtering and querying
"""

import asyncio
import os
import time
from typing import TYPE_CHECKING, List, Optional, Set, cast

import httpx
from sqlalchemy import and_, select
from sqlalchemy.exc import OperationalError

from app.constants.host_constants import (
    APPR_STATE_ENABLE,
    HOST_STATE_FREE,
    TCP_STATE_LISTEN,
)
from app.models.host_rec import HostRec
from app.schemas.host import AvailableHostInfo, AvailableHostsListResponse, HardwareHostData, QueryAvailableHostsRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Global HTTP client connection pool (reuse connections for better performance)
_http_client: Optional["httpx.AsyncClient"] = None

# Use try-except to handle path imports
try:
    from app.services.external_api_client import call_external_api
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger
except ImportError:
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from app.services.external_api_client import call_external_api
    from shared.common.database import mariadb_manager
    from shared.common.decorators import handle_service_errors, monitor_operation
    from shared.common.exceptions import BusinessError, ServiceErrorCodes
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class HostDiscoveryService:
    """Host Discovery Service Class

    Responsible for host discovery, querying and filtering related business logic,
    supports cursor pagination and external API integration.
    """

    # Circuit Breaker State (Shared across all instances)
    _last_failure_time = 0.0
    _consecutive_failures = 0
    _circuit_open = False

    # Circuit Breaker Configuration
    CB_FAILURE_THRESHOLD = 5
    CB_RECOVERY_TIMEOUT = 60.0

    def __init__(self, hardware_api_url: Optional[str] = None):
        """Initialize Host Discovery Service

        Args:
            hardware_api_url: Hardware API base URL. If not provided, default value will be used
        """
        self.hardware_api_url = hardware_api_url or "http://hardware-service:8000"
        self._http_client: Optional[httpx.AsyncClient] = None
        # ✅ Optimization: Cache session factory
        self._session_factory = None

    @property
    def session_factory(self):
        """Get session factory (lazy initialization, singleton pattern)

        ✅ Optimization: Cache session factory to avoid repeated retrieval
        """
        if self._session_factory is None:
            self._session_factory = mariadb_manager.get_session()
        return self._session_factory

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client connection pool (singleton pattern)

        ⚠️ Deprecated: Please use external_api_client.call_external_api method,
        which supports unified SSL configuration and authentication

        Returns:
            httpx.AsyncClient: HTTP client instance
        """
        global _http_client
        if _http_client is None:
            # ✅ Read SSL verification configuration from environment variables
            # (consistent with other external APIs)
            verify_ssl_env = os.getenv("HTTP_CLIENT_VERIFY_SSL", "true").lower()
            verify_ssl = verify_ssl_env in ("true", "1", "yes", "on", "enabled")

            # Create HTTP client with connection pool for better high-concurrency performance
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),  # Total timeout 10s, connection timeout 5s
                limits=httpx.Limits(
                    max_keepalive_connections=50,  # Keep-alive connections
                    max_connections=200,  # Maximum connections
                ),
                verify=verify_ssl,  # ✅ Support SSL configuration
            )
        return _http_client

    @monitor_operation("query_available_hosts", record_duration=True)
    @handle_service_errors(error_message="Failed to query available host list", error_code="QUERY_HOSTS_FAILED")
    async def query_available_hosts(
        self,
        request: QueryAvailableHostsRequest,
        fastapi_request=None,  # FastAPI Request object (used to get user_id)
        user_id: Optional[int] = None,  # User ID (optional, can be None if email is provided)
    ) -> AvailableHostsListResponse:
        """Query available host list with cursor pagination support

        Business Logic:
        1. Calculate initial offset based on last_id (for querying from external API)
        2. Call external hardware API to get paginated host list (with authentication)
           - If request.email exists, directly use this email for external API authentication,
             without querying database
           - If request.email does not exist, query database to get email based on user_id
        3. Query host_rec table for filtering based on hardware_id
        4. Filter conditions: appr_state=1 (enabled), host_state=0 (free),
           tcp_state=2 (listening/connected), del_flag=0 (not deleted)
        5. Collect results that meet pagination size and return
        6. Each user is processed independently, no global state pollution

        Cursor Pagination:
        - First request: last_id = None, start from skip=0
        - Subsequent requests: ***REMOVED*** last_id from previous page, system automatically calculates skip
        - Avoid concurrent users interfering with each other

        Authentication Optimization:
        - If request.email is provided, system directly uses this email to get external API token,
          skipping database query for better performance
        - If request.email is not provided, system will query database to get email based on user_id
          (from fastapi_request or parameter)

        Args:
            request: Query request parameters, including:
                - tc_id: Test case ID
                - cycle_name: Test cycle name
                - user_name: Username
                - page_size: Page size (1-100)
                - last_id: ID of last record from previous page (optional)
                - email: User email (optional). If provided, will directly use this email for
                  external API authentication without querying database
            fastapi_request: FastAPI Request object (used to get user_id from request headers)
            user_id: User ID (optional, can be None if request.email is provided)

        Returns:
            Paginated response containing available host list

        Raises:
            BusinessError: When external API call fails or data query fails
        """
        operation_start_time = time.time()

        logger.info(
            "Starting to query available host list",
            extra={
                "operation": "query_available_hosts",
                "tc_id": request.tc_id,
                "cycle_name": request.cycle_name,
                "user_name": request.user_name,
                "page_size": request.page_size,
                "last_id": request.last_id,
                "email": request.email,  # ✅ Record email parameter (if provided)
            },
        )

        # Step 1: Calculate initial offset for external API based on last_id
        initial_skip = 0
        if request.last_id is not None:
            # Need to traverse from beginning, but will skip through seen_ids
            initial_skip = 0

        # Cache processed host_rec_id in this query to ensure no duplicates
        # This cache is only valid within a single request, does not cross requests
        seen_ids: Set[str] = set()
        all_available_hosts: List[AvailableHostInfo] = []

        # External API pagination parameters
        skip = initial_skip
        # limit = 100  # Request 100 records per call
        limit = 10  # Request 10 records per call
        max_iterations = 100  # Maximum 100 iterations to prevent infinite loop

        # ✅ Infinite loop detection: record consecutive iterations with no progress
        no_progress_count = 0  # Consecutive iterations with no progress
        max_no_progress = 5  # Maximum 5 iterations with no progress allowed
        last_available_count = 0  # Available host count after previous iteration
        seen_hardware_ids: Set[str] = set()  # Set of processed hardware_id (for detecting duplicates)

        # Optimization: Create database session outside loop, reuse connection, reduce connection pool pressure
        session_factory = self.session_factory
        async with session_factory() as session:
            # Record connection pool status (before connection acquisition)
            pool_status_before = mariadb_manager.get_pool_status()
            if pool_status_before["usage_percent"] >= 80:
                logger.warning(
                    "Database connection pool usage is high, starting query",
                    extra={
                        "usage_percent": pool_status_before["usage_percent"],
                        "checked_out": pool_status_before["checked_out"],
                        "max_connections": pool_status_before["max_connections"],
                    },
                )

            # Loop to get external API data and filter until pagination requirements are met
            for iteration in range(max_iterations):
                # If enough data has been collected, exit loop early
                if len(all_available_hosts) >= request.page_size:
                    logger.info(
                        "Enough data obtained for pagination, exiting loop early",
                        extra={
                            "iteration": iteration,
                            "required_size": request.page_size,
                            "actual_count": len(all_available_hosts),
                            "skip": skip,
                        },
                    )
                    break

                # ✅ Infinite loop detection: if consecutive iterations have not added any records, exit loop
                if iteration > 0 and len(all_available_hosts) == last_available_count:
                    no_progress_count += 1
                    if no_progress_count >= max_no_progress:
                        logger.warning(
                            "Detected infinite loop risk, consecutive iterations with no progress, exiting loop",
                            extra={
                                "iteration": iteration,
                                "no_progress_count": no_progress_count,
                                "current_available_count": len(all_available_hosts),
                                "required_size": request.page_size,
                                "skip": skip,
                            },
                        )
                        break
                else:
                    # Has progress, reset no progress count
                    no_progress_count = 0

                # Only log detailed information on first iteration or every 10 iterations to reduce log volume
                if iteration == 0 or iteration % 10 == 0:
                    logger.debug(
                        "Calling external API to get hardware host list",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "limit": limit,
                            "current_available_count": len(all_available_hosts),
                            "no_progress_count": no_progress_count,
                        },
                    )

                # Step 2: Call external hardware API to get host list (with authentication)
                hardware_hosts = await self._fetch_hardware_hosts(
                    tc_id=request.tc_id,
                    skip=skip,
                    limit=limit,
                    request=fastapi_request,
                    user_id=user_id,
                    email=request.email,  # ✅ Pass email parameter
                )

                # If external API returns empty, stop loop
                if not hardware_hosts:
                    logger.info(
                        "External API returned empty data or reached end",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "total_available": len(all_available_hosts),
                        },
                    )
                    break

                # ✅ Infinite loop detection: check if duplicate hardware_id is returned
                # (indicates external API does not support true pagination)
                current_hardware_ids = {host.hardware_id for host in hardware_hosts if host.hardware_id}
                if current_hardware_ids.issubset(seen_hardware_ids):
                    logger.warning(
                        "Detected external API returned duplicate data, may not support true pagination, exiting loop",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "current_hardware_ids_count": len(current_hardware_ids),
                            "seen_hardware_ids_count": len(seen_hardware_ids),
                            "current_available_count": len(all_available_hosts),
                        },
                    )
                    break

                # Update processed hardware_id set
                seen_hardware_ids.update(current_hardware_ids)

                # Step 3: Extract hardware ID list for querying local database
                hardware_ids = [host.hardware_id for host in hardware_hosts if host.hardware_id]

                # Step 4: Query host_rec table to get available hosts
                # (Optimization: reuse session, reduce connection usage)
                query_start_time = time.time()
                available_hosts = await self._filter_available_hosts_in_session(session, hardware_ids)
                query_duration = time.time() - query_start_time

                # Record query performance (if query time exceeds threshold)
                if query_duration > 0.5:  # Log warning if exceeds 500ms
                    logger.warning(
                        "Database query took too long",
                        extra={
                            "iteration": iteration,
                            "query_duration_ms": round(query_duration * 1000, 2),
                            "hardware_ids_count": len(hardware_ids),
                            "available_count": len(available_hosts),
                        },
                    )

                logger.debug(
                    "This round of filtering completed",
                    extra={
                        "iteration": iteration,
                        "fetched_hardware_count": len(hardware_hosts),
                        "available_count": len(available_hosts),
                        "total_available_before": len(all_available_hosts),
                        "query_duration_ms": round(query_duration * 1000, 2),
                    },
                )

                # Record available host count before this iteration (for no progress detection)
                last_available_count = len(all_available_hosts)

                # Step 5: Add new data, while skipping data after last_id
                added_count = 0  # Number of records added in this iteration
                for host in available_hosts:
                    # If last_id is specified, skip all records with ID less than or equal to last_id
                    # Note: Since ID is string, need to convert to integer for comparison
                    # ✅ Use actual field name id (not alias host_rec_id)
                    if request.last_id is not None:
                        try:
                            host_id_int = int(host.id)
                            last_id_int = int(request.last_id)
                            if host_id_int <= last_id_int:
                                continue
                        except (ValueError, TypeError):
                            # If conversion fails, use string comparison (fallback solution)
                            if host.id <= request.last_id:
                                continue

                    # Check if already added (deduplication in this query)
                    if host.id in seen_ids:
                        continue

                    all_available_hosts.append(host)
                    seen_ids.add(host.id)
                    added_count += 1

                    # If required count has been reached, can exit inner loop early
                    if len(all_available_hosts) >= request.page_size:
                        break

                # ✅ Record number of records added in this iteration (for debugging)
                if added_count == 0:
                    logger.debug(
                        "This iteration did not add any records",
                        extra={
                            "iteration": iteration,
                            "skip": skip,
                            "available_hosts_count": len(available_hosts),
                            "current_total": len(all_available_hosts),
                            "no_progress_count": no_progress_count + 1,
                        },
                    )

                # Prepare next page request (before checking if to exit early)
                skip += limit

            # Record connection pool status (after connection release)
            pool_status_after = mariadb_manager.get_pool_status()
            if pool_status_after["usage_percent"] >= 80:
                logger.warning(
                    "Database connection pool usage is high, query completed",
                    extra={
                        "usage_percent": pool_status_after["usage_percent"],
                        "checked_out": pool_status_after["checked_out"],
                        "max_connections": pool_status_after["max_connections"],
                    },
                )

        # Step 7: Perform pagination slice - return first page_size records
        paginated_hosts = all_available_hosts[: request.page_size]

        # Step 8: Determine if there is next page
        has_next = len(all_available_hosts) > request.page_size

        # Determine next page's last_id
        last_id: Optional[str] = None
        if paginated_hosts:
            # ✅ Use actual field name id (not alias host_rec_id)
            last_id = paginated_hosts[-1].id

        operation_duration = time.time() - operation_start_time

        # Record total operation duration
        logger.info(
            "Query available host list completed",
            extra={
                "tc_id": request.tc_id,
                "total_available_in_query": len(all_available_hosts),
                "page_size": request.page_size,
                "returned_count": len(paginated_hosts),
                "has_next": has_next,
                "last_id": last_id,
                "operation_duration_ms": round(operation_duration * 1000, 2),
                "is_test_data": len(paginated_hosts) == 1 and paginated_hosts[0].id == "1111111",
            },
        )

        # If operation duration exceeds 2 seconds, log warning
        if operation_duration > 2.0:
            logger.warning(
                "Query available host list took too long",
                extra={
                    "operation_duration_ms": round(operation_duration * 1000, 2),
                    "returned_count": len(paginated_hosts),
                    "page_size": request.page_size,
                },
            )

        # Build response object
        return AvailableHostsListResponse(
            hosts=paginated_hosts,
            total=len(all_available_hosts),  # Total discovered in this query
            page_size=request.page_size,
            has_next=has_next,
            last_id=last_id,
        )

    async def _fetch_hardware_hosts(
        self,
        tc_id: str,
        skip: int = 0,
        limit: int = 100,
        request=None,  # FastAPI Request object (used to get user_id)
        user_id: Optional[int] = None,  # User ID (optional, can be None if email provided)
        email: Optional[str] = None,  # User email (optional). If provided, directly use to get token
    ) -> List[HardwareHostData]:
        """Call external hardware API to get host list (with authentication)

        Uses unified external API client, automatically handles authentication and SSL configuration.

        Authentication methods:
        - **Method 1 (Recommended)**: If `email` parameter is provided, directly use this email
          to get external API token, skip database query for better performance
        - **Method 2**: If `email` is not provided, system will query database to get email
          based on `user_id` (from request or parameter)

        Args:
            tc_id: Test case ID
            skip: Number of records to skip (for pagination)
            limit: Number of records to return (maximum per request)
            request: FastAPI Request object (used to get user_id from request headers)
            user_id: ID of currently logged in admin user (optional, can be None if email provided)
            email: User email (optional). If provided, directly use to get token without querying database

        Returns:
            Hardware host list (list of HardwareHostData objects)

        Raises:
            BusinessError: When API call fails, including:
                - External API call failed (network error, timeout, etc.)
                - External API returned non-200 status code
                - Response data format does not meet expectations

        Note:
            - Circuit Breaker pattern implemented (Threshold: 5 failures, Recovery: 60s)
        """
        # ✅ Circuit Breaker Check
        current_time = time.time()
        if HostDiscoveryService._circuit_open:
            if current_time - HostDiscoveryService._last_failure_time < HostDiscoveryService.CB_RECOVERY_TIMEOUT:
                logger.warning(
                    "Hardware API circuit breaker is OPEN, rejecting request",
                    extra={
                        "tc_id": tc_id,
                        "last_failure_time": HostDiscoveryService._last_failure_time,
                        "recovery_timeout": HostDiscoveryService.CB_RECOVERY_TIMEOUT,
                    },
                )
                raise BusinessError(
                    message="Hardware API service is temporarily unavailable (Circuit Breaker Open)",
                    error_code="HOST_HARDWARE_API_CIRCUIT_BREAKER_OPEN",
                    code=ServiceErrorCodes.HOST_HARDWARE_API_CIRCUIT_BREAKER_OPEN,
                    http_status_code=503,
                )
            logger.info("Hardware API circuit breaker entering HALF-OPEN state", extra={"tc_id": tc_id})

        try:
            # ✅ Use unified external API client (supports authentication and SSL configuration)
            url_path = "/api/v1/hardware/hosts"
            params = {
                "tc_id": tc_id,
                "skip": skip,
                "limit": limit,
            }

            logger.debug(
                "Calling hardware API (with authentication)",
                extra={
                    "url_path": url_path,
                    "params": params,
                    "user_id": user_id,
                    "email": email,
                },
            )

            # ✅ Use unified external API call method (automatically handles token acquisition and authentication)
            # If email is provided, will directly use this email to get token without querying database
            # ✅ Optimization: Reduce timeout from 30s to 10s, fail fast to avoid blocking
            try:
                response = await call_external_api(
                    method="GET",
                    url_path=url_path,
                    request=request,
                    user_id=user_id,
                    email=email,  # ✅ Pass email parameter
                    params=params,
                    timeout=10.0,  # ✅ Optimization: Reduced from 30.0 to 10.0
                )
            except (asyncio.TimeoutError, httpx.TimeoutException):
                # ❌ Circuit Breaker: Record Failure (Timeout)
                HostDiscoveryService._consecutive_failures += 1
                if HostDiscoveryService._consecutive_failures >= HostDiscoveryService.CB_FAILURE_THRESHOLD:
                    HostDiscoveryService._circuit_open = True
                    HostDiscoveryService._last_failure_time = time.time()
                    logger.error(
                        "Hardware API circuit breaker TRIPPED (OPEN) due to timeout",
                        extra={"failures": HostDiscoveryService._consecutive_failures},
                    )

                logger.error(
                    "Hardware API call timeout",
                    extra={
                        "tc_id": tc_id,
                        "url_path": url_path,
                        "timeout": 10.0,
                    },
                )
                raise BusinessError(
                    message="Hardware API call timed out, please try again later",
                    error_code="HOST_HARDWARE_API_TIMEOUT",
                    code=ServiceErrorCodes.HOST_HARDWARE_API_TIMEOUT,
                    http_status_code=504,  # Gateway Timeout
                )
            except Exception:
                # ❌ Circuit Breaker: Record Failure (Other errors)
                HostDiscoveryService._consecutive_failures += 1
                if HostDiscoveryService._consecutive_failures >= HostDiscoveryService.CB_FAILURE_THRESHOLD:
                    HostDiscoveryService._circuit_open = True
                    HostDiscoveryService._last_failure_time = time.time()
                    logger.error(
                        "Hardware API circuit breaker TRIPPED (OPEN) due to exception",
                        extra={"failures": HostDiscoveryService._consecutive_failures},
                    )
                raise

            status_code = response.get("status_code")
            response_body = response.get("body")

            if status_code != 200:
                # ❌ Circuit Breaker: Record Failure (Non-200)
                HostDiscoveryService._consecutive_failures += 1
                if HostDiscoveryService._consecutive_failures >= HostDiscoveryService.CB_FAILURE_THRESHOLD:
                    HostDiscoveryService._circuit_open = True
                    HostDiscoveryService._last_failure_time = time.time()
                    logger.error(
                        f"Hardware API circuit breaker TRIPPED (OPEN) due to status {status_code}",
                        extra={"failures": HostDiscoveryService._consecutive_failures},
                    )

                error_msg = (
                    response.get("body", {}).get("message", "Unknown error")
                    if isinstance(response.get("body"), dict)
                    else str(response.get("body"))
                )

                # Check for 504 Gateway Timeout from external service
                if status_code == 504:
                    raise BusinessError(
                        message="Hardware API gateway timeout",
                        error_code="HOST_HARDWARE_API_TIMEOUT",
                        code=ServiceErrorCodes.HOST_HARDWARE_API_TIMEOUT,
                        http_status_code=504,
                    )

                raise BusinessError(
                    message=f"Hardware API call failed: {error_msg}",
                    error_code="HOST_HARDWARE_API_ERROR",
                    code=ServiceErrorCodes.HOST_HARDWARE_API_ERROR,
                    http_status_code=status_code or 500,
                )

            # ✅ Circuit Breaker: Success (Reset)
            if HostDiscoveryService._circuit_open or HostDiscoveryService._consecutive_failures > 0:
                logger.info(
                    "Hardware API circuit breaker CLOSED (Recovered)",
                    extra={"failures_reset": HostDiscoveryService._consecutive_failures},
                )
                HostDiscoveryService._circuit_open = False
                HostDiscoveryService._consecutive_failures = 0

            # Parse response data
            data = response_body if response_body else {}
            hardware_hosts: List[HardwareHostData] = []
            skipped_count = 0  # ✅ Initialize counter

            if isinstance(data, list):
                # Response format: direct array
                for item in data:
                    # ✅ Filter out records with hardware_id as None or empty string
                    hardware_id = item.get("hardware_id") if isinstance(item, dict) else None
                    if not hardware_id or (isinstance(hardware_id, str) and not hardware_id.strip()):
                        skipped_count += 1
                        logger.debug(
                            "Skipping invalid hardware record (hardware_id is empty)",
                            extra={
                                "tc_id": tc_id,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
                        continue

                    try:
                        hardware_hosts.append(HardwareHostData(**item))
                    except Exception as e:
                        # ✅ Catch Pydantic validation error, log detailed information and skip this record
                        skipped_count += 1
                        logger.warning(
                            "Hardware record validation failed, skipping this record",
                            extra={
                                "tc_id": tc_id,
                                "hardware_id": hardware_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
            elif isinstance(data, dict) and "data" in data:
                # Response format: { "data": [...] }
                for item in data["data"]:
                    # ✅ Filter out records with hardware_id as None or empty string
                    hardware_id = item.get("hardware_id") if isinstance(item, dict) else None
                    if not hardware_id or (isinstance(hardware_id, str) and not hardware_id.strip()):
                        skipped_count += 1
                        logger.debug(
                            "Skipping invalid hardware record (hardware_id is empty)",
                            extra={
                                "tc_id": tc_id,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
                        continue

                    try:
                        hardware_hosts.append(HardwareHostData(**item))
                    except Exception as e:
                        # ✅ Catch Pydantic validation error, log detailed information and skip this record
                        skipped_count += 1
                        logger.warning(
                            "Hardware record validation failed, skipping this record",
                            extra={
                                "tc_id": tc_id,
                                "hardware_id": hardware_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "item_keys": list(item.keys()) if isinstance(item, dict) else "N/A",
                            },
                        )
            else:
                logger.warning(
                    "Hardware API response data format does not meet expectations",
                    extra={
                        "response_type": type(data).__name__,
                        "response_keys": (list(data.keys()) if isinstance(data, dict) else "N/A"),
                    },
                )

            # ✅ Record parsing result statistics
            if skipped_count > 0:
                logger.warning(
                    "Hardware API returned invalid records, skipped",
                    extra={
                        "tc_id": tc_id,
                        "skipped_count": skipped_count,
                        "valid_count": len(hardware_hosts),
                        "total_count": skipped_count + len(hardware_hosts),
                    },
                )
            else:
                logger.debug(
                    "Hardware API data parsing completed",
                    extra={
                        "tc_id": tc_id,
                        "valid_count": len(hardware_hosts),
                    },
                )

            return hardware_hosts

        except BusinessError:
            # ✅ Re-raise business exception
            raise
        except Exception as e:
            # ✅ Catch other unexpected exceptions
            logger.error(
                "Hardware API call exception",
                extra={
                    "tc_id": tc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise BusinessError(
                message="Hardware API call exception, please try again later",
                error_code="HOST_HARDWARE_API_ERROR",
                code=ServiceErrorCodes.HOST_OPERATION_FAILED,
                http_status_code=500,
            )

    async def _filter_available_hosts_in_session(
        self,
        session: "AsyncSession",
        hardware_ids: List[str],
    ) -> List[AvailableHostInfo]:
        """Filter available hosts based on conditions (using existing session, optimize connection pool usage)

        This is an optimized version of _filter_available_hosts that accepts an existing session parameter,
        avoiding repeated database connection creation in loops.

        Args:
            session: Database session (already created)
            hardware_ids: Hardware ID list

        Returns:
            Available host list
        """
        if not hardware_ids:
            return []

        # Batch query optimization: if hardware_ids is too many, query in batches
        batch_size = 500
        all_available_hosts: List[AvailableHostInfo] = []

        try:
            total_query_time = 0.0

            # Process hardware_ids in batches
            for i in range(0, len(hardware_ids), batch_size):
                batch_ids = hardware_ids[i : i + batch_size]
                batch_start_time = time.time()

                # Build query conditions (using index optimization)
                # Use composite index: ix_host_rec_hardware_id_state
                # (hardware_id, host_state, appr_state, tcp_state, del_flag)
                stmt = (
                    select(HostRec)
                    .where(
                        and_(
                            HostRec.hardware_id.in_(batch_ids),
                            HostRec.appr_state == 1,  # Enabled state
                            HostRec.host_state == 0,  # Free state
                            HostRec.tcp_state == 2,  # Listening/connected
                            HostRec.del_flag == 0,  # Not deleted
                        )
                    )
                    .limit(1000)
                )  # Limit single query result count

                result = await session.execute(stmt)
                host_recs = result.scalars().all()
                batch_duration = time.time() - batch_start_time
                total_query_time += batch_duration

                # Record slow query (single batch exceeds 200ms)
                if batch_duration > 0.2:
                    logger.warning(
                        "Database batch query took too long",
                        extra={
                            "batch_index": i // batch_size + 1,
                            "batch_size": len(batch_ids),
                            "batch_duration_ms": round(batch_duration * 1000, 2),
                            "result_count": len(host_recs),
                        },
                    )

                # Convert to response format
                batch_hosts: List[AvailableHostInfo] = [
                    AvailableHostInfo(
                        host_rec_id=str(host_rec.id),
                        user_name=host_rec.host_no or "",  # Use host_no instead of host_acct
                        host_ip=cast(str, host_rec.host_ip) if host_rec.host_ip else "",
                    )
                    for host_rec in host_recs
                    if host_rec.hardware_id  # Ensure hardware_id is not empty
                ]

                all_available_hosts.extend(batch_hosts)

            logger.debug(
                "host_rec table query completed (reusing session)",
                extra={
                    "requested_hardware_ids": len(hardware_ids),
                    "available_hosts": len(all_available_hosts),
                    "batches": (len(hardware_ids) + batch_size - 1) // batch_size,
                    "total_query_duration_ms": round(total_query_time * 1000, 2),
                    "avg_query_duration_ms": round(
                        (total_query_time / max(1, (len(hardware_ids) + batch_size - 1) // batch_size)) * 1000,
                        2,
                    ),
                },
            )

            return all_available_hosts

        except Exception as e:
            logger.error(
                "Database query failed",
                extra={
                    "requested_hardware_ids": len(hardware_ids),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise

    async def _filter_available_hosts(
        self,
        hardware_ids: List[str],
    ) -> List[AvailableHostInfo]:
        """Filter available hosts based on conditions (batch query optimization)

        Filter conditions:
        - hardware_id in specified list
        - appr_state = 1 (enabled state)
        - host_state = 0 (free state)
        - tcp_state = 2 (listening/connected)
        - del_flag = 0 (not deleted)

        Performance optimizations:
        - Use hardware_id index to accelerate query
        - Batch query to reduce database round trips
        - Limit query result count to avoid memory overflow
        - Add database connection retry mechanism to handle connection lost issues

        Args:
            hardware_ids: Hardware ID list

        Returns:
            Available host list
        """
        if not hardware_ids:
            return []

        # Batch query optimization: if hardware_ids is too many, query in batches
        # Avoid SQL IN clause being too long (MySQL/MariaDB limitation)
        batch_size = 500
        all_available_hosts: List[AvailableHostInfo] = []

        # Retry configuration
        max_retries = 3
        retry_delay = 1.0  # Initial retry delay (seconds)

        for attempt in range(max_retries):
            try:
                session_factory = self.session_factory
                async with session_factory() as session:
                    # Process hardware_ids in batches
                    for i in range(0, len(hardware_ids), batch_size):
                        batch_ids = hardware_ids[i : i + batch_size]

                        # Build query conditions (using index optimization)
                        stmt = (
                            select(HostRec)
                            .where(
                                and_(
                                    HostRec.hardware_id.in_(batch_ids),
                                    HostRec.appr_state == 1,  # Enabled state
                                    HostRec.host_state == 0,  # Free state
                                    HostRec.tcp_state == 2,  # Listening/connected
                                    HostRec.del_flag == 0,  # Not deleted
                                )
                            )
                            .limit(1000)
                        )  # Limit single query result count

                        result = await session.execute(stmt)
                        host_recs = result.scalars().all()

                        # Convert to response format
                        batch_hosts: List[AvailableHostInfo] = [
                            AvailableHostInfo(
                                host_rec_id=str(host_rec.id),  # ✅ Convert to string to avoid precision loss
                                user_name=host_rec.host_no or "",  # Use host_no instead of host_acct
                                host_ip=cast(str, host_rec.host_ip) if host_rec.host_ip else "",
                            )
                            for host_rec in host_recs
                            if host_rec.hardware_id  # Ensure hardware_id is not empty
                        ]

                        all_available_hosts.extend(batch_hosts)

                    logger.debug(
                        "host_rec table query completed",
                        extra={
                            "requested_hardware_ids": len(hardware_ids),
                            "available_hosts": len(all_available_hosts),
                            "batches": (len(hardware_ids) + batch_size - 1) // batch_size,
                            "attempt": attempt + 1,
                        },
                    )

                    return all_available_hosts

            except OperationalError as e:
                # Database connection error, try retry
                error_code = getattr(e.orig, "args", [None])[0] if hasattr(e, "orig") else None
                is_connection_lost = (
                    error_code == 2013  # Lost connection to MySQL server during query
                    or "Lost connection" in str(e)
                    or "Connection lost" in str(e)
                )

                if is_connection_lost and attempt < max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = retry_delay * (2**attempt)
                    logger.warning(
                        "Database connection lost, preparing to retry",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay_seconds": delay,
                            "error_code": error_code,
                            "error_message": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                    # Clear collected results, restart query
                    all_available_hosts = []
                    continue
                # Retry count exhausted or not a connection lost error, re-raise exception
                logger.error(
                    "Database query failed, cannot retry",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error_code": error_code,
                        "error_message": str(e),
                        "is_connection_lost": is_connection_lost,
                    },
                    exc_info=True,
                )
                raise

        # If all retries failed, return empty list (should not reach here as exception will be raised)
        logger.error(
            "Database query failed, all retries failed",
            extra={
                "requested_hardware_ids": len(hardware_ids),
                "max_retries": max_retries,
            },
        )
        return []
