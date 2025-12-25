# Redis 宕机降级符合性分析报告

## 概述

本文档分析了当前服务是否符合测试文档中 **SIT-INF-02: Redis 宕机降级** 的要求。

**测试要求**:
1. **API**: 仍能返回 DB 中的数据 (降级成功)
2. **Log**: 记录 Redis 连接异常，系统未 Crash

**分析日期**: 2025-01-30

---

## 符合性评估结果

### ✅ **总体评估: 基本符合，但有改进空间**

当前服务在大部分场景下已实现 Redis 宕机降级，但在某些边缘场景可能需要增强。

---

## 详细分析

### 1. Redis 连接管理 ✅ **符合要求**

**文件**: `shared/common/cache.py`

**实现情况**:
- ✅ Redis 连接失败时，不会抛出异常导致服务崩溃
- ✅ 设置 `self.client = None` 和 `self._is_connected = False`
- ✅ 记录详细的错误日志和故障排查建议
- ✅ 记录警告日志："Redis 不可用，服务已降级到无缓存模式，将继续运行"

**代码位置**:
```468:493:shared/common/cache.py
        except Exception as e:
            # 记录连接失败错误
            logger.error(f"Redis 连接失败: {masked_url}")
            logger.error(f"错误详情: {type(e).__name__}: {e!s}")

            # 调用诊断函数获取详细的排查建议
            diagnosis = await diagnose_connection_error(...)

            # 记录所有排查建议
            logger.error("故障排查建议:")
            for i, suggestion in enumerate(diagnosis["suggestions"], 1):
                logger.error(f"  {i}. {suggestion}")

            # 降级到无缓存模式
            self.client = None
            self._is_connected = False
            logger.warning("Redis 不可用，服务已降级到无缓存模式，将继续运行")
```

**符合性**: ✅ **完全符合**

---

### 2. Redis 基础操作（get/set/delete）✅ **符合要求**

**文件**: `shared/common/cache.py`

**实现情况**:
- ✅ `get()`: 如果 `client` 为 None 或操作异常，返回 `None`，不抛出异常
- ✅ `set()`: 如果 `client` 为 None 或操作异常，返回 `False`，不抛出异常
- ✅ `delete()`: 如果 `client` 为 None 或操作异常，返回 `False`，不抛出异常
- ✅ 所有操作都有异常捕获和日志记录

**代码示例**:
```502:521:shared/common/cache.py
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e!s}")
            return None
```

**符合性**: ✅ **完全符合**

---

### 3. 业务逻辑中的 Redis 使用

#### 3.1 Token 黑名单检查 ✅ **符合要求**

**文件**: `services/auth-service/app/services/auth_service.py`

**实现情况**:
- ✅ 使用 `get_cache()` 辅助函数（有降级处理）
- ✅ 有 try-except 异常处理
- ✅ Redis 失败时记录警告但继续验证 token（fail-open 策略）

**代码位置**:
```429:451:services/auth-service/app/services/auth_service.py
            try:
                is_blacklisted = await get_cache(blacklist_key)
                if is_blacklisted:
                    return IntrospectResponse(active=False)
            except Exception as redis_error:
                # ✅ Redis 连接失败时，记录警告但继续验证（降级处理）
                logger.warning(
                    "Redis 黑名单检查失败，继续验证 token",
                    extra={
                        "operation": "introspect_token",
                        "error": str(redis_error),
                    },
                )
                # 继续执行 token 验证，不因为 Redis 失败而拒绝所有请求
```

**符合性**: ✅ **完全符合**

---

#### 3.2 外部 API Token 缓存 ✅ **符合要求**

**文件**: `services/host-service/app/services/external_api_client.py`

**实现情况**:
- ✅ 使用 `redis_manager.get()` 和 `redis_manager.set()`（有降级处理）
- ✅ 缓存失败时，会重新调用外部 API 获取 token
- ✅ 不会因为缓存失败而阻止业务逻辑

**代码位置**:
```217:236:services/host-service/app/services/external_api_client.py
    # 2. 先从 Redis 缓存获取 token
    cache_key = f"{TOKEN_CACHE_KEY_PREFIX}:{user_email}"
    cached_token_data = await redis_manager.get(cache_key)
    if cached_token_data and isinstance(cached_token_data, dict):
        access_token = cached_token_data.get("access_token")
        if access_token:
            # 返回缓存的 token
            return {...}
    
    # 3. 缓存为空，继续调用外部 API 获取 token
```

**符合性**: ✅ **完全符合**

---

#### 3.3 Case 超时配置缓存 ✅ **符合要求**

**文件**: `services/host-service/app/services/case_timeout_task.py`

**实现情况**:
- ✅ 使用 `redis_manager.get()` 和 `redis_manager.set()`（有降级处理）
- ✅ 缓存失败时，从数据库查询配置
- ✅ 不会因为缓存失败而阻止定时任务执行

**代码位置**:
```242:314:services/host-service/app/services/case_timeout_task.py
            # 1. 先从缓存获取
            cached_value = await redis_manager.get(CACHE_KEY_CASE_TIMEOUT)
            if cached_value is not None:
                # 使用缓存值
                return timeout_minutes
            
            # 2. 缓存为空，从数据库查询
            # 3. 查询成功后，存入缓存（即使缓存失败也不影响）
            await redis_manager.set(...)
```

**符合性**: ✅ **完全符合**

---

#### 3.4 WebSocket 跨实例消息发布 ✅ **符合要求**

**文件**: `services/host-service/app/services/agent_websocket_manager.py`

**实现情况**:
- ✅ 发布前检查 `redis_manager.is_connected` 和 `redis_manager.client`
- ✅ Redis 不可用时，返回 `False` 或直接返回，不抛出异常
- ✅ 有 try-except 异常处理
- ✅ 降级处理：Redis 不可用时，只在本实例发送，不跨实例

**代码位置**:
```437:440:services/host-service/app/services/agent_websocket_manager.py
        # 检查 Redis 是否可用
        if not redis_manager.is_connected or not redis_manager.client:
            logger.debug("Redis 不可用，无法跨实例发送")
            return False
```

```592:595:services/host-service/app/services/agent_websocket_manager.py
        # 检查 Redis 是否可用
        if not redis_manager.is_connected or not redis_manager.client:
            logger.debug("Redis 不可用，跳过跨实例广播")
            return
```

**符合性**: ✅ **完全符合**

---

#### 3.5 分布式锁 ⚠️ **部分符合**

**文件**: `services/host-service/app/services/admin_appr_host_service.py`

**实现情况**:
- ✅ 获取锁失败时，检查 `redis_manager.is_connected`
- ✅ Redis 不可用时，记录警告但继续执行（降级处理）
- ⚠️ **注意**: 分布式锁在 Redis 不可用时无法工作，可能导致并发问题

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

**符合性**: ⚠️ **部分符合**（功能降级，但不会导致服务崩溃）

---

### 4. 数据库查询接口 ✅ **符合要求**

**关键接口**: `/api/v1/host/hosts/available` (查询可用主机列表)

**实现情况**:
- ✅ 主要数据源是数据库（`host_rec` 表）
- ✅ Redis 仅用于外部 API token 缓存（有降级处理）
- ✅ Redis 不可用时，仍能从数据库返回数据

**代码位置**:
```84:101:services/host-service/app/services/host_discovery_service.py
        """查询可用的主机列表，支持游标分页

        业务逻辑：
        1. 根据 last_id 计算初始偏移量（用于从外部接口查询）
        2. 调用外部硬件接口分页获取主机列表（带认证）
        3. 根据 hardware_id 查询 host_rec 表进行过滤
        4. 过滤条件：appr_state=1（启用）, host_state=0（空闲），tcp_state=2（监听/连接正常），del_flag=0（未删除）
        5. 收集满足分页大小的结果后返回
```

**符合性**: ✅ **完全符合**

---

## 符合性总结

### ✅ **符合要求的方面**

1. **Redis 连接管理**: 连接失败时降级到无缓存模式，不抛出异常
2. **Redis 基础操作**: 所有操作都有降级处理，返回默认值而不抛出异常
3. **Token 黑名单**: Redis 失败时继续验证 token（fail-open）
4. **外部 API Token 缓存**: 缓存失败时重新获取，不影响业务
5. **Case 超时配置**: 缓存失败时从数据库查询，不影响定时任务
6. **WebSocket 消息发布**: Redis 不可用时只在本实例发送，不跨实例
7. **数据库查询接口**: 主要数据源是数据库，Redis 不可用仍能返回数据

### ⚠️ **需要注意的方面**

1. **分布式锁**: Redis 不可用时，分布式锁失效，可能导致并发问题（但不会导致服务崩溃）
   - **建议**: 在文档中说明此限制，或考虑使用数据库锁作为降级方案

---

## 测试验证建议

### 测试场景 1: Redis 服务断开

**操作步骤**:
1. 启动服务（Redis 正常连接）
2. 停止 Redis 服务
3. 调用 `/api/v1/host/hosts/available` 接口

**预期结果**:
- ✅ API 返回 200，包含数据库中的主机数据
- ✅ 日志中记录 Redis 连接异常
- ✅ 服务未 Crash，继续正常运行

### 测试场景 2: Redis 连接失败（启动时）

**操作步骤**:
1. 确保 Redis 服务未启动
2. 启动服务

**预期结果**:
- ✅ 服务正常启动（不因 Redis 失败而崩溃）
- ✅ 日志中记录："Redis 不可用，服务已降级到无缓存模式，将继续运行"
- ✅ 健康检查端点 `/health` 显示 Redis 状态为 `unavailable`，模式为 `degraded`

---

## 改进建议

### 优先级 P1（建议实施）

1. **分布式锁降级方案**
   - 考虑在 Redis 不可用时使用数据库锁（SELECT ... FOR UPDATE）
   - 或在文档中明确说明此限制

### 优先级 P2（可选优化）

2. **增强日志记录**
   - 在关键业务逻辑中，当 Redis 降级时记录更详细的上下文信息
   - 便于排查和监控

3. **监控指标**
   - 添加 Redis 降级状态的 Prometheus 指标
   - 便于监控和告警

---

## 结论

**当前服务基本符合 Redis 宕机降级要求**：

✅ **符合项**:
- Redis 连接失败时，服务不会崩溃
- 所有 Redis 操作都有降级处理
- 数据库查询接口在 Redis 不可用时仍能返回数据
- 关键业务逻辑都有异常处理和降级策略

⚠️ **注意事项**:
- 分布式锁在 Redis 不可用时失效（功能降级，但不影响服务可用性）

**总体评分**: **90/100** （基本符合，有改进空间）

---

**最后更新**: 2025-01-30  
**分析人员**: AI Assistant  
**状态**: 待用户确认

