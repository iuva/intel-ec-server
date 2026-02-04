# 主机状态流转规则文档

## 📋 概述

本文档详细说明了主机状态（`host_state`）和审批状态（`appr_state`）的流转规则，包括审批接口和 WebSocket 触发的状态变更。

## 🎯 状态定义

### 审批状态 (appr_state)

| 值 | 名称 | 说明 |
|---|---|---|
| 0 | 停用 (DISABLE) | 主机已停用 |
| 1 | 启用 (ENABLE) | 主机已启用/新增 |
| 2 | 存在改动 (CHANGE) | 存在硬件改动，等待审批 |

### 主机状态 (host_state)

| 值 | 名称 | 说明 |
|---|---|---|
| 0 | 空闲 (FREE) | 主机空闲，可以使用 |
| 1 | 已锁定 (LOCKED) | 主机已被锁定，准备执行任务 |
| 2 | 已占用 (OCCUPIED) | 主机已被占用，正在执行任务 |
| 3 | 执行中 (RUNNING) | Case 执行中 |
| 4 | 离线 (OFFLINE) | 主机离线 |
| 5 | 待激活 (INACTIVE) | 待激活 |
| 6 | 硬件改动 (HW_CHANGE) | 存在潜在的硬件改动 |
| 7 | 手动停用 (DISABLED) | 手动停用 |
| 8 | 更新中 (UPDATING) | 更新中 |

### 同步状态 (sync_state) - host_hw_rec 表

| 值 | 名称 | 说明 |
|---|---|---|
| 0 | 空状态 (EMPTY) | 空状态 |
| 1 | 待同步 (WAIT) | 待审批/待同步 |
| 2 | 通过 (SUCCESS) | 已审批通过 |
| 3 | 异常 (FAILED) | 异常 |
| 4 | 已审批 (APPROVED) | 已审批（批量审批后的状态） |

### 差异状态 (diff_state) - host_hw_rec 表

| 值 | 名称 | 说明 |
|---|---|---|
| None | 无差异 | 首次上报或无差异 |
| 1 | 版本号变化 (VERSION) | 硬件版本号变化 |
| 2 | 内容更改 (CONTENT) | 硬件内容更改 |
| 3 | 异常 (FAILED) | 对比异常 |

## 🔄 状态流转规则

### 1. 设备登录流程（Auth Service）

#### 1.1 设备登录（传统方式）

**接口**: `POST /api/v1/auth/device/login`

**触发条件**: 设备首次登录或更新登录信息

**请求参数**:
- `mg_id`: 唯一引导ID
- `host_ip`: 主机IP地址
- `username`: 主机账号

**状态变更逻辑**:

```python
# 1. 查询设备记录（根据 mg_id）
host_rec = query_host_rec(mg_id=mg_id, del_flag=0)

# 2. 如果设备已存在
if host_rec:
    # 检查设备是否被停用
    if host_rec.appr_state == 0:
        raise BusinessError("设备已停用，无法登录")
    
    # 更新设备信息
    host_rec.host_ip = host_ip
    host_rec.host_acct = username
    host_rec.updated_time = now()
    host_rec.updated_by = current_user_id  # 从 token 获取
    # host_state 和 appr_state 保持不变

# 3. 如果设备不存在（首次登录）
else:
    # 创建新设备记录
    host_rec = HostRec(
        mg_id=mg_id,
        host_ip=host_ip,
        host_acct=username,
        appr_state=2,  # 存在改动（新增）
        host_state=5,  # 待激活
        subm_time=now(),
        created_by=current_user_id,
        updated_by=current_user_id,
        del_flag=0,
    )

# 4. 生成 JWT Token
access_token = create_access_token({
    "sub": str(host_rec.id),
    "mg_id": mg_id,
    "host_ip": host_ip,
    "username": username,
    "user_type": "device",
})
```

**状态流转图**:
```
首次登录（设备不存在）:
  无记录 → 创建新记录
  host_rec: 新增 (appr_state=2, host_state=5)  # 存在改动 + 待激活

再次登录（设备已存在）:
  host_rec: (appr_state=?, host_state=?) → 不变
  仅更新: host_ip, host_acct, updated_time, updated_by

登录失败（设备已停用）:
  appr_state=0 → 抛出异常 "设备已停用，无法登录"
```

**注意事项**:
- 首次登录时，设备状态为 `appr_state=2, host_state=5`（待激活状态）
- 需要管理员审批后才能使用（审批后变为 `appr_state=1, host_state=0`）
- 再次登录时，只更新设备信息，不改变状态
- 如果设备被停用（`appr_state=0`），无法登录

---

### 2. 硬件上报流程（Agent → Server）

#### 2.1 Agent 上报硬件信息

**接口**: `POST /api/v1/agent/hardware/report`

**触发条件**: Agent 主动上报硬件信息

**状态变更逻辑**:

```python
# 1. 首次上报（无历史记录）
if not current_hw_rec:
    # 插入 host_hw_rec 记录
    sync_state = 1  # 待同步
    diff_state = None  # 无差异
    # host_rec 表不更新状态

# 2. 版本号变化
if current_revision != previous_revision:
    diff_state = 1  # 版本号变化
    # 更新 host_rec 表
    appr_state = 2  # 存在改动
    host_state = 6  # 硬件改动
    # 插入新的 host_hw_rec 记录
    sync_state = 1  # 待同步

# 3. 内容变化（版本号相同但内容不同）
if content_diff:
    diff_state = 2  # 内容更改
    # 更新 host_rec 表
    appr_state = 2  # 存在改动
    host_state = 6  # 硬件改动
    # 插入新的 host_hw_rec 记录
    sync_state = 1  # 待同步

# 4. 无变化
# 不更新任何状态
```

**状态流转图**:
```
首次上报:
  host_rec: (appr_state=?, host_state=?) → 不变
  host_hw_rec: 新增 (sync_state=1, diff_state=None)

版本号变化:
  host_rec: (appr_state=?, host_state=?) → (appr_state=2, host_state=6)
  host_hw_rec: 新增 (sync_state=1, diff_state=1)

内容变化:
  host_rec: (appr_state=?, host_state=?) → (appr_state=2, host_state=6)
  host_hw_rec: 新增 (sync_state=1, diff_state=2)
```

**邮件通知**: 
- 当检测到硬件变更（diff_state = 1 或 2）时，发送邮件通知维护人员
- 邮件包含：host_id, hardware_id, host_ip, 变更类型

---

### 3. 审批流程（管理后台 → Server）

#### 2.1 查询待审批主机列表

**接口**: `GET /api/v1/host/admin/appr-host/list`

**查询条件**:
- `host_state > 4 AND host_state < 8` (5-待激活, 6-硬件改动, 7-手动停用)
- `appr_state != 1` (非启用状态)
- `del_flag = 0` (未删除)

**返回数据**: 待审批主机列表，包含最新的 `diff_state`

---

#### 2.2 查询待审批主机详情

**接口**: `GET /api/v1/host/admin/appr-host/detail`

**查询逻辑**:
- 查询 `host_rec` 表基础信息
- 关联 `host_hw_rec` 表，获取 `sync_state=1` 的记录（按 `created_time` 倒序）
- 密码字段 AES 解密

---

#### 2.3 同意启用主机（审批通过）

**接口**: `POST /api/v1/host/admin/appr-host/approve`

**请求参数**:
- `diff_type`: 变更类型（1-版本号变化, 2-内容变化）
- `host_ids`: 主机ID列表（diff_type=2 时必填；diff_type=1 时可选）

**业务逻辑**:

##### diff_type = 1（版本号变化）

```python
# 如果未传入 host_ids，自动查询
if not host_ids:
    # 查询所有 host_hw_rec 表 sync_state=1, diff_state=1 的 host_id
    host_ids = query_host_ids(sync_state=1, diff_state=1)

# 处理每个 host_id
for host_id in host_ids:
    # 1. 查询 host_hw_rec 表 sync_state=1 的记录
    hw_recs = query_hw_recs(host_id, sync_state=1)
    
    # 2. 最新一条记录
    latest_hw_rec = hw_recs[0]
    latest_hw_rec.sync_state = 2  # 通过
    latest_hw_rec.appr_time = now()
    latest_hw_rec.appr_by = appr_by
    
    # 3. 其他记录
    for hw_rec in hw_recs[1:]:
        hw_rec.sync_state = 4  # 已审批
    
    # 4. 更新 host_rec 表
    host_rec.appr_state = 1  # 启用
    host_rec.host_state = 0  # 空闲
    host_rec.hw_id = latest_hw_rec.id
    host_rec.subm_time = now()
```

##### diff_type = 2（内容变化）

```python
# host_ids 必填
if not host_ids:
    raise BusinessError("host_ids 为必填参数")

# 处理逻辑与 diff_type=1 相同
```

**状态流转图**:
```
审批通过前:
  host_rec: (appr_state=2, host_state=6)
  host_hw_rec: (sync_state=1, diff_state=1或2)

审批通过后:
  host_rec: (appr_state=1, host_state=0)  # 启用 + 空闲
  host_hw_rec[最新]: (sync_state=2, appr_time=now(), appr_by=审批人ID)
  host_hw_rec[其他]: (sync_state=4)  # 已审批
```

**邮件通知**:
- 审批完成后，发送邮件通知维护人员
- 邮件包含：审批人信息、变更的主机信息（hardware_id, host_ip）

---

#### 2.4 停用主机

**接口**: `PUT /api/v1/host/admin/host/disable`

**业务逻辑**:
```python
# 更新 host_rec 表
host_rec.appr_state = 0  # 停用
host_rec.host_state = 7  # 手动停用
```

**状态流转图**:
```
停用前: (appr_state=?, host_state=?)
停用后: (appr_state=0, host_state=7)
```

---

#### 2.5 强制下线主机

**接口**: `POST /api/v1/host/admin/host/force-offline`

**业务逻辑**:
```python
# 更新 host_rec 表
host_rec.host_state = 4  # 离线

# 通知 WebSocket
ws_manager.send_host_offline_notification(host_id)
```

**状态流转图**:
```
下线前: (host_state=?)
下线后: (host_state=4)
```

**WebSocket 通知**:
- 发送 `HOST_OFFLINE_NOTIFICATION` 消息给对应的 Agent
- Agent 收到后更新 `host_exec_log` 表的 `host_state = 4`

---

### 4. WebSocket 状态流转（Agent ↔ Server）

#### 3.1 Agent 连接建立

**触发**: Agent WebSocket 连接成功

**状态变更**:
```python
# 更新 host_rec 表
host_rec.tcp_state = 2  # 监听（连接成功）
```

**消息流程**:
```
Agent → Server: WebSocket 连接建立
Server → Agent: WELCOME 消息
```

---

#### 3.2 心跳更新

**触发**: Agent 定期发送心跳消息

**消息类型**: `HEARTBEAT`

**状态变更**:
```python
# 更新 host_rec 表
host_rec.updated_time = now()  # 自动更新（数据库 onupdate）
host_rec.tcp_state = 2  # 监听（连接正常）
# 不更新 host_state 和 appr_state
```

**心跳超时处理**:
```
1. 检测到超时（60秒无心跳）
2. 发送警告消息 (HEARTBEAT_TIMEOUT_WARNING)
   更新 tcp_state = 1  # 等待/心跳超时
3. 等待 10 秒
4. 如果仍无心跳，主动关闭连接
5. 更新状态:
   - host_rec.tcp_state = 0  # 关闭
   - host_rec.host_state = 4  # 离线
```

---

#### 3.3 Agent 上报连接结果

**触发**: Agent 收到 VNC 连接通知后，上报连接结果

**消息类型**: `CONNECTION_RESULT`

**业务逻辑**:
```python
# 1. 查询 host_exec_log 表
# 条件: host_id = agent_id, host_state = 1, del_flag = 0
exec_log = query_exec_log(host_id, host_state=1)

# 2. 如果找到记录
if exec_log:
    # 更新 host_exec_log 表
    exec_log.host_state = 2  # 已占用
    
    # 下发执行参数给 Agent
    send_message(agent_id, {
        "type": "COMMAND",
        "command": "execute_test_case",
        "tc_id": exec_log.tc_id,
        "cycle_name": exec_log.cycle_name,
        "user_name": exec_log.user_name,
    })
else:
    # 发送错误消息
    send_error_message(agent_id, "未找到待执行任务")
```

**状态流转图**:
```
上报前:
  host_exec_log: (host_state=1)  # 已锁定

上报后:
  host_exec_log: (host_state=2)  # 已占用
  Server → Agent: COMMAND 消息（执行参数）
```

---

#### 3.4 Agent 状态更新

**触发**: Agent 主动上报状态变化

**消息类型**: `STATUS_UPDATE`

**业务逻辑**:
```python
# 解析状态更新消息
status = data.get("status")  # "online", "offline", "error"

# 更新 host_rec 表
if status == "offline":
    host_rec.host_state = 4  # 离线
elif status == "online":
    # 在线状态不需要更新 host_state
    pass
```

---

#### 3.5 Host 下线通知（Server → Agent）

**触发**: 管理后台强制下线主机

**消息类型**: `HOST_OFFLINE_NOTIFICATION`

**业务逻辑**:
```python
# Server 发送消息给 Agent
send_message(agent_id, {
    "type": "HOST_OFFLINE_NOTIFICATION",
    "host_id": host_id,
    "reason": "管理员强制下线",
})

# Agent 收到后（在 _handle_host_offline_notification 中处理）
# 查询 host_exec_log 表最新一条记录
exec_log = query_latest_exec_log(host_id)

# 更新 host_exec_log 表
if exec_log:
    exec_log.host_state = 4  # 离线
```

**状态流转图**:
```
管理后台强制下线:
  host_rec: (host_state=4)  # 离线
  Server → Agent: HOST_OFFLINE_NOTIFICATION
  host_exec_log: (host_state=4)  # 离线
```

---

#### 3.6 VNC 连接成功通知（Server → Agent）

**触发**: 浏览器 VNC 上报连接状态为成功

**接口**: `POST /api/v1/host/browser/vnc/report`

**业务逻辑**:
```python
# 1. 浏览器上报 VNC 连接成功
if vnc_report.connection_status == "success":
    # 2. 创建/更新 host_exec_log 记录
    exec_log = HostExecLog(
        host_state=1,  # 已锁定
        case_state=0,  # 空闲
    )
    
    # 3. 更新 host_rec 表
    host_rec.host_state = 1  # 已锁定
    host_rec.subm_time = now()
    
    # 4. 发送连接通知给 Agent
    send_message(host_id, {
        "type": "CONNECTION_NOTIFICATION",
        "host_id": host_id,
        "message": "VNC连接成功，请开始日志监控",
        "action": "start_log_monitoring",
        "details": {
            "user_id": vnc_report.user_id,
            "tc_id": vnc_report.tc_id,
            "cycle_name": vnc_report.cycle_name,
            "user_name": vnc_report.user_name,
        },
    })
```

**状态流转图**:
```
VNC 连接成功前:
  host_rec: (host_state=?)
  host_exec_log: 无或已删除

VNC 连接成功后:
  host_rec: (host_state=1)  # 已锁定
  host_exec_log: 新增 (host_state=1, case_state=0)
  Server → Agent: CONNECTION_NOTIFICATION
```

---

#### 3.7 Agent 断开连接

**触发**: Agent WebSocket 连接断开

**状态变更**:
```python
# 清理连接记录
del active_connections[agent_id]
del heartbeat_timestamps[agent_id]

# 更新 host_rec 表
host_rec.tcp_state = 0  # 关闭
host_rec.host_state = 4  # 离线（如果之前是在线状态）
```

**状态流转图**:
```
断开前: (tcp_state=2, host_state=?)
断开后: (tcp_state=0, host_state=4)
```

---

### 5. 浏览器插件流程（Browser → Server）

#### 4.1 VNC 连接上报

**接口**: `POST /api/v1/host/browser/vnc/report`

**业务逻辑**:
```python
if connection_status == "success":
    # 1. 逻辑删除旧记录（如果存在）
    if existing_log:
        existing_log.del_flag = 1
    
    # 2. 创建新记录
    new_log = HostExecLog(
        host_state=1,  # 已锁定
        case_state=0,  # 空闲
    )
    
    # 3. 更新 host_rec 表
    host_rec.host_state = 1  # 已锁定
    host_rec.subm_time = now()
    
    # 4. 发送连接通知给 Agent
    send_connection_notification(host_id)
```

**状态流转图**:
```
上报前:
  host_rec: (host_state=?)
  host_exec_log: 无或已删除

上报后:
  host_rec: (host_state=1)  # 已锁定
  host_exec_log: 新增 (host_state=1, case_state=0)
  Server → Agent: CONNECTION_NOTIFICATION
```

---

## 📊 完整状态流转图

### 设备登录 → 审批 → 使用流程

```
1. 设备首次登录
   ↓
2. 创建 host_rec 记录
   (appr_state=2, host_state=5)  # 存在改动 + 待激活
   ↓
3. 设备上报硬件信息
   ↓
4. 检测到硬件变更（可选）
   (appr_state=2, host_state=6)  # 存在改动 + 硬件改动
   ↓
5. 管理后台查询待审批列表
   ↓
6. 管理后台审批通过
   ↓
7. 更新状态: (appr_state=1, host_state=0)  # 启用 + 空闲
   ↓
8. 设备可用（可以执行任务）
```

### 硬件上报 → 审批流程

```
1. Agent 上报硬件信息
   ↓
2. 检测到硬件变更（版本号或内容）
   ↓
3. 更新 host_rec: (appr_state=2, host_state=6)
   插入 host_hw_rec: (sync_state=1, diff_state=1或2)
   发送邮件通知
   ↓
4. 管理后台查询待审批列表
   ↓
5. 管理后台审批通过
   ↓
6. 更新 host_hw_rec[最新]: (sync_state=2, appr_time, appr_by)
   更新 host_hw_rec[其他]: (sync_state=4)
   更新 host_rec: (appr_state=1, host_state=0)
   发送邮件通知
   ↓
7. 主机可用（空闲状态）
```

### VNC 连接 → 任务执行流程

```
1. 浏览器 VNC 连接成功
   ↓
2. 上报连接结果
   ↓
3. 创建 host_exec_log: (host_state=1, case_state=0)
   更新 host_rec: (host_state=1)
   发送 CONNECTION_NOTIFICATION 给 Agent
   ↓
4. Agent 收到通知，上报连接结果
   ↓
5. 更新 host_exec_log: (host_state=2)  # 已占用
   下发执行参数给 Agent
   ↓
6. Agent 执行测试用例
   ↓
7. Agent 上报执行结果
   ↓
8. 更新 host_exec_log: (case_state=2或3)  # 成功或失败
```

### WebSocket 连接生命周期

```
1. Agent 连接建立
   ↓
2. 更新 tcp_state = 2  # 监听
   发送 WELCOME 消息
   ↓
3. 定期心跳更新
   每次心跳: tcp_state = 2, updated_time = now()
   ↓
4. 心跳超时检测（60秒无心跳）
   ↓
5a. 收到心跳 → tcp_state = 2 → 继续连接
5b. 超时无心跳 → tcp_state = 1 → 发送警告 → 等待10秒 → 关闭连接
   ↓
6. 连接断开
   更新 tcp_state = 0  # 关闭
   更新 host_state = 4  # 离线
```

### TCP 状态 (tcp_state) 流转

| 值 | 名称 | 说明 | 触发时机 |
|---|---|---|---|
| 0 | 关闭 (CLOSE) | 连接关闭 | Agent 断开连接、心跳超时关闭 |
| 1 | 等待 (WAIT) | 等待/心跳超时 | 心跳超时警告期间 |
| 2 | 监听 (LISTEN) | 连接正常 | Agent 连接建立、收到心跳 |

---

## 🔍 TCP 状态流转规则

### TCP 状态变更时机

| 操作 | 原状态 | 新状态 | 说明 |
|---|---|---|---|
| Agent 连接建立 | ? | 2 (LISTEN) | WebSocket 连接成功 |
| 收到心跳 | ? | 2 (LISTEN) | 每次收到心跳消息 |
| 心跳超时警告 | 2 | 1 (WAIT) | 60秒无心跳，发送警告 |
| 心跳恢复 | 1 | 2 (LISTEN) | 警告期间收到心跳 |
| 连接关闭 | 1/2 | 0 (CLOSE) | 主动关闭或超时关闭 |

---

## 🔍 关键接口汇总

### 认证相关接口

| 接口 | 方法 | 说明 | 状态变更 |
|---|---|---|---|
| `/api/v1/auth/device/login` | POST | 设备登录（传统方式） | 首次登录: `appr_state=2, host_state=5` |

### 审批相关接口

| 接口 | 方法 | 说明 | 状态变更 |
|---|---|---|---|
| `/api/v1/host/admin/appr-host/list` | GET | 查询待审批主机列表 | 无 |
| `/api/v1/host/admin/appr-host/detail` | GET | 查询待审批主机详情 | 无 |
| `/api/v1/host/admin/appr-host/approve` | POST | 同意启用主机 | `appr_state: 2→1`, `host_state: 6→0` |
| `/api/v1/host/admin/host/disable` | PUT | 停用主机 | `appr_state: ?→0`, `host_state: ?→7` |
| `/api/v1/host/admin/host/force-offline` | POST | 强制下线主机 | `host_state: ?→4` |

### Agent 上报接口

| 接口 | 方法 | 说明 | 状态变更 |
|---|---|---|---|
| `/api/v1/agent/hardware/report` | POST | 上报硬件信息 | 可能触发 `appr_state=2, host_state=6` |
| `/api/v1/agent/testcase/report` | POST | 上报测试用例结果 | 更新 `host_exec_log.case_state` |

### OAuth 2.0 认证接口

| 接口 | 方法 | 说明 | 状态变更 |
|---|---|---|---|
| `/api/v1/oauth2/device/token` | POST | 设备 OAuth 2.0 令牌 | 无（仅生成令牌） |
| `/api/v1/oauth2/admin/token` | POST | 管理员 OAuth 2.0 令牌 | 无（仅生成令牌） |
| `/api/v1/oauth2/introspect` | POST | 令牌内省验证 | 无（仅验证令牌） |

### 浏览器插件接口

| 接口 | 方法 | 说明 | 状态变更 |
|---|---|---|---|
| `/api/v1/host/browser/vnc/report` | POST | 上报 VNC 连接结果 | `host_state: ?→1` |

### WebSocket 消息类型

| 消息类型 | 方向 | 说明 | 状态变更 |
|---|---|---|---|
| `WELCOME` | Server → Agent | 连接建立欢迎消息 | `tcp_state: ?→2` |
| `HEARTBEAT` | Agent → Server | 心跳消息 | 更新 `updated_time` |
| `HEARTBEAT_ACK` | Server → Agent | 心跳确认 | 无 |
| `HEARTBEAT_TIMEOUT_WARNING` | Server → Agent | 心跳超时警告 | 无 |
| `STATUS_UPDATE` | Agent → Server | 状态更新 | 可能更新 `host_state` |
| `CONNECTION_RESULT` | Agent → Server | 连接结果上报 | `host_exec_log.host_state: 1→2` |
| `CONNECTION_NOTIFICATION` | Server → Agent | VNC 连接成功通知 | 无（触发 Agent 上报） |
| `COMMAND` | Server → Agent | 执行命令 | 无 |
| `HOST_OFFLINE_NOTIFICATION` | Server → Agent | Host 下线通知 | `host_exec_log.host_state: ?→4` |

---

## 📝 状态查询规则

### 可用主机列表

**接口**: `GET /api/v1/host/admin/host/list`

**查询条件**:
- `host_state = 0` (空闲)
- `appr_state = 1` (启用)
- `del_flag = 0` (未删除)

**说明**: 只有审批通过且空闲的主机才会出现在可用列表中

### 待审批主机列表

**接口**: `GET /api/v1/host/admin/appr-host/list`

**查询条件**:
- `host_state > 4 AND host_state < 8` (5-待激活, 6-硬件改动, 7-手动停用)
- `appr_state != 1` (非启用状态)
- `del_flag = 0` (未删除)

**说明**: 
- 包括首次登录的设备（`host_state=5, appr_state=2`）
- 包括硬件变更的设备（`host_state=6, appr_state=2`）
- 包括手动停用的设备（`host_state=7, appr_state=0`）

---

## ⚠️ 注意事项

1. **状态一致性**: 
   - `host_rec.host_state` 和 `host_exec_log.host_state` 可能不同步
   - `host_rec.host_state` 表示主机整体状态
   - `host_exec_log.host_state` 表示执行日志中的主机状态
   - 两个状态字段独立管理，用于不同的业务场景

2. **设备登录流程**:
   - 首次登录时，设备状态为 `appr_state=2, host_state=5`（待激活状态）
   - 需要管理员审批后才能使用（审批后变为 `appr_state=1, host_state=0`）
   - 再次登录时，只更新设备信息（host_ip, host_acct），不改变状态
   - 如果设备被停用（`appr_state=0`），无法登录

3. **审批流程**:
   - 待审批列表包括：首次登录的设备（`host_state=5`）、硬件变更的设备（`host_state=6`）、手动停用的设备（`host_state=7`）
   - 查询条件：`host_state > 4 AND host_state < 8, appr_state != 1`
   - 审批通过后，主机状态变为 `appr_state=1, host_state=0`（可用状态）
   - 审批时会更新 `host_hw_rec` 表的 `sync_state` 和 `appr_time`、`appr_by`

4. **WebSocket 超时**:
   - 心跳超时时间：60秒
   - 警告等待时间：10秒
   - 总超时时间：70秒

5. **邮件通知**:
   - 硬件变更时自动发送邮件
   - 审批通过后发送邮件
   - 邮件发送失败不影响主流程

6. **状态更新时机**:
   - WebSocket 更新不设置 `updated_by`
   - WebSocket 更新不手动设置 `updated_time`（由数据库自动更新）

---

8. **设备登录与硬件上报的关系**:
   - 设备登录：创建/更新 `host_rec` 记录，设置初始状态
   - 硬件上报：创建/更新 `host_hw_rec` 记录，可能触发状态变更
   - 两者可以独立进行，但通常设备登录在前，硬件上报在后
   - 首次登录的设备需要审批后才能使用，硬件变更的设备也需要审批

---

## 🔗 相关文件

- `services/host-service/app/constants/host_constants.py` - 状态常量定义
- `services/auth-service/app/services/auth_service.py` - 认证服务（设备登录）
- `services/host-service/app/services/admin_appr_host_service.py` - 审批服务
- `services/host-service/app/services/agent_report_service.py` - Agent 上报服务
- `services/host-service/app/services/agent_websocket_manager.py` - WebSocket 管理
- `services/host-service/app/services/browser_vnc_service.py` - VNC 服务
- `services/host-service/app/services/browser_host_service.py` - 浏览器主机服务

---

**最后更新**: 2025-01-30
**版本**: 1.1
**更新内容**:
- 新增设备登录流程的状态流转规则
- 新增设备登录 → 审批 → 使用的完整流程
- 补充 OAuth 2.0 认证接口说明
- 完善注意事项和设备登录相关说明

