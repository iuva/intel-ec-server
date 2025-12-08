# Intel EC 微服务管理系统

[![Python Version](https://img.shields.io/badge/python-3.8.10-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.11-blue.svg)](https://mariadb.com)
[![Redis](https://img.shields.io/badge/Redis-6.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://docker.com)

## 📖 项目简介

Intel EC 微服务架构项目是一个基于 **Python 3.8.10** 构建的企业级微服务管理系统，采用现代化技术栈实现高可用、可扩展的分布式应用架构。

### 🎯 核心特性

- ✅ **微服务架构**: 3个核心微服务（网关、认证、主机服务）
- ✅ **高性能**: FastAPI异步框架，支持高并发
<!-- - ✅ **分布式追踪**: Jaeger + OpenTelemetry全链路追踪
- ✅ **监控系统**: Prometheus + Grafana完整监控方案 -->
- ✅ **容器化部署**: Docker + Docker Compose完整部署方案
- ✅ **代码质量**: Ruff + MyPy + Pyright严格代码规范
- ✅ **实时通信**: WebSocket支持Agent实时通信

## 🏗️ 微服务架构

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gateway       │    │   Auth Service  │    │  Host Service   │
│   (8000)        │    │   (8001)        │    │   (8003)        │
│                 │    │                 │    │                 │
│ • API网关       │    │ • 用户认证        │    │ • Host管理       │
│ • 路由转发       │    │ • JWT管理        │    │ • Agent通信      │
│ • 负载均衡       │    │ • OAuth 2.0     │    │ • WebSocket     │
│ • 认证验证       │    │ • 会话管理        │    │ • 实时监控       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Shared        │
                    │   Modules       │
                    │                 │
                    │ • 公共组件       │
                    │ • 工具类         │
                    │ • 配置管理       │
                    │ • 数据库连接     │
                    │ • 缓存管理       │
                    │ • 日志系统       │
                    │ • 响应格式化     │
                    │ • 监控指标       │
                    │ • WebSocket     │
                    │ • Jaeger追踪    │
                    └─────────────────┘
```

## 📖 文档导航

本项目提供了完整的文档体系，所有详细文档位于 [`docs/`](./docs/) 目录。

### 快速开始

- 🚀 **[快速开始指南](docs/00-quick-start.md)** - 5分钟快速上手
- 💻 **[本地开发环境搭建](docs/33-local-development-setup.md)** - Windows/macOS 完整搭建指南
- 📦 **[项目设置](docs/04-project-setup.md)** - 完整环境配置
- 📚 **[API 文档指南](docs/api/API_DOCUMENTATION_GUIDE.md)** - API 接口文档访问
- 🧪 **[接口压测方案](docs/34-api-load-testing-plan.md)** - 完整压测方案和技术栈

### 核心功能

- 🔐 **[认证架构](docs/12-authentication-architecture.md)** - JWT 认证系统设计
- 🌐 **[WebSocket 使用指南](docs/18-websocket-usage.md)** - WebSocket 完整使用指南
- 📊 **[SQL性能监控](docs/40-sql-performance-monitoring.md)** - SQL性能监控和慢查询定位系统
<!-- - 🛠️ **[基础设施配置](docs/01-infrastructure-config.md)** - MariaDB、Redis、Nacos、Jaeger 配置 -->

<!-- ### 监控和追踪

- 📊 **[监控系统完整配置](docs/05-monitoring-setup-complete.md)** - Prometheus + Grafana
- 📈 **[Grafana 仪表盘指南](docs/06-grafana-dashboard-guide.md)** - 监控面板使用
- 🔍 **[监控快速参考](docs/07-monitoring-quick-reference.md)** - 常用命令
- 🔍 **[Jaeger 存储配置](docs/11-jaeger-storage-config.md)** - 分布式追踪 -->

### 代码质量

- ✅ **[代码质量配置](docs/08-code-quality-setup.md)** - Ruff + MyPy + Pyright
- 📊 **[代码质量工具分析](docs/13-code-quality-tools-analysis.md)** - 工具选型分析
- 🐍 **[Python 3.8 兼容性](docs/09-python38-compatibility.md)** - 版本兼容性说明
- 🔧 **[Pyright 故障排除](docs/16-pyright-troubleshooting.md)** - 类型检查问题解决
- 📖 **[Pyright 总览](docs/17-pyright-overview.md)** - 文档索引

<!-- ### 故障排除

- 🔧 **[Nacos 故障排除](docs/10-nacos-troubleshooting.md)** - Nacos 常见问题 -->

### 部署指南

- 🚀 **[部署指南](docs/03-deployment-guide.md)** - 生产环境部署

> 📌 **提示**: 更多详细文档请查看 [`docs/README.md`](docs/README.md)

## 🚀 快速开始

### 环境要求

- **Python**: 3.8.10 (严格版本)
- **Docker**: 20.10+
- **Docker Compose**: v2.0+
- **Git**: 2.30+

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd intel-cw-ms
```

2. **启动服务**

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

3. **验证服务**

访问以下地址确认服务正常运行：

- **Gateway**: <http://localhost:8000/health>
- **Auth**: <http://localhost:8001/health>
- **Host**: <http://localhost:8003/health>

## 📊 服务端口

### 微服务

| 服务 | 端口 | 健康检查 | API文档 |
|------|------|----------|---------|
| Gateway Service | 8000 | <http://localhost:8000/health> | <http://localhost:8000/docs> |
| Auth Service | 8001 | <http://localhost:8001/health> | <http://localhost:8001/docs> |
| Host Service | 8003 | <http://localhost:8003/health> | <http://localhost:8003/docs> |

<!-- ### 基础设施

| 服务 | 端口 | 访问地址 | 说明 |
|------|------|---------|------|
| Nacos | 8848 | <http://localhost:8848/nacos> | 服务发现（用户名/密码: nacos/nacos） |
| Jaeger | 16686 | <http://localhost:16686> | 分布式追踪 |
| Prometheus | 9090 | <http://localhost:9090> | 指标采集 |
| Grafana | 3000 | <http://localhost:3000> | 监控可视化（用户名/密码: admin/***REMOVED***） | -->

## 🛠️ 开发工具

### 代码质量检查

```bash
# Ruff检查和修复
ruff check services/ shared/
ruff check --fix services/ shared/

# 类型检查
mypy services/ shared/
pyright services/ shared/

# 格式化
ruff format services/ shared/
```

### 测试运行

```bash
# 运行所有测试
pytest --cov=services --cov-report=html

# 生成覆盖率报告
open htmlcov/index.html
```

## 📋 API 接口

### 认证接口

```bash
# 管理员登录
POST /api/v1/auth/admin/login

# 设备登录
POST /api/v1/auth/device/login

# Token刷新
POST /api/v1/auth/refresh

# Token验证
POST /api/v1/auth/introspect
```

### 管理接口

```bash
# 获取管理员列表
GET /api/v1/admin/users

# 创建管理员
POST /api/v1/admin/users

# 更新管理员
PUT /api/v1/admin/users/{user_id}
```

### 主机接口

```bash
# 获取主机列表
GET /api/v1/host/hosts

# WebSocket连接
WS /api/v1/ws/host

# 获取活跃Hosts
GET /api/v1/host/ws/hosts

# 发送消息
POST /api/v1/host/ws/send
```

<!-- ## 📊 监控和追踪

### Jaeger UI

- **地址**: <http://localhost:16686>
- **功能**: 分布式追踪可视化

### Prometheus指标

- **地址**: <http://localhost:9090>
- **指标**: 服务性能、错误率、响应时间

### Grafana面板

- **地址**: <http://localhost:3000>
- **功能**: 可视化监控面板 -->

## 🔧 配置说明

### 环境变量

```bash
# Python 环境配置
# 用于确保 pyright 和运行时都能正确找到 shared 模块

# 添加项目根目录到 Python 路径
# 这样可以直接 import shared.* 而不需要相对导入
PYTHONPATH=your-path/intel_ec_ms # /Users/xiyeming/VsCodeProjects/intel_ec_ms

# 服务配置示例（各服务可以覆盖这些默认值）
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# 服务映射配置 docker auth-service  admin-service  host-service  本地启动 127.0.0.1
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

# 数据库配置 本地启动 127.0.0.1  docker 启动 mariadb
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=intel_user
MARIADB_PASSWORD=
MARIADB_DATABASE=intel_cw

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 日志配置
LOG_LEVEL=INFO

# Intel 服务 api 配置
HARDWARE_API_URL=http://localhost:8080

# AES 密钥
AES_ENCRYPTION_KEY=your_secure_32_byte_key_here_1234567890123456

# 文件上传配置
FILE_UPLOAD_DIR=/Users/xiyeming/Downloads/uploads

# ==========================================
# 组件开关配置
# ==========================================
# Nacos 服务发现开关（默认：启用）
ENABLE_NACOS=false

# Jaeger 分布式追踪开关（默认：启用）
ENABLE_JAEGER=false

# Prometheus 监控指标开关（默认：启用）
ENABLE_PROMETHEUS=false

# 硬件接口 Mock 配置（开发环境使用）
USE_HARDWARE_MOCK=true

# ==========================================
# 邮箱配置
# ==========================================
SMTP_FROM_EMAIL=example@163.com
SMTP_SERVER=smtp.163.com
SMTP_PORT=25
SMTP_USER=example@163.com
SMTP_PASSWORD=
```
