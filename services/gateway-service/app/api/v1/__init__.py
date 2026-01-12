"""
Gateway Service API v1 route configuration
"""

from app.api.v1.endpoints import proxy
from fastapi import APIRouter

# Create API router
api_router = APIRouter()

# Register endpoint routes
api_router.include_router(proxy.router, tags=["Proxy Forwarding"])
