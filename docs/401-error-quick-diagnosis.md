# 401 错误快速诊断指南

## 📋 根据错误响应快速诊断

从你的错误响应来看：
```json
{
  "code": 401,
  "message": "无效或过期的认证令牌",
  "error_code": "TOKEN_INVALID_OR_EXPIRED",
  "details": {
    "hint": "令牌可能已过期或无效，请重新登录获取新令牌"
  }
}
```

## 🔍 立即检查步骤

### 步骤 1：查看 Gateway 日志（最重要）

查看 Gateway 服务日志，查找以下关键信息：

```bash
# 查看最近的 token 验证日志
docker-compose logs gateway-service --tail=100 | grep -A 10 "token\|401\|验证"

# 查找特定请求的日志（使用 request_id）
docker-compose logs gateway-service | grep "req_1748755218"
```

**关键日志字段**：
- `reason`: 错误原因（`token_inactive`, `missing_user_id`, `auth_service_error`, `http_error`, `timeout`, `connection_error`）
- `token_preview`: Token 预览（前8个字符）
- `auth_service_url`: Auth Service 地址
- `auth_service_response`: Auth Service 返回的完整响应

### 步骤 2：查看 Auth Service 日志

查看 Auth Service 的 introspect 端点日志：

```bash
# 查看 Auth Service 日志
docker-compose logs auth-service --tail=100 | grep -A 10 "introspect\|验证令牌"
```

**关键日志**：
- `验证令牌` - 开始验证
- `令牌验证成功` - 验证成功
- `令牌验证失败` - 验证失败
- `Redis 黑名单检查失败` - Redis 连接问题

### 步骤 3：检查 Token 本身

1. **解码 token**（查看内容）：
```python
import jwt
token = "你的token"
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded)
```

2. **检查关键字段**：
   - `sub`: 用户ID（必需，不能为空）
   - `exp`: 过期时间（检查是否已过期）
   - `type`: token 类型（应该是 `access`）
   - `iat`: 签发时间

3. **检查是否过期**：
```python
from datetime import datetime
exp = decoded.get("exp")
if exp:
    exp_time = datetime.fromtimestamp(exp)
    now = datetime.now()
    print(f"过期时间: {exp_time}")
    print(f"当前时间: {now}")
    print(f"是否过期: {exp_time < now}")
```

### 步骤 4：测试 Auth Service 端点

直接调用 Auth Service 的 introspect 端点：

```bash
curl -X POST http://auth-service:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "你的token"}'
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

## 🐛 常见原因及解决方案

### 原因 1：Token 已过期

**检查方法**：
- 查看 token 的 `exp` 字段
- 检查系统时间是否同步

**解决方案**：
- 重新登录获取新 token
- 检查系统时间同步

### 原因 2：Token 被加入黑名单

**检查方法**：
```bash
# 连接 Redis
docker-compose exec redis redis-cli

# 检查黑名单
GET token_blacklist:<你的token>
```

**解决方案**：
- 如果返回 `1` 或 `true`，说明 token 已被加入黑名单（用户注销）
- 重新登录获取新 token

### 原因 3：user_id 为空（我们刚修复的问题）

**检查方法**：
- 查看 Gateway 日志中的 `reason: missing_user_id`
- 查看 Auth Service 日志，确认返回的 `user_id` 值

**解决方案**：
- 检查 token payload 中的 `sub` 字段是否存在
- 如果 `sub` 字段缺失，需要重新生成 token

### 原因 4：Auth Service 不可用

**检查方法**：
- 查看 Gateway 日志中的 `reason: timeout` 或 `connection_error`
- 检查 Auth Service 健康状态：`curl http://auth-service:8001/health`

**解决方案**：
- 检查 Auth Service 是否正常运行
- 检查网络连接
- 检查服务发现配置

### 原因 5：Redis 连接问题

**检查方法**：
- 查看 Auth Service 日志中的 `Redis 黑名单检查失败`
- 检查 Redis 连接：`docker-compose exec redis redis-cli ping`

**解决方案**：
- 检查 Redis 服务是否正常运行
- 检查 Redis 连接配置
- 注意：Redis 不可用时，Auth Service 会降级处理（跳过黑名单检查），但 token 本身必须有效

## 📊 诊断流程图

```
401 错误
  │
  ├─→ 查看 Gateway 日志中的 reason 字段
  │
  ├─→ reason: token_inactive
  │   ├─→ 检查 token 是否过期（exp 字段）
  │   ├─→ 检查 token 是否在黑名单中
  │   └─→ 检查 token 格式是否正确
  │
  ├─→ reason: missing_user_id
  │   ├─→ 检查 token payload 中的 sub 字段
  │   └─→ 检查 Auth Service 返回的 user_id
  │
  ├─→ reason: auth_service_error
  │   ├─→ 检查 Auth Service 日志
  │   └─→ 检查 Auth Service 健康状态
  │
  ├─→ reason: http_error
  │   ├─→ 检查 Auth Service 是否正常运行
  │   └─→ 检查网络连接
  │
  ├─→ reason: timeout
  │   ├─→ 检查 Auth Service 性能
  │   └─→ 检查网络延迟
  │
  └─→ reason: connection_error
      ├─→ 检查 Auth Service 是否运行
      └─→ 检查服务发现配置
```

## 🎯 快速诊断命令

```bash
# 1. 查看 Gateway 最近的 token 验证日志（包含 reason 字段）
docker-compose logs gateway-service --tail=200 | grep -E "token|验证|401|reason" | tail -50

# 2. 查看 Auth Service 最近的 introspect 日志
docker-compose logs auth-service --tail=200 | grep -E "introspect|验证令牌|黑名单" | tail -50

# 3. 检查 Auth Service 健康状态
curl -s http://auth-service:8001/health | jq

# 4. 检查 Redis 连接
docker-compose exec redis redis-cli ping

# 5. 测试 token 验证（替换 YOUR_TOKEN）
curl -X POST http://auth-service:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN"}' | jq

# 6. 检查 Gateway 到 Auth Service 的连接
docker-compose exec gateway-service ping -c 3 auth-service
```

## 📝 日志示例

### 成功验证的日志

```
开始验证令牌 | path=/api/v1/host/host/list | method=GET | token_preview=eyJhbGc...
调用 Auth Service 验证令牌 | introspect_url=http://auth-service:8001/api/v1/auth/introspect
令牌验证成功 - Auth Service 返回有效用户信息 | user_id=123 | username=admin
令牌验证成功，允许访问 | path=/api/v1/host/host/list | user_id=123
```

### 验证失败的日志（token_inactive）

```
开始验证令牌 | path=/api/v1/host/host/list | method=GET | token_preview=eyJhbGc...
调用 Auth Service 验证令牌 | introspect_url=http://auth-service:8001/api/v1/auth/introspect
令牌验证失败 - 令牌未激活 | reason=token_inactive | active=false
令牌验证失败，拒绝访问 | path=/api/v1/host/host/list
```

### 验证失败的日志（missing_user_id）

```
开始验证令牌 | path=/api/v1/host/host/list | method=GET | token_preview=eyJhbGc...
调用 Auth Service 验证令牌 | introspect_url=http://auth-service:8001/api/v1/auth/introspect
Token 验证成功但 user_id 为空 | reason=missing_user_id | data_keys=['active', 'username', 'exp']
令牌验证失败，拒绝访问 | path=/api/v1/host/host/list
```

## 🔗 相关文档

- [401 错误排查指南](./troubleshooting-401-error.md) - 详细的排查步骤
- [Token 认证 401 错误问题分析报告](./auth-token-401-issues-analysis.md) - 问题分析和修复方案

