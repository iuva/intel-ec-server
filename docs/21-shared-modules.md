# 共享模块 (Shared Modules)

本目录包含所有微服务共享的通用功能模块。

## 目录结构

```
shared/
├── app/                    # 应用模块
│   ├── application.py      # FastAPI应用模板
│   └── __init__.py
├── common/                 # 通用模块
│   ├── cache.py           # Redis缓存管理
│   ├── database.py        # MySQL数据库连接管理
│   ├── decorators.py      # 装饰器工具
│   ├── exceptions.py      # 异常处理
│   ├── http_client.py     # 异步HTTP客户端
│   ├── loguru_config.py   # 日志配置
│   ├── response.py        # 统一响应格式
│   ├── security.py        # 认证和安全工具
│   └── __init__.py
├── config/                 # 配置模块
│   ├── nacos_config.py    # Nacos服务发现
│   └── __init__.py
├── monitoring/             # 监控模块
│   ├── jaeger.py          # Jaeger分布式追踪
│   ├── metrics.py         # Prometheus指标收集
│   └── __init__.py
├── middleware/             # 中间件模块
│   └── __init__.py
├── models/                 # 模型模块
│   └── __init__.py
└── services/               # 服务模块
    └── __init__.py
```

## 模块说明

### 1. 应用模块 (app/)

#### application.py
- **功能**: 提供统一的FastAPI应用创建和配置
- **主要类/函数**:
  - `create_fastapi_app()`: 创建配置好的FastAPI应用
  - `create_lifespan_handler()`: 创建应用生命周期处理器
  - `create_exception_handlers()`: 创建全局异常处理器

### 2. 通用模块 (common/)

#### database.py
- **功能**: MySQL异步连接池管理
- **主要类**:
  - `MySQLManager`: MySQL连接管理器
  - `BaseDBModel`: 数据库模型基类
  - `Base`: SQLAlchemy声明式基类
- **全局实例**: `mariadb_manager`

#### cache.py
- **功能**: Redis异步缓存管理
- **主要类**:
  - `RedisManager`: Redis缓存管理器
- **装饰器**:
  - `@cache_result`: 缓存函数结果
- **全局实例**: `redis_manager`

#### response.py
- **功能**: 统一的API响应格式
- **主要类**:
  - `SuccessResponse`: 成功响应
  - `ErrorResponse`: 错误响应
  - `PaginationResponse`: 分页响应
  - `PaginationInfo`: 分页信息

#### security.py
- **功能**: JWT令牌管理和密码加密
- **主要类**:
  - `JWTManager`: JWT令牌管理器
- **主要函数**:
  - `hash_***REMOVED***word()`: 密码加密
  - `verify_***REMOVED***word()`: 密码验证
  - `init_jwt_manager()`: 初始化JWT管理器
  - `get_jwt_manager()`: 获取JWT管理器

#### exceptions.py
- **功能**: 统一的异常处理
- **主要类**:
  - `BusinessError`: 业务异常基类
  - `ErrorCodes`: 错误码常量
  - `AuthenticationError`: 认证异常
  - `AuthorizationError`: 授权异常
  - `ValidationError`: 验证异常
  - `ResourceNotFoundError`: 资源不存在异常
  - `DatabaseError`: 数据库异常

#### decorators.py
- **功能**: 提供常用装饰器
- **主要装饰器**:
  - `@handle_service_errors`: 服务层错误处理
  - `@handle_api_errors`: API 层错误处理
  - `@monitor_operation`: 业务操作监控
- **使用场景**:
  - 统一错误处理
  - 自动日志记录
  - 监控指标收集

#### http_client.py
- **功能**: 异步 HTTP 客户端管理
- **主要类**:
  - `AsyncHTTPClient`: 异步 HTTP 客户端
- **主要方法**:
  - `request()`: 发送 HTTP 请求
  - `close()`: 关闭客户端连接
- **特性**:
  - 连接池管理
  - 超时配置
  - 自动重试

#### loguru_config.py
- **功能**: 基于Loguru的日志配置
- **主要函数**:
  - `configure_logger()`: 配置日志系统
  - `get_logger()`: 获取日志记录器
  - `log_request()`: 记录HTTP请求
  - `log_exception()`: 记录异常

### 3. 配置模块 (config/)

#### nacos_config.py
- **功能**: Nacos服务发现和配置管理
- **主要类**:
  - `NacosManager`: Nacos管理器
- **主要方法**:
  - `register_service()`: 注册服务
  - `deregister_service()`: 注销服务
  - `discover_service()`: 发现服务
  - `start_heartbeat()`: 启动心跳
  - `stop_heartbeat()`: 停止心跳
- **全局实例**: `nacos_manager`

### 4. 监控模块 (monitoring/)

#### jaeger.py
- **功能**: Jaeger分布式追踪
- **主要类**:
  - `JaegerManager`: Jaeger管理器
- **主要函数**:
  - `init_jaeger()`: 初始化追踪
  - `get_tracer()`: 获取追踪器
  - `instrument_app()`: 为应用添加追踪
  - `instrument_database()`: 为数据库添加追踪
  - `instrument_cache()`: 为缓存添加追踪
- **全局实例**: `jaeger_manager`

#### metrics.py
- **功能**: Prometheus监控指标收集
- **主要类**:
  - `MetricsCollector`: 指标收集器
- **主要指标**:
  - HTTP请求指标
  - 数据库查询指标
  - 缓存操作指标
  - 业务操作指标
  - 系统指标
- **全局实例**: `metrics_collector`

## 使用示例

### 创建FastAPI应用

```python
from shared.app.application import create_fastapi_app

app = create_fastapi_app(
    service_name="my-service",
    service_version="1.0.0",
    database_url="mysql+aiomysql://user:***REMOVED***@localhost:3306/db",
    redis_url="redis://localhost:6379/0",
    jwt_secret_key="your-secret-key",
    jaeger_endpoint="http://localhost:4318/v1/traces",
    log_level="INFO"
)
```

### 使用数据库

```python
from shared.common.database import mariadb_manager, BaseDBModel
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

# 定义模型
class User(BaseDBModel):
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

# 使用数据库
async with mariadb_manager.get_session()() as session:
    user = User(username="admin", email="admin@example.com")
    session.add(user)
    await session.commit()
```

### 使用缓存

```python
from shared.common.cache import redis_manager, cache_result

# 直接使用
await redis_manager.set("key", "value", expire=3600)
value = await redis_manager.get("key")

# 使用装饰器
@cache_result(expire=3600, key_prefix="user")
async def get_user(user_id: str):
    # 函数结果会自动缓存
    return {"id": user_id, "name": "John"}
```

### 使用统一响应

```python
from shared.common.response import create_success_response, create_error_response

# 成功响应
return create_success_response(
    data={"user_id": "123"},
    message="用户创建成功"
)

# 错误响应
return create_error_response(
    message="用户不存在",
    error_code="USER_NOT_FOUND",
    code=404
)
```

### 使用JWT认证

```python
from shared.common.security import get_jwt_manager

jwt_manager = get_jwt_manager()

# 创建令牌
access_token = jwt_manager.create_access_token({"sub": "user_id"})
refresh_token = jwt_manager.create_refresh_token({"sub": "user_id"})

# 验证令牌
payload = jwt_manager.verify_token(access_token)
```

### 使用Nacos服务发现

```python
from shared.config.nacos_config import nacos_manager

# 注册服务
await nacos_manager.register_service(
    service_name="my-service",
    ip="127.0.0.1",
    port=8000,
    ephemeral=True
)

# 启动心跳
await nacos_manager.start_heartbeat(
    service_name="my-service",
    ip="127.0.0.1",
    port=8000,
    interval=5
)

# 发现服务
instances = await nacos_manager.discover_service("other-service")
```

### 使用装饰器

```python
from shared.common.decorators import (
    handle_service_errors,
    handle_api_errors,
    monitor_operation,
)

# 服务层使用
@monitor_operation("user_create", record_duration=True)
@handle_service_errors(
    error_message="创建用户失败",
    error_code="USER_CREATE_FAILED",
)
async def create_user(user_data: dict):
    """创建用户"""
    # 业务逻辑
    ***REMOVED***

# API 层使用
@router.post("/users")
@handle_api_errors
async def create_user_endpoint(user_data: dict):
    """创建用户 API 端点"""
    user = await user_service.create_user(user_data)
    return SuccessResponse(data=user, message="用户创建成功")
```

### 使用 HTTP 客户端

```python
from shared.common.http_client import AsyncHTTPClient

# 创建客户端
http_client = AsyncHTTPClient()

# 发送请求
response = await http_client.request(
    method="GET",
    url="http://example.com/api/users",
    headers={"Authorization": "Bearer token"},
)

# 关闭客户端
await http_client.close()
```

### 使用监控指标

```python
from shared.monitoring.metrics import metrics_collector

# 记录HTTP请求
metrics_collector.record_http_request(
    method="GET",
    endpoint="/api/users",
    status=200,
    duration=0.123
)

# 记录数据库查询
metrics_collector.record_db_query(
    operation="select",
    table="users",
    duration=0.05
)

# 记录缓存操作
metrics_collector.record_cache_operation(
    operation="get",
    hit=True,
    duration=0.001
)
```

## 依赖要求

所有共享模块的依赖已在项目根目录的 `requirements.txt` 中定义。

## 注意事项

1. 所有异步函数必须使用 `async/await` 语法
2. 数据库连接和Redis连接需要在应用启动时初始化
3. JWT管理器需要在使用前初始化
4. 日志配置应在应用启动时完成
5. 所有模块都支持Python 3.8.10

## 更新日志

- **2025-10-16**: 添加装饰器模块和 HTTP 客户端模块
  - 新增 `decorators.py`：提供错误处理和监控装饰器
  - 新增 `http_client.py`：提供异步 HTTP 客户端
  - 更新文档和使用示例
- **2025-01-29**: 初始版本，实现所有核心共享模块
