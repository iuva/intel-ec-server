# WebSocket Token 验证流程分析报告

## 📋 概述

本文档分析 WebSocket token 验证流程，检查潜在问题并提供修复建议。

## 🔍 验证流程分析

### 1. Gateway WebSocket 代理验证流程

**位置**：`services/gateway-service/app/api/v1/endpoints/proxy.py::websocket_proxy()`

**流程**：
1. **Token 提取**（第 79-96 行）：
   - 从查询参数提取：`websocket.query_params.get("token")`
   - 从 Authorization 头提取：`Authorization: Bearer <token>`
   - 从自定义头提取：`X-Token` 或 `token`
   - ⚠️ **问题 1**：代码重复提取 `X-Token`（第 92 行和第 96 行）

2. **Token 验证**（第 125-154 行）：
   - 调用 `verify_token_string(token)` 验证 token
   - 如果验证失败（返回 `None`），发送错误消息并关闭连接
   - ✅ **正确**：在 accept 之前验证 token

3. **传递 host_id**（第 166-168 行）：
   - 将 `user_id` 作为 `host_id` 参数传递给后端服务
   - ✅ **正确**：后端服务无需重复验证

### 2. verify_token_string 函数

**位置**：`shared/common/websocket_auth.py::verify_token_string()`

**流程**：
1. **构建认证服务地址列表**（第 365-406 行）：
   - 从参数、环境变量、服务发现获取地址
   - ✅ **正确**：支持多地址降级策略

2. **调用 Auth Service 验证**（第 410-478 行）：
   - 调用 `/api/v1/auth/introspect` 端点
   - 检查 `data.get("active")` 是否为 `True`
   - 提取 `user_id` 或 `sub` 字段
   - ⚠️ **问题 2**：如果 `user_id` 和 `sub` 都为 `None`，返回 `None`（正确）
   - ⚠️ **问题 3**：没有验证 `user_id` 是否为空字符串或 0

3. **错误处理**（第 488-520 行）：
   - ✅ **正确**：支持多地址重试
   - ✅ **正确**：记录详细错误日志

### 3. Host Service WebSocket 端点验证流程

**位置**：`services/host-service/app/api/v1/endpoints/agent_websocket.py::_handle_websocket_connection()`

**流程**：
1. **获取 host_id**（第 51-85 行）：
   - **方式一**：从查询参数获取 `host_id`（网关传递）
   - **方式二**：调用 `verify_websocket_token(websocket)` 验证 token
   - ⚠️ **问题 4**：`verify_websocket_token` 目前被禁用（`skip_verification = True`）

2. **验证 host_id**（第 82-85 行）：
   - 如果 `host_id` 为空，返回错误
   - ✅ **正确**：验证 host_id 是否存在

### 4. verify_websocket_token 函数

**位置**：`shared/common/websocket_auth.py::verify_websocket_token()`

**当前状态**：
- ⚠️ **问题 5**：验证逻辑被禁用（`skip_verification = True`，第 90 行）
- 即使禁用，也会从 token 中解码信息（不验证签名）
- 如果启用，会调用 Auth Service 验证 token

**潜在问题**：
- 如果 Gateway 验证失败，Host Service 无法降级验证（因为验证被禁用）
- 直接解码 token 不验证签名，存在安全风险

## 🐛 发现的问题

### 问题 1：Gateway 重复提取 X-Token

**位置**：`services/gateway-service/app/api/v1/endpoints/proxy.py:92, 96`

**代码**：
```python
# 如果仍然没有，尝试读取常见自定义头
if not token:
    token = websocket.headers.get("X-Token") or websocket.headers.get("token")

# 如果还是没有，尝试从自定义头提取
if not token:
    token = websocket.headers.get("X-Token")  # ❌ 重复提取
```

**影响**：代码冗余，不影响功能

**修复建议**：删除重复的提取逻辑

### 问题 2：verify_token_string 未验证 user_id 是否有效

**位置**：`shared/common/websocket_auth.py:450`

**代码**：
```python
if data.get("active", False):
    user_id = data.get("user_id") or data.get("sub")
    if user_id:  # ⚠️ 只检查是否为 None，不检查是否为空字符串或 0
        return str(user_id)
```

**影响**：
- 如果 `user_id` 为空字符串 `""`，会返回空字符串
- 如果 `user_id` 为 `0`，会返回 `"0"`（可能是有效的 host_id）

**修复建议**：
```python
if data.get("active", False):
    user_id = data.get("user_id") or data.get("sub")
    # ✅ 验证 user_id 是否有效（不为 None、空字符串、0）
    if user_id and str(user_id).strip() and str(user_id) != "0":
        return str(user_id)
    # ⚠️ 注意：如果 host_id 可能为 0，需要特殊处理
```

### 问题 3：verify_websocket_token 被禁用但仍有安全风险

**位置**：`shared/common/websocket_auth.py:90-145`

**问题**：
- 验证逻辑被禁用（`skip_verification = True`）
- 但仍然从 token 中解码信息（不验证签名）
- 如果 token 被篡改，可能提取到错误的 `host_id`

**影响**：
- 如果 Gateway 验证失败，Host Service 无法降级验证
- 直接解码 token 不验证签名，存在安全风险

**修复建议**：
1. **保持禁用状态**（推荐）：因为 Gateway 已经验证了 token
2. **如果启用**：应该调用 Auth Service 验证 token，而不是直接解码

### 问题 4：Gateway 验证失败时未记录详细错误

**位置**：`services/gateway-service/app/api/v1/endpoints/proxy.py:127-154`

**问题**：
- 如果 `verify_token_string` 返回 `None`，只记录警告日志
- 没有记录 Auth Service 返回的详细错误信息

**修复建议**：
- 增强 `verify_token_string` 的返回值，包含错误信息
- 或者在 Gateway 中记录更详细的错误日志

### 问题 5：Host Service 直接解码 token 不验证签名

**位置**：`shared/common/websocket_auth.py:119`

**代码**：
```python
# 不验证签名，只解码以获取信息
decoded = jwt.decode(token, options={"verify_signature": False})
```

**问题**：
- 不验证签名，可能被篡改的 token 也能解码
- 如果 Gateway 验证失败，Host Service 无法正确验证

**影响**：
- 安全风险：如果 Gateway 被绕过，Host Service 无法正确验证 token
- 功能风险：如果 Gateway 验证失败，Host Service 无法降级验证

**修复建议**：
- 保持禁用状态，依赖 Gateway 验证
- 或者启用完整验证，调用 Auth Service 验证 token

## 🔧 修复方案

### 修复 1：删除 Gateway 重复提取 X-Token 的代码

### 修复 2：增强 verify_token_string 的 user_id 验证

### 修复 3：增强错误日志记录

### 修复 4：考虑启用 Host Service 的 token 验证（可选）

## 📝 测试建议

1. **测试 token 提取**：
   - 测试从查询参数提取 token
   - 测试从 Authorization 头提取 token
   - 测试从 X-Token 头提取 token

2. **测试 token 验证**：
   - 测试有效 token 验证成功
   - 测试无效 token 验证失败
   - 测试过期 token 验证失败
   - 测试 user_id 为空的情况

3. **测试降级策略**：
   - 测试 Auth Service 不可用时的行为
   - 测试多地址重试逻辑

4. **测试安全**：
   - 测试篡改 token 后的行为
   - 测试绕过 Gateway 直接连接 Host Service 的行为

## 🎯 优先级

1. **高优先级**：修复 verify_token_string 的 user_id 验证
2. **中优先级**：删除 Gateway 重复提取代码
3. **低优先级**：增强错误日志记录
4. **可选**：考虑启用 Host Service 的 token 验证

