# WebSocket API 访问指南

## 🎯 Gateway 路由规则

### Gateway 路由模式
```
/api/v1/{service_name}/{subpath:path}
         └─ 服务名       └─ 服务内路径
```

### 示例
```
访问路径: /api/v1/host/ws/hosts
           │       │    └─ subpath = "ws/hosts"
           │       └─ service_name = "host"
           └─ Gateway prefix

转发到: http://host-service:8003/api/v1/host/ws/hosts
                                    └─ 保留完整路径
```

## 📋 Host Service API 端点列表

### WebSocket 连接端点（通过 Gateway 访问）

| 直接访问 (Host Service) | 通过 Gateway 访问 | 说明 |
|---|---|---|
| `ws://localhost:8003/api/v1/ws/host` | `ws://localhost:8000/api/v1/host/ws/host` | 新版连接（推荐） |
| `ws://localhost:8003/api/v1/ws/host/{host_id}` | `ws://localhost:8000/api/v1/host/ws/host/{host_id}` | 旧版连接（兼容） |

### HTTP 管理端点（通过 Gateway 访问）

| 直接访问 (Host Service) | 通过 Gateway 访问 | 说明 |
|---|---|---|
| `http://localhost:8003/api/v1/ws/hosts` | `http://localhost:8000/api/v1/host/ws/hosts` | 获取活跃Host列表 |
| `http://localhost:8003/api/v1/ws/status/{host_id}` | `http://localhost:8000/api/v1/host/ws/status/{host_id}` | 检查连接状态 |
| `http://localhost:8003/api/v1/ws/send/{host_id}` | `http://localhost:8000/api/v1/host/ws/send/{host_id}` | 发送消息给指定Host |
| `http://localhost:8003/api/v1/ws/send-to-hosts` | `http://localhost:8000/api/v1/host/ws/send-to-hosts` | 发送消息给多个Hosts |
| `http://localhost:8000/api/v1/ws/broadcast` | `http://localhost:8000/api/v1/host/ws/broadcast` | 广播给所有Hosts |

## 🔐 认证要求

### HTTP 管理端点
- **需要认证**: ✅ 是
- **Token 类型**: JWT Access Token
- **获取方式**: `/api/v1/auth/admin/login` 或 `/api/v1/auth/device/login`
- **传递方式**:
  ```bash
  # 方式1: Authorization Header (推荐)
  curl -H "Authorization: Bearer YOUR_TOKEN" \
       http://localhost:8000/api/v1/host/ws/hosts

  # 方式2: X-Token Header
  curl -H "X-Token: YOUR_TOKEN" \
       http://localhost:8000/api/v1/host/ws/hosts

  # 方式3: Query Parameter
  curl "http://localhost:8000/api/v1/host/ws/hosts?token=YOUR_TOKEN"
  ```

### WebSocket 连接端点
- **需要认证**: ✅ 是
- **Token 类型**: JWT Access Token (来自 `/api/v1/auth/device/login`)
- **传递方式**:
  ```javascript
  // Query Parameter (推荐)
  ws://localhost:8000/api/v1/host/ws/host?token=YOUR_TOKEN

  // 或在 WebSocket 握手时通过 Header
  // (需要客户端支持)
  ```

## 🧪 测试示例

### 1. 获取管理员 Token

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "***REMOVED***word": "Admin@123"
  }'

# 响应
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}

# 提取 Token
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. 测试 HTTP 管理端点

```bash
# ✅ 正确: 通过 Gateway 访问
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/host/ws/hosts

# ✅ 正确: 直接访问 Host Service
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8003/api/v1/ws/hosts

# ❌ 错误: Gateway 路径错误
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/ws/host/hosts
# 返回: 401 Unauthorized (service_name 解析错误)
```

### 3. 测试 WebSocket 连接

```bash
# 安装 wscat (如果没有)
npm install -g wscat

# ✅ 正确: 通过 Gateway 连接
wscat -c "ws://localhost:8000/api/v1/host/ws/host?token=$TOKEN"

# ✅ 正确: 直接连接 Host Service
wscat -c "ws://localhost:8003/api/v1/ws/host?token=$TOKEN"

# ❌ 错误: Gateway 路径错误
wscat -c "ws://localhost:8000/api/v1/ws/host/host?token=$TOKEN"
# 结果: 连接失败或 403
```

### 4. 发送消息给指定 Host

```bash
# 通过 Gateway 发送
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "command",
    "command_id": "cmd_001",
    "command": "restart",
    "args": {"service": "nginx"}
  }' \
  http://localhost:8000/api/v1/host/ws/send/1846486359367955051

# 响应
{
  "code": 200,
  "message": "消息发送成功",
  "data": {
    "host_id": "1846486359367955051",
    "success": true
  }
}
```

### 5. 广播消息

```bash
# 通过 Gateway 广播
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "notification",
    "message": "系统维护通知",
    "data": {"maintenance_time": "2025-10-28 22:00:00"}
  }' \
  "http://localhost:8000/api/v1/host/ws/broadcast?exclude_host_id=1846486359367955051"

# 响应
{
  "code": 200,
  "message": "广播完成 (99/100成功)",
  "data": {
    "total_count": 100,
    "success_count": 99,
    "failed_count": 1,
    "exclude_host_id": "1846486359367955051"
  }
}
```

## 🐛 常见错误及解决方案

### 错误1: 401 Unauthorized
```log
WARNING  | gateway-service | app.middleware.auth_middleware:dispatch:175 | 令牌验证失败，拒绝访问
```

**可能原因**:
1. **路径错误** ❌: `/api/v1/ws/host/hosts` (service_name 解析为 "ws")
   - **解决**: 使用正确路径 `/api/v1/host/ws/hosts`

2. **Token 过期**:
   - **解决**: 重新登录获取新 Token

3. **Token 格式错误**:
   - **解决**: 确保使用 `Bearer YOUR_TOKEN` 格式

4. **Token 无效**:
   - **解决**: 检查 Token 是否正确复制完整

### 错误2: 404 Not Found
```json
{
  "code": 404,
  "message": "请求的资源不存在",
  "error_code": "RESOURCE_NOT_FOUND"
}
```

**可能原因**:
1. **路径拼写错误**: `/api/v1/host/ws/hostss` (多了一个 s)
2. **缺少路径段**: `/api/v1/ws/hosts` (通过 Gateway 必须包含 service_name)
3. **服务未启动**: Host Service 未运行

**解决**:
```bash
# 检查服务状态
docker-compose ps host-service

# 查看 Swagger 文档确认正确路径
open http://localhost:8003/docs
```

### 错误3: 403 Forbidden (WebSocket)
```json
{
  "code": 403,
  "message": "WebSocket 认证失败，Token 无效或已过期",
  "error_code": "WEBSOCKET_AUTH_FAILED"
}
```

**可能原因**:
1. **Token 类型错误**: 使用了 Admin Token 而不是 Device Token
   - **解决**: 使用 `/api/v1/auth/device/login` 获取设备 Token

2. **Token 未包含 host_id**: Token 的 `sub` 字段为空
   - **解决**: 确保 device_login 时正确存储了 `host_rec.id`

## 📚 API 文档链接

- **Gateway Swagger**: http://localhost:8000/docs
- **Host Service Swagger**: http://localhost:8003/docs
- **Auth Service Swagger**: http://localhost:8001/docs

## 🔗 相关文档

- [WEBSOCKET_API_GUIDE.md](services/host-service/WEBSOCKET_API_GUIDE.md) - 详细的 WebSocket API 文档
- [WEBSOCKET_LOGGING_GUIDE.md](services/host-service/WEBSOCKET_LOGGING_GUIDE.md) - WebSocket 日志分析指南
- [WEBSOCKET_AUTH_OPTIMIZATION.md](WEBSOCKET_AUTH_OPTIMIZATION.md) - 认证优化文档

---

**最后更新**: 2025-10-28
**核心要点**: 
- ✅ 通过 Gateway 访问时，路径格式为 `/api/v1/{service_name}/{service_path}`
- ✅ Host Service 管理端点: `/api/v1/host/ws/hosts` (不是 `/api/v1/ws/host/hosts`)
- ✅ 所有管理端点都需要 JWT Token 认证

