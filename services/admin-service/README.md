# Admin Service

管理服务 - 提供后台管理、用户管理、系统配置等功能

## 功能特性

- 用户管理（CRUD操作）
- 用户搜索和分页
- JWT认证和权限检查
- 健康检查和监控
- Jaeger分布式追踪

## 技术栈

- **Python**: 3.8.10
- **Web框架**: FastAPI 0.116.1
- **数据库**: MariaDB (SQLAlchemy异步ORM)
- **缓存**: Redis
- **服务发现**: Nacos
- **监控**: Prometheus + Jaeger
- **日志**: Loguru

## API 端点

### 用户管理

- `GET /api/v1/users` - 获取用户列表（分页）
- `POST /api/v1/users` - 创建用户
- `GET /api/v1/users/{user_id}` - 获取用户详情
- `PUT /api/v1/users/{user_id}` - 更新用户信息
- `DELETE /api/v1/users/{user_id}` - 删除用户（软删除）

### 系统端点

- `GET /` - 服务根路径
- `GET /health` - 健康检查
- `GET /metrics` - Prometheus指标
- `GET /docs` - API文档（Swagger UI）
- `GET /redoc` - API文档（ReDoc）

## 环境变量

```bash
# 服务配置
SERVICE_NAME=admin-service
SERVICE_PORT=8002
SERVICE_IP=172.20.0.102

# 数据库配置
MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/intel_cw

# Redis配置
REDIS_URL=redis://redis:6379/2

# Nacos配置
NACOS_SERVER_ADDR=172.20.0.12:8848

# Jaeger配置
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces
```

## 本地开发

### 安装依赖

```bash
cd services/admin-service
pip install -r requirements.txt
```

### 启动服务

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 访问API文档

- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

## Docker部署

### 构建镜像

```bash
docker build -t intel-cw-ms/admin-service:latest -f services/admin-service/Dockerfile .
```

### 运行容器

```bash
docker run -d \
  --name admin-service \
  -p 8002:8002 \
  -e MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/intel_cw \
  -e REDIS_URL=redis://redis:6379/2 \
  -e NACOS_SERVER_ADDR=172.20.0.12:8848 \
  intel-cw-ms/admin-service:latest
```

## 认证说明

### JWT认证

所有API端点（除公开路径外）都需要JWT认证：

```bash
# 获取令牌（通过Auth Service）
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "***REMOVED***word": "***REMOVED***word"}'

# 使用令牌访问API
curl -X GET http://localhost:8002/api/v1/users \
  -H "Authorization: Bearer <access_token>"
```

### 公开路径

以下路径不需要认证：

- `/` - 根路径
- `/health` - 健康检查
- `/metrics` - Prometheus指标
- `/docs` - API文档
- `/redoc` - ReDoc文档
- `/openapi.json` - OpenAPI规范

## 监控和追踪

### 健康检查

```bash
curl http://localhost:8002/health
```

### Prometheus指标

```bash
curl http://localhost:8002/metrics
```

### Jaeger追踪

访问 Jaeger UI: http://localhost:16686

## 开发规范

- 遵循 Python 3.8.10 兼容性
- 使用类型注解
- 编写中文注释
- 遵循 RESTful API 设计规范
- 使用统一的响应格式
- 实现完整的错误处理

## 目录结构

```
services/admin-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 应用入口
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── dependencies.py # 依赖注入
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── users.py    # 用户管理端点
│   ├── core/
│   │   ├── __init__.py
│   │   └── auth_middleware.py # 认证中间件
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py            # 用户数据模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py            # 用户数据模式
│   └── services/
│       ├── __init__.py
│       └── user_service.py    # 用户业务逻辑
├── Dockerfile
├── requirements.txt
└── README.md
```

## 故障排查

### 数据库连接失败

检查MariaDB服务是否运行，数据库URL是否正确

### Redis连接失败

检查Redis服务是否运行，Redis URL是否正确

### Nacos注册失败

检查Nacos服务是否运行，服务器地址是否正确

### 认证失败

检查JWT密钥配置，令牌是否有效

## 相关文档

- [项目总体规范](../../.cursor/rules/project-overview.mdc)
- [微服务架构规范](../../.cursor/rules/microservice-architecture.mdc)
- [API设计规范](../../.cursor/rules/api-design-standards.mdc)
- [认证安全规范](../../.cursor/rules/auth-security.mdc)
