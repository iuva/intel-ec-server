# WebSocket 403 Forbidden 认证失败修复报告

## 问题概述

WebSocket连接在网关验证token时失败，返回403 Forbidden错误：

```
2025-10-28 03:18:08.728 | ERROR | Token 字符串验证异常 (websocket_auth.py:249)
2025-10-28 03:18:08.729 | WARNING | WebSocket 连接 token 验证失败 (proxy.py:96)
INFO: connection rejected (403 Forbidden)
```

## 根本原因分析

### 问题链路
```
1. WebSocket客户端连接: /api/v1/ws/host/agent/{agent_id}?token=<token>
   ↓
2. 网关proxy.py调用: verify_token_string(token)
   ↓
3. verify_token_string发起HTTP请求: auth-service/api/v1/auth/introspect
   ↓
4. auth-service返回: {code: 200, data: {active: true/false, user_id: int}, ...}
   ↓
5. verify_token_string解析响应，提取user_id
   ↓
6. 如果user_id为None或无效，拒绝连接返回403
```

### 核心问题

在 `shared/common/websocket_auth.py` 的 `verify_token_string()` 函数中：

**原始代码（第218行）:**
```python
if data.get("active", False):
    user_id = data.get("user_id") or data.get("sub")
    logger.info("Token 字符串验证成功", extra={...})
    return user_id  # ❌ 如果user_id为None，直接返回None
```

**问题:**
- 没有检查 `user_id` 是否为 None
- 没有区分"token有效但user_id为None"和"token无效"的情况
- 缺乏详细的DEBUG日志，难以诊断问题

## 修复方案

### 修复内容

已在 `shared/common/websocket_auth.py` 中进行了以下改进：

1. **添加详细的DEBUG日志** (第205-221行)
   - 记录token验证的每个阶段
   - 便于问题诊断和性能监控

2. **改进user_id提取逻辑** (第227-243行)
   ```python
   if data.get("active", False):
       user_id = data.get("user_id") or data.get("sub")
       
       if user_id:  # ✅ 显式检查user_id
           logger.info("Token 字符串验证成功", ...)
           return str(user_id)  # 确保返回字符串类型
       else:
           logger.warning("Token有效但未获取到user_id", ...)
           return None  # 显式返回None并记录警告
   ```

3. **增强错误处理** (第246-251行)
   - 区分不同的失败场景
   - 提供更准确的错误上下文

### 修复的关键改进

| 改进项 | 原始代码 | 修复后 |
|------|--------|------|
| user_id检查 | 无 | 显式检查user_id是否为None |
| 返回类型 | Optional[str] | str (如果有效) 或 None |
| 日志详细度 | 最小 | DEBUG+INFO+WARNING三层日志 |
| 错误诊断 | 困难 | 易于定位问题 |

## 验证步骤

### 1. 查看DEBUG日志

启用DEBUG级别日志后，会看到：
```
DEBUG: 开始验证 Token 字符串
    token_preview: "eyJhbGciOiJIUz..."
    auth_service_url: "http://auth-service:8001"

DEBUG: Token 验证响应收到
    status_code: 200
    response_keys: ['code', 'message', 'data', 'timestamp']

DEBUG: Token 验证响应解析
    active: true
    user_id: 123
    username: "admin"
    data_keys: ['active', 'username', 'user_id', 'exp', 'token_type']

INFO: Token 字符串验证成功
    user_id: "123"
    username: "admin"
```

### 2. 测试WebSocket连接

```bash
# 1. 获取有效的token
TOKEN=$(curl -s -X POST "http://localhost:8001/api/v1/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","***REMOVED***word":"***REMOVED***"}' | jq -r '.data.access_token')

# 2. 测试WebSocket连接
wscat -c "ws://localhost:8000/api/v1/ws/host/agent/agent-123?token=${TOKEN}"

# 3. 检查网关日志
docker-compose logs gateway-service | grep -i "websocket\|token"
```

### 3. 监控关键指标

- ✅ Token验证响应时间（<100ms为正常）
- ✅ user_id提取成功率（应为100%）
- ✅ WebSocket连接成功率

## 可能仍需检查的问题

### A. IntrospectResponse模型验证

验证模型是否正确定义 (services/auth-service/app/schemas/auth.py):
```python
class IntrospectResponse(BaseModel):
    active: bool = Field(description="令牌是否有效")
    username: Optional[str] = Field(default=None, description="用户名")
    user_id: Optional[int] = Field(default=None, description="用户ID")  # ✅ 必须有
    exp: Optional[int] = Field(default=None, description="过期时间戳")
    token_type: Optional[str] = Field(default=None, description="令牌类型")
```

**状态: ✅ 已验证 - 模型正确包含user_id字段**

### B. JWT Token Payload检查

确保JWT中包含必需的字段 (auth_service.py中的generate_tokens方法):
```python
payload = {
    "sub": str(user.id),  # ✅ 用户ID
    "username": user.user_account,  # ✅ 用户名
    "type": "access",  # ✅ token类型
    "exp": access_token_exp_timestamp  # ✅ 过期时间
}
```

### C. 网络连接验证

```bash
# 检查网关是否能连接到auth-service
docker-compose exec gateway-service bash -c \
  'curl -X POST "http://auth-service:8001/api/v1/auth/introspect" \
   -H "Content-Type: application/json" \
   -d "{\"token\":\"test-token\"}"'
```

## 性能优化建议

### 1. 缓存token验证结果

```python
# 在verify_token_string中添加缓存
cache_key = f"ws_token_verify:{hash(token)}"
cached_result = await get_cache(cache_key)
if cached_result is not None:
    return cached_result

# 调用auth-service验证
result = ...  # 验证逻辑

# 缓存结果（5分钟过期）
await set_cache(cache_key, result, expire=300)
return result
```

### 2. 连接池优化

```python
# 使用连接池
async with httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
) as client:
    ...
```

### 3. 重试机制

```python
# 添加重试逻辑
max_retries = 3
for attempt in range(max_retries):
    try:
        response = await client.post(...)
        break
    except httpx.RequestError:
        if attempt == max_retries - 1:
            raise
        await asyncio.sleep(2 ** attempt)  # exponential backoff
```

## 文件修改清单

- ✅ `/shared/common/websocket_auth.py` - verify_token_string函数增强
  - 添加详细DEBUG日志
  - 改进user_id提取逻辑
  - 增强错误处理

## 测试清单

- [ ] WebSocket连接测试（成功场景）
- [ ] WebSocket连接测试（失败场景）
- [ ] 查看DEBUG日志输出
- [ ] 性能监控（响应时间）
- [ ] 并发连接测试
- [ ] 网络抖动场景测试

## 相关文档

- [WebSocket认证规范](shared/common/websocket_auth.py)
- [网关代理规范](services/gateway-service/app/api/v1/endpoints/proxy.py)
- [认证服务规范](services/auth-service/app/services/auth_service.py)

## 修复状态

**修复日期**: 2025-10-28  
**修复版本**: v1.0  
**测试状态**: 待测试  
**发布状态**: 待部署

