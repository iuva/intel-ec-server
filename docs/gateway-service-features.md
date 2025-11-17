# Gateway Service 功能特点详解

## 📋 目录

- [概述](#概述)
- [核心功能](#核心功能)
- [HTTP 代理功能](#http-代理功能)
- [WebSocket 代理功能](#websocket-代理功能)
- [认证中间件](#认证中间件)
- [服务配置](#服务配置)
- [请求示例](#请求示例)
- [响应示例](#响应示例)
- [服务路由规则](#服务路由规则)
- [多语言支持](#多语言支持)
- [错误处理](#错误处理)

---

## 概述

Gateway Service 是 Intel EC 微服务架构的 **API 网关**，作为系统的统一入口，提供以下核心能力：

- ✅ **统一认证**: 所有请求在网关层进行 JWT 令牌验证
- ✅ **路由转发**: 智能路由请求到对应的后端微服务
- ✅ **静态配置**: 基于静态 IP 和端口的服务配置
- ✅ **WebSocket 支持**: 完整的 WebSocket 连接代理功能
- ✅ **用户信息传递**: 认证后自动将用户信息传递给后端服务
- ✅ **请求日志**: 完整的请求追踪和日志记录

---

## 核心功能

### 1. 统一认证中心

**功能说明**:

- Gateway 作为系统的唯一认证入口
- 所有需要认证的请求在 Gateway 层进行 JWT 令牌验证
- 验证通过后，用户信息通过 `X-User-Info` header 传递给后端服务
- 后端服务无需再次验证 token，直接从 header 获取用户信息

**优势**:

- ✅ 减少后端服务的认证负担
- ✅ 统一的认证逻辑，便于维护
- ✅ 提高系统安全性

### 2. 智能路由转发

**功能说明**:

- 基于静态配置的服务路由（IP + 端口）
- 自动路由到对应的后端微服务
- 支持路径重写和服务标识符前缀

**路由格式**:

```
/{service_name}/{subpath:path}
```

**服务配置**:

- 通过环境变量配置各服务的 IP 和端口
- 支持 Docker Compose 网络中的服务名解析
- 配置简单，无需额外的服务发现组件

### 4. WebSocket 代理

**功能说明**:

- 完整的 WebSocket 连接代理
- 支持 token 认证（从查询参数、Authorization 头或自定义头提取）
- 双向消息转发
- 连接状态监控

### 5. 多语言支持

**功能说明**:

- 支持通过 `Accept-Language` 请求头指定语言偏好
- 自动解析语言代码（如 `zh-CN` → `zh_CN`）
- 响应消息根据语言偏好自动翻译
- 响应中包含 `locale` 字段，标识使用的语言代码

**支持的语言**:

- `zh_CN`: 简体中文（默认）
- `en_US`: 美式英语

**使用方式**:

- 在请求头中添加: `Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8`
- 系统会自动解析并返回对应语言的响应消息
- 响应中包含 `locale` 字段，显示实际使用的语言代码

---

## HTTP 代理功能

### 路由规则

**格式**: `/{service_name}/{subpath:path}`

**示例**:

```
GET  /api/v1/host/admin/appr-host/list
POST /api/v1/auth/admin/login
PUT  /api/v1/host/admin/host/123
```

### 支持的方法

- `GET`: 查询请求
- `POST`: 创建请求
- `PUT`: 更新请求
- `DELETE`: 删除请求
- `PATCH`: 部分更新请求

### 请求处理流程

```
1. 客户端请求 → Gateway
2. 认证中间件验证 JWT token
3. 提取用户信息，存储在 request.state.user
4. 代理服务转发请求到后端服务
5. 将用户信息编码为 JSON，通过 X-User-Info header 传递
6. 后端服务接收请求，从 X-User-Info header 获取用户信息
7. 返回响应给客户端
```

### 请求头处理

**自动添加的 Header**:

- `X-User-Info`: 认证后的用户信息（JSON 格式）

**自动移除的 Header**:

- `host`: 避免与后端服务冲突
- `content-length`: 由代理服务重新计算

### 请求体处理

- 自动解析 JSON 格式的请求体
- 支持原始二进制数据转发
- 自动设置 `Content-Type` header

---

## WebSocket 代理功能

### 路由规则

**格式**: `/ws/{hostname}/{apiurl:path}`

**示例**:

```
ws://gateway:8000/api/v1/ws/host-service/agent/agent-123?token=xxx
```

### 认证方式

支持三种 token 提取方式（按优先级）:

1. **查询参数**: `?token=xxx`
2. **Authorization 头**: `Authorization: Bearer xxx`
3. **自定义头**: `X-Token: xxx`

### 连接流程

```
1. 客户端发起 WebSocket 连接
2. Gateway 提取并验证 token（在接受连接前）
3. 验证通过后接受连接
4. 转发连接到后端服务
5. 双向消息转发（客户端 ↔ 后端服务）
6. 连接关闭时清理资源
```

### 消息转发

- **客户端 → 后端**: 实时转发所有消息
- **后端 → 客户端**: 实时转发所有消息
- **错误处理**: 连接异常时自动关闭并记录日志

---

## 认证中间件

### 公开路径（无需认证）

以下路径不需要认证即可访问:

```python
public_paths = {
    "/",                          # 根路径
    "/health",                    # 健康检查
    "/health/detailed",          # 详细健康检查
    "/docs",                      # Swagger 文档
    "/redoc",                     # ReDoc 文档
    "/openapi.json",              # OpenAPI 规范
    "/api/v1/auth/admin/login",   # 管理员登录
    "/api/v1/auth/device/login",  # 设备登录
    "/api/v1/auth/logout",        # 登出
    "/api/v1/auth/refresh",       # Token 刷新
    "/api/v1/auth/auto-refresh",  # 自动续期
    "/api/v1/auth/introspect",    # Token 验证
}
```

### 认证流程

```
1. 提取 Authorization header（支持多种格式）
2. 检查是否为公开路径
3. 如果是公开路径，跳过认证
4. 如果是需要认证的路径：
   a. 提取 JWT token
   b. 调用 auth-service 验证 token
   c. 验证通过后，提取用户信息
   d. 将用户信息存储在 request.state.user
5. 继续处理请求
```

### Token 验证

- 调用 `auth-service` 的 `/api/v1/auth/introspect` 端点
- 验证 token 的有效性和过期时间
- 提取用户信息（user_id, username, user_type, active）

---

## 服务配置

### 静态配置方式

Gateway 使用静态配置方式管理后端服务地址，通过环境变量配置各服务的 IP 和端口。

### 服务地址配置

**环境变量配置**:

```bash
# 认证服务
SERVICE_HOST_AUTH=auth-service
AUTH_SERVICE_PORT=8001

# 主机服务
SERVICE_HOST_HOST=host-service
HOST_SERVICE_PORT=8003
```

**Docker Compose 网络**:

- 在 Docker Compose 环境中，可以使用服务名作为主机名
- Gateway 会自动解析服务名到对应的容器 IP
- 例如: `auth-service` → `http://auth-service:8001`

### 服务名称映射

Gateway 支持服务名称的短名称和完整名称映射:

```python
service_name_map = {
    "auth": "auth-service",
    "host": "host-service",
}
```

### 配置优势

- ✅ **简单直接**: 无需额外的服务发现组件
- ✅ **易于维护**: 配置集中管理
- ✅ **快速启动**: 无需等待服务注册
- ✅ **稳定可靠**: 不依赖外部服务发现系统

---

## 请求示例

### 1. HTTP GET 请求（查询待审批主机列表）

**请求**:

```bash
curl -X GET 'http://localhost:8000/api/v1/host/admin/appr-host/list?page=1&page_size=20' \
  -H 'Accept: application/json' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

**Gateway 处理**:

1. 解析路径: `service_name="host"`, `subpath="admin/appr-host/list"`
2. 验证 JWT token
3. 提取用户信息: `{user_id: "1", username: "admin", user_type: "admin", active: true}`
4. 解析语言偏好: `Accept-Language: zh-CN` → `locale: zh_CN`
5. 解析服务地址: `host` → `host-service:8003`
6. 转发请求到: `http://host-service:8003/api/v1/host/admin/appr-host/list?page=1&page_size=20`
7. 添加 header: `X-User-Info: {"user_id":"1","username":"admin","user_type":"admin","active":true}`
8. 传递 header: `Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8`

### 2. HTTP POST 请求（管理员登录）

**请求**:

```bash
curl -X POST 'http://localhost:8000/api/v1/auth/admin/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8' \
  -H 'Authorization: Basic Y2xpZW50X2lkOmNsaWVudF9zZWNyZXQ=' \
  -d 'username=admin&***REMOVED***word=your_***REMOVED***word&grant_type=***REMOVED***word'
```

**Gateway 处理**:

1. 解析路径: `service_name="auth"`, `subpath="admin/login"`
2. 检查路径 `/api/v1/auth/admin/login` 是否为公开路径
3. 发现是公开路径，跳过认证
4. 解析语言偏好: `Accept-Language: zh-CN` → `locale: zh_CN`
5. 解析服务地址: `auth` → `auth-service:8001`
6. 转发请求到: `http://auth-service:8001/api/v1/auth/admin/login`
7. 传递 header: `Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8`

### 3. HTTP POST 请求（设置维护通知邮箱）

**请求**:

```bash
curl -X POST 'http://localhost:8000/api/v1/host/admin/appr-host/maintain-email' \
  -H 'Content-Type: application/json' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -d '{
    "email": "admin@example.com,operator@example.com"
  }'
```

**Gateway 处理**:

1. 验证 JWT token
2. 提取用户信息: `{user_id: "1", username: "admin", user_type: "admin", active: true}`
3. 解析语言偏好: `Accept-Language: zh-CN` → `locale: zh_CN`
4. 解析 JSON 请求体
5. 转发请求到: `http://host-service:8003/api/v1/host/admin/appr-host/maintain-email`
6. 添加 header: `X-User-Info: {"user_id":"1","username":"admin","user_type":"admin","active":true}`
7. 传递 header: `Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8`

### 4. WebSocket 连接（Agent 通信）

**请求**:

```javascript
// JavaScript 示例
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/host-service/agent/agent-123?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...');

ws.onopen = () => {
  console.log('WebSocket 连接已建立');
  ws.send(JSON.stringify({ type: 'ping', data: 'hello' }));
};

ws.onmessage = (event) => {
  console.log('收到消息:', event.data);
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
  console.log('WebSocket 连接已关闭');
};
```

**Gateway 处理**:

1. 从查询参数提取 token: `?token=xxx`
2. 验证 token 有效性
3. 接受 WebSocket 连接
4. 转发连接到: `ws://host-service:8003/api/v1/ws/host/agent/agent-123?token=xxx`
5. 双向消息转发

---

## 响应示例

### 1. 成功响应（200 OK）

**响应（中文）**:

```json
{
  "code": 200,
  "message": "查询待审批主机列表成功",
  "data": {
    "hosts": [
      {
        "host_id": 1,
        "mg_id": "mg-001",
        "mac_addr": "00:11:22:33:44:55",
        "host_state": 5,
        "subm_time": "2025-11-10T10:00:00Z",
        "diff_state": 1
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "timestamp": "2025-11-10T14:00:00.000Z",
  "locale": "zh_CN"
}
```

**响应（英文）** - 当请求头为 `Accept-Language: en-US` 时:

```json
{
  "code": 200,
  "message": "Pending approval host list query successful",
  "data": {
    "hosts": [
      {
        "host_id": 1,
        "mg_id": "mg-001",
        "mac_addr": "00:11:22:33:44:55",
        "host_state": 5,
        "subm_time": "2025-11-10T10:00:00Z",
        "diff_state": 1
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "timestamp": "2025-11-10T14:00:00.000Z",
  "locale": "en_US"
}
```

### 2. 认证失败响应（401 Unauthorized）

**响应（中文）**:

```json
{
  "code": 401,
  "message": "缺少认证令牌",
  "error_code": "AUTHENTICATION_ERROR",
  "timestamp": "2025-11-10T14:00:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "zh_CN"
}
```

**响应（英文）** - 当请求头为 `Accept-Language: en-US` 时:

```json
{
  "code": 401,
  "message": "Missing authentication token",
  "error_code": "AUTHENTICATION_ERROR",
  "timestamp": "2025-11-10T14:00:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "en_US"
}
```

### 3. 服务不可用响应（503 Service Unavailable）

**响应（中文）**:

```json
{
  "code": 503,
  "message": "服务暂时不可用",
  "error_code": "SERVICE_UNAVAILABLE",
  "details": {
    "service_name": "host-service",
    "reason": "没有可用的服务实例"
  },
  "timestamp": "2025-11-10T14:00:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "zh_CN"
}
```

**响应（英文）** - 当请求头为 `Accept-Language: en-US` 时:

```json
{
  "code": 503,
  "message": "Service temporarily unavailable",
  "error_code": "SERVICE_UNAVAILABLE",
  "details": {
    "service_name": "host-service",
    "reason": "No available service instances"
  },
  "timestamp": "2025-11-10T14:00:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "en_US"
}
```

### 4. 网关内部错误响应（500 Internal Server Error）

**响应（中文）**:

```json
{
  "code": 500,
  "message": "网关内部错误",
  "error_code": "GATEWAY_ERROR",
  "timestamp": "2025-11-10T14:00:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "zh_CN"
}
```

**响应（英文）** - 当请求头为 `Accept-Language: en-US` 时:

```json
{
  "code": 500,
  "message": "Gateway internal error",
  "error_code": "GATEWAY_ERROR",
  "timestamp": "2025-11-10T14:00:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "en_US"
}
```

### 5. WebSocket 错误响应

**连接失败时发送的 JSON 消息（中文）**:

```json
{
  "code": 401,
  "message": "认证失败",
  "error_code": "AUTHENTICATION_ERROR",
  "timestamp": "2025-11-10T14:00:00.000Z",
  "locale": "zh_CN"
}
```

**连接失败时发送的 JSON 消息（英文）** - 当连接请求头为 `Accept-Language: en-US` 时:

```json
{
  "code": 401,
  "message": "Authentication failed",
  "error_code": "AUTHENTICATION_ERROR",
  "timestamp": "2025-11-10T14:00:00.000Z",
  "locale": "en_US"
}
```

---

## 服务路由规则

### 服务名称映射

Gateway 支持两种服务名称格式:

1. **完整服务名**: `auth-service`, `host-service`
2. **短名称**: `auth`, `host`（自动映射为完整服务名）

### 路径转换规则

**HTTP 请求**:

```
客户端请求: /api/v1/host/admin/appr-host/list
↓
Gateway 解析: service_name="host", subpath="admin/appr-host/list"
↓
Gateway 转发: http://host-service:8003/api/v1/host/admin/appr-host/list
```

**说明**:

- 客户端请求路径格式: `/api/v1/{service_name}/{subpath}`
- `service_name` 是服务标识符（如 `host`, `auth`）
- Gateway 将 `service_name` 解析为实际服务地址（如 `host` → `host-service:8003`）
- 转发时保持完整路径，包含服务标识符前缀

**WebSocket 请求**:

```
客户端连接: ws://gateway:8000/api/v1/ws/host-service/agent/agent-123?token=xxx
↓
Gateway 解析: hostname="host-service", apiurl="agent/agent-123"
↓
Gateway 转发: ws://host-service:8003/api/v1/ws/host/agent/agent-123?token=xxx
```

### 服务标识符前缀

Gateway 路径中必须包含服务标识符前缀，用于标识目标服务:

- `host` → 转发到 `host-service`
- `auth` → 转发到 `auth-service`

**路径格式**:

- HTTP: `/api/v1/{service_identifier}/{subpath}`
- WebSocket: `/api/v1/ws/{hostname}/{apiurl}`

**示例**:

- `/api/v1/host/admin/appr-host/list` → `host-service`
- `/api/v1/auth/admin/login` → `auth-service`
- `/api/v1/ws/host-service/agent/agent-123` → `host-service`

---

## 多语言支持

### Accept-Language 请求头

Gateway 支持通过 `Accept-Language` HTTP 请求头指定语言偏好，系统会自动解析并返回对应语言的响应消息。

**请求头格式**:

```
Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8
```

**支持的语言代码**:

- `zh-CN` 或 `zh` → `zh_CN` (简体中文)
- `en-US` 或 `en` → `en_US` (美式英语)
- 默认语言: `zh_CN`

**语言解析规则**:

1. 完整匹配: `zh-CN` → `zh_CN`
2. 部分匹配: `zh` → `zh_CN`, `en` → `en_US`
3. 优先级排序: 按 `q` 值从高到低排序
4. 默认回退: 如果无法匹配，使用默认语言 `zh_CN`

### 响应中的语言字段

所有响应都包含 `locale` 字段，标识实际使用的语言代码:

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {...},
  "timestamp": "2025-11-10T14:00:00.000Z",
  "locale": "zh_CN"  // 标识使用的语言代码
}
```

### 多语言消息翻译

系统使用 `message_key` 进行消息翻译:

- **请求**: 包含 `Accept-Language` 头
- **处理**: Gateway 解析语言偏好并传递给后端服务
- **响应**: 后端服务根据 `locale` 自动翻译 `message_key` 对应的消息
- **返回**: 响应中包含翻译后的 `message` 和 `locale` 字段

**示例**:

```bash
# 中文请求
curl -X GET 'http://localhost:8000/api/v1/host/admin/appr-host/list' \
  -H 'Accept-Language: zh-CN' \
  -H 'Authorization: Bearer ...'

# 响应
{
  "code": 200,
  "message": "查询待审批主机列表成功",  // 中文消息
  "locale": "zh_CN"
}

# 英文请求
curl -X GET 'http://localhost:8000/api/v1/host/admin/appr-host/list' \
  -H 'Accept-Language: en-US' \
  -H 'Authorization: Bearer ...'

# 响应
{
  "code": 200,
  "message": "Pending approval host list query successful",  // 英文消息
  "locale": "en_US"
}
```

---

## 错误处理

### 错误类型

1. **认证错误** (401):
   - Token 缺失
   - Token 无效
   - Token 过期

2. **服务错误** (503):
   - 服务不存在
   - 服务不可用
   - 没有可用的服务实例

3. **网关错误** (500):
   - 请求转发失败
   - 内部处理异常

4. **业务错误** (4xx):
   - 透传后端服务的业务错误

### 错误响应格式

所有错误响应遵循统一的格式:

```json
{
  "code": <HTTP状态码>,
  "message": "<错误消息>",
  "error_code": "<错误代码>",
  "timestamp": "<时间戳>",
  "request_id": "<请求ID>",
  "details": {
    // 可选的错误详情
  }
}
```

### 错误日志

Gateway 会记录详细的错误日志，包括:

- 错误类型和消息
- 请求路径和方法
- 用户信息（如果可用）
- 异常堆栈跟踪

---

## 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed
```

---

**最后更新**: 2025-11-16  
**版本**: v1.0.0
