# Intel EC 微服务管理系统

[![Python Version](https://img.shields.io/badge/python-3.8.10-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.11-blue.svg)](https://mariadb.com)
[![Redis](https://img.shields.io/badge/Redis-6.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://docker.com)

## 📖 项目简介

Intel EC 微服务架构项目是一个基于 **Python 3.8.10** 构建的企业级微服务管理系统，采用现代化技术栈实现高可用、可扩展的分布式应用架构。

### 🎯 核心特性

- ✅ **微服务架构**: 4个核心微服务（网关、认证、后台管理、主机服务）
- ✅ **高性能**: FastAPI异步框架，支持高并发
- ✅ **分布式追踪**: Jaeger + OpenTelemetry全链路追踪
- ✅ **监控系统**: Prometheus + Grafana完整监控方案
- ✅ **容器化部署**: Docker + Docker Compose完整部署方案
- ✅ **代码质量**: Ruff + MyPy + Pyright严格代码规范
- ✅ **实时通信**: WebSocket支持Agent实时通信

## 🏗️ 微服务架构

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gateway       │    │   Auth Service  │    │  Admin Service  │    │  Host Service   │
│   (8000)        │    │   (8001)        │    │   (8002)        │    │   (8003)        │
│                 │    │                 │    │                 │    │                 │
│ • API网关       │    │ • 用户认证        │    │ • 后台管理       │    │ • Host管理       │
│ • 路由转发       │    │ • JWT管理        │    │ • 系统配置       │    │ • Agent通信      │
│ • 负载均衡       │    │ • OAuth 2.0     │    │ • 邮件通知       │    │ • WebSocket     │
│ • 认证验证       │    │ • 会话管理        │    │ • 审计日志       │    │ • 实时监控       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         └───────────────────────┼───────────────────────┼───────────────────────┘
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
- 📦 **[项目设置](docs/04-project-setup.md)** - 完整环境配置
- 📚 **[API 文档指南](docs/api/API_DOCUMENTATION_GUIDE.md)** - API 接口文档访问

### 核心功能

- 🔐 **[认证架构](docs/12-authentication-architecture.md)** - JWT 认证系统设计
- 🌐 **[WebSocket 完整指南](docs/WEBSOCKET_GUIDE.md)** - WebSocket 使用指南
- 🛠️ **[外部数据库配置](docs/01-external-database-setup.md)** - MariaDB & Redis 配置
- 🌐 **[外部服务配置](docs/02-external-services-config.md)** - Nacos & Jaeger 配置

### 监控和追踪

- 📊 **[监控系统完整配置](docs/05-monitoring-setup-complete.md)** - Prometheus + Grafana
- 📈 **[Grafana 仪表盘指南](docs/06-grafana-dashboard-guide.md)** - 监控面板使用
- 🔍 **[监控快速参考](docs/07-monitoring-quick-reference.md)** - 常用命令
- 🔍 **[Jaeger 存储配置](docs/11-jaeger-storage-config.md)** - 分布式追踪

### 代码质量

- ✅ **[代码质量配置](docs/08-code-quality-setup.md)** - Ruff + MyPy + Pyright
- 📊 **[代码质量工具分析](docs/13-code-quality-tools-analysis.md)** - 工具选型分析
- 🐍 **[Python 3.8 兼容性](docs/09-python38-compatibility.md)** - 版本兼容性说明
- 🔧 **[Pyright 故障排除](docs/16-pyright-troubleshooting.md)** - 类型检查问题解决
- 📖 **[Pyright 总览](docs/17-pyright-overview.md)** - 文档索引

### 故障排除

- 🔧 **[Nacos 故障排除](docs/10-nacos-troubleshooting.md)** - Nacos 常见问题

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
- **Admin**: <http://localhost:8002/health>
- **Host**: <http://localhost:8003/health>

## 📊 服务端口

### 微服务

| 服务 | 端口 | 健康检查 | API文档 |
|------|------|----------|---------|
| Gateway Service | 8000 | <http://localhost:8000/health> | <http://localhost:8000/docs> |
| Auth Service | 8001 | <http://localhost:8001/health> | <http://localhost:8001/docs> |
| Admin Service | 8002 | <http://localhost:8002/health> | <http://localhost:8002/docs> |
| Host Service | 8003 | <http://localhost:8003/health> | <http://localhost:8003/docs> |

### 基础设施

| 服务 | 端口 | 访问地址 | 说明 |
|------|------|---------|------|
| Nacos | 8848 | <http://localhost:8848/nacos> | 服务发现（用户名/密码: nacos/nacos） |
| Jaeger | 16686 | <http://localhost:16686> | 分布式追踪 |
| Prometheus | 9090 | <http://localhost:9090> | 指标采集 |
| Grafana | 3000 | <http://localhost:3000> | 监控可视化（用户名/密码: admin/***REMOVED***） |

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

## 📊 监控和追踪

### Jaeger UI

- **地址**: <http://localhost:16686>
- **功能**: 分布式追踪可视化

### Prometheus指标

- **地址**: <http://localhost:9090>
- **指标**: 服务性能、错误率、响应时间

### Grafana面板

- **地址**: <http://localhost:3000>
- **功能**: 可视化监控面板

## 🔧 配置说明

### 环境变量

```bash
# 数据库配置
MARIADB_HOST=mariadb
MARIADB_PORT=3306
MARIADB_DATABASE=intel_cw
MARIADB_USER=intel_user
MARIADB_PASSWORD=intel_***REMOVED***

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Jaeger配置
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces

# 服务配置
SERVICE_NAME=gateway-service
SERVICE_PORT=8000
```

## 📝 更新日志

### v1.2.0 (2025-10-28)

#### ✨ 新功能

- ✅ **WebSocket 完整实现**
  - 支持 WebSocket 连接和心跳监控
  - 实现单播、多播、广播消息
  - 完整的错误处理和日志记录

- ✅ **Gateway 优化**
  - 修复 Token 验证逻辑
  - 优化 URL 转发机制
  - 改进 WebSocket 错误处理

### v1.1.0 (2025-10-16)

#### ✨ 代码优化

- ✅ 统一依赖注入模式
- ✅ 优化数据库会话管理
- ✅ 统一错误处理机制
- ✅ 统一 HTTP 客户端使用
- ✅ 增强监控指标收集

### v1.0.0 (2025-10-12)

#### ✨ 初始版本

- ✅ 微服务架构实现
- ✅ JWT认证系统
- ✅ Prometheus + Grafana 监控
- ✅ Jaeger 分布式追踪
- ✅ Docker 容器化部署

### 代码规范

- ✅ 通过所有自动化检查 (Ruff, MyPy, Pyright)
- ✅ 添加适当的测试用例
- ✅ 更新相关文档
- ✅ 遵循现有的代码风格
