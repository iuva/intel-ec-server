# Intel EC 微服务项目文档

**项目**: Intel EC 微服务系统  
**最后更新**: 2025-10-16

---

## 📋 文档概述

本目录包含 Intel EC 微服务项目的完整技术文档，涵盖快速开始、基础设施配置、监控系统、代码质量、API 参考等各个方面。

---

## 📚 文档目录

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

---

### 🔐 安全和认证 (12 系列)

| 文档 | 说明 |
|------|------|
| [12-authentication-architecture.md](./12-authentication-architecture.md) | 认证架构设计 - JWT Token、用户认证流程 |

---

### 🔧 故障排除 (10 系列)

| 文档 | 说明 |
|------|------|
| [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md) | Nacos 故障排除 - 服务注册失败、服务发现问题 |

---

### 🚀 部署指南 (03 系列)

| 文档 | 说明 |
|------|------|
| [03-deployment-guide.md](./03-deployment-guide.md) | 生产环境部署指南 - Docker、Kubernetes、CI/CD |

---

### 📝 其他文档

| 文档 | 说明 |
|------|------|
| [CHANGELOG.md](./CHANGELOG.md) | 项目变更日志 |
| [Execution Copilot - 后端开发计划.md](./Execution%20Copilot%20-%20后端开发计划.md) | 后端开发计划 |
| [database/](./database/) | 数据库脚本目录 |

---

## 📌 文档使用指南

### 🎯 对于新用户

1. 首先阅读 **[快速开始指南](./00-quick-start.md)**
2. 然后查看 **[项目设置](./04-project-setup.md)** 进行完整环境配置
3. 学习 **[监控系统配置](./05-monitoring-setup-complete.md)** 了解监控体系

### 🛠️ 对于开发者

1. 阅读 **[代码质量配置](./08-code-quality-setup.md)** 了解代码规范
2. 查看 **[Pyright 快速指南](./14-pyright-quick-guide.md)** 学习类型检查
3. 参考 **[Python 3.8 兼容性](./09-python38-compatibility.md)** 避免兼容性问题
4. 查看 **[API 参考文档](./api/API_REFERENCE.md)** 了解 API 接口

### 🔧 对于运维人员

1. 学习 **[部署指南](./03-deployment-guide.md)** 了解部署流程
2. 阅读 **[监控快速参考](./07-monitoring-quick-reference.md)** 掌握监控命令
3. 查看各个故障排除文档解决常见问题

---

## 🔍 快速搜索

### 按主题搜索

| 主题 | 相关文档 |
|------|----------|
| **快速开始** | 00, 04 |
| **基础设施** | 01, 02 |
| **监控追踪** | 05, 06, 07, 11 |
| **代码质量** | 08, 09, 13 |
| **类型检查** | 14, 15, 16, 17 |
| **API 文档** | 18, api/ |
| **认证安全** | 12 |
| **故障排除** | 10 |
| **部署运维** | 03 |

### 按难度级别

- **初级** 🌱: 00, 04, 07, 14
- **中级** 🌿: 01, 02, 05, 06, 08, 12, 18
- **高级** 🌳: 03, 09, 10, 11, 13, 15, 16, 17

---

## 📝 文档贡献

### 文档命名规范

```
XX-topic-name.md
│  │         └── 主题名称（kebab-case）
│  └───────────── 顺序编号（00-99）
└──────────────── 文档编号
```

### 文档类别

- **00-04**: 快速开始和基础配置
- **01-02**: 基础设施配置
- **03**: 部署指南
- **05-07, 11**: 监控和追踪
- **08-09, 13**: 代码质量
- **10**: 故障排除
- **12**: 安全和认证
- **14-17**: 类型检查 (Pyright)
- **18**: API 响应格式

---

## ✨ 最近更新

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

---

## 📧 联系我们

如果您对文档有任何疑问或建议，请：

1. 提交 Issue 到项目仓库
2. 参与文档贡献
3. 加入项目讨论组

---

**📚 持续更新中... | 最后更新: 2025-10-16**
