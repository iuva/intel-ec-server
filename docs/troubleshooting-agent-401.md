# Agent 认证 401 错误排查指南

## 问题描述

`get_current_agent` 函数返回 401 错误，但 token 还未过期。

## 可能的原因

### 1. 请求来源 IP 验证失败

**问题**：请求不是从 Gateway IP 发起的。

**检查方法**：
- 查看 Host Service 日志，查找以下日志：
  ```
  拒绝非 Gateway 来源的 Agent 请求 | client_host=xxx | forwarded_for=xxx | real_ip=xxx
  ```

**解决方案**：
- 确保请求通过 Gateway 转发，不要直接访问 Host Service
- 检查 `GATEWAY_IP_ADDRESSES` 配置是否包含实际的 Gateway IP
- 如果使用 Docker，确保 Gateway IP 为 `172.20.0.100`
- 如果使用本地开发，确保 Gateway IP 为 `127.0.0.1` 或 `localhost`

**代码位置**：
- `services/host-service/app/api/v1/dependencies.py:475-521`

### 2. X-User-Info Header 缺失

**问题**：Gateway 没有正确设置 `X-User-Info` header。

**检查方法**：
- 查看 Host Service 日志，查找以下日志：
  ```
  Agent 未接收到 X-User-Info header | path=xxx | client=xxx
  ```
- 查看 Gateway 日志，确认是否设置了 `X-User-Info` header：
  ```
  添加用户信息到请求头 | user_id=xxx | username=xxx | user_type=xxx
  ```

**可能的原因**：
1. Gateway 的 `AuthMiddleware` 验证 token 失败
2. Gateway 的 `proxy.py` 没有正确从 `request.state.user` 获取用户信息
3. Auth Service 的 `introspect` 端点返回的格式不正确

**解决方案**：
- 检查 Gateway 日志，确认 token 验证是否成功
- 检查 Gateway 的 `request.state.user` 是否包含 `user_id` 字段
- 检查 Auth Service 的 `introspect` 端点返回的响应格式

**代码位置**：
- Gateway: `services/gateway-service/app/middleware/auth_middleware.py:376`
- Gateway: `services/gateway-service/app/api/v1/endpoints/proxy.py:410-414`
- Host Service: `services/host-service/app/api/v1/dependencies.py:558-582`

### 3. user_id 字段缺失

**问题**：`X-User-Info` header 存在，但缺少 `user_id` 字段。

**检查方法**：
- 查看 Host Service 日志，查找以下日志：
  ```
  用户信息中缺少 user_id (host_id)
  ```
- 检查 Gateway 日志，确认 `user_info` 是否包含 `user_id`：
  ```
  令牌验证成功 - Auth Service 返回有效用户信息 | user_id=xxx
  ```

**可能的原因**：
1. Auth Service 的 `introspect` 端点返回的 `user_id` 为 `None`
2. Gateway 的 `AuthMiddleware` 没有正确提取 `user_id` 字段
3. Device token 的 payload 中 `sub` 字段为空

**解决方案**：
- 检查 Auth Service 的 `introspect_token` 方法是否正确提取 `user_id`（从 `sub` 字段）
- 检查 Device token 的 payload 是否包含 `sub` 字段
- 检查 Gateway 的 `AuthMiddleware` 是否正确从 Auth Service 响应中提取 `user_id`

**代码位置**：
- Auth Service: `services/auth-service/app/services/auth_service.py:419-456`
- Gateway: `services/gateway-service/app/middleware/auth_middleware.py:527-532`
- Host Service: `services/host-service/app/api/v1/dependencies.py:636-659`

### 4. X-User-Info Header JSON 格式错误

**问题**：`X-User-Info` header 存在，但 JSON 格式不正确。

**检查方法**：
- 查看 Host Service 日志，查找以下日志：
  ```
  解析 Agent X-User-Info header 失败 | error=xxx | header_preview=xxx
  ```

**解决方案**：
- 检查 Gateway 的 `proxy.py` 是否正确序列化 `user_info` 为 JSON
- 确保 `json.dumps(user_info, ensure_ascii=False)` 正确执行

**代码位置**：
- Gateway: `services/gateway-service/app/api/v1/endpoints/proxy.py:414`
- Host Service: `services/host-service/app/api/v1/dependencies.py:585-633`

## 排查步骤

### 步骤 1：检查 Gateway 日志

查看 Gateway 日志，确认：
1. Token 验证是否成功
2. `request.state.user` 是否包含 `user_id` 字段
3. `X-User-Info` header 是否被正确设置

```bash
# 查看 Gateway 日志
docker-compose logs gateway-service | grep -E "令牌验证成功|添加用户信息到请求头|X-User-Info"
```

### 步骤 2：检查 Host Service 日志

查看 Host Service 日志，确认：
1. 请求来源 IP 是否正确
2. `X-User-Info` header 是否存在
3. `user_id` 字段是否存在

```bash
# 查看 Host Service 日志
docker-compose logs host-service | grep -E "拒绝非 Gateway|未接收到 X-User-Info|缺少 user_id"
```

### 步骤 3：检查 Auth Service 日志

查看 Auth Service 日志，确认：
1. `introspect` 端点是否被正确调用
2. 返回的响应是否包含 `user_id` 字段

```bash
# 查看 Auth Service 日志
docker-compose logs auth-service | grep -E "introspect|user_id"
```

### 步骤 4：手动测试 Token 验证

使用 curl 测试 token 验证：

```bash
# 1. 获取 Agent token（通过 device/login）
curl -X POST http://localhost:8000/api/v1/auth/device/login \
  -H "Content-Type: application/json" \
  -d '{
    "mg_id": "test-mg-id",
    "host_ip": "192.168.1.100",
    "username": "test-agent"
  }'

# 2. 使用 token 验证（通过 Gateway）
curl -X POST http://localhost:8000/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"token": "<token>"}'

# 3. 调用 Agent API（通过 Gateway）
curl -X GET http://localhost:8000/api/v1/host/agent/hardware/report \
  -H "Authorization: Bearer <token>"
```

## 常见问题

### Q1: Token 未过期，但返回 401

**A**: 可能的原因：
1. Token 被加入黑名单（logout 或 refresh token 后）
2. Gateway 无法连接到 Auth Service
3. Auth Service 的 `introspect` 端点返回错误

**排查方法**：
- 检查 Redis 中是否存在 token 黑名单：`token_blacklist:<token>`
- 检查 Gateway 和 Auth Service 之间的网络连接
- 查看 Auth Service 日志，确认 `introspect` 端点是否正常工作

### Q2: Gateway 日志显示 token 验证成功，但 Host Service 返回 401

**A**: 可能的原因：
1. Gateway 没有正确设置 `X-User-Info` header
2. Host Service 的 IP 验证失败
3. `X-User-Info` header 中的 `user_id` 字段缺失

**排查方法**：
- 检查 Gateway 的 `proxy.py` 是否正确设置 `X-User-Info` header
- 检查 Host Service 的 `GATEWAY_IP_ADDRESSES` 配置
- 检查 Gateway 的 `request.state.user` 是否包含 `user_id` 字段

### Q3: Device token 的 user_id 为空

**A**: 可能的原因：
1. Device token 的 payload 中 `sub` 字段为空
2. Auth Service 的 `introspect_token` 方法没有正确提取 `user_id`

**排查方法**：
- 检查 Device token 的 payload（使用 jwt.io 解码）
- 检查 Auth Service 的 `introspect_token` 方法是否正确提取 `user_id`
- 检查 Device login 时是否正确设置 `sub` 字段（应为 `host_rec.id`）

## 代码修复建议

### 1. 增强日志输出

在 `get_current_agent` 函数中添加更详细的日志：

```python
# 在检查 X-User-Info header 之前
logger.debug(
    "检查 X-User-Info header",
    extra={
        "path": request.url.path,
        "has_x_user_info": bool(user_info_header),
        "x_user_info_length": len(user_info_header) if user_info_header else 0,
        "client_host": request.client.host if request.client else "unknown",
    },
)
```

### 2. 增强错误信息

在返回 401 错误时，提供更详细的错误信息：

```python
raise HTTPException(
    status_code=HTTP_401_UNAUTHORIZED,
    detail=ErrorResponse(
        code=HTTP_401_UNAUTHORIZED,
        message="缺少用户认证信息",
        message_key="error.auth.missing_user_info",
        error_code="UNAUTHORIZED",
        locale=locale,
        details={
            "hint": "请求必须通过 Gateway 转发，Gateway 会在认证后传递用户信息",
            "has_x_user_info": bool(user_info_header),
            "client_host": request.client.host if request.client else "unknown",
        },
    ).model_dump(),
)
```

## 相关文件

- `services/host-service/app/api/v1/dependencies.py` - `get_current_agent` 函数
- `services/gateway-service/app/middleware/auth_middleware.py` - Gateway 认证中间件
- `services/gateway-service/app/api/v1/endpoints/proxy.py` - Gateway 代理端点
- `services/auth-service/app/services/auth_service.py` - Auth Service 认证服务

