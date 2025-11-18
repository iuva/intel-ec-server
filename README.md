# Intel EC 微服务管理系统

[![Python Version](https://img.shields.io/badge/python-3.8.10-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.11-blue.svg)](https://mariadb.com)
[![Redis](https://img.shields.io/badge/Redis-6.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://docker.com)

## 📖 项目简介

Intel EC 微服务架构项目是一个基于 **Python 3.8.10** 构建的企业级微服务管理系统，采用现代化技术栈实现高可用、可扩展的分布式应用架构。

### 🆕 最近更新

- ⚡ **WebSocket Host_ID 转发优化**：网关验证 token 后直接将 host_id 作为查询参数转发给 host-service，减少后端重复验证，性能提升 20-30%，同时保持完全向后兼容。[详见文档](./docs/WEBSOCKET_HOST_ID_FORWARDING_OPTIMIZATION.md)
- 🎯 **WebSocket Token 自动提取 Host_ID**：WebSocket 连接建立时自动从 JWT token 中读取 host_id（设备ID）。支持 `sub` 和 `user_id` 字段，无需路径参数或额外配置，自动在连接时提取和注册。[详见文档](./docs/WEBSOCKET_TOKEN_HOST_ID_EXTRACTION.md)
- 🎯 **WebSocket 活跃主机列表修复**：修复 host-service WebSocket 连接返回 "unknown" 的问题。现在即使禁用完整 token 验证，仍从 token 中解码提取真实 host_id，确保活跃主机列表返回正确的主机标识。[详见文档](./docs/WEBSOCKET_ACTIVE_HOSTS_UNKNOWN_FIX.md)
- 🔓 **WebSocket Token 验证禁用优化**：根据网关已进行 token 验证的现实，禁用 host-service 中的重复 token 验证。减少不必要的认证服务调用，提升性能，简化逻辑。[详见文档](./docs/WEBSOCKET_TOKEN_VERIFICATION_DISABLED.md)
- 📦 **Agent OTA 配置查询 API**：host-service 新增 `/api/v1/agent/ota/latest` 端点，Agent 可直接获取 `sys_conf` 中最新的 OTA 配置列表（包含 `conf_name/conf_ver/conf_val`），用于自动检测版本更新。
- 🔐 **WebSocket 认证服务发现修复**：修复 WebSocket token 验证使用硬编码认证服务地址的问题。现在采用与 HTTP 请求转发相同的多策略地址解析机制（环境变量 → Nacos ServiceDiscovery → 后备地址），确保在各种部署场景中都能正确连接认证服务。[详见文档](./docs/WEBSOCKET_AUTH_FIX.md)
- 🚀 **网关 HTTP 客户端增强**：新增 `HTTPClientConfig` 配置，统一连接池、重试与 Prometheus 指标（`http_client_requests_total`、`http_client_request_duration_seconds` 等），支持通过环境变量自定义超时/并发参数。
- 📊 **数据库性能优化**：为 `host_exec_log`、`host_hw_rec`、`host_rec` 等核心表添加多列索引，显著提升审批列表与硬件同步查询性能（预期提升 40-60%）。
- 🧰 **代码复用提升**：新增 `shared/utils/query_helpers.py`（通用分页查询助手）与 `services/host-service/app/constants/host_constants.py`（主机状态常量），降低重复逻辑与魔法值风险。
- 🛡️ **错误处理改进**：网关代理层修复防御性异常处理问题，未处理异常日志包含完整错误消息，方便快速定位。
- ⚡ **批量操作优化**：使用 `bulk_update_mappings` 替代循环更新，批量更新性能提升 50-70%。
- 🔧 **Bug 修复**：修复网关 HTTP 客户端初始化缺失配置、host-service model_dump 参数冲突等关键问题。

### 🎯 核心特性

- ✅ **微服务架构**: 3个核心微服务（网关、认证、主机服务）
- ✅ **高性能**: FastAPI异步框架，支持高并发
- ✅ **分布式追踪**: Jaeger + OpenTelemetry全链路追踪
- ✅ **监控系统**: Prometheus + Grafana完整监控方案
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
- 📦 **[项目设置](docs/04-project-setup.md)** - 完整环境配置
- 📚 **[API 文档指南](docs/api/API_DOCUMENTATION_GUIDE.md)** - API 接口文档访问

### 核心功能

- 🔐 **[认证架构](docs/12-authentication-architecture.md)** - JWT 认证系统设计
- 🌐 **[WebSocket 使用指南](docs/18-websocket-usage.md)** - WebSocket 完整使用指南
- 🛠️ **[基础设施配置](docs/01-infrastructure-config.md)** - MariaDB、Redis、Nacos、Jaeger 配置

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
- **Host**: <http://localhost:8003/health>

## 📊 服务端口

### 微服务

| 服务 | 端口 | 健康检查 | API文档 |
|------|------|----------|---------|
| Gateway Service | 8000 | <http://localhost:8000/health> | <http://localhost:8000/docs> |
| Auth Service | 8001 | <http://localhost:8001/health> | <http://localhost:8001/docs> |
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
