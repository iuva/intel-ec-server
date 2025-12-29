# Gateway 未传递 X-User-Info Header 问题分析

## 🐛 问题描述

通过 Gateway 访问接口 `/api/v1/host/agent/hardware/report` 时，Gateway 没有传递 `X-User-Info` header 到后端服务。

## 🔍 问题分析

### 数据流程

```
Agent 请求
  ↓
Gateway 认证中间件 (AuthMiddleware)
  ↓ 验证 token
Auth Service /api/v1/auth/introspect
  ↓ 返回 IntrospectResponse { user_id, username, user_type, ... }
Gateway 认证中间件
  ↓ 构造 user_info = { user_id, username, user_type, active }
  ↓ 存储到 request.state.user
Gateway 代理端点 (proxy_request)
  ↓ 从 request.state.user 获取用户信息
  ↓ 检查 user_id 是否存在
  ↓ 如果存在，添加到 X-User-Info header
  ↓ 转发到后端服务
Host Service
  ↓ 从 X-User-Info header 获取用户信息
```

### 可能的问题点

#### 1. **认证中间件未正确验证 token**

**检查点**:
- Gateway 日志中是否有 "令牌验证成功" 的日志
- `request.state.user` 是否被正确设置

**可能原因**:
- Token 格式错误（不是 `Bearer <token>` 格式）
- Token 已过期或无效
- Auth Service 不可用或超时

#### 2. **Auth Service 返回的 user_id 为空**

**检查点**:
- Auth Service 日志中 `introspect_token` 的返回数据
- `IntrospectResponse.user_id` 是否为 None

**可能原因**:
- Device token 的 payload 中 `sub` 字段为空
- Token payload 格式不正确

#### 3. **Gateway 代理端点未正确传递 header**

**检查点**:
- Gateway 日志中是否有 "用户信息中缺少 user_id，跳过设置 X-User-Info header" 的警告
- `request.state.user` 是否存在但 `user_id` 为空

**可能原因**:
- `user_info.get("user_id")` 返回 None 或空字符串
- 代理端点的逻辑判断有问题

---

## 🔧 诊断步骤

### 步骤 1: 检查 Gateway 认证中间件日志

查看 Gateway 日志，确认 token 验证是否成功：

```bash
# 查看 Gateway 日志
docker-compose logs gateway-service | grep -A 10 "令牌验证成功\|令牌验证失败\|Token 验证"
```

**期望看到**:
```
令牌验证成功，允许访问
  user_id: <host_id>
  username: <username>
  user_type: device
```

**如果看到**:
```
令牌验证失败，拒绝访问
```
说明 token 验证失败，需要检查 token 是否有效。

### 步骤 2: 检查 Auth Service 日志

查看 Auth Service 日志，确认 introspect 接口返回的数据：

```bash
# 查看 Auth Service 日志
docker-compose logs auth-service | grep -A 10 "Token 验证成功\|introspect"
```

**期望看到**:
```
Token 验证成功 - 返回用户信息
  user_id: <host_id>
  username: <username>
  user_type: device
```

**如果看到**:
```
Token payload 中缺少 sub 字段
```
说明 device token 的 payload 中没有 `sub` 字段，需要检查 token 生成逻辑。

### 步骤 3: 检查 Gateway 代理端点日志

查看 Gateway 代理端点日志，确认是否设置了 X-User-Info header：

```bash
# 查看 Gateway 日志
docker-compose logs gateway-service | grep -A 5 "添加用户信息到请求头\|用户信息中缺少 user_id"
```

**期望看到**:
```
添加用户信息到请求头
  user_id: <host_id>
  username: <username>
  user_type: device
```

**如果看到**:
```
用户信息中缺少 user_id，跳过设置 X-User-Info header
```
说明 `request.state.user` 中的 `user_id` 为空，需要检查认证中间件的逻辑。

---

## ✅ 解决方案

### 方案 1: 检查 Device Token 生成逻辑

如果 Auth Service 返回的 `user_id` 为空，需要检查 device token 生成时是否正确设置了 `sub` 字段。

**检查位置**: `services/auth-service/app/services/auth_service.py::device_login()`

**期望代码**:
```python
# 生成 token 时，sub 字段应该是 host_id
payload = {
    "sub": str(host_id),  # ✅ 确保 sub 字段存在且不为空
    "username": device.username,
    "user_type": "device",
    # ...
}
```

### 方案 2: 增强 Gateway 日志

在 Gateway 的认证中间件和代理端点中添加更详细的日志，便于诊断问题。

**已实现**: Gateway 代码中已经包含了详细的日志记录。

### 方案 3: 修复 Gateway 代理端点逻辑

如果 `user_id` 为空字符串，应该也视为无效。当前代码已经检查了 `user_id` 是否存在，但可能需要更严格的检查。

**当前代码**:
```python
if not user_info.get("user_id"):
    logger.warning("用户信息中缺少 user_id，跳过设置 X-User-Info header")
```

**建议增强**:
```python
user_id = user_info.get("user_id")
if not user_id or (isinstance(user_id, str) and not user_id.strip()):
    logger.warning("用户信息中缺少 user_id，跳过设置 X-User-Info header")
```

---

## 🧪 测试验证

### 测试 1: 直接调用 Auth Service Introspect 接口

```bash
# 使用 device token 调用 introspect 接口
curl -X POST http://localhost:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "<device_token>"}'
```

**期望响应**:
```json
{
  "code": 200,
  "message": "验证成功",
  "data": {
    "active": true,
    "user_id": "<host_id>",
    "username": "<username>",
    "user_type": "device",
    "sub": "<host_id>"
  }
}
```

### 测试 2: 通过 Gateway 访问接口

```bash
# 通过 Gateway 访问接口，检查 X-User-Info header
curl -X POST http://localhost:8000/api/v1/host/agent/hardware/report \
  -H "Authorization: Bearer <device_token>" \
  -H "Content-Type: application/json" \
  -d '{"hardware_data": {...}}'
```

**检查 Gateway 日志**:
- 确认 "令牌验证成功" 日志中有 `user_id`
- 确认 "添加用户信息到请求头" 日志中有 `user_id`

**检查 Host Service 日志**:
- 确认 `get_current_agent` 函数能够从 `X-User-Info` header 获取用户信息

---

## 📋 检查清单

- [ ] Gateway 认证中间件日志显示 "令牌验证成功"
- [ ] Gateway 日志中的 `user_id` 不为空
- [ ] Auth Service 日志显示 `user_id` 不为空
- [ ] Gateway 代理端点日志显示 "添加用户信息到请求头"
- [ ] Host Service 能够从 `X-User-Info` header 获取用户信息
- [ ] Device token 的 payload 中包含 `sub` 字段
- [ ] `IntrospectResponse.user_id` 不为空

---

## 🔗 相关文件

- `services/gateway-service/app/middleware/auth_middleware.py` - Gateway 认证中间件
- `services/gateway-service/app/api/v1/endpoints/proxy.py` - Gateway 代理端点
- `services/auth-service/app/services/auth_service.py::introspect_token()` - Auth Service token 验证
- `services/host-service/app/api/v1/dependencies.py::get_current_agent()` - Host Service Agent 认证

---

**最后更新**: 2025-01-30
**问题状态**: 待诊断
**建议**: 先查看 Gateway 和 Auth Service 的日志，确认问题出现在哪个环节

