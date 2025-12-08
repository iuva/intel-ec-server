# WebSocket 连接和断线处理逻辑文档

## 概述

本文档详细说明 `websocket_endpoint_new` 端点的连接处理逻辑、断线处理逻辑，以及涉及的数据表和字段。

## 端点信息

### 基本信息

- **端点路径**: `/ws/host`
- **端点函数**: `websocket_endpoint_new`
- **处理函数**: `_handle_websocket_connection`
- **文件位置**: `services/host-service/app/api/v1/endpoints/agent_websocket.py`

## 连接处理逻辑

### 1. 认证阶段

#### 1.1 获取 host_id

支持两种认证方式：

#### 方式一：网关传递（推荐）

- 从查询参数获取：`websocket.query_params.get("host_id")`
- 网关已验证 token，直接使用传递的 `host_id`

#### 方式二：直接连接（兼容）

- 从 JWT token 中验证并提取 `host_id`
- 调用 `verify_websocket_token(websocket)` 验证 token
- 从 `user_info.get("user_id")` 获取 `host_id`（实际是 `host_rec.id`）

#### 1.2 认证失败处理

- 如果认证失败，调用 `handle_websocket_auth_error()` 返回错误消息
- 不建立 WebSocket 连接，直接返回

### 2. 连接建立阶段

#### 2.1 接受连接

```python
await websocket.accept()
```

#### 2.2 注册连接

调用 `ws_manager.connect(host_id, websocket)` 注册连接：

**连接管理器处理逻辑**：

1. **检查连接数限制**
   - 如果连接数 >= `max_connections`（默认 1000），拒绝连接
   - 返回错误码 `1008`，原因："服务器连接数已达上限"

2. **处理重复连接**
   - 如果同一个 `host_id` 已有连接，先断开旧连接
   - 调用 `disconnect(host_id)` 断开旧连接

3. **建立新连接**
   - 将连接添加到 `active_connections` 字典：`{host_id: websocket}`
   - 初始化心跳时间戳：`heartbeat_timestamps[host_id] = datetime.now(timezone.utc)`

4. **发送欢迎消息**
   - 消息类型：`MessageType.WELCOME`
   - 包含：`agent_id`、`message`、`timestamp`

5. **更新数据库状态**
   - 调用 `host_service.update_tcp_state(host_id, tcp_state=2)`
   - 更新 `host_rec` 表的 `tcp_state` 字段为 `2`（监听/连接建立）

### 3. 消息处理阶段

#### 3.1 消息循环

```python
while True:
    data = await websocket.receive_json()
    await ws_manager.handle_message(host_id, data)
```

#### 3.2 支持的消息类型

- `HEARTBEAT`: 心跳消息
- `STATUS_UPDATE`: 状态更新消息
- `COMMAND_RESPONSE`: 命令响应消息
- `CONNECTION_RESULT`: Agent 上报连接结果
- `HOST_OFFLINE_NOTIFICATION`: Host 下线通知

#### 3.3 心跳处理

**心跳接收**：

- 更新内存中的心跳时间戳：`heartbeat_timestamps[agent_id] = datetime.now(timezone.utc)`
- 如果之前发送过警告，清除警告记录
- 更新 TCP 状态为 `2`（连接正常）
- 调用 `host_service.update_heartbeat_silent(agent_id)` 更新数据库心跳时间
- 发送心跳确认消息：`MessageType.HEARTBEAT_ACK`

**心跳检测**：

- 统一心跳检查任务每 10 秒检查一次所有连接
- 心跳超时时间：60 秒
- 警告等待时间：10 秒

**心跳超时处理流程**：

1. 首次检测到超时（> 60 秒）：
   - 发送心跳超时警告：`MessageType.HEARTBEAT_TIMEOUT_WARNING`
   - 更新 TCP 状态为 `1`（等待/心跳超时）
   - 记录警告时间：`_heartbeat_warning_sent[agent_id] = datetime.now(timezone.utc)`

2. 警告后仍未恢复（警告后 > 10 秒）：
   - 关闭连接：调用 `disconnect(agent_id)`

## 断线处理逻辑

### 1. 正常断开（WebSocketDisconnect）

```python
except WebSocketDisconnect:
    logger.info(f"WebSocket 正常断开: {host_id}")
    if host_id in ws_manager.active_connections:
        await ws_manager.disconnect(host_id)
```

### 2. 异常断开（Exception）

```python
except Exception as e:
    logger.error(f"WebSocket 异常: {host_id}, 错误: {e!s}")
    if host_id in ws_manager.active_connections:
        await ws_manager.disconnect(host_id)
```

### 3. disconnect() 方法处理逻辑

#### 3.1 防重复断开机制

- 使用 `_disconnecting` 集合标记正在断开的连接
- 使用 `_disconnect_locks` 字典为每个连接创建锁
- 双重检查：检查是否正在断开，避免重复调用

#### 3.2 清理连接资源

1. **从连接字典移除**

   ```python
   if agent_id in self.active_connections:
       websocket = self.active_connections[agent_id]
       del self.active_connections[agent_id]
   ```

2. **清理心跳相关数据**
   - 删除心跳时间戳：`del self.heartbeat_timestamps[agent_id]`
   - 删除警告记录：`del self._heartbeat_warning_sent[agent_id]`

3. **关闭 WebSocket 连接**
   - 检查连接状态：`websocket.client_state`
   - 如果状态为 `CONNECTED`，调用 `websocket.close(code=1008, reason="心跳超时，连接已关闭")`
   - 如果状态为 `DISCONNECTED`，跳过关闭操作

#### 3.3 更新数据库状态

1. **更新 TCP 状态**

   ```python
   await self.host_service.update_tcp_state(agent_id, tcp_state=0)
   ```

   - 更新 `host_rec` 表的 `tcp_state` 字段为 `0`（关闭/连接断开）

2. **更新主机状态**

   ```python
   await self.host_service.update_host_status(agent_id, HostStatusUpdate(status="offline"))
   ```

   - 更新 `host_rec` 表的 `host_state` 字段为 `4`（离线）

#### 3.4 清理断开标记

```python
finally:
    self._disconnecting.discard(agent_id)
    if agent_id in self._disconnect_locks:
        del self._disconnect_locks[agent_id]
```

## 涉及的数据表和字段

### 1. host_rec 表（主机记录表）

#### 连接时更新的字段

| 字段名 | 类型 | 说明 | 更新值 | 更新时机 |
|--------|------|------|--------|----------|
| `tcp_state` | SmallInteger | TCP在线状态 | `2` (监听/连接建立) | 连接建立后 |
| `updated_time` | DateTime | 更新时间 | `CURRENT_TIMESTAMP` | 自动更新（ON UPDATE） |

#### 断线时更新的字段

| 字段名 | 类型 | 说明 | 更新值 | 更新时机 |
|--------|------|------|--------|----------|
| `tcp_state` | SmallInteger | TCP在线状态 | `0` (关闭/连接断开) | 断线时 |
| `host_state` | SmallInteger | 主机状态 | `4` (离线) | 断线时 |
| `updated_time` | DateTime | 更新时间 | `CURRENT_TIMESTAMP` | 自动更新（ON UPDATE） |

#### 心跳时更新的字段

| 字段名 | 类型 | 说明 | 更新值 | 更新时机 |
|--------|------|------|--------|----------|
| `updated_time` | DateTime | 更新时间 | `CURRENT_TIMESTAMP` | 心跳时（静默更新） |

**TCP 状态码说明**：

- `0`: 关闭（close）
- `1`: 等待（wait）
- `2`: 监听（lsn）

**主机状态码说明**：

- `0`: 空闲（free）
- `1`: 已锁定（lock）
- `2`: 已占用（occ）
- `3`: case执行中（run）
- `4`: 离线（offline）
- `5`: 待激活（inact）
- `6`: 硬件改动（hw_chg）
- `7`: 手动停用（disable）
- `8`: 更新中（updating）

### 2. host_exec_log 表（主机执行日志表）

#### 连接结果上报时更新的字段

| 字段名 | 类型 | 说明 | 更新值 | 更新时机 |
|--------|------|------|--------|----------|
| `host_state` | SmallInteger | 主机状态 | `2` (已占用) | Agent 上报连接结果时 |
| `updated_time` | DateTime | 更新时间 | `CURRENT_TIMESTAMP` | 自动更新（ON UPDATE） |

**查询条件**：

- `host_id = agent_id`
- `host_state = 1` (已锁定)
- `del_flag = 0`
- 按 `created_at` 降序，获取最新一条

#### Host 下线通知时更新的字段

| 字段名 | 类型 | 说明 | 更新值 | 更新时机 |
|--------|------|------|--------|----------|
| `host_state` | SmallInteger | 主机状态 | `4` (离线) | 收到 Host 下线通知时 |
| `updated_time` | DateTime | 更新时间 | `CURRENT_TIMESTAMP` | 自动更新（ON UPDATE） |

**查询条件**：

- `host_id = msg_host_id`
- `del_flag = 0`
- 按 `created_time` 降序，获取最新一条

**主机状态码说明**（host_exec_log 表）：

- `0`: 空闲（free）
- `1`: 已锁定（lock）
- `2`: 已占用（occ）
- `3`: case执行中（run）
- `4`: 离线（offline）

## 关键方法说明

### 1. update_tcp_state()

**位置**: `services/host-service/app/services/browser_host_service.py`

**功能**: 更新主机 TCP 状态

**SQL 更新语句**:

```sql
UPDATE host_rec 
SET tcp_state = ?, updated_time = CURRENT_TIMESTAMP 
WHERE id = ? AND del_flag = 0
```

**参数**:

- `host_id`: 主机ID（字符串，转换为整数）
- `tcp_state`: TCP状态（0-关闭, 1-等待, 2-监听）

### 2. update_host_status()

**位置**: `services/host-service/app/services/browser_host_service.py`

**功能**: 更新主机状态

**SQL 更新语句**:

```sql
UPDATE host_rec 
SET host_state = ?, updated_time = CURRENT_TIMESTAMP 
WHERE id = ? AND del_flag = 0
```

**参数**:

- `host_id`: 主机ID（字符串，转换为整数）
- `status_update`: 状态更新对象（`HostStatusUpdate`）

### 3. update_heartbeat_silent()

**位置**: `services/host-service/app/services/browser_host_service.py`

**功能**: 静默更新主机心跳时间（用于 WebSocket）

**特点**:

- 失败时不记录 ERROR 日志
- 不抛出异常，仅返回成功/失败状态
- 适用于 `host_id` 可能不在数据库中的场景

**SQL 更新语句**:

```sql
UPDATE host_rec 
SET updated_time = CURRENT_TIMESTAMP 
WHERE id = ? AND del_flag = 0
```

## 连接状态管理

### 内存数据结构

| 数据结构 | 类型 | 说明 |
|----------|------|------|
| `active_connections` | `Dict[str, WebSocket]` | 活跃连接字典：`{host_id: websocket}` |
| `heartbeat_timestamps` | `Dict[str, datetime]` | 心跳时间戳字典：`{host_id: datetime}` |
| `_heartbeat_warning_sent` | `Dict[str, datetime]` | 已发送警告的连接和时间：`{host_id: datetime}` |
| `_disconnecting` | `set[str]` | 正在断开连接的集合（防止重复调用） |
| `_disconnect_locks` | `Dict[str, asyncio.Lock]` | 断开连接的锁（防止并发断开同一个连接） |

### 连接数限制

- **最大连接数**: 1000（默认，可通过 `max_connections` 参数配置）
- **连接数检查**: 在 `connect()` 方法中检查，超过限制拒绝连接
- **有效连接检查**: 在检查连接数限制前，会先清理无效连接（`_cleanup_invalid_connections()`），确保只统计有效连接

#### 连接数检查逻辑

1. **清理无效连接**: 检查 `active_connections` 字典中所有连接的状态
   - 如果连接状态为 `DISCONNECTED`，从字典中移除
   - 清理相关的心跳时间戳和警告记录

2. **统计有效连接数**: 使用清理后的 `len(self.active_connections)` 统计

3. **检查限制**: 如果有效连接数 >= `max_connections`，拒绝新连接

#### 为什么需要清理无效连接

- 如果客户端异常断开（直接关闭、网络中断），可能不会立即触发 `disconnect()` 方法
- 这些无效连接在心跳检测清理前（最多 70 秒）仍会被计入连接数
- 可能导致实际有效连接数 < 1000，但因为包含无效连接，导致新连接被拒绝
- 通过主动清理无效连接，确保连接数统计的准确性

## 心跳检测机制

### 统一心跳检查任务

- **检查间隔**: 10 秒
- **心跳超时时间**: 60 秒
- **警告等待时间**: 10 秒

### 心跳检测流程

1. **批量检查所有连接**
   - 每 10 秒检查一次所有连接的心跳时间戳
   - 计算距离上次心跳的时间差

2. **首次超时处理**
   - 如果时间差 > 60 秒，发送心跳超时警告
   - 更新 TCP 状态为 `1`（等待）
   - 记录警告时间

3. **警告后仍未恢复**
   - 如果警告后 > 10 秒仍未收到心跳，关闭连接
   - 调用 `disconnect(agent_id)` 断开连接

## 消息处理流程

### 消息路由

1. 接收消息：`await websocket.receive_json()`
2. 提取消息类型：`data.get("type")`
3. 查找处理器：`message_handlers.get(message_type)`
4. 调用处理器：`await handler(agent_id, data)`

### 默认消息处理器

| 消息类型 | 处理器方法 | 说明 |
|----------|------------|------|
| `HEARTBEAT` | `_handle_heartbeat` | 处理心跳消息 |
| `STATUS_UPDATE` | `_handle_status_update` | 处理状态更新消息 |
| `COMMAND_RESPONSE` | `_handle_command_response` | 处理命令响应消息 |
| `CONNECTION_RESULT` | `_handle_connection_result` | 处理 Agent 上报连接结果 |
| `HOST_OFFLINE_NOTIFICATION` | `_handle_host_offline_notification` | 处理 Host 下线通知 |

## 错误处理

### 连接错误

- **认证失败**: 返回错误消息，不建立连接
- **连接数超限**: 返回错误码 `1008`，原因："服务器连接数已达上限"
- **重复连接**: 先断开旧连接，再建立新连接

### 消息处理错误

- **未知消息类型**: 发送错误消息给客户端
- **消息处理异常**: 记录错误日志，发送错误消息给客户端

### 断线错误

- **正常断开**: 记录 INFO 日志
- **异常断开**: 记录 ERROR 日志，包含异常堆栈
- **数据库更新失败**: 记录 WARNING 日志，不影响断线流程

## 性能优化

### 1. 统一心跳检查

- **优化前**: 每个连接一个独立心跳任务（500 个连接 = 500 个任务）
- **优化后**: 单个任务批量检查所有连接（500 个连接 = 1 个任务）
- **效果**: CPU 消耗降低 90%

### 2. 并发消息发送

- **广播消息**: 使用批量并发发送（每批 50 个连接）
- **效果**: 500 个连接的延迟从 500ms 降低到 10ms（50倍提升）

### 3. 防重复断开机制

- 使用锁和集合防止并发断开同一个连接
- 避免重复关闭 WebSocket 连接

## 日志记录

### 连接日志

- **连接请求**: INFO 级别，记录客户端信息
- **认证成功**: INFO 级别，记录 host_id 和用户信息
- **连接建立**: INFO 级别，记录连接数和活跃主机列表
- **连接注册完成**: INFO 级别，记录新的连接数和活跃主机列表

### 断线日志

- **正常断开**: INFO 级别
- **异常断开**: ERROR 级别，包含异常堆栈
- **断线完成**: INFO 级别，记录剩余连接数

### 心跳日志

- **心跳接收**: DEBUG 级别
- **心跳超时警告**: WARNING 级别
- **心跳恢复**: INFO 级别
- **心跳超时关闭**: WARNING 级别

### 消息日志

- **接收消息**: INFO 级别，包含完整消息内容（JSON）
- **发送消息**: INFO 级别，包含完整消息内容（JSON）
- **消息处理失败**: ERROR 级别，包含异常堆栈

## 总结

`websocket_endpoint_new` 端点提供了完整的 WebSocket 连接和断线处理机制，包括：

1. **双重认证支持**: 网关传递和直接连接两种方式
2. **连接管理**: 连接数限制、重复连接处理、连接状态跟踪
3. **心跳检测**: 统一心跳检查任务，自动检测和关闭超时连接
4. **消息路由**: 支持多种消息类型，可扩展的消息处理器
5. **数据库同步**: 自动更新 `host_rec` 和 `host_exec_log` 表的状态
6. **错误处理**: 完善的错误处理和日志记录
7. **性能优化**: 统一心跳检查、并发消息发送、防重复断开

所有数据库更新操作都使用事务，确保数据一致性。断线时的数据库更新失败不会影响断线流程，只记录警告日志。
