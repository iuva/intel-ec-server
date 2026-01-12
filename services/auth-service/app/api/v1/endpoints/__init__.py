"""
API endpoints module

Export all endpoint routes
"""

from app.api.v1.endpoints.auth import router as auth_router

__all__ = ["auth_router"]
