# Intel EC 微服务API参考文档

## 📋 概述

本文档提供Intel EC微服务系统的完整API参考，包括所有服务的端点说明、使用示例和最佳实践。

**版本**: v1.0.0
**更新时间**: 2025-01-29
**兼容性**: OpenAPI 3.0

> **注意**: Admin Service 已从项目中移除，相关功能已整合到其他服务中。

---

## 🎯 文档访问指南

### 微服务文档端点

#### Gateway Service (端口 8000)
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **健康检查**: http://localhost:8000/health
- **监控指标**: http://localhost:8000/metrics

#### Auth Service (端口 8001)
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json
- **健康检查**: http://localhost:8001/health
- **监控指标**: http://localhost:8001/metrics

#### Host Service (端口 8003)
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json
- **健康检查**: http://localhost:8003/health
- **监控指标**: http://localhost:8003/metrics

### 🚀 启动服务并访问文档

#### 1. 启动单个服务
```bash
# 启动网关服务
cd services/gateway-service && python -m app.main

# 启动认证服务
cd services/auth-service && python -m app.main

# 启动主机服务
cd services/host-service && python -m app.main
```

#### 2. 启动所有服务 (Docker Compose)
```bash
# 在项目根目录
docker-compose up -d gateway-service auth-service host-service
```

#### 3. 访问文档
启动服务后，在浏览器中访问相应端口的 `/docs` 路径即可查看 Swagger UI 文档。

### 📋 文档特性

#### 自动生成特性
- ✅ 基于 FastAPI 自动生成
- ✅ 实时同步代码变更
- ✅ 包含请求/响应示例
- ✅ 支持在线测试接口

#### 统一格式
- ✅ 标准 OpenAPI 3.0 规范
- ✅ 统一的响应格式
- ✅ 错误响应文档化

#### 安全特性
- ✅ JWT 认证集成
- ✅ 权限检查说明
- ✅ 请求头示例

### 🛠️ 生成静态文档

#### 1. 使用脚本生成
```bash
# 生成所有服务的 OpenAPI 规范
./scripts/generate_docs.sh
```

#### 2. 手动生成
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

### 📚 文档维护规范

#### 端点文档要求
- ✅ 中文描述（函数docstring）
- ✅ 参数类型和描述
- ✅ 响应格式说明
- ✅ 错误情况说明
- ✅ 使用示例

#### 版本管理
- ✅ API 版本控制（v1）
- ✅ 向后兼容性保证
- ✅ 版本变更日志

#### 更新流程
1. 修改代码中的 docstring
2. 更新响应模型的 Field 描述
3. 重启服务验证文档
4. 提交代码时包含文档更新

### 🔍 API响应格式验证

#### 错误响应格式规范

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

#### 验证命令

##### OAuth2认证端点
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

##### 网关404响应
```bash
# 不存在的端点 - 不应包含available_endpoints字段
curl http://localhost:8000/api/v1/nonexistent
```

#### 响应格式规范

##### ErrorResponse模型
- `code`: HTTP状态码 (int)
- `message`: 错误消息 (str)
- `error_code`: 错误类型编码 (str)
- `details`: 附加信息 (Optional[Dict])
- `timestamp`: 响应时间 (str)

##### SuccessResponse模型
- `code`: HTTP状态码 (int, 默认200)
- `message`: 成功消息 (str, 默认"操作成功")
- `data`: 响应数据 (Any)
- `timestamp`: 响应时间 (str)
- `request_id`: 请求ID (str)

### 📄 特定API端点文档

以下文档提供特定API端点的详细说明：
- **[释放主机API](./release-hosts-api.md)** - 释放主机资源API
- **[重试VNC列表API](./retry-vnc-api.md)** - 获取重试VNC连接列表API
- **[上报VNC连接结果API](./vnc-report-api-update.md)** - VNC连接结果上报API

### 📄 端点列表文档（自动生成）

以下文档由脚本自动生成，包含各服务的完整端点列表：
- **[网关服务端点列表](./gateway-service-endpoints.md)** - Gateway Service API端点
- **[认证服务端点列表](./auth-service-endpoints.md)** - Auth Service API端点
- **[主机服务端点列表](./host-service-endpoints.md)** - Host Service API端点

### 📄 OpenAPI规范文件

以下JSON文件包含完整的OpenAPI 3.0规范，可用于生成客户端代码：
- **[网关服务OpenAPI规范](./gateway-service-openapi.json)**
- **[认证服务OpenAPI规范](./auth-service-openapi.json)**
- **[主机服务OpenAPI规范](./host-service-openapi.json)**

### 📄 自动生成的API文档

> **注意**: `API Documentation.md` 是由工具自动生成的OpenAPI文档，请勿手动编辑。如需更新，请修改代码中的API定义，然后重新生成文档。

---

## 🏗️ 架构概览

## 🏗️ 架构概览

### 服务架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gateway       │────│   Auth Service  │────│   Host Service  │
│   (8000)        │    │   (8001)        │    │   (8003)        │
│                 │    │                 │    │                 │
│ • API网关       │    │ • JWT认证       │    │ • Host管理      │
│ • 路由转发      │    │ • OAuth 2.0     │    │ • Agent通信     │
│ • 负载均衡      │    │ • 会话管理      │    │ • WebSocket     │
│ • 认证验证      │    │ • 令牌刷新      │    │ • 实时监控      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 统一响应格式

#### 成功响应
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "result": "响应数据"
  },
  "timestamp": "2025-10-15T10:30:00Z"
}
```

#### 错误响应
```json
{
  "code": 404,
  "message": "请求的资源不存在",
  "error_code": "RESOURCE_NOT_FOUND",
  "details": {
    "method": "GET",
    "path": "/api/v1/users/123"
  },
  "timestamp": "2025-10-15T10:30:00Z"
}
```

## 🚪 网关服务 (Gateway Service)

**端口**: 8000
**文档**: http://localhost:8000/docs

### 核心功能
- API路由转发
- 负载均衡
- 认证验证
- 请求限流
- 熔断降级

### 主要端点

#### 健康检查
```http
GET /health
```

**响应示例**:
```json
{
  "code": 200,
  "message": "服务运行正常",
  "data": {
    "service": "gateway-service",
    "status": "healthy",
    "version": "1.0.0"
  }
}
```

#### 详细健康检查
```http
GET /health/detailed
```

**响应示例**:
```json
{
  "code": 200,
  "message": "详细健康检查完成",
  "data": {
    "service": "gateway-service",
    "status": "healthy",
    "checks": {
      "nacos": "connected",
      "backend_services": {
        "auth-service": "healthy",
        "host-service": "healthy"
      }
    }
  }
}
```

#### 监控指标
```http
GET /metrics
```

返回Prometheus格式的监控指标。

## 🔐 认证服务 (Auth Service)

**端口**: 8001
**文档**: http://localhost:8001/docs

### 核心功能
- JWT令牌管理
- 用户认证
- OAuth 2.0 授权
- 会话管理
- 令牌刷新

### 认证流程

#### 1. 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "***REMOVED***word": "your_***REMOVED***word"
}
```

**成功响应**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user_info": {
      "user_id": "user123",
      "username": "admin",
      "permissions": ["admin", "user:read"]
    }
  }
}
```

#### 2. 令牌刷新
```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

#### 3. 令牌验证
```http
POST /api/v1/auth/introspect
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
}
```

**响应**:
```json
{
  "code": 200,
  "message": "令牌验证成功",
  "data": {
    "active": true,
    "user_id": "user123",
    "username": "admin",
    "permissions": ["admin", "user:read"],
    "exp": 1697123456
  }
}
```

#### 4. 用户登出
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

### OAuth 2.0 端点

#### 管理员令牌
```http
POST /api/v1/oauth2/admin/token
Content-Type: application/x-www-form-urlencoded

grant_type=***REMOVED***word&username=admin&***REMOVED***word=***REMOVED***&scope=admin
```

#### 设备令牌
```http
POST /api/v1/oauth2/device/token
Content-Type: application/x-www-form-urlencoded

grant_type=***REMOVED***word&username=device001&***REMOVED***word=device_secret&scope=device
```

## 🖥️ 主机服务 (Host Service)

**端口**: 8003
**文档**: http://localhost:8003/docs

### 核心功能
- 主机信息管理
- Agent通信
- WebSocket实时连接
- 系统监控

### 主机管理API

#### 获取主机列表
```http
GET /api/v1/hosts
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "code": 200,
  "message": "获取主机列表成功",
  "data": [
    {
      "host_id": "host001",
      "hostname": "web-server-01",
      "ip_address": "192.168.1.100",
      "os": "Ubuntu 20.04",
      "status": "online",
      "last_seen": "2025-10-15T10:30:00Z"
    }
  ]
}
```

#### 注册新主机
```http
POST /api/v1/hosts
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "hostname": "web-server-02",
  "ip_address": "192.168.1.101",
  "os": "CentOS 7",
  "tags": ["web", "production"]
}
```

### WebSocket通信

#### Agent连接
```javascript
// JavaScript WebSocket连接示例
const ws = new WebSocket('ws://localhost:8003/api/v1/ws/agent/agent001');

ws.onopen = function(event) {
    console.log('WebSocket连接已建立');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};

ws.onclose = function(event) {
    console.log('WebSocket连接已关闭');
};
```

#### 消息格式
```json
{
  "type": "heartbeat",
  "agent_id": "agent001",
  "timestamp": "2025-10-15T10:30:00Z",
  "data": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 23.1
  }
}
```

## 🔑 认证和授权

### JWT令牌

所有API请求（除公开端点外）都需要在请求头中包含有效的JWT令牌：

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

### 权限控制

系统使用基于角色的访问控制(RBAC)，权限格式为 `resource:action`：

- `user:read` - 读取用户信息
- `user:create` - 创建用户
- `admin:*` - 管理员权限
- `device:connect` - 设备连接权限

### 公开端点

以下端点无需认证即可访问：

- `GET /health` - 健康检查
- `GET /metrics` - 监控指标
- `GET /docs` - API文档
- `GET /redoc` - ReDoc文档
- `GET /openapi.json` - OpenAPI规范

## 📊 监控和指标

### Prometheus指标

所有服务都提供Prometheus格式的监控指标：

```http
GET /metrics
```

#### HTTP指标
- `http_requests_total` - HTTP请求总数
- `http_request_duration_seconds` - 请求响应时间
- `http_request_size_bytes` - 请求大小
- `http_response_size_bytes` - 响应大小

#### 数据库指标
- `db_queries_total` - 数据库查询总数
- `db_query_duration_seconds` - 查询响应时间

#### 缓存指标
- `cache_operations_total` - 缓存操作总数
- `cache_hit_ratio` - 缓存命中率

### Jaeger追踪

系统集成了分布式追踪，所有请求都会被追踪：

- **Jaeger UI**: http://localhost:16686
- **追踪包含**: HTTP请求、数据库查询、缓存操作、业务逻辑

## 🧪 测试和示例

### 使用cURL测试

```bash
# 1. 获取访问令牌
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","***REMOVED***word":"***REMOVED***"}'

# 2. 使用令牌访问API
curl -X GET http://localhost:8002/api/v1/users \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 使用Python客户端

```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        # 登录获取令牌
        response = await client.post(
            "http://localhost:8001/api/v1/auth/login",
            json={"username": "admin", "***REMOVED***word": "***REMOVED***"}
        )
        token_data = response.json()
        access_token = token_data["data"]["access_token"]

        # 使用令牌访问API
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(
            "http://localhost:8002/api/v1/users",
            headers=headers
        )
        users = response.json()
        print("用户列表:", users)

asyncio.run(test_api())
```

## 🚨 错误处理

### HTTP状态码

- `200` - 成功
- `201` - 创建成功
- `400` - 请求参数错误
- `401` - 未授权
- `403` - 权限不足
- `404` - 资源不存在
- `422` - 数据验证失败
- `500` - 服务器内部错误

### 错误响应格式

所有错误响应都遵循统一的格式：

```json
{
  "code": 404,
  "message": "用户不存在",
  "error_code": "USER_NOT_FOUND",
  "details": {
    "user_id": "user123"
  },
  "timestamp": "2025-10-15T10:30:00Z"
}
```

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

## 📚 相关资源

### 文档链接
- [快速开始指南](../00-quick-start.md)
- [基础设施配置](../01-infrastructure-config.md)
- [部署指南](../03-deployment-guide.md)
- [监控配置](../05-monitoring-setup-complete.md)

### 开发资源
- [代码规范](../08-code-quality-setup.md)
- [API设计规范](../api-design-standards.md)
- [数据库规范](../43-mariadb-ssl-configuration.md)

### 工具和脚本
- [脚本使用指南](../26-scripts-guide.md)
- [代码质量检查](../../scripts/check_quality.sh)

---

**最后更新**: 2025-01-29  
**文档版本**: 2.0.0（合并访问指南）
