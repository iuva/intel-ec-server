# Intel EC 微服务管理系统 - 文档中心

欢迎来到 Intel EC 微服务管理系统的文档中心！本目录包含了项目的所有详细文档。

## 📚 文档索引

### 🚀 快速开始 (0x 系列)

#### [00-quick-start.md](./00-quick-start.md)
**5分钟快速上手指南**
- 环境准备
- 快速安装
- 服务启动
- 基本验证

#### [04-project-setup.md](./04-project-setup.md)
**项目完整设置指南**
- 详细安装步骤
- 开发环境配置
- IDE 配置推荐
- 常见问题解决

---

### 🛠️ 基础设施配置 (01-02 系列)

#### [01-external-database-setup.md](./01-external-database-setup.md)
**外部数据库配置指南**
- MariaDB 10.11 配置
- Redis 6.0+ 配置
- 数据库连接管理
- 连接池优化
- 故障排除

#### [02-external-services-config.md](./02-external-services-config.md)
**外部服务配置指南**
- Nacos 服务注册与发现
- Jaeger 分布式追踪
- 服务配置管理
- 环境变量设置

---

### 📊 监控和追踪 (05-07, 11 系列)

#### [05-monitoring-setup-complete.md](./05-monitoring-setup-complete.md)
**Prometheus + Grafana 监控系统完整配置**
- Prometheus 指标采集配置
- Grafana 仪表盘设置
- 自定义监控指标
- 告警规则配置
- 完整监控解决方案

#### [06-grafana-dashboard-guide.md](./06-grafana-dashboard-guide.md)
**Grafana 仪表盘使用指南**
- 仪表盘导入和配置
- 常用监控面板介绍
- 自定义面板创建
- 监控数据分析

#### [07-monitoring-quick-reference.md](./07-monitoring-quick-reference.md)
**监控系统快速参考**
- 常用命令速查
- 故障排除流程
- 性能优化建议
- 监控最佳实践

#### [11-jaeger-storage-config.md](./11-jaeger-storage-config.md)
**Jaeger 分布式追踪配置**
- Jaeger 存储后端配置
- 追踪数据持久化
- 性能调优
- 数据保留策略

---

### ✅ 代码质量 (08-09, 13 系列)

#### [08-code-quality-setup.md](./08-code-quality-setup.md)
**代码质量工具配置**
- Ruff 代码检查和格式化
- MyPy 静态类型检查
- Black 代码格式化
- Pre-commit hooks 配置
- CI/CD 集成

#### [09-python38-compatibility.md](./09-python38-compatibility.md)
**Python 3.8 兼容性说明**
- Python 3.8.10 特性说明
- 类型注解兼容性
- 依赖包版本限制
- 常见兼容性问题

#### [13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md)
**代码质量工具分析**
- Ruff vs Black vs Flake8 对比
- 工具选型决策
- 性能对比分析
- 最佳实践推荐

---

### 🔍 类型检查 - Pyright (14-17 系列)

#### [14-pyright-quick-guide.md](./14-pyright-quick-guide.md)
**Pyright 快速开始指南**
- 5分钟快速上手
- 常用命令和用法
- IDE 集成配置
- 快速参考

#### [15-pyright-fixes-summary.md](./15-pyright-fixes-summary.md)
**Pyright 类型检查修复总结**
- 完整修复记录（983 → 56 个错误）
- 详细修复步骤
- 配置优化说明
- 最佳实践总结

#### [16-pyright-troubleshooting.md](./16-pyright-troubleshooting.md)
**Pyright 故障排除指南**
- 常见问题解决（207 个错误）
- PYTHONPATH 配置说明
- 诊断步骤和方法
- FAQ 常见问题解答

#### [17-pyright-overview.md](./17-pyright-overview.md)
**Pyright 文档总览**
- Pyright 文档索引
- 学习路径推荐
- 团队协作指南
- 资源和工具链接

---

### 🔧 API 响应格式修复 (18 系列)

#### [18-api-response-format-fixes.md](./18-api-response-format-fixes.md)
**API响应格式修复记录**
- OAuth2端点响应格式统一
- 网关404响应安全优化
- 异常处理中间件修复
- 响应格式验证指南

---

### 🔐 安全和认证 (12 系列)

#### [12-authentication-architecture.md](./12-authentication-architecture.md)
**认证架构设计**
- JWT Token 认证机制
- 用户认证流程
- Session 管理
- 安全最佳实践

---

### 🔧 故障排除 (10 系列)

#### [10-nacos-troubleshooting.md](./10-nacos-troubleshooting.md)
**Nacos 服务注册与发现故障排除**
- Nacos 服务注册失败
- 服务发现问题
- 配置管理问题
- 常见错误解决

---

### 🚀 部署指南 (03 系列)

#### [03-deployment-guide.md](./03-deployment-guide.md)
**生产环境部署指南**
- Docker 容器化部署
- Kubernetes 部署配置
- CI/CD 流程设计
- 环境变量管理
- 监控和日志

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

### 🔧 对于运维人员

1. 学习 **[部署指南](./03-deployment-guide.md)** 了解部署流程
2. 阅读 **[监控快速参考](./07-monitoring-quick-reference.md)** 掌握监控命令
3. 查看各个故障排除文档解决常见问题

---

## 🔍 快速搜索

### 按主题搜索

| 主题 | 相关文档 |
|------|----------|
| **快速开始** | [00](./00-quick-start.md), [04](./04-project-setup.md) |
| **数据库** | [01](./01-external-database-setup.md) |
| **服务发现** | [02](./02-external-services-config.md), [10](./10-nacos-troubleshooting.md) |
| **监控** | [05](./05-monitoring-setup-complete.md), [06](./06-grafana-dashboard-guide.md), [07](./07-monitoring-quick-reference.md) |
| **追踪** | [11](./11-jaeger-storage-config.md) |
| **代码质量** | [08](./08-code-quality-setup.md), [13](./13-code-quality-tools-analysis.md) |
| **类型检查** | [14](./14-pyright-quick-guide.md), [15](./15-pyright-fixes-summary.md), [16](./16-pyright-troubleshooting.md), [17](./17-pyright-overview.md) |
| **Python 3.8** | [09](./09-python38-compatibility.md) |
| **认证** | [12](./12-authentication-architecture.md) |
| **API响应格式** | [18](./18-api-response-format-fixes.md) |
| **部署** | [03](./03-deployment-guide.md) |

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

- **0x**: 快速开始和基础配置
- **01-02**: 基础设施配置
- **03**: 部署指南
- **05-07**: 监控和追踪
- **08-09**: 代码质量
- **10-13**: 故障排除和工具
- **14-17**: 类型检查 (Pyright)
- **18**: API响应格式修复

---

## ✨ 最近更新

- **2025-10-15**: 添加 [API响应格式修复记录](./18-api-response-format-fixes.md) - OAuth2端点和网关404响应格式统一
- **2025-10-15**: 重新生成所有微服务API文档 (OpenAPI JSON + 端点列表)
- **2025-10-15**: 更新API文档验证指南，包含响应格式测试命令
- **2025-10-13**: 添加 Pyright 类型检查完整文档 (14-17)
- **2025-10-13**: 整理文档结构，删除重复文档
- **2025-10-12**: 删除临时和过时文档
- **2025-10-11**: 添加代码质量工具分析文档
- **2025-10-10**: 更新监控系统配置文档

---

## 📧 联系我们

如果您对文档有任何疑问或建议，请：

1. 提交 Issue 到项目仓库
2. 参与文档贡献
3. 加入项目讨论组

---

**📚 持续更新中... | 最后更新: 2025-10-15**
