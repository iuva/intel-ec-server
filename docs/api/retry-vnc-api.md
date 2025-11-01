# 重试 VNC 列表 API 文档

## API 概述

获取需要重试的 VNC 连接列表，查询指定用户所有未成功的主机执行记录。

## 端点信息

- **URL**: `POST /api/v1/host/hosts/retry-vnc`
- **方法**: POST
- **认证**: 需要有效的 JWT 令牌

## 业务逻辑

1. 查询 `host_exec_log` 表:
   - 条件: `user_id = 入参的user_id`
   - `case_state != 2` (非成功状态)
   - `del_flag = 0` (未删除)
2. 获取这些记录的 `host_id`（去重）
3. 查询 `host_rec` 表对应的主机信息
4. 返回主机信息列表（包含 `host_id`、`host_ip`、`user_name`）

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

### 请求示例

```bash
# 使用 curl 调用
curl -X POST "http://localhost:8000/api/v1/host/hosts/retry-vnc" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1852278641262084097"
  }'
```

```json
// 请求 Body
{
  "user_id": "1852278641262084097"
}
```

## 响应格式

### 成功响应 (200 OK)

```json
{
  "hosts": [
    {
      "host_id": 1846486359367955051,
      "host_ip": "192.168.1.100",
      "user_name": "admin"
    },
    {
      "host_id": 1846486359367955052,
      "host_ip": "192.168.1.101",
      "user_name": "root"
    }
  ],
  "total": 2
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|-------|------|------|
| hosts | array | 需要重试的主机列表 |
| hosts[].host_id | integer | 主机ID (host_rec.id) |
| hosts[].host_ip | string | 主机IP地址 |
| hosts[].user_name | string | 主机账号 (host_acct) |
| total | integer | 主机总数 |

### 错误响应

#### 400 Bad Request - 参数错误
```json
{
  "code": 400,
  "message": "请求参数无效",
  "error_code": "INVALID_PARAMS"
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
  "message": "查询重试 VNC 列表失败",
  "error_code": "GET_RETRY_VNC_LIST_FAILED"
}
```

## 使用场景

### 场景1：获取用户的重试列表
用户需要查看所有未成功的 VNC 连接，以便重新尝试连接。

```bash
# 请求
POST /api/v1/host/hosts/retry-vnc
{
  "user_id": "1852278641262084097"
}

# 响应
{
  "hosts": [
    {
      "host_id": 1846486359367955051,
      "host_ip": "192.168.1.100",
      "user_name": "admin"
    }
  ],
  "total": 1
}
```

### 场景2：用户没有失败记录
查询用户没有任何失败的执行记录。

```bash
# 请求
POST /api/v1/host/hosts/retry-vnc
{
  "user_id": "user_with_no_failures"
}

# 响应
{
  "hosts": [],
  "total": 0
}
```

## 数据库查询说明

### 查询逻辑

1. **第一步：查询执行日志**
```sql
SELECT DISTINCT host_id
FROM host_exec_log
WHERE user_id = '1852278641262084097'
  AND case_state != 2
  AND del_flag = 0;
```

2. **第二步：查询主机信息**
```sql
SELECT id, host_ip, host_acct
FROM host_rec
WHERE id IN (查询到的host_id列表)
  AND del_flag = 0;
```

### case_state 说明

| 值 | 状态 | 说明 |
|---|------|------|
| 0 | free | 空闲 |
| 1 | start | 启动 |
| 2 | success | 成功（不包含在重试列表中） |
| 3 | failed | 失败（包含在重试列表中） |

## 测试步骤

### 1. 获取 JWT Token
```bash
# 使用管理员登录获取 Token
curl -X POST "http://localhost:8000/api/v1/auth/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "***REMOVED***" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=***REMOVED***"
```

### 2. 调用重试 VNC 列表 API
```bash
# 使用获取的 Token 调用 API
TOKEN="your_jwt_token_here"

curl -X POST "http://localhost:8000/api/v1/host/hosts/retry-vnc" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1852278641262084097"
  }'
```

### 3. 验证响应
检查响应是否包含预期的主机列表。

## 注意事项

1. **去重处理**: 同一个 `host_id` 可能有多条失败记录，API 会自动去重
2. **空值处理**: 如果 `host_ip` 或 `host_acct` 为 NULL，会返回空字符串
3. **性能考虑**: 使用了数据库索引优化查询性能（`user_id`、`case_state`、`del_flag` 均有索引）
4. **认证要求**: 必须提供有效的 JWT Token 才能访问此 API

## 更新历史

- **2025-10-29**: 初始版本，实现重试 VNC 列表查询功能
- **核心功能**:
  - 支持按用户ID查询失败的执行记录
  - 自动关联 host_rec 表获取主机详细信息
  - 返回标准化的主机信息（host_id, host_ip, user_name）
  - 完整的错误处理和日志记录

## 相关文件

- [services/host-service/app/api/v1/endpoints/hosts.py](../../services/host-service/app/api/v1/endpoints/hosts.py) - API 端点定义
- [services/host-service/app/services/host_service.py](../../services/host-service/app/services/host_service.py) - 业务逻辑实现
- [services/host-service/app/models/host_exec_log.py](../../services/host-service/app/models/host_exec_log.py) - 执行日志模型
- [services/host-service/app/schemas/host.py](../../services/host-service/app/schemas/host.py) - 请求/响应模型

