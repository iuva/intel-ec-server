# WebSocket 连接 403 Forbidden 问题解决方案

## 🐛 问题分析

### 症状
```
INFO:     ('192.168.65.1', 46494) - "WebSocket /ws/agent/agent-123" 403
INFO:     connection rejected (403 Forbidden)
INFO:     connection closed
```

### 根本原因
**Gateway Service 的 `AuthMiddleware` 认证中间件拦截了所有 WebSocket 请求，包括未在公开路径白名单中的 `/ws/` 路由**。

在 FastAPI 中，WebSocket 连接首先会通过 HTTP 握手，而这个握手过程必须通过认证中间件。如果认证中间件拒绝了这个握手请求，就会返回 403 Forbidden。

## ✅ 解决方案

### 修复内容

#### 1. **添加 WebSocket 路由到公开路径白名单**

**文件**: `services/gateway-service/app/middleware/auth_middleware.py`

在 `AuthMiddleware.__init__` 中的 `public_paths` 添加 WebSocket 路由前缀：

```python
# 公开路径白名单（不需要认证）
self.public_paths = {
    # ... 其他路径 ...
    # ✅ WebSocket 代理路由（公开访问）
    "/ws/",  # WebSocket 路由前缀
}
```

#### 2. **启用 WebSocket 路径的前缀匹配**

同一文件的 `_is_public_path` 方法：

```python
# 检查路径前缀匹配（仅用于特定的文档路径和 WebSocket）
# 只对以下路径进行前缀匹配：/docs, /redoc, /openapi.json, /ws/
prefix_match_paths = {"/docs", "/redoc", "/openapi.json", "/ws/"}
```

## 🧪 测试 WebSocket 连接

### 方式 1：使用 Python 测试

```python
import asyncio
import websockets

async def test_websocket():
    """测试 WebSocket 连接"""
    try:
        # 不带认证的公开连接（可选）
        uri = "ws://localhost:8000/ws/host-service/ws/agent/agent-123"
        
        async with websockets.connect(uri) as ws:
            print("✅ WebSocket 连接成功")
            
            # 发送测试消息
            await ws.send('{"type": "ping"}')
            
            # 接收响应
            response = await ws.recv()
            print(f"收到消息: {response}")
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")

asyncio.run(test_websocket())
```

### 方式 2：使用 JavaScript/Node.js 测试

```javascript
// Node.js 示例
const WebSocket = require('ws');

function testWebSocket() {
  const ws = new WebSocket('ws://localhost:8000/ws/host-service/ws/agent/agent-123');
  
  ws.onopen = () => {
    console.log('✅ WebSocket 连接成功');
    ws.send(JSON.stringify({ type: 'ping' }));
  };
  
  ws.onmessage = (event) => {
    console.log('收到消息:', event.data);
  };
  
  ws.onerror = (error) => {
    console.log('❌ 连接错误:', error);
  };
  
  ws.onclose = () => {
    console.log('连接已关闭');
  };
}

testWebSocket();
```

### 方式 3：使用 curl 模拟握手

```bash
# curl 不原生支持 WebSocket，但可以查看握手响应
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
  -H "Sec-WebSocket-Version: 13" \
  http://localhost:8000/ws/host-service/ws/agent/agent-123

# 预期响应应该是 101 Switching Protocols（或 200 如果你有认证检查）
# 而不是 403 Forbidden
```

## 📋 验证清单

运行以下检查确保修复有效：

```bash
# 1. 检查认证中间件配置
grep -n "/ws/" services/gateway-service/app/middleware/auth_middleware.py

# 2. 检查代码质量
cd /Users/chiyeming/KiroProjects/intel_ec_ms
ruff check services/gateway-service/app/middleware/auth_middleware.py

# 3. 启动服务并测试
docker-compose up -d
sleep 5

# 4. 执行 Python 测试
python test_websocket.py

# 5. 查看日志验证
docker-compose logs gateway-service | grep -i websocket
docker-compose logs host-service | grep -i websocket
```

## 🔗 相关文档

- `services/gateway-service/app/middleware/auth_middleware.py` - 认证中间件实现
- `services/gateway-service/app/api/v1/endpoints/proxy.py` - WebSocket 代理端点
- `services/host-service/app/api/v1/endpoints/websocket.py` - Host 服务 WebSocket 端点

## 📊 完整的 WebSocket 连接流程

```
┌─────────────────────────────────────────────────────────────┐
│  客户端                                                      │
└─────────────────────────────────────────────────────────────┘
             │
             │ 1. WebSocket 握手请求
             │ GET /ws/host-service/ws/agent/agent-123
             │ Upgrade: websocket
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Gateway Service (端口 8000)                                 │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  AuthMiddleware (验证中间件)                              │ │
│  │  ✅ 检查路径: /ws/host-service/ws/agent/agent-123       │ │
│  │  ✅ 匹配前缀: /ws/                                       │ │
│  │  ✅ 允许通过 (公开路径)                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│             │                                                  │
│             ▼                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  WebSocket Proxy 端点                                    │ │
│  │  @router.websocket("/ws/{service_name}/{path:path}")   │ │
│  │  - 建立客户端连接: accept()                             │ │
│  │  - 连接到后端服务                                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
             │
             │ 2. 转发连接
             │ ws://host-service:8003/ws/agent/agent-123
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Host Service (端口 8003)                                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  WebSocket 端点                                          │ │
│  │  @router.websocket("/ws/agent/{agent_id}")             │ │
│  │  - 接收连接                                              │ │
│  │  - 处理消息                                              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 最佳实践

### 1. **认证可选的 WebSocket**

如果需要对 WebSocket 进行认证（但当前是公开的），可以在连接建立后手动验证：

```python
from app.middleware.websocket_auth_middleware import WebSocketAuthMiddleware
from shared.common.security import JWTManager

@router.websocket("/ws/private/{service_name}/{path:path}")
async def websocket_private_proxy(websocket, service_name: str, path: str):
    # 可选：验证令牌（认证中间件已跳过）
    jwt_manager = JWTManager()
    auth = WebSocketAuthMiddleware(jwt_manager)
    
    user_info = await auth.authenticate(websocket, require_auth=False)
    
    await websocket.accept()
    # ... 处理连接
```

### 2. **监控 WebSocket 连接**

在网关添加连接日志：

```python
logger.info(
    "WebSocket 连接建立",
    extra={
        "service": service_name,
        "path": path,
        "client_ip": websocket.client.host,
        "connection_type": "websocket"
    }
)
```

### 3. **处理连接失败**

添加更详细的错误信息：

```python
if websocket.client_state.name == "DISCONNECTED":
    logger.warning(
        "WebSocket 已断开连接",
        extra={
            "service": service_name,
            "path": path,
            "reason": "client_disconnect"
        }
    )
```

## 📈 故障排查

### 仍然收到 403 错误？

1. **重启 Gateway Service**
   ```bash
   docker-compose restart gateway-service
   ```

2. **检查认证中间件日志**
   ```bash
   docker-compose logs -f gateway-service | grep "WebSocket\|公开路径"
   ```

3. **验证中间件配置**
   ```bash
   python -c "
   from app.middleware.auth_middleware import AuthMiddleware
   class MockApp:
       ***REMOVED***
   
   middleware = AuthMiddleware(MockApp())
   print('公开路径:', middleware.public_paths)
   print('是否为公开路径 /ws/:', middleware._is_public_path('/ws/'))
   print('是否为公开路径 /ws/host-service/ws/agent/123:', middleware._is_public_path('/ws/host-service/ws/agent/123'))
   "
   ```

4. **检查网关日志中的具体错误**
   ```bash
   docker-compose logs gateway-service | grep "403\|Forbidden\|缺少认证"
   ```

## 成功标志

修复完成后，您应该看到：

```
✅ WebSocket 握手成功（HTTP 101 Switching Protocols）
✅ 连接保持打开状态
✅ 能够发送和接收消息
✅ 日志显示 "公开路径，跳过认证检查"
```

---

**修复日期**: 2025-10-25
**修改文件**: `services/gateway-service/app/middleware/auth_middleware.py`
**影响范围**: 所有通过网关的 WebSocket 连接
