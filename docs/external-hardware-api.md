# 外部硬件接口 API 文档

## 概述

本文档描述了 Host Service 与外部硬件服务（Hardware Service）之间的接口规范。所有接口调用都需要先获取访问令牌（Token），然后在请求头中携带该令牌进行认证。

**基础 URL**: 通过环境变量 `HARDWARE_API_URL` 配置，默认值为 `http://hardware-service:8000`

**认证方式**: Bearer Token（在请求头中携带 `Authorization: bearer {access_token}`）

---

## 1. 获取访问令牌 (Get Token)

### 接口信息

- **URL**: `{HARDWARE_API_URL}/api/v1/auth/login`
- **方法**: `POST`
- **认证**: 无需认证（公开接口）

### 请求参数

#### Headers

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Content-Type | string | 是 | `application/json` |

#### Request Body

```json
{
  "email": "user@example.com"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| email | string | 是 | 用户邮箱地址（从 sys_user 表获取） |

### 响应示例

#### 成功响应 (200)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": "15552000"
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| access_token | string | 访问令牌，用于后续接口认证 |
| token_type | string | Token 类型，通常为 "bearer" |
| expires_in | string | 过期时间（秒），默认 15552000 秒（约 180 天） |

#### 错误响应

```json
{
  "message": "认证失败",
  "code": 401
}
```

### 业务逻辑

1. 根据 `user_id` 查询 `sys_user` 表获取用户邮箱
2. 先从 Redis 缓存获取 token（缓存键：`external_api_token:{user_email}`）
3. 如果缓存为空，使用锁防止并发请求，调用登录接口获取 token
4. 根据 `expires_in` 的值将 token 存入 Redis 缓存
5. 返回完整的 token 信息

### 注意事项

- Token 会被缓存到 Redis，避免频繁请求登录接口
- 缓存键格式：`external_api_token:{user_email}`
- 缓存过期时间：根据 `expires_in` 字段设置（默认 15552000 秒）

---

## 2. 新增硬件 (Create Hardware)

### 接口信息

- **URL**: `{HARDWARE_API_URL}/api/v1/hardware/`
- **方法**: `POST`
- **认证**: 需要 Bearer Token

### 请求参数

#### Headers

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | `bearer {access_token}` |
| Content-Type | string | 是 | `application/json` |

#### Request Body

```json
{
  "Head": {
    "ConfigName": "DMR-sample-1",
    "Component": "bios.playform",
    "Owner": "zeyichen",
    "Project": "bios.oakstream_diamondrapids",
    "Environment": "silicon",
    "Milestone": "Alpha",
    "SubComponent": "",
    "Type": "hardware",
    "Tag": ""
  },
  "Payload": {
    "dmr_config": {
      "mainboard": {
        "board": {
          "board_meta_data": {
            "host_name": "Host-192.168.1.100"
          }
        }
      }
    },
    "host_ip": "192.168.1.100",
    "mg_id": "MG001",
    "other_fields": "..."
  }
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Head | object | 是 | 硬件头部信息（固定格式） |
| Head.ConfigName | string | 是 | 配置名称，默认 "DMR-sample-1" |
| Head.Component | string | 是 | 组件名称，默认 "bios.playform" |
| Head.Owner | string | 是 | 所有者，默认 "zeyichen" |
| Head.Project | string | 是 | 项目名称，默认 "bios.oakstream_diamondrapids" |
| Head.Environment | string | 是 | 环境类型，默认 "silicon" |
| Head.Milestone | string | 是 | 里程碑，默认 "Alpha" |
| Head.SubComponent | string | 否 | 子组件，默认空字符串 |
| Head.Type | string | 是 | 类型，固定为 "hardware" |
| Head.Tag | string | 否 | 标签，默认空字符串 |
| Payload | object | 是 | 硬件详细信息（对应 host_hw_rec 表的 hw_info 字段） |

**Payload 说明**：
- `Payload` 字段的内容来自 `host_hw_rec` 表的 `hw_info` 字段（JSON 格式）
- 通常包含 `dmr_config`、`host_ip`、`mg_id` 等硬件配置信息

### 响应示例

#### 成功响应 (200)

```json
{
  "_id": "507f1f77bcf86cd799439011",
  "code": 200,
  "message": "创建成功"
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| _id | string | 新创建的硬件 ID（hardware_id） |
| code | integer | 响应码，200 表示成功 |
| message | string | 响应消息 |

**注意**：响应中可能使用 `hardware_id` 或 `id` 字段名，但优先使用 `_id` 字段。

#### 错误响应

```json
{
  "code": 400,
  "message": "创建失败：参数错误"
}
```

### 业务逻辑

1. 调用 `get_external_api_token()` 获取访问令牌
2. 构建请求体，包含 `Head` 和 `Payload` 两部分
3. 发送 POST 请求到 `/api/v1/hardware/`
4. 从响应中提取 `_id` 字段作为新的 `hardware_id`
5. 将 `hardware_id` 更新到 `host_rec` 和 `host_hw_rec` 表

### 使用场景

- 主机审批通过时，如果 `host_rec.hardware_id` 为空，则调用此接口创建新的硬件记录

---

## 3. 修改硬件 (Update Hardware)

### 接口信息

- **URL**: `{HARDWARE_API_URL}/api/v1/hardware/{hardware_id}`
- **方法**: `PUT`
- **认证**: 需要 Bearer Token

### 请求参数

#### URL 参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| hardware_id | string | 是 | 硬件 ID（路径参数） |

#### Headers

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | `bearer {access_token}` |
| Content-Type | string | 是 | `application/json` |

#### Request Body

```json
{
  "_id": {
    "$oid": "507f1f77bcf86cd799439011"
  },
  "Head": {
    "ConfigName": "DMR-sample-1",
    "Component": "bios.playform",
    "Owner": "zeyichen",
    "Project": "bios.oakstream_diamondrapids",
    "Environment": "silicon",
    "Milestone": "Alpha",
    "SubComponent": "",
    "Type": "hardware",
    "Tag": ""
  },
  "Payload": {
    "dmr_config": {
      "mainboard": {
        "board": {
          "board_meta_data": {
            "host_name": "Host-192.168.1.100"
          }
        }
      }
    },
    "host_ip": "192.168.1.100",
    "mg_id": "MG001",
    "other_fields": "..."
  }
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| _id | object | 是 | 硬件 ID 对象（MongoDB 格式） |
| _id.$oid | string | 是 | 硬件 ID 字符串 |
| Head | object | 是 | 硬件头部信息（与新增接口相同） |
| Payload | object | 是 | 硬件详细信息（与新增接口相同） |

### 响应示例

#### 成功响应 (200)

```json
{
  "code": 200,
  "message": "更新成功"
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | integer | 响应码，200 表示成功 |
| message | string | 响应消息 |

#### 错误响应

```json
{
  "code": 404,
  "message": "硬件记录不存在"
}
```

### 业务逻辑

1. 调用 `get_external_api_token()` 获取访问令牌
2. 构建请求体，包含 `_id`、`Head` 和 `Payload` 三部分
3. 发送 PUT 请求到 `/api/v1/hardware/{hardware_id}`
4. 检查响应状态码或响应体中的 `code` 字段是否为 200
5. 如果成功，返回原 `hardware_id`；如果失败，抛出异常

### 使用场景

- 主机审批通过时，如果 `host_rec.hardware_id` 不为空，则调用此接口更新现有硬件记录
- 主机信息变更时，同步更新外部硬件服务中的硬件信息

---

## 4. 删除硬件 (Delete Hardware)

### 接口信息

- **URL**: `{HARDWARE_API_URL}/api/v1/hardware/{hardware_id}`
- **方法**: `DELETE`
- **认证**: 需要 Bearer Token

### 请求参数

#### URL 参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| hardware_id | string | 是 | 硬件 ID（路径参数） |

#### Headers

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | `bearer {access_token}` |
| Content-Type | string | 是 | `application/json` |

#### Request Body

无（DELETE 请求通常不需要请求体）

### 响应示例

#### 成功响应 (200)

```json
{
  "code": 200,
  "message": "删除成功"
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | integer | 响应码，200 表示成功 |
| message | string | 响应消息 |

#### 错误响应

```json
{
  "code": 404,
  "message": "硬件记录不存在"
}
```

### 业务逻辑

1. 调用 `get_external_api_token()` 获取访问令牌
2. 发送 DELETE 请求到 `/api/v1/hardware/{hardware_id}`
3. 检查响应状态码或响应体中的 `code` 字段是否为 200
4. 如果成功，外部硬件服务中的硬件记录已被删除；如果失败，抛出异常

### 使用场景

- 主机删除时，同步删除外部硬件服务中的硬件记录
- 确保外部硬件服务与 Host Service 的数据一致性

---

## 通用说明

### 认证流程

所有需要认证的接口都遵循以下流程：

1. **获取 Token**：调用 `/api/v1/auth/login` 接口获取访问令牌
2. **缓存 Token**：将 token 缓存到 Redis，避免频繁请求
3. **携带 Token**：在请求头中携带 `Authorization: bearer {access_token}`

### 错误处理

所有接口调用失败时，会抛出 `BusinessError` 异常，包含以下信息：

- `message`: 错误消息
- `error_code`: 错误代码（如 `HARDWARE_CREATE_FAILED`、`HARDWARE_UPDATE_FAILED` 等）
- `details`: 详细错误信息（包含请求 URL、状态码、响应体等）

### 成功判断标准

接口调用成功的判断标准（满足任一条件即可）：

1. HTTP 响应头 `:status` 或 `status` 等于 `200`
2. HTTP 响应状态码 `status_code` 等于 `200`
3. 响应体中的 `code` 字段等于 `200`

### Mock 模式

如果环境变量 `USE_HARDWARE_MOCK` 设置为 `true`，则所有硬件接口调用都会使用 Mock 数据，不会实际调用外部接口。

**Mock 行为**：
- 新增硬件：返回模拟的 `hardware_id`（格式：`mock-hardware-{uuid}`）
- 修改硬件：直接返回原 `hardware_id`
- 删除硬件：直接返回成功（不实际调用接口）

### 环境变量配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| HARDWARE_API_URL | string | `http://hardware-service:8000` | 外部硬件服务的基础 URL |
| USE_HARDWARE_MOCK | boolean | `false` | 是否使用 Mock 模式 |

### 日志记录

所有接口调用都会记录详细的日志，包括：

- 请求方法、URL、路径
- 请求头（Authorization 已脱敏）
- 请求参数、请求体（完整 JSON，不截断）
- 响应状态码、响应头（已脱敏）
- 响应体（完整 JSON，不截断）

日志级别：`INFO`

---

## 接口调用示例

### Python 示例

```python
from app.services.external_api_client import call_external_api

# 1. 获取 Token（自动处理，无需手动调用）
# Token 获取由 call_external_api 内部自动处理

# 2. 新增硬件
response = await call_external_api(
    method="POST",
    url_path="/api/v1/hardware/",
    request=request,
    user_id=user_id,
    json_data={
        "Head": {
            "ConfigName": "DMR-sample-1",
            "Component": "bios.playform",
            "Owner": "zeyichen",
            "Project": "bios.oakstream_diamondrapids",
            "Environment": "silicon",
            "Milestone": "Alpha",
            "SubComponent": "",
            "Type": "hardware",
            "Tag": ""
        },
        "Payload": hw_info
    },
    locale="zh_CN"
)
hardware_id = response["body"]["_id"]

# 3. 修改硬件
response = await call_external_api(
    method="PUT",
    url_path=f"/api/v1/hardware/{hardware_id}",
    request=request,
    user_id=user_id,
    json_data={
        "_id": {"$oid": hardware_id},
        "Head": {...},
        "Payload": hw_info
    },
    locale="zh_CN"
)

# 4. 删除硬件
response = await call_external_api(
    method="DELETE",
    url_path=f"/api/v1/hardware/{hardware_id}",
    request=request,
    user_id=user_id,
    locale="zh_CN"
)
```

### cURL 示例

```bash
# 1. 获取 Token
curl -X POST "http://hardware-service:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# 2. 新增硬件
curl -X POST "http://hardware-service:8000/api/v1/hardware/" \
  -H "Authorization: bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "Head": {
      "ConfigName": "DMR-sample-1",
      "Component": "bios.playform",
      "Owner": "zeyichen",
      "Project": "bios.oakstream_diamondrapids",
      "Environment": "silicon",
      "Milestone": "Alpha",
      "SubComponent": "",
      "Type": "hardware",
      "Tag": ""
    },
    "Payload": {
      "dmr_config": {...},
      "host_ip": "192.168.1.100"
    }
  }'

# 3. 修改硬件
curl -X PUT "http://hardware-service:8000/api/v1/hardware/{hardware_id}" \
  -H "Authorization: bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "_id": {"$oid": "{hardware_id}"},
    "Head": {...},
    "Payload": {...}
  }'

# 4. 删除硬件
curl -X DELETE "http://hardware-service:8000/api/v1/hardware/{hardware_id}" \
  -H "Authorization: bearer {access_token}" \
  -H "Content-Type: application/json"
```

---

## 相关文件

- **接口调用客户端**: `services/host-service/app/services/external_api_client.py`
- **硬件接口调用**: `services/host-service/app/services/admin_appr_host_service.py` (函数 `_call_hardware_api`)
- **主机删除接口**: `services/host-service/app/services/admin_host_service.py`

---

**最后更新**: 2025-12-23  
**文档版本**: 1.0.0

