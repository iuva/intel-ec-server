"""
Pydantic Data Schemas for Authentication

Define request and response schemas for login, tokens, etc.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Token Response"""

    access_token: str = Field(description="Access token")
    refresh_token: str = Field(description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Expiration time (seconds)")
    refresh_expires_in: Optional[int] = Field(default=None, description="Refresh token expiration time (seconds)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "refresh_expires_in": 604800,
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """Refresh Token Request"""

    refresh_token: str = Field(description="Refresh token")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class AutoRefreshTokenRequest(BaseModel):
    """Auto-refresh Token Request (renew both access_token and refresh_token simultaneously)"""

    refresh_token: str = Field(description="Current refresh token")
    auto_renew: bool = Field(default=True, description="Whether to automatically renew refresh_token")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "auto_renew": True,
            }
        }
    }


class IntrospectRequest(BaseModel):
    """Token Validation Request"""

    token: str = Field(description="Token to be validated")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class IntrospectResponse(BaseModel):
    """Token Validation Response"""

    active: bool = Field(description="Whether the token is valid")
    id: Optional[str] = Field(default=None, description="User/Device ID (unified field name)")
    username: Optional[str] = Field(default=None, description="Username")
    user_id: Optional[str] = Field(default=None, description="User ID (compatibility field, deprecated, use id)")
    exp: Optional[int] = Field(default=None, description="Expiration timestamp")
    token_type: Optional[str] = Field(default=None, description="Token type")
    # Additional fields: Support additional information for device login
    user_type: Optional[str] = Field(default=None, description="User type (admin/device)")
    mg_id: Optional[str] = Field(default=None, description="Device management ID")
    host_ip: Optional[str] = Field(default=None, description="Host IP")
    sub: Optional[str] = Field(default=None, description="Subject (user/device ID, compatibility field)")
    error: Optional[str] = Field(default=None, description="Error message (when active=False)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "active": True,
                "username": "admin",
                "user_id": "1",
                "exp": 1640995200,
                "token_type": "access",
            }
        }
    }


class LogoutRequest(BaseModel):
    """Logout Request"""

    token: str = Field(description="Access token")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class AdminLoginRequest(BaseModel):
    """Admin Login Request"""

    username: str = Field(description="Username")
    ***REMOVED***word: str = Field(description="Password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "***REMOVED***word": "***REMOVED***",
            }
        }
    }


class DeviceLoginRequest(BaseModel):
    """Device Login Request"""

    mg_id: str = Field(description="Unique boot ID")
    host_ip: str = Field(description="Host IP address")
    username: str = Field(description="Host account")

    model_config = {
        "json_schema_extra": {
            "example": {
                "mg_id": "device-12345",
                "host_ip": "192.168.1.100",
                "username": "root",
            }
        }
    }


class LoginResponse(BaseModel):
    """Login Response"""

    access_token: str = Field(description="Access token")
    token: Optional[str] = Field(
        default=None,
        description="Access token compatibility field (same as access_token, retained for backward compatibility)",
    )
    refresh_token: Optional[str] = Field(default=None, description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Expiration time (seconds)")
    refresh_expires_in: Optional[int] = Field(default=None, description="Refresh token expiration time (seconds)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "refresh_expires_in": 604800,
            }
        }
    }


class DeviceLoginRequest(BaseModel):
    """设备登录请求"""

    mg_id: str = Field(description="唯一引导ID")
    host_ip: str = Field(description="主机IP地址")
    username: str = Field(description="主机账号")

    model_config = {
        "json_schema_extra": {
            "example": {
                "mg_id": "device-12345",
                "host_ip": "192.168.1.100",
                "username": "root",
            }
        }
    }


class LoginResponse(BaseModel):
    """登录响应"""

    token: str = Field(description="访问令牌")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间（秒）")
    refresh_expires_in: Optional[int] = Field(default=None, description="刷新令牌过期时间（秒）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "refresh_expires_in": 604800,
            }
        }
    }


class TokenResponseSuccessResponse(BaseModel):
    """令牌响应成功包装模型

    用于 FastAPI 文档展示，明确指定 data 字段的类型
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="操作成功", description="响应消息")
    data: TokenResponse = Field(description="令牌数据")
    timestamp: str = Field(description="响应时间戳")

    model_config = {"from_attributes": True}


class LoginResponseSuccessResponse(BaseModel):
    """登录响应成功包装模型

    用于 FastAPI 文档展示，明确指定 data 字段的类型
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="登录成功", description="响应消息")
    data: LoginResponse = Field(description="登录数据")
    timestamp: str = Field(description="响应时间戳")

    model_config = {"from_attributes": True}


class IntrospectResponseSuccessResponse(BaseModel):
    """令牌验证响应成功包装模型

    用于 FastAPI 文档展示，明确指定 data 字段的类型
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="验证成功", description="响应消息")
    data: IntrospectResponse = Field(description="验证结果数据")
    timestamp: str = Field(description="响应时间戳")

    model_config = {"from_attributes": True}
