# Auth Service (Authentication Service)

## Overview

Auth Service is the authentication service in Intel EC microservice architecture, providing user authentication, device authentication, JWT token management, and other functions.

## Features

- ✅ Administrator login authentication (traditional way)
- ✅ Device login authentication (traditional way)
- ✅ JWT token generation and validation
- ✅ Token refresh mechanism
- ✅ User logout (token blacklisting)
- ✅ Health checks
- ✅ Prometheus monitoring metrics
- ✅ Jaeger distributed tracing

## Tech Stack

- **Python**: 3.8.10
- **Web Framework**: FastAPI 0.116.1
- **Database**: MariaDB (SQLAlchemy async ORM)
- **Cache**: Redis
- **Service Discovery**: Nacos
- **Monitoring**: Prometheus + Jaeger
- **Logging**: Loguru

## Project Structure

```
auth-service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── dependencies.py      # Dependency injection
│   │       └── endpoints/
│   │           └── auth.py          # Authentication endpoints
│   ├── core/                        # Core configuration
│   ├── models/
│   │   ├── user.py                  # User model
│   │   └── user_session.py          # Session model
│   ├── schemas/
│   │   ├── auth.py                  # Authentication data schemas
│   │   └── user.py                  # User data schemas
│   ├── services/
│   │   └── auth_service.py          # Authentication business logic
│   └── main.py                      # Application entry
├── create_tables.py                 # Database table creation script
├── Dockerfile                       # Docker configuration
├── requirements.txt                 # Python dependencies
└── README.md                        # This document
```

## API Endpoints

### Authentication Related

- `POST /api/v1/auth/admin/login` - Admin login
- `POST /api/v1/auth/device/login` - Device login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/introspect` - Validate token
- `POST /api/v1/auth/logout` - User logout

### System Endpoints

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /docs` - API documentation
- `GET /` - Service information

## Database Tables

### sys_user Table (Administrators)

| Field | Type | Description |
|------|------|------|
<<<<<<< HEAD
| id | BIGINT | Primary key ID |
| user_name | VARCHAR(32) | User name |
| user_account | VARCHAR(32) | Login account |
| user_pwd | VARCHAR(128) | Login ***REMOVED***word (bcrypt encrypted) |
| user_avatar | VARCHAR(32) | User avatar |
| email | VARCHAR(32) | Email |
| state_flag | SMALLINT | Account status (0: enabled, 1: disabled) |
| del_flag | SMALLINT | Deletion flag (0: in use, 1: deleted) |
| created_time | DATETIME | Creation time |
| updated_time | DATETIME | Update time |

### host_rec Table (Devices)

| Field | Type | Description |
|------|------|------|
| id | BIGINT | Primary key ID (Snowflake ID) |
| mg_id | VARCHAR(128) | Unique boot ID |
| host_ip | VARCHAR(32) | IP address |
| host_acct | VARCHAR(32) | Host account |
| appr_state | SMALLINT | Approval status |
| host_state | SMALLINT | Host status |
| subm_time | DATETIME | Submission time |
| created_by | BIGINT | Created by (current logged-in user ID, automatically obtained from token) |
| created_time | DATETIME | Creation time |
| updated_by | BIGINT | Updated by (current logged-in user ID, automatically obtained from token) |
| updated_time | DATETIME | Update time |
| del_flag | SMALLINT | Deletion flag (0: in use, 1: deleted) |
=======
| id | INT | 主键ID |
| entity_id | INT | 实体ID（用户或设备ID） |
| entity_type | VARCHAR(50) | 实体类型（admin_user/device） |
| session_id | VARCHAR(255) | 会话ID（唯一） |
| access_token | TEXT | 访问令牌 |
| refresh_token | TEXT | 刷新令牌 |
| client_ip | VARCHAR(45) | 客户端IP |
| expires_at | DATETIME | 过期时间 |
<<<<<<< HEAD
| created_at | DATETIME | 创建时间 |
| is_deleted | BOOLEAN | 是否已删除 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
=======
| created_time | DATETIME | 创建时间 |
| del_flag | BOOLEAN | 是否已删除 |
>>>>>>> 1c319f3 (feat(host): 添加VNC连接结果上报功能-[#16])

### user_sessions Table (Session Management)

| Field | Type | Description |
|------|------|------|
| id | INT | Primary key ID |
| entity_id | INT | Entity ID (user or device ID) |
| entity_type | VARCHAR(50) | Entity type (admin_user/device) |
| session_id | VARCHAR(255) | Session ID (unique) |
| access_token | TEXT | Access token |
| refresh_token | TEXT | Refresh token |
| client_ip | VARCHAR(45) | Client IP |
| expires_at | DATETIME | Expiration time |
| created_time | DATETIME | Creation time |
| del_flag | BOOLEAN | Is deleted |

## Device Login Audit Mechanism

### Problem Description

On 2025-10-20, it was found that during device login, the `id` field in the `host_rec` table reported an error: `Field 'id' doesn't have a default value`.

### Solution

#### 1. Primary key changed to Snowflake ID generation

```python
# app/models/host_rec.py
def generate_snowflake_id() -> int:
    """Generate Snowflake ID"""
    import random, time
    timestamp = int(time.time() * 1000)
    random_part = random.randint(0, 999999)
    return (timestamp << 20) | random_part

class HostRec(Base):
    id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        default=generate_snowflake_id,
        comment="Primary key (Snowflake ID)"
    )
```

#### 2. Audit fields automatic setting

During device login, automatically get user ID from JWT token and set `created_by` and `updated_by` fields:

```python
# app/services/auth_service.py
async def device_login(
    self, login_data: DeviceLoginRequest, 
    current_user_id: Optional[int] = None
) -> LoginResponse:
    # When creating new device
    host_rec = HostRec(
        mg_id=login_data.mg_id,
        host_ip=login_data.host_ip,
        host_acct=login_data.username,
        created_by=current_user_id,      # Set creator
        created_time=datetime.now(timezone.utc),
        updated_by=current_user_id,      # Set updater
        updated_time=datetime.now(timezone.utc),
        del_flag=0,
    )
    
    # When updating existing device
    if host_rec:
        host_rec.host_ip = login_data.host_ip
        host_rec.host_acct = login_data.username
        host_rec.updated_by = current_user_id  # Updater
        host_rec.updated_time = datetime.now(timezone.utc)
```

#### 3. API endpoint gets current user information

```python
# app/api/v1/endpoints/auth.py
@router.post("/device/login")
async def device_login(
    login_data: DeviceLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Optional[dict] = Depends(get_current_user),  # Get current user
) -> SuccessResponse:
    # Extract user_id from token
    current_user_id = None
    if current_user:
        current_user_id = int(current_user.get("sub", 0)) if current_user.get("sub") else None
    
    # Pass to service layer
    login_response = await auth_service.device_login(
        login_data, 
        current_user_id=current_user_id
    )
```

### Audit Tracking Advantages

- ✅ Record when device was created and by whom
- ✅ Record when device was updated and by whom
- ✅ Complete audit trail chain
- ✅ Facilitate issue troubleshooting and log analysis

### Environment Variables

```bash
# Service configuration
SERVICE_NAME=auth-service
SERVICE_PORT=8001
SERVICE_IP=172.20.0.101

# Database configuration
MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/intel_cw

# Redis configuration
REDIS_URL=redis://redis:6379/1

# Nacos configuration
NACOS_SERVER_ADDR=172.20.0.12:8848

# Jaeger configuration
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces
```

## Quick Start

### 1. Create database tables

```bash
cd services/auth-service
python create_tables.py create
```

### 2. Start the service

> **💡 Tip**: When starting locally, the code will automatically load the `.env` file from the project root directory.

```bash
# Development mode (supports hot reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Environment Variable Configuration**:
- If the database is in Docker, you need to set the correct database host address in the `.env` file
- For detailed configuration, please refer to [Quick Start Guide](../../docs/00-quick-start.md#step-7-start-microservices-locally-non-docker-way)

### 3. Docker Deployment

```bash
# Build image
docker build -t intel-cw-ms/auth-service:latest -f services/auth-service/Dockerfile .

# Run container
docker run -d \
  --name auth-service \
  -p 8001:8001 \
  -e MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/intel_cw \
  -e REDIS_URL=redis://redis:6379/1 \
  intel-cw-ms/auth-service:latest
```

## API Usage Examples

<<<<<<< HEAD
### Administrator Login
=======
### 管理员登录
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

```bash
curl -X POST http://localhost:8001/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "***REMOVED***word": "***REMOVED***"
  }'
```

Response:

```json
{
  "code": 200,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
<<<<<<< HEAD
=======
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### 设备登录

```bash
curl -X POST http://localhost:8001/api/v1/auth/device/login \
  -H "Content-Type: application/json" \
  -d '{
    "mg_id": "device-12345",
    "host_ip": "192.168.1.100",
    "username": "root"
  }'
```

响应：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### Device Login

```bash
curl -X POST http://localhost:8001/api/v1/auth/device/login \
  -H "Content-Type: application/json" \
  -d '{
    "mg_id": "device-12345",
    "host_ip": "192.168.1.100",
    "username": "root"
  }'
```

Response:

```json
{
  "code": 200,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```
<<<<<<< HEAD
=======

### 用户注销

```bash
curl -X POST http://localhost:8001/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

## 监控和健康检查

### 健康检查

```bash
curl http://localhost:8001/health
```

### Prometheus 指标

```bash
curl http://localhost:8001/metrics
```

## 开发指南

### 添加新的认证方式

1. 在 `app/schemas/auth.py` 中定义新的请求/响应模式
2. 在 `app/services/auth_service.py` 中实现业务逻辑
3. 在 `app/api/v1/endpoints/auth.py` 中添加新的端点
4. 更新 API 文档

### 代码质量检查

```bash
# Ruff 检查
ruff check services/auth-service/

# MyPy 类型检查
mypy services/auth-service/

# Black 格式化
black services/auth-service/
```

## 故障排查

### 数据库连接失败

1. 检查 MariaDB 服务是否运行
2. 验证 `MARIADB_URL` 环境变量配置
3. 检查数据库用户权限

### Redis 连接失败

1. 检查 Redis 服务是否运行
2. 验证 `REDIS_URL` 环境变量配置
3. 检查 Redis 网络连接

### Nacos 注册失败

1. 检查 Nacos 服务是否运行
2. 验证 `NACOS_SERVER_ADDR` 配置
3. 检查服务 IP 和端口配置

## 相关文档

- [项目总体规范](../../.cursor/rules/project-overview.mdc)
- [微服务架构规范](../../.cursor/rules/microservice-architecture.mdc)
- [API 设计规范](../../.cursor/rules/api-design-standards.mdc)
- [认证安全规范](../../.cursor/rules/auth-security.mdc)

## 更新历史

- **2025-10-17**: 重构认证方式，移除 OAuth 2.0
  - 实现传统登录方式
  - 添加管理员登录接口（使用 sys_user 表）
  - 添加设备登录接口（使用 host_rec 表）
  - 移除 OAuth 2.0 相关代码
  - 简化认证流程

- **2025-01-29**: 初始版本，实现基础认证功能
  - 用户登录认证
  - JWT 令牌管理
  - 令牌刷新和验证
  - 用户注销
  - 健康检查和监控
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
