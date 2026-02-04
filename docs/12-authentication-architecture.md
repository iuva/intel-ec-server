# OAuth 2.0 微服务认证架构

> 以下是基于OAuth 2.0标准的微服务认证系统架构：

## 🏗️ **OAuth 2.0 系统架构概览**

```text
客户端 → Gateway Service → Auth Service (OAuth 2.0) → Admin/Host Service
     ↓           ↓              ↓                         ↓
   请求     认证+路由转发     OAuth令牌验证               业务处理
```

## 📋 **OAuth 2.0 认证流程**

### **1. 客户端认证流程**

#### **管理后台认证流程**

```text
1. POST /api/v1/auth-service/api/v1/oauth2/admin/token
   Authorization: Basic <base64(admin_client:admin_secret)>
   Body: grant_type=password&username=admin&password=secret&scope=admin

2. Auth Service → 验证客户端凭据 → 验证管理员凭据 → 生成OAuth令牌

3. 返回: {
     "access_token": "oauth-jwt-token",
     "token_type": "Bearer",
     "expires_in": 3600,
     "scope": "admin"
   }
```

#### **设备认证流程**

```text
1. POST /api/v1/auth-service/api/v1/oauth2/device/token
   Authorization: Basic <base64(device_client:device_secret)>
   Body: grant_type=client_credentials&device_id=device001&device_secret=secret&scope=device

2. Auth Service → 验证客户端凭据 → 验证设备凭据 → 生成OAuth令牌

3. 返回: {
     "access_token": "oauth-jwt-token",
     "token_type": "Bearer",
     "expires_in": 7200,
     "scope": "device"
   }
```

### **2. 网关认证中间件 (`AuthMiddleware`)**

- **位置**: `services/gateway-service/app/middleware/auth_middleware.py`
- **功能**:
  - 检查请求路径是否在公开白名单中
  - 验证 `Authorization: Bearer <token>` 头
  - 调用 Auth Service 的 `/api/v1/oauth2/introspect` 端点验证OAuth令牌
  - 将用户信息存储到 `request.state.user`

### **3. 公开路径白名单**

```python
public_paths = {
    "/", "/health", "/health/detailed", "/metrics", "/docs", "/redoc", "/openapi.json",
    # OAuth 2.0认证端点（公开访问）
    "/api/v1/auth-service/api/v1/oauth2/admin/token",
    "/api/v1/auth-service/api/v1/oauth2/device/token",
    "/api/v1/auth-service/api/v1/oauth2/introspect",
    "/api/v1/auth-service/api/v1/oauth2/revoke",
}
```

### **4. OAuth令牌验证流程**

```text
Gateway → Auth Service (8001) → OAuth 2.0 Introspect → 返回令牌信息
```

### **5. 请求转发流程**

```text
Gateway → 目标服务 (8001/8002/8003)
路由规则: /api/v1/{service_name}/{path} → http://{service_name}:{port}/{path}
```

## 🔐 **OAuth 2.0 认证机制详解**

### **授权类型**

#### **密码授权 (Password Grant) - 管理后台**

- **端点**: `POST /api/v1/oauth2/admin/token`
- **用途**: 管理员用户认证
- **流程**: 客户端认证 → 用户凭据验证 → 生成令牌

#### **客户端凭据授权 (Client Credentials) - 设备**

- **端点**: `POST /api/v1/oauth2/device/token`
- **用途**: 物联网设备认证
- **流程**: 客户端认证 → 设备凭据验证 → 生成令牌

### **OAuth 2.0 服务API**

| 端点 | 方法 | 功能 | 授权类型 |
|------|------|------|----------|
| `/api/v1/oauth2/admin/token` | POST | 管理后台令牌 | 密码授权 |
| `/api/v1/oauth2/device/token` | POST | 设备令牌 | 客户端凭据 |
| `/api/v1/oauth2/introspect` | POST | 令牌内省 | - |
| `/api/v1/oauth2/revoke` | POST | 令牌撤销 | - |
| `/api/v1/auth/refresh` | POST | 刷新令牌 | - |

### **令牌格式**

- **类型**: JWT (JSON Web Token) with OAuth 2.0 claims
- **结构**: `Authorization: Bearer <oauth_jwt_token>`
- **载荷包含**:
  - `sub`: 用户/设备ID
  - `client_id`: OAuth客户端ID
  - `scope`: 授权范围
  - `user_type`: 用户类型 (admin/device)
  - `permissions`: 权限列表

### **令牌内省响应格式**

```json
{
  "code": 200,
  "message": "令牌内省完成",
  "data": {
    "active": true,
    "client_id": "admin_client",
    "username": "admin",
    "device_id": null,
    "scope": "admin",
    "token_type": "Bearer",
    "exp": 1640995200,
    "iat": 1640991600,
    "sub": "123",
    "user_type": "admin",
    "permissions": ["admin", "read", "write"],
    "host_ip": null
  }
}
```

## 🚪 **OAuth权限验证**

### **权限检查逻辑**

1. **网关层认证**: 调用OAuth 2.0 introspect验证令牌有效性
2. **用户信息提取**: 从OAuth令牌中提取用户/设备信息和权限
3. **业务层校验**: 各服务根据用户类型和权限执行具体业务逻辑

### **OAuth用户信息数据结构**

```python
request.state.user = {
    "user_id": "123",           # 用户/设备ID
    "username": "admin",        # 用户名（管理员）
    "device_id": "device001",   # 设备ID（设备）
    "client_id": "admin_client", # OAuth客户端ID
    "scope": "admin",           # 授权范围
    "user_type": "admin",       # 用户类型: admin/device
    "permissions": ["admin", "read", "write"],
    "host_ip": null,            # 设备IP（仅设备）
    "active": true
}
```

### **用户类型区分**

#### **管理后台用户 (admin)**

- `user_type: "admin"`
- `username`: 管理员账号
- `permissions`: 管理员权限列表
- `scope`: "admin"

#### **设备用户 (device)**

- `user_type: "device"`
- `device_id`: 设备唯一标识
- `permissions`: 设备权限列表
- `scope`: "device"
- `host_ip`: 设备IP地址

## 🌐 **服务路由映射**

### **硬编码路由表** (`services/gateway-service/app/services/proxy_service.py`)

```python
service_routes = {
    "auth-service": "http://auth-service:8001",
    "host-service": "http://host-service:8003",
}
```

### **代理转发规则**

```text
GET /api/v1/host-service/admin/host/list → GET http://host-service:8003/api/v1/host/admin/host/list
POST /api/v1/auth-service/login → POST http://auth-service:8001/api/v1/auth/login
```

## 📊 **OAuth 2.0 完整请求示例**

### **管理后台认证流程**

```text
1. POST /api/v1/auth-service/api/v1/oauth2/admin/token
   Authorization: Basic YWRtaW5fY2xpZW50OmFkbWluX3NlY3JldA== (admin_client:admin_secret)
   Body: grant_type=password&username=admin&password=admin123&scope=admin

2. Gateway → Auth Service 直接转发 (公开路径)

3. Auth Service → 验证OAuth客户端 → 验证管理员凭据 → 生成OAuth令牌

4. 返回: {
     "access_token": "oauth-jwt-token...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "scope": "admin"
   }
```

### **设备认证流程**

```text
1. POST /api/v1/auth-service/api/v1/oauth2/device/token
   Authorization: Basic ZGV2aWNlX2NsaWVudDpkZXZpY2Vfc2VjcmV0 (device_client:device_secret)
   Body: grant_type=client_credentials&device_id=HOST-2025-001&device_secret=device123&scope=device

2. Gateway → Auth Service 直接转发 (公开路径)

3. Auth Service → 验证OAuth客户端 → 验证设备凭据 → 生成OAuth令牌

4. 返回: {
     "access_token": "oauth-jwt-token...",
     "token_type": "Bearer",
     "expires_in": 7200,
     "scope": "device"
   }
```

### **访问受保护资源流程**

```text
1. GET /api/v1/host-service/admin/host/list
   Header: Authorization: Bearer <oauth_jwt_token>

2. Gateway → 验证OAuth令牌 (调用Auth Service的oauth2/introspect)

3. 令牌有效 → 转发到 Host Service

4. Host Service → 检查用户类型和权限 → 返回数据
```

### **令牌内省验证**

```text
1. POST /api/v1/auth-service/api/v1/oauth2/introspect
   Body: token=oauth-jwt-token-here

2. Auth Service → 验证令牌 → 返回详细信息

3. 返回: {
     "active": true,
     "client_id": "admin_client",
     "username": "admin",
     "scope": "admin",
     "user_type": "admin",
     "permissions": ["admin"]
   }
```

## 🛡️ **OAuth 2.0 安全特性**

1. **OAuth 2.0标准**: 完全符合OAuth 2.0授权框架规范
2. **双重认证**: 客户端认证 + 用户/设备认证
3. **JWT令牌**: 安全的JSON Web Token，支持标准claims
4. **权限验证**: 支持基于scope和permissions的细粒度权限控制
5. **公开路径豁免**: OAuth认证端点等路径无需认证
6. **令牌内省**: 标准化的令牌验证机制
7. **令牌撤销**: 支持令牌的安全撤销
8. **客户端隔离**: 管理后台和设备使用独立的OAuth客户端

### ⚡ **性能优化**

1. **异步处理**: 全链路异步请求处理
2. **连接池**: HTTPX连接池复用
3. **缓存机制**: Redis缓存令牌验证结果
4. **数据库优化**: 索引优化和连接池管理
5. **令牌缓存**: JWT令牌本地缓存减少网络调用

### 🔧 **配置要点**

- **环境变量**:
  - `AUTH_SERVICE_URL`: 认证服务地址
  - `ADMIN_CLIENT_SECRET`: 管理后台客户端密钥
  - `DEVICE_CLIENT_SECRET`: 设备客户端密钥
- **超时设置**: 默认30秒超时，连接10秒
- **健康检查**: `/health` 端点监控服务状态
- **监控指标**: Prometheus指标收集OAuth请求统计

## 📋 **数据表结构**

### **OAuth客户端表 (oauth_clients)**

```sql
CREATE TABLE oauth_clients (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    client_id VARCHAR(255) UNIQUE NOT NULL,
    client_secret_hash VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    client_type VARCHAR(50) DEFAULT 'confidential',
    grant_types JSON,
    scope VARCHAR(255) DEFAULT 'read write',
    is_active BOOLEAN DEFAULT TRUE,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### **设备表 (devices)**

```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY,
    device_id VARCHAR(128) UNIQUE NOT NULL,
    device_secret_hash VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) DEFAULT 'iot',
    host_ip VARCHAR(32) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    permissions JSON DEFAULT ('["device"]'),
    last_seen DATETIME,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    del_flag TINYINT DEFAULT 0
);
```

### **会话表 (user_sessions)**

```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    entity_id INTEGER NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    client_ip VARCHAR(45),
    expires_at DATETIME NOT NULL,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    del_flag BOOLEAN DEFAULT FALSE
);
```

这个架构实现了**OAuth 2.0标准的微服务认证体系**，支持管理后台和物联网设备的统一认证，既保证了安全性，又提供了标准的授权机制。

## 📝 **更新历史**

- **2025-01-29**: 升级为OAuth 2.0认证架构
- **主要变更**:
  - 删除普通用户登录方式，保留管理后台和Host认证
  - 管理后台改为OAuth 2.0密码授权 (`/admin/token`)
  - Host认证改为OAuth 2.0客户端凭据授权 (`/device/token`)
  - 新增OAuth客户端表和设备表
  - 更新网关认证中间件支持OAuth令牌验证
  - 完善令牌内省和撤销机制
- **架构优势**: 符合OAuth 2.0标准，支持多租户认证，更好的安全性和扩展性
