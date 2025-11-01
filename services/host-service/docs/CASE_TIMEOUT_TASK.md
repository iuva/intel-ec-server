# Case 超时检测定时任务

## 📋 功能概述

定时检测执行超时的测试用例，并通过 WebSocket 通知对应的 Host 结束任务。

## 🎯 功能特性

1. **定时执行**：每 10 分钟执行一次超时检测
2. **配置缓存**：从 `sys_conf` 表查询 `case_timeout` 配置，缓存 1 小时
3. **超时检测**：查询符合条件的超时任务并发送通知
4. **WebSocket 通知**：通过 WebSocket 实时通知 Host 结束任务

## 🔍 查询条件

定时任务会查询 `host_exec_log` 表中满足以下条件的记录：

- `host_state` in (2, 3) - 已占用或 case 执行中
- `case_state` = 1 - 启动状态
- `del_flag` = 0 - 未删除
- `begin_time` < 当前时间 - `case_timeout`（分钟）

## 📊 数据库表结构

### sys_conf 表

用于存储系统配置，包括 `case_timeout` 配置。

```sql
-- 查询 case_timeout 配置
SELECT conf_val FROM sys_conf 
WHERE conf_key = 'case_timeout' 
  AND del_flag = 0 
  AND state_flag = 0;
```

**配置说明**：
- `conf_key`: `'case_timeout'`
- `conf_val`: 超时时间（分钟），字符串类型的整数
- `state_flag`: 0-启用，1-停用

### host_exec_log 表

存储主机执行日志，用于检测超时任务。

**关键字段**：
- `host_id`: 主机ID
- `host_state`: 主机状态（2-已占用，3-case执行中）
- `case_state`: 执行状态（1-启动）
- `begin_time`: 开始时间
- `del_flag`: 删除标识（0-未删除）

## 🚀 实现方式

### 定时任务服务

使用 `asyncio.create_task` 实现后台定时任务，与项目现有实现方式保持一致。

**文件位置**：`app/services/case_timeout_task.py`

**核心类**：`CaseTimeoutTaskService`

### 生命周期集成

定时任务在应用启动时自动启动，关闭时自动停止。

**集成位置**：`app/main.py`

```python
# 定时任务启动和关闭处理器
async def startup_case_timeout_task():
    """启动 Case 超时检测定时任务"""
    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.start()

async def shutdown_case_timeout_task():
    """停止 Case 超时检测定时任务"""
    case_timeout_task = get_case_timeout_task_service()
    await case_timeout_task.stop()

# 集成到生命周期
app = FastAPI(
    lifespan=create_service_lifespan(
        config,
        startup_handlers=[startup_case_timeout_task],
        shutdown_handlers=[shutdown_case_timeout_task],
    ),
)
```

## 🔧 配置缓存

### 缓存策略

- **缓存键**：`sys_conf:case_timeout`
- **缓存过期时间**：1 小时（3600 秒）
- **缓存存储**：Redis

### 缓存逻辑

1. **首次查询**：从数据库查询配置并存入缓存
2. **后续查询**：优先从缓存获取，缓存过期后重新查询数据库
3. **异常处理**：缓存失效时自动回退到数据库查询

## 📨 WebSocket 通知

### 通知消息格式

```json
{
  "type": "case_timeout_notification",
  "host_id": "1846486359367955051",
  "log_id": 12345,
  "tc_id": "tc_001",
  "message": "测试用例执行超时（超过 30 分钟），请结束任务",
  "timeout_minutes": 30,
  "begin_time": "2025-01-30T10:00:00Z",
  "timestamp": "2025-01-30T10:30:00Z"
}
```

### 通知条件

1. Host 必须在线（WebSocket 连接存在）
2. 执行日志记录必须有效（host_id 不为空）
3. 消息发送成功才记录成功日志

## 📝 日志记录

### 日志级别

- **INFO**：任务启动/停止、检测完成、通知发送成功
- **DEBUG**：配置获取、查询详情
- **WARNING**：配置无效、Host 未连接、通知发送失败
- **ERROR**：异常情况（查询失败、通知发送异常）

### 关键日志示例

```
[INFO] Case 超时检测定时任务已启动 - interval_minutes=10
[INFO] 开始检测超时的测试用例
[INFO] 发现超时的测试用例 - count=2, timeout_minutes=30
[INFO] 超时通知已发送 - host_id=xxx, log_id=xxx
[INFO] 超时检测完成 - total=2, success=2, failed=0
```

## 🧪 配置设置

### 初始化配置（必须）

定时任务需要 `case_timeout` 配置才能正常工作。请执行以下 SQL 插入配置：

```sql
-- 插入 case_timeout 配置（如果不存在）
INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag)
VALUES ('case_timeout', '30', 'Case超时时间(分钟)', 0, 0)
ON DUPLICATE KEY UPDATE 
    conf_val = '30',
    state_flag = 0,
    del_flag = 0;
```

**配置说明**：
- `conf_key`: 必须为 `'case_timeout'`
- `conf_val`: 超时时间（分钟），字符串类型的整数，例如 `'30'` 表示 30 分钟
- `conf_name`: 配置名称，例如 `'Case超时时间(分钟)'`
- `state_flag`: 必须为 `0`（启用状态）
- `del_flag`: 必须为 `0`（未删除）

### 配置验证

```sql
-- 查询配置是否正确
SELECT conf_key, conf_val, conf_name, state_flag, del_flag 
FROM sys_conf 
WHERE conf_key = 'case_timeout' AND del_flag = 0 AND state_flag = 0;
```

## 🧪 测试建议

### 2. 超时任务测试

```sql
-- 创建超时测试数据
INSERT INTO host_exec_log (
    host_id, case_state, host_state, begin_time, del_flag
) VALUES (
    1846486359367955051, 1, 2, 
    DATE_SUB(NOW(), INTERVAL 35 MINUTE), 
    0
);
```

### 3. 验证步骤

1. 确保 `sys_conf` 表中有 `case_timeout` 配置
2. 创建符合条件的超时测试数据
3. 等待定时任务执行（最多 10 分钟）
4. 检查日志确认检测和通知是否成功
5. 验证 Host 是否收到超时通知消息

## 📊 监控指标

建议添加以下监控指标：

1. **定时任务执行次数**：记录每次检测的执行
2. **超时任务数量**：记录每次检测发现的超时任务数
3. **通知成功率**：记录通知发送的成功率
4. **配置缓存命中率**：记录配置缓存的命中情况

## 🔄 后续优化建议

1. **可配置执行间隔**：支持通过环境变量或配置文件设置执行间隔
2. **批量通知优化**：批量发送通知以提高效率
3. **任务状态更新**：检测到超时后自动更新任务状态
4. **告警集成**：超时任务数量超过阈值时发送告警

## 📚 相关文件

- **服务实现**：`app/services/case_timeout_task.py`
- **生命周期集成**：`app/main.py`
- **数据库模型**：`app/models/host_exec_log.py`, `app/models/sys_conf.py`
- **WebSocket 管理**：`app/services/agent_websocket_manager.py`
- **缓存管理**：`shared/common/cache.py`

