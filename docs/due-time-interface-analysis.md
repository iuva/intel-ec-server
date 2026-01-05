# Due Time 接口业务逻辑分析

## 📋 概述

`due_time` 接口用于 Agent 上报测试用例的预期结束时间，系统会根据上报的时间进行超时检测和邮件通知。

## 🔗 接口信息

### 接口路径
```
POST /api/v1/host/agent/testcase/due-time
```

### 接口文件
- **端点定义**: `services/host-service/app/api/v1/endpoints/agent_report.py`
- **服务实现**: `services/host-service/app/services/agent_report_service.py`
- **数据模型**: `services/host-service/app/schemas/testcase.py`

---

## 📥 请求参数

### 请求模型 (`TestCaseDueTimeRequest`)

```python
{
    "tc_id": "absdf1234",      # 测试用例ID（必需，字符串，1-64字符）
    "due_time": 60             # 预期结束时间（必需，整数，>=0，表示分钟数）
}
```

**参数说明**:
- `tc_id`: 测试用例ID，用于标识正在执行的测试用例
- `due_time`: **分钟时间差**（整数），从当前时间开始计算，表示多少分钟后预期结束
  - 例如：`due_time = 60` 表示预期 60 分钟后结束
  - 服务器会自动计算：`预期结束时间 = 当前时间 + due_time 分钟`

---

## 📤 响应数据

### 响应模型 (`TestCaseDueTimeResponse`)

```python
{
    "host_id": "123",                    # 主机ID（字符串）
    "tc_id": "absdf1234",                # 测试用例ID
    "due_time": "2025-01-30T15:30:00Z", # 预期结束时间（ISO 8601 格式）
    "updated": true                       # 是否成功更新
}
```

---

## 🔄 业务逻辑流程

### 1. 接口层处理 (`report_due_time`)

**文件**: `services/host-service/app/api/v1/endpoints/agent_report.py:532`

```python
async def report_due_time(
    report_data: TestCaseDueTimeRequest,
    agent_info: Dict[str, Any] = Depends(get_current_agent),
    agent_report_service: AgentReportService = Depends(get_agent_report_service),
) -> Result[TestCaseDueTimeResponse]:
```

**处理步骤**:
1. 从 JWT token 中提取 `host_id`（通过 `get_current_agent` 依赖注入）
2. 记录请求日志（包含 `host_id`, `tc_id`, `due_time_minutes`）
3. 调用服务层方法 `update_due_time()`
4. 返回统一格式的成功响应

---

### 2. 服务层处理 (`update_due_time`)

**文件**: `services/host-service/app/services/agent_report_service.py:855`

#### 2.1 时间计算

```python
# 计算实际的预期结束时间（当前时间 + 分钟数）
now = datetime.now(timezone.utc)
due_time = now + timedelta(minutes=due_time_minutes)
```

**关键点**:
- 使用 UTC 时间确保时区一致性
- `due_time_minutes` 是整数，表示分钟数
- 计算结果存储在 `host_exec_log.due_time` 字段（`DateTime` 类型）

#### 2.2 查询执行日志

**查询条件**:
```python
select(HostExecLog)
.where(
    and_(
        HostExecLog.host_id == host_id,      # 主机ID匹配
        HostExecLog.tc_id == tc_id,          # 测试用例ID匹配
        HostExecLog.case_state == 1,        # 启动状态（执行中）
        HostExecLog.del_flag == 0,          # 未删除
    )
)
.order_by(HostExecLog.created_time.desc())  # 按创建时间倒序
.limit(1)                                   # 只取最新一条
```

**业务规则**:
- 只更新**执行中**的记录（`case_state = 1`）
- 如果未找到执行中的记录，返回 `EXEC_LOG_NOT_FOUND` 错误（400）

#### 2.3 更新 due_time 字段

```python
update(HostExecLog)
.where(HostExecLog.id == exec_log.id)
.values(due_time=due_time)  # 更新为计算后的 datetime
```

**更新操作**:
- 直接更新 `host_exec_log.due_time` 字段
- 使用数据库事务确保数据一致性
- 提交后返回更新结果

---

## ⏰ 超时检测逻辑

### 定时任务使用 (`case_timeout_task.py`)

**文件**: `services/host-service/app/services/case_timeout_task.py:351`

#### 超时判断规则

定时任务每 10 分钟执行一次，查询超时的执行日志记录。

**查询条件**:
```python
select(HostExecLog)
.where(
    and_(
        HostExecLog.host_state.in_([2, 3]),  # 已占用或case执行中
        HostExecLog.case_state == 1,         # 启动状态
        HostExecLog.del_flag == 0,           # 未删除
        HostExecLog.notify_state == 0,       # 未通知
        or_(
            # 情况1：存在 due_time，判断 due_time < 当前时间
            and_(
                HostExecLog.due_time.is_not(None),
                HostExecLog.due_time < now,
            ),
            # 情况2：不存在 due_time，判断 begin_time < 当前时间 - timeout_minutes
            and_(
                HostExecLog.due_time.is_(None),
                HostExecLog.begin_time < timeout_threshold,
            ),
        ),
    )
)
```

#### 超时判断优先级

1. **优先使用 `due_time`**（如果存在）:
   - 判断条件：`due_time < 当前时间`
   - 说明：Agent 已上报预期结束时间，使用精确的超时判断

2. **回退使用 `begin_time`**（如果 `due_time` 不存在）:
   - 判断条件：`begin_time < 当前时间 - timeout_minutes`
   - 说明：Agent 未上报预期结束时间，使用系统配置的超时时间（从 `sys_conf` 表获取 `case_timeout`）

#### 超时处理流程

1. **查询超时记录**: 使用上述查询条件获取超时的执行日志
2. **发送邮件通知**: 调用 `_send_timeout_email_notification()` 发送邮件
3. **更新通知状态**: 邮件发送成功后，更新 `notify_state = 1`（已通知），避免重复通知

---

## 📊 数据流图

```
┌─────────────────┐
│   Agent 上报    │
│  due_time (分钟) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   接口层处理     │
│  report_due_time │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   服务层处理     │
│  update_due_time │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│ 计算   │ │  查询执行日志 │
│ 时间   │ │  (case_state=1)│
└────┬───┘ └──────┬───────┘
     │            │
     └─────┬──────┘
           │
           ▼
    ┌──────────────┐
    │  更新数据库   │
    │  due_time字段 │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  定时任务检测 │
    │  (每10分钟)   │
    └──────┬───────┘
           │
      ┌────┴────┐
      │         │
      ▼         ▼
┌─────────┐ ┌──────────────┐
│ 超时判断 │ │  邮件通知     │
│         │ │  (notify_state)│
└─────────┘ └──────────────┘
```

---

## 🔍 关键业务规则

### 1. 时间计算规则

| 输入 | 计算方式 | 输出 |
|------|---------|------|
| `due_time = 60` (分钟) | `当前时间 + 60分钟` | `2025-01-30T15:30:00Z` |
| `due_time = 0` | `当前时间 + 0分钟` | `2025-01-30T14:30:00Z` |
| `due_time = 120` | `当前时间 + 120分钟` | `2025-01-30T16:30:00Z` |

**注意**: 
- 所有时间使用 UTC 时区
- `due_time` 参数是**相对时间**（分钟数），不是绝对时间

### 2. 查询条件规则

**必须满足的条件**:
- ✅ `host_id` 匹配（从 token 中提取）
- ✅ `tc_id` 匹配（请求参数）
- ✅ `case_state = 1`（执行中状态）
- ✅ `del_flag = 0`（未删除）

**查询结果**:
- 如果找到记录：更新 `due_time` 字段
- 如果未找到记录：返回 `EXEC_LOG_NOT_FOUND` 错误（400）

### 3. 超时检测规则

**优先级**:
1. **优先使用 `due_time`**（如果存在）:
   ```
   due_time < 当前时间 → 超时
   ```

2. **回退使用 `begin_time`**（如果 `due_time` 不存在）:
   ```
   begin_time < 当前时间 - timeout_minutes → 超时
   ```

**超时配置**:
- `timeout_minutes` 从 `sys_conf` 表获取（`conf_key = "case_timeout"`）
- 配置缓存 1 小时，避免频繁查询数据库

### 4. 通知去重规则

**避免重复通知**:
- 只查询 `notify_state = 0`（未通知）的记录
- 邮件发送成功后，更新 `notify_state = 1`（已通知）
- 确保同一条记录不会被重复通知

---

## ⚠️ 错误处理

### 错误码定义

| 错误码 | HTTP状态码 | 说明 | 触发条件 |
|--------|-----------|------|---------|
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 | `due_time < 0` 或 `tc_id` 为空 |
| `EXEC_LOG_NOT_FOUND` | 400 | 未找到执行中的记录 | 查询不到 `case_state=1` 的记录 |
| `DUE_TIME_UPDATE_FAILED` | 500 | 更新处理失败 | 数据库操作异常 |

### 错误响应示例

```json
{
    "code": 400,
    "message": "未找到主机 123 的测试用例 absdf1234 执行中的记录",
    "error_code": "EXEC_LOG_NOT_FOUND",
    "details": {
        "host_id": 123,
        "tc_id": "absdf1234"
    },
    "timestamp": "2025-01-30T14:30:00Z"
}
```

---

## 🔄 与其他接口的关联

### 1. 测试用例结果上报 (`report_testcase_result`)

**关联关系**:
- `report_testcase_result` 接口会更新 `case_state`（从 1 变为 2 或 3）
- 一旦 `case_state` 不再是 1，`due_time` 接口将无法找到执行中的记录

**业务逻辑**:
```
测试用例开始 → case_state = 1 → 可以上报 due_time
测试用例结束 → case_state = 2/3 → 无法上报 due_time（记录已结束）
```

### 2. 定时任务超时检测 (`_check_timeout_cases`)

**关联关系**:
- 定时任务使用 `due_time` 字段判断任务是否超时
- 如果 `due_time` 存在，优先使用 `due_time` 进行超时判断
- 如果 `due_time` 不存在，回退使用 `begin_time + timeout_minutes`

**业务逻辑**:
```
Agent 上报 due_time → 定时任务使用 due_time 判断超时
Agent 未上报 due_time → 定时任务使用 begin_time + timeout_minutes 判断超时
```

---

## 📝 使用场景示例

### 场景 1: Agent 上报预期结束时间

**步骤**:
1. Agent 开始执行测试用例，系统创建 `host_exec_log` 记录（`case_state = 1`）
2. Agent 预估测试用例需要 60 分钟完成
3. Agent 调用接口：`POST /api/v1/host/agent/testcase/due-time`
   ```json
   {
       "tc_id": "test_case_001",
       "due_time": 60
   }
   ```
4. 服务器计算：`due_time = 当前时间 + 60分钟`
5. 更新 `host_exec_log.due_time` 字段

**结果**:
- 定时任务会在 `due_time` 时间点检测是否超时
- 如果超过 `due_time` 仍未完成，发送邮件通知

### 场景 2: Agent 未上报预期结束时间

**步骤**:
1. Agent 开始执行测试用例，系统创建 `host_exec_log` 记录（`case_state = 1`）
2. Agent **未调用** `due_time` 接口
3. 定时任务检测超时时：
   - 发现 `due_time` 为 `NULL`
   - 使用 `begin_time + timeout_minutes` 判断超时

**结果**:
- 使用系统配置的 `case_timeout` 作为超时时间
- 如果超过 `begin_time + timeout_minutes` 仍未完成，发送邮件通知

### 场景 3: Agent 更新预期结束时间

**步骤**:
1. Agent 已上报 `due_time = 60`（预期 60 分钟后结束）
2. 执行过程中发现需要更多时间
3. Agent 再次调用接口：`POST /api/v1/host/agent/testcase/due-time`
   ```json
   {
       "tc_id": "test_case_001",
       "due_time": 120  # 更新为 120 分钟
   }
   ```
4. 服务器重新计算并更新 `due_time` 字段

**结果**:
- `due_time` 字段被更新为新的预期结束时间
- 定时任务使用新的 `due_time` 进行超时判断

---

## 🎯 最佳实践

### 1. Agent 端建议

- ✅ **及时上报**: 测试用例开始后，尽快上报预期结束时间
- ✅ **动态更新**: 如果执行时间超出预期，及时更新 `due_time`
- ✅ **合理估算**: 根据测试用例复杂度合理估算 `due_time`，避免频繁更新

### 2. 系统端建议

- ✅ **超时配置**: 合理配置 `case_timeout`（系统默认超时时间）
- ✅ **邮件通知**: 确保邮箱配置正确，及时接收超时通知
- ✅ **监控告警**: 监控超时任务数量，及时发现异常情况

---

## 📊 数据表结构

### `host_exec_log` 表相关字段

| 字段名 | 类型 | 说明 | 更新时机 |
|--------|------|------|---------|
| `due_time` | `DateTime` | 预期结束时间 | Agent 调用 `due_time` 接口时更新 |
| `begin_time` | `DateTime` | 开始时间 | 测试用例开始时设置 |
| `case_state` | `SmallInteger` | 执行状态 | 测试用例状态变更时更新 |
| `notify_state` | `SmallInteger` | 通知状态 | 邮件发送成功后更新为 1 |

---

## 🔗 相关接口

1. **测试用例结果上报**: `POST /api/v1/host/agent/testcase/result`
   - 更新 `case_state`（结束测试用例）
   - 一旦 `case_state` 不再是 1，`due_time` 接口将无法找到记录

2. **硬件信息上报**: `POST /api/v1/host/agent/hardware/report`
   - 创建或更新 `host_exec_log` 记录
   - 可能触发 `case_state = 1`（开始执行）

---

## 📈 性能考虑

### 1. 数据库查询优化

- ✅ 使用索引：`host_id`, `tc_id`, `case_state`, `del_flag` 组合索引
- ✅ 限制查询结果：`limit(1)` 只查询最新一条记录
- ✅ 按创建时间倒序：`order_by(HostExecLog.created_time.desc())`

### 2. 定时任务优化

- ✅ 批量查询：一次性查询所有超时记录
- ✅ 通知去重：只查询 `notify_state = 0` 的记录
- ✅ 配置缓存：`case_timeout` 配置缓存 1 小时

---

## 🐛 常见问题

### Q1: 为什么上报 `due_time` 后仍然收到超时通知？

**可能原因**:
1. `due_time` 计算错误（时区问题）
2. 定时任务检测时 `due_time` 已过期
3. 测试用例执行时间超出预期

**解决方案**:
- 检查 `due_time` 计算逻辑（确保使用 UTC 时间）
- 动态更新 `due_time`（如果执行时间超出预期）

### Q2: 为什么查询不到执行中的记录？

**可能原因**:
1. `case_state` 不是 1（测试用例已结束）
2. `tc_id` 不匹配
3. `host_id` 不匹配（token 中的 ID 不正确）

**解决方案**:
- 确认测试用例是否仍在执行中
- 检查 `tc_id` 是否正确
- 验证 token 中的 `host_id` 是否正确

### Q3: `due_time` 和 `begin_time + timeout_minutes` 的区别？

**区别**:
- `due_time`: Agent 主动上报的预期结束时间（精确）
- `begin_time + timeout_minutes`: 系统默认超时时间（回退方案）

**优先级**:
- 如果 `due_time` 存在，优先使用 `due_time`
- 如果 `due_time` 不存在，使用 `begin_time + timeout_minutes`

---

**最后更新**: 2025-01-30  
**文档版本**: 1.0.0

