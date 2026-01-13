"""
Gateway Service API v1 route configuration
"""

from fastapi import APIRouter

from app.api.v1.endpoints import proxy

# Create API router
api_router = APIRouter()

# Register endpoint routes
api_router.include_router(proxy.router, tags=["Proxy Forwarding"])
