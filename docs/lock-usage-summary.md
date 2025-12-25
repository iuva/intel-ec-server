# 锁使用情况汇总

## 概述

本文档汇总了项目中所有使用锁的接口和场景，包括 Redis 分布式锁和 asyncio 本地锁。

**更新日期**: 2025-01-30

---

## 锁类型分类

### 1. Redis 分布式锁

用于多实例部署场景，防止并发操作导致数据不一致。

### 2. asyncio 本地锁

用于单实例内的并发控制，防止同一进程内的并发问题。

---

## Redis 分布式锁使用场景

### 1. 硬件审批同意接口（新增硬件时）

**接口路径**: `POST /api/v1/host/admin/appr-host/approve`

**服务**: `host-service`

**文件位置**: 
- 接口端点: `services/host-service/app/api/v1/endpoints/admin_appr_host.py`
- 业务逻辑: `services/host-service/app/services/admin_appr_host_service.py`

**锁的键名**: `hardware_create_lock:{host_id}`

**锁的超时时间**: 30 秒

**使用场景**:
- 当 `hardware_id` 为空（新增硬件）时使用
- 防止多实例部署或接口抖动导致的并发创建脏数据
- 确保同一主机不会并发创建多个 hardware 记录

**锁处理逻辑**:
```python
# 生成锁的键：基于 host_id
lock_key = f"hardware_create_lock:{host_id}"
lock_value = str(uuid.uuid4())

# 尝试获取锁（超时时间 30 秒）
lock_acquired = await redis_manager.acquire_lock(lock_key, timeout=30, lock_value=lock_value)

if not lock_acquired:
    if not redis_manager.is_connected:
        # Redis 不可用，记录警告但继续执行（降级处理）
        logger.warning("Redis 不可用，无法获取分布式锁，继续执行（降级处理）")
    else:
        # Redis 可用但获取锁失败，说明其他实例正在处理
        raise BusinessError("主机正在创建硬件记录，请稍后重试", http_status_code=409)

try:
    # 调用外部硬件接口（新增）
    hardware_id = await call_external_api(...)
finally:
    # 释放锁
    await redis_manager.release_lock(lock_key, lock_value)
```

**降级处理**:
- ✅ Redis 不可用时，记录警告但继续执行（降级处理）
- ⚠️ 可能导致并发问题，但不会导致服务崩溃

**相关接口调用链**:
```
POST /api/v1/host/admin/appr-host/approve
  → AdminApprHostService.approve_hosts()
    → _call_hardware_api() [新增硬件时]
      → redis_manager.acquire_lock() [获取锁]
      → call_external_api() [调用外部接口]
      → redis_manager.release_lock() [释放锁]
```

---

## asyncio 本地锁使用场景

### 1. 外部 API Token 获取（防止并发请求）

**服务**: `host-service`

**文件位置**: `services/host-service/app/services/external_api_client.py`

**锁变量**: `_token_lock = asyncio.Lock()`

**使用场景**:
- 防止多个协程同时请求外部 API token
- 使用双重检查机制，避免重复请求

**锁处理逻辑**:
```python
# Token 缓存锁（防止并发请求）
_token_lock = asyncio.Lock()

async def get_external_api_token(...):
    # 1. 先检查缓存
    cached_token = await redis_manager.get(cache_key)
    if cached_token:
        return cached_token
    
    # 2. 缓存为空，使用锁防止并发请求
    async with _token_lock:
        # 双重检查：在获取锁后再次检查缓存
        cached_token = await redis_manager.get(cache_key)
        if cached_token:
            return cached_token
        
        # 3. 调用外部 API 获取 token
        token = await call_external_api(...)
        
        # 4. 存入缓存
        await redis_manager.set(cache_key, token, expire=expires_in)
        return token
```

**影响范围**:
- 所有调用 `get_external_api_token()` 的地方
- 包括：硬件审批、查询可用主机列表等需要调用外部硬件接口的场景

---

### 2. WebSocket 连接断开（防止重复断开）

**服务**: `host-service`

**文件位置**: `services/host-service/app/services/agent_websocket_manager.py`

**锁变量**: `self._disconnect_locks: Dict[str, asyncio.Lock] = {}`

**使用场景**:
- 防止同一连接被多次并发断开
- 每个连接使用独立的锁

**锁处理逻辑**:
```python
# 断开连接的锁（防止并发断开同一个连接）
self._disconnect_locks: Dict[str, asyncio.Lock] = {}

async def disconnect_agent(agent_id: str):
    # 获取或创建断开锁（每个连接一个锁）
    if agent_id not in self._disconnect_locks:
        self._disconnect_locks[agent_id] = asyncio.Lock()
    
    async with self._disconnect_locks[agent_id]:
        # 双重检查：再次检查是否正在断开
        if agent_id in self._disconnecting:
            return  # 已在断开中，跳过
        
        # 执行断开逻辑
        ...
```

**影响范围**:
- WebSocket 连接断开操作
- Agent 下线、心跳超时等场景

---

### 3. Gateway WebSocket 连接数限制

**服务**: `gateway-service`

**文件位置**: `services/gateway-service/app/services/proxy_service.py`

**锁变量**: `self._websocket_connection_lock: Optional[asyncio.Lock] = None`

**使用场景**:
- 限制 WebSocket 连接数
- 防止连接数超过最大限制

**锁处理逻辑**:
```python
# WebSocket 连接数限制锁（延迟创建）
self._websocket_connection_lock: Optional[asyncio.Lock] = None

async def proxy_websocket(...):
    # 延迟创建锁（在异步上下文中）
    if self._websocket_connection_lock is None:
        self._websocket_connection_lock = asyncio.Lock()
    
    # 检查连接数限制
    async with self._websocket_connection_lock:
        current_connections = len(self.active_websocket_connections)
        if current_connections >= self.max_websocket_connections:
            raise HTTPException(503, "WebSocket 连接数已达上限")
        
        # 添加连接
        self.active_websocket_connections[connection_id] = ...
```

**影响范围**:
- Gateway 的 WebSocket 代理功能
- 所有通过 Gateway 的 WebSocket 连接

---

## 锁使用统计

| 锁类型 | 使用场景 | 接口/功能 | 服务 |
|--------|---------|----------|------|
| **Redis 分布式锁** | 硬件审批同意（新增硬件） | `POST /api/v1/host/admin/appr-host/approve` | host-service |
| **asyncio 本地锁** | 外部 API Token 获取 | `get_external_api_token()` | host-service |
| **asyncio 本地锁** | WebSocket 连接断开 | `disconnect_agent()` | host-service |
| **asyncio 本地锁** | WebSocket 连接数限制 | `proxy_websocket()` | gateway-service |

---

## 接口详细说明

### 1. POST /api/v1/host/admin/appr-host/approve

**功能**: 同意启用待审批主机

**使用锁**: Redis 分布式锁（仅新增硬件时）

**锁的键**: `hardware_create_lock:{host_id}`

**锁的超时**: 30 秒

**触发条件**:
- `diff_type = 1` 或 `2`（版本号变化或内容变化）
- `hardware_id` 为空（新增硬件场景）

**业务逻辑**:
1. 查询待审批的硬件记录
2. 判断是新增还是修改（通过 `host_rec.hardware_id` 是否为空）
3. **如果是新增**：
   - 获取 Redis 分布式锁 `hardware_create_lock:{host_id}`
   - 调用外部硬件接口 `POST /api/v1/hardware/`
   - 释放锁
4. **如果是修改**：
   - 直接调用外部硬件接口 `PUT /api/v1/hardware/{hardware_id}`
   - 不使用锁

**错误处理**:
- 获取锁失败（Redis 可用）：返回 409 Conflict，提示"主机正在创建硬件记录，请稍后重试"
- 获取锁失败（Redis 不可用）：记录警告但继续执行（降级处理）

---

## 锁的降级处理

### Redis 分布式锁降级

**场景**: Redis 不可用时

**处理方式**:
- ✅ 记录警告日志
- ✅ 继续执行业务逻辑（降级处理）
- ⚠️ 可能导致并发问题，但不会导致服务崩溃

**代码位置**:
```365:376:services/host-service/app/services/admin_appr_host_service.py
                lock_acquired = await redis_manager.acquire_lock(lock_key, timeout=30, lock_value=lock_value)

                if not lock_acquired:
                    # 如果 Redis 不可用，记录警告但继续执行（降级处理）
                    if not redis_manager.is_connected:
                        logger.warning(
                            "Redis 不可用，无法获取分布式锁，继续执行（降级处理）",
                            extra={
                                "host_id": host_id,
                                "lock_key": lock_key,
                            },
                        )
```

---

## 测试建议

### 测试场景 1: 并发审批同一主机

**操作步骤**:
1. 准备一个待审批的主机（`hardware_id` 为空）
2. 同时发起两个审批请求（不同实例或快速连续请求）
3. 观察日志和数据库结果

**预期结果**:
- ✅ 只有一个请求成功获取锁并创建 hardware
- ✅ 另一个请求返回 409 Conflict 或等待锁释放
- ✅ 数据库中只有一条 `sync_state=2` 的记录

### 测试场景 2: Redis 不可用时的降级

**操作步骤**:
1. 停止 Redis 服务
2. 发起审批请求（新增硬件场景）

**预期结果**:
- ✅ 服务不崩溃
- ✅ 记录警告日志："Redis 不可用，无法获取分布式锁，继续执行（降级处理）"
- ✅ 业务逻辑继续执行（可能产生并发问题，但不崩溃）

---

## 注意事项

### 1. 分布式锁的限制

- ⚠️ Redis 不可用时，分布式锁失效
- ⚠️ 可能导致并发问题，但不会导致服务崩溃
- ✅ 建议在文档中说明此限制

### 2. 本地锁的限制

- ✅ 只适用于单实例场景
- ⚠️ 多实例部署时，本地锁无法跨实例工作
- ✅ 外部 API Token 获取使用本地锁 + Redis 缓存，可以跨实例工作

### 3. 锁的超时时间

- Redis 分布式锁：30 秒（固定）
- 如果外部 API 调用超过 30 秒，锁会自动释放（可能导致并发问题）

---

## 改进建议

### 优先级 P1（建议实施）

1. **分布式锁超时时间优化**
   - 根据外部 API 的实际响应时间动态调整锁的超时时间
   - 或增加锁的续期机制

2. **分布式锁降级方案**
   - 考虑在 Redis 不可用时使用数据库锁（SELECT ... FOR UPDATE）
   - 或在文档中明确说明此限制

### 优先级 P2（可选优化）

3. **锁的监控和告警**
   - 添加锁获取失败的 Prometheus 指标
   - 添加锁持有时间的监控

---

## 总结

**使用锁的接口**:
1. ✅ `POST /api/v1/host/admin/appr-host/approve` - 硬件审批同意（新增硬件时使用 Redis 分布式锁）

**使用锁的内部功能**:
1. ✅ 外部 API Token 获取（使用 asyncio 本地锁）
2. ✅ WebSocket 连接断开（使用 asyncio 本地锁）
3. ✅ Gateway WebSocket 连接数限制（使用 asyncio 本地锁）

**锁的类型**:
- Redis 分布式锁：1 个场景（硬件审批新增）
- asyncio 本地锁：3 个场景（Token 获取、连接断开、连接数限制）

---

**最后更新**: 2025-01-30  
**分析人员**: AI Assistant

