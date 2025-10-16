"""
认证相关的 Pydantic 数据模式

定义登录、令牌等请求和响应模式
"""

from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """令牌响应"""

    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间（秒）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(description="刷新令牌")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class IntrospectRequest(BaseModel):
    """令牌验证请求"""

    token: str = Field(description="待验证的令牌")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class IntrospectResponse(BaseModel):
    """令牌验证响应"""

    active: bool = Field(description="令牌是否有效")
    username: Optional[str] = Field(default=None, description="用户名")
    user_id: Optional[int] = Field(default=None, description="用户ID")
    exp: Optional[int] = Field(default=None, description="过期时间戳")
    token_type: Optional[str] = Field(default=None, description="令牌类型")

    model_config = {
        "json_schema_extra": {
            "example": {
                "active": True,
                "username": "admin",
                "user_id": 1,
                "exp": 1640995200,
                "token_type": "access",
            }
        }
    }


class LogoutRequest(BaseModel):
    """注销请求"""

    token: str = Field(description="访问令牌")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class AdminLoginRequest(BaseModel):
    """管理后台登录请求"""

    user_account: str = Field(description="用户账号")
    ***REMOVED***word: str = Field(description="密码")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_account": "admin",
                "***REMOVED***word": "***REMOVED***",
            }
        }
    }
