# Intel EC Microservices Management System

[![Python Version](https://img.shields.io/badge/python-3.8.10-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.11-blue.svg)](https://mariadb.com)
[![Redis](https://img.shields.io/badge/Redis-6.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://docker.com)

## 📖 Project Introduction

Intel EC microservices architecture project is an enterprise-level microservices management system built on **Python 3.8.10**, using modern technology stack to implement a highly available and scalable distributed application architecture.

### 🎯 Core Features

- ✅ **Microservices Architecture**: 3 core microservices (gateway, authentication, host service)
- ✅ **High Performance**: FastAPI asynchronous framework supporting high concurrency
<!-- - ✅ **Distributed Tracing**: Jaeger + OpenTelemetry full-chain tracing
- ✅ **Monitoring System**: Prometheus + Grafana complete monitoring solution -->
- ✅ **Containerized Deployment**: Docker + Docker Compose complete deployment solution
- ✅ **Code Quality**: Ruff + MyPy + Pyright strict code standards
- ✅ **Real-time Communication**: WebSocket supports real-time Agent communication

## 🏗️ Microservices Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gateway       │    │   Auth Service  │    │  Host Service   │
│   (8000)        │    │   (8001)        │    │   (8003)        │
│                 │    │                 │    │                 │
│ • API Gateway   │    │ • User Auth       │    │ • Host Management│
│ • Route Forward │    │ • JWT Management │    │ • Agent Comm     │
│ • Load Balance  │    │ • OAuth 2.0      │    │ • WebSocket     │
│ • Auth Verify   │    │ • Session Mgmt   │    │ • Real-time Mgmt│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Shared        │
                    │   Modules       │
                    │                 │
                    │ • Common Comp    │
                    │ • Utility Class  │
                    │ • Config Mgmt    │
                    │ • DB Connection  │
                    │ • Cache Mgmt     │
                    │ • Logging System │
                    │ • Response Format│
                    │ • Monitor Metrics│
                    │ • WebSocket     │
                    │ • Jaeger Tracing │
                    └─────────────────┘
```

## 📖 Documentation Navigation

This project provides a complete documentation system, all detailed documents are located in the [`docs/`](./docs/) directory.

### Quick Start

<<<<<<< HEAD
- 🚀 **[Quick Start Guide](docs/00-quick-start.md)** - Get started in 5 minutes
- 💻 **[Local Development Environment Setup](docs/33-local-development-setup.md)** - Complete setup guide for Windows/macOS
- 📦 **[Project Setup](docs/04-project-setup.md)** - Complete environment configuration
- 📚 **[API Reference Documentation](docs/api/API_REFERENCE.md)** - API interface documentation access (Swagger UI, ReDoc, OpenAPI JSON)
- 🧪 **[Interface Load Testing Plan](docs/34-api-load-testing-plan.md)** - Complete load testing plan and technology stack
=======
- 🚀 **[快速开始指南](docs/00-quick-start.md)** - 5分钟快速上手
- 📦 **[项目设置](docs/04-project-setup.md)** - 完整环境配置
- 📚 **[API 文档指南](docs/api/API_DOCUMENTATION_GUIDE.md)** - API 接口文档访问
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

### Core Functions

- 🔐 **[Authentication Architecture](docs/12-authentication-architecture.md)** - JWT authentication system design
- 🌐 **[WebSocket Usage Guide](docs/18-websocket-usage.md)** - Complete WebSocket usage guide
- 📊 **[SQL Performance Monitoring](docs/40-sql-performance-monitoring.md)** - SQL performance monitoring and slow query location system
<!-- - 🛠️ **[Infrastructure Configuration](docs/01-infrastructure-config.md)** - MariaDB, Redis, Nacos, Jaeger configuration -->

<!-- ### Monitoring and Tracing

- 📊 **[Complete Monitoring System Configuration](docs/05-monitoring-setup-complete.md)** - Prometheus + Grafana
- 📈 **[Grafana Dashboard Guide](docs/06-grafana-dashboard-guide.md)** - Monitoring dashboard usage
- 🔍 **[Monitoring Quick Reference](docs/07-monitoring-quick-reference.md)** - Common commands
- 🔍 **[Jaeger Storage Configuration](docs/11-jaeger-storage-config.md)** - Distributed tracing -->

### Code Quality

- ✅ **[Code Quality Configuration](docs/08-code-quality-setup.md)** - Ruff + MyPy + Pyright
- 📊 **[Code Quality Tools Analysis](docs/13-code-quality-tools-analysis.md)** - Tool selection analysis
- 🐍 **[Python 3.8 Compatibility](docs/09-python38-compatibility.md)** - Version compatibility notes
- 🔧 **[Pyright Troubleshooting](docs/16-pyright-troubleshooting.md)** - Type checking issue resolution
- 📖 **[Pyright Overview](docs/17-pyright-overview.md)** - Documentation index

<!-- ### Troubleshooting

- 🔧 **[Nacos Troubleshooting](docs/10-nacos-troubleshooting.md)** - Nacos common issues -->

### Deployment Guide

- 🚀 **[Deployment Guide](docs/03-deployment-guide.md)** - Production environment deployment

> 📌 **Note**: For more detailed documentation, please check [`docs/README.md`](docs/README.md)

## 🚀 Quick Start

### Environment Requirements

- **Python**: 3.8.10 (strict version)
- **Docker**: 20.10+
- **Docker Compose**: v2.0+
- **Git**: 2.30+

### Installation Steps

1. **Clone the Project**

```bash
git clone <repository-url>
cd intel-cw-ms
```

2. **Start Services**

```bash
# Start all services
docker-compose up -d

# View service status
docker-compose ps

# View logs
docker-compose logs -f
```

3. **Verify Services**

Access the following addresses to confirm that services are running normally:

- **Gateway**: <http://localhost:8000/health>
- **Auth**: <http://localhost:8001/health>
- **Host**: <http://localhost:8003/health>

## 📊 Service Ports

### Microservices

| Service | Port | Health Check | API Documentation |
|------|------|----------|---------|
| Gateway Service | 8000 | <http://localhost:8000/health> | <http://localhost:8000/docs> |
| Auth Service | 8001 | <http://localhost:8001/health> | <http://localhost:8001/docs> |
| Host Service | 8003 | <http://localhost:8003/health> | <http://localhost:8003/docs> |

<!-- ### Infrastructure

| Service | Port | Access Address | Description |
|------|------|---------|------|
| Nacos | 8848 | <http://localhost:8848/nacos> | Service Discovery (username/***REMOVED***word: nacos/nacos) |
| Jaeger | 16686 | <http://localhost:16686> | Distributed Tracing |
| Prometheus | 9090 | <http://localhost:9090> | Metric Collection |
| Grafana | 3000 | <http://localhost:3000> | Monitoring Visualization (username/***REMOVED***word: admin/***REMOVED***) | -->

## 🛠️ Development Tools

### Code Quality Checks

```bash
# Ruff check and fix
ruff check services/ shared/
ruff check --fix services/ shared/

# Type checking
mypy services/ shared/
pyright services/ shared/

# Formatting
ruff format services/ shared/
```

### Test Execution

```bash
# Run all tests
pytest --cov=services --cov-report=html

# Generate coverage report
open htmlcov/index.html
```

## 📋 API Interfaces

### Authentication Interfaces

```bash
# Admin login
POST /api/v1/auth/admin/login

# Device login
POST /api/v1/auth/device/login

# Token refresh
POST /api/v1/auth/refresh

# Token validation
POST /api/v1/auth/introspect
```

### Management Interfaces

```bash
# Get admin list
GET /api/v1/admin/users

# Create admin
POST /api/v1/admin/users

# Update admin
PUT /api/v1/admin/users/{user_id}
```

### Host Interfaces

```bash
# Get host list
GET /api/v1/host/hosts

# WebSocket connection
WS /api/v1/ws/host

# Get active Hosts
GET /api/v1/host/ws/hosts

# Send message
POST /api/v1/host/ws/send
```

<!-- ## 📊 Monitoring and Tracing

### Jaeger UI

- **Address**: <http://localhost:16686>
- **Function**: Distributed tracing visualization

### Prometheus Metrics

- **Address**: <http://localhost:9090>
- **Metrics**: Service performance, error rate, response time

### Grafana Dashboard

- **Address**: <http://localhost:3000>
- **Function**: Visual monitoring panel -->

## 🔧 Configuration Instructions

### Environment Variables

```bash
# Python environment configuration
# Used to ensure pyright and runtime can correctly locate shared modules

# Add project root directory to Python path
# This allows direct import of shared.* without relative imports
PYTHONPATH=your-path/intel_ec_ms # /Users/xiyeming/VsCodeProjects/intel_ec_ms

# Service configuration example (each service can override these default values)
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# Service mapping configuration docker auth-service  admin-service  host-service  local startup 127.0.0.1
# SERVICE_HOST_AUTH=auth-service
# SERVICE_HOST_HOST=host-service
SERVICE_HOST_AUTH=127.0.0.1
SERVICE_HOST_HOST=127.0.0.1

GATEWAY_SERVICE_NAME=gateway-service
GATEWAY_SERVICE_PORT=8000
#GATEWAY_SERVICE_IP=172.20.0.100

AUTH_SERVICE_NAME=auth-service
AUTH_SERVICE_PORT=8001
#AUTH_SERVICE_IP=172.20.0.101

HOST_SERVICE_NAME=host-service
HOST_SERVICE_PORT=8003
#HOST_SERVICE_IP=172.20.0.103


# SERVICE_HOST_AUTH=127.0.0.1 #auth-service
# SERVICE_HOST_ADMIN=127.0.0.1 #admin-service
# SERVICE_HOST_HOST=127.0.0.1 #host-service

# Database configuration local startup 127.0.0.1  docker startup mariadb
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=intel_user
MARIADB_PASSWORD=
MARIADB_DATABASE=intel_cw

# MariaDB SSL/TLS Configuration (optional)
# MARIADB_SSL_ENABLED=false
# MARIADB_SSL_CA=./infrastructure/mysql/ssl/ca-cert.pem
# MARIADB_SSL_CERT=./infrastructure/mysql/ssl/client-cert.pem
# MARIADB_SSL_KEY=./infrastructure/mysql/ssl/client-key.pem
# MARIADB_SSL_VERIFY_CERT=true
# MARIADB_SSL_VERIFY_IDENTITY=false

# Redis configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT configuration
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Logging Configuration
LOG_LEVEL=INFO

# Intel service API configuration
HARDWARE_API_URL=http://localhost:8080

# AES key
AES_ENCRYPTION_KEY=your_secure_32_byte_key_here_1234567890123456

# File Upload Configuration
FILE_UPLOAD_DIR=/Users/xiyeming/Downloads/uploads

# ==========================================
# Component Switch Configuration
# ==========================================
# Nacos Service Discovery Switch (default: enabled)
ENABLE_NACOS=false

# Jaeger Distributed Tracing Switch (default: enabled)
ENABLE_JAEGER=false

# Prometheus Monitoring Metrics Switch (default: enabled)
ENABLE_PROMETHEUS=false

# Hardware Interface Mock Configuration (for development environment)
USE_HARDWARE_MOCK=true

# ==========================================
# Email Configuration
# ==========================================
SMTP_FROM_EMAIL=example@163.com
SMTP_SERVER=smtp.163.com
SMTP_PORT=25
SMTP_USER=example@163.com
SMTP_PASSWORD=
```
<<<<<<< HEAD
=======

### Docker Compose配置

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ***REMOVED***word

  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"

  jaeger:
    image: jaegertracing/all-in-one:1.54
    ports:
      - "16686:16686"
      - "4318:4318"
```

## 📊 监控系统

### Prometheus + Grafana

项目集成了完整的监控系统：

```bash
# 启动监控服务
./scripts/start_monitoring.sh

# 或手动启动
docker-compose up -d prometheus grafana
```

**访问地址**：

- **Prometheus**: <http://localhost:9090> - 指标采集和查询
- **Grafana**: <http://localhost:3000> - 数据可视化
  - 用户名: `admin`
  - 密码: `***REMOVED***` (可在 `.env` 中配置)

**监控指标**：

- ✅ 服务健康状态
- ✅ 请求速率 (RPS)
- ✅ 响应时间 (P50/P95/P99)
- ✅ 错误率
- ✅ 系统资源使用

详细配置请参考：[Prometheus + Grafana 监控指南](docs/prometheus-grafana-setup.md)

## 📝 更新日志

### v1.1.0 (2025-10-16)

#### ✨ 代码优化完成

- ✅ **统一依赖注入模式**
  - 所有服务使用单例模式的依赖注入
  - 依赖注入函数统一为同步函数
  - 全局实例使用 `Optional[Type]` 类型注解

- ✅ **优化数据库会话管理**
  - 直接使用 `async with mariadb_manager.get_session()`
  - 移除不必要的 `session_factory` 中间变量
  - 简化代码，提升性能

- ✅ **统一错误处理机制**
  - 创建 `@handle_service_errors` 装饰器
  - 创建 `@handle_api_errors` 装饰器
  - 统一异常转换和日志记录

- ✅ **统一 HTTP 客户端使用**
  - 创建 `AsyncHTTPClient` 共享模块
  - 移除 `requests` 库，统一使用 `httpx.AsyncClient`
  - 配置连接池和超时参数

- ✅ **增强监控指标收集**
  - 创建 `@monitor_operation` 装饰器
  - 自动记录操作成功/失败次数
  - 自动记录操作耗时

- ✅ **改进日志记录**
  - 统一使用结构化日志格式
  - 添加 `extra` 参数记录上下文
  - 统一日志级别使用

#### 📚 文档更新

- ✅ **新增最佳实践指南** - `.kiro/specs/code-optimization/BEST_PRACTICES.md`
  - 代码组织规范
  - 依赖注入最佳实践
  - 数据库操作最佳实践
  - 错误处理最佳实践
  - HTTP 客户端使用
  - 监控和日志规范
  - 装饰器使用指南
  - 性能优化建议

- ✅ **新增架构文档** - `.kiro/specs/code-optimization/ARCHITECTURE.md`
  - 架构概述和架构图
  - 微服务组件详细说明
  - 共享模块说明
  - 数据流图
  - 技术栈清单
  - 部署架构

- ✅ **更新 API 文档指南**
  - 添加健康检查和监控指标端点
  - 添加代码优化文档链接
  - 完善文档维护规范

- ✅ **更新 README**
  - 添加代码优化文档导航
  - 更新文档结构
  - 添加更新日志

#### 🎯 优化成果

- **代码质量**: 统一规范，减少重复代码
- **性能提升**: 优化数据库会话管理，使用异步 HTTP 客户端
- **可维护性**: 装饰器模式，简化错误处理
- **可观测性**: 完整的监控和日志体系
- **开发效率**: 最佳实践指南，加速开发

### v1.0.2 (2025-10-14)

#### 🐛 问题修复

- ✅ **修复auth-service启动失败问题**
  - 问题：auth-service启动时报错 `No module named 'app.models.user'`
  - 原因：`app/models/__init__.py`中存在对不存在的`app.models.user`模块的导入
  - 解决方案：移除`__init__.py`中对`User`模型的错误引用，只保留`UserSession`模型

- ✅ **修复auth-service LoginRequest导入错误**
  - 问题：auth-service启动时报错 `cannot import name 'LoginRequest' from 'app.schemas.auth'`
  - 原因：`app/schemas/__init__.py`中试图导入`auth.py`中不存在的`LoginRequest`类
  - 解决方案：移除对不存在的`LoginRequest`类的导入引用

- ✅ **修复auth-service路径导入深度错误**
  - 问题：auth-service中多个文件路径计算错误，无法导入shared模块
  - 原因：路径深度计算不正确（向上3级而不是4级）
  - 解决方案：修复所有auth-service文件中shared模块的路径导入

- ✅ **修复Device模型metadata字段命名冲突**
  - 问题：SQLAlchemy错误 `Attribute name 'metadata' is reserved`
  - 原因：Device模型使用了SQLAlchemy保留字段名`metadata`
  - 解决方案：重命名字段为`device_metadata`

- ✅ **修复AdminLoginRequest和verify_admin_***REMOVED***word导入错误**
  - 问题：`AdminLoginRequest`类未定义，`verify_admin_***REMOVED***word`函数不存在
  - 原因：缺少必要的类定义和函数导入
  - 解决方案：添加`AdminLoginRequest`类定义，更改导入为`verify_***REMOVED***word`

- ✅ **修复Pyright类型检查错误**
  - 问题：29个类型检查错误，包括未使用的导入、类型参数错误等
  - 原因：代码中存在未使用的导入和错误的函数调用参数
  - 解决方案：移除未使用的导入，修复BusinessError参数顺序，处理None值类型问题

- ✅ **修复Ruff代码质量检查错误**
  - 问题：11个代码质量检查错误，包括异常处理和布尔值比较
  - 原因：API端点捕获Exception被认为过于宽泛，布尔值比较不符合规范
  - 解决方案：添加BLE001到忽略列表（API端点需要捕获所有异常），修复布尔值比较语法

- ✅ **修复Grafana仪表板单位设置错误**
  - 问题：admin-service和host-service在"各服务请求速率"图表中不显示数据
  - 原因："各服务请求速率"面板的单位错误设置为`"s"`而不是`"reqps"`
  - 解决方案：修复Grafana仪表板配置中的单位设置，确保所有服务数据正确显示

#### 📚 文档更新

- ✅ **新增Grafana仪表板单位设置规范**
  - 创建Cursor Rule: `grafana-dashboard-units.mdc`
  - 详细说明各类型指标的正确单位设置
  - 提供故障排查指南和最佳实践
  - 防止类似配置错误再次发生

- ✅ **实现管理后台密码加密存储**
  - 使用bcrypt算法对sys_user表密码进行加密
  - 提供密码哈希和验证工具函数
  - 创建密码迁移脚本处理现有数据
  - 增强系统安全性

#### ✅ 验证结果

- 所有4个微服务(admin/auth/gateway/host)在Grafana图表中正确显示
- 各服务请求速率、响应时间和HTTP状态码分布图表数据完整
- 新增的规范文档帮助团队避免类似配置错误
- 管理后台密码使用bcrypt加密存储，安全性显著提升
- 密码哈希和验证功能正常工作

### v1.0.1 (2025-10-13)

#### 🐛 问题修复

- ✅ **修复"Too much data for declared Content-Length"错误**
  - 问题原因：网关HTTP客户端与后端服务Content-Length头部冲突
  - 解决方案：简化HTTP请求处理，使用更稳定的库和头部管理
- ✅ **修复API路径映射错误**
  - 问题：网关转发请求时URL不正确（如`/auth/login`而不是`/api/v1/auth/login`）
  - 解决方案：为每个服务添加正确的API前缀映射
- ✅ **优化HTTP客户端实现**
  - 替换httpx为requests库，避免异步处理中的Content-Length问题
  - 移除可能导致冲突的HTTP头部
  - 简化请求体处理逻辑

#### ✅ 验证结果

- 网关现在能正确转发请求到后端服务
- API路径映射正确：`/api/v1/auth/login` → `http://auth-service:8001/api/v1/auth/login`
- 不再出现Content-Length相关的HTTP错误
- 错误响应格式正确统一

### v1.0.0 (2025-10-12)

#### ✨ 新功能

- ✅ **统一404错误响应**: 修复FastAPI默认404响应格式不符合项目规范的问题
  - 添加根级别catch-all路由处理所有未匹配请求
  - 添加API级别catch-all路由处理`/api/v1/*`路径
  - 统一返回符合项目规范的JSON错误响应格式
- ✅ **错误响应格式标准化**: 所有404错误现在返回统一的格式：

  ```json
  {
    "code": 404,
    "message": "请求的资源不存在",
    "error_code": "RESOURCE_NOT_FOUND",
    "details": {
      "method": "GET",
      "path": "/not-found",
      "available_endpoints": [...]
    },
    "timestamp": "2025-10-12T10:00:00Z"
  }
  ```

#### 🔧 技术改进

- 优化路由注册顺序，确保catch-all路由具有最低优先级
- 增强错误日志记录，包含请求方法、路径、客户端信息
- 提供详细的可用端点提示，帮助开发调试
- **修复ServiceUnavailableError构造函数调用bug** - 确保返回正确的503状态码而不是500

#### 🔧 最新更新 (2025-10-20)

- ✅ **修复网关JSONResponse导入错误**
  - 问题：`POST /api/v1/auth/admin/login`请求返回500错误，日志显示`NameError: name 'JSONResponse' is not defined`
  - 原因：网关proxy.py异常处理中使用`JSONResponse`但未正确导入
  - 解决方案：在文件顶部导入语句中添加`from fastapi.responses import JSONResponse`，删除重复局部导入
  - 验证：创建`test_gateway_import_fix.py`测试脚本验证修复

- ✅ **修复admin服务数据库连接问题**
  - 问题：`GET /api/v1/admin/users`返回400错误，日志显示"获取用户列表失败"
  - 原因：admin服务数据库连接未初始化，`mariadb_manager.get_session()`抛出"数据库未连接"错误
  - 解决方案：改进admin服务的数据库初始化函数，添加连接测试和详细错误日志
  - 诊断工具：创建`scripts/check_admin_service_startup.py`用于检查admin服务启动状态
  - 验证：确保数据库服务运行、表存在且连接正常

- ✅ **修复admin服务list_users查询SQL语法错误**
  - 问题：admin服务用户列表查询失败，count查询语法不正确
  - 原因：使用了`select(func.count()).select_from(stmt.subquery())`语法问题
  - 解决方案：改为`select(func.count(User.id)).where(...)`，并确保count查询与主查询条件一致
  - 修复内容：count查询现在正确应用搜索和过滤条件，避免N+1查询问题
  - 验证：创建`test_admin_query_fix.py`测试脚本验证SQL生成和逻辑正确性

- ✅ **修复admin服务数据库连接配置不一致**
  - 问题：admin服务启动时数据库连接失败，找不到"mariadb"主机
  - 原因：代码中的数据库默认值与docker-compose.yml不一致，导致fallback到错误的默认值
  - 解决方案：修正`services/admin-service/app/main.py`中的`_build_database_urls()`函数默认值
  - 修复内容：将代码默认值从(localhost, root, ***REMOVED***word)改为(mariadb, intel_user, intel_***REMOVED***)
  - 验证：创建`test_admin_db_config.py`测试脚本验证配置兼容性和URL生成正确性

- ✅ **修复admin服务user_service.py语法错误**
  - 问题：admin服务启动失败，显示`SyntaxError: invalid syntax`在user_service.py第279行
  - 原因：try-except块的缩进错误，导致`if search:`语句不在正确的代码块中
  - 解决方案：修正`services/admin-service/app/services/user_service.py`中list_users方法的缩进结构
  - 修复内容：确保所有数据库查询逻辑都在try-except块内部，添加详细的数据库错误日志记录
  - 验证：代码质量检查通过，所有模块导入成功

#### 🔧 最新更新 (2025-10-15)

- ✅ **修复OAuth2端点响应格式问题**
  - 问题：OAuth2端点返回`{"detail": {...}}`格式，不符合统一响应规范
  - 原因：FastAPI自动处理HTTP Basic认证失败时添加外层detail字段
  - 解决方案：移除HTTPBasic依赖，手动处理认证，统一返回ErrorResponse格式

- ✅ **优化网关404响应格式**
  - 问题：网关404响应包含过多信息泄露风险
  - 原因：返回available_endpoints字段暴露内部端点结构
  - 解决方案：移除available_endpoints字段，只保留method和path信息

- ✅ **完善API响应格式统一规范**
  - 创建Cursor Rule: `api-response-format.mdc`
  - 建立OAuth2端点特殊处理规范
  - 规范网关响应格式要求
  - 提供FastAPI响应模型最佳实践

- ✅ **优化异常处理中间件**
  - 修复loguru日志格式化错误
  - 改进异常信息记录方式
  - 确保错误响应格式完全统一

- ✅ **修复OAuth2端点Form参数验证**
  - 问题：缺少必需Form参数时返回Pydantic验证错误而不是统一格式
  - 原因：FastAPI在函数调用前进行参数验证，绕过异常中间件
  - 解决方案：将必需参数改为可选，在函数内手动验证并返回统一ErrorResponse

## 🤝 贡献指南

1. **Fork** 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个 **Pull Request**

### 代码规范

- ✅ 通过所有自动化检查 (Ruff, MyPy, Black)
- ✅ 添加适当的测试用例
- ✅ 更新相关文档
- ✅ 遵循现有的代码风格

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系我们

- **项目负责人**: Intel EC开发团队
- **技术支持**: 通过项目Issue提交
- **文档更新**: 及时同步更新

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**⭐ 如果这个项目对你有帮助，请给我们一个star！**
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
