# 可用主机列表缓存逻辑详解

## 📋 缓存概述

### 缓存目的
减少外部硬件接口调用，提升首次查询性能。由于可用主机列表查询涉及：
1. 调用外部硬件接口（可能较慢）
2. 多次数据库查询和过滤
3. 循环遍历直到收集足够数据

首次查询结果缓存可以显著减少重复的外部接口调用。

---

## 🔑 缓存键生成逻辑

### 缓存条件
**只缓存首次查询**（`last_id=None`），后续分页查询不缓存。

### 缓存键生成算法

```python
# 1. 检查是否为首次查询
if request.last_id is None:
    # 2. 构建缓存参数（包含关键查询参数）
    cache_params = f"{request.tc_id}:{request.cycle_name}:{request.page_size}"
    
    # 3. 生成 MD5 哈希值（确保缓存键长度固定）
    cache_hash = hashlib.md5(cache_params.encode()).hexdigest()
    
    # 4. 生成完整缓存键
    cache_key = f"available_hosts:first_page:{cache_hash}"
```

### 缓存键组成

| 组成部分 | 说明 | 示例 |
|---------|------|------|
| 前缀 | `available_hosts:first_page:` | 固定前缀 |
| 哈希值 | MD5(tc_id:cycle_name:page_size) | `a1b2c3d4e5f6...` |

### 缓存键示例

```python
# 示例1: tc_id="test_001", cycle_name="cycle_1", page_size=20
cache_key = "available_hosts:first_page:a1b2c3d4e5f6789012345678901234abcd"

# 示例2: tc_id="test_001", cycle_name="cycle_1", page_size=50
cache_key = "available_hosts:first_page:ef1234567890abcdef1234567890abcd12"
```

### 为什么使用哈希值？

1. **固定长度**: MD5 哈希值固定为 32 字符，便于管理
2. **唯一性**: 不同查询参数组合生成不同的哈希值
3. **安全性**: 避免缓存键过长或包含特殊字符

---

## 📊 缓存数据结构

### 缓存的数据格式

```python
cache_data = {
    "hosts": [
        {
            "id": "123456",
            "host_rec_id": "123456",
            "user_name": "ccr\\sys_eval",
            "host_ip": "10.239.168.184",
        },
        # ... 更多主机
    ],
    "total": 50,           # 本次查询中发现的总数
    "page_size": 20,       # 每页大小
    "has_next": True,      # 是否有下一页
    "last_id": "123456",   # 当前页最后一条记录的 id
}
```

### 响应对象结构

```python
class AvailableHostsListResponse(BaseModel):
    """可用主机列表响应模式"""
    
    hosts: List[AvailableHostInfo] = Field(description="可用主机列表")
    total: int = Field(description="本次查询中发现的总数")
    page_size: int = Field(description="每页大小")
    has_next: bool = Field(description="是否有下一页")
    last_id: Optional[str] = Field(description="当前页最后一条记录的 id，用于请求下一页")

class AvailableHostInfo(BaseModel):
    """可用主机信息"""
    
    id: str = Field(description="主机ID（host_rec.id）")
    host_rec_id: str = Field(description="主机记录ID（与 id 相同）")
    user_name: str = Field(description="主机账号（host_acct）")
    host_ip: str = Field(description="主机IP地址")
```

---

## 🔄 缓存流程

### 1. 查询流程（首次查询）

```
用户请求（last_id=None）
    │
    ├──→ 生成缓存键
    │       └──→ available_hosts:first_page:{hash}
    │
    ├──→ 尝试从缓存获取
    │       │
    │       ├──→ 缓存命中 ✅
    │       │       └──→ 直接返回缓存数据（跳过外部接口调用）
    │       │
    │       └──→ 缓存未命中 ❌
    │               │
    │               ├──→ 调用外部硬件接口
    │               ├──→ 查询数据库过滤
    │               ├──→ 循环收集数据
    │               │
    │               └──→ 存入缓存（30秒过期）
    │                       └──→ 返回结果
```

### 2. 查询流程（分页查询）

```
用户请求（last_id="123456"）
    │
    ├──→ 检查 last_id
    │       └──→ last_id != None
    │
    └──→ 不生成缓存键（跳过缓存）
            │
            ├──→ 调用外部硬件接口
            ├──→ 查询数据库过滤
            ├──→ 循环收集数据
            │
            └──→ 返回结果（不缓存）
```

---

## ⏱️ 缓存过期时间

### 过期时间设置

```python
await redis_manager.set(cache_key, cache_data, expire=30)  # 30秒过期
```

### 为什么是 30 秒？

1. **数据新鲜度**: 主机列表可能频繁变化（主机被占用、释放等）
2. **性能平衡**: 太短（<10秒）缓存效果不明显，太长（>60秒）数据可能过时
3. **自动过期**: 30秒后自动失效，无需手动清除

### 缓存时间对比

| 缓存类型 | 过期时间 | 原因 |
|---------|---------|------|
| OTA 配置 | 5分钟 | 配置变化频率低 |
| 硬件模板 | 5分钟 | 模板变化频率低 |
| **可用主机列表** | **30秒** | **主机状态变化频繁** |

---

## 🎯 缓存策略设计

### 为什么只缓存首次查询？

#### ✅ 缓存首次查询的原因

1. **查询成本高**: 首次查询需要调用外部接口，可能涉及多次循环
2. **用户行为**: 用户通常先查看第一页，再决定是否翻页
3. **缓存命中率高**: 首次查询的重复率较高

#### ❌ 不缓存分页查询的原因

1. **last_id 不同**: 每个用户的 `last_id` 不同，缓存键会非常多
2. **数据变化**: 分页查询时，前面的主机可能已被占用，数据已变化
3. **缓存管理**: 过多的缓存键难以管理，容易造成内存浪费

### 缓存键包含的参数

**包含的参数**:
- `tc_id`: 测试用例 ID
- `cycle_name`: 测试周期名称
- `page_size`: 每页大小

**不包含的参数**:
- `last_id`: 首次查询时固定为 None
- `user_name`: 不影响查询结果（用于日志记录）
- `email`: 不影响查询结果（用于认证优化）

**为什么这样设计？**
- 包含影响查询结果的参数（tc_id, cycle_name, page_size）
- 排除不影响结果的参数（user_name, email）
- 排除分页参数（last_id），因为只缓存首次查询

---

## 📈 性能影响分析

### 缓存命中场景

**场景1: 同一用户重复查询第一页**
```
用户A: POST /api/v1/host/hosts/available
  - tc_id="test_001", cycle_name="cycle_1", page_size=20, last_id=None
  - 第一次: 缓存未命中，查询外部接口，耗时 ~1500ms
  - 第二次（30秒内）: 缓存命中，直接返回，耗时 ~10ms
  - 性能提升: 99.3% ↓
```

**场景2: 不同用户查询相同条件的第一页**
```
用户A: POST /api/v1/host/hosts/available
  - tc_id="test_001", cycle_name="cycle_1", page_size=20, last_id=None
  - 缓存未命中，查询外部接口，存入缓存

用户B（30秒内）: POST /api/v1/host/hosts/available
  - tc_id="test_001", cycle_name="cycle_1", page_size=20, last_id=None
  - 缓存命中，直接返回（共享缓存）
  - 性能提升: 99.3% ↓
```

### 缓存未命中场景

**场景1: 分页查询**
```
用户: POST /api/v1/host/hosts/available
  - last_id="123456"  # 不是首次查询
  - 不生成缓存键，直接查询
```

**场景2: 缓存过期**
```
用户: POST /api/v1/host/hosts/available
  - 缓存已过期（>30秒）
  - 缓存未命中，重新查询并更新缓存
```

**场景3: 查询参数不同**
```
用户A: tc_id="test_001", cycle_name="cycle_1", page_size=20
用户B: tc_id="test_002", cycle_name="cycle_1", page_size=20
  - 缓存键不同（tc_id 不同）
  - 各自独立缓存
```

---

## 🔍 缓存数据转换

### 存储格式（字典）

```python
cache_data = {
    "hosts": [
        {
            "id": "123456",
            "host_rec_id": "123456",
            "user_name": "ccr\\sys_eval",
            "host_ip": "10.239.168.184",
        },
    ],
    "total": 50,
    "page_size": 20,
    "has_next": True,
    "last_id": "123456",
}
```

### 读取格式（响应对象）

```python
# 从缓存读取
cached_result = await redis_manager.get(cache_key)

# 转换为响应对象
response = AvailableHostsListResponse(**cached_result)

# 返回
return response
```

### 为什么需要转换？

1. **存储**: Redis 只能存储 JSON 可序列化的数据（字典）
2. **使用**: API 需要返回 Pydantic 模型对象
3. **验证**: Pydantic 模型提供数据验证和类型安全

---

## 🚨 注意事项

### 1. 缓存一致性

**问题**: 缓存的数据可能与实际数据不一致

**原因**:
- 主机状态可能变化（被占用、释放等）
- 缓存时间 30 秒，期间数据可能已变化

**影响**:
- 用户可能看到已占用的主机（30秒内的缓存）
- 但影响较小，因为：
  - 缓存时间短（30秒）
  - 用户通常会重试或刷新

**解决方案**:
- 保持 30 秒的缓存时间（平衡性能和一致性）
- 如果将来需要，可以添加手动清除缓存的接口

### 2. 缓存键冲突

**问题**: 不同查询参数可能生成相同的哈希值（MD5 碰撞）

**概率**: 极低（MD5 碰撞概率约为 1/2^128）

**影响**: 如果发生碰撞，不同查询可能返回相同的缓存数据

**解决方案**:
- 当前方案已足够（碰撞概率极低）
- 如果将来需要，可以使用 SHA-256 或更长的哈希值

### 3. 缓存内存占用

**问题**: 大量不同的查询参数组合会产生大量缓存键

**估算**:
- 每个缓存数据约 1-5 KB
- 假设 1000 个不同的查询组合
- 总内存占用: 1-5 MB（可接受）

**解决方案**:
- 缓存时间短（30秒），自动过期
- Redis 内存充足，影响较小

---

## 📊 缓存命中率监控

### 日志记录

**缓存命中**:
```python
logger.debug(
    "从缓存获取可用主机列表（首次查询）",
    extra={
        "cache_key": cache_key,
        "count": len(cached_result.get("hosts", [])),
    },
)
```

**缓存未命中**:
```python
logger.warning(
    "从缓存获取可用主机列表失败，将查询数据库",
    extra={"cache_key": cache_key, "error": str(e)},
)
```

**缓存写入**:
```python
logger.debug(
    "可用主机列表已缓存（首次查询）",
    extra={"cache_key": cache_key, "expire_seconds": 30},
)
```

### 监控指标建议

```python
# 可以添加的 Prometheus 指标
CACHE_HITS = Counter(
    "available_hosts_cache_hits_total",
    "可用主机列表缓存命中次数",
    ["tc_id", "cycle_name"],
)

CACHE_MISSES = Counter(
    "available_hosts_cache_misses_total",
    "可用主机列表缓存未命中次数",
    ["tc_id", "cycle_name"],
)
```

---

## 🔧 优化建议

### 当前实现 ✅

- ✅ 只缓存首次查询（避免缓存键过多）
- ✅ 30秒过期时间（平衡性能和一致性）
- ✅ 包含关键查询参数（tc_id, cycle_name, page_size）
- ✅ 异常处理完善（Redis 不可用时降级）

### 未来优化（可选）

1. **缓存预热**: 系统启动时预加载常用查询的缓存
2. **缓存版本控制**: 使用版本号管理缓存，支持快速失效
3. **智能过期**: 根据数据变化频率动态调整过期时间
4. **缓存压缩**: 对大型缓存数据进行压缩，减少内存占用

---

## 📋 代码位置

### 缓存逻辑实现

**文件**: `services/host-service/app/services/host_discovery_service.py`

**关键代码位置**:
- 缓存键生成: 第 148-155 行
- 缓存读取: 第 157-174 行
- 缓存写入: 第 397-414 行

### 响应模型定义

**文件**: `services/host-service/app/schemas/host.py`

**关键类**:
- `AvailableHostsListResponse`: 第 232 行
- `AvailableHostInfo`: 第 222 行
- `QueryAvailableHostsRequest`: 第 127 行

---

## 🧪 测试场景

### 测试用例1: 缓存命中

```python
# 第一次请求
response1 = await query_available_hosts(
    QueryAvailableHostsRequest(
        tc_id="test_001",
        cycle_name="cycle_1",
        page_size=20,
        last_id=None,  # 首次查询
    )
)
# 预期: 缓存未命中，查询外部接口，耗时 ~1500ms

# 第二次请求（30秒内）
response2 = await query_available_hosts(
    QueryAvailableHostsRequest(
        tc_id="test_001",
        cycle_name="cycle_1",
        page_size=20,
        last_id=None,  # 首次查询
    )
)
# 预期: 缓存命中，直接返回，耗时 ~10ms
# 验证: response1 == response2
```

### 测试用例2: 缓存未命中（分页查询）

```python
# 分页查询
response = await query_available_hosts(
    QueryAvailableHostsRequest(
        tc_id="test_001",
        cycle_name="cycle_1",
        page_size=20,
        last_id="123456",  # 不是首次查询
    )
)
# 预期: 不生成缓存键，直接查询，不缓存
```

### 测试用例3: 缓存过期

```python
# 第一次请求
response1 = await query_available_hosts(...)
# 存入缓存，30秒过期

# 等待 31 秒
await asyncio.sleep(31)

# 第二次请求
response2 = await query_available_hosts(...)
# 预期: 缓存已过期，重新查询并更新缓存
```

---

## 📚 相关文档

- [性能优化实施总结](./optimization-implementation-summary.md) - 完整的优化实施总结
- [缓存失效策略](./cache-invalidation-strategy.md) - 缓存失效策略说明
- [性能测试计划](../performance_test_plan.md) - 性能测试要求

---

**最后更新**: 2025-01-30
**维护者**: 开发团队
**相关文件**:
- `services/host-service/app/services/host_discovery_service.py` - 缓存逻辑实现
- `services/host-service/app/schemas/host.py` - 响应模型定义

