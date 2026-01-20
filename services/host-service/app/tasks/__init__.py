"""
Host Service Background Tasks Package

This package contains various background scheduled tasks and worker services.
It uses a robust import mechanism to support both module usage and direct script execution.
"""

try:
    from app.tasks.case_timeout_task import CaseTimeoutTaskService, get_case_timeout_task_service
except ImportError:
    import os
    import sys

    # Handle import paths when running as a standalone script or in different environments
    # Add project root directory to Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from app.tasks.case_timeout_task import CaseTimeoutTaskService, get_case_timeout_task_service

__all__ = ["CaseTimeoutTaskService", "get_case_timeout_task_service"]
