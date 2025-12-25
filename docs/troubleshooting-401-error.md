# 401 错误排查指南

## 📋 问题描述

通过 Gateway 访问 API 时返回 401 错误：
- **错误码**: `TOKEN_INVALID_OR_EXPIRED`
- **错误消息**: "无效或过期的认证令牌"
- **请求路径**: `/api/v1/host/host/list`

## 🔍 可能的原因

### 1. Token 验证失败（Auth Service 返回 active=false）

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
令牌验证失败 - 令牌未激活
reason: token_inactive
```

**可能原因**：
- Token 确实已过期
- Token 已被加入黑名单（用户注销）
- Token 格式错误或损坏
- Redis 黑名单检查失败（但继续验证时 token 本身无效）

**解决方案**：
1. 检查 token 是否过期：查看 token 的 `exp` 字段
2. 检查 token 是否在黑名单中：查看 Redis 中的 `token_blacklist:{token}` 键
3. 重新登录获取新 token

### 2. user_id 为空（我们刚修复的问题）

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
Token 验证成功但 user_id 为空
reason: missing_user_id
```

**可能原因**：
- Auth Service 返回的 `user_id` 字段为 `None` 或空字符串
- Token payload 中缺少 `sub` 字段

**解决方案**：
1. 检查 Auth Service 日志，确认 `introspect_token` 返回的 `user_id` 值
2. 检查 token payload，确认 `sub` 字段是否存在
3. 如果 `sub` 字段缺失，需要重新生成 token

### 3. Auth Service 返回错误码

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
令牌验证失败 - Auth Service 返回错误码
response_code: <code>
reason: auth_service_error
```

**可能原因**：
- Auth Service 内部错误
- Auth Service 无法处理请求

**解决方案**：
1. 检查 Auth Service 日志
2. 检查 Auth Service 健康状态：`GET /health`
3. 检查 Auth Service 是否正常运行

### 4. HTTP 状态码异常

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
令牌验证失败 - HTTP 状态码异常
status_code: <code>
reason: http_error
```

**可能原因**：
- Auth Service 返回非 200 状态码
- 网络连接问题

**解决方案**：
1. 检查 Auth Service 是否正常运行
2. 检查网络连接
3. 检查 Gateway 到 Auth Service 的连接配置

### 5. Auth Service 超时或连接错误

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
令牌验证超时 - Auth Service 响应超时
reason: timeout
```
或
```
无法连接到认证服务 - 网络连接失败
reason: connection_error
```

**可能原因**：
- Auth Service 响应慢
- Auth Service 不可用
- 网络连接问题

**解决方案**：
1. 检查 Auth Service 健康状态
2. 检查网络连接
3. 增加超时时间配置（如果需要）

### 6. Token 格式错误

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
无效的 Authorization 头格式
```

**可能原因**：
- Authorization 头格式不正确
- Token 被截断或损坏

**解决方案**：
1. 检查 Authorization 头格式：`Bearer <token>`
2. 确认 token 完整且未被截断

### 7. 缺少 Authorization 头

**检查方法**：
查看 Gateway 日志，查找以下日志：
```
受保护路径缺少 Authorization 头
```

**可能原因**：
- 请求未包含 Authorization 头
- Authorization 头为空

**解决方案**：
1. 确认请求包含 `Authorization: Bearer <token>` 头
2. 检查前端代码是否正确设置 Authorization 头

## 🔧 排查步骤

### 步骤 1：检查 Gateway 日志

查看 Gateway 服务的日志，查找与 token 验证相关的日志：

```bash
# 查看 Gateway 日志
docker-compose logs gateway-service | grep -i "token\|401\|unauthorized" | tail -50

# 或查看特定请求的日志
docker-compose logs gateway-service | grep "req_1748755218"
```

**关键日志**：
- `开始验证令牌` - 开始验证
- `令牌验证成功` - 验证成功
- `令牌验证失败` - 验证失败（需要查看具体原因）

### 步骤 2：检查 Auth Service 日志

查看 Auth Service 的日志，确认 token 验证结果：

```bash
# 查看 Auth Service 日志
docker-compose logs auth-service | grep -i "introspect\|token" | tail -50
```

**关键日志**：
- `验证令牌` - 开始验证
- `令牌验证成功` - 验证成功
- `令牌验证失败` - 验证失败（需要查看具体原因）

### 步骤 3：检查 Token 本身

1. **解码 token**（不验证签名）：
```python
import jwt
token = "your_token_here"
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded)
```

2. **检查 token 字段**：
   - `sub`: 用户ID（必需）
   - `exp`: 过期时间（必需）
   - `type`: token 类型（access/refresh）
   - `iat`: 签发时间

3. **检查 token 是否过期**：
```python
import jwt
from datetime import datetime

token = "your_token_here"
decoded = jwt.decode(token, options={"verify_signature": False})
exp = decoded.get("exp")
if exp:
    exp_time = datetime.fromtimestamp(exp)
    now = datetime.now()
    print(f"Token 过期时间: {exp_time}")
    print(f"当前时间: {now}")
    print(f"是否过期: {exp_time < now}")
```

### 步骤 4：检查 Redis 黑名单

检查 token 是否在黑名单中：

```bash
# 连接 Redis
docker-compose exec redis redis-cli

# 检查黑名单
GET token_blacklist:<your_token>
```

如果返回 `1` 或 `true`，说明 token 已被加入黑名单。

### 步骤 5：测试 Auth Service 端点

直接调用 Auth Service 的 introspect 端点：

```bash
curl -X POST http://auth-service:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "your_token_here"}'
```

**预期响应**：
```json
{
  "code": 200,
  "message": "验证成功",
  "data": {
    "active": true,
    "user_id": "123",
    "username": "admin",
    "user_type": "admin",
    "exp": 1234567890,
    "token_type": "access"
  }
}
```

**如果 `active` 为 `false`**，说明 token 无效。

## 🐛 常见问题及解决方案

### 问题 1：Token 未过期但返回 401

**可能原因**：
1. Token 已被加入黑名单（用户注销）
2. `user_id` 为空（我们刚修复的问题）
3. Redis 黑名单检查失败，但 token 本身无效

**解决方案**：
1. 检查 Redis 黑名单
2. 检查 Gateway 日志中的 `reason` 字段
3. 重新登录获取新 token

### 问题 2：Token 格式正确但返回 401

**可能原因**：
1. Token 签名验证失败（JWT secret 不匹配）
2. Token 类型错误（使用了 refresh token 作为 access token）
3. Auth Service 无法验证 token

**解决方案**：
1. 确认使用正确的 token 类型（access token）
2. 检查 JWT secret 配置是否一致
3. 检查 Auth Service 日志

### 问题 3：间歇性 401 错误

**可能原因**：
1. Auth Service 响应慢或超时
2. Redis 连接不稳定
3. 网络连接问题

**解决方案**：
1. 检查 Auth Service 性能
2. 检查 Redis 连接状态
3. 检查网络连接

## 📝 日志示例

### 成功验证的日志

```
开始验证令牌 | path=/api/v1/host/host/list | method=GET | token_preview=eyJhbGc...
调用 Auth Service 验证令牌 | introspect_url=http://auth-service:8001/api/v1/auth/introspect
令牌验证成功 - Auth Service 返回有效用户信息 | user_id=123 | username=admin
令牌验证成功，允许访问 | path=/api/v1/host/host/list | user_id=123
```

### 验证失败的日志

```
开始验证令牌 | path=/api/v1/host/host/list | method=GET | token_preview=eyJhbGc...
调用 Auth Service 验证令牌 | introspect_url=http://auth-service:8001/api/v1/auth/introspect
令牌验证失败 - 令牌未激活 | reason=token_inactive | active=false
令牌验证失败，拒绝访问 | path=/api/v1/host/host/list
```

## 🎯 快速诊断命令

```bash
# 1. 查看 Gateway 最近的 token 验证日志
docker-compose logs gateway-service --tail=100 | grep -A 5 "token\|401"

# 2. 查看 Auth Service 最近的 introspect 日志
docker-compose logs auth-service --tail=100 | grep -A 5 "introspect"

# 3. 检查 Auth Service 健康状态
curl http://auth-service:8001/health

# 4. 检查 Redis 连接
docker-compose exec redis redis-cli ping

# 5. 测试 token 验证（替换 YOUR_TOKEN）
curl -X POST http://auth-service:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN"}'
```

## 🔗 相关文档

- [Token 认证 401 错误问题分析报告](./auth-token-401-issues-analysis.md)
- [WebSocket Token 验证流程分析报告](./websocket-token-verification-analysis.md)
- [Agent 认证 401 错误排查指南](./troubleshooting-agent-401.md)

