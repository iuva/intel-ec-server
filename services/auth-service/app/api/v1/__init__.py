"""
API v1 Version

Register all v1 version routes
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router

# Create v1 API router
api_router = APIRouter()

<<<<<<< HEAD
<<<<<<< HEAD
# Register endpoint routes - Using /auth prefix
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
=======
# 注册端点路由（去掉/auth前缀，与其他服务保持一致）
api_router.include_router(auth_router, prefix="", tags=["认证"])
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
# 注册端点路由 - 使用 /auth 前缀
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
>>>>>>> 1d435cd (fix: 修复WebSocket 403问题 - 修复auth-service路由前缀注册错误)

__all__ = ["api_router"]
