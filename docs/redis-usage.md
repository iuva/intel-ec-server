# Redis 使用文档

## 概述

本文档详细描述了项目中所有使用 Redis 的地方，包括缓存键、业务逻辑、过期时间等信息。

**Redis 管理器**: `shared/common/cache.py` 中的 `RedisManager` 类

**全局实例**: `redis_manager`（单例模式）

---

## 1. 外部 API Token 缓存

### 基本信息

- **文件位置**: `services/host-service/app/services/external_api_client.py`
- **缓存键格式**: `external_api_token:{user_email}`
- **过期时间**: 根据外部 API 返回的 `expires_in` 字段（默认 15552000 秒，约 180 天）
- **数据类型**: JSON 对象

### 业务逻辑

1. **获取 Token 流程**:
   - 根据 `user_id` 查询 `sys_user` 表获取用户邮箱
   - 先从 Redis 缓存获取 token（缓存键：`external_api_token:{user_email}`）
   - 如果缓存为空，使用锁防止并发请求，调用外部登录接口获取 token
   - 根据 `expires_in` 的值将 token 存入 Redis 缓存
   - 返回完整的 token 信息

2. **缓存数据结构**:

   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in": "15552000"
   }
   ```

3. **并发控制**:
   - 使用 `asyncio.Lock()` 防止多个协程同时请求 token
   - 双重检查机制：获取锁后再次检查缓存

### 使用接口

```python
# 获取 Token（自动处理缓存）
token_info = await get_external_api_token(user_id, locale="zh_CN")

# 内部实现
cache_key = f"external_api_token:{user_email}"
cached_token = await redis_manager.get(cache_key)  # 获取缓存
await redis_manager.set(cache_key, token_data, expire=expire_seconds)  # 设置缓存
```

### 过期时间说明

- **默认过期时间**: 15552000 秒（约 180 天）
- **实际过期时间**: 根据外部 API 返回的 `expires_in` 字段动态设置
- **过期处理**: Token 过期后自动重新获取

### 相关代码

- **函数**: `get_external_api_token(user_id: int, locale: str = "zh_CN")`
- **缓存键前缀**: `TOKEN_CACHE_KEY_PREFIX = "external_api_token"`
- **缓存键生成**: `f"{TOKEN_CACHE_KEY_PREFIX}:{user_email}"`

---

## 2. Refresh Token 黑名单

### 基本信息

- **文件位置**: `services/auth-service/app/services/auth_service.py`
- **缓存键格式**: `refresh_token_blacklist:{refresh_token}`
- **过期时间**: refresh_token 的剩余有效期（TTL，动态计算）
- **数据类型**: 布尔值（`True`）

### 业务逻辑

1. **黑名单机制**:
   - 当用户使用 refresh_token 刷新 access_token 时，将旧的 refresh_token 加入黑名单
   - 防止 refresh_token 被重复使用（防止重放攻击）
   - 过期时间设置为 refresh_token 的剩余有效期

2. **使用场景**:
   - `refresh_access_token()`: 刷新访问令牌时
   - `auto_refresh_tokens()`: 自动刷新令牌时

3. **安全检查**:
   - 每次刷新前检查 refresh_token 是否在黑名单中
   - 如果 Redis 连接失败，为了安全起见拒绝刷新

### 使用接口

```python
# 检查黑名单
blacklist_key = f"refresh_token_blacklist:{refresh_token}"
is_blacklisted = await get_cache(blacklist_key)

# 添加到黑名单
exp = payload.get("exp", 0)
ttl = max(1, int(exp - time.time()))  # 确保 TTL 至少为 1 秒
await set_cache(blacklist_key, True, expire=ttl)
```

### 过期时间说明

- **计算方式**: `ttl = max(1, int(exp - time.time()))`
  - `exp`: refresh_token 的过期时间戳（从 JWT payload 中提取）
  - `time.time()`: 当前时间戳
  - `max(1, ...)`: 确保 TTL 至少为 1 秒
- **过期处理**: Token 过期后自动从 Redis 中删除

### 相关代码

- **函数**:
  - `refresh_access_token(refresh_data: RefreshTokenRequest)`
  - `auto_refresh_tokens(refresh_data: AutoRefreshTokenRequest)`
- **缓存键格式**: `refresh_token_blacklist:{refresh_token}`

---

## 3. Access Token 黑名单

### 基本信息

- **文件位置**: `services/auth-service/app/services/auth_service.py`
- **缓存键格式**: `token_blacklist:{token}`
- **过期时间**: token 的剩余有效期（TTL，动态计算）
- **数据类型**: 布尔值（`True`）

### 业务逻辑

1. **黑名单机制**:
   - 用户注销时，将 access_token 加入黑名单
   - 防止已注销的 token 继续使用
   - 过期时间设置为 token 的剩余有效期

2. **使用场景**:
   - `logout(token: str)`: 用户注销时

3. **验证流程**:
   - 在令牌验证时检查 token 是否在黑名单中
   - 如果 token 在黑名单中，拒绝访问

### 使用接口

```python
# 添加到黑名单
blacklist_key = f"token_blacklist:{token}"
exp = payload.get("exp", 0)
ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))
await set_cache(blacklist_key, True, expire=ttl)
```

### 过期时间说明

- **计算方式**: `ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))`
  - `exp`: access_token 的过期时间戳（从 JWT payload 中提取）
  - `datetime.now(timezone.utc).timestamp()`: 当前 UTC 时间戳
  - `max(0, ...)`: 确保 TTL 不为负数
- **过期处理**: Token 过期后自动从 Redis 中删除

### 相关代码

- **函数**: `logout(token: str)`
- **缓存键格式**: `token_blacklist:{token}`

---

## 4. Case 超时配置缓存

### 基本信息

- **文件位置**: `services/host-service/app/services/case_timeout_task.py`
- **缓存键格式**: `sys_conf:case_timeout`
- **过期时间**: 1 小时（3600 秒）
- **数据类型**: 整数（超时时间，单位：分钟）

### 业务逻辑

1. **配置获取流程**:
   - 先从 Redis 缓存获取配置
   - 如果缓存为空，从 `sys_conf` 表查询 `case_timeout` 配置
   - 将配置值存入 Redis 缓存（1 小时过期）

2. **使用场景**:
   - Case 超时检测定时任务
   - 每 10 分钟执行一次超时检测
   - 需要获取 `case_timeout` 配置值（单位：分钟）

3. **缓存策略**:
   - 缓存 1 小时，减少数据库查询
   - 配置变更后最多 1 小时内生效

### 使用接口

```python
# 获取配置（带缓存）
CACHE_KEY_CASE_TIMEOUT = "sys_conf:case_timeout"
CACHE_EXPIRE_CASE_TIMEOUT = 3600  # 1 小时

cached_value = await redis_manager.get(CACHE_KEY_CASE_TIMEOUT)
if cached_value is None:
    # 从数据库查询
    timeout_minutes = await query_from_database()
    # 存入缓存
    await redis_manager.set(
        CACHE_KEY_CASE_TIMEOUT,
        timeout_minutes,
        expire=CACHE_EXPIRE_CASE_TIMEOUT
    )
```

### 过期时间说明

- **固定过期时间**: 3600 秒（1 小时）
- **过期处理**: 缓存过期后自动从数据库重新获取

### 相关代码

- **函数**: `_get_case_timeout_config()`
- **常量**:
  - `CACHE_KEY_CASE_TIMEOUT = "sys_conf:case_timeout"`
  - `CACHE_EXPIRE_CASE_TIMEOUT = 3600`

---

## 5. WebSocket 跨实例通信（Redis Pub/Sub）

### 基本信息

- **文件位置**: `services/host-service/app/services/agent_websocket_manager.py`
- **广播频道**: `websocket:broadcast`
- **单播频道模式**: `websocket:unicast:{host_id}`
- **过期时间**: 无（Pub/Sub 消息不持久化）

### 业务逻辑

1. **跨实例广播**:
   - 当需要向所有连接的 Host 广播消息时，先发送给本地连接
   - 然后通过 Redis Pub/Sub 发布到 `websocket:broadcast` 频道
   - 其他实例订阅该频道，收到消息后广播给本地连接

2. **跨实例单播**:
   - 当需要向指定 Host 发送消息但当前实例没有连接时
   - 通过 Redis Pub/Sub 发布到 `websocket:unicast:{host_id}` 频道
   - 其他实例订阅该频道模式，收到消息后检查本地是否有连接并发送

3. **实例标识**:
   - 每个实例有唯一的 `instance_id`（通过环境变量 `SERVICE_INSTANCE_ID` 配置）
   - 发布消息时包含 `instance_id`，避免自己重复处理

### 使用接口

#### 广播消息

```python
# 发布广播消息
pubsub_message = {
    "instance_id": self.instance_id,
    "message": message,
    "exclude": exclude,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
await redis_manager.client.publish(
    "websocket:broadcast",
    json.dumps(pubsub_message, ensure_ascii=False)
)

# 订阅广播频道
pubsub = redis_manager.client.pubsub()
await pubsub.subscribe("websocket:broadcast")
```

#### 单播消息

```python
# 发布单播消息
unicast_message = {
    "instance_id": self.instance_id,
    "target_host_id": host_id,
    "message": message,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
unicast_channel = f"websocket:unicast:{host_id}"
await redis_manager.client.publish(
    unicast_channel,
    json.dumps(unicast_message, ensure_ascii=False)
)

# 订阅单播频道模式
await pubsub.psubscribe("websocket:unicast:*")
```

### 消息格式

#### 广播消息格式

```json
{
  "instance_id": "host-service-instance-1",
  "message": {
    "type": "ota_config_update",
    "data": {...}
  },
  "exclude": "host_id_to_exclude",
  "timestamp": "2025-12-23T10:00:00.000Z"
}
```

#### 单播消息格式

```json
{
  "instance_id": "host-service-instance-1",
  "target_host_id": "2000000001",
  "message": {
    "type": "force_offline",
    "data": {...}
  },
  "timestamp": "2025-12-23T10:00:00.000Z"
}
```

### 过期时间说明

- **Pub/Sub 消息**: 不持久化，不设置过期时间
- **消息处理**: 消息发布后立即被订阅者接收，不会在 Redis 中存储

### 相关代码

- **类**: `AgentWebSocketManager`
- **方法**:
  - `_publish_broadcast_to_redis()`: 发布广播消息
  - `_send_to_host_cross_instance()`: 发布单播消息
  - `_redis_pubsub_listener()`: 订阅并处理消息
  - `_handle_redis_broadcast_message()`: 处理广播消息
  - `_handle_redis_unicast_message()`: 处理单播消息

### 环境变量配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| SERVICE_INSTANCE_ID | string | `{uuid}` | 服务实例唯一标识符 |

---

## 缓存键命名规范

### 命名规则

所有缓存键遵循以下命名规范：

1. **使用冒号分隔**: `prefix:identifier:sub_identifier`
2. **使用小写字母和下划线**: `external_api_token`, `refresh_token_blacklist`
3. **明确的前缀**: 每个缓存键都有明确的前缀，便于识别和管理

### 缓存键列表

| 缓存键格式 | 前缀 | 说明 | 服务 |
|-----------|------|------|------|
| `external_api_token:{user_email}` | `external_api_token` | 外部 API Token 缓存 | host-service |
| `refresh_token_blacklist:{refresh_token}` | `refresh_token_blacklist` | Refresh Token 黑名单 | auth-service |
| `token_blacklist:{token}` | `token_blacklist` | Access Token 黑名单 | auth-service |
| `sys_conf:case_timeout` | `sys_conf` | Case 超时配置缓存 | host-service |
| `websocket:broadcast` | `websocket` | WebSocket 广播频道（Pub/Sub） | host-service |
| `websocket:unicast:{host_id}` | `websocket:unicast` | WebSocket 单播频道（Pub/Sub） | host-service |
| `hardware_create_lock:{host_id}` | `hardware_create_lock` | 硬件创建分布式锁 | host-service |

---

## 过期时间汇总表

| 缓存类型 | 缓存键格式 | 过期时间 | 说明 |
|---------|-----------|---------|------|
| 外部 API Token | `external_api_token:{user_email}` | 动态（默认 15552000 秒，约 180 天） | 根据外部 API 返回的 `expires_in` 字段 |
| Refresh Token 黑名单 | `refresh_token_blacklist:{refresh_token}` | 动态（refresh_token 的剩余有效期） | TTL = `max(1, exp - time.time())` |
| Access Token 黑名单 | `token_blacklist:{token}` | 动态（token 的剩余有效期） | TTL = `max(0, exp - timestamp)` |
| Case 超时配置 | `sys_conf:case_timeout` | 固定 3600 秒（1 小时） | 系统配置缓存 |
| WebSocket 广播频道 | `websocket:broadcast` | 无（Pub/Sub 消息） | 不持久化 |
| WebSocket 单播频道 | `websocket:unicast:{host_id}` | 无（Pub/Sub 消息） | 不持久化 |
| 硬件创建锁 | `hardware_create_lock:{host_id}` | 固定 30 秒 | 分布式锁，防止并发创建 |

---

## 业务逻辑详细说明

### 1. 外部 API Token 缓存

#### 完整流程

```
1. 用户调用外部硬件接口
   ↓
2. 检查 Redis 缓存（键：external_api_token:{user_email}）
   ├─ 缓存命中 → 直接返回 token
   └─ 缓存未命中 → 继续步骤 3
   ↓
3. 获取锁（防止并发请求）
   ↓
4. 双重检查缓存（可能其他协程已获取）
   ├─ 缓存命中 → 返回 token
   └─ 缓存未命中 → 继续步骤 5
   ↓
5. 调用外部登录接口获取 token
   ↓
6. 解析响应，提取 expires_in
   ↓
7. 存入 Redis 缓存（过期时间 = expires_in）
   ↓
8. 返回 token
```

#### 并发控制

- 使用 `asyncio.Lock()` 确保同一时间只有一个协程请求 token
- 双重检查机制避免重复请求

### 2. Refresh Token 黑名单

#### 完整流程

```
1. 用户使用 refresh_token 刷新 access_token
   ↓
2. 验证 refresh_token 有效性
   ↓
3. 检查 refresh_token 是否在黑名单中
   ├─ 在黑名单 → 拒绝刷新，抛出异常
   └─ 不在黑名单 → 继续步骤 4
   ↓
4. 生成新的 access_token 和 refresh_token
   ↓
5. 将旧的 refresh_token 加入黑名单
   ├─ 计算 TTL = max(1, exp - time.time())
   └─ 设置缓存：refresh_token_blacklist:{old_refresh_token} = True
   ↓
6. 返回新的 token
```

#### 安全机制

- Redis 连接失败时拒绝刷新（安全优先）
- TTL 设置为 refresh_token 的剩余有效期，确保过期后自动清理

### 3. Access Token 黑名单

#### 完整流程

```
1. 用户调用注销接口
   ↓
2. 验证 token 有效性
   ↓
3. 解析 token，提取 exp（过期时间）
   ↓
4. 计算 TTL = max(0, exp - current_timestamp)
   ↓
5. 将 token 加入黑名单
   └─ 设置缓存：token_blacklist:{token} = True
   ↓
6. 删除数据库中的会话记录
   ↓
7. 返回成功
```

### 4. Case 超时配置缓存

#### 完整流程

```
1. 定时任务需要获取 case_timeout 配置
   ↓
2. 检查 Redis 缓存（键：sys_conf:case_timeout）
   ├─ 缓存命中 → 直接返回配置值
   └─ 缓存未命中 → 继续步骤 3
   ↓
3. 从 sys_conf 表查询配置
   ├─ 查询成功 → 继续步骤 4
   └─ 查询失败 → 返回 None
   ↓
4. 存入 Redis 缓存（过期时间 = 3600 秒）
   ↓
5. 返回配置值
```

### 5. WebSocket 跨实例通信

#### 广播流程

```
1. 需要向所有 Host 广播消息
   ↓
2. 先广播给本地连接的 Hosts
   ↓
3. 构建 Pub/Sub 消息（包含 instance_id）
   ↓
4. 发布到 Redis 频道：websocket:broadcast
   ↓
5. 其他实例订阅者收到消息
   ↓
6. 检查 instance_id，跳过自己发布的消息
   ↓
7. 广播给本地连接的 Hosts
```

#### 单播流程

```
1. 需要向指定 Host 发送消息
   ↓
2. 检查本地是否有该 Host 的连接
   ├─ 有连接 → 直接发送
   └─ 无连接 → 继续步骤 3
   ↓
3. 构建 Pub/Sub 消息（包含 instance_id 和 target_host_id）
   ↓
4. 发布到 Redis 频道：websocket:unicast:{host_id}
   ↓
5. 其他实例订阅者收到消息（模式匹配）
   ↓
6. 检查 instance_id，跳过自己发布的消息
   ↓
7. 检查本地是否有 target_host_id 的连接
   ├─ 有连接 → 发送消息
   └─ 无连接 → 忽略（可能所有实例都没有连接）
```

### 6. 硬件创建分布式锁

#### 完整流程

```
1. 需要为某个主机创建新的硬件记录
   ↓
2. 生成锁的键：hardware_create_lock:{host_id}
   ↓
3. 尝试获取 Redis 分布式锁
   ├─ Redis 不可用 → 记录警告，继续执行（降级处理）
   ├─ 获取锁失败 → 抛出异常（409 Conflict）
   └─ 获取锁成功 → 继续步骤 4
   ↓
4. 调用外部硬件接口创建硬件
   ↓
5. 从响应中提取 hardware_id
   ↓
6. 释放锁（使用 Lua 脚本确保原子性）
   ↓
7. 返回 hardware_id
```

#### 并发控制

- 使用 Redis `SET NX EX` 命令确保同一时间只有一个实例能创建硬件
- 锁的值为 UUID，用于验证锁的持有者
- 使用 Lua 脚本释放锁，确保只有锁的持有者才能释放

#### 降级处理

- **Redis 不可用**: 记录警告但继续执行，避免单点故障
- **获取锁失败**: 抛出 409 Conflict 错误，提示用户稍后重试

---

### 6. 硬件创建分布式锁

#### 完整流程

```
1. 需要为某个主机创建新的硬件记录
   ↓
2. 生成锁的键：hardware_create_lock:{host_id}
   ↓
3. 尝试获取 Redis 分布式锁
   ├─ Redis 不可用 → 记录警告，继续执行（降级处理）
   ├─ 获取锁失败 → 抛出异常（409 Conflict）
   └─ 获取锁成功 → 继续步骤 4
   ↓
4. 调用外部硬件接口创建硬件
   ↓
5. 从响应中提取 hardware_id
   ↓
6. 释放锁（使用 Lua 脚本确保原子性）
   ↓
7. 返回 hardware_id
```

#### 并发控制

- 使用 Redis `SET NX EX` 命令确保同一时间只有一个实例能创建硬件
- 锁的值为 UUID，用于验证锁的持有者
- 使用 Lua 脚本释放锁，确保只有锁的持有者才能释放

#### 降级处理

- **Redis 不可用**: 记录警告但继续执行，避免单点故障
- **获取锁失败**: 抛出 409 Conflict 错误，提示用户稍后重试

---
