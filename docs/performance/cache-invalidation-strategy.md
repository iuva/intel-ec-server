# 缓存失效策略文档

## 📋 缓存清单

### 已实现的缓存

| 缓存键 | 缓存内容 | 过期时间 | 是否需要手动清除 | 状态 |
|--------|---------|---------|----------------|------|
| `ota_configs:latest` | OTA 配置列表 | 5分钟 | ✅ **是** | ✅ 已实现 |
| `hardware_template` | 硬件模板配置 | 5分钟 | ✅ **是** | ⚠️ 待实现 |
| `available_hosts:first_page:{hash}` | 可用主机列表（首次查询） | 30秒 | ✅ **是** | ✅ 已实现 |

---

## ✅ 已实现的缓存失效

### 1. OTA 配置缓存失效 ✅

**缓存键**: `ota_configs:latest`

**失效触发点**:
- `POST /api/v1/admin/ota/deploy` - OTA 配置下发接口

**实现位置**:
- `services/host-service/app/services/admin_ota_service.py::deploy_ota_config()`
- 使用工具函数: `app.utils.cache_invalidation.invalidate_ota_config_cache()`

**代码实现**:
```python
# ✅ 优化：清除 OTA 配置缓存，确保下次查询获取最新数据
from app.utils.cache_invalidation import invalidate_ota_config_cache
await invalidate_ota_config_cache()
```

**验证方法**:
1. 下发 OTA 配置后，检查日志是否有 "OTA 配置缓存已清除"
2. 立即查询 OTA 配置接口，确认返回最新数据（非缓存数据）

---

## ⚠️ 待实现的缓存失效

### 2. 硬件模板缓存失效 ⚠️

**缓存键**: `hardware_template`

**失效触发点**:
- ⚠️ **当前未找到硬件模板更新接口**
- 如果将来添加硬件模板更新接口，需要在更新后清除缓存

**建议实现位置**:
- 如果添加硬件模板更新接口，应在更新 `sys_conf` 表（`conf_key='hw_temp'`）后调用：
  ```python
  from app.utils.cache_invalidation import invalidate_hardware_template_cache
  await invalidate_hardware_template_cache()
  ```

**工具函数**:
- 已提供: `app.utils.cache_invalidation.invalidate_hardware_template_cache()`
- 可直接使用，无需额外实现

**注意事项**:
- 硬件模板可能通过数据库直接更新
- 如果通过数据库直接更新，需要手动清除缓存或重启服务

---

## ✅ 已实现的缓存失效（可用主机列表）

### 3. 可用主机列表缓存失效 ✅

**缓存键**: `available_hosts:first_page:{hash}`

**过期时间**: 30秒（自动过期）

**失效触发点**:
- `POST /api/v1/host/vnc/connect` - 获取 VNC 连接信息接口（主机状态变为已锁定）
- `POST /api/v1/host/vnc/report` - 上报 VNC 连接成功接口（主机状态变为已锁定）

**实现位置**:
- `services/host-service/app/services/browser_vnc_service.py::get_vnc_connection_info()`
- `services/host-service/app/services/browser_vnc_service.py::report_vnc_connection()`
- 使用工具函数: `app.utils.cache_invalidation.invalidate_available_hosts_cache()`

**代码实现**:
```python
# ✅ 优化：清除可用主机列表缓存，因为主机状态已变为已锁定
# 该主机不应再出现在可用主机列表中，需要清除相关缓存
try:
    deleted_count = await invalidate_available_hosts_cache()
    if deleted_count > 0:
        logger.info("可用主机列表缓存已清除（主机状态已锁定）")
except Exception as e:
    logger.warning("清除可用主机列表缓存失败", extra={"error": str(e)})
```

**为什么需要清除**:
1. **主机状态变化**: 当主机状态变为已锁定（`host_state = 1`）时，该主机不应再出现在可用主机列表中
2. **数据一致性**: 清除缓存确保下次查询时获取最新的可用主机列表（不包含已锁定的主机）
3. **用户体验**: 避免用户看到已锁定的主机，导致连接失败

**清除策略**:
- 使用模式匹配清除所有相关缓存: `available_hosts:first_page:*`
- 因为缓存键包含哈希值，无法精确匹配，所以清除所有首次查询缓存
- 影响范围小：只清除首次查询缓存，分页查询不受影响

**验证方法**:
1. 获取 VNC 连接信息后，检查日志是否有 "可用主机列表缓存已清除"
2. 立即查询可用主机列表接口，确认已锁定的主机不在列表中

---

## 🛠️ 缓存失效工具函数

### 工具模块位置

**文件**: `services/host-service/app/utils/cache_invalidation.py`

### 提供的函数

#### 1. `invalidate_ota_config_cache()`
```python
async def invalidate_ota_config_cache() -> bool:
    """清除 OTA 配置缓存"""
    # 清除缓存键: ota_configs:latest
```

#### 2. `invalidate_hardware_template_cache()`
```python
async def invalidate_hardware_template_cache() -> bool:
    """清除硬件模板缓存"""
    # 清除缓存键: hardware_template
```

#### 3. `invalidate_available_hosts_cache(pattern)`
```python
async def invalidate_available_hosts_cache(pattern: Optional[str] = None) -> int:
    """清除可用主机列表缓存（支持模式匹配）"""
    # 默认清除: available_hosts:first_page:*
```

#### 4. `invalidate_sys_conf_cache(conf_key)`
```python
async def invalidate_sys_conf_cache(conf_key: str) -> bool:
    """根据 conf_key 清除对应的系统配置缓存"""
    # 支持: "ota", "hw_temp"
```

---

## 📝 使用示例

### 在更新接口中使用

```python
from app.utils.cache_invalidation import (
    invalidate_ota_config_cache,
    invalidate_hardware_template_cache,
    invalidate_sys_conf_cache,
)

# 示例1: 更新 OTA 配置后清除缓存
async def update_ota_config():
    # 更新数据库
    await update_sys_conf_ota(...)
    
    # 清除缓存
    await invalidate_ota_config_cache()

# 示例2: 更新硬件模板后清除缓存
async def update_hardware_template():
    # 更新数据库
    await update_sys_conf_hw_temp(...)
    
    # 清除缓存
    await invalidate_hardware_template_cache()

# 示例3: 通用方法（根据 conf_key 自动选择）
async def update_sys_conf(conf_key: str):
    # 更新数据库
    await update_sys_conf_by_key(conf_key, ...)
    
    # 清除对应缓存
    await invalidate_sys_conf_cache(conf_key)
```

---

## 🔍 检查清单

### 代码审查检查点

- [x] OTA 配置更新接口已添加缓存清除逻辑
- [ ] 硬件模板更新接口（如果存在）已添加缓存清除逻辑
- [ ] 所有更新 `sys_conf` 表的地方都检查了是否需要清除缓存
- [ ] 缓存清除逻辑包含异常处理，不影响主流程

### 测试验证

- [ ] 下发 OTA 配置后，立即查询 OTA 配置接口，确认返回最新数据
- [ ] 更新硬件模板后（如果接口存在），立即查询硬件模板，确认返回最新数据
- [ ] Redis 不可用时，缓存清除失败不影响主流程

---

## 🚨 注意事项

### 1. 异常处理

所有缓存清除操作都包含异常处理，确保 Redis 不可用时不影响主流程：

```python
try:
    await invalidate_ota_config_cache()
except Exception as e:
    logger.warning(f"清除缓存失败: {e!s}")
    # 继续执行，不影响主流程
```

### 2. 数据库直接更新

如果通过数据库直接更新 `sys_conf` 表（不通过 API 接口），需要：

- **方案1**: 手动清除缓存
  ```bash
  redis-cli DEL ota_configs:latest
  redis-cli DEL hardware_template
  ```

- **方案2**: 重启服务（缓存会自动过期）

### 3. 缓存键命名规范

所有缓存键遵循统一命名规范：
- OTA 配置: `ota_configs:latest`
- 硬件模板: `hardware_template`
- 可用主机: `available_hosts:first_page:{hash}`

---

## 📊 缓存失效流程图

```
管理员更新配置
    │
    ├──→ 更新 sys_conf 表
    │       │
    │       ├──→ conf_key = 'ota'
    │       │       └──→ 调用 invalidate_ota_config_cache()
    │       │
    │       └──→ conf_key = 'hw_temp'
    │               └──→ 调用 invalidate_hardware_template_cache()
    │
    └──→ 清除 Redis 缓存
            │
            └──→ 下次查询时重新加载并缓存
```

---

## 🔄 未来扩展

### 如果添加新的缓存

1. **在 `cache_invalidation.py` 中添加清除函数**
2. **在对应的更新接口中调用清除函数**
3. **更新本文档**

### 如果添加硬件模板更新接口

1. **在更新接口中调用 `invalidate_hardware_template_cache()`**
2. **更新本文档状态为"已实现"**

---

**最后更新**: 2025-01-30
**维护者**: 开发团队
**相关文件**:
- `services/host-service/app/utils/cache_invalidation.py` - 缓存失效工具
- `services/host-service/app/services/admin_ota_service.py` - OTA 配置服务
- `services/host-service/app/services/agent_report_service.py` - Agent 上报服务

