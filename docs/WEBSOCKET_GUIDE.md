# WebSocket 完整指南

## 📚 目录

- [快速开始](#快速开始)
- [API 访问指南](#api-访问指南)
- [认证架构](#认证架构)
- [错误处理](#错误处理)
- [故障排查](#故障排查)

---

## 🚀 快速开始

### WebSocket 连接示例

```javascript
// 设备连接 WebSocket
const token = "your-device-token-here";
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/host?token=${token}`);

ws.onopen = () => {
    console.log("WebSocket 连接成功");
    
    // 发送心跳
    ws.send(JSON.stringify({
        type: "heartbeat",
        timestamp: new Date().toISOString()
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log("收到消息:", message);
    
    switch(message.type) {
        case "welcome":
            console.log("欢迎消息:", message.message);
            break;
        case "heartbeat_ack":
            console.log("心跳确认");
            break;
        case "command":
            console.log("执行命令:", message.command);
            break;
    }
};

ws.onerror = (error) => {
    console.error("WebSocket 错误:", error);
};

ws.onclose = (event) => {
    console.log(`WebSocket 关闭: ${event.code} ${event.reason}`);
};
```

### HTTP 管理端点

```bash
# 获取活跃 Host 列表
curl -X GET 'http://localhost:8000/api/v1/host/ws/hosts' \
  -H "Authorization: Bearer $TOKEN"

# 发送单播消息
curl -X POST 'http://localhost:8000/api/v1/host/ws/send' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host_id": "1846486359367955051",
    "message": {
      "type": "command",
      "command": "restart"
    }
  }'

# 广播消息
curl -X POST 'http://localhost:8000/api/v1/host/ws/broadcast' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "notification",
      "message": "系统维护通知"
    }
  }'
```

---

## 📍 API 访问指南

### Gateway 路由规则

**路由模式**: `/api/v1/{service_name}/{subpath:path}`

| 功能 | 直接访问路径 | Gateway 访问路径 |
|-----|------------|----------------|
| WebSocket 连接 | `ws://host-service:8003/api/v1/ws/host` | `ws://localhost:8000/api/v1/ws/host` |
| 获取活跃 Hosts | `http://host-service:8003/api/v1/ws/hosts` | `http://localhost:8000/api/v1/host/ws/hosts` |
| 发送单播消息 | `http://host-service:8003/api/v1/ws/send` | `http://localhost:8000/api/v1/host/ws/send` |
| 广播消息 | `http://host-service:8003/api/v1/ws/broadcast` | `http://localhost:8000/api/v1/host/ws/broadcast` |

**关键点**:
- ✅ **WebSocket 连接**: `/api/v1/ws/host` (不需要 `/host` 前缀)
- ✅ **HTTP 管理端点**: `/api/v1/host/ws/hosts` (需要 `/host` 前缀)
- ❌ **错误路径**: `/api/v1/ws/host/hosts` (会返回 401)

### Gateway 转发逻辑

```
Gateway 接收: /api/v1/{service_name}/{subpath}
           ↓
服务识别: service_name → 查找后端服务
           ↓
URL 转发: http://{backend-service}:port/api/v1/{subpath}

示例:
  Gateway 接收: /api/v1/host/ws/hosts
  服务识别: service_name="host" → host-service:8003
  转发 URL: http://host-service:8003/api/v1/ws/hosts ✅
```

---

## 🔐 认证架构

### Token 获取

#### 管理员登录
```bash
curl -X POST 'http://localhost:8000/api/v1/auth/admin/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "***REMOVED***word": "your-***REMOVED***word"
  }'
```

#### 设备登录
```bash
curl -X POST 'http://localhost:8000/api/v1/auth/device/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "agent-123",
    "device_secret": "your-secret"
  }'
```

### Token 传递方式

1. **Authorization Header** (推荐)
```bash
-H "Authorization: Bearer your-token-here"
```

2. **Query Parameter** (WebSocket)
```
ws://localhost:8000/api/v1/ws/host?token=your-token-here
```

3. **X-Token Header**
```bash
-H "X-Token: your-token-here"
```

### Token 验证流程

```
客户端请求
    ↓
Gateway 认证中间件
    ↓
Auth Service Token 验证 (/api/v1/auth/introspect)
    ↓
验证成功 → 转发到后端服务
验证失败 → 返回 401/403
```

**Token 内容 (JWT Payload)**:
```json
{
  "sub": "1846486359367955051",  // host_id 或 user_id
  "mg_id": "abc_123",
  "host_ip": "127.0.0.2",
  "username": "sunwukong",
  "user_type": "device",
  "exp": 1761644208,
  "type": "access",
  "iat": 1761642408
}
```

---

## ⚠️ 错误处理

### HTTP 状态码

| 状态码 | 含义 | 原因 | 解决方案 |
|-------|------|------|---------|
| 200 | 成功 | 请求成功处理 | - |
| 401 | 未授权 | Token 缺失/过期/无效 | 重新登录获取新 Token |
| 403 | 禁止访问 | Token 类型错误或权限不足 | 使用正确类型的 Token |
| 404 | 未找到 | API 路径错误 | 检查路径拼写和格式 |
| 500 | 服务器错误 | 后端服务异常 | 查看日志排查问题 |

### WebSocket Close Codes

| Close Code | 含义 | 原因 |
|-----------|------|------|
| 1000 | 正常关闭 | 客户端主动关闭 |
| 1001 | 端点离开 | 页面关闭或导航 |
| 1005 | 无状态码 | 正常断开连接 |
| 1006 | 异常关闭 | 连接异常中断 |
| 1008 | 策略违规 | 认证失败 |
| 1011 | 服务器错误 | 后端处理异常 |

### 常见错误及解决方案

#### 1. 401 Unauthorized

**错误**: 
```json
{
  "code": 401,
  "message": "无效或过期的认证令牌",
  "error_code": "UNAUTHORIZED"
}
```

**原因**:
- Token 已过期
- Token 格式错误
- Token 不存在
- Gateway 调用 Auth Service 失败

**解决方案**:
```bash
# 1. 重新登录获取新 Token
curl -X POST 'http://localhost:8000/api/v1/auth/device/login' \
  -H 'Content-Type: application/json' \
  -d '{"device_id": "your-id", "device_secret": "your-secret"}'

# 2. 使用新 Token 重新请求
curl -X GET 'http://localhost:8000/api/v1/host/ws/hosts' \
  -H "Authorization: Bearer $NEW_TOKEN"
```

#### 2. 403 Forbidden (WebSocket)

**错误**: WebSocket 连接被拒绝，Close Code: 1008

**原因**:
- Token 类型错误（使用了 Admin Token 访问 Device 端点）
- 权限不足
- Host Service 认证失败

**解决方案**:
```bash
# 确保使用正确的 Token 类型
# Device WebSocket 需要 Device Token
curl -X POST 'http://localhost:8000/api/v1/auth/device/login' ...
```

#### 3. 404 Not Found

**错误**:
```json
{
  "code": 404,
  "message": "后端服务错误: 404",
  "error_code": "BACKEND_404"
}
```

**原因**:
- API 路径拼写错误
- 使用了错误的 Gateway 路由格式

**解决方案**:
```bash
# ❌ 错误路径
http://localhost:8000/api/v1/ws/host/hosts

# ✅ 正确路径
http://localhost:8000/api/v1/host/ws/hosts
```

---

## 🔧 故障排查

### 调试步骤

#### 1. 检查服务状态
```bash
# 查看所有服务状态
docker-compose ps

# 查看 Gateway 日志
docker-compose logs --tail=50 gateway-service

# 查看 Host Service 日志
docker-compose logs --tail=50 host-service

# 查看 Auth Service 日志
docker-compose logs --tail=50 auth-service
```

#### 2. 测试 Token 验证
```bash
# 直接测试 Auth Service introspect 端点
curl -X POST 'http://localhost:8001/api/v1/auth/introspect' \
  -H 'Content-Type: application/json' \
  -d '{"token": "your-token-here"}' | jq .

# 预期响应
{
  "code": 200,
  "message": "令牌验证完成",
  "data": {
    "active": true,
    "username": "sunwukong",
    "user_id": 1846486359367955051,
    "user_type": "device"
  }
}
```

#### 3. 测试后端服务
```bash
# 直接访问 Host Service (跳过 Gateway)
curl -X GET 'http://localhost:8003/api/v1/ws/hosts' \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### 4. 检查 WebSocket 连接
```bash
# 使用 wscat 测试 WebSocket
npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/ws/host?token=$TOKEN"

# 发送心跳
> {"type":"heartbeat","timestamp":"2025-10-28T10:00:00Z"}
```

### 监控指标

```bash
# 查看 Gateway Prometheus 指标
curl http://localhost:8000/metrics | grep http_requests

# 查看 Host Service 指标
curl http://localhost:8003/metrics | grep websocket
```

### 日志分析

**Gateway 日志关键字**:
```bash
# Token 验证日志
docker-compose logs gateway-service | grep "令牌验证"

# 请求转发日志
docker-compose logs gateway-service | grep "代理请求"

# 错误日志
docker-compose logs gateway-service | grep -E "ERROR|WARNING"
```

**Host Service 日志关键字**:
```bash
# WebSocket 连接日志
docker-compose logs host-service | grep "WebSocket"

# 消息处理日志
docker-compose logs host-service | grep "接收消息"

# 心跳日志
docker-compose logs host-service | grep "heartbeat"
```

---

## 📚 相关文档

- [WebSocket API 详细文档](../services/host-service/WEBSOCKET_API_GUIDE.md)
- [WebSocket 日志指南](../services/host-service/WEBSOCKET_LOGGING_GUIDE.md)
- [认证架构文档](./12-authentication-architecture.md)
- [API 参考文档](./api/README.md)

---

## 🔄 版本历史

### v1.0.0 (2025-10-28)
- ✅ 实现完整的 WebSocket 连接和管理功能
- ✅ 支持心跳监控和自动断线检测
- ✅ 修复 Gateway Token 验证问题
- ✅ 修复 Gateway URL 转发逻辑
- ✅ 优化错误处理和日志记录

