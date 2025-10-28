# WebSocket 403 Forbidden 问题深度诊断

## 🔍 问题现象

```
INFO:     ('192.168.65.1', 46494) - "WebSocket /ws/agent/agent-123" 403
INFO:     connection rejected (403 Forbidden)
INFO:     connection closed
```

## 🎯 关键发现

1. **错误来源**: 这个 403 错误来自 **FastAPI/Starlette 框架层面**，而不是认证中间件
2. **时机**: 在 WebSocket 握手时直接返回
3. **原因**: WebSocket 握手涉及两个阶段：
   - **HTTP 升级握手** (GET 请求)
   - **WebSocket 帧协议** (升级后的连接)

## 📊 问题分析

### 第一阶段: HTTP 升级握手

```
GET /ws/agent/agent-123 HTTP/1.1
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: ...
Sec-WebSocket-Version: 13
Authorization: Bearer <token>  ← 你提供的 token
```

**问题**: 
- 网关的 `/ws/agent/agent-123` 路径不正确
- 正确的路径应该是: `/ws/host-service/ws/agent/agent-123`
- 即使你提供了 token，**路径本身就无法匹配到代理端点**

### 第二阶段: 路由匹配失败

在 `gateway-service/app/api/v1/endpoints/proxy.py` 中：

```python
@router.websocket("/ws/{service_name}/{path:path}")
async def websocket_proxy(
    websocket: WebSocket,
    service_name: str,
    path: str,
    proxy_service: ProxyService = Depends(get_proxy_service),
) -> None:
```

路由期望:
- `/ws/{service_name}/{path:path}`
- 例如: `/ws/host-service/ws/agent/agent-123`

你的请求:
- `/ws/agent/agent-123` ← **缺少 service_name 参数!**

**所以根本问题是: 404 路由不存在 → FastAPI 返回 403 (WebSocket握手失败)**

## ✅ 解决方案

### 1. **正确的 WebSocket 地址格式**

```
ws://localhost:8000/ws/{service_name}/{path}
```

具体例子:
```
ws://localhost:8000/ws/host-service/ws/agent/agent-123
```

参数说明:
- `service_name`: `host-service` (后端服务名称)
- `path`: `ws/agent/agent-123` (后端服务上的实际路径)

### 2. **Python 客户端连接示例**

```python
import asyncio
import websockets
import json

async def connect_websocket():
    """连接到 WebSocket 端点"""
    
    # ✅ 正确的地址
    uri = "ws://localhost:8000/ws/host-service/ws/agent/agent-123"
    
    # 可选: 添加 Authorization 头
    headers = {
        "Authorization": "Bearer your-jwt-token-here"
    }
    
    try:
        async with websockets.connect(
            uri,
            extra_headers=headers.items()
        ) as websocket:
            print("✅ WebSocket 连接成功")
            
            # 发送测试消息
            await websocket.send(json.dumps({"type": "ping"}))
            
            # 接收响应
            response = await websocket.recv()
            print(f"收到: {response}")
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")

asyncio.run(connect_websocket())
```

### 3. **JavaScript/Node.js 客户端示例**

```javascript
// Node.js
const WebSocket = require('ws');

function connectWebSocket() {
  // ✅ 正确的地址
  const uri = 'ws://localhost:8000/ws/host-service/ws/agent/agent-123';
  
  const token = 'your-jwt-token-here';
  
  const ws = new WebSocket(uri, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  ws.on('open', () => {
    console.log('✅ WebSocket 连接成功');
    ws.send(JSON.stringify({ type: 'ping' }));
  });
  
  ws.on('message', (data) => {
    console.log('收到:', data);
  });
  
  ws.on('error', (error) => {
    console.log('❌ 错误:', error);
  });
}

connectWebSocket();
```

### 4. **浏览器 JavaScript 示例**

```javascript
// 注意: 浏览器 WebSocket API 不支持自定义 headers
// 需要使用查询参数传递 token

const token = 'your-jwt-token-here';
const agentId = 'agent-123';

// ✅ 通过查询参数传递 token
const ws = new WebSocket(
  `ws://localhost:8000/ws/host-service/ws/agent/${agentId}?token=${token}`
);

ws.onopen = () => {
  console.log('✅ WebSocket 连接成功');
  ws.send(JSON.stringify({ type: 'ping' }));
};

ws.onmessage = (event) => {
  console.log('收到:', event.data);
};

ws.onerror = (error) => {
  console.log('❌ 错误:', error);
};

ws.onclose = () => {
  console.log('连接已关闭');
};
```

## 🔐 认证方式

当前网关的 WebSocket 代理**不对路径进行认证检查**，但有两种方式提供 token:

### 方式 1: 请求头 (推荐，在 Node.js/Python 中)

```python
headers = {"Authorization": "Bearer <token>"}
```

```javascript
headers: { "Authorization": `Bearer ${token}` }
```

### 方式 2: 查询参数 (浏览器)

```
ws://localhost:8000/ws/host-service/ws/agent/agent-123?token=<token>
```

## 📋 验证清单

- [ ] 使用正确的地址格式: `/ws/{service_name}/{path:path}`
- [ ] 确保 `service_name` 是正确的服务名称 (如 `host-service`)
- [ ] 确保 `path` 是后端服务上的正确路径 (如 `ws/agent/agent-123`)
- [ ] 如果需要认证，使用请求头或查询参数提供 token
- [ ] 在网关和后端服务日志中验证连接是否建立

## 🧪 测试步骤

### 1. 查看网关日志

```bash
docker-compose logs -f gateway-service | grep -i websocket
```

预期看到:
```
INFO ... WebSocket 连接已建立: host-service/ws/agent/agent-123
```

### 2. 查看 Host Service 日志

```bash
docker-compose logs -f host-service | grep -i websocket
```

预期看到:
```
INFO ... 客户端已连接: agent-123
```

### 3. 运行 Python 测试脚本

```bash
python test_websocket_correct.py
```

### 4. 检查网关路由

```bash
curl -X GET http://localhost:8000/openapi.json | grep -A 10 'websocket_proxy'
```

应该看到:
```json
{
  "path": "/ws/{service_name}/{path:path}",
  "methods": ["GET"],
  "operationId": "websocket_proxy"
}
```

## 🚨 常见错误

### 错误 1: 使用了错误的路径

```
❌ 错误: ws://localhost:8000/ws/agent/agent-123
✅ 正确: ws://localhost:8000/ws/host-service/ws/agent/agent-123
```

### 错误 2: Authorization 头格式错误

```
❌ 错误: Authorization: <token>
❌ 错误: Authorization: Token <token>
✅ 正确: Authorization: Bearer <token>
```

### 错误 3: token 无效或过期

```
确保 token 是从登录端点获取的有效 JWT
POST /api/v1/auth/admin/login 或 /api/v1/auth/device/login
```

## 📈 架构图

```
┌─────────────────────────────────────────────────────────┐
│  客户端 WebSocket 请求                                  │
│  GET /ws/host-service/ws/agent/agent-123                │
│  Authorization: Bearer <token>                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Gateway Service (port 8000)                            │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ AuthMiddleware                                     │ │
│  │ - 检查路径 /ws/host-service/ws/agent/agent-123   │ │
│  │ - 提取 token: Authorization: Bearer <token>      │ │
│  │ - 验证 token (可选，如果路径需要认证)            │ │
│  └────────────────────────────────────────────────────┘ │
│                     │                                    │
│                     ▼                                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │ WebSocket 代理端点                                 │ │
│  │ @router.websocket("/ws/{service_name}/{path:path}"│ │
│  │ - service_name: "host-service"                    │ │
│  │ - path: "ws/agent/agent-123"                      │ │
│  └────────────────────────────────────────────────────┘ │
│                     │                                    │
│                     ├─→ 连接到后端: ws://host-service:8003/api/v1/ws/agent/agent-123
│                     │                                    │
└─────────────────────┼────────────────────────────────────┘
                      │
                      ▼
            ┌──────────────────────┐
            │  Host Service        │
            │  (port 8003)         │
            │                      │
            │  WebSocket Handler   │
            │  /ws/agent/agent-123 │
            └──────────────────────┘
```

## 🎯 结论

你的问题不是认证问题，而是 **路由地址错误**。
- **你用的地址**: `/ws/agent/agent-123` (不存在的路由)
- **正确地址**: `/ws/host-service/ws/agent/agent-123` (正确的代理路由)

使用正确的地址后，token 认证就会正常进行。

