# Host 状态变更逻辑完整文档

## 📋 概述

本文档整理了所有与 `host_rec` 表中 `host_state` 和 `appr_state` 字段变更相关的逻辑，包括：
- **接口层面**：API 端点触发的状态变更
- **业务服务层面**：服务类中的状态变更逻辑
- **定时任务层面**：定时任务触发的状态变更
- **WebSocket 层面**：WebSocket 消息触发的状态变更

## 🔢 状态常量定义

### 审批状态 (appr_state)
- `APPR_STATE_DISABLE = 0` - 停用
- `APPR_STATE_ENABLE = 1` - 启用
- `APPR_STATE_CHANGE = 2` - 存在改动

### 主机状态 (host_state)
- `HOST_STATE_FREE = 0` - 空闲
- `HOST_STATE_LOCKED = 1` - 已锁定
- `HOST_STATE_OCCUPIED = 2` - 已占用
- `HOST_STATE_RUNNING = 3` - case执行中
- `HOST_STATE_OFFLINE = 4` - 离线
- `HOST_STATE_INACTIVE = 5` - 待激活
- `HOST_STATE_HW_CHANGE = 6` - 存在潜在的硬件改动
- `HOST_STATE_DISABLED = 7` - 手动停用
- `HOST_STATE_UPDATING = 8` - 更新中

---

## 1️⃣ 接口层面 (API Endpoints)

### 1.1 管理后台 - 主机审批

**接口**: `POST /api/v1/host/admin/appr-host/approve`  
**文件**: `services/host-service/app/api/v1/endpoints/admin_appr_host.py`  
**服务**: `AdminApprHostService.approve_hosts()`

**业务逻辑**:
- 当 `diff_type = 2`（内容变化）时：
  1. 查询所有 `host_hw_rec` 表 `host_id = id, sync_state = 1` 的数据
  2. 最新一条数据：`sync_state = 2, appr_time = now(), appr_by = appr_by`
  3. 其他数据：`sync_state = 4`
  4. **修改 `host_rec` 表**：
     - `appr_state = 1`（启用）
     - `host_state = 0`（空闲）
     - `hw_id = host_hw_rec` 最新一条数据的 `id`
     - `subm_time = now()`
  5. 调用外部 API 同步硬件信息

**状态变更**:
```
appr_state: ? → 1 (启用)
host_state: ? → 0 (空闲)
subm_time: null → now()
```

---

### 1.2 管理后台 - 主机停用

**接口**: `POST /api/v1/host/admin/hosts/{host_id}/disable`  
**文件**: `services/host-service/app/api/v1/endpoints/admin_hosts.py`  
**服务**: `AdminHostService.disable_host()`

**业务逻辑**:
1. 检查主机是否存在且未删除
2. 检查主机状态是否为 0（空闲状态），只有空闲状态才能停用
3. **更新 `host_rec` 表**：
   - `appr_state = 0`（停用）
   - `host_state = 7`（手动停用）

**状态变更**:
```
appr_state: ? → 0 (停用)
host_state: 0 → 7 (手动停用)
前置条件: host_state 必须为 0（空闲）
```

---

### 1.3 管理后台 - 强制下线主机

**接口**: `POST /api/v1/host/admin/hosts/{host_id}/force-offline`  
**文件**: `services/host-service/app/api/v1/endpoints/admin_hosts.py`  
**服务**: `AdminHostService.force_offline_host()`

**业务逻辑**:
1. 检查主机是否存在且未删除
2. 检查主机状态是否为 0（空闲状态），只有空闲状态才能下线
3. **更新 `host_rec` 表**：
   - `host_state = 4`（离线状态）

**状态变更**:
```
host_state: 0 → 4 (离线)
前置条件: host_state 必须为 0（空闲）
```

---

### 1.4 浏览器端 - VNC 连接结果上报

**接口**: `POST /api/v1/host/hosts/vnc/report`  
**文件**: `services/host-service/app/api/v1/endpoints/browser_hosts.py`  
**服务**: `BrowserVNCService.report_vnc_connection()`

**业务逻辑**:
1. 验证主机存在且已启用（`appr_state = 1`）
2. 处理 `host_exec_log` 表（逻辑删除旧记录，创建新记录）
3. **更新 `host_rec` 表**：
   - `host_state = 1`（已锁定）
   - `subm_time = now()`
4. 如果连接状态为 `success`，通过 WebSocket 通知 Agent 开始日志监控

**状态变更**:
```
host_state: ? → 1 (已锁定)
subm_time: ? → now()
前置条件: appr_state 必须为 1（启用）
```

---

### 1.5 浏览器端 - 获取 VNC 连接信息

**接口**: `GET /api/v1/host/hosts/{host_rec_id}/vnc/info`  
**文件**: `services/host-service/app/api/v1/endpoints/browser_hosts.py`  
**服务**: `BrowserVNCService.get_vnc_connection_info()`

**业务逻辑**:
1. 验证主机存在且已启用（`appr_state = 1`）
2. 检查 VNC 连接信息是否完整（IP、端口）
3. **更新 `host_rec` 表**：
   - `host_state = 1`（已锁定）

**状态变更**:
```
host_state: ? → 1 (已锁定)
前置条件: appr_state 必须为 1（启用）
```

---

### 1.6 浏览器端 - 更新主机状态

**接口**: `PUT /api/v1/host/hosts/{host_id}/status`  
**文件**: `services/host-service/app/api/v1/endpoints/browser_hosts.py`  
**服务**: `BrowserHostService.update_host_status()`

**业务逻辑**:
1. 验证主机存在
2. 根据请求参数更新 `host_state` 和 `appr_state`
3. **更新 `host_rec` 表**：
   - `host_state`（根据请求参数）
   - `appr_state`（根据请求参数）

**状态变更**:
```
host_state: ? → ? (根据请求参数)
appr_state: ? → ? (根据请求参数)
```

---

### 1.7 浏览器端 - 测试重置主机

**接口**: `POST /api/v1/host/hosts/reset`  
**文件**: `services/host-service/app/api/v1/endpoints/browser_hosts.py`  
**服务**: `BrowserHostService.reset_host_for_test()`

**业务逻辑**:
1. 验证主机存在
2. **更新 `host_rec` 表**：
   - `appr_state = 1`（启用）
   - `host_state = 0`（空闲）
   - `subm_time = null`
3. 逻辑删除 `host_exec_log` 表中对应的记录（`del_flag = 1`）

**状态变更**:
```
appr_state: ? → 1 (启用)
host_state: ? → 0 (空闲)
subm_time: ? → null
```

---

### 1.8 Agent - VNC 连接状态上报

**接口**: `POST /api/v1/host/agent/vnc/state`  
**文件**: `services/host-service/app/api/v1/endpoints/agent_report.py`  
**服务**: `AgentReportService.report_vnc_connection_state()`

**业务逻辑**:
- **当 `vnc_state = 1`（连接成功）时**：
  1. 检查主机状态是否为 `HOST_STATE_LOCKED`（1）
  2. 如果是，**更新 `host_rec` 表**：
     - `host_state = 2`（已占用）
  3. 如果主机状态不是 `HOST_STATE_LOCKED`，返回错误 `VNC_STATE_MISMATCH`（53016）

- **当 `vnc_state = 2`（连接断开/失败）时**：
  1. **不需要做状态判断**，直接**更新 `host_rec` 表**：
     - `host_state = 0`（空闲）
  2. 逻辑删除 `host_exec_log` 表中对应的有效数据（`del_flag = 1`）

**状态变更**:
```
vnc_state = 1 (连接成功):
  host_state: 1 (已锁定) → 2 (已占用)
  前置条件: host_state 必须为 1（已锁定）

vnc_state = 2 (连接断开/失败):
  host_state: ? → 0 (空闲)
  同时: 逻辑删除 host_exec_log 表中对应的有效数据
```

---

### 1.9 Agent - OTA 更新状态上报

**接口**: `POST /api/v1/host/agent/ota/update-status`  
**文件**: `services/host-service/app/api/v1/endpoints/agent_report.py`  
**服务**: `AgentReportService.report_ota_update_status()`

**业务逻辑**:
1. 验证 Agent 版本号必填
2. 查询 `host_upd` 表，更新 `app_state` 基于 `biz_state`
3. 如果 `biz_state = 2`（成功），**更新 `host_rec` 表**：
   - `host_state = 0`（空闲）
   - `agent_ver` = 新版本号

**状态变更**:
```
当 biz_state = 2 (成功) 时:
  host_state: ? → 0 (空闲)
  agent_ver: ? → 新版本号
```

---

## 2️⃣ 业务服务层面 (Business Services)

### 2.1 Agent WebSocket 管理器 - 处理 Case 开始消息

**文件**: `services/host-service/app/services/agent_websocket_manager.py`  
**方法**: `_handle_case_start_message()`

**业务逻辑**:
1. 验证主机存在
2. 创建或更新 `host_exec_log` 记录
3. **更新 `host_rec` 表**：
   - `host_state = 2`（已占用）
4. **更新 `host_exec_log` 表**：
   - `host_state = 2`（已占用）

**状态变更**:
```
host_rec.host_state: ? → 2 (已占用)
host_exec_log.host_state: ? → 2 (已占用)
```

---

### 2.2 Agent WebSocket 管理器 - 处理 Case 结束消息

**文件**: `services/host-service/app/services/agent_websocket_manager.py`  
**方法**: `_handle_case_end_message()`

**业务逻辑**:
1. 验证主机存在
2. 更新 `host_exec_log` 记录（`case_state`, `end_time`, `result_msg`）
3. **更新 `host_rec` 表**：
   - `host_state = 0`（空闲）
4. **更新 `host_exec_log` 表**：
   - `host_state = 4`（离线）

**状态变更**:
```
host_rec.host_state: ? → 0 (空闲)
host_exec_log.host_state: ? → 4 (离线)
```

---

## 3️⃣ 定时任务层面 (Scheduled Tasks)

### 3.1 VNC 连接超时检测

**文件**: `services/host-service/app/services/case_timeout_task.py`  
**方法**: `CaseTimeoutTaskService._check_vnc_connection_timeout()`

**触发条件**: 定时任务每 10 分钟执行一次

**业务逻辑**:
1. 查询 `host_rec` 表，条件：
   - `host_state = 1`（已锁定）
   - `subm_time - now() > 5 分钟`
2. 对于每个超时的主机：
   - 尝试通过 WebSocket 发送 `HOST_OFFLINE_NOTIFICATION` 消息给 Agent
   - 如果 Agent 未在线，**更新 `host_rec` 表**：
     - `host_state = 0`（空闲）
     - `subm_time = null`
   - 逻辑删除 `host_exec_log` 表中对应的有效数据（`del_flag = 1`）

**状态变更**:
```
当 Agent 未在线时:
  host_state: 1 (已锁定) → 0 (空闲)
  subm_time: ? → null
  同时: 逻辑删除 host_exec_log 表中对应的有效数据
```

---

### 3.2 Case 超时检测

**文件**: `services/host-service/app/services/case_timeout_task.py`  
**方法**: `CaseTimeoutTaskService._check_timeout_cases()`

**触发条件**: 定时任务每 10 分钟执行一次

**业务逻辑**:
1. 查询 `sys_conf` 表获取 `case_timeout` 配置（缓存 1 小时）
2. 查询 `host_exec_log` 表，条件：
   - `host_state` 为 `2`（已占用）或 `3`（case执行中）
   - `case_state = 1`（启动）
   - `del_flag = 0`（未删除）
   - `notify_state = 0`（未通知）
   - `due_time < current_time` 或 `due_time` 为 `NULL` 且 `begin_time < current_time - timeout_minutes`
3. 发送邮件通知并更新 `notify_state = 1`

**注意**: 此任务**不直接修改 `host_rec.host_state`**，只发送通知。

---

## 4️⃣ WebSocket 层面 (WebSocket Messages)

### 4.1 Agent WebSocket - 连接建立

**文件**: `services/host-service/app/api/v1/endpoints/agent_websocket.py`  
**方法**: `agent_websocket_endpoint()`

**业务逻辑**:
1. 验证 WebSocket token
2. 建立 WebSocket 连接
3. **不直接修改 `host_rec.host_state`**，但会注册连接信息

**状态变更**: 无直接状态变更

---

### 4.2 Agent WebSocket - 处理心跳消息

**文件**: `services/host-service/app/services/agent_websocket_manager.py`  
**方法**: `_handle_heartbeat()`

**业务逻辑**:
1. 更新心跳时间戳
2. **不直接修改 `host_rec.host_state`**

**状态变更**: 无直接状态变更

---

### 4.3 Agent WebSocket - 处理 Case 开始/结束消息

**见 2.1 和 2.2 节**

---

## 📊 状态变更流程图

### 主机生命周期状态流转

```
[空闲 (0)]
  ↓ (VNC连接请求)
[已锁定 (1)]
  ↓ (VNC连接成功)
[已占用 (2)]
  ↓ (Case开始)
[Case执行中 (3)]
  ↓ (Case结束)
[空闲 (0)]
```

### 审批流程状态流转

```
[停用 (appr_state=0)]
  ↓ (审批通过)
[启用 (appr_state=1, host_state=0)]
  ↓ (VNC连接)
[已锁定 (host_state=1)]
  ↓ (VNC连接成功)
[已占用 (host_state=2)]
```

### 异常情况状态流转

```
[已锁定 (1)] + (超时 5 分钟)
  ↓ (定时任务检测)
[空闲 (0)] + (subm_time=null)

[已占用 (2)] + (VNC断开)
  ↓ (Agent上报)
[空闲 (0)] + (逻辑删除执行日志)
```

---

## 🔍 关键业务规则总结

### 1. 状态变更前置条件

| 操作 | 前置条件 |
|------|---------|
| 停用主机 | `host_state` 必须为 `0`（空闲） |
| 强制下线 | `host_state` 必须为 `0`（空闲） |
| VNC 连接 | `appr_state` 必须为 `1`（启用） |
| VNC 连接成功上报 | `host_state` 必须为 `1`（已锁定） |

### 2. 状态变更与执行日志的关系

- **VNC 连接成功**：创建 `host_exec_log` 记录，`host_state = 1`（已锁定）
- **VNC 连接断开**：逻辑删除 `host_exec_log` 记录，`host_state = 0`（空闲）
- **Case 开始**：更新 `host_exec_log.host_state = 2`（已占用）
- **Case 结束**：更新 `host_exec_log.host_state = 4`（离线）

### 3. 定时任务清理逻辑

- **VNC 连接超时**：检测 `host_state = 1` 且 `subm_time > 5 分钟`，自动清理
- **Case 超时**：检测 `host_exec_log` 超时记录，发送邮件通知（不修改 `host_rec.host_state`）

### 4. WebSocket 通知机制

- **VNC 连接成功**：通过 WebSocket 通知 Agent 开始日志监控
- **VNC 连接超时**：通过 WebSocket 通知 Agent 下线（如果 Agent 在线）

---

## 📝 注意事项

1. **事务一致性**：所有状态变更操作都在数据库事务中执行，确保数据一致性
2. **并发控制**：部分操作使用 `WHERE` 条件确保状态一致性（如强制下线）
3. **逻辑删除**：`host_exec_log` 表使用逻辑删除（`del_flag = 1`），不物理删除
4. **缓存失效**：VNC 连接成功后，会清除可用主机列表缓存
5. **错误处理**：所有状态变更都有详细的错误处理和日志记录

---

**最后更新**: 2025-01-30  
**文档版本**: 1.0.0

