# 接口文档访问指南

## 🎯 微服务文档端点

### Gateway Service (端口 8000)
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **健康检查**: http://localhost:8000/health
- **监控指标**: http://localhost:8000/metrics

### Auth Service (端口 8001)
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json
- **健康检查**: http://localhost:8001/health
- **监控指标**: http://localhost:8001/metrics

### Host Service (端口 8003)
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json
- **健康检查**: http://localhost:8003/health
- **监控指标**: http://localhost:8003/metrics

## 🚀 启动服务并访问文档

### 1. 启动单个服务
```bash
# 启动网关服务
cd services/gateway-service && python -m app.main

# 启动认证服务
cd services/auth-service && python -m app.main

# 启动主机服务
cd services/host-service && python -m app.main
```

### 2. 启动所有服务 (Docker Compose)
```bash
# 在项目根目录
docker-compose up -d gateway-service auth-service host-service
```

### 3. 访问文档
启动服务后，在浏览器中访问相应端口的 /docs 路径即可查看 Swagger UI 文档。

## 📋 文档特性

### 自动生成特性
- ✅ 基于 FastAPI 自动生成
- ✅ 实时同步代码变更
- ✅ 包含请求/响应示例
- ✅ 支持在线测试接口

### 统一格式
- ✅ 标准 OpenAPI 3.0 规范
- ✅ 统一的响应格式
- ✅ 错误响应文档化

### 安全特性
- ✅ JWT 认证集成
- ✅ 权限检查说明
- ✅ 请求头示例

## 🛠️ 生成静态文档

### 1. 使用脚本生成
```bash
# 生成所有服务的 OpenAPI 规范
./scripts/generate_docs.sh
```

### 2. 手动生成
```bash
# 获取服务的 OpenAPI JSON
curl http://localhost:8001/openapi.json > auth-service-api.json
curl http://localhost:8003/openapi.json > host-service-api.json

# 使用 Swagger Codegen 生成客户端代码
# JavaScript 客户端
swagger-codegen generate -i auth-service-api.json -l javascript -o client-js

# Python 客户端  
swagger-codegen generate -i auth-service-api.json -l python -o client-py

# TypeScript 客户端
swagger-codegen generate -i auth-service-api.json -l typescript-angular -o client-ts
```

## 📚 文档维护规范

### 端点文档要求
- ✅ 中文描述（函数docstring）
- ✅ 参数类型和描述
- ✅ 响应格式说明
- ✅ 错误情况说明
- ✅ 使用示例

### 版本管理
- ✅ API 版本控制（v1）
- ✅ 向后兼容性保证
- ✅ 版本变更日志

### 更新流程
1. 修改代码中的 docstring
2. 更新响应模型的 Field 描述
3. 重启服务验证文档
4. 提交代码时包含文档更新

## 🎨 代码优化文档

项目已完成全面的代码优化，相关文档位于 `.kiro/specs/code-optimization/` 目录：

### 优化文档
- **[需求文档](../.kiro/specs/code-optimization/requirements.md)** - 优化需求和目标
- **[设计文档](../.kiro/specs/code-optimization/design.md)** - 技术设计方案
- **[任务列表](../.kiro/specs/code-optimization/tasks.md)** - 实施任务清单
- **[最佳实践](../.kiro/specs/code-optimization/BEST_PRACTICES.md)** - 开发最佳实践
- **[架构文档](../.kiro/specs/code-optimization/ARCHITECTURE.md)** - 系统架构说明

### 优化成果
- ✅ 统一依赖注入模式
- ✅ 优化数据库会话管理
- ✅ 统一错误处理机制
- ✅ 统一 HTTP 客户端使用
- ✅ 增强监控指标收集
- ✅ 改进日志记录
- ✅ 提供装饰器工具

## 🔍 故障排查

### 文档无法访问
1. 检查服务是否正常启动
2. 确认端口配置正确
3. 查看服务日志中的错误信息

### 文档内容不完整
1. 检查所有端点的 docstring
2. 验证响应模型的 Field 描述
3. 确认路由正确注册

### 认证问题
1. 某些端点可能需要认证
2. 使用 JWT token 进行测试
3. 检查认证中间件配置

---

## 📋 服务列表

### 网关服务 (gateway-service)
- **端口**: 8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **健康检查**: http://localhost:8000/health
- **监控指标**: http://localhost:8000/metrics

### 认证服务 (auth-service)
- **端口**: 8001
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json
- **健康检查**: http://localhost:8001/health
- **监控指标**: http://localhost:8001/metrics

### 主机服务 (host-service)
- **端口**: 8003
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json
- **健康检查**: http://localhost:8003/health
- **监控指标**: http://localhost:8003/metrics

## 🔍 API响应格式验证

### 错误响应格式规范

所有API错误响应都应符合以下格式：

```json
{
  "code": 401,
  "message": "认证失败",
  "error_code": "UNAUTHORIZED",
  "details": null,
  "timestamp": "2025-10-15T10:00:00Z"
}
```

**禁止的格式**:
```json
{
  "detail": {
    "code": 401,
    "message": "认证失败"
  }
}
```

### 验证命令

#### OAuth2认证端点
```bash
# 错误的客户端凭据 - 应返回统一错误格式
curl -X POST http://localhost:8001/api/v1/oauth2/admin/token \
  -H "Authorization: Basic d3JvbmdfY2xpZW50Ondyb25nX3NlY3JldA==" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=wrong"

# 缺少必需参数 - 应返回统一错误格式
curl -X POST http://localhost:8001/api/v1/oauth2/admin/token \
  -H "Authorization: Basic YWRtaW5fY2xpZW50OmFkbWluX3NlY3JldA==" \
  -d "grant_type=***REMOVED***word"
```

#### 网关404响应
```bash
# 不存在的端点 - 不应包含available_endpoints字段
curl http://localhost:8000/api/v1/nonexistent
```

### 响应格式规范

#### ErrorResponse模型
- `code`: HTTP状态码 (int)
- `message`: 错误消息 (str)
- `error_code`: 错误类型编码 (str)
- `details`: 附加信息 (Optional[Dict])
- `timestamp`: 响应时间 (str)

#### SuccessResponse模型
- `code`: HTTP状态码 (int, 默认200)
- `message`: 成功消息 (str, 默认"操作成功")
- `data`: 响应数据 (Any)
- `timestamp`: 响应时间 (str)
- `request_id`: 请求ID (str)

## 📚 详细API文档

详细的API接口说明请参考：
- **[完整API参考](./API_REFERENCE.md)** - 所有服务的完整API端点说明
- **[端点列表文档](./gateway-service-endpoints.md)** - 各服务的API端点列表（由脚本自动生成）

## 📄 特定API端点文档

以下文档提供特定API端点的详细说明：
- **[释放主机API](./release-hosts-api.md)** - 释放主机资源API
- **[重试VNC列表API](./retry-vnc-api.md)** - 获取重试VNC连接列表API
- **[上报VNC连接结果API](./vnc-report-api-update.md)** - VNC连接结果上报API

## 📄 端点列表文档（自动生成）

以下文档由脚本自动生成，包含各服务的完整端点列表：
- **[网关服务端点列表](./gateway-service-endpoints.md)** - Gateway Service API端点
- **[认证服务端点列表](./auth-service-endpoints.md)** - Auth Service API端点
- **[主机服务端点列表](./host-service-endpoints.md)** - Host Service API端点

## 📄 OpenAPI规范文件

以下JSON文件包含完整的OpenAPI 3.0规范，可用于生成客户端代码：
- **[网关服务OpenAPI规范](./gateway-service-openapi.json)**
- **[认证服务OpenAPI规范](./auth-service-openapi.json)**
- **[主机服务OpenAPI规范](./host-service-openapi.json)**

---

**更新时间**: 2025-11-01
**适用版本**: FastAPI + OpenAPI 3.0
