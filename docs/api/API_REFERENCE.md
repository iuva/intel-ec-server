# Intel EC 微服务API参考文档

## 📋 概述

本文档提供Intel EC微服务系统的完整API参考，包括所有服务的端点说明、使用示例和最佳实践。

**版本**: v1.0.0
**更新时间**: 2025-10-15
**兼容性**: OpenAPI 3.0

## 🏗️ 架构概览

### 服务架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gateway       │────│   Auth Service  │────│   Admin Service │
│   (8000)        │    │   (8001)        │    │   (8002)        │
│                 │    │                 │    │                 │
│ • API网关       │    │ • JWT认证       │    │ • 用户管理      │
│ • 路由转发      │    │ • OAuth 2.0     │    │ • 系统配置      │
│ • 负载均衡      │    │ • 会话管理      │    │ • 权限控制      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Host Service  │
                    │   (8003)        │
                    │                 │
                    │ • Host管理      │
                    │ • Agent通信     │
                    │ • WebSocket     │
                    │ • 实时监控      │
                    └─────────────────┘
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
        "admin-service": "healthy",
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
  "***REMOVED***word": "***REMOVED***"
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

## 👥 管理服务 (Admin Service)

**端口**: 8002
**文档**: http://localhost:8002/docs

### 核心功能
- 用户管理
- 角色权限管理
- 系统配置
- 审计日志

### 用户管理API

#### 获取用户列表
```http
GET /api/v1/users?page=1&page_size=20&keyword=admin
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "code": 200,
  "message": "获取用户列表成功",
  "data": {
    "data": [
      {
        "user_id": "user123",
        "username": "admin",
        "email": "admin@example.com",
        "is_active": true,
        "created_at": "2025-01-01T00:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

#### 创建用户
```http
POST /api/v1/users
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "username": "newuser",
  "email": "newuser@example.com",
  "***REMOVED***word": "***REMOVED***",
  "phone": "+8613800000000"
}
```

#### 更新用户信息
```http
PUT /api/v1/users/{user_id}
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "email": "updated@example.com",
  "phone": "+8613811111111"
}
```

#### 删除用户
```http
DELETE /api/v1/users/{user_id}
Authorization: Bearer <access_token>
```

### 角色和权限管理

#### 获取角色列表
```http
GET /api/v1/roles
Authorization: Bearer <access_token>
```

#### 分配用户角色
```http
POST /api/v1/users/{user_id}/roles
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "role_ids": ["admin", "manager"]
}
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

## 📚 相关资源

### 文档链接
- [快速开始指南](../00-quick-start.md)
- [项目架构说明](../01-project-overview.md)
- [部署指南](../03-deployment-guide.md)
- [监控配置](../05-monitoring-setup-complete.md)

### 开发资源
- [代码规范](../python-code-standards.md)
- [API设计规范](../api-design-standards.md)
- [数据库规范](../mariadb-database.md)

### 工具和脚本
- [开发环境脚本](../../scripts/dev_docs.sh)
- [文档生成脚本](../../scripts/generate_docs.sh)
- [代码质量检查](../../scripts/check_quality.sh)

---

## 📞 支持与反馈

如有API使用问题或建议，请通过以下方式联系：

- 📧 邮箱: dev@intel-ec.com
- 📖 文档: https://docs.intel-ec.com
- 🐛 问题反馈: https://github.com/intel-ec/ms/issues

**最后更新**: 2025-10-15
**版本**: v1.0.0
**维护者**: Intel EC 开发团队
