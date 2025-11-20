# WebSocket 详细使用指南

## 📚 目录

- [快速开始](#快速开始)
- [建立连接](#建立连接)
- [认证机制](#认证机制)
- [心跳检测](#心跳检测)
- [消息类型](#消息类型)
- [获取在线Host](#获取在线host)
- [发送消息](#发送消息)
- [广播功能](#广播功能)
- [错误处理](#错误处理)
- [完整示例](#完整示例)
- [故障排查](#故障排查)

---

## 🚀 快速开始

### 最简单的连接示例

```python
import asyncio
import json
import websockets

async def connect():
    # 获取认证Token
    token = "your_jwt_token_here"
    
    # 建立WebSocket连接
    uri = f"ws://localhost:8003/api/v1/ws/host?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # 接收欢迎消息
        welcome = await websocket.recv()
        print(f"✅ 连接成功: {welcome}")
        
        # 发送心跳
        heartbeat = {"type": "heartbeat"}
        await websocket.send(json.dumps(heartbeat))
        
        # 接收心跳确认
        ack = await websocket.recv()
        print(f"💓 心跳确认: {ack}")

asyncio.run(connect())
```

### 通过Gateway连接

```python
# 通过Gateway访问Host Service
uri = f"ws://localhost:8000/api/v1/ws/host?token={token}"
```

---

## 🔌 建立连接

### 连接端点

**直接连接 Host Service:**

```
ws://localhost:8003/api/v1/ws/host
```

**通过 Gateway 连接:**

```
ws://localhost:8000/api/v1/ws/host
```

### 连接参数

| 参数 | 必需 | 说明 | 示例 |
|-----|------|------|------|
| `Authorization` | ✅ | 请球头JWT认证令牌（推荐） | `?token=eyJhbGc...` |
| `token` | ✅ | JWT认证令牌（不推荐） | `?token=eyJhbGc...` |

### ⚠️ 重要变更

**新版本 (v1.2.0+):**

- ✅ **不再需要** 在 URL 中传递 `host_id`
- ✅ `host_id` 自动从 JWT token 的 `sub` 字段中提取
- ✅ 更安全、更符合标准

**旧版本 (已废弃):**

```
❌ ws://localhost:8003/api/v1/ws/host/{host_id}?token=xxx
```

**新版本 (推荐):**

```
✅ ws://localhost:8003/api/v1/ws/host?token=xxx
```

### 连接流程

```
1. 客户端发起WebSocket连接请求
   ↓
2. Gateway/Host Service 验证Token
   ↓
3. 从Token中提取host_id (sub字段)
   ↓
4. 连接建立成功，返回欢迎消息
   ↓
5. 开始正常通信
```

### Python 连接示例

```python
import asyncio
import json
import websockets
from typing import Optional

class WebSocketClient:
    def __init__(self, token: str, host: str = "localhost", port: int = 8003):
        self.token = token
        self.uri = f"ws://{host}:{port}/api/v1/ws/host?token={token}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
    
    async def connect(self):
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(self.uri)
            
            # 接收欢迎消息
            welcome = json.loads(await self.websocket.recv())
            print(f"✅ 连接成功: {welcome['message']}")
            print(f"📍 Host ID: {welcome['agent_id']}")
            
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 连接已断开")

# 使用示例
async def main():
    client = WebSocketClient(token="your_token_here")
    if await client.connect():
        # 连接成功，进行其他操作
        await client.disconnect()

asyncio.run(main())
```

### JavaScript 连接示例

```javascript
// 原生 WebSocket
const token = 'your_jwt_token_here';
const ws = new WebSocket(`ws://localhost:8003/api/v1/ws/host?token=${token}`);

ws.onopen = () => {
    console.log('✅ WebSocket 连接成功');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('📥 收到消息:', message);
    
    if (message.type === 'welcome') {
        console.log('🎉 欢迎消息:', message.message);
        console.log('📍 Host ID:', message.agent_id);
    }
};

ws.onerror = (error) => {
    console.error('❌ WebSocket 错误:', error);
};

ws.onclose = (event) => {
    console.log('🔌 WebSocket 连接已关闭:', event.code, event.reason);
};
```

---

## 🔐 认证机制

### Token 获取

#### 管理员Token

```bash
curl -X POST 'http://localhost:8000/api/v1/auth/admin/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "***REMOVED***word": "your_***REMOVED***word"
  }'
```

#### 设备Token

```bash
curl -X POST 'http://localhost:8000/api/v1/auth/device/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "host-001",
    "device_secret": "your_secret"
  }'
```

### Token 格式

JWT Token 必须包含以下字段：

```json
{
  "sub": "1846486359367955051",  // ✅ Host ID (从这里提取)
  "user_type": "device",         // ✅ 必须为 "device"
  "mg_id": "device-001",         // 设备管理ID
  "host_ip": "192.168.1.100",   // 设备IP地址
  "username": "device_user",     // 用户名
  "exp": 1640995200,            // 过期时间
  "type": "access",             // Token类型
  "iat": 1640991600            // 签发时间
}
```

### 认证方式

#### 方式1: 查询参数

```
ws://localhost:8003/api/v1/ws/host?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 方式2: Authorization Header (推荐)

```python
import websockets

async with websockets.connect(
    "ws://localhost:8003/api/v1/ws/host",
    extra_headers={"Authorization": f"Bearer {token}"}
) as websocket:
    # 连接成功
    ***REMOVED***
```

#### 方式3: X-Token Header

```python
async with websockets.connect(
    "ws://localhost:8003/api/v1/ws/host",
    extra_headers={"X-Token": token}
) as websocket:
    # 连接成功
    ***REMOVED***
```

### 认证错误处理

```python
try:
    async with websockets.connect(uri) as websocket:
        # 正常使用
        ***REMOVED***
except websockets.exceptions.InvalidStatusCode as e:
    if e.status_code == 401:
        print("❌ 认证失败: Token无效或已过期")
    elif e.status_code == 403:
        print("❌ 权限不足: Token类型错误")
    else:
        print(f"❌ 连接失败: HTTP {e.status_code}")
```

---

## 💓 心跳检测

### 心跳机制说明

- **目的**: 保持连接活跃，检测网络断线
- **频率**: 建议每 **30-60秒** 发送一次心跳
- **超时**: 服务器端超过 **60秒** 未收到心跳会认为连接断开

### 发送心跳

```python
import asyncio
import json
import websockets
from datetime import datetime, timezone

async def send_heartbeat(websocket):
    """发送心跳消息"""
    heartbeat = {
        "type": "heartbeat",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await websocket.send(json.dumps(heartbeat))
    print(f"💓 发送心跳: {heartbeat['timestamp']}")

# 使用示例
async with websockets.connect(uri) as websocket:
    await send_heartbeat(websocket)
    
    # 接收心跳确认
    ack = json.loads(await websocket.recv())
    if ack['type'] == 'heartbeat_ack':
        print(f"✅ 心跳确认: {ack['message']}")
```

### 自动心跳循环

```python
import asyncio
import json
import websockets
from datetime import datetime, timezone

async def heartbeat_loop(websocket, interval=30):
    """自动心跳循环"""
    try:
        while True:
            # 发送心跳
            heartbeat = {
                "type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(heartbeat))
            print(f"💓 发送心跳")
            
            # 等待下一次心跳
            await asyncio.sleep(interval)
    except websockets.exceptions.ConnectionClosed:
        print("❌ 连接已关闭，停止心跳")

async def receive_messages(websocket):
    """接收消息循环"""
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"📥 收到消息: {data}")
    except websockets.exceptions.ConnectionClosed:
        print("❌ 连接已关闭，停止接收")

async def main():
    uri = f"ws://localhost:8003/api/v1/ws/host?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # 接收欢迎消息
        welcome = json.loads(await websocket.recv())
        print(f"✅ {welcome['message']}")
        
        # 同时运行心跳和消息接收
        await asyncio.gather(
            heartbeat_loop(websocket, interval=30),
            receive_messages(websocket)
        )

asyncio.run(main())
```

### 心跳监控

服务器端会监控所有连接的心跳状态：

```python
# 服务器端日志示例
2025-10-28 10:00:00 | INFO | 📥 接收消息 | agent_id=host-001 | message_type=heartbeat
2025-10-28 10:00:00 | INFO | 📤 发送消息 | host_id=host-001 | message_type=heartbeat_ack
2025-10-28 10:01:00 | WARNING | ⚠️ Host 心跳超时: host-002 (最后心跳: 65秒前)
```

### 心跳最佳实践

1. **客户端定时发送**: 建议每30-60秒发送一次
2. **等待确认**: 发送心跳后等待 `heartbeat_ack` 确认
3. **超时处理**: 如果3次心跳未收到确认，考虑重连
4. **错误重试**: 心跳发送失败时，尝试重新连接

---

## 🔄 消息流向全景

为了方便 Agent、Browser 插件以及后端排查问题，本节整理了最重要的消息流向。所有消息都遵循 [消息类型](#-消息类型) 中的格式，以下流程引用 `MessageType` 枚举值，方便与代码对应。

### 1. 连接建立与认证（Server ↔ Agent）

```
Browser/Agent ──► Gateway/Host Service ──► 验证 JWT
                             │
                             └──► `welcome`（Server → Agent）
```

1. Agent 通过 Gateway 或 Host Service 发起 WebSocket 连接。
2. 服务端验证 Token，提取 `host_id`/`agent_id`。
3. 连接建立成功后发送 `welcome`，携带 `agent_id`、当前时间等信息。

### 2. 心跳与离线判定（Agent ↔ Server）

```
Agent ──► `heartbeat`
Server ──► `heartbeat_ack`
Server ──► `heartbeat_timeout_warning`（超时 1 次）
Server ──► `host_offline_notification`（超时 2 次仍未恢复）
```

- 默认 30~60s 发送一次 `heartbeat`。
- Server 每次收到心跳后返回 `heartbeat_ack`。
- 如果 60s 内未收到心跳，会先推送 `heartbeat_timeout_warning`，提醒 Agent 10 秒内自检。
- 如果再次超时，Server 会主动关闭连接，并广播 `host_offline_notification`，驱动 host 状态更新。

### 3. 状态同步 & 审批场景（Agent → Server）

```
Agent ──► `status_update`
Server ──► 更新 host_rec / host_exec_log
Server ──► `status_update_ack`
```

- Agent 上报运行状态、资源占用、任务进度等。
- 服务端写入数据库，并在需要时触发审批链（详见 `docs/host-state-transition-rules.md`）。
- 成功后返回 `status_update_ack`，避免重复上报。

### 4. 命令下发与执行结果（Server → Agent）

```
控制台/API ──► Server ──► `command`
Agent ──► 执行指令
Agent ──► `command_response`（成功或失败）
```

- 控制台通过 `POST /api/v1/host/ws/send` / `send-to-hosts` / `broadcast` 提交命令。
- Server 将命令序列化成 `command` 推送给指定 Agent。
- Agent 执行后用同一个 `command_id` 回传 `command_response`，便于审计。
- 如果 Agent 在执行过程中检测到 VNC/测试任务启动结果，会额外发送 `connection_result` 告知浏览器插件。

### 5. 浏览器 VNC 连接与日志监控（Browser → Server → Agent）

```
Browser ──► HTTP `/api/v1/browser/vnc/report` 上报结果
Server ──► 更新 host_exec_log / host_state
Server ──► `connection_notification`（Server → Agent）
Agent ──► 启动日志监控/回放
```

- 浏览器插件在 VNC 链接成功后通过 HTTP 报告状态。
- Server 写入数据库并派发 `connection_notification` 给对应 Agent，携带 `host_id`、动作（`start_log_monitoring`）等信息。
- Agent 收到通知后进入日志监控模式，配合浏览器实时展示。

> 📌 提示：更多状态流转可参考 `docs/host-state-transition-rules.md`，WebSocket 消息是其中的关键触发器。

---

## 📨 消息类型

### 消息格式规范

所有消息都遵循统一格式：

```json
{
  "type": "message_type",           // ✅ 必需: 消息类型
  "timestamp": "2025-10-28T10:00:00+00:00",  // 时间戳
  "message_id": "optional_id",      // 可选: 消息ID
  // ... 其他字段根据类型而定
}
```

### 完整消息类型列表

| 消息类型 | 方向 | 说明 | 示例 |
|---------|------|------|------|
| `welcome` | Server → Client | 连接成功欢迎消息 | [示例](#welcome-欢迎消息) |
| `heartbeat` | Client → Server | 客户端心跳 | [示例](#heartbeat-心跳) |
| `heartbeat_ack` | Server → Client | 心跳确认 | [示例](#heartbeat_ack-心跳确认) |
| `status_update` | Client → Server | 状态更新 | [示例](#status_update-状态更新) |
| `status_update_ack` | Server → Client | 状态更新确认 | [示例](#status_update_ack-状态更新确认) |
| `command` | Server → Client | 执行命令 | [示例](#command-命令) |
| `command_response` | Client → Server | 命令执行结果 | [示例](#command_response-命令响应) |
| `notification` | Server → Client | 系统通知/公告 | [示例](#notification-通知) |
| `error` | Server → Client | 错误消息 | [示例](#error-错误) |
| `config_update` | Server → Client | 配置更新 | [示例](#config_update-配置更新) |
| `log` | Client → Server | 日志上报 | [示例](#log-日志) |
| `metric` | Client → Server | 指标数据 | [示例](#metric-指标) |
| `connection_result` | Client → Server | Agent 上报连接结果（如 VNC） | [示例](#connection_result-连接结果) |
| `heartbeat_timeout_warning` | Server → Client | 心跳超时预警 | [示例](#heartbeat_timeout_warning-心跳超时预警) |
| `host_offline_notification` | Server → Client | Host 下线通知 | [示例](#host_offline_notification-host-下线通知) |
| `connection_notification` | Server → Client | 连接成功后通知 Agent 开启日志监控 | [示例](#connection_notification-连接通知) |

### 消息类型详解

#### `welcome` 欢迎消息

连接建立后服务器自动发送的欢迎消息。

```json
{
  "type": "welcome",
  "agent_id": "1846486359367955051",
  "message": "WebSocket 连接已建立",
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `heartbeat` 心跳

客户端定期发送的心跳消息。

```json
{
  "type": "heartbeat",
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `heartbeat_ack` 心跳确认

服务器对心跳的确认响应。

```json
{
  "type": "heartbeat_ack",
  "message": "心跳已接收",
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `status_update` 状态更新

客户端上报自身状态信息。

```json
{
  "type": "status_update",
  "status": "running",
  "details": {
    "cpu_usage": 45.5,
    "memory_usage": 62.3,
    "disk_usage": 78.9,
    "network_rx": 1024000,
    "network_tx": 512000
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `status_update_ack` 状态更新确认

服务器确认状态更新。

```json
{
  "type": "status_update_ack",
  "message": "状态更新成功",
  "status": "running",
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `command` 命令

服务器向客户端发送执行命令。

```json
{
  "type": "command",
  "command_id": "cmd-12345",
  "command": "restart_service",
  "args": {
    "service_name": "nginx",
    "graceful": true,
    "timeout": 30
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `command_response` 命令响应

客户端返回命令执行结果。

```json
{
  "type": "command_response",
  "command_id": "cmd-12345",
  "success": true,
  "result": {
    "output": "Service nginx restarted successfully",
    "exit_code": 0,
    "duration_ms": 1500
  },
  "error": null,
  "timestamp": "2025-10-28T10:00:02+00:00"
}
```

**失败响应:**

```json
{
  "type": "command_response",
  "command_id": "cmd-12345",
  "success": false,
  "result": null,
  "error": {
    "code": "SERVICE_NOT_FOUND",
    "message": "Service nginx not found"
  },
  "timestamp": "2025-10-28T10:00:02+00:00"
}
```

#### `notification` 通知

服务器向客户端发送通知消息。

```json
{
  "type": "notification",
  "title": "系统维护通知",
  "content": "系统将在30分钟后进行维护，预计维护时间30分钟",
  "level": "warning",  // info, warning, error, critical
  "data": {
    "maintenance_time": "14:30",
    "duration_minutes": 30,
    "affected_services": ["api", "web"]
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `error` 错误

服务器向客户端发送错误消息。

```json
{
  "type": "error",
  "message": "命令执行失败",
  "error_code": "COMMAND_FAILED",
  "details": {
    "command_id": "cmd-12345",
    "reason": "Service not found",
    "suggestion": "Check service name and try again"
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `config_update` 配置更新

服务器向客户端推送配置更新。

```json
{
  "type": "config_update",
  "config_key": "log_level",
  "config_value": "debug",
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `log` 日志

客户端向服务器上报日志。

```json
{
  "type": "log",
  "level": "error",
  "message": "Failed to connect to database",
  "details": {
    "error": "Connection timeout",
    "database": "mysql",
    "host": "localhost:3306"
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `metric` 指标

客户端向服务器上报性能指标。

```json
{
  "type": "metric",
  "metrics": {
    "cpu_usage": 45.5,
    "memory_usage": 62.3,
    "disk_usage": 78.9,
    "network_rx_bytes": 1024000,
    "network_tx_bytes": 512000,
    "process_count": 125
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### `connection_result` 连接结果

Agent 在完成某些操作（例如代理 VNC、执行远控指令）后需要把成功/失败情况告诉服务器，便于浏览器或控制台更新 UI。

```json
{
  "type": "connection_result",
  "host_id": "1846486359367955051",
  "task_id": "case-20250129-001",
  "success": true,
  "message": "VNC 连接成功",
  "details": {
    "user": "qa_user",
    "ip": "10.1.2.3",
    "session_id": "vnc-aaa-bbb"
  },
  "timestamp": "2025-10-28T10:00:05+00:00"
}
```

#### `heartbeat_timeout_warning` 心跳超时预警

当 Server 超过阈值未收到心跳，会先发送警告，让 Agent 有 10 秒缓冲时间打印日志或尝试自检。若仍未恢复，将触发下线流程。

```json
{
  "type": "heartbeat_timeout_warning",
  "message": "60 秒内未收到心跳，请检查网络/进程状态",
  "timeout": 60,
  "host_id": "1846486359367955051",
  "timestamp": "2025-10-28T10:02:00+00:00"
}
```

#### `host_offline_notification` Host 下线通知

的确确认 Agent 已经掉线时推送。Agent 收到后应停止本地任务并更新埋点；Browser/控制台也会据此刷新 host 状态。

```json
{
  "type": "host_offline_notification",
  "host_id": "1846486359367955051",
  "message": "Host 已离线，日志监控已停止",
  "reason": "heartbeat_timeout",
  "timestamp": "2025-10-28T10:02:15+00:00"
}
```

#### `connection_notification` 连接通知

当浏览器 VNC 报告成功，Server 会把这个通知推送给 Agent，指导其开始日志监控或执行后续动作。

```json
{
  "type": "connection_notification",
  "host_id": "1846486359367955051",
  "action": "start_log_monitoring",
  "message": "VNC 连接成功，请开始日志监控",
  "details": {
    "browser_user": "qa_admin",
    "case_id": "case-20250129-001",
    "ip": "10.1.2.3"
  },
  "timestamp": "2025-10-28T10:00:12+00:00"
}
```

---

## 🌐 获取在线Host

### HTTP API 方式

#### 获取所有活跃Host

```bash
curl -X GET 'http://localhost:8000/api/v1/host/ws/hosts' \
  -H "Authorization: Bearer $TOKEN"
```

**响应:**

```json
{
  "code": 200,
  "message": "获取活跃Host成功",
  "data": {
    "hosts": [
      "1846486359367955051",
      "1846486359367955052",
      "1846486359367955053"
    ],
    "count": 3
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

#### 检查特定Host状态

```bash
curl -X GET 'http://localhost:8000/api/v1/host/ws/status/1846486359367955051' \
  -H "Authorization: Bearer $TOKEN"
```

**响应:**

```json
{
  "code": 200,
  "message": "获取Host状态成功",
  "data": {
    "host_id": "1846486359367955051",
    "connected": true
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

### Python 客户端示例

```python
import httpx
import asyncio

async def get_active_hosts(token: str) -> list:
    """获取所有活跃的Host列表"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/host/ws/hosts",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['data']['hosts']
        else:
            print(f"❌ 获取失败: {response.status_code}")
            return []

async def check_host_status(token: str, host_id: str) -> bool:
    """检查特定Host是否在线"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/host/ws/status/{host_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['data']['connected']
        else:
            return False

# 使用示例
async def main():
    token = "your_token_here"
    
    # 获取所有在线Host
    hosts = await get_active_hosts(token)
    print(f"📊 在线Host数量: {len(hosts)}")
    print(f"📋 Host列表: {hosts}")
    
    # 检查特定Host状态
    if hosts:
        host_id = hosts[0]
        is_online = await check_host_status(token, host_id)
        print(f"🔍 Host {host_id} 状态: {'在线' if is_online else '离线'}")

asyncio.run(main())
```

---

## 📤 发送消息

### 发送消息给单个Host

```bash
curl -X POST 'http://localhost:8000/api/v1/host/ws/send' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host_id": "1846486359367955051",
    "message": {
      "type": "command",
      "command_id": "cmd-12345",
      "command": "restart_service",
      "args": {
        "service_name": "nginx"
      }
    }
  }'
```

**响应:**

```json
{
  "code": 200,
  "message": "消息发送成功",
  "data": {
    "host_id": "1846486359367955051",
    "success": true
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

### 发送消息给多个Host

```bash
curl -X POST 'http://localhost:8000/api/v1/host/ws/send-to-hosts' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host_ids": [
      "1846486359367955051",
      "1846486359367955052",
      "1846486359367955053"
    ],
    "message": {
      "type": "notification",
      "title": "系统更新",
      "content": "系统已更新到v1.2.0，请注意查看更新日志"
    }
  }'
```

**响应:**

```json
{
  "code": 200,
  "message": "消息发送完成 (3/3成功)",
  "data": {
    "target_count": 3,
    "success_count": 3,
    "failed_count": 0
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

### Python 发送消息示例

```python
import httpx
import asyncio

async def send_message_to_host(token: str, host_id: str, message: dict):
    """发送消息给指定Host"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/host/ws/send",
            json={
                "host_id": host_id,
                "message": message
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return response.json()

async def send_message_to_hosts(token: str, host_ids: list, message: dict):
    """发送消息给多个Host"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/host/ws/send-to-hosts",
            json={
                "host_ids": host_ids,
                "message": message
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return response.json()

# 使用示例
async def main():
    token = "your_token_here"
    
    # 发送命令给单个Host
    result = await send_message_to_host(
        token,
        "1846486359367955051",
        {
            "type": "command",
            "command": "restart_service",
            "args": {"service_name": "nginx"}
        }
    )
    print(f"✅ 发送结果: {result['message']}")
    
    # 发送通知给多个Host
    result = await send_message_to_hosts(
        token,
        ["1846486359367955051", "1846486359367955052"],
        {
            "type": "notification",
            "title": "测试通知",
            "content": "这是一条测试通知消息"
        }
    )
    print(f"✅ 广播结果: {result['data']}")

asyncio.run(main())
```

---

## 📢 广播功能

### 广播消息给所有Host

```bash
curl -X POST 'http://localhost:8000/api/v1/host/ws/broadcast' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "notification",
      "title": "紧急通知",
      "content": "检测到安全威胁，请立即检查系统",
      "level": "critical"
    }
  }'
```

### 排除特定Host的广播

```bash
curl -X POST 'http://localhost:8000/api/v1/host/ws/broadcast?exclude_host_id=1846486359367955051' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "notification",
      "title": "系统维护",
      "content": "系统将在30分钟后进行维护"
    }
  }'
```

**响应:**

```json
{
  "code": 200,
  "message": "广播完成 (9/10成功)",
  "data": {
    "total_count": 10,
    "success_count": 9,
    "failed_count": 1
  },
  "timestamp": "2025-10-28T10:00:00+00:00"
}
```

### Python 广播示例

```python
import httpx
import asyncio

async def broadcast_message(
    token: str, 
    message: dict, 
    exclude_host_id: str = None
):
    """广播消息给所有Host"""
    async with httpx.AsyncClient() as client:
        params = {}
        if exclude_host_id:
            params["exclude_host_id"] = exclude_host_id
        
        response = await client.post(
            "http://localhost:8000/api/v1/host/ws/broadcast",
            params=params,
            json={"message": message},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return response.json()

# 使用示例
async def main():
    token = "your_token_here"
    
    # 广播紧急通知
    result = await broadcast_message(
        token,
        {
            "type": "notification",
            "title": "紧急通知",
            "content": "检测到系统异常，请立即处理",
            "level": "critical"
        }
    )
    
    print(f"📢 广播结果:")
    print(f"  总数: {result['data']['total_count']}")
    print(f"  成功: {result['data']['success_count']}")
    print(f"  失败: {result['data']['failed_count']}")

asyncio.run(main())
```

---

## ⚠️ 错误处理

### WebSocket 错误码

| Close Code | 含义 | 原因 | 处理建议 |
|-----------|------|------|---------|
| 1000 | 正常关闭 | 客户端主动关闭 | 无需处理 |
| 1001 | 端点离开 | 页面关闭或导航 | 无需处理 |
| 1005 | 无状态码 | 正常断开连接 | 无需处理 |
| 1006 | 异常关闭 | 连接异常中断 | 检查网络，尝试重连 |
| 1008 | 策略违规 | 认证失败 | 检查Token，重新登录 |
| 1011 | 服务器错误 | 后端处理异常 | 查看日志，联系管理员 |

### HTTP 错误码

| 状态码 | 含义 | 原因 | 解决方案 |
|-------|------|------|---------|
| 200 | 成功 | 请求成功 | - |
| 401 | 未授权 | Token缺失/过期/无效 | 重新登录获取Token |
| 403 | 禁止访问 | Token类型错误或权限不足 | 使用正确类型Token |
| 404 | 未找到 | API路径错误或Host不存在 | 检查路径和Host ID |
| 500 | 服务器错误 | 后端服务异常 | 查看日志排查问题 |

### Python 错误处理示例

```python
import asyncio
import json
import websockets
from websockets.exceptions import (
    ConnectionClosed,
    InvalidStatusCode,
    WebSocketException
)

async def connect_with_error_handling(uri: str, max_retries: int = 3):
    """带错误处理的WebSocket连接"""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"✅ 连接成功")
                
                # 正常通信
                async for message in websocket:
                    data = json.loads(message)
                    print(f"📥 收到消息: {data}")
                    
        except InvalidStatusCode as e:
            if e.status_code == 401:
                print(f"❌ 认证失败: Token无效或已过期")
                break  # 不重试，需要重新获取Token
            elif e.status_code == 403:
                print(f"❌ 权限不足: Token类型错误")
                break
            else:
                print(f"❌ HTTP错误: {e.status_code}")
                retry_count += 1
                
        except ConnectionClosed as e:
            if e.code == 1000:
                print(f"✅ 连接正常关闭")
                break
            elif e.code == 1008:
                print(f"❌ 认证失败: {e.reason}")
                break
            else:
                print(f"⚠️ 连接意外关闭: code={e.code}, reason={e.reason}")
                retry_count += 1
                
        except WebSocketException as e:
            print(f"❌ WebSocket异常: {e}")
            retry_count += 1
            
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            retry_count += 1
        
        if retry_count < max_retries:
            wait_time = 2 ** retry_count  # 指数退避
            print(f"⏳ 等待 {wait_time}秒后重试...")
            await asyncio.sleep(wait_time)
        else:
            print(f"❌ 达到最大重试次数 ({max_retries})")

# 使用示例
asyncio.run(connect_with_error_handling(uri))
```

---

## 📦 完整示例

### 完整的客户端实现

```python
import asyncio
import json
import websockets
from datetime import datetime, timezone
from typing import Optional, Callable
from websockets.exceptions import ConnectionClosed

class WebSocketClient:
    def __init__(
        self, 
        token: str,
        host: str = "localhost",
        port: int = 8003,
        heartbeat_interval: int = 30
    ):
        self.token = token
        self.uri = f"ws://{host}:{port}/api/v1/ws/host?token={token}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.heartbeat_interval = heartbeat_interval
        self.running = False
        
        # 消息处理器
        self.message_handlers = {}
    
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
    
    async def connect(self):
        """建立连接"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.running = True
            
            # 接收欢迎消息
            welcome = json.loads(await self.websocket.recv())
            print(f"✅ 连接成功: {welcome['message']}")
            print(f"📍 Host ID: {welcome['agent_id']}")
            
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            print("🔌 连接已断开")
    
    async def send_message(self, message: dict):
        """发送消息"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.send(json.dumps(message))
    
    async def heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.running:
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_message(heartbeat)
                print(f"💓 发送心跳")
                await asyncio.sleep(self.heartbeat_interval)
        except ConnectionClosed:
            print("❌ 心跳循环停止: 连接已关闭")
    
    async def receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get('type')
                
                # 调用对应的消息处理器
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](data)
                else:
                    print(f"📥 收到消息: {data}")
        except ConnectionClosed:
            print("❌ 接收循环停止: 连接已关闭")
    
    async def run(self):
        """启动客户端"""
        if not await self.connect():
            return
        
        try:
            # 同时运行心跳和消息接收
            await asyncio.gather(
                self.heartbeat_loop(),
                self.receive_loop()
            )
        except KeyboardInterrupt:
            print("\n⚠️ 收到中断信号")
        finally:
            await self.disconnect()

# 使用示例
async def main():
    token = "your_token_here"
    client = WebSocketClient(token, heartbeat_interval=30)
    
    # 注册消息处理器
    async def handle_command(data: dict):
        print(f"📋 收到命令: {data['command']}")
        # 执行命令...
        # 返回结果
        await client.send_message({
            "type": "command_response",
            "command_id": data['command_id'],
            "success": True,
            "result": {"output": "Command executed successfully"}
        })
    
    async def handle_notification(data: dict):
        print(f"📢 收到通知: {data['title']} - {data['content']}")
    
    async def handle_heartbeat_ack(data: dict):
        print(f"✅ 心跳确认: {data['message']}")
    
    client.register_handler("command", handle_command)
    client.register_handler("notification", handle_notification)
    client.register_handler("heartbeat_ack", handle_heartbeat_ack)
    
    # 运行客户端
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 故障排查

### 常见问题

#### Q1: WebSocket连接被拒绝（401）

**症状**: `InvalidStatusCode: server rejected WebSocket connection: HTTP 401`

**原因**:

- Token无效或已过期
- Token未正确传递

**解决方案**:

```python
# 1. 检查Token是否有效
async def verify_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/introspect",
            json={"token": token}
        )
        result = response.json()
        return result['data']['active']

# 2. 重新获取Token
async def get_new_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/device/login",
            json={
                "device_id": "your_device_id",
                "device_secret": "your_secret"
            }
        )
        result = response.json()
        return result['data']['access_token']
```

#### Q2: 消息发送失败（Host未连接）

**症状**: `{"code": 400, "message": "Host未连接"}`

**原因**: 目标Host没有建立WebSocket连接

**解决方案**:

```python
# 1. 检查Host连接状态
async def check_host_connected(token: str, host_id: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/host/ws/status/{host_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        result = response.json()
        return result['data']['connected']

# 2. 等待Host连接
async def wait_for_host(token: str, host_id: str, timeout: int = 60):
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await check_host_connected(token, host_id):
            return True
        await asyncio.sleep(1)
    return False
```

#### Q3: 心跳超时警告

**症状**: 服务器日志显示 "⚠️ Host 心跳超时"

**原因**: Host超过60秒未发送心跳

**解决方案**:

1. 检查网络连接稳定性
2. 调整心跳间隔（建议30秒）
3. 增加错误重试机制

```python
# 更可靠的心跳实现
async def reliable_heartbeat_loop(client, interval=30):
    consecutive_failures = 0
    max_failures = 3
    
    while client.running:
        try:
            await client.send_message({
                "type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            consecutive_failures = 0  # 重置失败计数
            await asyncio.sleep(interval)
        except Exception as e:
            consecutive_failures += 1
            print(f"⚠️ 心跳发送失败 ({consecutive_failures}/{max_failures}): {e}")
            
            if consecutive_failures >= max_failures:
                print("❌ 心跳失败次数过多，尝试重连")
                await client.reconnect()
                consecutive_failures = 0
            else:
                await asyncio.sleep(5)  # 短暂等待后重试
```

### 调试工具

#### 查看WebSocket日志

```bash
# 查看Host Service WebSocket日志
docker-compose logs -f host-service | grep -E "(📥|📤|📢|❌)"

# 查看特定Host的消息
docker-compose logs host-service | grep "host-001"

# 查看心跳消息
docker-compose logs host-service | grep "heartbeat"

# 查看错误消息
docker-compose logs host-service | grep "ERROR"
```

#### 使用wscat测试

```bash
# 安装wscat
npm install -g wscat

# 测试连接
wscat -c "ws://localhost:8003/api/v1/ws/host?token=$TOKEN"

# 发送心跳
> {"type":"heartbeat"}

# 发送状态更新
> {"type":"status_update","status":"running","details":{"cpu":45.5}}
```

---

## 📚 相关文档

- [WebSocket 快速指南](./WEBSOCKET_GUIDE.md) - 简化版使用指南
- [Host Service WebSocket API](../services/host-service/WEBSOCKET_API_GUIDE.md) - 详细API文档
- [WebSocket 日志指南](../services/host-service/WEBSOCKET_LOGGING_GUIDE.md) - 日志分析
- [认证架构文档](./12-authentication-architecture.md) - 认证系统说明

---

## 📝 更新历史

### v1.3.0 (2025-11-19)

- ✅ 新增“消息流向全景”章节，覆盖连接、心跳、状态同步、命令、VNC 日志监控等链路
- ✅ 补充 `connection_result`、`heartbeat_timeout_warning`、`host_offline_notification`、`connection_notification` 的使用说明
- ✅ 更新消息类型总表，指明方向与业务场景

### v1.2.0 (2025-10-28)

- ✅ 完整的WebSocket使用指南
- ✅ 新增从Token获取host_id的认证优化
- ✅ 心跳检测详细说明
- ✅ 完整的消息类型说明
- ✅ HTTP API获取在线Host
- ✅ 错误处理最佳实践
- ✅ 完整的Python客户端示例

---

**作者**: Intel EC开发团队  
**最后更新**: 2025-10-28  
**文档版本**: 1.0
