# Host Upd 表新增记录接口汇总

## 📋 概述

`host_upd` 表用于记录主机 OTA 更新状态。本文档汇总了所有会新增 `host_upd` 记录的接口和场景。

---

## 🔍 新增记录的场景

### 场景 1: 管理后台 OTA 配置下发（WebSocket 回调）

**接口路径**: `POST /api/v1/host/admin/ota/deploy`

**触发方式**: 通过 WebSocket 回调处理器

**文件位置**:

- **API 端点**: `services/host-service/app/api/v1/endpoints/admin_ota.py:144`
- **服务层**: `services/host-service/app/services/admin_ota_service.py:119`
- **回调处理器**: `services/host-service/app/services/admin_ota_service.py:282`

#### 业务流程

```
1. 管理后台调用下发接口
   ↓
2. 更新 sys_conf 表（OTA 配置）
   ↓
3. 通过 WebSocket 广播消息给所有连接的 Host
   ↓
4. Agent 收到消息后，回调通知服务器
   ↓
5. 回调处理器 _handle_ota_deploy_notification 创建 host_upd 记录
```

#### 创建记录的条件

- **触发时机**: Agent 收到 OTA 下发消息后，通过 WebSocket 回调通知服务器
- **回调消息格式**:

  ```json
  {
    "conf_name": "配置名称",
    "conf_ver": "配置版本号"
  }
  ```

#### 创建的记录字段

```python
host_upd = HostUpd(
    host_id=host_id_int,        # 从 WebSocket agent_id 获取
    app_name=conf_name,         # 从回调消息中获取
    app_ver=conf_ver,           # 从回调消息中获取
    app_state=0,                # 预更新状态（固定为 0）
    created_by=None,            # 创建人（可选）
    updated_by=None,            # 更新人（可选）
)
```

#### 代码位置

```python
# services/host-service/app/services/admin_ota_service.py:282
async def _handle_ota_deploy_notification(self, agent_id: str, data: dict) -> None:
    """处理 Host OTA 下发回调通知
    
    业务逻辑：
    - 当 host 收到 OTA 下发消息后，会回调此处理器
    - 在 host_upd 表中新增一条记录：
      - app_state = 0 (预更新)
      - host_id = host_id (从 websocket agent_id 获取)
      - app_name = conf_name (从回调消息中获取)
      - app_ver = conf_ver (从回调消息中获取)
    """
    # ... 创建 host_upd 记录
    host_upd = HostUpd(
        host_id=host_id_int,
        app_name=conf_name,
        app_ver=conf_ver,
        app_state=0,  # 预更新状态
        created_by=None,
    )
    session.add(host_upd)
    await session.commit()
```

---

### 场景 2: Agent OTA 更新状态上报（未找到记录时）

**接口路径**: `POST /api/v1/host/agent/ota/update-status`

**触发方式**: Agent 主动上报更新状态

**文件位置**:

- **API 端点**: `services/host-service/app/api/v1/endpoints/agent_report.py:908`
- **服务层**: `services/host-service/app/services/agent_report_service.py:1207`

#### 业务流程

```
1. Agent 调用更新状态上报接口
   ↓
2. 查询 host_upd 表（host_id, app_name, app_ver, del_flag=0）
   ↓
3. 如果未找到记录：
   ├─ 逻辑删除该 host_id 和 app_name 的所有有效记录（保证有效数据只有一条）
   └─ 创建新记录，设置 app_state = biz_state
   ↓
4. 如果找到记录：
   └─ 更新 app_state 字段
   ↓
5. 如果 biz_state = 2（成功）：
   ├─ 更新 host_rec 表（host_state=0, agent_ver）
   └─ 逻辑删除 host_upd 当前记录（del_flag=1）
```

#### 创建记录的条件

- **触发时机**: Agent 上报更新状态时，如果未找到对应的 `host_upd` 记录
- **查询条件**: `host_id`, `app_name`, `app_ver`, `del_flag=0`
- **创建前处理**: 逻辑删除该 `host_id` 和 `app_name` 的所有有效记录（保证有效数据只有一条）

#### 创建的记录字段

```python
host_upd = HostUpd(
    host_id=host_id,            # 从 JWT token 中提取
    app_name=app_name,          # 从请求参数中获取
    app_ver=app_ver,            # 从请求参数中获取
    app_state=app_state,        # 等于 biz_state（1=更新中，2=成功，3=失败）
    created_by=None,            # 创建人（可选）
    updated_by=None,            # 更新人（可选）
)
```

#### 代码位置

```python
# services/host-service/app/services/agent_report_service.py:1284
if not host_upd:
    # 逻辑删除该 host_id 和 app_name 的所有有效记录（保证有效数据只有一条）
    delete_other_stmt = (
        update(HostUpd)
        .where(
            and_(
                HostUpd.host_id == host_id,
                HostUpd.app_name == app_name,
                HostUpd.del_flag == 0,
            )
        )
        .values(del_flag=1)
    )
    await session.execute(delete_other_stmt)
    
    # 创建新记录
    host_upd = HostUpd(
        host_id=host_id,
        app_name=app_name,
        app_ver=app_ver,
        app_state=app_state,  # 等于 biz_state
        created_by=None,
        updated_by=None,
    )
    session.add(host_upd)
    await session.flush()  # 刷新以获取生成的 ID
```

---

## 📊 对比分析

| 特性 | 场景 1: OTA 配置下发 | 场景 2: Agent 状态上报 |
|------|---------------------|----------------------|
| **接口路径** | `POST /api/v1/host/admin/ota/deploy` | `POST /api/v1/host/agent/ota/update-status` |
| **触发方式** | WebSocket 回调（被动） | HTTP API 调用（主动） |
| **调用方** | Agent（通过 WebSocket 回调） | Agent（直接 HTTP 调用） |
| **创建时机** | Agent 收到 OTA 下发消息后 | Agent 上报状态时未找到记录 |
| **app_state 初始值** | `0`（预更新） | `biz_state`（1=更新中，2=成功，3=失败） |
| **创建前处理** | 无 | 逻辑删除其他有效记录 |
| **数据来源** | WebSocket 回调消息 | HTTP 请求参数 |
| **host_id 来源** | WebSocket `agent_id` | JWT token `id` |

---

## 🔄 完整流程示例

### 流程 1: 正常 OTA 更新流程

```
1. 管理后台下发 OTA 配置
   POST /api/v1/host/admin/ota/deploy
   ↓
2. 系统广播 WebSocket 消息给所有 Host
   ↓
3. Agent 收到消息，回调通知服务器
   → 创建 host_upd 记录（app_state=0，预更新）
   ↓
4. Agent 开始更新，上报状态
   POST /api/v1/host/agent/ota/update-status
   biz_state=1（更新中）
   → 更新 host_upd 记录（app_state=1）
   ↓
5. Agent 更新完成，上报状态
   POST /api/v1/host/agent/ota/update-status
   biz_state=2（成功）
   → 更新 host_rec 表（host_state=0, agent_ver）
   → 逻辑删除 host_upd 记录（del_flag=1）
```

### 流程 2: 直接上报状态（未经过下发）

```
1. Agent 直接上报更新状态
   POST /api/v1/host/agent/ota/update-status
   biz_state=1（更新中）
   ↓
2. 系统查询 host_upd 表，未找到记录
   ↓
3. 逻辑删除该 host_id 和 app_name 的所有有效记录
   ↓
4. 创建新记录（app_state=1，更新中）
   ↓
5. Agent 更新完成，上报状态
   POST /api/v1/host/agent/ota/update-status
   biz_state=2（成功）
   → 更新 host_rec 表（host_state=0, agent_ver）
   → 逻辑删除 host_upd 记录（del_flag=1）
```

---

## 📝 关键业务规则

### 1. 数据唯一性保证

- **场景 1**: 不检查唯一性，直接创建（依赖 Agent 回调的时序）
- **场景 2**: 创建前逻辑删除其他有效记录，保证有效数据只有一条

### 2. 记录状态流转

```
预更新 (0) → 更新中 (1) → 成功 (2) / 失败 (3)
```

- **场景 1**: 创建时状态为 `0`（预更新）
- **场景 2**: 创建时状态为 `biz_state`（可能是 1、2 或 3）

### 3. 记录清理规则

- **更新成功时**: 逻辑删除当前记录（`del_flag=1`）
- **更新失败时**: 保留记录，状态为 `3`（失败）

---

## 🔗 相关接口

### 管理后台接口

- **查询 OTA 配置列表**: `GET /api/v1/host/admin/ota/list`
- **下发 OTA 配置**: `POST /api/v1/host/admin/ota/deploy` ⭐（触发场景 1）

### Agent 接口

- **获取最新 OTA 配置**: `GET /api/v1/host/agent/ota/latest`
- **上报 OTA 更新状态**: `POST /api/v1/host/agent/ota/update-status` ⭐（触发场景 2）

---

## 📊 数据表结构

### `host_upd` 表字段

| 字段名 | 类型 | 说明 | 来源 |
|--------|------|------|------|
| `id` | BIGINT | 主键（自增） | 数据库自动生成 |
| `host_id` | BIGINT | 主机ID | WebSocket `agent_id` 或 JWT token `id` |
| `app_name` | VARCHAR(32) | 应用名称 | WebSocket 回调消息或 HTTP 请求参数 |
| `app_ver` | VARCHAR(32) | 应用版本号 | WebSocket 回调消息或 HTTP 请求参数 |
| `app_state` | SMALLINT | 更新状态 | 场景1固定为0，场景2为`biz_state` |
| `created_by` | BIGINT | 创建人 | 可选，通常为 `None` |
| `updated_by` | BIGINT | 更新人 | 可选，通常为 `None` |
| `created_time` | DATETIME | 创建时间 | 数据库自动生成 |
| `updated_time` | DATETIME | 更新时间 | 数据库自动更新 |
| `del_flag` | TINYINT | 删除标志 | 默认 `0`，成功时设置为 `1` |

### `app_state` 状态值

| 值 | 状态 | 说明 |
|---|------|------|
| `0` | 预更新 | 已下发配置，等待 Agent 开始更新 |
| `1` | 更新中 | Agent 正在执行更新 |
| `2` | 成功 | 更新成功，记录会被逻辑删除 |
| `3` | 失败 | 更新失败，记录保留 |

---

## ⚠️ 注意事项

### 1. 并发处理

- **场景 1**: WebSocket 回调可能并发，但每个 Agent 只会回调一次
- **场景 2**: Agent 可能并发上报状态，但通过逻辑删除保证唯一性

### 2. 数据一致性

- **场景 1**: 如果 Agent 未回调，`host_upd` 记录不会创建
- **场景 2**: 如果 Agent 直接上报状态，会自动创建记录

### 3. 记录清理

- **更新成功时**: 记录会被逻辑删除（`del_flag=1`）
- **更新失败时**: 记录保留，状态为 `3`（失败）

---

## 🔍 调试建议

### 1. 检查记录创建

```sql
-- 查询所有有效的 host_upd 记录
SELECT * FROM host_upd WHERE del_flag = 0 ORDER BY created_time DESC;

-- 查询特定主机的更新记录
SELECT * FROM host_upd WHERE host_id = 123 AND del_flag = 0;
```

### 2. 检查 WebSocket 回调

- 查看日志：`_handle_ota_deploy_notification` 相关日志
- 确认 Agent 是否收到 OTA 下发消息
- 确认 Agent 是否成功回调通知服务器

### 3. 检查 Agent 上报

- 查看日志：`report_ota_update_status` 相关日志
- 确认 Agent 是否成功调用更新状态上报接口
- 确认是否创建了新记录（`is_new_record=True`）

---

**最后更新**: 2025-01-30  
**文档版本**: 1.0.0
