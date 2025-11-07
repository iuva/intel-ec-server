# 数据库索引优化建议

## 📊 索引使用情况分析

### ✅ 已有索引（已验证）

#### BaseDBModel（所有表继承）
- `del_flag` - 软删除标记（已在 BaseDBModel 中定义 `index=True`）

#### host_rec 表
- `host_no` - 主机主键（模型中有 `index=True`）
- `tcp_state` - TCP在线状态（模型中有 `index=True`）
- `mg_id` - 唯一引导ID（SQL 文件中有索引 `ix_mg`）
- `mac_addr` - MAC地址（SQL 文件中有索引 `ix_mac`）
- `appr_state` - 审批状态（SQL 文件中有索引 `ix_as`）
- `subm_time` - 申报时间（SQL 文件中有索引 `ix_st`）

#### host_exec_log 表
- `host_id` - 主机主键（模型中有 `index=True`）
- `user_id` - 执行用户（模型中有 `index=True`）
- `host_state` - 主机状态（模型中有 `index=True`）
- `created_time` - 创建时间（SQL 文件中有索引 `ix_ct`）

#### host_hw_rec 表
- `host_id` - 主机主键（模型中有 `index=True`）

#### sys_conf 表
- `conf_key` - 配置键（模型中有 `index=True`）

### ⚠️ 建议添加的索引

#### host_rec 表
```sql
-- 建议添加复合索引（如果经常同时查询这些字段）
CREATE INDEX `ix_host_state_appr_del` ON host_rec (`host_state`, `appr_state`, `del_flag`);
CREATE INDEX `ix_created_time` ON host_rec (`created_time` DESC);
```

**原因**：
- `host_state` 和 `appr_state` 经常在 WHERE 条件中同时使用
- `created_time` 用于排序，添加索引可提升排序性能

#### host_exec_log 表
```sql
-- 建议添加 case_state 索引（常用查询字段）
CREATE INDEX `ix_case_state` ON host_exec_log (`case_state`);
-- 建议添加复合索引（用于超时查询）
CREATE INDEX `ix_host_case_begin_del` ON host_exec_log (`host_state`, `case_state`, `begin_time`, `del_flag`);
-- 建议添加 tc_id 索引（如果经常按测试用例查询）
CREATE INDEX `ix_tc_id` ON host_exec_log (`tc_id`);
```

**原因**：
- `case_state` 在多个查询中使用（如 `get_retry_vnc_list`）
- 超时查询需要同时使用 `host_state`, `case_state`, `begin_time`, `del_flag`
- `tc_id` 用于查询特定测试用例的执行记录

#### host_hw_rec 表
```sql
-- 建议添加 sync_state 和 diff_state 索引（常用查询字段）
CREATE INDEX `ix_sync_state` ON host_hw_rec (`sync_state`, `del_flag`);
CREATE INDEX `ix_diff_state` ON host_hw_rec (`diff_state`, `del_flag`);
-- 建议添加复合索引（用于审批查询）
CREATE INDEX `ix_host_sync_diff_del` ON host_hw_rec (`host_id`, `sync_state`, `diff_state`, `del_flag`);
-- 建议添加 created_time 索引（用于排序）
CREATE INDEX `ix_created_time` ON host_hw_rec (`created_time` DESC, `id` DESC);
```

**原因**：
- `sync_state` 和 `diff_state` 在审批流程中频繁查询
- 审批查询需要同时使用 `host_id`, `sync_state`, `diff_state`
- `created_time` 用于获取最新记录

## 🔍 查询模式分析

### 常用查询模式

1. **主机列表查询**（`admin_host_service.list_hosts`）
   - WHERE: `host_state < 5`, `appr_state = 1`, `del_flag = 0`
   - ORDER BY: `created_time DESC`
   - **建议索引**: `(host_state, appr_state, del_flag, created_time)`

2. **待审批主机查询**（`admin_appr_host_service.list_appr_hosts`）
   - WHERE: `appr_state = 0`, `del_flag = 0`
   - JOIN: `host_hw_rec` WHERE `sync_state = 1`, `diff_state = 1`
   - **建议索引**: `host_rec(appr_state, del_flag)`, `host_hw_rec(sync_state, diff_state, del_flag)`

3. **执行日志查询**（`browser_host_service.get_retry_vnc_list`）
   - WHERE: `user_id = ?`, `case_state != 2`, `del_flag = 0`
   - **建议索引**: `(user_id, case_state, del_flag)`

4. **超时查询**（`case_timeout_task._query_timeout_cases`）
   - WHERE: `host_state IN (2, 3)`, `case_state = 1`, `del_flag = 0`, `begin_time < ?`
   - **建议索引**: `(host_state, case_state, del_flag, begin_time)`

## 📝 实施建议

### 优先级

**高优先级**（立即实施）：
1. `host_exec_log.case_state` - 常用查询字段
2. `host_hw_rec.sync_state` - 审批流程核心字段
3. `host_hw_rec.diff_state` - 审批流程核心字段

**中优先级**（近期实施）：
1. `host_exec_log` 复合索引 `(host_state, case_state, begin_time, del_flag)`
2. `host_hw_rec` 复合索引 `(host_id, sync_state, diff_state, del_flag)`
3. `host_rec` 复合索引 `(host_state, appr_state, del_flag)`

**低优先级**（按需实施）：
1. `host_exec_log.tc_id` - 如果经常按测试用例查询
2. `host_rec.created_time` - 如果数据量很大

### 注意事项

1. **索引维护成本**：每个索引都会增加写入操作的开销
2. **复合索引顺序**：将选择性高的字段放在前面
3. **覆盖索引**：如果查询只需要索引字段，可以避免回表查询
4. **定期监控**：使用 `EXPLAIN` 分析查询计划，确认索引被使用

## 🔧 创建索引的 SQL 语句

```sql
-- host_exec_log 表索引
CREATE INDEX `ix_case_state` ON host_exec_log (`case_state`);
CREATE INDEX `ix_host_case_begin_del` ON host_exec_log (`host_state`, `case_state`, `begin_time`, `del_flag`);
CREATE INDEX `ix_tc_id` ON host_exec_log (`tc_id`);

-- host_hw_rec 表索引
CREATE INDEX `ix_sync_state` ON host_hw_rec (`sync_state`, `del_flag`);
CREATE INDEX `ix_diff_state` ON host_hw_rec (`diff_state`, `del_flag`);
CREATE INDEX `ix_host_sync_diff_del` ON host_hw_rec (`host_id`, `sync_state`, `diff_state`, `del_flag`);
CREATE INDEX `ix_created_time` ON host_hw_rec (`created_time` DESC, `id` DESC);

-- host_rec 表索引（如果不存在）
CREATE INDEX `ix_host_state_appr_del` ON host_rec (`host_state`, `appr_state`, `del_flag`);
CREATE INDEX `ix_created_time` ON host_rec (`created_time` DESC);
```

## 📊 性能影响评估

### 预期改进

1. **查询性能**：
   - 主机列表查询：预计提升 30-50%
   - 待审批主机查询：预计提升 40-60%
   - 执行日志查询：预计提升 50-70%

2. **写入性能**：
   - 索引维护开销：预计增加 5-10% 写入时间
   - 对于读多写少的场景，收益明显大于成本

### 监控指标

建议监控以下指标：
- 查询执行时间（慢查询日志）
- 索引使用率（`SHOW INDEX FROM table_name`）
- 表大小和索引大小
- 写入操作性能

---

**最后更新**: 2025-01-29
**状态**: 建议实施
**优先级**: 高优先级索引建议立即实施

