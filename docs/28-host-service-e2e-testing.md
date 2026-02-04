# Host Service 端到端测试文档

## 📋 目录

- [测试环境准备](#测试环境准备)
- [接口分类](#接口分类)
- [浏览器插件接口测试](#浏览器插件接口测试)
- [Agent HTTP API 测试](#agent-http-api-测试)
- [管理后台接口测试](#管理后台接口测试)
- [文件管理接口测试](#文件管理接口测试)
- [WebSocket 接口测试](#websocket-接口测试)
- [端到端测试场景](#端到端测试场景)

---

## 测试环境准备

### 1. 服务地址配置

```bash
# Gateway Service
GATEWAY_URL="http://localhost:8000"

# Host Service (直接访问)
HOST_SERVICE_URL="http://localhost:8003"

# 通过 Gateway 访问 Host Service
HOST_API_URL="${GATEWAY_URL}/api/v1/host"
```

### 2. 认证 Token 获取

```bash
# 管理员登录获取 Token
curl -X POST "${GATEWAY_URL}/api/v1/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# 响应示例
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}

# 设置环境变量
export ADMIN_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. 测试数据准备

```bash
# 测试用例 ID
export TC_ID="test_case_001"

# 测试周期名称
export CYCLE_NAME="test_cycle_001"

# 用户名
export USER_NAME="test_user"

# 用户 ID
export USER_ID="user_123"

# 主机 ID（需要从实际查询结果中获取）
export HOST_ID="1846486359367955051"
```

---

## 接口分类

### 接口分类表

| 分类 | 接口数量 | 认证要求 | 路径前缀 |
|------|---------|---------|---------|
| 浏览器插件接口 | 5 | ❌ 无需认证 | `/api/v1/host/hosts`, `/api/v1/host/vnc` |
| Agent HTTP API | 3 | ❌ 无需认证 | `/api/v1/host/agent` |
| 管理后台接口 | 13 | ✅ 需要认证 | `/api/v1/host/admin/*` |
| 文件管理接口 | 2 | ✅ 需要认证 | `/api/v1/host/file` |
| WebSocket 接口 | 1 | ✅ 需要认证 | `/api/v1/host/ws/host` |
| WebSocket 管理接口 | 6 | ✅ 需要认证 | `/api/v1/host/ws/*` |

---

## 浏览器插件接口测试

### 1. 查询可用主机列表

**接口信息**
- **路径**: `POST /api/v1/host/hosts/available`
- **认证**: ❌ 无需认证
- **跨域**: ✅ 支持

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/hosts/available" \
  -H "Content-Type: application/json" \
  -d '{
    "tc_id": "test_case_001",
    "cycle_name": "test_cycle_001",
    "user_name": "test_user",
    "page_size": 20,
    "last_id": null
  }'
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `tc_id` | string | ✅ | 测试用例 ID |
| `cycle_name` | string | ✅ | 测试周期名称 |
| `user_name` | string | ✅ | 用户名 |
| `page_size` | integer | ❌ | 每页大小，1-100，默认 20 |
| `last_id` | string\|null | ❌ | 上一页最后一条记录的 id，首次请求传 null |

**响应示例**

```json
{
  "code": 200,
  "message": "查询可用主机列表成功",
  "data": {
    "hosts": [
      {
        "id": "1846486359367955051",
        "hardware_id": "HW001",
        "host_ip": "192.168.1.100",
        "host_acct": "neusoft",
        "host_pwd": "password123"
      }
    ],
    "total": 10,
    "page_size": 20,
    "has_next": false,
    "last_id": "1846486359367955051"
  },
  "locale": "zh-CN"
}
```

**测试用例**

```bash
# 测试用例 1: 首次查询（不传 last_id）
curl -X POST "${HOST_API_URL}/hosts/available" \
  -H "Content-Type: application/json" \
  -d '{
    "tc_id": "TC001",
    "cycle_name": "CYCLE001",
    "user_name": "user1",
    "page_size": 10
  }'

# 测试用例 2: 分页查询（传入 last_id）
curl -X POST "${HOST_API_URL}/hosts/available" \
  -H "Content-Type: application/json" \
  -d '{
    "tc_id": "TC001",
    "cycle_name": "CYCLE001",
    "user_name": "user1",
    "page_size": 10,
    "last_id": "1846486359367955051"
  }'

# 测试用例 3: 参数验证（缺少必填参数）
curl -X POST "${HOST_API_URL}/hosts/available" \
  -H "Content-Type: application/json" \
  -d '{
    "tc_id": "TC001"
  }'
# 预期: 400 错误，提示缺少必填参数
```

---

### 2. 获取重试 VNC 列表

**接口信息**
- **路径**: `POST /api/v1/host/hosts/retry-vnc`
- **认证**: ❌ 无需认证
- **跨域**: ✅ 支持

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/hosts/retry-vnc" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123"
  }'
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | ✅ | 用户ID |

**响应示例**

```json
{
  "code": 200,
  "message": "查询重试 VNC 列表成功",
  "data": {
    "hosts": [
      {
        "host_id": "1846486359367955051",
        "host_ip": "192.168.1.100",
        "user_name": "neusoft"
      }
    ],
    "total": 1
  },
  "locale": "zh-CN"
}
```

---

### 3. 释放主机

**接口信息**
- **路径**: `POST /api/v1/host/hosts/release`
- **认证**: ❌ 无需认证
- **跨域**: ✅ 支持

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/hosts/release" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "host_list": ["1846486359367955051", "1846486359367955052"]
  }'
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | ✅ | 用户ID |
| `host_list` | array[string] | ✅ | 主机ID列表 |

**响应示例**

```json
{
  "code": 200,
  "message": "释放主机成功",
  "data": {
    "updated_count": 2,
    "user_id": "user_123",
    "host_list": ["1846486359367955051", "1846486359367955052"]
  },
  "locale": "zh-CN"
}
```

---

### 4. 上报 VNC 连接结果

**接口信息**
- **路径**: `POST /api/v1/host/vnc/report`
- **认证**: ❌ 无需认证
- **跨域**: ✅ 支持

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/vnc/report" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "tc_id": "TC001",
    "cycle_name": "CYCLE001",
    "user_name": "test_user",
    "host_id": "1846486359367955051",
    "connection_status": "success",
    "connection_time": "2025-01-15T10:00:00Z"
  }'
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | ✅ | 用户ID |
| `tc_id` | string | ✅ | 执行测试ID |
| `cycle_name` | string | ✅ | 周期名称 |
| `user_name` | string | ✅ | 用户名称 |
| `host_id` | string | ✅ | 主机ID |
| `connection_status` | string | ✅ | 连接状态：`success` 或 `failed` |
| `connection_time` | string | ✅ | VNC 连接时间（ISO 8601 格式） |

**响应示例**

```json
{
  "code": 200,
  "message": "VNC连接结果上报成功",
  "data": {
    "host_id": "1846486359367955051",
    "connection_status": "success",
    "connection_time": "2025-01-15T10:00:00Z"
  },
  "locale": "zh-CN"
}
```

---

### 5. 获取 VNC 连接信息

**接口信息**
- **路径**: `POST /api/v1/host/vnc/connect`
- **认证**: ❌ 无需认证
- **跨域**: ✅ 支持

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/vnc/connect" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "1846486359367955051"
  }'
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 主机ID（host_rec.id） |

**响应示例**

```json
{
  "code": 200,
  "message": "获取VNC连接信息成功",
  "data": {
    "ip": "192.168.101.118",
    "port": "5900",
    "username": "neusoft",
    "password": "f7e7925c3b79c4f05ab2cdc0badcaf13"
  },
  "locale": "zh-CN"
}
```

---

## Agent HTTP API 测试

### 1. 上报硬件信息

**接口信息**
- **路径**: `POST /api/v1/host/agent/report`
- **认证**: ❌ 无需认证

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/agent/report" \
  -H "Content-Type: application/json" \
  -d '{
    "hardware_id": "HW001",
    "name": "Agent Config",
    "dmr_config": {
      "revision": 1,
      "mainboard": {
        "revision": 1
      }
    }
  }'
```

---

### 2. 上报主机状态

**接口信息**
- **路径**: `POST /api/v1/host/agent/status`
- **认证**: ❌ 无需认证

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/agent/status" \
  -H "Content-Type: application/json" \
  -d '{
    "hardware_id": "HW001",
    "status": "online",
    "timestamp": "2025-01-15T10:00:00Z"
  }'
```

---

### 3. 获取 OTA 配置

**接口信息**
- **路径**: `GET /api/v1/host/agent/ota/latest`
- **认证**: ❌ 无需认证

**请求示例**

```bash
curl -X GET "${HOST_API_URL}/agent/ota/latest?hardware_id=HW001"
```

---

## 管理后台接口测试

### 1. 查询可用主机列表

**接口信息**
- **路径**: `GET /api/v1/host/admin/host/list`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X GET "${HOST_API_URL}/admin/host/list?page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | integer | ❌ | 页码，默认 1 |
| `page_size` | integer | ❌ | 每页大小，默认 20 |
| `mac` | string | ❌ | MAC地址搜索 |
| `username` | string | ❌ | 主机账号搜索 |
| `mg_id` | string | ❌ | 唯一引导ID搜索 |
| `use_by` | string | ❌ | 使用人搜索 |

**响应示例**

```json
{
  "code": 200,
  "message": "查询主机列表成功",
  "data": {
    "hosts": [
      {
        "host_id": "1846486359367955051",
        "username": "neusoft",
        "mg_id": "MG001",
        "mac": "00:11:22:33:44:55",
        "use_by": "user1",
        "host_state": 0,
        "appr_state": 1
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "locale": "zh-CN"
}
```

---

### 2. 删除主机

**接口信息**
- **路径**: `DELETE /api/v1/host/admin/host/{host_id}`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X DELETE "${HOST_API_URL}/admin/host/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

**响应示例**

```json
{
  "code": 200,
  "message": "主机删除成功",
  "data": {
    "id": "1846486359367955051"
  },
  "locale": "zh-CN"
}
```

---

### 3. 更新主机信息

**接口信息**
- **路径**: `PUT /api/v1/host/admin/host/{host_id}`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X PUT "${HOST_API_URL}/admin/host/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "host_acct": "new_username",
    "host_pwd": "new_password",
    "host_ip": "192.168.1.200"
  }'
```

---

### 4. 获取主机详情

**接口信息**
- **路径**: `GET /api/v1/host/admin/host/{host_id}`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X GET "${HOST_API_URL}/admin/host/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

---

### 5. 禁用主机

**接口信息**
- **路径**: `PUT /api/v1/host/admin/host/{host_id}/disable`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X PUT "${HOST_API_URL}/admin/host/${HOST_ID}/disable" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "主机故障，需要维护"
  }'
```

---

### 6. 强制主机下线

**接口信息**
- **路径**: `POST /api/v1/host/admin/host/{host_id}/force-offline`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/admin/host/${HOST_ID}/force-offline" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "紧急维护"
  }'
```

---

### 7. 更新主机密码

**接口信息**
- **路径**: `PUT /api/v1/host/admin/host/{host_id}/password`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X PUT "${HOST_API_URL}/admin/host/${HOST_ID}/password" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "new_password123"
  }'
```

---

### 8. 查询主机执行日志

**接口信息**
- **路径**: `GET /api/v1/host/admin/host/{host_id}/exec-logs`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X GET "${HOST_API_URL}/admin/host/${HOST_ID}/exec-logs?page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

---

### 9. 查询待审批主机列表

**接口信息**
- **路径**: `GET /api/v1/host/admin/appr-host/list`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X GET "${HOST_API_URL}/admin/appr-host/list?page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

---

### 10. 审批主机

**接口信息**
- **路径**: `POST /api/v1/host/admin/appr-host/{host_id}/approve`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/admin/appr-host/${HOST_ID}/approve" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "approve": true,
    "remark": "审批通过"
  }'
```

---

### 11. 查询 OTA 配置列表

**接口信息**
- **路径**: `GET /api/v1/host/admin/ota/list`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X GET "${HOST_API_URL}/admin/ota/list" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

---

### 12. 部署 OTA 配置

**接口信息**
- **路径**: `POST /api/v1/host/admin/ota/deploy`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/admin/ota/deploy" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "host_ids": ["1846486359367955051"],
    "ota_config_id": 1
  }'
```

---

## 文件管理接口测试

### 1. 上传文件

**接口信息**
- **路径**: `POST /api/v1/host/file/upload`
- **认证**: ✅ 需要认证

**请求示例**

```bash
curl -X POST "${HOST_API_URL}/file/upload" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -F "file=@/path/to/test.txt"
```

**响应示例**

```json
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "test.txt",
    "saved_filename": "550e8400-e29b-41d4-a716-446655440000.txt",
    "file_url": "/api/v1/host/file/550e8400-e29b-41d4-a716-446655440000.txt",
    "file_size": 1024,
    "content_type": "text/plain",
    "upload_time": "2025-01-15T10:00:00Z"
  },
  "locale": "zh-CN"
}
```

---

### 2. 下载文件（支持断点续传）

**接口信息**
- **路径**: `GET /api/v1/host/file/{filename}`
- **认证**: ✅ 需要认证
- **特性**: ✅ 支持 HTTP Range 请求（断点续传）

**请求示例**

```bash
# 完整下载
curl -X GET "${HOST_API_URL}/file/test.txt" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -o test.txt

# 断点续传（从第 1000 字节开始）
curl -X GET "${HOST_API_URL}/file/test.txt" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Range: bytes=1000-" \
  -o test_partial.txt

# 下载指定范围（第 1000-1999 字节）
curl -X GET "${HOST_API_URL}/file/test.txt" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Range: bytes=1000-1999" \
  -o test_range.txt
```

**响应头说明**

- `Accept-Ranges: bytes` - 表示支持字节范围请求
- `Content-Length` - 文件总大小（完整下载）或范围大小（部分下载）
- `Content-Range: bytes 1000-1999/5000` - 部分下载时，表示返回的字节范围

---

## WebSocket 接口测试

### 1. WebSocket 连接

**接口信息**
- **路径**: `WS /api/v1/host/ws/host`
- **认证**: ✅ 需要认证（通过查询参数或请求头）

**连接示例（JavaScript）**

```javascript
// 方式1: 通过查询参数传递 token
const ws = new WebSocket('ws://localhost:8003/api/v1/host/ws/host?token=YOUR_TOKEN');

// 方式2: 通过请求头传递 token（需要自定义 WebSocket 客户端）
// 注意：标准 WebSocket API 不支持自定义请求头，需要使用支持自定义头的库

ws.onopen = () => {
  console.log('WebSocket 连接已建立');
  
  // 发送消息
  ws.send(JSON.stringify({
    type: 'ping',
    data: {}
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('收到消息:', message);
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
  console.log('WebSocket 连接已关闭');
};
```

**连接示例（Python）**

```python
import asyncio
import websockets
import json

async def connect_websocket():
    uri = "ws://localhost:8003/api/v1/host/ws/host?token=YOUR_TOKEN"
    
    async with websockets.connect(uri) as websocket:
        # 发送消息
        await websocket.send(json.dumps({
            "type": "ping",
            "data": {}
        }))
        
        # 接收消息
        response = await websocket.recv()
        print(f"收到消息: {response}")

asyncio.run(connect_websocket())
```

---

### 2. WebSocket 管理接口

#### 2.1 获取活跃 Host 列表

```bash
curl -X GET "${HOST_API_URL}/ws/hosts" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

#### 2.2 获取 Host 连接状态

```bash
curl -X GET "${HOST_API_URL}/ws/status/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

#### 2.3 向指定 Host 发送消息

```bash
curl -X POST "${HOST_API_URL}/ws/send/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "command",
    "data": {
      "action": "reboot"
    }
  }'
```

#### 2.4 向多个 Host 发送消息

```bash
curl -X POST "${HOST_API_URL}/ws/send-to-hosts" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "host_ids": ["1846486359367955051", "1846486359367955052"],
    "message": {
      "type": "command",
      "data": {
        "action": "reboot"
      }
    }
  }'
```

#### 2.5 广播消息

```bash
curl -X POST "${HOST_API_URL}/ws/broadcast" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "notification",
      "data": {
        "content": "系统维护通知"
      }
    }
  }'
```

#### 2.6 通知 Host 下线

```bash
curl -X POST "${HOST_API_URL}/ws/notify-offline/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "管理员强制下线"
  }'
```

---

## 端到端测试场景

### 场景 1: 浏览器插件完整流程

**测试步骤**

1. **查询可用主机**
```bash
curl -X POST "${HOST_API_URL}/hosts/available" \
  -H "Content-Type: application/json" \
  -d '{
    "tc_id": "TC001",
    "cycle_name": "CYCLE001",
    "user_name": "user1",
    "page_size": 10
  }'
```

2. **获取 VNC 连接信息**
```bash
# 从步骤1的响应中获取 host_id
HOST_ID="1846486359367955051"

curl -X POST "${HOST_API_URL}/vnc/connect" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"${HOST_ID}\"
  }"
```

3. **上报 VNC 连接结果**
```bash
curl -X POST "${HOST_API_URL}/vnc/report" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "tc_id": "TC001",
    "cycle_name": "CYCLE001",
    "user_name": "user1",
    "host_id": "1846486359367955051",
    "connection_status": "success",
    "connection_time": "2025-01-15T10:00:00Z"
  }'
```

4. **释放主机**
```bash
curl -X POST "${HOST_API_URL}/hosts/release" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user_123\",
    \"host_list\": [\"${HOST_ID}\"]
  }"
```

---

### 场景 2: Agent 注册和上报流程

**测试步骤**

1. **上报硬件信息**
```bash
curl -X POST "${HOST_API_URL}/agent/report" \
  -H "Content-Type: application/json" \
  -d '{
    "hardware_id": "HW001",
    "name": "Agent Config",
    "dmr_config": {
      "revision": 1
    }
  }'
```

2. **上报主机状态**
```bash
curl -X POST "${HOST_API_URL}/agent/status" \
  -H "Content-Type: application/json" \
  -d '{
    "hardware_id": "HW001",
    "status": "online",
    "timestamp": "2025-01-15T10:00:00Z"
  }'
```

3. **建立 WebSocket 连接**
```javascript
const ws = new WebSocket('ws://localhost:8003/api/v1/host/ws/host?token=AGENT_TOKEN');
```

4. **获取 OTA 配置**
```bash
curl -X GET "${HOST_API_URL}/agent/ota/latest?hardware_id=HW001"
```

---

### 场景 3: 管理后台主机管理流程

**测试步骤**

1. **查询待审批主机**
```bash
curl -X GET "${HOST_API_URL}/admin/appr-host/list?page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

2. **审批主机**
```bash
curl -X POST "${HOST_API_URL}/admin/appr-host/${HOST_ID}/approve" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "approve": true,
    "remark": "审批通过"
  }'
```

3. **查询可用主机列表**
```bash
curl -X GET "${HOST_API_URL}/admin/host/list?page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

4. **获取主机详情**
```bash
curl -X GET "${HOST_API_URL}/admin/host/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

5. **更新主机信息**
```bash
curl -X PUT "${HOST_API_URL}/admin/host/${HOST_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "host_acct": "new_username",
    "host_pwd": "new_password"
  }'
```

6. **查询主机执行日志**
```bash
curl -X GET "${HOST_API_URL}/admin/host/${HOST_ID}/exec-logs?page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

---

### 场景 4: 文件管理流程

**测试步骤**

1. **上传文件**
```bash
curl -X POST "${HOST_API_URL}/file/upload" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -F "file=@/path/to/test.txt"
```

2. **下载文件（完整）**
```bash
curl -X GET "${HOST_API_URL}/file/test.txt" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -o downloaded_file.txt
```

3. **下载文件（断点续传）**
```bash
# 从第 1000 字节开始下载
curl -X GET "${HOST_API_URL}/file/test.txt" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Range: bytes=1000-" \
  -o partial_file.txt
```

---

## 测试检查清单

### 功能测试

- [ ] 浏览器插件接口无需认证即可访问
- [ ] 浏览器插件接口支持跨域请求
- [ ] Agent 接口无需认证即可访问
- [ ] 管理后台接口需要认证才能访问
- [ ] 文件上传和下载功能正常
- [ ] 文件下载支持断点续传
- [ ] WebSocket 连接正常
- [ ] WebSocket 消息发送和接收正常

### 错误处理测试

- [ ] 缺少必填参数时返回 400 错误
- [ ] 无效的认证 token 返回 401 错误
- [ ] 资源不存在时返回 404 错误
- [ ] 权限不足时返回 403 错误
- [ ] 服务器错误时返回 500 错误

### 性能测试

- [ ] 接口响应时间 < 1 秒
- [ ] 并发请求处理正常
- [ ] 大文件上传和下载正常
- [ ] WebSocket 连接稳定性测试

---

## 测试工具推荐

### 1. Postman

- 创建 Collection 管理所有接口
- 使用 Environment Variables 管理环境变量
- 使用 Tests 编写自动化测试脚本

### 2. curl

- 命令行快速测试
- 适合 CI/CD 集成
- 支持脚本化测试

### 3. JavaScript/TypeScript

- 使用 `fetch` API 测试 HTTP 接口
- 使用 `WebSocket` API 测试 WebSocket 连接
- 适合前端集成测试

### 4. Python

- 使用 `requests` 库测试 HTTP 接口
- 使用 `websockets` 库测试 WebSocket 连接
- 适合自动化测试脚本

---

## 常见问题排查

### 1. 401 未授权错误

**原因**: 缺少或无效的认证 token

**解决方案**:
- 检查请求头中是否包含 `Authorization: Bearer <token>`
- 确认 token 是否过期
- 重新登录获取新的 token

### 2. 跨域请求失败

**原因**: CORS 配置问题

**解决方案**:
- 确认 Gateway 和 Host Service 的 CORS 中间件已正确配置
- 检查浏览器控制台的 CORS 错误信息
- 确认请求头中是否包含必要的 CORS 头

### 3. WebSocket 连接失败

**原因**: 认证或网络问题

**解决方案**:
- 检查 token 是否正确传递（查询参数或请求头）
- 确认 WebSocket 服务器地址和端口正确
- 检查防火墙和网络配置

### 4. 文件下载失败

**原因**: 文件不存在或权限问题

**解决方案**:
- 确认文件路径和文件名正确
- 检查文件是否存在
- 确认用户有访问权限

---

**最后更新**: 2025-01-15  
**文档版本**: 1.0.0  
**维护者**: Host Service 开发团队

