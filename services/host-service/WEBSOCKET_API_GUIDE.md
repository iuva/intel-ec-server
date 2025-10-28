# Host Service WebSocket API 使用指南

## 📖 概述

Host Service 提供了完整的WebSocket API，支持：
1. **实时连接管理** - Host连接、心跳检测、自动断线处理
2. **消息类型路由** - 12种预定义消息类型，自动类型识别和路由
3. **指定Host通知** - 向单个或多个Host发送消息
4. **广播通知** - 向所有连接的Host广播消息
5. **可扩展处理器** - 支持自定义消息处理逻辑

---

## 🔌 WebSocket 连接

### 建立连接

```
ws://localhost:8003/api/v1/ws/host?token=your_jwt_token
```

**重要变更**: ✅ 不再需要在 URL 中传递 `host_id`，改为从 JWT token 中的 `sub` 字段获取。

### 认证方式

支持两种认证方式：

**方式1: 查询参数（推荐）**
```
ws://localhost:8003/api/v1/ws/host?token=eyJ...
```

**方式2: 请求头**
```
Authorization: Bearer eyJ...
```

### Token 要求

JWT token 必须包含以下字段：
- **`sub`**: Host ID（来自设备登录时的 `host_rec.id`）
- **`user_type`**: 必须为 `"device"`
- **`mg_id`**: 设备管理ID（可选，用于日志记录）

Token 示例 payload:
```json
{
  "sub": "123",
  "user_type": "device",
  "mg_id": "device-001",
  "host_ip": "192.168.1.100",
  "username": "device_user",
  "exp": 1640995200
}
```

### 连接示例

```python
import asyncio
import json
import websockets

async def connect():
    # ✅ 新格式：不需要在 URL 中指定 host_id
    uri = "ws://localhost:8003/api/v1/ws/host?token=your_jwt_token"
    
    async with websockets.connect(uri) as websocket:
        # 接收欢迎消息
        welcome = await websocket.recv()
        print(f"欢迎消息: {welcome}")
        
        # 发送心跳（无需指定 agent_id，从 token 中自动获取）
        heartbeat = {"type": "heartbeat"}
        await websocket.send(json.dumps(heartbeat))
        
        # 接收心跳确认
        ack = await websocket.recv()
        print(f"心跳确认: {ack}")

asyncio.run(connect())
```

### 通过 Gateway 连接

如果通过 Gateway 连接：

```
ws://localhost:8000/ws/host-service/host?token=your_jwt_token
```

Gateway 会将请求转发到 Host Service 的 `/api/v1/ws/host` 端点。

---

## 📨 消息类型

所有消息都遵循统一格式：

```json
{
  "type": "message_type",
  "timestamp": "2025-10-28T14:00:00+00:00",
  "message_id": "optional_message_id",
  // ... 其他字段
}
```

### 消息类型列表

#### 1️⃣ 连接管理

**欢迎消息** (Server → Host)
```json
{
  "type": "welcome",
  "agent_id": "host-001",
  "message": "WebSocket 连接已建立",
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

**心跳** (Host → Server)
```json
{
  "type": "heartbeat",
  "agent_id": "host-001",
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

**心跳确认** (Server → Host)
```json
{
  "type": "heartbeat_ack",
  "message": "心跳已接收",
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

#### 2️⃣ 状态管理

**状态更新** (Host → Server)
```json
{
  "type": "status_update",
  "agent_id": "host-001",
  "status": "online",
  "details": {
    "cpu_usage": 45.5,
    "memory_usage": 62.3,
    "disk_usage": 78.9
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

**状态更新确认** (Server → Host)
```json
{
  "type": "status_update_ack",
  "message": "状态更新成功",
  "status": "online",
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

#### 3️⃣ 命令执行

**命令** (Server → Host)
```json
{
  "type": "command",
  "command_id": "cmd-12345",
  "command": "restart_service",
  "args": {
    "service_name": "nginx",
    "graceful": true
  },
  "target_agents": ["host-001", "host-002"],
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

**命令响应** (Host → Server)
```json
{
  "type": "command_response",
  "agent_id": "host-001",
  "command_id": "cmd-12345",
  "success": true,
  "result": {
    "output": "Service restarted successfully",
    "exit_code": 0
  },
  "error": null,
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

#### 4️⃣ 系统通知

**通知** (Server → Host)
```json
{
  "type": "notification",
  "title": "系统维护通知",
  "content": "系统将在30分钟后进行维护",
  "level": "warning",
  "data": {
    "maintenance_time": "14:30",
    "duration_minutes": 30
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

**错误消息** (Server → Host)
```json
{
  "type": "error",
  "message": "命令执行失败",
  "error_code": "COMMAND_FAILED",
  "details": {
    "command_id": "cmd-12345",
    "reason": "Service not found"
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

---

## 🌐 HTTP API 端点

### 1. 获取活跃Host列表

**请求**
```bash
GET /api/v1/ws/hosts
Authorization: Bearer {token}
```

**响应**
```json
{
  "code": 200,
  "message": "获取活跃Host成功",
  "data": {
    "hosts": ["host-001", "host-002", "host-003"],
    "count": 3
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

### 2. 检查Host连接状态

**请求**
```bash
GET /api/v1/ws/status/{host_id}
Authorization: Bearer {token}
```

**响应**
```json
{
  "code": 200,
  "message": "获取Host状态成功",
  "data": {
    "host_id": "host-001",
    "connected": true
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

### 3. 发送消息给指定Host

**请求**
```bash
POST /api/v1/ws/send/host-001
Authorization: Bearer {token}
Content-Type: application/json

{
  "type": "command",
  "command_id": "cmd-12345",
  "command": "restart_service",
  "args": {
    "service_name": "nginx"
  }
}
```

**响应**
```json
{
  "code": 200,
  "message": "消息发送成功",
  "data": {
    "host_id": "host-001",
    "success": true
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

### 4. 发送消息给多个Host

**请求**
```bash
POST /api/v1/ws/send-to-hosts
Authorization: Bearer {token}
Content-Type: application/json

{
  "host_ids": ["host-001", "host-002", "host-003"],
  "message": {
    "type": "notification",
    "title": "系统更新",
    "content": "系统已更新到v1.2.0"
  }
}
```

**响应**
```json
{
  "code": 200,
  "message": "消息发送完成 (3/3成功)",
  "data": {
    "target_count": 3,
    "success_count": 3,
    "failed_count": 0
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

### 5. 广播消息给所有Host

**请求**
```bash
POST /api/v1/ws/broadcast?exclude_host_id=host-001
Authorization: Bearer {token}
Content-Type: application/json

{
  "type": "notification",
  "title": "紧急通知",
  "content": "检测到安全威胁",
  "level": "critical"
}
```

**响应**
```json
{
  "code": 200,
  "message": "广播完成 (9/10成功)",
  "data": {
    "total_count": 10,
    "success_count": 9,
    "failed_count": 1
  },
  "timestamp": "2025-10-28T14:00:00+00:00"
}
```

---

## 🛠️ 自定义消息处理器

### 注册自定义处理器

在 Host Service 启动时注册自定义消息处理器：

```python
from app.services.websocket_manager import WebSocketManager
from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

async def handle_custom_message(host_id: str, data: dict):
    """处理自定义消息"""
    custom_field = data.get("custom_field")
    logger.info(f"收到自定义消息: {host_id}, 字段: {custom_field}")
    
    # 处理逻辑
    # ...

# 获取WebSocketManager实例并注册
ws_manager = WebSocketManager()
ws_manager.register_handler("custom_type", handle_custom_message)
```

### 消息处理器签名

```python
async def message_handler(host_id: str, data: dict) -> None:
    """
    消息处理器
    
    Args:
        host_id: Host ID
        data: 消息数据字典
    """
    ***REMOVED***
```

---

## 📊 完整使用示例

### 客户端发送心跳示例

```python
import asyncio
import json
import websockets

async def host_client():
    uri = "ws://localhost:8003/api/v1/ws/host/host-001?token=your_jwt_token"
    
    async with websockets.connect(uri) as websocket:
        try:
            # 1. 接收欢迎消息
            welcome = json.loads(await websocket.recv())
            print(f"✅ 连接成功: {welcome['message']}")
            
            # 2. 定期发送心跳
            for i in range(5):
                await asyncio.sleep(5)
                
                heartbeat = {
                    "type": "heartbeat",
                    "agent_id": "host-001"
                }
                await websocket.send(json.dumps(heartbeat))
                print(f"💓 发送心跳 #{i+1}")
                
                # 3. 接收确认
                ack = json.loads(await websocket.recv())
                print(f"✅ 心跳确认: {ack['message']}")
        
        except websockets.exceptions.ConnectionClosed:
            print("连接已关闭")

asyncio.run(host_client())
```

### 服务端发送命令示例

```python
import httpx
import json

async def send_command():
    async with httpx.AsyncClient() as client:
        # 发送命令给指定Host
        response = await client.post(
            "http://localhost:8003/api/v1/ws/send/host-001",
            json={
                "type": "command",
                "command_id": "cmd-12345",
                "command": "update_config",
                "args": {
                    "config_key": "log_level",
                    "config_value": "debug"
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        result = response.json()
        print(f"命令发送结果: {result['data']}")

asyncio.run(send_command())
```

### 广播消息示例

```python
import httpx
import json

async def broadcast_notification():
    async with httpx.AsyncClient() as client:
        # 广播通知给所有Host
        response = await client.post(
            "http://localhost:8003/api/v1/ws/broadcast",
            params={"exclude_host_id": "host-001"},  # 排除某个Host
            json={
                "type": "notification",
                "title": "系统维护",
                "content": "系统将在22:00进行日常维护",
                "level": "warning"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        result = response.json()
        print(f"广播结果: 成功 {result['data']['success_count']}/{result['data']['total_count']}")

asyncio.run(broadcast_notification())
```

---

## 🔧 配置和调优

### 心跳超时设置

```python
from app.services.websocket_manager import WebSocketManager

ws_manager = WebSocketManager()
ws_manager.heartbeat_timeout = 60  # 秒
```

### 连接限制

当前设计支持无限制连接数，但建议：
- 生产环境：监控内存使用，定期清理断连Host
- 大规模部署：考虑负载均衡和水平扩展

---

## ⚠️ 常见问题

### Q1: WebSocket连接被拒绝（401）

**原因**: 认证令牌无效或过期

**解决**:
1. 检查令牌是否有效：`GET /auth/v1/auth/verify-token`
2. 获取新令牌：`POST /auth/v1/auth/login`
3. 使用新令牌重新连接

### Q2: 消息发送失败（Host未连接）

**原因**: 目标Host没有建立WebSocket连接

**解决**:
1. 检查Host连接状态：`GET /api/v1/ws/status/{host_id}`
2. 查看Host是否在线：`GET /api/v1/ws/hosts`
3. 检查Host日志确认连接问题

### Q3: 心跳超时警告

**原因**: Host超过60秒未发送心跳

**解决**:
1. 检查Host网络连接
2. 检查Host端应用状态
3. 增加心跳检测间隔或超时时间

---

## 📚 架构设计

### 消息流

```
┌─────────────────┐
│   Host Client   │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────────────────────────┐
│  Host Service WebSocket Manager     │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Message Router & Handler     │  │
│  │ (按type自动路由)             │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │ Connection Pool              │  │
│  │ {host_id -> WebSocket}       │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │ Heartbeat Monitor            │  │
│  │ (定期检测连接活跃性)         │  │
│  └──────────────────────────────┘  │
└────────┬────────────────────────────┘
         │ Async Operations
         ▼
┌─────────────────┐
│  Host Service   │
│  Business Logic │
└─────────────────┘
```

---

**文档版本**: 1.0  
**最后更新**: 2025-10-28  
**作者**: AI Assistant
