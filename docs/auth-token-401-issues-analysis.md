# Token 认证 401 错误问题分析报告

## 📋 问题描述

用户报告：**token 未过期，却经常出现 401 错误**

## 🔍 问题分析

### 1. Redis 黑名单检查问题

**问题位置**：`services/auth-service/app/services/auth_service.py::introspect_token()`

**当前实现**：
```python
# 检查令牌黑名单缓存
blacklist_key = f"token_blacklist:{token}"
is_blacklisted = await get_cache(blacklist_key)
if is_blacklisted:
    return IntrospectResponse(active=False)
```

**潜在问题**：
1. **Redis 不可用时的行为**：
   - `get_cache()` 在 Redis 不可用时会返回 `None`
   - 当前代码：`if is_blacklisted:` 会正确处理 `None`（不会进入 if 分支）
   - ✅ **当前逻辑正确**：Redis 不可用时，`is_blacklisted = None`，不会误判为黑名单

2. **但是存在另一个问题**：
   - 如果 Redis 连接失败，`get_cache()` 会捕获异常并返回 `None`
   - 但如果在检查黑名单时 Redis 突然断开，可能导致异常被捕获但未正确处理

### 2. Gateway 验证 Token 流程

**问题位置**：`services/gateway-service/app/middleware/auth_middleware.py::_verify_token()`

**当前实现**：
```python
response = await client.post(
    introspect_url,
    json={"token": token},
    headers={"Content-Type": "application/json"},
)

if response.status_code == 200:
    result = response.json()
    if result.get("code") == 200:
        data = result.get("data", {})
        if data.get("active"):
            # 构造用户信息
            user_info = {
                "user_id": data.get("user_id"),
                "username": data.get("username"),
                "user_type": data.get("user_type"),
                "active": data.get("active"),
            }
            return user_info
```

**潜在问题**：
1. **user_id 可能为 None**：
   - 如果 `data.get("user_id")` 返回 `None`，`user_info["user_id"]` 会是 `None`
   - Host Service 的 `get_current_agent` 会检查 `user_id` 是否存在，如果为 `None` 会返回 401

2. **响应格式不一致**：
   - Auth Service 返回的 `user_id` 可能是字符串或整数
   - Gateway 直接使用，可能导致类型不匹配

### 3. Host Service Agent 认证问题

**问题位置**：`services/host-service/app/api/v1/dependencies.py::get_current_agent()`

**当前实现**：
```python
user_info_header = request.headers.get("X-User-Info")
if not user_info_header:
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, ...)

user_info = json.loads(user_info_header)
user_id = user_info.get("user_id")

if not user_id:
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, ...)
```

**潜在问题**：
1. **X-User-Info Header 缺失**：
   - Gateway 可能没有正确设置 `X-User-Info` header
   - 或者 Gateway 的 `request.state.user` 为 `None`

2. **user_id 字段缺失或为空**：
   - Gateway 传递的 `user_info` 中可能没有 `user_id` 字段
   - 或者 `user_id` 为 `None`、空字符串、0 等

3. **IP 验证过于严格**：
   - `GATEWAY_IP_ADDRESSES` 可能不包含实际的 Gateway IP
   - 导致请求被拒绝

### 4. Token 验证时序问题

**可能的问题**：
1. **Token 刚创建就被验证**：
   - Token 创建后立即验证，可能存在时序问题
   - JWT 的 `iat`（issued at）和 `exp`（expiration）时间可能不一致

2. **时钟不同步**：
   - 如果服务器时钟不同步，可能导致 token 验证失败
   - JWT 验证时会检查 `exp` 字段

3. **Token 格式问题**：
   - Token 可能被截断或损坏
   - 导致 JWT 解码失败

## 🐛 已发现的问题

### 问题 1：Redis 黑名单检查缺少异常处理

**位置**：`services/auth-service/app/services/auth_service.py::introspect_token()`

**问题**：
- 如果 `get_cache()` 抛出异常（而不是返回 `None`），会导致整个 `introspect_token` 方法失败
- 当前代码使用 `try-except` 包裹整个方法，但异常处理可能不够细致

**修复方案**：
```python
try:
    # 检查令牌黑名单缓存
    blacklist_key = f"token_blacklist:{token}"
    try:
        is_blacklisted = await get_cache(blacklist_key)
        if is_blacklisted:
            logger.debug("Token 在黑名单中", extra={"blacklist_key": blacklist_key[:50] + "..."})
            return IntrospectResponse(active=False)
    except Exception as redis_error:
        # Redis 连接失败时，记录警告但继续验证（降级处理）
        logger.warning(
            "Redis 黑名单检查失败，继续验证 token",
            extra={
                "error": str(redis_error),
                "error_type": type(redis_error).__name__,
            },
        )
        # 继续执行 token 验证，不因为 Redis 失败而拒绝所有请求
```

### 问题 2：Gateway 未验证 user_id 是否存在

**位置**：`services/gateway-service/app/middleware/auth_middleware.py::_verify_token()`

**问题**：
- Gateway 构造 `user_info` 时，如果 `data.get("user_id")` 为 `None`，仍然会设置 `user_info["user_id"] = None`
- 这会导致 Host Service 的 `get_current_agent` 检查失败

**修复方案**：
```python
if data.get("active"):
    user_id = data.get("user_id")
    if not user_id:
        logger.warning(
            "Token 验证成功但 user_id 为空",
            extra={
                "data_keys": list(data.keys()),
                "token_preview": token_preview,
            },
        )
        return None  # 返回 None 表示验证失败
    
    # 构造用户信息
    user_info = {
        "user_id": user_id,
        "username": data.get("username"),
        "user_type": data.get("user_type"),
        "active": data.get("active"),
    }
    return user_info
```

### 问题 3：Auth Service 返回的 user_id 可能为 None

**位置**：`services/auth-service/app/services/auth_service.py::introspect_token()`

**问题**：
- 如果 `sub` 字段为 `None`，`user_id` 也会是 `None`
- 这会导致 Gateway 和 Host Service 的验证失败

**修复方案**：
```python
# 提取 user_id（sub 字段）
sub = payload.get("sub")
if not sub:
    logger.warning(
        "Token payload 中缺少 sub 字段",
        extra={
            "payload_keys": list(payload.keys()),
            "token_type": payload.get("type"),
        },
    )
    return IntrospectResponse(active=False)

# ✅ 转换为字符串避免精度丢失
user_id = str(sub)
```

### 问题 4：Gateway 设置 X-User-Info 时未验证 user_id

**位置**：`services/gateway-service/app/api/v1/endpoints/proxy.py`

**问题**：
- Gateway 从 `request.state.user` 获取用户信息时，如果 `user_id` 为 `None`，仍然会设置 header
- 这会导致 Host Service 验证失败

**修复方案**：
```python
# ✅ 添加用户信息到请求头（从request.state.user获取）
user_info = getattr(request.state, "user", None)
if user_info:
    # ✅ 验证 user_id 是否存在
    if not user_info.get("user_id"):
        logger.warning(
            "用户信息中缺少 user_id，跳过设置 X-User-Info header",
            extra={
                "user_info_keys": list(user_info.keys()),
                "service_name": service_name,
                "subpath": subpath,
            },
        )
    else:
        # 将用户信息序列化为JSON并添加到请求头
        headers["X-User-Info"] = json.dumps(user_info, ensure_ascii=False)
        logger.debug(
            "添加用户信息到请求头",
            extra={
                "user_id": user_info.get("user_id"),
                "username": user_info.get("username"),
                "user_type": user_info.get("user_type"),
            },
        )
```

## 🔧 修复方案

### 修复 1：增强 Redis 黑名单检查的异常处理

### 修复 2：Gateway 验证 user_id 是否存在

### 修复 3：Auth Service 确保返回有效的 user_id

### 修复 4：Gateway 设置 X-User-Info 时验证 user_id

## 📝 测试建议

1. **测试 Redis 不可用场景**：
   - 停止 Redis 服务
   - 验证 token 应该仍然可以工作（降级处理）

2. **测试 user_id 为 None 的场景**：
   - 创建 token 时故意不设置 `sub` 字段
   - 验证应该返回 401

3. **测试 Gateway IP 验证**：
   - 从非 Gateway IP 访问 Host Service
   - 应该返回 401

4. **测试 X-User-Info Header 缺失**：
   - 模拟 Gateway 未设置 header 的情况
   - 应该返回 401

## 🎯 优先级

1. **高优先级**：修复 Gateway 和 Auth Service 的 user_id 验证
2. **中优先级**：增强 Redis 黑名单检查的异常处理
3. **低优先级**：优化日志记录，便于问题排查

