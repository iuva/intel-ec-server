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
    refresh_expires_in: Optional[int] = Field(default=None, description="刷新令牌过期时间（秒）")

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
    """刷新令牌请求"""

    refresh_token: str = Field(description="刷新令牌")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class AutoRefreshTokenRequest(BaseModel):
    """自动续期令牌请求（同时续期 access_token 和 refresh_token）"""

    refresh_token: str = Field(description="当前刷新令牌")
    auto_renew: bool = Field(default=True, description="是否自动续期 refresh_token")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "auto_renew": True,
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
    user_id: Optional[str] = Field(default=None, description="用户ID")
    exp: Optional[int] = Field(default=None, description="过期时间戳")
    token_type: Optional[str] = Field(default=None, description="令牌类型")
    # 新增字段：支持设备登录的额外信息
    user_type: Optional[str] = Field(default=None, description="用户类型（admin/device）")
    mg_id: Optional[str] = Field(default=None, description="设备管理ID")
    host_ip: Optional[str] = Field(default=None, description="主机IP")
    sub: Optional[str] = Field(default=None, description="Subject（用户/设备ID）")

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

    username: str = Field(description="用户名")
    ***REMOVED***word: str = Field(description="密码")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "***REMOVED***word": "***REMOVED***",
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
