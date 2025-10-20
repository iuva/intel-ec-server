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
- ✅ **代码质量**: Ruff + MyPy + Black严格代码规范
- ✅ **实时通信**: WebSocket支持Agent实时通信

## 🏗️ 微服务架构

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gateway       │    │   Auth Service  │    │  Admin Service  │    │  Host Service   │
│   (8000)        │    │   (8001)        │    │   (8002)        │    │   (8003)        │
│                 │    │                 │    │                 │    │                 │
│ • API网关       │    │ • 用户认证      │    │ • 后台管理      │    │ • Host管理      │
│ • 路由转发      │    │ • JWT管理       │    │ • 系统配置      │    │ • Agent通信     │
│ • 负载均衡      │    │ • OAuth 2.0     │    │ • 邮件通知      │    │ • WebSocket     │
│ • 认证验证      │    │ • 会话管理      │    │ • 审计日志      │    │ • 实时监控      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         └───────────────────────┼───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Shared       │
                    │   Modules      │
                    │                │
                    │ • 公共组件     │
                    │ • 工具类       │
                    │ • 配置管理     │
                    │ • 数据库连接   │
                    │ • 缓存管理     │
                    │ • 日志系统     │
                    │ • 响应格式化   │
                    │ • 监控指标     │
                    │ • WebSocket    │
                    │ • Jaeger追踪   │
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
- 🛠️ **[外部数据库配置](docs/01-external-database-setup.md)** - MariaDB & Redis 配置
- 🌐 **[外部服务配置](docs/02-external-services-config.md)** - Nacos & Jaeger 配置

### 监控和追踪

- 📊 **[监控系统完整配置](docs/05-monitoring-setup-complete.md)** - Prometheus + Grafana
- 📈 **[Grafana 仪表盘指南](docs/06-grafana-dashboard-guide.md)** - 监控面板使用
- 🔍 **[监控快速参考](docs/07-monitoring-quick-reference.md)** - 常用命令
- 🔍 **[Jaeger 存储配置](docs/11-jaeger-storage-config.md)** - 分布式追踪

### 代码质量

- ✅ **[代码质量配置](docs/08-code-quality-setup.md)** - Ruff + MyPy + Black
- 📊 **[代码质量工具分析](docs/13-code-quality-tools-analysis.md)** - 工具选型分析
- 🐍 **[Python 3.8 兼容性](docs/09-python38-compatibility.md)** - 版本兼容性说明

### 类型检查 (Pyright)

- 🚀 **[Pyright 快速指南](docs/14-pyright-quick-guide.md)** - 5分钟上手
- 📝 **[Pyright 修复总结](docs/15-pyright-fixes-summary.md)** - 完整修复记录
- 🐛 **[Pyright 故障排除](docs/16-pyright-troubleshooting.md)** - 常见问题解决
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

2. **创建虚拟环境**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **启动基础设施**

```bash
docker-compose -f infrastructure/docker-compose.yml up -d
```

5. **运行服务**

```bash
# 网关服务
uvicorn services.gateway-service.app.main:app --host 0.0.0.0 --port 8000 --reload

# 认证服务
uvicorn services.auth-service.app.main:app --host 0.0.0.0 --port 8001 --reload

# 管理服务
uvicorn services.admin-service.app.main:app --host 0.0.0.0 --port 8002 --reload

# 主机服务
uvicorn services.host-service.app.main:app --host 0.0.0.0 --port 8003 --reload
```

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

# 格式化
black services/ shared/
isort services/ shared/
```

### 测试运行

```bash
# 运行所有测试
pytest --cov=services --cov-report=html

# 生成覆盖率报告
open htmlcov/index.html
```

### 基础设施管理

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 📋 API 接口

### 认证接口

```bash
# 用户登录
POST /api/v1/auth/login

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
GET /api/v1/hosts

# 注册主机
POST /api/v1/hosts

# WebSocket连接
WS /ws/agent/{agent_id}
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
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=intel_cw
MYSQL_USER=root
MYSQL_PASSWORD=***REMOVED***word

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Jaeger配置
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces

# 服务配置
SERVICE_NAME=gateway-service
SERVICE_PORT=8000
```

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
