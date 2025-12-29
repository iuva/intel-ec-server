# Agent 硬件上报接口 401 错误诊断指南

## 🐛 问题描述

调用 `/api/v1/host/agent/hardware/report` 接口时返回 401 Unauthorized 错误。

## 🔍 诊断步骤

### 步骤 1: 检查请求路径

**确认正确的路径**:
- ✅ **正确**: `/api/v1/host/agent/hardware/report`
- ❌ **错误**: `/api/v1/host/hardware/report`（缺少 `agent`）

### 步骤 2: 检查认证方式

接口支持两种认证方式：

#### 方式1: 通过 Gateway（推荐）

**请求路径**: `http://gateway:8000/api/v1/host/agent/hardware/report`

**请求头**:
```http
Authorization: Bearer <device_token>
```

**Gateway 处理流程**:
1. Gateway 认证中间件验证 token
2. Gateway 将用户信息添加到 `X-User-Info` header
3. Host Service 从 `X-User-Info` header 获取用户信息

**检查 Gateway 日志**:
```bash
docker-compose logs gateway-service | grep -E "令牌验证成功|添加用户信息到请求头|用户信息中缺少 user_id"
```

**期望看到**:
```
令牌验证成功，允许访问
  user_id: <host_id>
  user_type: device

✅ 添加用户信息到请求头
  user_id: <host_id>
  username: <username>
  user_type: device
```

**如果看到**:
```
用户信息中缺少 user_id，跳过设置 X-User-Info header
```
说明 Gateway 没有正确传递用户信息。

#### 方式2: 直接访问 Host Service（兼容）

**请求路径**: `http://host-service:8003/api/v1/host/agent/hardware/report`

**请求头**:
```http
Authorization: Bearer <device_token>
```

**Host Service 处理流程**:
1. 检查是否有 `X-User-Info` header（如果没有）
2. 从 `Authorization` header 提取 token
3. 调用 auth-service 验证 token
4. 从验证结果中提取用户信息

**检查 Host Service 日志**:
```bash
docker-compose logs host-service | grep -E "Agent 请求未包含 X-User-Info|从 JWT token 获取 Agent 信息|Agent JWT token 验证失败"
```

**期望看到**:
```
Agent 请求未包含 X-User-Info header，尝试从 JWT token 验证

初始化 TokenExtractor 验证 Agent token
  auth_service_url: http://auth-service:8001

Token 验证成功
  user_id: <host_id>
  username: <username>
  user_type: device

从 JWT token 获取 Agent 信息成功（直接访问）
```

**如果看到**:
```
Agent JWT token 验证失败
```
说明 token 验证失败，需要检查：
- Token 是否有效
- Token 是否过期
- Auth Service 是否可用

### 步骤 3: 检查 Token 有效性

**直接调用 Auth Service 验证 token**:
```bash
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

**如果返回**:
```json
{
  "code": 200,
  "data": {
    "active": false
  }
}
```
说明 token 已过期或无效，需要重新登录获取新 token。

### 步骤 4: 检查环境变量配置

**Host Service 环境变量**:
```bash
# 检查环境变量
docker-compose exec host-service env | grep AUTH_SERVICE
```

**期望配置**:
```bash
AUTH_SERVICE_URL=http://auth-service:8001
# 或
AUTH_SERVICE_IP=auth-service
AUTH_SERVICE_PORT=8001
```

**如果环境变量未设置**:
- Docker 环境：默认使用 `http://auth-service:8001`
- 本地环境：默认使用 `http://127.0.0.1:8001`

### 步骤 5: 检查 Auth Service 可用性

**测试 Auth Service 连接**:
```bash
# 从 Host Service 容器内测试
docker-compose exec host-service curl -f http://auth-service:8001/health

# 或从本地测试
curl -f http://localhost:8001/health
```

**期望响应**: `{"status": "healthy"}`

**如果连接失败**:
- 检查 Auth Service 是否运行：`docker-compose ps auth-service`
- 检查网络连接：`docker-compose exec host-service ping auth-service`

## 🔧 常见问题及解决方案

### 问题 1: Gateway 未传递 X-User-Info header

**症状**: Host Service 日志显示 "Agent 请求未包含 X-User-Info header"

**可能原因**:
1. Gateway 认证中间件未正确验证 token
2. Gateway 代理端点未正确传递 header
3. `request.state.user` 为空或 `user_id` 为空

**解决方案**:
1. 检查 Gateway 认证中间件日志，确认 token 验证是否成功
2. 检查 Gateway 代理端点日志，确认是否设置了 `X-User-Info` header
3. 查看 Gateway 日志中的详细诊断信息

### 问题 2: Token 验证失败

**症状**: Host Service 日志显示 "Agent JWT token 验证失败"

**可能原因**:
1. Token 已过期
2. Token 格式错误
3. Auth Service 不可用或超时
4. Token 中的 `user_type` 不是 "device"

**解决方案**:
1. 重新登录获取新 token
2. 检查 token 格式：`Authorization: Bearer <token>`
3. 检查 Auth Service 是否可用
4. 确认使用的是设备登录获取的 token（`user_type=device`）

### 问题 3: Auth Service URL 配置错误

**症状**: Host Service 日志显示 "Token 验证超时" 或 "无法连接到认证服务"

**可能原因**:
1. `AUTH_SERVICE_URL` 环境变量配置错误
2. 网络连接问题

**解决方案**:
1. 检查环境变量配置
2. 测试网络连接
3. 确认 Auth Service 地址是否正确

### 问题 4: user_id 为空

**症状**: Host Service 日志显示 "Token 验证成功但缺少 user_id"

**可能原因**:
1. Device token 的 payload 中 `sub` 字段为空
2. Auth Service 返回的 `user_id` 为空

**解决方案**:
1. 检查 device login 时 token 生成逻辑
2. 确认 `host_rec.id` 是否正确设置
3. 查看 Auth Service 日志，确认 introspect 返回的数据

## 📋 诊断检查清单

- [ ] 确认请求路径正确：`/api/v1/host/agent/hardware/report`
- [ ] 确认请求头包含 `Authorization: Bearer <token>`
- [ ] 检查 Gateway 日志，确认 token 验证是否成功
- [ ] 检查 Gateway 日志，确认是否设置了 `X-User-Info` header
- [ ] 检查 Host Service 日志，确认认证流程
- [ ] 直接调用 Auth Service introspect 接口验证 token
- [ ] 检查环境变量配置
- [ ] 测试 Auth Service 连接
- [ ] 确认使用的是设备登录获取的 token

## 🧪 测试命令

### 测试 1: 通过 Gateway 访问（推荐）

```bash
curl -X POST http://localhost:8000/api/v1/host/agent/hardware/report \
  -H "Authorization: Bearer <device_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "dmr_config": {
      "revision": 1,
      "mainboard": {
        "revision": 1
      }
    }
  }'
```

### 测试 2: 直接访问 Host Service

```bash
curl -X POST http://localhost:8003/api/v1/host/agent/hardware/report \
  -H "Authorization: Bearer <device_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "dmr_config": {
      "revision": 1,
      "mainboard": {
        "revision": 1
      }
    }
  }'
```

### 测试 3: 验证 Token

```bash
curl -X POST http://localhost:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "<device_token>"}'
```

## 🔗 相关文件

- `services/host-service/app/api/v1/dependencies.py::get_current_agent()` - Agent 认证依赖
- `services/host-service/app/api/v1/endpoints/agent_report.py::report_hardware()` - 硬件上报接口
- `services/gateway-service/app/middleware/auth_middleware.py` - Gateway 认证中间件
- `services/gateway-service/app/api/v1/endpoints/proxy.py` - Gateway 代理端点
- `shared/utils/token_extractor.py::TokenExtractor` - Token 验证工具类
- `services/auth-service/app/services/auth_service.py::introspect_token()` - Token 验证服务

---

**最后更新**: 2025-01-30
**问题状态**: 待诊断
**建议**: 按照诊断步骤逐一检查，查看日志定位问题

