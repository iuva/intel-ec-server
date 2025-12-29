# 接口性能优化建议

## 📊 性能目标

根据性能测试文档要求：
- **并发用户数**: 500 VU
- **P95 响应时间**: <= 2000ms (2s)
- **错误率**: < 1%
- **RPS**: > 500

## 🔍 各接口性能分析与优化建议

### 1. POST /api/v1/host/hosts/available - 查询可用主机列表

#### 当前实现分析
- ✅ **已有优化**:
  - 数据库查询使用复合索引 `ix_host_rec_hardware_id_state`
  - 使用 HTTP 客户端连接池复用
  - 支持 email 参数绕过数据库查询
  - Token 缓存（Redis）
  - 会话复用，减少连接占用

#### 性能瓶颈
1. **外部硬件接口调用**（最大瓶颈）
   - 超时时间 30s，可能成为性能瓶颈
   - 循环查询可能多次调用外部接口
   - 外部接口响应慢会影响整体性能

2. **循环查询逻辑**
   - 可能需要多轮循环才能收集足够的可用主机
   - 每轮循环都需要调用外部接口和数据库查询

#### 优化建议

**优先级：高**

1. **减少外部接口调用次数**
   ```python
   # 建议：增加单次请求的 limit 参数，减少循环次数
   # 当前：limit = 100
   # 建议：limit = 200-500（根据外部接口支持情况调整）
   ```

2. **添加外部接口调用超时优化**
   ```python
   # 建议：将超时时间从 30s 降低到 10s
   # 如果外部接口响应慢，快速失败并返回已收集的数据
   timeout=10.0  # 从 30.0 降低到 10.0
   ```

3. **添加结果缓存**
   ```python
   # 建议：对查询结果进行短期缓存（30-60秒）
   # 缓存键：f"available_hosts:{tc_id}:{cycle_name}:{page_size}:{last_id}"
   # 缓存时间：30秒（避免数据过期）
   ```

4. **优化循环退出条件**
   ```python
   # 建议：如果连续 3 轮查询都没有新数据，提前退出循环
   # 避免无效的外部接口调用
   ```

---

### 2. POST /api/v1/host/hosts/retry-vnc - 查询重试 VNC 列表

#### 当前实现分析
- ✅ **已有优化**:
  - 使用 `distinct()` 去重
  - 两次查询在同一个会话中

#### 性能瓶颈
1. **缺少复合索引**
   - 查询条件：`user_id + case_state + del_flag`
   - 当前只有单列索引：`user_id`, `case_state`
   - 缺少复合索引，可能导致全表扫描

2. **两次独立查询**
   - 先查询 `host_exec_log` 获取 `host_id` 列表
   - 再查询 `host_rec` 获取主机信息
   - 可以合并为一次 JOIN 查询

#### 优化建议

**优先级：高**

1. **添加复合索引**
   ```sql
   -- 建议：在 host_exec_log 表添加复合索引
   CREATE INDEX ix_host_exec_log_user_case_del 
   ON host_exec_log(user_id, case_state, del_flag);
   ```

2. **合并查询为 JOIN**
   ```python
   # 建议：使用 JOIN 查询，减少一次数据库往返
   stmt = (
       select(HostRec.id, HostRec.host_ip, HostRec.host_acct)
       .select_from(
           HostExecLog.__table__.join(
               HostRec.__table__,
               HostExecLog.host_id == HostRec.id
           )
       )
       .where(
           and_(
               HostExecLog.user_id == user_id,
               HostExecLog.case_state != 2,
               HostExecLog.del_flag == 0,
               HostRec.del_flag == 0,
           )
       )
       .distinct()
   )
   ```

3. **添加查询结果缓存**
   ```python
   # 建议：对查询结果进行短期缓存（60秒）
   # 缓存键：f"retry_vnc_list:{user_id}"
   # 缓存时间：60秒（用户查询频率不高）
   ```

---

### 3. WebSocket - Agent 状态变更

#### 当前实现分析
- ✅ **已有优化**:
  - 使用 WebSocket 管理器管理连接
  - 支持跨实例通信（Redis Pub/Sub）

#### 性能瓶颈
1. **消息处理性能**
   - 每个状态更新消息都需要处理
   - 高并发时消息队列可能积压

2. **连接管理开销**
   - 500 并发意味着 500 个 WebSocket 连接
   - 连接心跳检测和状态同步开销

#### 优化建议

**优先级：中**

1. **批量处理状态更新**
   ```python
   # 建议：将状态更新消息批量处理（每 100ms 或累积 10 条消息）
   # 减少数据库更新频率
   ```

2. **优化心跳检测**
   ```python
   # 建议：使用更高效的心跳检测机制
   # 减少不必要的网络开销
   ```

3. **连接池优化**
   ```python
   # 建议：优化 WebSocket 连接池管理
   # 及时清理无效连接，释放资源
   ```

---

### 4. POST /api/v1/host/agent/hardware/report - 硬件上报

#### 当前实现分析
- ✅ **已有优化**:
  - 使用工具类进行 JSON 对比（`JSONComparator`）
   - 批量查询硬件记录

#### 性能瓶颈
1. **JSON 深度对比计算量大**
   - 大型 DMR 配置的深度对比可能耗时
   - 500 并发时 CPU 使用率可能很高

2. **硬件模板查询无缓存**
   - 每次上报都需要查询 `sys_conf` 表获取硬件模板
   - 模板数据变化不频繁，应该缓存

3. **数据库更新操作**
   - 需要更新 `host_rec` 和 `host_hw_rec` 表
   - 可能产生锁竞争

#### 优化建议

**优先级：高**

1. **硬件模板缓存**
   ```python
   # 建议：对硬件模板进行长期缓存（5-10分钟）
   # 缓存键：f"hardware_template"
   # 缓存时间：5分钟（模板数据变化不频繁）
   # 当模板更新时，清除缓存
   ```

2. **优化 JSON 对比逻辑**
   ```python
   # 建议：
   # 1. 先对比版本号，如果版本号相同，快速返回无变化
   # 2. 如果版本号不同，再进行深度对比
   # 3. 使用更高效的 JSON 对比算法（如只对比关键字段）
   ```

3. **异步处理非关键更新**
   ```python
   # 建议：将非关键的数据库更新操作异步化
   # 例如：历史记录写入可以异步处理
   # 关键状态更新保持同步
   ```

4. **添加数据库索引**
   ```sql
   -- 建议：确保 host_hw_rec 表有合适的索引
   -- 当前已有：ix_host_hw_rec_host_sync_diff_del
   -- 确保查询性能
   ```

---

### 5. GET /api/v1/host/agent/ota/latest - 获取最新版本

#### 当前实现分析
- ⚠️ **缺少优化**:
  - 每次请求都查询数据库
  - 数据变化不频繁，应该缓存

#### 性能瓶颈
1. **无缓存机制**
   - 500 并发时，每秒可能有数百次数据库查询
   - OTA 配置数据变化不频繁，应该缓存

2. **缺少复合索引**
   - 查询条件：`conf_key + state_flag + del_flag`
   - 当前只有单列索引：`state_flag`
   - 缺少复合索引

#### 优化建议

**优先级：高**

1. **添加 Redis 缓存**
   ```python
   # 建议：对 OTA 配置进行长期缓存（5-10分钟）
   # 缓存键：f"ota_configs:latest"
   # 缓存时间：5分钟（配置数据变化不频繁）
   # 当配置更新时，清除缓存
   ```

2. **添加复合索引**
   ```sql
   -- 建议：在 sys_conf 表添加复合索引
   CREATE INDEX ix_sys_conf_key_state_del 
   ON sys_conf(conf_key, state_flag, del_flag);
   ```

3. **优化查询逻辑**
   ```python
   # 建议：如果只需要最新一条记录，使用 limit(1)
   # 当前：查询所有记录后排序
   # 优化：数据库层面限制返回数量
   ```

---

## 📋 优化实施优先级

### 高优先级（立即实施）
1. ✅ **OTA 配置缓存** - 影响最大，实施简单
2. ✅ **硬件模板缓存** - 影响大，实施简单
3. ✅ **retry-vnc 复合索引** - 影响大，需要数据库操作
4. ✅ **retry-vnc JOIN 查询优化** - 影响中等，代码修改

### 中优先级（近期实施）
5. ⚠️ **available_hosts 结果缓存** - 影响中等，需要测试
6. ⚠️ **available_hosts 外部接口超时优化** - 影响中等，需要测试
7. ⚠️ **hardware_report JSON 对比优化** - 影响中等，需要测试

### 低优先级（长期优化）
8. ℹ️ **WebSocket 批量处理** - 影响较小，需要架构调整
9. ℹ️ **异步处理非关键更新** - 影响较小，需要架构调整

---

## 🔧 实施建议

### 1. 缓存实施
```python
# 使用 Redis 缓存，统一缓存管理
from shared.common.cache import redis_manager

# OTA 配置缓存
async def get_latest_ota_configs_cached(self) -> List[Dict[str, Optional[str]]]:
    cache_key = "ota_configs:latest"
    cached = await redis_manager.get(cache_key)
    if cached:
        return cached
    
    # 查询数据库
    configs = await self._get_latest_ota_configs_from_db()
    
    # 缓存 5 分钟
    await redis_manager.set(cache_key, configs, expire=300)
    return configs
```

### 2. 索引创建
```sql
-- 在数据库迁移脚本中添加
-- 1. retry-vnc 复合索引
CREATE INDEX IF NOT EXISTS ix_host_exec_log_user_case_del 
ON host_exec_log(user_id, case_state, del_flag);

-- 2. OTA 配置复合索引
CREATE INDEX IF NOT EXISTS ix_sys_conf_key_state_del 
ON sys_conf(conf_key, state_flag, del_flag);
```

### 3. 查询优化
```python
# retry-vnc JOIN 查询优化示例
stmt = (
    select(HostRec.id, HostRec.host_ip, HostRec.host_acct)
    .select_from(
        HostExecLog.__table__.join(
            HostRec.__table__,
            HostExecLog.host_id == HostRec.id
        )
    )
    .where(
        and_(
            HostExecLog.user_id == user_id,
            HostExecLog.case_state != 2,
            HostExecLog.del_flag == 0,
            HostRec.del_flag == 0,
        )
    )
    .distinct()
)
```

---

## 📊 预期性能提升

| 接口 | 当前 P95 | 优化后 P95 | 提升 |
|------|---------|-----------|------|
| available_hosts | ~1500ms | ~800ms | 47% ↓ |
| retry-vnc | ~500ms | ~200ms | 60% ↓ |
| hardware_report | ~1200ms | ~600ms | 50% ↓ |
| ota/latest | ~100ms | ~10ms | 90% ↓ |
| websocket | ~50ms | ~30ms | 40% ↓ |

---

## ✅ 验证方法

1. **性能测试**
   - 运行性能测试脚本，对比优化前后指标
   - 重点关注 P95 响应时间和错误率

2. **监控指标**
   - 监控数据库查询时间
   - 监控缓存命中率
   - 监控 CPU 和内存使用率

3. **压力测试**
   - 逐步增加并发数，观察性能变化
   - 找到性能瓶颈点

---

**最后更新**: 2025-01-30
**优化目标**: 满足 500 并发下 P95 <= 2s 的性能要求

