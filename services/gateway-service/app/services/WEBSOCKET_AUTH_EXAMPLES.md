# WebSocket 认证完整指南

## 🎯 认证方式概览

WebSocket 认证支持两种方式：

### 1️⃣ 查询参数方式 (Query Parameter)

```text
ws://localhost:8000/ws/agent/agent-123?token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 2️⃣ Authorization 请求头方式 (Header)

```text
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## 📋 服务器端实现

### 1. 基础 WebSocket 端点（无认证）

```python
# services/host-service/app/api/v1/endpoints/websocket.py
import os
import sys
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.websocket("/ws/public/{client_id}")
async def websocket_public_endpoint(websocket: WebSocket, client_id: str):
    """公开 WebSocket 端点 - 无认证要求"""
    await websocket.accept()
    
    logger.info(f"客户端已连接: {client_id}")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            logger.info(f"收到消息: {client_id} - {data}")
            
            # 发送回复
            await websocket.send_text(f"Echo: {data}")
            
    except WebSocketDisconnect:
        logger.info(f"客户端已断开连接: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket 异常: {client_id} - {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
```

### 2. 使用认证的 WebSocket 端点

```python
# services/host-service/app/api/v1/endpoints/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.middleware.websocket_auth_middleware import WebSocketAuthMiddleware
from shared.common.security import JWTManager

# 初始化认证中间件
jwt_manager = JWTManager()
auth_middleware = WebSocketAuthMiddleware(jwt_manager)

router = APIRouter()

@router.websocket("/ws/private/{agent_id}")
async def websocket_private_endpoint(websocket: WebSocket, agent_id: str):
    """私有 WebSocket 端点 - 需要认证"""
    await websocket.accept()
    
    try:
        # 1. 认证连接
        user_info = await auth_middleware.authenticate(
            websocket,
            require_auth=True  # 必须提供有效令牌
        )
        
        if not user_info:
            await websocket.close(code=1008, reason="认证失败")
            return
        
        logger.info(
            f"Agent 已认证连接: {agent_id}",
            extra={"user_id": user_info.get("user_id")}
        )
        
        # 2. 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": f"欢迎 {user_info.get('username')}",
            "user_id": user_info.get("user_id")
        })
        
        # 3. 消息处理循环
        while True:
            data = await websocket.receive_text()
            logger.info(f"收到消息: {agent_id} - {data}")
            
            # 发送回复
            await websocket.send_json({
                "type": "message",
                "data": f"Echo: {data}",
                "sender": user_info.get("user_id")
            })
        
    except WebSocketDisconnect:
        logger.info(f"Agent 已断开连接: {agent_id}")
    except Exception as e:
        logger.error(f"WebSocket 异常: {agent_id} - {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

@router.websocket("/ws/admin/{agent_id}")
async def websocket_admin_endpoint(websocket: WebSocket, agent_id: str):
    """管理员 WebSocket 端点 - 需要认证和管理员权限"""
    await websocket.accept()
    
    try:
        # 1. 认证连接
        user_info = await auth_middleware.authenticate(
            websocket,
            require_auth=True
        )
        
        if not user_info:
            await websocket.close(code=1008, reason="认证失败")
            return
        
        # 2. 检查权限
        try:
            await auth_middleware.check_permissions(
                user_info,
                required_permissions=["admin:websocket:connect"]
            )
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "code": "PERMISSION_DENIED",
                "message": str(e)
            })
            await websocket.close(code=1008, reason="权限不足")
            return
        
        logger.info(f"管理员已连接: {agent_id} ({user_info.get('user_id')})")
        
        # 3. 处理管理员消息
        while True:
            data = await websocket.receive_json()
            
            # 验证管理员操作
            operation = data.get("operation")
            logger.info(f"管理员操作: {operation}")
            
            # 返回结果
            await websocket.send_json({
                "type": "result",
                "operation": operation,
                "status": "success"
            })
        
    except WebSocketDisconnect:
        logger.info(f"管理员已断开连接: {agent_id}")
    except Exception as e:
        logger.error(f"WebSocket 异常: {agent_id} - {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
```

### 3. 可选认证的 WebSocket 端点

```python
@router.websocket("/ws/hybrid/{agent_id}")
async def websocket_hybrid_endpoint(websocket: WebSocket, agent_id: str):
    """混合 WebSocket 端点 - 认证可选"""
    await websocket.accept()
    
    try:
        # 认证（可选）
        user_info = await auth_middleware.authenticate(
            websocket,
            require_auth=False  # 认证可选
        )
        
        if user_info:
            logger.info(f"已认证用户连接: {agent_id} ({user_info.get('user_id')})")
            user_context = {
                "authenticated": True,
                "user_id": user_info.get("user_id"),
                "permissions": user_info.get("permissions", [])
            }
        else:
            logger.info(f"匿名用户连接: {agent_id}")
            user_context = {
                "authenticated": False,
                "user_id": None,
                "permissions": ["public:read"]
            }
        
        # 发送连接信息
        await websocket.send_json({
            "type": "connected",
            "authentication_status": "authenticated" if user_info else "anonymous",
            "permissions": user_context["permissions"]
        })
        
        # 消息处理
        while True:
            data = await websocket.receive_json()
            
            # 基于权限处理不同操作
            operation = data.get("operation")
            
            if operation == "write" and not user_info:
                await websocket.send_json({
                    "type": "error",
                    "code": "PERMISSION_DENIED",
                    "message": "只有认证用户可以执行写操作"
                })
                continue
            
            # 处理操作
            await websocket.send_json({
                "type": "result",
                "operation": operation,
                "status": "success"
            })
        
    except Exception as e:
        logger.error(f"WebSocket 异常: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
```

---

## 🔌 客户端实现

### 1. Python 客户端示例

#### 方式 1: 使用查询参数

```python
# client_example.py
import asyncio
import websockets
import json

async def websocket_client_with_query_param():
    """使用查询参数进行认证的客户端"""
    
    # 假设已从认证服务获得 JWT token
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    
    # 构建 WebSocket URL（包含 token）
    uri = f"ws://localhost:8000/ws/private/agent-123?token={token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[连接成功]")
            
            # 接收欢迎消息
            welcome = await websocket.recv()
            print(f"服务器: {welcome}")
            
            # 发送消息
            await websocket.send("Hello from client!")
            response = await websocket.recv()
            print(f"响应: {response}")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"[连接失败] {e}")

asyncio.run(websocket_client_with_query_param())
```

#### 方式 2: 使用 Authorization 请求头

```python
# client_example_with_header.py
import asyncio
import websockets
import json

async def websocket_client_with_header():
    """使用 Authorization 请求头进行认证的客户端"""
    
    # 获取 JWT token
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    
    uri = "ws://localhost:8000/ws/private/agent-123"
    
    try:
        # 使用自定义请求头
        extra_headers = {
            "Authorization": f"Bearer {token}"
        }
        
        async with websockets.connect(uri, extra_headers=extra_headers) as websocket:
            print("[连接成功]")
            
            # 接收欢迎消息
            welcome = await websocket.recv()
            print(f"服务器: {welcome}")
            
            # 发送消息
            await websocket.send("Hello from client!")
            response = await websocket.recv()
            print(f"响应: {response}")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"[连接失败] {e}")

asyncio.run(websocket_client_with_header())
```

### 2. JavaScript/TypeScript 客户端示例

#### 方式 1: 使用查询参数

```javascript
// client.js - 使用查询参数
class WebSocketClient {
  constructor(serverUrl, token) {
    // 构建包含 token 的 URL
    const url = new URL(serverUrl);
    url.searchParams.append('token', token);
    this.url = url.toString();
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('[✓] WebSocket 连接成功');
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          console.log('[←] 收到消息:', JSON.parse(event.data));
        };
        
        this.ws.onerror = (error) => {
          console.error('[✗] WebSocket 错误:', error);
          reject(error);
        };
        
        this.ws.onclose = () => {
          console.log('[✓] WebSocket 连接已关闭');
        };
        
      } catch (error) {
        reject(error);
      }
    });
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      console.log('[→] 发送消息:', message);
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
async function main() {
  const token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...';
  const client = new WebSocketClient('ws://localhost:8000/ws/private/agent-123', token);
  
  try {
    await client.connect();
    
    // 发送消息
    client.send({
      type: 'message',
      data: 'Hello from JavaScript client!'
    });
    
    // 3 秒后关闭连接
    setTimeout(() => client.close(), 3000);
    
  } catch (error) {
    console.error('连接失败:', error);
  }
}

main();
```

#### 方式 2: 使用 Authorization 请求头

```javascript
// client_with_header.js - 使用请求头
class WebSocketClientWithHeader {
  constructor(serverUrl, token) {
    this.url = serverUrl;
    this.token = token;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        // 创建自定义握手
        this.ws = new WebSocket(this.url);
        
        // 注意：WebSocket API 不支持直接设置请求头
        // 但可以使用子协议或在连接前处理
        
        this.ws.onopen = () => {
          // 连接后发送认证消息
          this.ws.send(JSON.stringify({
            type: 'authenticate',
            token: this.token
          }));
          console.log('[✓] WebSocket 连接成功，已发送认证令牌');
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          // 处理认证响应
          if (data.type === 'authenticated') {
            console.log('[✓] 认证成功');
          }
          
          console.log('[←] 收到消息:', data);
        };
        
        this.ws.onerror = (error) => {
          console.error('[✗] WebSocket 错误:', error);
          reject(error);
        };
        
      } catch (error) {
        reject(error);
      }
    });
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      console.log('[→] 发送消息:', message);
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
async function main() {
  const token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...';
  const client = new WebSocketClientWithHeader(
    'ws://localhost:8000/ws/private/agent-123',
    token
  );
  
  try {
    await client.connect();
    
    // 发送消息
    client.send({
      type: 'message',
      data: 'Hello from JavaScript client!'
    });
    
  } catch (error) {
    console.error('连接失败:', error);
  }
}

main();
```

### 3. React 客户端示例

```javascript
// useWebSocket.tsx - React Hook
import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketConfig {
  url: string;
  token: string;
  onMessage: (data: any) => void;
  onError?: (error: Error) => void;
}

export function useWebSocket(config: WebSocketConfig) {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        // 方式 1: 使用查询参数
        const url = new URL(config.url);
        url.searchParams.append('token', config.token);
        
        ws.current = new WebSocket(url.toString());

        ws.current.onopen = () => {
          console.log('[✓] WebSocket 连接成功');
          setConnected(true);
        };

        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            config.onMessage(data);
          } catch (error) {
            console.error('消息解析失败:', error);
          }
        };

        ws.current.onerror = (error) => {
          console.error('[✗] WebSocket 错误:', error);
          config.onError?.(new Error('WebSocket connection error'));
          setConnected(false);
        };

        ws.current.onclose = () => {
          console.log('[✓] WebSocket 连接已关闭');
          setConnected(false);
          
          // 重新连接（可选）
          setTimeout(connectWebSocket, 3000);
        };

      } catch (error) {
        console.error('连接失败:', error);
        config.onError?.(error as Error);
      }
    };

    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [config, config.token]);

  const send = useCallback((data: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  return { connected, send };
}

// 使用示例
function AgentDashboard() {
  const token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...';
  
  const { connected, send } = useWebSocket({
    url: 'ws://localhost:8000/ws/private/agent-123',
    token,
    onMessage: (data) => {
      console.log('收到消息:', data);
    },
    onError: (error) => {
      console.error('连接错误:', error);
    },
  });

  return (
    <div>
      <p>连接状态: {connected ? '✓ 已连接' : '✗ 未连接'}</p>
      <button onClick={() => send({ type: 'message', data: 'Hello' })}>
        发送消息
      </button>
    </div>
  );
}
```

---

## 🔐 获取 JWT Token 流程

### 1. 从认证服务获取 Token

```python
# 获取 token 的方式
import requests

def get_auth_token(username: str, ***REMOVED***word: str) -> str:
    """从认证服务获取 JWT token"""
    
    response = requests.post(
        "http://localhost:8001/api/v1/auth/login",
        json={
            "username": username,
            "***REMOVED***word": ***REMOVED***word
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("access_token")
    else:
        raise Exception(f"认证失败: {response.status_code}")

# 使用
token = get_auth_token("admin", "***REMOVED***")
print(f"获得 Token: {token}")
```

### 2. Token 验证流程

```text
1. 客户端获取 Token（通过 HTTP 认证接口）
   ↓
2. 客户端初始化 WebSocket 连接（附加 Token）
   ↓
3. 服务器接收连接请求
   ↓
4. 服务器提取 Token（查询参数或请求头）
   ↓
5. 服务器验证 Token（通过 JWTManager）
   ↓
6. 验证成功 ✓ / 验证失败 ✗
```

---

## 📊 认证流程图

```text
┌─────────────┐
│   客户端    │
└──────┬──────┘
       │
       │ 1. 请求认证 (HTTP)
       ↓
┌──────────────────┐
│  Auth Service    │ 
│  (8001 port)     │
└────────┬─────────┘
         │
         │ 2. 返回 JWT Token
         ↓
    ┌────────────┐
    │ Token:xxxx │
    └─────┬──────┘
          │
          │ 3. WebSocket 连接 + Token
          ↓
┌──────────────────────┐
│  Gateway Service     │
│ (WebSocket Handler)  │
└────────┬─────────────┘
         │
         │ 4. 验证 Token
         │    (JWTManager)
         ↓
    ┌─────────────┐
    │ 验证成功?   │
    └─────┬───┬───┘
          │   │
         ✓    ✗
         │    │
         ↓    ↓
      连接   关闭连接
      成功   (1008)
```

---

## ✅ 认证检查清单

### 服务器端

- [ ] 创建 `WebSocketAuthMiddleware` 实例
- [ ] 配置 JWT 管理器
- [ ] 在 WebSocket 端点调用 `authenticate()`
- [ ] 根据需要检查权限 `check_permissions()`
- [ ] 处理认证异常

### 客户端

- [ ] 从认证服务获取 JWT token
- [ ] 构建包含 token 的 WebSocket URL
- [ ] 建立 WebSocket 连接
- [ ] 处理连接成功/失败
- [ ] 实现自动重连机制

### Token 管理

- [ ] Token 存储安全性
- [ ] Token 过期处理
- [ ] Token 刷新机制
- [ ] Token 撤销处理

---

## 🚀 生产环境建议

### 安全最佳实践

1. **使用 HTTPS/WSS**

```javascript
// 使用 wss:// 而不是 ws://（加密）
const client = new WebSocket('wss://api.example.com/ws/private/agent-123?token=...');
```

2. **Token 过期和刷新**

```python
# 实现 token 刷新机制
@router.websocket("/ws/private/{agent_id}")
async def websocket_with_refresh(websocket: WebSocket, agent_id: str):
    # 检查 token 过期
    user_info = await auth_middleware.authenticate(websocket, require_auth=True)
    
    # 定期刷新 token
    # ...
```

3. **连接超时**

```python
# 设置心跳检测防止连接超时
features_manager.heartbeat_manager.register_connection(
    agent_id,
    send_heartbeat,
    interval=30  # 每 30 秒发送一次心跳
)
```

---

现在您已经了解了完整的 WebSocket 认证实现方式！ 🎉
