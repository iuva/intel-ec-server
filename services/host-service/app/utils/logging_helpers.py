"""Logging helper functions

Provides unified logging utility functions, re-exports shared module functions to maintain backward compatibility.

Note: This module is kept for backward compatibility, new code should import directly from shared.utils.logging_utils.
"""

# Re-export shared module functions to maintain backward compatibility
from shared.utils.logging_utils import (
    log_auth_failure,
    log_auth_success,
    log_db_error,
    log_db_query,
    log_external_api_call,
    log_external_api_error,
    log_operation_completed,
    log_operation_failed,
    log_operation_start,
    log_request_completed,
    log_request_received,
    log_service_shutdown,
    log_service_startup,
    log_websocket_connect,
    log_websocket_disconnect,
    log_websocket_message,
    timed_operation,
    timed_operation_sync,
    with_request_logging,
)

__all__ = [
    # Basic logging
    "log_request_received",
    "log_request_completed",
    "log_operation_start",
    "log_operation_completed",
    "log_operation_failed",
    # Database logging
    "log_db_query",
    "log_db_error",
    # External API logging
    "log_external_api_call",
    "log_external_api_error",
    # Performance tracking
    "timed_operation",
    "timed_operation_sync",
    # Decorators
    "with_request_logging",
    # WebSocket logging
    "log_websocket_connect",
    "log_websocket_disconnect",
    "log_websocket_message",
    # Authentication logging
    "log_auth_success",
    "log_auth_failure",
    # Service logging
    "log_service_startup",
    "log_service_shutdown",
]
