# 定时任务文档

## 概述

本文档详细描述了项目中所有定时任务的逻辑、处理的表数据、执行时间等信息。

**定时任务类型**: 使用 `asyncio.Task` 实现的后台定时任务

**生命周期管理**: 通过 FastAPI 的 `lifespan` 处理器管理任务的启动和停止

---

## 1. Case 超时检测定时任务

### 基本信息

- **服务**: `host-service`
- **文件位置**: `services/host-service/app/services/case_timeout_task.py`
- **类名**: `CaseTimeoutTaskService`
- **执行间隔**: 10 分钟（600 秒）
- **首次执行延迟**: 60 秒（服务启动后等待 60 秒再执行第一次检查）

### 业务逻辑

1. **定时检测流程**:
   - 每 10 分钟执行一次超时检测
   - 从 `sys_conf` 表查询 `case_timeout` 配置（带 Redis 缓存，缓存 1 小时）
   - 查询超时的 `host_exec_log` 记录
   - 通过 WebSocket 通知对应的 Host 结束任务

2. **超时判断条件**:
   - `host_state` in (2, 3)  # 已占用或 case 执行中
   - `case_state` = 1        # 启动
   - `del_flag` = 0          # 未删除
   - `begin_time` < 当前时间 - `case_timeout` 分钟

3. **通知机制**:
   - 检查 Host 是否在线（WebSocket 连接）
   - 如果在线，发送超时通知消息
   - 如果不在线，记录 DEBUG 日志（可能是历史超时记录）

### 处理的表数据

#### 1. `sys_conf` 表

- **查询字段**: `conf_key = 'case_timeout'`
- **查询条件**: `del_flag = 0` 且 `state_flag = 0`（启用状态）
- **用途**: 获取 Case 超时时间配置（单位：分钟）
- **缓存**: Redis 缓存键 `sys_conf:case_timeout`，过期时间 1 小时

**配置示例**:
```sql
INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag)
VALUES ('case_timeout', '30', 'Case超时时间(分钟)', 0, 0);
```

#### 2. `host_exec_log` 表

- **查询字段**: 所有字段
- **查询条件**:
  - `host_state` IN (2, 3)  # 已占用或 case 执行中
  - `case_state` = 1         # 启动
  - `del_flag` = 0           # 未删除
  - `begin_time` < 当前时间 - `case_timeout` 分钟
- **排序**: 按 `begin_time` 升序
- **用途**: 查找超时的测试用例执行记录

**表结构说明**:
- `id`: 执行日志 ID
- `host_id`: 主机 ID
- `tc_id`: 测试用例 ID
- `host_state`: 主机状态（2=已占用, 3=case执行中）
- `case_state`: Case 状态（1=启动）
- `begin_time`: 开始时间
- `del_flag`: 删除标志

### 执行时间

- **执行间隔**: 600 秒（10 分钟）
- **首次执行延迟**: 60 秒（服务启动后等待 60 秒）
- **异常重试间隔**: 60 秒（如果执行异常，等待 60 秒后继续）

### 使用接口

```python
# 获取定时任务服务实例（单例）
from app.services.case_timeout_task import get_case_timeout_task_service

case_timeout_task = get_case_timeout_task_service()

# 启动定时任务
await case_timeout_task.start()

# 停止定时任务
await case_timeout_task.stop()
```

### 生命周期管理

在 `services/host-service/app/main.py` 中通过 FastAPI 的 `lifespan` 处理器管理：

```python
async def startup_case_timeout_task(app):
    """启动 Case 超时检测定时任务"""
    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.start()

async def shutdown_case_timeout_task(app):
    """停止 Case 超时检测定时任务"""
    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.stop()

app = FastAPI(
    lifespan=create_service_lifespan(
        config,
        startup_handlers=[startup_case_timeout_task],
        shutdown_handlers=[shutdown_case_timeout_task],
    ),
)
```

### 相关代码

- **类**: `CaseTimeoutTaskService`
- **方法**:
  - `start()`: 启动定时任务
  - `stop()`: 停止定时任务
  - `_run_loop()`: 定时任务循环
  - `_check_timeout_cases()`: 检查超时的测试用例
  - `_get_case_timeout_config()`: 获取超时配置（带缓存）
  - `_query_timeout_cases()`: 查询超时的执行日志
  - `_notify_case_timeout()`: 通知 Host 结束超时任务

### 日志记录

- **启动日志**: `INFO` 级别，记录执行间隔
- **检测日志**: `INFO` 级别，记录检测到的超时用例数量
- **通知日志**: `INFO` 级别，记录通知发送成功/失败
- **配置缺失警告**: `WARNING` 级别（仅第一次），提示配置 SQL
- **异常日志**: `ERROR` 级别，记录异常详情

---

## 2. WebSocket 心跳检查任务

### 基本信息

- **服务**: `host-service`
- **文件位置**: `services/host-service/app/services/agent_websocket_manager.py`
- **类名**: `AgentWebSocketManager`
- **执行间隔**: 10 秒
- **心跳超时时间**: 60 秒
- **心跳警告等待时间**: 10 秒（发送警告后等待 10 秒，如果仍未收到心跳则关闭连接）

### 业务逻辑

1. **心跳检查流程**:
   - 每 10 秒批量检查所有 WebSocket 连接的心跳状态
   - 检测心跳超时的连接（超过 60 秒未收到心跳）
   - 首次超时：发送警告并记录警告时间
   - 已发送警告且超过等待时间：关闭连接

2. **优化机制**:
   - 使用单个任务批量检查所有连接（替代每个连接独立的心跳任务）
   - 500 个连接从 500 个任务减少到 1 个任务
   - CPU 消耗降低 90%

3. **连接管理**:
   - 自动清理已断开的连接的心跳记录
   - 批量处理超时连接（并发发送警告和关闭连接）

### 处理的表数据

**无数据库表操作**，仅处理内存中的连接状态：

- `active_connections`: 活跃连接字典 `{agent_id: WebSocket}`
- `heartbeat_timestamps`: 心跳时间戳字典 `{agent_id: datetime}`
- `_heartbeat_warning_sent`: 已发送警告的连接和时间 `{agent_id: datetime}`

### 执行时间

- **执行间隔**: 10 秒（`heartbeat_check_interval`）
- **心跳超时时间**: 60 秒（`heartbeat_timeout`）
- **警告等待时间**: 30 秒（`heartbeat_warning_wait_time`）

### 使用接口

```python
# 心跳检查任务在 AgentWebSocketManager 初始化时自动启动
ws_manager = get_agent_websocket_manager()
# 心跳检查任务已自动启动
```

### 相关代码

- **类**: `AgentWebSocketManager`
- **方法**:
  - `_start_heartbeat_checker()`: 启动心跳检查任务
  - `_heartbeat_check_loop()`: 心跳检查循环
  - `_check_all_heartbeats()`: 批量检查所有连接的心跳
  - `_send_heartbeat_warning()`: 发送心跳超时警告
  - `_disconnect_heartbeat_timeout()`: 关闭心跳超时的连接

### 日志记录

- **启动日志**: `INFO` 级别，记录任务启动
- **超时警告**: `WARNING` 级别，记录超时连接数量
- **关闭连接**: `WARNING` 级别，记录关闭的连接数量
- **异常日志**: `ERROR` 级别，记录异常详情

---

## 3. WebSocket 连接池清理任务

### 基本信息

- **服务**: `gateway-service`
- **文件位置**: `services/gateway-service/app/services/websocket_connection_pool.py`
- **类名**: `WebSocketConnectionPool`
- **执行间隔**: 60 秒（`health_check_interval`）

### 业务逻辑

1. **清理流程**:
   - 每 60 秒执行一次连接池清理
   - 清理非活跃连接
   - 释放资源

2. **清理策略**:
   - 检查连接是否活跃
   - 清理已关闭或非活跃的连接
   - 维护连接池的健康状态

### 处理的表数据

**无数据库表操作**，仅处理连接池状态：

- 连接池中的 WebSocket 连接对象
- 连接的状态信息（活跃/非活跃）

### 执行时间

- **执行间隔**: 60 秒（`health_check_interval`）

### 使用接口

```python
# 连接池清理任务在 WebSocketConnectionPool 初始化时自动启动
pool = WebSocketConnectionPool(...)
await pool.start_background_tasks()  # 启动所有后台任务
```

### 相关代码

- **类**: `WebSocketConnectionPool`
- **方法**:
  - `start_background_tasks()`: 启动所有后台任务（包括清理任务）
  - `stop_background_tasks()`: 停止所有后台任务
  - `_cleanup_loop()`: 清理循环
  - `cleanup()`: 执行清理操作

---

## 4. WebSocket 连接池健康检查任务

### 基本信息

- **服务**: `gateway-service`
- **文件位置**: `services/gateway-service/app/services/websocket_connection_pool.py`
- **类名**: `WebSocketConnectionPool`
- **执行间隔**: 30 秒（`health_check_interval // 2`）

### 业务逻辑

1. **健康检查流程**:
   - 每 30 秒执行一次健康检查
   - 遍历所有连接池中的连接
   - 对活跃连接执行 ping 操作
   - 如果 ping 失败，标记连接为非活跃

2. **检查策略**:
   - 只检查标记为活跃的连接
   - 使用连接的 `ping()` 方法检查连接状态
   - 自动标记失效连接为非活跃

### 处理的表数据

**无数据库表操作**，仅处理连接池状态：

- 连接池中的 WebSocket 连接对象
- 连接的状态信息（活跃/非活跃）

### 执行时间

- **执行间隔**: 30 秒（`health_check_interval // 2`）

### 使用接口

```python
# 健康检查任务在 WebSocketConnectionPool 初始化时自动启动
pool = WebSocketConnectionPool(...)
await pool.start_background_tasks()  # 启动所有后台任务
```

### 相关代码

- **类**: `WebSocketConnectionPool`
- **方法**:
  - `start_background_tasks()`: 启动所有后台任务（包括健康检查任务）
  - `stop_background_tasks()`: 停止所有后台任务
  - `_health_check_loop()`: 健康检查循环

---

## 5. WebSocket 连接池监控任务

### 基本信息

- **服务**: `gateway-service`
- **文件位置**: `services/gateway-service/app/services/websocket_connection_pool.py`
- **类名**: `WebSocketConnectionPool`
- **执行间隔**: 60 秒

### 业务逻辑

1. **监控流程**:
   - 每 60 秒执行一次连接池状态监控
   - 获取连接池统计信息
   - 记录连接池状态日志

2. **监控指标**:
   - 总连接数
   - 活跃连接数
   - 命中率
   - 创建的连接总数
   - 关闭的连接总数

### 处理的表数据

**无数据库表操作**，仅处理连接池状态：

- 连接池统计信息

### 执行时间

- **执行间隔**: 60 秒

### 使用接口

```python
# 监控任务在 WebSocketConnectionPool 初始化时自动启动
pool = WebSocketConnectionPool(...)
await pool.start_background_tasks()  # 启动所有后台任务
```

### 相关代码

- **类**: `WebSocketConnectionPool`
- **方法**:
  - `start_background_tasks()`: 启动所有后台任务（包括监控任务）
  - `stop_background_tasks()`: 停止所有后台任务
  - `_monitor_loop()`: 监控循环
  - `get_stats()`: 获取连接池统计信息

### 日志记录

- **监控日志**: `INFO` 级别，记录连接池状态统计信息

---

## 定时任务汇总表

| 任务名称 | 服务 | 执行间隔 | 处理的表 | 功能说明 |
|---------|------|---------|---------|---------|
| Case 超时检测 | host-service | 10 分钟 | `host_exec_log`, `sys_conf` | 检测超时的测试用例，通知 Host 结束任务 |
| WebSocket 心跳检查 | host-service | 10 秒 | 无（内存状态） | 检查 WebSocket 连接的心跳状态 |
| 连接池清理 | gateway-service | 60 秒 | 无（连接池状态） | 清理非活跃连接 |
| 连接池健康检查 | gateway-service | 30 秒 | 无（连接池状态） | 检查连接池中连接的健康状态 |
| 连接池监控 | gateway-service | 60 秒 | 无（连接池状态） | 监控连接池状态并记录日志 |

---

## 定时任务执行时间汇总

| 任务名称 | 首次执行延迟 | 执行间隔 | 异常重试间隔 |
|---------|------------|---------|------------|
| Case 超时检测 | 60 秒 | 600 秒（10 分钟） | 60 秒 |
| WebSocket 心跳检查 | 立即 | 10 秒 | 无（循环继续） |
| 连接池清理 | 立即 | 60 秒 | 无（循环继续） |
| 连接池健康检查 | 立即 | 30 秒 | 无（循环继续） |
| 连接池监控 | 立即 | 60 秒 | 无（循环继续） |

---

## 定时任务生命周期管理

### host-service

**Case 超时检测任务**通过 FastAPI 的 `lifespan` 处理器管理：

```python
# services/host-service/app/main.py
async def startup_case_timeout_task(app):
    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.start()

async def shutdown_case_timeout_task(app):
    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.stop()

app = FastAPI(
    lifespan=create_service_lifespan(
        config,
        startup_handlers=[startup_case_timeout_task],
        shutdown_handlers=[shutdown_case_timeout_task],
    ),
)
```

### gateway-service

**WebSocket 连接池任务**在连接池初始化时自动启动：

```python
# services/gateway-service/app/services/websocket_connection_pool.py
pool = WebSocketConnectionPool(...)
await pool.start_background_tasks()  # 启动所有后台任务
```

---

## 定时任务配置

### Case 超时检测任务配置

**超时时间配置**（存储在 `sys_conf` 表）：

```sql
INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag)
VALUES ('case_timeout', '30', 'Case超时时间(分钟)', 0, 0);
```

**配置说明**:
- `conf_key`: `case_timeout`
- `conf_val`: 超时时间（分钟），例如 `30` 表示 30 分钟
- `state_flag`: `0` 表示启用
- `del_flag`: `0` 表示未删除

**缓存配置**:
- Redis 缓存键: `sys_conf:case_timeout`
- 缓存过期时间: 1 小时（3600 秒）

### WebSocket 心跳检查任务配置

**配置参数**（代码中硬编码）:
- `heartbeat_check_interval`: 10 秒（检查间隔）
- `heartbeat_timeout`: 60 秒（心跳超时时间）
- `heartbeat_warning_wait_time`: 10 秒（警告后等待时间）