# approve_hosts 接口详细逻辑文档

## 📋 接口概述

**接口路径**: `POST /api/v1/admin-appr-host/approve`

**功能描述**: 同意启用待审批主机，更新硬件记录和主机状态，并调用外部硬件接口同步硬件配置。

**接口位置**:

- API 端点: `services/host-service/app/api/v1/endpoints/admin_appr_host.py:304`
- 服务层: `services/host-service/app/services/admin_appr_host_service.py:811`

---

## 🔄 完整业务流程

### 1. 参数验证和预处理

#### 1.1 diff_type = 2（内容变化）

- **host_ids 必填**: 如果未传入或为空，抛出 `HOST_IDS_REQUIRED` 错误
- **处理逻辑**: 使用传入的 `host_ids` 列表

#### 1.2 diff_type = 1（版本号变化）

- **情况A**: 如果传入了 `host_ids`，逻辑与 `diff_type = 2` 相同
- **情况B**: 如果未传入 `host_ids`，自动查询所有符合条件的 `host_id`:

  ```sql
  SELECT DISTINCT host_id 
  FROM host_hw_rec 
  WHERE sync_state = 1 
    AND diff_state = 1 
    AND del_flag = 0
  ```

- **空结果处理**: 如果未找到符合条件的记录，返回空结果（`success_count=0, failed_count=0`）

#### 1.3 diff_type 验证

- 如果 `diff_type` 不是 1 或 2，抛出 `DIFF_TYPE_NOT_SUPPORTED` 错误

---

### 2. 批量数据查询（优化：避免 N+1 查询）

#### 2.1 批量查询主机记录

```python
SELECT * FROM host_rec 
WHERE id IN (host_ids) 
  AND del_flag = 0
```

- 结果存储在 `host_recs_map` 字典中，以 `host_id` 为键

#### 2.2 批量查询硬件记录

```python
SELECT * FROM host_hw_rec 
WHERE host_id IN (host_ids) 
  AND sync_state = 1 
  AND del_flag = 0
ORDER BY host_id, created_time DESC, id DESC
```

- 结果按 `host_id` 组织到 `hw_recs_by_host` 字典中

---

### 3. 逐个主机处理循环

对每个 `host_id` 执行以下步骤：

#### 3.1 验证主机存在性

- 检查 `host_recs_map` 中是否存在该主机
- **失败处理**: 记录错误，`failed_count++`，继续处理下一个主机

#### 3.2 验证硬件记录存在性

- 检查 `hw_recs_by_host` 中是否存在该主机的硬件记录
- **失败处理**: 记录错误，`failed_count++`，继续处理下一个主机

#### 3.3 获取最新硬件记录

- 从已排序的硬件记录列表中取第一条（`hw_recs[0]`）
- 该记录将被设置为 `sync_state = 2`（已审批）

#### 3.4 收集更新数据

- **最新硬件记录ID**: 添加到 `latest_hw_ids_to_update` 列表
- **其他硬件记录ID**: 添加到 `other_hw_ids_to_update` 列表
- **主机更新信息**: 存储到 `host_updates` 字典

---

### 4. ⚠️ **外部硬件接口调用**（关键步骤）

#### 4.1 调用条件

- 仅当硬件记录中存在 `hw_info` 字段时调用
- 如果 `hw_info` 为空，记录警告日志并跳过

#### 4.2 提取配置信息

```python
# 提取 dmr_config
dmr_config = latest_hw_rec.hw_info.get("dmr_config")

# 提取配置名称（优先从 dmr_config 中提取 host_name）
name = _get_hardware_name_from_hw_info(hw_info, host_rec)
```

#### 4.3 判断新增或修改

- **新增**: 如果 `host_rec.hardware_id` 为空，调用新增接口
- **修改**: 如果 `host_rec.hardware_id` 不为空，调用修改接口

#### 4.4 外部接口调用详情

**接口配置**:

- **URL**: 通过环境变量 `HARDWARE_API_URL` 配置，默认值: `http://hardware-service:8000`
- **Mock 模式**: 通过环境变量 `USE_HARDWARE_MOCK` 控制（`true/1/yes` 启用）

**新增硬件接口**:

```
POST {HARDWARE_API_URL}/api/v1/hardware/
Content-Type: application/json

{
  "name": "配置名称",
  "dmr_config": { ... }
}
```

**响应处理**:

- 成功状态码: `200` 或 `201`
- 从响应中提取 `hardware_id` 或 `id` 字段
- 如果响应格式错误，抛出 `HARDWARE_INVALID_RESPONSE` 错误

**修改硬件接口**:

```
PUT {HARDWARE_API_URL}/api/v1/hardware/{hardware_id}
Content-Type: application/json

{
  "dmr_config": { ... }
}
```

**响应处理**:

- 成功状态码: `200` 或 `204`
- 返回原 `hardware_id`

#### 4.5 错误处理

- **业务错误**: 直接抛出 `BusinessError`，导致该主机处理失败
- **系统异常**: 捕获异常并包装为 `BusinessError`，错误码: `HARDWARE_API_CALL_FAILED`
- **失败影响**: 如果外部接口调用失败，该主机的整个审批流程失败，不会更新数据库

#### 4.6 更新 hardware_id

- 如果外部接口调用成功，将返回的 `hardware_id` 更新到:
  - `host_rec.hardware_id` 字段
  - `host_hw_rec.hardware_id` 字段（最新记录）

---

### 5. 批量数据库更新

#### 5.1 更新最新硬件记录

```sql
UPDATE host_hw_rec 
SET sync_state = 2,
    appr_time = NOW(),
    appr_by = {appr_by},
    hardware_id = {hardware_id}  -- 如果外部接口返回了 hardware_id
WHERE id IN (latest_hw_ids)
```

#### 5.2 更新其他硬件记录

```sql
UPDATE host_hw_rec 
SET sync_state = 4
WHERE id IN (other_hw_ids)
```

#### 5.3 更新主机记录

```sql
UPDATE host_rec 
SET appr_state = 1,
    host_state = 0,
    hw_id = {latest_hw_id},
    subm_time = NOW(),
    hardware_id = {hardware_id}  -- 如果外部接口返回了 hardware_id
WHERE id IN (host_ids)
```

#### 5.4 事务提交

- 所有更新操作在一个事务中执行
- 如果任何步骤失败，整个事务回滚

---

### 6. 📧 邮件通知（事务提交后执行）

#### 6.1 查询邮箱配置

```sql
SELECT conf_val 
FROM sys_conf 
WHERE conf_key = 'email' 
  AND state_flag = 0 
  AND del_flag = 0
```

#### 6.2 邮箱地址处理

- 支持多个邮箱，以半角逗号分隔
- 去除空格和空值
- 如果配置为空，跳过邮件发送

#### 6.3 查询审批人信息

```sql
SELECT user_name, user_account 
FROM sys_user 
WHERE id = {appr_by} 
  AND del_flag = 0
```

#### 6.4 查询主机信息

```sql
SELECT hardware_id, host_ip 
FROM host_rec 
WHERE id IN (successful_host_ids) 
  AND del_flag = 0
```

#### 6.5 构建邮件内容

- **主题**: "变更 Host 通过硬件变更审核"（支持多语言）
- **内容**: HTML 格式，包含:
  - 审批人信息（用户名称、登录账号）
  - 变更的主机信息表格（Hardware ID、Host IP）

#### 6.6 发送邮件

- 调用 `send_email()` 函数发送邮件
- **失败处理**: 邮件发送失败不影响全局事务，错误信息记录到 `email_notification_errors` 列表

#### 6.7 错误信息记录

- 如果邮件发送失败，错误信息会添加到响应结果的 `results` 列表中:

```json
{
  "type": "email_notification",
  "success": false,
  "message": "邮件发送异常: ..."
}
```

---

## 📊 响应数据结构

### 成功响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "success_count": 5,
    "failed_count": 0,
    "results": [
      {
        "host_id": 123,
        "success": true,
        "message": "主机启用成功",
        "hw_id": 456,
        "hardware_id": "hw-789"
      },
      ...
    ]
  }
}
```

### 部分失败响应

```json
{
  "code": 200,
  "message": "操作完成",
  "data": {
    "success_count": 3,
    "failed_count": 2,
    "results": [
      {
        "host_id": 123,
        "success": true,
        "message": "主机启用成功",
        "hw_id": 456,
        "hardware_id": "hw-789"
      },
      {
        "host_id": 124,
        "success": false,
        "message": "未找到待审批的硬件记录（ID: 124）"
      },
      {
        "type": "email_notification",
        "success": false,
        "message": "邮件发送异常: ..."
      }
    ]
  }
}
```

---

## 🔍 关键特性总结

### ✅ 包含外部接口调用

**是的，`approve_hosts` 接口包含外部硬件接口调用！**

1. **调用时机**: 在处理每个主机的审批流程中（步骤 4）
2. **接口类型**:
   - 新增硬件: `POST /api/v1/hardware/`
   - 修改硬件: `PUT /api/v1/hardware/{hardware_id}`
3. **配置方式**: 通过环境变量 `HARDWARE_API_URL` 配置接口地址
4. **Mock 支持**: 通过环境变量 `USE_HARDWARE_MOCK` 启用 Mock 模式
5. **失败影响**: 外部接口调用失败会导致该主机的审批流程失败，事务回滚

### ✅ 包含邮件通知

1. **通知时机**: 在所有数据库操作提交成功后（步骤 6）
2. **通知内容**: 审批人信息和变更的主机信息
3. **失败处理**: 邮件发送失败不影响全局事务，错误信息记录到响应中

### ✅ 事务管理

- 所有数据库操作在一个事务中执行
- 如果任何步骤失败（包括外部接口调用失败），整个事务回滚
- 邮件通知在事务提交后执行，失败不影响数据一致性

### ✅ 性能优化

- 批量查询主机和硬件记录，避免 N+1 查询问题
- 批量更新数据库记录，提高更新效率

---

## 🚨 错误处理

### 参数验证错误

- `HOST_IDS_REQUIRED`: diff_type=2 时 host_ids 必填
- `DIFF_TYPE_NOT_SUPPORTED`: diff_type 不支持

### 业务逻辑错误

- `HOST_NOT_FOUND`: 主机不存在或已删除
- `HARDWARE_NOT_FOUND`: 未找到待审批的硬件记录
- `MISSING_DMR_CONFIG`: 硬件信息中缺少 dmr_config 字段

### 外部接口错误

- `HARDWARE_CREATE_FAILED`: 调用硬件接口失败（新增）
- `HARDWARE_UPDATE_FAILED`: 调用硬件接口失败（修改）
- `HARDWARE_INVALID_RESPONSE`: 硬件接口返回数据格式错误
- `HARDWARE_API_ERROR`: 调用硬件接口异常

### 系统错误

- `APPROVE_HOST_FAILED`: 同意启用主机失败（通用错误）

---

## 📝 环境变量配置

```bash
# 硬件接口 URL（必填）
HARDWARE_API_URL=http://hardware-service:8000

# 是否使用 Mock 硬件接口（可选，默认 false）
USE_HARDWARE_MOCK=false
```

---

## 🔗 相关文件

- **API 端点**: `services/host-service/app/api/v1/endpoints/admin_appr_host.py`
- **服务层**: `services/host-service/app/services/admin_appr_host_service.py`
- **外部接口调用函数**: `_call_hardware_api()` (第280-459行)
- **邮件发送函数**: `shared/common/email_sender.py`
- **HTTP 客户端**: `shared/common/http_client.py`

---

## 📅 更新历史

- **2025-01-29**: 初始版本，整理 `approve_hosts` 接口完整逻辑
- **核心内容**:
  - 详细业务流程（6个主要步骤）
  - 外部硬件接口调用逻辑
  - 邮件通知机制
  - 事务管理和错误处理
  - 性能优化说明
