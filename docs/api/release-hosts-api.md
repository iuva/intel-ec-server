# 释放主机 API 文档

## API 概述

释放主机 API 用于逻辑删除 `host_exec_log` 表中指定用户的主机执行记录（设置 `del_flag = 1`），释放主机资源。

## 端点信息

- **URL**: `POST /api/v1/host/hosts/release`
- **方法**: POST
- **认证**: 需要有效的 JWT 令牌

## 业务逻辑

逻辑删除 `host_exec_log` 表中的记录（设置 `del_flag = 1`）：
- 条件1: `user_id = 入参的 user_id`
- 条件2: `host_id IN (host_list)`
- 条件3: `del_flag = 0`（只删除未删除的记录）

这是一个软删除操作，数据不会被物理删除，只是将 `del_flag` 标记为 1。

## 请求参数

### Headers
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

### Body Parameters

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| user_id | string | 是 | 用户ID |
| host_list | array[string] | 是 | 主机ID列表 |

### 请求示例

```bash
# 使用 curl 调用
curl -X POST "http://localhost:8000/api/v1/host/hosts/release" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "adb1852278641262sdf097",
    "host_list": [
        "1852278641262084097",
        "1852278641262084098"
    ]
  }'
```

```json
// 请求 Body
{
  "user_id": "adb1852278641262sdf097",
  "host_list": [
    "1852278641262084097",
    "1852278641262084098"
  ]
}
```

## 响应格式

### 成功响应 (200 OK)

```json
{
  "updated_count": 5,
  "user_id": "adb1852278641262sdf097",
  "host_list": [
    "1852278641262084097",
    "1852278641262084098"
  ]
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|-------|------|------|
| updated_count | integer | 实际更新的记录数（逻辑删除） |
| user_id | string | 用户ID |
| host_list | array[string] | 主机ID列表 |

### 错误响应

#### 400 Bad Request - 主机ID格式错误
```json
{
  "code": 400,
  "message": "主机ID格式无效",
  "error_code": "INVALID_HOST_ID"
}
```

#### 401 Unauthorized - 未授权
```json
{
  "code": 401,
  "message": "未授权访问",
  "error_code": "UNAUTHORIZED"
}
```

#### 500 Internal Server Error - 服务器错误
```json
{
  "code": 500,
  "message": "释放主机失败",
  "error_code": "RELEASE_HOSTS_FAILED"
}
```

## 使用场景

### 场景1：释放单个主机
用户完成测试后，释放一个主机。

```bash
# 请求
POST /api/v1/host/hosts/release
{
  "user_id": "user123",
  "host_list": ["1852278641262084097"]
}

# 响应
{
  "updated_count": 2,
  "user_id": "user123",
  "host_list": ["1852278641262084097"]
}
```

### 场景2：批量释放多个主机
用户完成测试后，批量释放多个主机。

```bash
# 请求
POST /api/v1/host/hosts/release
{
  "user_id": "user123",
  "host_list": [
    "1852278641262084097",
    "1852278641262084098",
    "1852278641262084099"
  ]
}

# 响应
{
  "updated_count": 8,
  "user_id": "user123",
  "host_list": [
    "1852278641262084097",
    "1852278641262084098",
    "1852278641262084099"
  ]
}
```

### 场景3：释放不存在的主机
尝试释放不存在的主机记录或已删除的记录。

```bash
# 请求
POST /api/v1/host/hosts/release
{
  "user_id": "user123",
  "host_list": ["9999999999999999999"]
}

# 响应（updated_count 为 0）
{
  "updated_count": 0,
  "user_id": "user123",
  "host_list": ["9999999999999999999"]
}
```

## 数据库操作说明

### SQL 更新语句（逻辑删除）
```sql
UPDATE host_exec_log
SET del_flag = 1
WHERE user_id = 'adb1852278641262sdf097'
  AND host_id IN (1852278641262084097, 1852278641262084098)
  AND del_flag = 0;
```

### 注意事项

1. **软删除**: 这是一个软删除操作，数据不会被物理删除，只是将 `del_flag` 设置为 1
2. **数据恢复**: 如果需要，可以通过将 `del_flag` 设置回 0 来恢复数据
3. **批量操作**: 支持批量删除多个主机的记录
4. **返回值**: `updated_count` 表示实际更新的记录数，可能少于 `host_list` 的长度（如果某些主机没有对应记录或已删除）
5. **权限控制**: 只删除指定 `user_id` 的记录，避免误删其他用户的数据
6. **重复删除**: 多次对同一记录执行删除操作，只有第一次会生效（del_flag 已为 1 的记录不会被更新）

## 测试步骤

### 1. 获取 JWT Token
```bash
# 使用管理员登录获取 Token
curl -X POST "http://localhost:8000/api/v1/auth/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "***REMOVED***" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=***REMOVED***"
```

### 2. 调用释放主机 API
```bash
# 使用获取的 Token 调用 API
TOKEN="your_jwt_token_here"

curl -X POST "http://localhost:8000/api/v1/host/hosts/release" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "adb1852278641262sdf097",
    "host_list": [
        "1852278641262084097",
        "1852278641262084098"
    ]
  }'
```

### 3. 验证删除结果
检查响应中的 `updated_count` 确认更新的记录数。

### 4. 验证数据库（可选）
```bash
# 登录数据库验证记录已标记为删除
docker exec -it intel-mariadb mysql -u root -p

USE intel_cw_db;
SELECT * FROM host_exec_log 
WHERE user_id = 'adb1852278641262sdf097'
  AND host_id IN (1852278641262084097, 1852278641262084098)
  AND del_flag = 1;  -- 应该能看到被软删除的记录
```

## 性能考虑

1. **批量更新**: 使用 `IN` 操作符批量更新，比逐个更新效率高
2. **索引优化**: `user_id` 和 `host_id` 字段都有索引，更新性能良好
3. **事务支持**: 更新操作在事务中执行，确保数据一致性
4. **软删除优势**: 相比硬删除，软删除不会触发级联删除，性能更好

## 安全考虑

1. **权限验证**: 需要有效的 JWT Token 才能访问
2. **用户隔离**: 只更新指定 `user_id` 的记录，防止跨用户删除
3. **参数验证**: 验证 `host_id` 格式，防止 SQL 注入
4. **日志记录**: 详细记录删除操作的日志，便于审计
5. **数据恢复**: 软删除保留数据，支持误操作恢复

## 错误处理

### 主机ID格式错误
如果 `host_list` 中包含无效的主机ID格式：
```json
{
  "code": 400,
  "message": "主机ID格式无效",
  "error_code": "INVALID_HOST_ID"
}
```

### 数据库错误
如果数据库操作失败：
```json
{
  "code": 500,
  "message": "释放主机失败",
  "error_code": "RELEASE_HOSTS_FAILED"
}
```

## 最佳实践

1. **批量操作**: 尽量批量释放主机，减少 API 调用次数
2. **错误处理**: 检查 `updated_count`，如果为 0 可能表示记录不存在或已删除
3. **日志监控**: 监控 API 调用日志，发现异常删除操作
4. **数据恢复**: 如果误删除，可以通过更新 `del_flag = 0` 来恢复数据
5. **定期清理**: 定期物理删除 `del_flag = 1` 的旧记录，避免数据库膨胀

## 与其他 API 的关系

- **与重试 VNC 列表 API**: 释放主机后，该主机将不再出现在重试列表中（因为重试列表查询时过滤了 `del_flag = 1` 的记录）
- **与查询可用主机 API**: 释放主机不影响主机的可用状态，只标记执行记录为已删除

## 更新历史

- **2025-10-29**: 初始版本，实现释放主机功能
- **2025-10-29**: 修改为软删除（逻辑删除），使用 `del_flag = 1` 标记删除
- **核心功能**:
  - 支持批量逻辑删除主机执行记录
  - 软删除操作，数据可恢复
  - 完整的错误处理和日志记录
  - 返回实际更新的记录数

## 相关文件

- [services/host-service/app/api/v1/endpoints/hosts.py](../../services/host-service/app/api/v1/endpoints/hosts.py) - API 端点定义
- [services/host-service/app/services/host_service.py](../../services/host-service/app/services/host_service.py) - 业务逻辑实现
- [services/host-service/app/models/host_exec_log.py](../../services/host-service/app/models/host_exec_log.py) - 执行日志模型
- [services/host-service/app/schemas/host.py](../../services/host-service/app/schemas/host.py) - 请求/响应模型
