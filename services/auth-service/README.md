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
| id | BIGINT | 主键ID |
| mg_id | VARCHAR(128) | 唯一引导ID |
| host_ip | VARCHAR(32) | IP地址 |
| host_acct | VARCHAR(32) | 主机账号 |
| appr_state | SMALLINT | 审批状态 |
| host_state | SMALLINT | 主机状态 |
| subm_time | DATETIME | 申报时间 |
| del_flag | SMALLINT | 删除标识（0:使用中, 1:删除） |
| created_time | DATETIME | 创建时间 |
| updated_time | DATETIME | 更新时间 |

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
| created_at | DATETIME | 创建时间 |
| is_deleted | BOOLEAN | 是否已删除 |

## 环境变量

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

```bash
# 开发模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 生产模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

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
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### 刷新令牌

```bash
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### 验证令牌

```bash
curl -X POST http://localhost:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

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
