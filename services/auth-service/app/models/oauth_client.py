"""
OAuth 2.0客户端数据模型

定义OAuth客户端表结构和字段
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

# 使用 try-except 方式处理路径导入
try:
    from shared.common.database import Base
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from shared.common.database import Base


class OAuthClient(Base):
    """OAuth 2.0客户端模型"""

    __tablename__ = "oauth_clients"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键ID")

    # 客户端基本信息
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment="客户端ID")
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端密钥哈希")
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="客户端名称")

    # 客户端类型
    client_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="confidential", comment="客户端类型 (confidential/public)"
    )

    # OAuth 2.0配置
    grant_types: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, comment="支持的授权类型")
    response_types: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, comment="支持的响应类型")
    redirect_uris: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, comment="重定向URI")
    scope: Mapped[str] = mapped_column(String(255), nullable=False, default="read write", comment="授权范围")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否激活")

    # 时间字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<OAuthClient(id={self.id}, client_id={self.client_id}, client_name={self.client_name})>"
