# 上报 VNC 连接结果 API 更新文档

## 📋 更新概述

上报 VNC 连接结果 API 已更新，新增了多个请求参数，并优化了业务逻辑以支持执行日志的自动管理。

## 🔄 更新内容

### 1. 新增请求参数

| 参数名 | 类型 | 必填 | 说明 | 新增/原有 |
|-------|------|------|------|----------|
| user_id | string | ✅ | 用户ID | 原有 |
| **tc_id** | string | ✅ | 执行测试ID | **新增** |
| **cycle_name** | string | ✅ | 周期名称 | **新增** |
| **user_name** | string | ✅ | 用户名称 | **新增** |
| host_id | string | ✅ | 主机ID | 原有 |
| connection_status | string | ✅ | 连接状态 (success/failed) | 原有 |
| connection_time | datetime | ✅ | VNC 连接时间 | 原有 |

### 2. 业务逻辑优化

#### 原业务逻辑
1. 验证主机是否存在
2. 更新 `host_rec` 表：`host_state = 1`, `subm_time = 当前时间`

#### 新业务逻辑
1. 验证主机是否存在
2. **如果 `connection_status = "success"`**：
   - 查询 `host_exec_log` 表：
     - 条件：`user_id`、`tc_id`、`cycle_name`、`user_name`、`host_id`、`del_flag=0`
   - **如果存在旧记录**：先逻辑删除旧记录（`del_flag = 1`）
   - **无论是否存在旧记录**：都新增一条新记录
     - `host_state = 1`（已锁定）
     - `case_state = 0`（空闲）
     - `begin_time = 当前时间`
     - `del_flag = 0`
3. 更新 `host_rec` 表：`host_state = 1`, `subm_time = 当前时间`

## 📝 API 端点信息

### 基本信息
- **URL**: `POST /api/v1/host/vnc/report`
- **认证**: 需要有效的 JWT 令牌
- **Content-Type**: `application/json`

### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/host/vnc/report" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1852278641262084097",
    "tc_id": "1852278641262084097",
    "cycle_name": "gkvk@poxe.vlli",
    "user_name": "gkvk@poxe.vlli",
    "host_id": "1852278641262084097",
    "connection_status": "success",
    "connection_time": "2025-10-11T10:30:00Z"
  }'
```

### 请求 Body

```json
{
  "user_id": "1852278641262084097",
  "tc_id": "1852278641262084097",
  "cycle_name": "gkvk@poxe.vlli",
  "user_name": "gkvk@poxe.vlli",
  "host_id": "1852278641262084097",
  "connection_status": "success",
  "connection_time": "2025-10-11T10:30:00Z"
}
```

### 成功响应 (200 OK)

```json
{
  "code": 200,
  "message": "VNC连接结果上报成功",
  "data": {
    "host_id": "1852278641262084097",
    "connection_status": "success",
    "connection_time": "2025-10-11T10:30:00Z",
    "message": "VNC连接结果上报成功，主机已锁定，执行日志已created"
  },
  "timestamp": "2025-10-29T08:00:00Z"
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|-------|------|------|
| code | integer | HTTP 状态码 |
| message | string | 响应消息 |
| data.host_id | string | 主机ID |
| data.connection_status | string | 连接状态 |
| data.connection_time | datetime | 连接时间 |
| data.message | string | 处理结果消息 |

#### data.message 可能的值
- `"VNC连接结果上报成功，主机已锁定"` - 连接状态为 failed 或其他
- `"VNC连接结果上报成功，主机已锁定，执行日志已deleted_and_created"` - 找到旧记录，先逻辑删除旧记录，然后新增新记录
- `"VNC连接结果上报成功，主机已锁定，执行日志已created"` - 未找到旧记录，直接新增新记录

### 错误响应

#### 400 Bad Request - 主机不存在

```json
{
  "code": 400,
  "message": "主机不存在: 1852278641262084097",
  "error_code": "HOST_NOT_FOUND",
  "timestamp": "2025-10-29T08:00:00Z"
}
```

#### 400 Bad Request - 主机ID格式无效

```json
{
  "code": 400,
  "message": "主机ID格式无效",
  "error_code": "INVALID_HOST_ID",
  "timestamp": "2025-10-29T08:00:00Z"
}
```

## 🔍 使用场景

### 场景1：首次上报 VNC 连接成功

**请求**:
```json
{
  "user_id": "user123",
  "tc_id": "test001",
  "cycle_name": "cycle_001",
  "user_name": "John Doe",
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T10:00:00Z"
}
```

**处理流程**:
1. 验证主机 123 存在
2. 查询 `host_exec_log` 表，未找到匹配记录
3. 直接新增执行日志记录：
   - `host_state = 1` (已锁定)
   - `case_state = 0` (空闲)
   - `begin_time = 当前时间`
4. 更新 `host_rec` 表：`host_state = 1`

**响应**:
```json
{
  "code": 200,
  "message": "VNC连接结果上报成功",
  "data": {
    "message": "VNC连接结果上报成功，主机已锁定，执行日志已created"
  }
}
```

### 场景2：重复上报相同测试的 VNC 连接

**请求**:
```json
{
  "user_id": "user123",
  "tc_id": "test001",
  "cycle_name": "cycle_001",
  "user_name": "John Doe",
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T11:00:00Z"
}
```

**处理流程**:
1. 验证主机 123 存在
2. 查询 `host_exec_log` 表，找到已存在的旧记录
3. 先逻辑删除旧记录：`del_flag = 1`
4. 然后新增一条新记录：
   - `host_state = 1` (已锁定)
   - `case_state = 0` (空闲)
   - `begin_time = 当前时间`
5. 更新 `host_rec` 表：`host_state = 1`

**响应**:
```json
{
  "code": 200,
  "message": "VNC连接结果上报成功",
  "data": {
    "message": "VNC连接结果上报成功，主机已锁定，执行日志已deleted_and_created"
  }
}
```

### 场景3：上报 VNC 连接失败

**请求**:
```json
{
  "user_id": "user123",
  "tc_id": "test001",
  "cycle_name": "cycle_001",
  "user_name": "John Doe",
  "host_id": "123",
  "connection_status": "failed",
  "connection_time": "2025-10-29T10:00:00Z"
}
```

**处理流程**:
1. 验证主机 123 存在
2. 跳过 `host_exec_log` 表的处理（只在 success 时处理）
3. 更新 `host_rec` 表：`host_state = 1`

**响应**:
```json
{
  "code": 200,
  "message": "VNC连接结果上报成功",
  "data": {
    "message": "VNC连接结果上报成功，主机已锁定"
  }
}
```

## 🗄️ 数据库操作说明

### 涉及的表

#### 1. host_rec 表
- **操作**: UPDATE
- **条件**: `id = host_id AND del_flag = 0`
- **更新字段**:
  - `host_state = 1` (已锁定)
  - `subm_time = 当前时间`

#### 2. host_exec_log 表
- **操作**: SELECT + UPDATE 或 INSERT
- **查询条件**:
  ```sql
  SELECT * FROM host_exec_log
  WHERE user_id = :user_id
    AND tc_id = :tc_id
    AND cycle_name = :cycle_name
    AND user_name = :user_name
    AND host_id = :host_id
    AND del_flag = 0;
  ```
- **如果存在记录**:
  ```sql
  UPDATE host_exec_log
  SET del_flag = 1
  WHERE id = :existing_log_id;
  ```
- **如果不存在记录**:
  ```sql
  INSERT INTO host_exec_log (
    host_id, user_id, tc_id, cycle_name, user_name,
    host_state, case_state, begin_time, del_flag
  ) VALUES (
    :host_id, :user_id, :tc_id, :cycle_name, :user_name,
    1, 0, NOW(), 0
  );
  ```

## 🔒 安全考虑

1. **认证验证**: 需要有效的 JWT Token
2. **数据验证**: 所有必填字段都进行验证
3. **主机ID验证**: 验证主机ID格式和存在性
4. **事务支持**: 所有数据库操作在事务中执行，确保数据一致性
5. **日志记录**: 详细记录所有操作，便于审计和调试

## 📊 监控和日志

### 关键日志字段

```json
{
  "operation": "report_vnc_connection",
  "user_id": "user123",
  "tc_id": "test001",
  "cycle_name": "cycle_001",
  "user_name": "John Doe",
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T10:00:00Z",
  "old_host_state": 0,
  "new_host_state": 1,
  "exec_log_action": "created"
}
```

### exec_log_action 值说明
- `null`: 连接状态不是 success，未处理执行日志
- `"deleted"`: 找到已存在的执行日志并逻辑删除
- `"created"`: 未找到执行日志，新增记录

## 🔄 向后兼容性

### ⚠️ 重大变更
此更新包含 **破坏性变更**，新增了 3 个必填参数：
- `tc_id`
- `cycle_name`
- `user_name`

### 迁移指南

#### 旧版本请求（不再支持）
```json
{
  "user_id": "user123",
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T10:00:00Z"
}
```

#### 新版本请求（必须）
```json
{
  "user_id": "user123",
  "tc_id": "test001",           // 新增：必填
  "cycle_name": "cycle_001",   // 新增：必填
  "user_name": "John Doe",     // 新增：必填
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T10:00:00Z"
}
```

### 客户端升级步骤

1. **更新请求数据结构**：添加 `tc_id`、`cycle_name`、`user_name` 字段
2. **更新响应处理**：处理新的响应消息格式
3. **测试验证**：在测试环境验证新旧场景
4. **生产部署**：确保所有客户端同步更新

## 📝 更新历史

- **2025-10-29**: 初始版本
  - 新增 `tc_id`、`cycle_name`、`user_name` 请求参数
  - 优化业务逻辑，支持执行日志自动管理
  - 连接成功时自动创建或逻辑删除执行日志

## 🔗 相关文件

- [services/host-service/app/api/v1/endpoints/vnc.py](../../services/host-service/app/api/v1/endpoints/vnc.py) - API 端点定义
- [services/host-service/app/services/vnc_service.py](../../services/host-service/app/services/vnc_service.py) - 业务逻辑实现
- [services/host-service/app/schemas/host.py](../../services/host-service/app/schemas/host.py) - 请求/响应模型
- [services/host-service/app/models/host_exec_log.py](../../services/host-service/app/models/host_exec_log.py) - 执行日志模型
- [services/host-service/app/models/host_rec.py](../../services/host-service/app/models/host_rec.py) - 主机记录模型

