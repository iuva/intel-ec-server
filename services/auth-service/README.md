# Auth Service (认证服务)

## 概述

Auth Service 是 Intel EC 微服务架构中的认证服务，提供用户认证、设备认证、JWT令牌管理等功能。

## 功能特性

- ✅ 管理员登录认证（传统方式）
- ✅ 设备登录认证（传统方式）
- ✅ JWT 令牌生成和验证
- ✅ 令牌刷新机制
- ✅ 用户注销（令牌黑名单）
- ✅ 健康检查
- ✅ Prometheus 监控指标
- ✅ Jaeger 分布式追踪

## 技术栈

- **Python**: 3.8.10
- **Web框架**: FastAPI 0.116.1
- **数据库**: MariaDB (SQLAlchemy 异步ORM)
- **缓存**: Redis
- **服务发现**: Nacos
- **监控**: Prometheus + Jaeger
- **日志**: Loguru

## 项目结构

```
auth-service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── dependencies.py      # 依赖注入
│   │       └── endpoints/
│   │           └── auth.py          # 认证端点
│   ├── core/                        # 核心配置
│   ├── models/
│   │   ├── user.py                  # 用户模型
│   │   └── user_session.py          # 会话模型
│   ├── schemas/
│   │   ├── auth.py                  # 认证数据模式
│   │   └── user.py                  # 用户数据模式
│   ├── services/
│   │   └── auth_service.py          # 认证业务逻辑
│   └── main.py                      # 应用入口
├── create_tables.py                 # 数据库表创建脚本
├── Dockerfile                       # Docker配置
├── requirements.txt                 # Python依赖
└── README.md                        # 本文档
```

## API 端点

### 认证相关

- `POST /api/v1/auth/admin/login` - 管理员登录
- `POST /api/v1/auth/device/login` - 设备登录
- `POST /api/v1/auth/refresh` - 刷新访问令牌
- `POST /api/v1/auth/introspect` - 验证令牌
- `POST /api/v1/auth/logout` - 用户注销

### 系统端点

- `GET /health` - 健康检查
- `GET /metrics` - Prometheus 指标
- `GET /docs` - API 文档
- `GET /` - 服务信息

## 数据库表

### sys_user 表（管理员）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键ID |
| user_name | VARCHAR(32) | 用户名称 |
| user_account | VARCHAR(32) | 登录账号 |
| user_pwd | VARCHAR(128) | 登录密码（bcrypt加密） |
| user_avatar | VARCHAR(32) | 用户头像 |
| email | VARCHAR(32) | 邮箱 |
| state_flag | SMALLINT | 账号状态（0:启用, 1:停用） |
| del_flag | SMALLINT | 删除标识（0:使用中, 1:删除） |
| created_time | DATETIME | 创建时间 |
| updated_time | DATETIME | 更新时间 |

### host_rec 表（设备）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键ID（雪花ID） |
| mg_id | VARCHAR(128) | 唯一引导ID |
| host_ip | VARCHAR(32) | IP地址 |
| host_acct | VARCHAR(32) | 主机账号 |
| appr_state | SMALLINT | 审批状态 |
| host_state | SMALLINT | 主机状态 |
| subm_time | DATETIME | 申报时间 |
| created_by | BIGINT | 创建人（当前登录用户ID，从token自动获取） |
| created_time | DATETIME | 创建时间 |
| updated_by | BIGINT | 更新人（当前登录用户ID，从token自动获取） |
| updated_time | DATETIME | 更新时间 |
| del_flag | SMALLINT | 删除标识（0:使用中, 1:删除） |

### user_sessions 表（会话管理）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键ID |
| entity_id | INT | 实体ID（用户或设备ID） |
| entity_type | VARCHAR(50) | 实体类型（admin_user/device） |
| session_id | VARCHAR(255) | 会话ID（唯一） |
| access_token | TEXT | 访问令牌 |
| refresh_token | TEXT | 刷新令牌 |
| client_ip | VARCHAR(45) | 客户端IP |
| expires_at | DATETIME | 过期时间 |
| created_time | DATETIME | 创建时间 |
| del_flag | BOOLEAN | 是否已删除 |

## 设备登录（Device Login）审计机制

### 问题描述

2025-10-20 发现设备登录（Device Login）时 `host_rec` 表中 `id` 字段报错：`Field 'id' doesn't have a default value`。

### 解决方案

#### 1. 主键改为雪花ID生成

```python
# app/models/host_rec.py
def generate_snowflake_id() -> int:
    """生成雪花ID"""
    import random, time
    timestamp = int(time.time() * 1000)
    random_part = random.randint(0, 999999)
    return (timestamp << 20) | random_part

class HostRec(Base):
    id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        default=generate_snowflake_id,
        comment="主键（雪花ID）"
    )
```

#### 2. 审计字段自动设置

设备登录时自动从 JWT token 中获取用户 ID，设置 `created_by` 和 `updated_by` 字段：

```python
# app/services/auth_service.py
async def device_login(
    self, login_data: DeviceLoginRequest, 
    current_user_id: Optional[int] = None
) -> LoginResponse:
    # 创建新设备时
    host_rec = HostRec(
        mg_id=login_data.mg_id,
        host_ip=login_data.host_ip,
        host_acct=login_data.username,
        created_by=current_user_id,      # 设置创建人
        created_time=datetime.now(timezone.utc),
        updated_by=current_user_id,      # 设置更新人
        updated_time=datetime.now(timezone.utc),
        del_flag=0,
    )
    
    # 更新现有设备时
    if host_rec:
        host_rec.host_ip = login_data.host_ip
        host_rec.host_acct = login_data.username
        host_rec.updated_by = current_user_id  # 更新人
        host_rec.updated_time = datetime.now(timezone.utc)
```

#### 3. API 端点获取当前用户信息

```python
# app/api/v1/endpoints/auth.py
@router.post("/device/login")
async def device_login(
    login_data: DeviceLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Optional[dict] = Depends(get_current_user),  # 获取当前用户
) -> SuccessResponse:
    # 从 token 中提取 user_id
    current_user_id = None
    if current_user:
        current_user_id = int(current_user.get("sub", 0)) if current_user.get("sub") else None
    
    # 传递给服务层
    login_response = await auth_service.device_login(
        login_data, 
        current_user_id=current_user_id
    )
```

### 审计追踪优势

- ✅ 记录设备何时创建、由谁创建
- ✅ 记录设备何时更新、由谁更新
- ✅ 完整的操作审计追踪链
- ✅ 便于问题排查和日志分析

### 环境变量

```bash
# 服务配置
SERVICE_NAME=auth-service
SERVICE_PORT=8001
SERVICE_IP=172.20.0.101

# 数据库配置
MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/intel_cw

# Redis配置
REDIS_URL=redis://redis:6379/1

# Nacos配置
NACOS_SERVER_ADDR=172.20.0.12:8848

# Jaeger配置
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces
```

## 快速开始

### 1. 创建数据库表

```bash
cd services/auth-service
python create_tables.py create
```

### 2. 启动服务

> **💡 提示**: 本地启动时，代码会自动加载项目根目录的 `.env` 文件。

```bash
# 开发模式（支持热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 生产模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**环境变量配置**:
- 如果数据库在 Docker 中，需要在 `.env` 文件中设置正确的数据库主机地址
- 详细配置请参考 [快速开始指南](../../docs/00-quick-start.md#步骤-7-本地启动微服务非-docker-方式)

### 3. Docker 部署

```bash
# 构建镜像
docker build -t intel-cw-ms/auth-service:latest -f services/auth-service/Dockerfile .

# 运行容器
docker run -d \
  --name auth-service \
  -p 8001:8001 \
  -e MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/intel_cw \
  -e REDIS_URL=redis://redis:6379/1 \
  intel-cw-ms/auth-service:latest
```

## API 使用示例

### 管理员登录

```bash
curl -X POST http://localhost:8001/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "***REMOVED***word": "***REMOVED***"
  }'
```

响应：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400
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
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```