# VNC 连接结果上报 API 文档

## 概述

VNC 连接结果上报 API 用于记录用户与主机之间的 VNC 连接情况。当用户通过 VNC 尝试连接到主机时，客户端应该将连接结果上报到服务端。

## API 端点

### POST /api/v1/hosts/vnc/connection-report

上报 VNC 连接结果到服务端。

**请求方法**：`POST`  
**状态码**：`201 Created`

### 请求参数

```json
{
  "user_id": "1852278641262084097",
  "host_id": "1852278641262084097",
  "connection_status": "success",
  "connection_time": "2025-10-11T10:30:00Z"
}
```

#### 字段说明

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|---|---|---|---|---|
| `user_id` | string | ✓ | 用户ID | "1852278641262084097" |
| `host_id` | string | ✓ | 主机ID | "1852278641262084097" |
| `connection_status` | string | ✓ | 连接状态，只能是 `success` 或 `failed` | "success" |
| `connection_time` | string (ISO 8601) | ✓ | 连接时间，ISO 8601 格式 | "2025-10-11T10:30:00Z" |

### 响应成功 (201 Created)

```json
{
  "code": 201,
  "message": "VNC连接上报成功",
  "data": {
    "id": 1,
    "user_id": "1852278641262084097",
    "host_id": "1852278641262084097",
    "connection_status": "success",
    "connection_time": "2025-10-11T10:30:00Z",
    "created_time": "2025-10-11T10:30:01Z",
    "updated_time": "2025-10-11T10:30:01Z"
  },
  "timestamp": "2025-10-11T10:30:01Z",
  "request_id": "req-123456"
}
```

### 响应失败

#### 主机不存在 (404 Not Found)

```json
{
  "code": 404,
  "message": "主机不存在: 1852278641262084097",
  "error_code": "HOST_NOT_FOUND",
  "timestamp": "2025-10-11T10:30:01Z",
  "request_id": "req-123456"
}
```

#### 无效的连接状态 (400 Bad Request)

```json
{
  "code": 400,
  "message": "无效的连接状态: unknown，必须为 success 或 failed",
  "error_code": "INVALID_CONNECTION_STATUS",
  "timestamp": "2025-10-11T10:30:01Z",
  "request_id": "req-123456"
}
```

#### 数据验证失败 (422 Unprocessable Entity)

```json
{
  "code": 422,
  "message": "请求数据验证失败",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field_errors": [
      {
        "loc": ["body", "user_id"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  },
  "timestamp": "2025-10-11T10:30:01Z",
  "request_id": "req-123456"
}
```

## 使用示例

### cURL

#### 成功连接

```bash
curl -X POST http://localhost:8003/api/v1/hosts/vnc/connection-report \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1852278641262084097",
    "host_id": "1852278641262084097",
    "connection_status": "success",
    "connection_time": "2025-10-11T10:30:00Z"
  }'
```

#### 连接失败

```bash
curl -X POST http://localhost:8003/api/v1/hosts/vnc/connection-report \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1852278641262084097",
    "host_id": "1852278641262084097",
    "connection_status": "failed",
    "connection_time": "2025-10-11T10:30:00Z"
  }'
```

### Python (requests)

```python
import requests
from datetime import datetime, timezone

# 成功连接
response = requests.post(
    "http://localhost:8003/api/v1/hosts/vnc/connection-report",
    json={
        "user_id": "1852278641262084097",
        "host_id": "1852278641262084097",
        "connection_status": "success",
        "connection_time": datetime.now(timezone.utc).isoformat()
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
```

### Python (httpx - 异步)

```python
import httpx
from datetime import datetime, timezone

async def report_vnc_connection():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8003/api/v1/hosts/vnc/connection-report",
            json={
                "user_id": "1852278641262084097",
                "host_id": "1852278641262084097",
                "connection_status": "success",
                "connection_time": datetime.now(timezone.utc).isoformat()
            }
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

# 运行
import asyncio
asyncio.run(report_vnc_connection())
```

### JavaScript (Fetch API)

```javascript
const reportVNCConnection = async () => {
  const response = await fetch('http://localhost:8003/api/v1/hosts/vnc/connection-report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: '1852278641262084097',
      host_id: '1852278641262084097',
      connection_status: 'success',
      connection_time: new Date().toISOString()
    })
  });

  const data = await response.json();
  console.log('Status:', response.status);
  console.log('Response:', data);
};

reportVNCConnection();
```

## 业务流程

```
VNC 客户端              Host Service
    |                      |
    |-- 连接主机 --------->|
    |                      |
    |<-- 连接结果 ---------|
    |                      |
    |-- 上报连接结果 ----->|
    |  POST /vnc/connection-report
    |                      |
    |  验证主机是否存在     |
    |  验证连接状态有效性   |
    |  创建连接记录        |
    |                      |
    |<-- 返回记录ID -------|
    |
```

## 数据库表结构

VNC 连接记录存储在 `vnc_connections` 表中：

```sql
CREATE TABLE vnc_connections (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  host_id VARCHAR(100) NOT NULL,
  connection_status VARCHAR(20) NOT NULL,
  connection_time DATETIME(6) NOT NULL,
  created_time DATETIME(6) NOT NULL,
  updated_time DATETIME(6) NOT NULL,
  del_flag BOOLEAN DEFAULT FALSE,
  
  INDEX idx_vnc_user_host (user_id, host_id),
  INDEX idx_vnc_status (connection_status),
  INDEX idx_vnc_connection_time (connection_time)
);
```

## 监控和日志

### 日志格式

API 会在以下情况记录日志：

#### 成功情况
```
VNC连接上报成功
{
  "operation": "report_vnc_connection",
  "user_id": "1852278641262084097",
  "host_id": "1852278641262084097",
  "connection_status": "success",
  "connection_time": "2025-10-11T10:30:00Z",
  "record_id": 1
}
```

#### 失败情况
```
VNC连接上报失败
{
  "operation": "report_vnc_connection",
  "user_id": "1852278641262084097",
  "host_id": "1852278641262084097",
  "error_code": "HOST_NOT_FOUND"
}
```

### Prometheus 指标

该端点会自动收集以下指标：

- `http_requests_total{service="host-service", method="POST", endpoint="/api/v1/hosts/vnc/connection-report", status="201"}`
- `http_request_duration_seconds{service="host-service", method="POST", endpoint="/api/v1/hosts/vnc/connection-report"}`

## 限制和注意事项

### 请求限制

- **最大请求频率**：无限制（由网关限流控制）
- **请求体大小**：< 10KB
- **超时时间**：30 秒

### 数据有效期

- VNC 连接记录永久保存，不会自动删除
- 可以通过主机删除时级联删除相关记录

### 并发处理

- 支持高并发上报
- 每条记录的 ID 由数据库自动生成，保证唯一性

## 常见问题

### Q: connection_time 字段的时区是什么？
A: 使用 ISO 8601 格式（如 `2025-10-11T10:30:00Z`），其中 Z 表示 UTC 时区。

### Q: 支持批量上报吗？
A: 目前不支持批量上报，每个连接结果需要单独上报。

### Q: 如果上报同一连接多次会怎样？
A: 每次上报都会创建新的记录，不会检查重复。

### Q: 如何查询历史连接记录？
A: 可以通过其他 API 端点查询（将来实现），或直接访问数据库。

## 相关 API 端点

- `GET /api/v1/hosts` - 获取主机列表
- `GET /api/v1/hosts/{host_id}` - 获取主机详情
- `POST /api/v1/hosts` - 创建主机
- `DELETE /api/v1/hosts/{host_id}` - 删除主机

## 更新历史

- **2025-10-24**: 初始版本
  - 新增 VNC 连接结果上报 API
  - 创建 vnc_connections 数据库表
  - 添加连接状态验证
  - 集成日志和监控指标
