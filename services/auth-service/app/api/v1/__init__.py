"""
API v1 Version

Register all v1 version routes
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router

# Create v1 API router
api_router = APIRouter()

# Register endpoint routes - Using /auth prefix
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

__all__ = ["api_router"]
