# 测试文档与实际代码冲突分析报告

## 概述

本文档分析了 `docs/test-doc.md` 中测试用例与实际代码实现的冲突点，并提供了修改建议。

**分析日期**: 2025-01-30  
**文档版本**: test-doc.md v1.3

---

## 冲突点汇总

### 1. SIT-HOST-03: 获取VNC连接(占用) ❌

**测试文档描述**:
- 操作: 插件调用 `/api/v1/host/vnc/connect`
- 预期: `host_state` 变更为 **2** (已占用)

**实际代码行为**:
- `/api/v1/host/vnc/connect` 接口**只返回VNC连接信息**，**不会更新** `host_state`
- 实际更新 `host_state` 的时机：
  1. `/api/v1/host/vnc/report` 接口中，当 `connection_status="success"` 时，更新 `host_rec.host_state = 1`（已锁定），**不是2**
  2. `/api/v1/agent/vnc/report` 接口中，Agent上报VNC连接成功时，更新 `host_rec.host_state = 2`（已占用）

**修改建议**:
- 将测试用例拆分为两个：
  1. **SIT-HOST-03**: 获取VNC连接信息（不更新状态）
  2. **SIT-HOST-03A**: 上报VNC连接成功（更新 `host_state = 1` 或 `2`）

---

### 2. SIT-HOST-04: 释放主机资源 ❌

**测试文档描述**:
- 操作: 插件调用 `/api/v1/host/hosts/release`
- 预期: `host_rec.host_state` 变更为 **0** (空闲)

**实际代码行为**:
- `/api/v1/host/hosts/release` 接口**只逻辑删除** `host_exec_log` 记录（设置 `del_flag = 1`）
- **不会更新** `host_rec` 表的 `host_state` 字段
- 释放主机后，`host_rec.host_state` 仍保持原值（可能是 2 或 3）

**修改建议**:
- 修改验证点：只验证 `host_exec_log` 表的 `del_flag = 1`，不验证 `host_rec.host_state`
- 或者：添加说明，释放主机只是逻辑删除执行日志，不会自动重置主机状态

---

### 3. SIT-HOST-06: 下线 ❌

**测试文档描述**:
- 操作: 管理员 POST `/api/v1/host/admin/host/force-offline`
- 预期: `host_state = 7` (手动停用), `appr_state = 0` (停用)

**实际代码行为**:
- `/api/v1/host/admin/host/force-offline` 接口设置的是 `host_state = 4`（离线），**不是7**
- `appr_state` **不会更新**，保持原值
- `host_state = 7` 是"手动停用"功能，对应接口是 `/api/v1/host/admin/host/disable`

**修改建议**:
- 修改验证点：
  - `host_state = 4` (离线)
  - `appr_state` 保持不变（不更新）

---

### 4. SIT-TASK-04: 任务超时监控 ⚠️

**测试文档描述**:
- 操作: 修改 DB `begin_time` 为 2小时前，等待/触发定时任务
- 预期: `host_rec.host_state` 强制重置为 **0** (空闲)

**实际代码行为**:
- `case_timeout_task` 定时任务**只发送邮件通知**，**不会更新** `host_rec.host_state`
- 任务只更新 `host_exec_log.notify_state = 1`（已通知）
- 不会重置 `host_rec.host_state` 为 0

**修改建议**:
- 修改验证点：
  - `host_exec_log.notify_state = 1`（已通知）
  - 邮件通知已发送
  - **移除** `host_rec.host_state` 重置验证点

---

### 5. SIT-HOST-03: 接口路径确认 ✅

**测试文档描述**:
- 操作: 插件调用 `/api/v1/host/vnc/connect`

**实际代码路径**:
- ✅ 路径正确：`POST /api/v1/host/vnc/connect`

**无需修改**

---

### 6. SIT-HOST-04: 接口路径确认 ✅

**测试文档描述**:
- 操作: 插件调用 `/api/v1/host/hosts/release`

**实际代码路径**:
- ✅ 路径正确：`POST /api/v1/host/hosts/release`

**无需修改**

---

### 7. SIT-HOST-05: VNC历史重试接口路径 ⚠️

**测试文档描述**:
- 操作: 插件调用 `/api/v1/host/hosts/retry-vnc`

**实际代码路径**:
- ✅ 路径正确：`POST /api/v1/host/hosts/retry-vnc`

**无需修改**

---

### 8. SIT-HOST-10: 获取可用主机列表 ✅

**测试文档描述**:
- 操作: 插件调用 `/api/v1/host/hosts/available`

**实际代码路径**:
- ✅ 路径正确：`POST /api/v1/host/hosts/available`

**无需修改**

---

## 修改计划

### 优先级 P0（必须修改）

1. **SIT-HOST-03**: 拆分测试用例，明确VNC连接和状态更新的时机
2. **SIT-HOST-04**: 修改验证点，只验证执行日志删除，不验证主机状态重置
3. **SIT-HOST-06**: 修改验证点，`host_state = 4`（离线），不是7
4. **SIT-TASK-04**: 修改验证点，移除 `host_rec.host_state` 重置验证

### 优先级 P1（建议修改）

5. 补充说明：释放主机只是逻辑删除执行日志，不会自动重置主机状态
6. 补充说明：任务超时检测只发送邮件通知，不会自动重置主机状态

---

## 详细修改建议

### 修改1: SIT-HOST-03

**原描述**:
```
| **SIT-HOST-03** | 获取VNC连接(占用)   | Host状态=0 (空闲)      | 1. 插件调用 /api/v1/host/vnc/connect<br>2. 传入 host_id<br> | 1. **API**: 返回 VNC IP/Port/Pwd<br>2. **DB (host_rec)**:<br> - host_state 变更为 **2** (occ:已占用)<br> - updated_by 更新为当前用户ID<br> | P0     |
```

**修改后**:
```
| **SIT-HOST-03** | 获取VNC连接信息   | Host状态=0 (空闲)      | 1. 插件调用 /api/v1/host/vnc/connect<br>2. 传入 host_id<br> | 1. **API**: 返回 VNC IP/Port/Pwd<br>2. **DB (host_rec)**: 状态**不更新**（仍为0）<br> | P0     |
| **SIT-HOST-03A** | 上报VNC连接成功(占用)   | Host状态=0 (空闲)      | 1. 插件调用 /api/v1/host/vnc/report<br>2. 传入 connection_status="success"<br> | 1. **API**: 返回上报成功<br>2. **DB (host_rec)**:<br> - host_state 变更为 **1** (已锁定)<br>3. **DB (host_exec_log)**: 新增记录，host_state=1, case_state=0<br> | P0     |
| **SIT-HOST-03B** | Agent上报VNC连接成功(占用)   | Host状态=1 (已锁定)      | 1. Agent调用 /api/v1/agent/vnc/report<br>2. 从token中解析host_id<br> | 1. **API**: 返回上报成功<br>2. **DB (host_rec)**:<br> - host_state 变更为 **2** (已占用)<br> | P0     |
```

### 修改2: SIT-HOST-04

**原描述**:
```
| **SIT-HOST-04** | 释放主机资源        | Host状态=2 (占用)      | 1. 插件调用 /api/v1/host/hosts/release | 1. **DB (host_rec)**: host_state 变更为 **0** (free:空闲)<br>2. **WS**: 服务端向 Agent 推送断开连接指令<br>3. **Agent**: (Mock) 收到 Kill VNC 指令 | P0     |
```

**修改后**:
```
| **SIT-HOST-04** | 释放主机资源        | Host状态=2 (占用)      | 1. 插件调用 /api/v1/host/hosts/release | 1. **DB (host_exec_log)**: 逻辑删除记录（del_flag = 1）<br>2. **DB (host_rec)**: host_state **保持不变**（仍为2或3）<br>3. **注意**: 释放主机只是逻辑删除执行日志，不会自动重置主机状态<br> | P0     |
```

### 修改3: SIT-HOST-06

**原描述**:
```
| **SIT-HOST-06** | 下线                | Host在线且占用         | 1. 管理员 POST /api/v1/host/admin/host/force-offline | 1. **DB (host_rec)**:<br> - host_state = **7** (disable:手动停用)<br> - appr_state = **0** (disable:停用)<br>2. **Redis**: 频道 websocket:unicast:{id} 收到消息<br>3. **WS**: 仅目标 Agent 收到下线指令 | P1     |
```

**修改后**:
```
| **SIT-HOST-06** | 强制下线                | Host在线且空闲（host_state=0）         | 1. 管理员 POST /api/v1/host/admin/host/force-offline | 1. **DB (host_rec)**:<br> - host_state = **4** (offline:离线)<br> - appr_state **保持不变**<br>2. **Redis**: 频道 websocket:unicast:{id} 收到消息<br>3. **WS**: 仅目标 Agent 收到下线指令 | P1     |
| **SIT-HOST-06A** | 手动停用                | Host存在         | 1. 管理员调用停用接口 | 1. **DB (host_rec)**:<br> - host_state = **7** (disable:手动停用)<br> - appr_state = **0** (disable:停用)<br> | P1     |
```

### 修改4: SIT-TASK-04

**原描述**:
```
| **SIT-TASK-04** | 任务超时监控 | 构造超时数据  | 1. 修改 DB begin_time 为 2小时前<br>2. 等待/触发定时任务<br> | 1. **Redis**: 读取 sys_conf:case_timeout 配置<br>2. **WS**: 向 Agent 发送终止指令<br>3. **DB (host_exec_log)**: case_state 更新为超时状态 (如 3)<br>4. **DB (host_rec)**: 强制重置为 **0** (free) | P1     |
```

**修改后**:
```
| **SIT-TASK-04** | 任务超时监控 | 构造超时数据  | 1. 修改 DB begin_time 为 2小时前<br>2. 等待/触发定时任务<br> | 1. **Redis**: 读取 sys_conf:case_timeout 配置<br>2. **Email**: 发送超时邮件通知<br>3. **DB (host_exec_log)**: notify_state 更新为 **1** (已通知)<br>4. **注意**: 任务超时检测只发送邮件通知，不会自动重置主机状态或发送WS终止指令 | P1     |
```

---

## 总结

### 冲突统计

- **严重冲突**: 4个（P0）
- **轻微冲突**: 2个（P1）
- **路径正确**: 4个（无需修改）

### 建议

1. **立即修改** P0 冲突点，确保测试用例与实际代码一致
2. **补充说明** 释放主机和任务超时的实际行为
3. **拆分测试用例** 将VNC连接流程拆分为多个步骤，更清晰地描述状态变更时机

---

**最后更新**: 2025-01-30  
**分析人员**: AI Assistant  
**待确认**: 等待用户确认后执行修改

