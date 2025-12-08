# WebSocket 消息类型完整文档

## 📋 概述

本文档描述了 Intel EC 微服务系统中 Agent WebSocket 连接支持的所有消息类型，包括消息格式、使用场景和示例。

### 消息基础格式

所有消息都继承自 `BaseMessage`，包含以下基础字段：

```json
{
  "type": "消息类型",
  "timestamp": "2025-01-29T10:00:00Z",
  "message_id": "可选的消息ID，用于追踪"
}
```

### 重要说明

- **agent_id 获取方式**:
  - `agent_id` **不是** Agent 在消息中传入的，而是服务器在 WebSocket 连接建立时从 JWT token 中解析出来的 `host_id`
  - 连接建立时，服务器会验证 token 并提取 `host_id`（即 `agent_id`），存储在连接上下文中
  - 所有 Agent → Server 的消息中，`agent_id` 字段都是**可选的**，即使传递了也会被忽略
  - 系统会自动从连接上下文获取 `agent_id`，用于消息处理和路由
- **消息方向**:
  - `Server → Agent`: 服务器主动发送给 Agent
  - `Agent → Server`: Agent 主动发送给服务器
- **消息处理**: 所有消息都通过 `AgentWebSocketManager.handle_message(agent_id, data)` 方法路由到对应的处理器，其中 `agent_id` 来自连接上下文。

---

## 🔌 连接管理消息

### 1. WELCOME - 欢迎消息

**方向**: `Server → Agent`  
**触发时机**: WebSocket 连接建立后自动发送  
**用途**: 通知 Agent 连接已成功建立

#### 消息格式

```json
{
  "type": "welcome",
  "agent_id": "123456",
  "message": "WebSocket 连接已建立",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"welcome"` |
| `agent_id` | string | 是 | Agent ID（即 host_id） |
| `message` | string | 是 | 欢迎消息内容 |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 示例

```json
{
  "type": "welcome",
  "agent_id": "1846557388006625421",
  "message": "WebSocket 连接已建立",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

- 连接建立后，服务器自动发送此消息
- Agent 收到后可以确认连接已建立
- 同时更新 `host_rec` 表的 `tcp_state = 2`（监听/连接正常）

---

### 2. HEARTBEAT - 心跳消息

**方向**: `Agent → Server`  
**触发时机**: Agent 定期发送（建议每 30-60 秒）  
**用途**: 保持连接活跃，检测连接状态

#### 消息格式

```json
{
  "type": "heartbeat",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"heartbeat"` |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

**注意**: `agent_id` 不需要在消息中传递，系统会自动从连接上下文获取（来自连接时的 token）。

#### 示例

```json
{
  "type": "heartbeat",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

1. 更新内存中的心跳时间戳
2. 如果之前发送过心跳超时警告，清除警告记录
3. 更新 `host_rec` 表的 `tcp_state = 2`（连接正常）
4. 更新 `host_rec` 表的 `updated_time`（心跳时间）
5. 服务器返回 `HEARTBEAT_ACK` 确认消息

#### 心跳超时机制

- **超时时间**: 60 秒无心跳
- **警告机制**: 超时后发送 `HEARTBEAT_TIMEOUT_WARNING`
- **等待时间**: 警告后等待 10 秒
- **断开连接**: 如果 10 秒内仍未收到心跳，自动断开连接

---

### 3. HEARTBEAT_ACK - 心跳确认

**方向**: `Server → Agent`  
**触发时机**: 服务器收到 `HEARTBEAT` 消息后自动发送  
**用途**: 确认心跳消息已接收

#### 消息格式

```json
{
  "type": "heartbeat_ack",
  "message": "心跳已接收",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"heartbeat_ack"` |
| `message` | string | 是 | 确认消息内容 |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 示例

```json
{
  "type": "heartbeat_ack",
  "message": "心跳已接收",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

---

## 📊 状态管理消息

### 4. STATUS_UPDATE - 状态更新

**方向**: `Agent → Server`  
**触发时机**: Agent 状态发生变化时  
**用途**: 更新 Agent 的运行状态

#### 消息格式

```json
{
  "type": "status_update",
  "status": "online",
  "details": {
    "cpu_usage": 45.2,
    "memory_usage": 60.5
  },
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"status_update"` |
| `status` | string | 是 | 状态值: `online` / `offline` / `busy` / `error` |
| `details` | object | 否 | 状态详情（可选） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

**注意**: `agent_id` 不需要在消息中传递，系统会自动从连接上下文获取（来自连接时的 token）。

#### 状态值说明

| 状态值 | 说明 | 数据库映射 |
|--------|------|-----------|
| `online` | 在线/空闲 | `host_state = 0` |
| `offline` | 离线 | `host_state = 4` |
| `busy` | 忙碌 | `host_state = 2` |
| `error` | 错误 | `host_state = 8` |

#### 示例

```json
{
  "type": "status_update",
  "status": "online",
  "details": {
    "cpu_usage": 45.2,
    "memory_usage": 60.5,
    "disk_usage": 75.0
  },
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

1. 更新 `host_rec` 表的 `host_state` 字段
2. 服务器返回 `STATUS_UPDATE_ACK` 确认消息

---

### 5. STATUS_UPDATE_ACK - 状态更新确认

**方向**: `Server → Agent`  
**触发时机**: 服务器处理完 `STATUS_UPDATE` 消息后自动发送  
**用途**: 确认状态更新已处理

#### 消息格式

```json
{
  "type": "status_update_ack",
  "message": "状态更新成功",
  "status": "online",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"status_update_ack"` |
| `message` | string | 是 | 确认消息内容 |
| `status` | string | 是 | 更新后的状态值 |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 示例

```json
{
  "type": "status_update_ack",
  "message": "状态更新成功",
  "status": "online",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

---

## ⚙️ 命令执行消息

### 6. COMMAND - 执行命令

**方向**: `Server → Agent`  
**触发时机**: 服务器需要 Agent 执行特定命令时  
**用途**: 下发命令给 Agent 执行

#### 消息格式

```json
{
  "type": "command",
  "command_id": "cmd-20250129-001",
  "command": "execute_test_case",
  "args": {
    "tc_id": "TC001",
    "cycle_name": "Cycle1",
    "user_name": "test_user"
  },
  "target_agents": null,
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"command"` |
| `command_id` | string | 是 | 命令唯一标识符 |
| `command` | string | 是 | 命令名称 |
| `args` | object | 否 | 命令参数（可选） |
| `target_agents` | array | 否 | 目标 Agent 列表（`null` 表示所有） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 常用命令

| 命令名称 | 说明 | 参数 |
|---------|------|------|
| `execute_test_case` | 执行测试用例 | `tc_id`, `cycle_name`, `user_name` |
| `stop_test_case` | 停止测试用例 | `tc_id` |
| `restart_agent` | 重启 Agent | 无 |

#### 示例

**执行测试用例命令**:
```json
{
  "type": "command",
  "command_id": "cmd-20250129-001",
  "command": "execute_test_case",
  "args": {
    "tc_id": "TC001",
    "cycle_name": "Cycle1",
    "user_name": "test_user"
  },
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

**停止测试用例命令**:
```json
{
  "type": "command",
  "command_id": "cmd-20250129-002",
  "command": "stop_test_case",
  "args": {
    "tc_id": "TC001"
  },
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

---

### 7. COMMAND_RESPONSE - 命令响应

**方向**: `Agent → Server`  
**触发时机**: Agent 执行完命令后  
**用途**: 返回命令执行结果

#### 消息格式

```json
{
  "type": "command_response",
  "command_id": "cmd-20250129-001",
  "success": true,
  "result": {
    "output": "测试用例执行完成",
    "exit_code": 0
  },
  "error": null,
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"command_response"` |
| `command_id` | string | 是 | 对应的命令ID |
| `success` | boolean | 是 | 命令是否执行成功 |
| `result` | object | 否 | 命令执行结果（成功时） |
| `error` | string | 否 | 错误信息（失败时） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

**注意**: `agent_id` 不需要在消息中传递，系统会自动从连接上下文获取（来自连接时的 token）。

#### 示例

**成功响应**:
```json
{
  "type": "command_response",
  "command_id": "cmd-20250129-001",
  "success": true,
  "result": {
    "output": "测试用例执行完成",
    "exit_code": 0,
    "duration": 120.5
  },
  "timestamp": "2025-01-29T10:02:00.123456Z"
}
```

**失败响应**:
```json
{
  "type": "command_response",
  "command_id": "cmd-20250129-001",
  "success": false,
  "error": "测试用例执行失败: 超时",
  "timestamp": "2025-01-29T10:02:00.123456Z"
}
```

---

### 8. CONNECTION_RESULT - 连接结果上报

**方向**: `Agent → Server`  
**触发时机**: Agent 收到 `CONNECTION_NOTIFICATION` 后，上报连接结果  
**用途**: 上报 VNC 连接结果，触发测试用例执行

#### 消息格式

```json
{
  "type": "connection_result",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"connection_result"` |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

**注意**: `agent_id` 不需要在消息中传递，系统会自动从连接上下文获取（来自连接时的 token）。服务器会使用该 `agent_id` 查询 `host_exec_log` 表。

#### 示例

```json
{
  "type": "connection_result",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

1. 服务器从连接上下文获取 `agent_id`（来自连接时的 token）
2. 查询 `host_exec_log` 表:
   - 条件: `host_id = agent_id`, `host_state = 1`（已锁定）, `del_flag = 0`
   - 获取最新一条记录（按 `created_at` 降序）
3. 如果记录存在:
   - 更新 `host_state = 2`（已占用）
   - 提取 `tc_id`, `cycle_name`, `user_name`
   - 下发执行参数给 Agent（通过 `COMMAND` 消息）
4. 如果记录不存在:
   - 发送错误消息: `"未找到待执行任务，请先通过 VNC 上报连接结果"`

---

## 🔔 系统消息

### 9. NOTIFICATION - 系统通知

**方向**: `Server → Agent` / `Server → Broadcast`  
**触发时机**: 服务器需要通知 Agent 时  
**用途**: 发送系统通知给单个 Agent 或所有 Agent

#### 消息格式

```json
{
  "type": "notification",
  "title": "系统维护通知",
  "content": "系统将于今晚 22:00 进行维护，预计持续 1 小时",
  "level": "info",
  "data": {
    "maintenance_start": "2025-01-29T22:00:00Z",
    "maintenance_duration": 3600
  },
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"notification"` |
| `title` | string | 是 | 通知标题 |
| `content` | string | 是 | 通知内容 |
| `level` | string | 是 | 通知级别: `info` / `warning` / `error` / `critical` |
| `data` | object | 否 | 附加数据（可选） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 通知级别

| 级别 | 说明 | 使用场景 |
|------|------|---------|
| `info` | 信息 | 一般通知、状态更新 |
| `warning` | 警告 | 需要注意但不影响运行 |
| `error` | 错误 | 操作失败、配置错误 |
| `critical` | 严重 | 系统故障、需要立即处理 |

#### 示例

**信息通知**:
```json
{
  "type": "notification",
  "title": "系统更新",
  "content": "系统已更新到版本 1.2.0",
  "level": "info",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

**警告通知**:
```json
{
  "type": "notification",
  "title": "资源使用警告",
  "content": "磁盘使用率已达到 85%",
  "level": "warning",
  "data": {
    "disk_usage": 85.0,
    "threshold": 80.0
  },
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

---

### 10. ERROR - 错误消息

**方向**: `Server → Agent`  
**触发时机**: 服务器处理消息时发生错误  
**用途**: 通知 Agent 发生了错误

#### 消息格式

```json
{
  "type": "error",
  "message": "消息处理失败",
  "error_code": "INVALID_MESSAGE_FORMAT",
  "details": {
    "field": "version",
    "reason": "版本号格式无效"
  },
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"error"` |
| `message` | string | 是 | 错误消息内容 |
| `error_code` | string | 否 | 错误码（可选） |
| `details` | object | 否 | 错误详情（可选） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 常见错误码

| 错误码 | 说明 |
|--------|------|
| `INVALID_MESSAGE_FORMAT` | 消息格式无效 |
| `UNKNOWN_MESSAGE_TYPE` | 未知消息类型 |
| `MESSAGE_PROCESSING_FAILED` | 消息处理失败 |
| `HOST_NOT_FOUND` | 主机不存在 |
| `CONNECTION_RESULT_NOT_FOUND` | 未找到连接结果 |

#### 示例

```json
{
  "type": "error",
  "message": "版本更新失败，主机不存在或已被删除",
  "error_code": "HOST_NOT_FOUND",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

---

### 11. HEARTBEAT_TIMEOUT_WARNING - 心跳超时警告

**方向**: `Server → Agent`  
**触发时机**: 60 秒内未收到心跳消息  
**用途**: 警告 Agent 心跳超时，需要在 10 秒内发送心跳

#### 消息格式

```json
{
  "type": "heartbeat_timeout_warning",
  "message": "心跳超时警告，请在 10 秒内发送心跳，否则连接将被关闭",
  "timeout": 60,
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"heartbeat_timeout_warning"` |
| `message` | string | 是 | 警告消息内容 |
| `timeout` | integer | 是 | 心跳超时时间（秒） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 示例

```json
{
  "type": "heartbeat_timeout_warning",
  "message": "心跳超时警告，请在 10 秒内发送心跳，否则连接将被关闭",
  "timeout": 60,
  "timestamp": "2025-01-29T10:01:00.123456Z"
}
```

#### 业务逻辑

1. 更新 `host_rec` 表的 `tcp_state = 1`（等待/心跳超时）
2. Agent 收到警告后，应在 10 秒内发送心跳
3. 如果 10 秒内收到心跳，清除警告，恢复正常
4. 如果 10 秒内仍未收到心跳，自动断开连接

---

### 12. HOST_OFFLINE_NOTIFICATION - Host 下线通知

**方向**: `Server → Agent`  
**触发时机**: 服务器检测到 Host 下线时  
**用途**: 通知 Agent 其 Host 已下线，需要更新执行日志状态

#### 消息格式

```json
{
  "type": "host_offline_notification",
  "host_id": "123456",
  "message": "Host已下线",
  "reason": "连接超时",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"host_offline_notification"` |
| `host_id` | string | 是 | Host ID |
| `message` | string | 是 | 下线消息内容 |
| `reason` | string | 否 | 下线原因（可选） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 示例

```json
{
  "type": "host_offline_notification",
  "host_id": "1846557388006625421",
  "message": "Host已下线",
  "reason": "心跳超时，连接已关闭",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

1. 查询 `host_exec_log` 表:
   - 条件: `host_id = 消息中的host_id`, `del_flag = 0`
   - 获取最新一条记录（按 `created_time` 降序）
2. 如果记录存在且 `host_state != 3`（执行中）:
   - 更新 `host_state = 4`（离线）
   - 更新 `tcp_state = 0`（关闭）
3. 如果 `host_state == 3`（执行中）:
   - 不更新 `host_state`（保持执行中状态）
   - 仍然更新 `tcp_state = 0`（关闭）

---

### 13. CONNECTION_NOTIFICATION - 连接通知

**方向**: `Server → Agent`  
**触发时机**: 浏览器 VNC 连接成功时  
**用途**: 通知 Agent 开始日志监控

#### 消息格式

```json
{
  "type": "connection_notification",
  "host_id": "123456",
  "message": "VNC连接成功，请开始日志监控",
  "action": "start_log_monitoring",
  "details": {
    "user_id": "user123",
    "tc_id": "TC001",
    "cycle_name": "Cycle1"
  },
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"connection_notification"` |
| `host_id` | string | 是 | Host ID |
| `message` | string | 是 | 通知消息内容 |
| `action` | string | 是 | 操作类型（目前固定为 `"start_log_monitoring"`） |
| `details` | object | 否 | 附加信息（可选） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

#### 示例

```json
{
  "type": "connection_notification",
  "host_id": "1846557388006625421",
  "message": "VNC连接成功，请开始日志监控",
  "action": "start_log_monitoring",
  "details": {
    "user_id": "user123",
    "tc_id": "TC001",
    "cycle_name": "Cycle1",
    "user_name": "test_user"
  },
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

1. Agent 收到此消息后，应开始监控日志
2. Agent 监控到连接结果后，发送 `CONNECTION_RESULT` 消息
3. 服务器收到 `CONNECTION_RESULT` 后，下发测试用例执行参数

---

### 14. VERSION_UPDATE - 版本更新

**方向**: `Agent → Server`  
**触发时机**: Agent 启动时或版本更新后  
**用途**: 上报 Agent 当前版本号，更新数据库

#### 消息格式

```json
{
  "type": "version_update",
  "version": "1.0.0",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值: `"version_update"` |
| `version` | string | 是 | Agent 版本号（最大长度 10 个字符） |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |

**注意**: `agent_id` 从 WebSocket 连接时的 token 中获取，不需要在消息中传递。

#### 示例

```json
{
  "type": "version_update",
  "version": "1.0.0",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

#### 业务逻辑

1. 验证版本号长度（最大 10 个字符，超长自动截断）
2. 更新 `host_rec` 表的 `agent_ver` 字段
3. 服务器返回 `STATUS_UPDATE_ACK` 确认消息（包含版本号）

#### 响应示例

```json
{
  "type": "status_update_ack",
  "message": "版本更新成功",
  "version": "1.0.0",
  "timestamp": "2025-01-29T10:00:00.123456Z"
}
```

---

## 📝 消息处理流程

### Agent 连接流程

```
1. Agent 建立 WebSocket 连接（携带 JWT token）
   ↓
2. Server 验证 token，从 token 中提取 host_id（即 agent_id）
   ↓
3. Server 将 host_id 存储在连接上下文中
   ↓
4. Server 发送 WELCOME 消息（包含 agent_id）
   ↓
5. Agent 发送 VERSION_UPDATE 消息（可选，不需要包含 agent_id）
   ↓
6. Agent 开始定期发送 HEARTBEAT 消息（不需要包含 agent_id）
   ↓
7. Server 响应 HEARTBEAT_ACK（使用连接上下文中的 agent_id）
```

### 测试用例执行流程

```
1. 浏览器 VNC 连接成功
   ↓
2. Server 发送 CONNECTION_NOTIFICATION 给 Agent
   ↓
3. Agent 开始监控日志
   ↓
4. Agent 发送 CONNECTION_RESULT 消息
   ↓
5. Server 查询 host_exec_log，更新 host_state = 2
   ↓
6. Server 发送 COMMAND 消息（执行测试用例）
   ↓
7. Agent 执行测试用例
   ↓
8. Agent 发送 COMMAND_RESPONSE 消息（执行结果）
```

### 心跳超时处理流程

```
1. 60 秒内未收到心跳
   ↓
2. Server 发送 HEARTBEAT_TIMEOUT_WARNING
   ↓
3. Server 更新 tcp_state = 1（等待）
   ↓
4. 等待 10 秒
   ↓
5a. 收到心跳 → 清除警告，恢复正常
5b. 未收到心跳 → 断开连接，更新 tcp_state = 0
```

---

## 🔧 消息发送示例

### Python 客户端示例

```python
import asyncio
import websockets
import json
from datetime import datetime, timezone

async def agent_client():
    """Agent WebSocket 客户端示例"""
    uri = "ws://localhost:8003/ws/agent/123456?token=your_jwt_token"
    
    async with websockets.connect(uri) as websocket:
        # 1. 接收欢迎消息
        welcome = await websocket.recv()
        print(f"收到欢迎消息: {welcome}")
        
        # 2. 发送版本更新
        version_msg = {
            "type": "version_update",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(version_msg))
        
        # 3. 定期发送心跳
        async def heartbeat():
            while True:
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await websocket.send(json.dumps(heartbeat_msg))
                await asyncio.sleep(30)  # 每 30 秒发送一次
        
        # 4. 接收消息
        async def receive_messages():
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"收到消息: {data}")
                
                # 处理不同类型的消息
                if data["type"] == "command":
                    # 执行命令
                    response = {
                        "type": "command_response",
                        "command_id": data["command_id"],
                        "success": True,
                        "result": {"output": "命令执行完成"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send(json.dumps(response))
        
        # 并发执行心跳和消息接收
        await asyncio.gather(
            heartbeat(),
            receive_messages()
        )

# 运行客户端
asyncio.run(agent_client())
```

### JavaScript 客户端示例

```javascript
// Agent WebSocket 客户端示例
const token = 'your_jwt_token';
const hostId = '123456';
const ws = new WebSocket(`ws://localhost:8003/ws/agent/${hostId}?token=${token}`);

ws.onopen = () => {
    console.log('WebSocket 连接已建立');
    
    // 发送版本更新
    ws.send(JSON.stringify({
        type: 'version_update',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    }));
    
    // 定期发送心跳
    setInterval(() => {
        ws.send(JSON.stringify({
            type: 'heartbeat',
            timestamp: new Date().toISOString()
        }));
    }, 30000); // 每 30 秒发送一次
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);
    
    // 处理不同类型的消息
    switch (message.type) {
        case 'welcome':
            console.log('收到欢迎消息:', message.message);
            break;
            
        case 'command':
            // 执行命令
            const response = {
                type: 'command_response',
                command_id: message.command_id,
                success: true,
                result: { output: '命令执行完成' },
                timestamp: new Date().toISOString()
            };
            ws.send(JSON.stringify(response));
            break;
            
        case 'heartbeat_ack':
            console.log('心跳确认');
            break;
            
        case 'heartbeat_timeout_warning':
            console.warn('心跳超时警告:', message.message);
            // 立即发送心跳
            ws.send(JSON.stringify({
                type: 'heartbeat',
                timestamp: new Date().toISOString()
            }));
            break;
            
        default:
            console.log('未知消息类型:', message.type);
    }
};

ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
    console.log('WebSocket 连接已关闭');
};
```

---

## 📊 消息类型汇总表

| 消息类型 | 方向 | 处理器 | 说明 |
|---------|------|--------|------|
| `welcome` | Server → Agent | 自动发送 | 连接建立欢迎消息 |
| `heartbeat` | Agent → Server | `_handle_heartbeat` | 心跳消息 |
| `heartbeat_ack` | Server → Agent | 自动发送 | 心跳确认 |
| `status_update` | Agent → Server | `_handle_status_update` | 状态更新 |
| `status_update_ack` | Server → Agent | 自动发送 | 状态更新确认 |
| `command` | Server → Agent | - | 执行命令 |
| `command_response` | Agent → Server | `_handle_command_response` | 命令响应 |
| `connection_result` | Agent → Server | `_handle_connection_result` | 连接结果上报 |
| `notification` | Server → Agent | - | 系统通知 |
| `error` | Server → Agent | 自动发送 | 错误消息 |
| `heartbeat_timeout_warning` | Server → Agent | 自动发送 | 心跳超时警告 |
| `host_offline_notification` | Server → Agent | `_handle_host_offline_notification` | Host下线通知 |
| `connection_notification` | Server → Agent | - | 连接通知 |
| `version_update` | Agent → Server | `_handle_version_update` | 版本更新 |

---

## 🚨 注意事项

### 1. agent_id 获取方式

- **重要**: `agent_id` **不是** Agent 在消息中传入的，而是服务器在连接建立时从 JWT token 中解析出来的
- **连接建立流程**:
  1. Agent 建立 WebSocket 连接时携带 JWT token（通过查询参数 `?token=xxx` 或请求头）
  2. 服务器验证 token 并提取 `host_id`（即 `agent_id`）
  3. 服务器将 `host_id` 存储在连接上下文中
  4. 所有后续消息处理都使用连接上下文中的 `agent_id`
- **消息格式**: 所有 Agent → Server 的消息中，`agent_id` 字段都是**可选的**，即使传递了也会被忽略
- **系统行为**: 系统会自动从连接上下文获取 `agent_id`，用于消息路由和处理

### 2. 消息格式验证

- 所有消息必须包含 `type` 字段
- `timestamp` 字段会自动生成（如果未提供）
- 消息必须符合对应的消息类型定义

### 3. 错误处理

- 如果消息格式错误，服务器会发送 `ERROR` 消息
- 如果消息类型未知，服务器会发送 `ERROR` 消息
- Agent 应该处理所有可能的错误情况

### 4. 心跳机制

- Agent 应该每 30-60 秒发送一次心跳
- 如果 60 秒内未收到心跳，服务器会发送警告
- 警告后 10 秒内仍未收到心跳，连接会被关闭

### 5. 连接管理

- 每个 `host_id` 只能有一个活跃连接
- 如果新连接建立，旧连接会被自动断开
- 连接断开时，会自动更新 `tcp_state = 0`

---

## 📚 相关文档

- [WebSocket 使用指南](./18-websocket-usage.md) - WebSocket 连接和使用详细说明
- [WebSocket 连接断开逻辑](./31-websocket-connection-disconnection-logic.md) - 连接生命周期管理
- [API 端点文档](../services/host-service/app/api/v1/endpoints/agent_websocket.py) - WebSocket 端点定义

---

**最后更新**: 2025-01-29  
**版本**: 1.0.0  
**维护者**: Intel EC 开发团队
