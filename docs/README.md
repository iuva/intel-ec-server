# Intel EC 微服务项目文档

**项目**: Intel EC 微服务系统  
**最后更新**: 2025-11-01

---

## 📋 文档概述

本目录包含 Intel EC 微服务项目的完整技术文档，涵盖快速开始、基础设施配置、监控系统、代码质量、API 参考等各个方面。

---

## 📚 文档目录

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

---

### 📊 监控和追踪

| 文档 | 说明 |
|------|------|
| [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md) | **完整监控系统配置** - Prometheus、Grafana、Jaeger 一体化配置 |
| [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md) | **Grafana 仪表板指南** - 仪表板创建、面板设计、监控指标 |
| [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md) | **监控快速参考** - 常用命令、指标查询、快速诊断 |
| [11-jaeger-storage-config.md](./11-jaeger-storage-config.md) | **Jaeger 存储配置** - 存储后端配置、性能优化 |

---

### 🔍 代码质量

| 文档 | 说明 |
|------|------|
| [08-code-quality-setup.md](./08-code-quality-setup.md) | **代码质量工具配置** - Ruff、MyPy、Pyright 完整配置 |
| [09-python38-compatibility.md](./09-python38-compatibility.md) | **Python 3.8 兼容性指南** - 特性限制、类型注解、最佳实践 |
| [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md) | **代码质量工具分析** - 工具栈优化、性能对比、选型建议 |
| [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md) | **Pyright 故障排除** - 常见错误解决、配置问题 |
| [17-pyright-overview.md](./17-pyright-overview.md) | **Pyright 概览** - 完整功能介绍、架构设计 |

---

### 🔐 安全和认证

| 文档 | 说明 |
|------|------|
| [12-authentication-architecture.md](./12-authentication-architecture.md) | **认证架构设计** - JWT Token、OAuth 2.0、用户认证流程 |

---

### 🌐 WebSocket 通信

| 文档 | 说明 |
|------|------|
| [18-websocket-usage.md](./18-websocket-usage.md) | **WebSocket 详细使用指南** - 连接建立、消息类型、心跳检测、完整示例 |

---

### 📡 API 文档

| 文档 | 说明 |
|------|------|
| [api/](./api/) | **API 参考文档目录** |
| └─ [API_DOCUMENTATION_GUIDE.md](./api/API_DOCUMENTATION_GUIDE.md) | **API 文档访问指南** - 如何查看和生成 API 文档、响应格式验证 |
| └─ [API_REFERENCE.md](./api/API_REFERENCE.md) | **完整 API 参考** - 所有服务的 API 接口说明 |
| └─ [release-hosts-api.md](./api/release-hosts-api.md) | **释放主机 API** - 释放主机资源接口文档 |
| └─ [retry-vnc-api.md](./api/retry-vnc-api.md) | **重试 VNC API** - 获取重试 VNC 连接列表接口文档 |
| └─ [vnc-report-api-update.md](./api/vnc-report-api-update.md) | **上报 VNC 连接结果 API** - VNC 连接结果上报接口文档 |

---

### 🔧 故障排除

| 文档 | 说明 |
|------|------|
| [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md) | **Nacos 故障排除** - 服务注册失败、服务发现问题、常见错误解决 |

---

### 🚀 部署指南

| 文档 | 说明 |
|------|------|
| [03-deployment-guide.md](./03-deployment-guide.md) | **生产环境部署指南** - Docker、Docker Compose、生产环境配置 |

---

### 📝 其他文档

| 文档 | 说明 |
|------|------|
| [CHANGELOG.md](./CHANGELOG.md) | **项目变更日志** |
| [database/](./database/) | **数据库脚本目录** |
| [archive/](./archive/) | **历史文档归档** - 重构记录、API重命名记录、迁移文档 |

### 📦 归档文档说明

`archive/` 目录包含以下类型的文档：
- **重构文档**: 代码重构最佳实践、工具类提取记录
- **API变更记录**: WebSocket API重命名、浏览器插件API重命名等
- **迁移文档**: 雪花ID迁移、功能实现记录等
- **会话记录**: 开发会话总结文档

这些文档主要用于历史参考，新功能开发时可以参考相关实践。

---

## 📌 文档使用指南

### 🎯 对于新用户

1. **首先阅读** [快速开始指南](./00-quick-start.md) - 5分钟快速上手
2. **然后查看** [基础设施配置](./01-infrastructure-config.md) - 配置数据库和服务
3. **接着学习** [项目设置](./04-project-setup.md) - 完整环境配置

### 🛠️ 对于开发者

1. **代码规范** - 阅读 [代码质量配置](./08-code-quality-setup.md)
2. **类型检查** - 查看 [Pyright 概览](./17-pyright-overview.md) 和 [故障排除](./16-pyright-troubleshooting.md)
3. **API 接口** - 参考 [API 参考文档](./api/API_REFERENCE.md)
4. **WebSocket** - 学习 [WebSocket 使用指南](./18-websocket-usage.md)

### 🔧 对于运维人员

1. **部署** - 学习 [部署指南](./03-deployment-guide.md)
2. **监控** - 阅读 [监控快速参考](./07-monitoring-quick-reference.md)
3. **故障排除** - 查看 [Nacos 故障排除](./10-nacos-troubleshooting.md)

---

## 🔍 快速搜索

### 按主题搜索

| 主题 | 相关文档 |
|------|----------|
| **快速开始** | [00-quick-start.md](./00-quick-start.md), [04-project-setup.md](./04-project-setup.md) |
| **基础设施** | [01-infrastructure-config.md](./01-infrastructure-config.md) |
| **监控追踪** | [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md), [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md), [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md), [11-jaeger-storage-config.md](./11-jaeger-storage-config.md) |
| **代码质量** | [08-code-quality-setup.md](./08-code-quality-setup.md), [09-python38-compatibility.md](./09-python38-compatibility.md), [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md) |
| **类型检查** | [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md), [17-pyright-overview.md](./17-pyright-overview.md) |
| **API 文档** | [api/API_REFERENCE.md](./api/API_REFERENCE.md), [api/API_DOCUMENTATION_GUIDE.md](./api/API_DOCUMENTATION_GUIDE.md) |
| **认证安全** | [12-authentication-architecture.md](./12-authentication-architecture.md) |
| **故障排除** | [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md) |
| **部署运维** | [03-deployment-guide.md](./03-deployment-guide.md) |
| **WebSocket** | [18-websocket-usage.md](./18-websocket-usage.md) |

### 按难度级别

- **初级** 🌱: [00-quick-start.md](./00-quick-start.md), [04-project-setup.md](./04-project-setup.md), [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md)
- **中级** 🌿: [01-infrastructure-config.md](./01-infrastructure-config.md), [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md), [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md), [08-code-quality-setup.md](./08-code-quality-setup.md), [12-authentication-architecture.md](./12-authentication-architecture.md), [18-websocket-usage.md](./18-websocket-usage.md)
- **高级** 🌳: [03-deployment-guide.md](./03-deployment-guide.md), [09-python38-compatibility.md](./09-python38-compatibility.md), [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md), [11-jaeger-storage-config.md](./11-jaeger-storage-config.md), [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md), [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md), [17-pyright-overview.md](./17-pyright-overview.md)

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
- **01**: 基础设施配置（合并后）
- **03**: 部署指南
- **05-07, 11**: 监控和追踪
- **08-09, 13**: 代码质量
- **10**: 故障排除
- **12**: 安全和认证
- **16-17**: 类型检查 (Pyright)
- **18**: WebSocket 通信

---

## ✨ 最近更新

- **2025-11-01**: 
  - ✅ 合并重复API文档（合并docs/api/README.md到API_DOCUMENTATION_GUIDE.md）
  - ✅ 删除Admin Service相关文档引用（服务已移除）
  - ✅ 规范化API文档结构和命名
  - ✅ 更新文档索引和导航
  - ✅ 整理归档文档说明
- **2025-10-31**: 添加本地启动指南和环境变量加载机制说明
- **2025-10-16**: 文档结构整理，移动模块相关文档到 shared/ 目录
- **2025-10-15**: 添加 API 响应格式修复记录
- **2025-10-13**: 添加 Pyright 类型检查完整文档

---

## 📂 相关目录

### shared/ 目录中的文档

以下文档位于 `shared/` 目录，与对应的代码模块放在一起：

| 文档 | 位置 | 说明 |
|------|------|------|
| DECORATORS_README.md | shared/common/ | 装饰器使用指南 |
| LOGGING_STANDARDS.md | shared/common/ | 日志规范 |
| LOGGING_MIGRATION_GUIDE.md | shared/common/ | 日志迁移指南 |
| METRICS_ENHANCEMENT.md | shared/monitoring/ | 监控指标增强说明 |

### archive/ 目录

临时记录和历史文档已移至 `docs/archive/` 目录：

- 会话记录和开发记录
- 迁移总结文档
- API 变更记录
- 重构最佳实践（已整合到规范中）

---

## 📧 联系我们

如果您对文档有任何疑问或建议，请：

1. 提交 Issue 到项目仓库
2. 参与文档贡献
3. 加入项目讨论组

---

**📚 持续更新中... | 最后更新: 2025-11-01**
