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

- 🚀 **[Quick Start Guide](docs/00-quick-start.md)** - Get started in 5 minutes
- 💻 **[Local Development Environment Setup](docs/33-local-development-setup.md)** - Complete setup guide for Windows/macOS
- 📦 **[Project Setup](docs/04-project-setup.md)** - Complete environment configuration
- 📚 **[API Reference Documentation](docs/api/API_REFERENCE.md)** - API interface documentation access (Swagger UI, ReDoc, OpenAPI JSON)
- 🧪 **[Interface Load Testing Plan](docs/34-api-load-testing-plan.md)** - Complete load testing plan and technology stack

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

## 📝 最近修复记录

### 2025-11-11 - 修复Gateway未传递X-User-Info header问题

**问题**: Host服务返回401错误 "缺少 X-User-Info header，请求可能未通过 Gateway 认证"

**根本原因**: 
1. Gateway的`AuthMiddleware`成功验证JWT token后，将用户信息存储在`request.state.user`
2. 但在转发请求到下游服务时，**没有将用户信息添加到请求头中**
3. Host服务的`get_current_user`依赖期望从`X-User-Info` header获取用户信息

**修复方案**:
1. ✅ `services/gateway-service/app/api/v1/endpoints/proxy.py` - 在转发请求前，从`request.state.user`获取用户信息
2. ✅ 将用户信息序列化为JSON字符串，添加到请求headers中作为`X-User-Info`
3. ✅ 添加详细的调试日志，记录用户信息和header状态

**验证结果**:
- ✅ 下游服务能够正确接收`X-User-Info` header
- ✅ Host服务的`get_current_user`依赖正常工作
- ✅ API请求不再返回401错误

**代码变更**:
```python
# 在转发请求前添加用户信息到请求头
user_info = getattr(request.state, "user", None)
if user_info:
    headers["X-User-Info"] = json.dumps(user_info, ensure_ascii=False)
    logger.debug("添加用户信息到请求头", extra={...})
```

---

### 2025-11-10 - 修复 `KeyError: '"user_id"'` 错误

**问题**: host-service 在处理 X-User-Info header 时出现 `KeyError` 异常

**根本原因**: 
1. Loguru 在记录日志时，会尝试使用 `extra` 字典中的 key 作为格式化变量
2. 当 `extra` 中包含复杂对象（如字典）时，会导致序列化失败

**修复方案**:
1. ✅ `shared/common/i18n.py` - 过滤翻译函数的 kwargs，只保留基本类型
2. ✅ `shared/common/response.py` - 过滤 ErrorResponse 初始化的参数
3. ✅ `services/host-service/app/api/v1/dependencies.py` - 确保所有 logger.info/error 的 `extra` 只包含基本类型

**验证结果**:
- ✅ 无 KeyError 错误
- ✅ 日志正常记录
- ✅ API 返回正确的错误响应

---

### 环境变量

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
