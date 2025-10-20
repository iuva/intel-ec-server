# Intel EC 微服务项目文档

**项目**: Intel EC 微服务系统  
<<<<<<< HEAD
**最后更新**: 2025-01-30
=======
**最后更新**: 2025-10-16
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

## 📋 文档概述

本目录包含 Intel EC 微服务项目的完整技术文档，涵盖快速开始、基础设施配置、监控系统、代码质量、API 参考等各个方面。

---

## 📚 文档目录

<<<<<<< HEAD
### 🚀 快速开始

| 文档 | 说明 |
|------|------|
| [00-quick-start.md](./00-quick-start.md) | **快速开始指南** - 5分钟快速上手，包含本地启动和 Docker 启动两种方式 |
| [04-project-setup.md](./04-project-setup.md) | **完整项目设置** - 详细环境配置、依赖安装、数据库初始化 |

---

### 🏗️ 基础设施配置

| 文档 | 说明 |
|------|------|
| [01-infrastructure-config.md](./01-infrastructure-config.md) | **基础设施配置指南** - MariaDB、Redis、Nacos、Jaeger 完整配置说明 |
| [20-service-ip-port-config-explanation.md](./20-service-ip-port-config-explanation.md) | **SERVICE_IP 和 SERVICE_PORT 配置说明** - 服务注册配置原理、自动检测功能、Docker和本地环境兼容 |
| [25-infrastructure-grafana-datasources.md](./25-infrastructure-grafana-datasources.md) | **Grafana 数据源配置** - Prometheus 数据源自动配置说明 |

---

### 📊 监控和追踪

| 文档 | 说明 |
|------|------|
| [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md) | **完整监控系统配置** - Prometheus、Grafana、Jaeger 一体化配置 |
| [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md) | **Grafana 仪表板指南** - 仪表板创建、面板设计、监控指标 |
| [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md) | **监控快速参考** - 常用命令、指标查询、快速诊断 |
| [11-jaeger-storage-config.md](./11-jaeger-storage-config.md) | **Jaeger 存储配置** - 存储后端配置、性能优化 |
| [23-monitoring-metrics-enhancement.md](./23-monitoring-metrics-enhancement.md) | **监控指标增强说明** - 业务指标、性能监控、指标收集 |

---

### 🔍 代码质量

| 文档 | 说明 |
|------|------|
| [08-code-quality-setup.md](./08-code-quality-setup.md) | **代码质量工具配置** - Ruff、MyPy、Pyright 完整配置 |
| [09-python38-compatibility.md](./09-python38-compatibility.md) | **Python 3.8 兼容性指南** - 特性限制、类型注解、最佳实践 |
| [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md) | **代码质量工具分析** - 工具栈优化、性能对比、选型建议 |
| [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md) | **Pyright 故障排除** - 常见错误解决、配置问题 |
| [17-pyright-overview.md](./17-pyright-overview.md) | **Pyright 概览** - 完整功能介绍、架构设计 |
| [27-code-optimization.md](./27-code-optimization.md) | **代码优化完整指南** - 性能优化、代码结构优化、N+1查询修复 |
=======
### 🚀 快速开始 (00 系列)

| 文档 | 说明 |
|------|------|
| [00-quick-start.md](./00-quick-start.md) | 快速开始指南 - 环境要求、快速启动、基础配置 |
| [04-project-setup.md](./04-project-setup.md) | 完整项目设置 - 详细环境配置、依赖安装、数据库初始化 |

---

### 🏗️ 基础设施 (01-02 系列)

| 文档 | 说明 |
|------|------|
| [01-external-database-setup.md](./01-external-database-setup.md) | 外部数据库配置 - MariaDB 10.11 安装配置、用户权限 |
| [02-external-services-config.md](./02-external-services-config.md) | 外部服务配置 - Redis、Nacos 服务注册与发现 |

---

### 📊 监控系统 (05-07, 11 系列)

| 文档 | 说明 |
|------|------|
| [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md) | 完整监控系统配置 - Prometheus、Grafana、Jaeger |
| [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md) | Grafana 仪表板配置指南 - 仪表板创建、面板设计 |
| [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md) | 监控快速参考 - 常用命令、指标查询 |
| [11-jaeger-storage-config.md](./11-jaeger-storage-config.md) | Jaeger 存储配置 - 存储后端配置、性能优化 |

---

### 🔍 代码质量 (08-09, 13 系列)

| 文档 | 说明 |
|------|------|
| [08-code-quality-setup.md](./08-code-quality-setup.md) | 代码质量工具配置 - Ruff、MyPy、Pre-commit |
| [09-python38-compatibility.md](./09-python38-compatibility.md) | Python 3.8 兼容性指南 - 特性限制、类型注解 |
| [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md) | 代码质量工具分析 - 工具栈优化、性能对比 |

---

### 🔬 类型检查 (14-17 系列)

| 文档 | 说明 |
|------|------|
| [14-pyright-quick-guide.md](./14-pyright-quick-guide.md) | Pyright 快速指南 - 基本使用、常用命令 |
| [15-pyright-fixes-summary.md](./15-pyright-fixes-summary.md) | Pyright 修复总结 - 修复的错误类型、最佳实践 |
| [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md) | Pyright 故障排除 - 常见错误解决、配置问题 |
| [17-pyright-overview.md](./17-pyright-overview.md) | Pyright 概览 - 完整功能介绍、架构设计 |

---

### 📡 API 文档 (18 系列 + api/ 目录)

| 文档 | 说明 |
|------|------|
| [18-api-response-format-fixes.md](./18-api-response-format-fixes.md) | API 响应格式修复记录 - OAuth2 端点、网关优化 |
| [api/](./api/) | **API 参考文档目录** |
| └─ [API_REFERENCE.md](./api/API_REFERENCE.md) | 完整 API 参考文档 |
| └─ [API_DOCUMENTATION_GUIDE.md](./api/API_DOCUMENTATION_GUIDE.md) | 文档访问指南 |
| └─ [README.md](./api/README.md) | API 文档索引 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

### 🔐 安全和认证

| 文档 | 说明 |
|------|------|
<<<<<<< HEAD
| [12-authentication-architecture.md](./12-authentication-architecture.md) | **认证架构设计** - JWT Token、OAuth 2.0、用户认证流程 |
=======
| [12-authentication-architecture.md](./12-authentication-architecture.md) | 认证架构设计 - JWT Token、用户认证流程 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

### 🌐 WebSocket 通信

| 文档 | 说明 |
|------|------|
<<<<<<< HEAD
| [18-websocket-usage.md](./18-websocket-usage.md) | **WebSocket 详细使用指南** - 连接建立、消息类型、心跳检测、完整示例 |
=======
| [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md) | Nacos 故障排除 - 服务注册失败、服务发现问题 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

### 🧪 测试

| 文档 | 说明 |
|------|------|
<<<<<<< HEAD
| [24-testing-websocket.md](./24-testing-websocket.md) | **WebSocket 测试完整指南** - 35+ 测试用例、连接测试、消息测试、并发测试、性能测试 |

---

### 📝 日志管理

| 文档 | 说明 |
|------|------|
| [19-service-logs-guide.md](./19-service-logs-guide.md) | **服务日志查看指南** - 日志位置、查看方法、搜索技巧 |

---

### 🛠️ 开发工具

| 文档 | 说明 |
|------|------|
| [21-shared-modules.md](./21-shared-modules.md) | **共享模块说明** - 公共组件、工具类、配置管理、数据库连接、缓存管理 |
| [22-shared-utils.md](./22-shared-utils.md) | **共享工具类说明** - JSON对比、模板验证、分页工具、主机验证等 |
| [26-scripts-guide.md](./26-scripts-guide.md) | **脚本使用指南** - 服务管理、代码质量检查、监控管理、文档生成 |

---

### 📡 API 文档

| 文档 | 说明 |
|------|------|
| [api/](./api/) | **API 参考文档目录** |
| └─ [API_REFERENCE.md](./api/API_REFERENCE.md) | **完整 API 参考** - 所有服务的 API 接口说明、访问指南（Swagger UI、ReDoc、OpenAPI JSON） |
| └─ [API Documentation.md](./api/API%20Documentation.md) | **自动生成的 API 文档** - 由 FastAPI 自动生成的 OpenAPI 规范文档 |
| [41-approve-hosts-interface-logic.md](./41-approve-hosts-interface-logic.md) | **approve_hosts 接口详细逻辑** - 同意启用主机接口完整流程、外部硬件接口调用、邮件通知机制 |

---

### 🗄️ 数据库

| 文档 | 说明 |
|------|------|
| [database/](./database/) | **数据库脚本目录** |
| └─ [index-optimization-recommendations.md](./database/index-optimization-recommendations.md) | **索引优化建议** - 查询模式分析、索引建议、性能优化 |
| [43-mariadb-ssl-configuration.md](./43-mariadb-ssl-configuration.md) | **MariaDB SSL 配置指南** - SSL/TLS 加密连接配置、自签名证书生成、客户端连接配置 |

---

### ⚡ 性能优化

| 文档 | 说明 |
|------|------|
| [performance/optimization-summary.md](./performance/optimization-summary.md) | **性能优化总结** - 2000并发支持、连接池配置、查询优化、MySQL/MariaDB Windows服务器配置 |
| [performance/service-optimization-plan.md](./performance/service-optimization-plan.md) | **服务优化方案** - 性能瓶颈分析、优化建议、实施计划 |
| [performance/k6-load-test-analysis.md](./performance/k6-load-test-analysis.md) | **k6 负载测试分析** - 500并发和200并发测试结果分析、性能瓶颈识别 |
| [performance/database-connection-pool-diagnosis.md](./performance/database-connection-pool-diagnosis.md) | **数据库连接池诊断** - 连接池监控、问题排查 |

---

### 🔧 故障排除

| 文档 | 说明 |
|------|------|
| [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md) | **Nacos 故障排除** - 服务注册失败、服务发现问题、常见错误解决 |
| [42-windows-pip-encoding-fix.md](./42-windows-pip-encoding-fix.md) | **Windows pip 编码错误修复** - UnicodeDecodeError 解决方案、环境变量设置、安装脚本 |

---

### 🚀 部署指南

| 文档 | 说明 |
|------|------|
| [03-deployment-guide.md](./03-deployment-guide.md) | **生产环境部署指南** - Docker、Docker Compose、生产环境配置 |
=======
| [03-deployment-guide.md](./03-deployment-guide.md) | 生产环境部署指南 - Docker、Kubernetes、CI/CD |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

### 📝 其他文档

| 文档 | 说明 |
|------|------|
<<<<<<< HEAD
| [CHANGELOG.md](./CHANGELOG.md) | **项目变更日志** |
=======
| [CHANGELOG.md](./CHANGELOG.md) | 项目变更日志 |
| [Execution Copilot - 后端开发计划.md](./Execution%20Copilot%20-%20后端开发计划.md) | 后端开发计划 |
| [database/](./database/) | 数据库脚本目录 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

## 📌 文档使用指南

### 🎯 对于新用户

1. **首先阅读** [快速开始指南](./00-quick-start.md) - 5分钟快速上手
2. **然后查看** [基础设施配置](./01-infrastructure-config.md) - 配置数据库和服务
3. **接着学习** [项目设置](./04-project-setup.md) - 完整环境配置

### 🛠️ 对于开发者

<<<<<<< HEAD
1. **代码规范** - 阅读 [代码质量配置](./08-code-quality-setup.md)
2. **类型检查** - 查看 [Pyright 概览](./17-pyright-overview.md) 和 [故障排除](./16-pyright-troubleshooting.md)
3. **API 接口** - 参考 [API 参考文档](./api/API_REFERENCE.md)
4. **WebSocket** - 学习 [WebSocket 使用指南](./18-websocket-usage.md)
5. **共享模块** - 查看 [共享模块说明](./21-shared-modules.md) 和 [共享工具类](./22-shared-utils.md)
6. **测试** - 参考 [WebSocket 测试指南](./24-testing-websocket.md)
=======
1. 阅读 **[代码质量配置](./08-code-quality-setup.md)** 了解代码规范
2. 查看 **[Pyright 快速指南](./14-pyright-quick-guide.md)** 学习类型检查
3. 参考 **[Python 3.8 兼容性](./09-python38-compatibility.md)** 避免兼容性问题
4. 查看 **[API 参考文档](./api/API_REFERENCE.md)** 了解 API 接口
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

### 🔧 对于运维人员

1. **部署** - 学习 [部署指南](./03-deployment-guide.md)
2. **监控** - 阅读 [监控快速参考](./07-monitoring-quick-reference.md)
3. **故障排除** - 查看 [Nacos 故障排除](./10-nacos-troubleshooting.md)
4. **日志** - 参考 [服务日志查看指南](./19-service-logs-guide.md)

---

## 🔍 快速搜索

### 按主题搜索

| 主题 | 相关文档 |
|------|----------|
<<<<<<< HEAD
| **快速开始** | [00-quick-start.md](./00-quick-start.md), [04-project-setup.md](./04-project-setup.md) |
| **基础设施** | [01-infrastructure-config.md](./01-infrastructure-config.md), [20-service-ip-port-config-explanation.md](./20-service-ip-port-config-explanation.md), [25-infrastructure-grafana-datasources.md](./25-infrastructure-grafana-datasources.md) |
| **监控追踪** | [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md), [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md), [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md), [11-jaeger-storage-config.md](./11-jaeger-storage-config.md), [23-monitoring-metrics-enhancement.md](./23-monitoring-metrics-enhancement.md) |
| **代码质量** | [08-code-quality-setup.md](./08-code-quality-setup.md), [09-python38-compatibility.md](./09-python38-compatibility.md), [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md), [27-code-optimization.md](./27-code-optimization.md) |
| **类型检查** | [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md), [17-pyright-overview.md](./17-pyright-overview.md) |
| **API 文档** | [api/API_REFERENCE.md](./api/API_REFERENCE.md), [41-approve-hosts-interface-logic.md](./41-approve-hosts-interface-logic.md) |
| **认证安全** | [12-authentication-architecture.md](./12-authentication-architecture.md) |
| **故障排除** | [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md), [42-windows-pip-encoding-fix.md](./42-windows-pip-encoding-fix.md) |
| **部署运维** | [03-deployment-guide.md](./03-deployment-guide.md) |
| **WebSocket** | [18-websocket-usage.md](./18-websocket-usage.md) |
| **测试** | [24-testing-websocket.md](./24-testing-websocket.md) |
| **日志管理** | [19-service-logs-guide.md](./19-service-logs-guide.md) |
| **开发工具** | [21-shared-modules.md](./21-shared-modules.md), [22-shared-utils.md](./22-shared-utils.md), [26-scripts-guide.md](./26-scripts-guide.md) |
=======
| **快速开始** | 00, 04 |
| **基础设施** | 01, 02 |
| **监控追踪** | 05, 06, 07, 11 |
| **代码质量** | 08, 09, 13 |
| **类型检查** | 14, 15, 16, 17 |
| **API 文档** | 18, api/ |
| **认证安全** | 12 |
| **故障排除** | 10 |
| **部署运维** | 03 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

### 按难度级别

- **初级** 🌱: [00-quick-start.md](./00-quick-start.md), [04-project-setup.md](./04-project-setup.md), [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md)
- **中级** 🌿: [01-infrastructure-config.md](./01-infrastructure-config.md), [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md), [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md), [08-code-quality-setup.md](./08-code-quality-setup.md), [12-authentication-architecture.md](./12-authentication-architecture.md), [18-websocket-usage.md](./18-websocket-usage.md), [24-testing-websocket.md](./24-testing-websocket.md)
- **高级** 🌳: [03-deployment-guide.md](./03-deployment-guide.md), [09-python38-compatibility.md](./09-python38-compatibility.md), [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md), [11-jaeger-storage-config.md](./11-jaeger-storage-config.md), [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md), [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md), [17-pyright-overview.md](./17-pyright-overview.md), [27-code-optimization.md](./27-code-optimization.md)

---

## 📝 文档命名规范

```
XX-topic-name.md
│  │         └── 主题名称（kebab-case）
│  └───────────── 顺序编号（00-99）
└──────────────── 文档编号
```

### 文档编号规则

- **00-04**: 快速开始和基础配置
<<<<<<< HEAD
- **05-07, 11, 23**: 监控和追踪
- **08-09, 13, 16-17, 27**: 代码质量
- **10**: 故障排除
- **12**: 安全和认证
- **18**: WebSocket 通信
- **19**: 日志管理
- **20-22, 25-26**: 基础设施和开发工具
- **24**: 测试
- **40-43**: 接口逻辑、性能监控、故障排除和数据库 SSL 配置
=======
- **01-02**: 基础设施配置
- **03**: 部署指南
- **05-07, 11**: 监控和追踪
- **08-09, 13**: 代码质量
- **10**: 故障排除
- **12**: 安全和认证
- **14-17**: 类型检查 (Pyright)
- **18**: API 响应格式
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

## ✨ 最近更新

<<<<<<< HEAD
- **2025-01-29**: 
  - ✅ 文档整理完成，统一移动到 docs 目录
  - ✅ 合并重复文档（代码优化相关）
  - ✅ 重新命名所有文档，按序编号
  - ✅ 更新文档索引和导航
  - ✅ 新增共享模块和工具类文档
  - ✅ 新增测试文档
  - ✅ 新增脚本使用指南
  - ✅ 清理修复文档（删除已完成的临时修复文档）
  - ✅ 合并性能分析文档（删除v2、v3版本，保留最新总结）
  - ✅ 更新性能优化文档为2000并发支持
  - ✅ 新增性能优化文档索引
  - ✅ 合并API文档（API_DOCUMENTATION_GUIDE合并到API_REFERENCE）
  - ✅ 删除重复的性能测试文档（k6-load-test-analysis-200-concurrent合并到主文档）
  - ✅ 删除重复的MySQL配置文档（合并到optimization-summary）
  - ✅ 删除API endpoints和OpenAPI JSON文件（内容已包含在API_REFERENCE中）
  - ✅ 删除gateway-service-features.md（内容已包含在其他文档中）
  - ✅ 合并gateway-load-balancing故障排查文档
- **2025-01-29**: 
  - ✅ 新增 approve_hosts 接口详细逻辑文档（41-approve-hosts-interface-logic.md）
  - ✅ 整理接口完整业务流程、外部硬件接口调用、邮件通知机制
  - ✅ 新增 Windows pip 编码错误修复文档（42-windows-pip-encoding-fix.md）
  - ✅ 创建 Windows 安装脚本（PowerShell 和 CMD 版本）
  - ✅ 新增 MariaDB SSL 配置指南（43-mariadb-ssl-configuration.md）
  - ✅ 包含自签名证书生成、Docker 配置、Python 客户端连接完整方案
  - ✅ 更新 .env.example 文件，添加 MariaDB SSL 配置选项
  - ✅ 更新所有文档中的环境变量示例，包含 SSL 配置说明
- **2025-11-01**: 
  - ✅ 合并重复API文档
  - ✅ 删除Admin Service相关文档引用（服务已移除）
  - ✅ 规范化API文档结构和命名
  - ✅ 更新文档索引和导航
  - ✅ 新增服务日志查看指南（19-service-logs-guide.md）
- **2025-10-31**: 添加本地启动指南和环境变量加载机制说明
- **2025-10-16**: 文档结构整理，移动模块相关文档到 shared/ 目录
- **2025-10-15**: 添加 API 响应格式修复记录
- **2025-10-13**: 添加 Pyright 类型检查完整文档
=======
- **2025-10-16**: 文档结构整理，移动模块相关文档到 shared/ 目录
- **2025-10-15**: 添加 API 响应格式修复记录
- **2025-10-15**: 重新生成所有微服务 API 文档
- **2025-10-13**: 添加 Pyright 类型检查完整文档
- **2025-10-13**: 整理文档结构，删除重复文档
- **2025-10-11**: 添加代码质量工具分析文档

---

## 📂 相关目录

### shared/ 目录中的文档

以下文档已移至 `shared/` 目录，与对应的代码模块放在一起：

| 文档 | 位置 | 说明 |
|------|------|------|
| DECORATORS_README.md | shared/common/ | 装饰器使用指南 |
| LOGGING_STANDARDS.md | shared/common/ | 日志规范 |
| LOGGING_MIGRATION_GUIDE.md | shared/common/ | 日志迁移指南 |
| METRICS_ENHANCEMENT.md | shared/monitoring/ | 监控指标增强说明 |
| decorators_examples.py | shared/common/ | 装饰器示例代码 |
| http_client_example.py | shared/common/ | HTTP 客户端示例 |
| metrics_examples.py | shared/monitoring/ | 监控指标示例 |
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)

---

## 📂 相关目录

### 服务级文档

以下文档位于各自服务目录，提供服务的具体使用说明：

<<<<<<< HEAD
| 文档 | 位置 | 说明 |
|------|------|------|
| Gateway Service README | services/gateway-service/README.md | 网关服务使用说明 |
| Auth Service README | services/auth-service/README.md | 认证服务使用说明 |
| Host Service README | services/host-service/README.md | 主机服务使用说明 |
=======
---

**📚 持续更新中... | 最后更新: 2025-10-16**
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
