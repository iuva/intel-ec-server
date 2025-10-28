# 网关 WebSocket 支持使用指南

## 🎯 概述

网关现已支持 WebSocket 连接转发，允许客户端通过网关访问后端微服务的 WebSocket 端点。

## 🔌 WebSocket 路由

### 网关 WebSocket 端点格式

```
ws://gateway-host:8000/ws/{service_name}/{path}
```

### 参数说明

- `gateway-host`: 网关服务器地址（localhost、172.20.0.100 等）
- `service_name`: 后端服务名称（auth、admin、host）
- `path`: 后端服务的 WebSocket 路径

### 示例

```python
# 连接到 host 服务的 WebSocket
uri = "ws://localhost:8000/ws/host/api/v1/ws/agent/agent-001"

async with websockets.connect(uri) as websocket:
    await websocket.send_json({"type": "ping"})
    response = await websocket.recv()
```

## 🚀 快速开始

### 方法 1：直接连接（开发测试）

```python
import websockets
import json

async def connect_directly():
    """直接连接 host-service WebSocket（跳过网关）"""
    uri = "ws://localhost:8003/api/v1/ws/agent/agent-001"
    
    async with websockets.connect(uri) as websocket:
        print(f"连接已建立: {uri}")
        
        # 发送消息
        await websocket.send_json({"type": "ping", "data": "hello"})
        
        # 接收消息
        response = await websocket.recv()
        print(f"收到响应: {response}")
```

### 方法 2：通过网关连接（推荐用于生产）

```python
import websockets
import json

async def connect_via_gateway():
    """通过网关转发连接 host-service WebSocket"""
    uri = "ws://localhost:8000/ws/host/api/v1/ws/agent/agent-001"
    
    async with websockets.connect(uri) as websocket:
        print(f"通过网关连接: {uri}")
        
        # 发送消息
        await websocket.send_json({"type": "ping", "data": "hello"})
        
        # 接收消息
        response = await websocket.recv()
        print(f"收到响应: {response}")
```

## 📋 环境配置

### Docker Compose 环境

```bash
# 启动网关和 host-service
docker-compose up -d gateway-service host-service

# 测试网关 WebSocket 连接
python test_gateway_websocket.py
```

### 本地开发环境

```bash
# 终端 1: 启动网关
cd services/gateway-service
python -m app.main

# 终端 2: 启动 host-service
cd services/host-service
python -m app.main

# 终端 3: 运行测试
cd services/host-service/tests
pytest test_websocket_connection.py::TestWebSocketConnection::test_successful_connection -v
```

## 🔐 认证和授权

### WebSocket 认证方式

当前网关 WebSocket 支持两种模式：

#### 模式 1：公开 WebSocket（无认证）

```python
# 直接连接，无需认证令牌
uri = "ws://localhost:8000/ws/host/api/v1/ws/agent/agent-001"
async with websockets.connect(uri) as ws:
    ***REMOVED***
```

#### 模式 2：使用认证令牌（需要配置中间件）

```python
# 通过查询参数传递认证令牌
uri = "ws://localhost:8000/ws/host/api/v1/ws/agent/agent-001?token=<jwt_token>"
async with websockets.connect(uri) as ws:
    ***REMOVED***
```

**注意**：认证功能需要在网关的 WebSocket 端点添加认证中间件支持。

## 🔄 消息格式

### 客户端到服务器

```json
{
  "type": "message_type",
  "data": {
    "key": "value"
  }
}
```

### 服务器到客户端

```json
{
  "type": "response_type",
  "data": {
    "key": "value"
  }
}
```

## 📊 网关 WebSocket 架构

```
┌──────────────────┐
│   WebSocket      │
│   客户端         │
└────────┬─────────┘
         │ ws://localhost:8000/ws/host/...
         │
    ┌────▼─────────────────────────┐
    │   网关 WebSocket 路由         │
    │  /ws/{service}/{path}        │
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────────────┐
    │   代理服务 (ProxyService)             │
    │  forward_websocket()                  │
    └────┬───────────────────────────────────┘
         │
    ┌────▼──────────────────┐
    │   双向消息转发        │
    │  (客户端 <-> 服务器)  │
    └────┬───────────────────┘
         │ ws://host-service:8003/api/v1/ws/agent/...
         │
    ┌────▼──────────────┐
    │  后端 WebSocket   │
    │  (host-service)   │
    └───────────────────┘
```

## 🛠️ 故障排查

### 问题 1：连接超时

**症状**：`websockets.exceptions.InvalidURI: Expected "http://" or "https://" in URI`

**原因**：URL 协议不正确

**解决**：
```python
# ❌ 错误
uri = "http://localhost:8000/ws/host/..."

# ✅ 正确
uri = "ws://localhost:8000/ws/host/..."
```

### 问题 2：连接被拒绝

**症状**：`ConnectionRefusedError: [Errno 111] Connection refused`

**原因**：网关或后端服务未运行

**解决**：
```bash
# 检查网关服务
curl http://localhost:8000/health

# 检查 host-service
curl http://localhost:8003/health

# 查看日志
docker-compose logs gateway-service
docker-compose logs host-service
```

### 问题 3：消息无法转发

**症状**：发送消息后无响应，或收到错误消息

**原因**：后端服务异常或路径错误

**解决**：
```python
# 查看网关日志，找到转发 URL
# 验证后端服务的 WebSocket 端点
curl -i http://localhost:8003/api/v1/ws/agent/agent-001

# 直接连接后端 WebSocket 测试
uri = "ws://localhost:8003/api/v1/ws/agent/agent-001"
```

### 问题 4：连接立即关闭

**症状**：WebSocket 连接建立后立即断开

**原因**：可能是后端服务错误或消息格式不正确

**解决**：
```bash
# 查看网关日志
docker-compose logs -f gateway-service

# 查看 host-service 日志
docker-compose logs -f host-service

# 查看错误消息
# 网关会尝试发送错误 JSON 响应
```

## 💻 完整示例

### 测试脚本

```python
# test_gateway_websocket.py
import asyncio
import websockets
import json
from datetime import datetime

async def test_gateway_websocket():
    """测试通过网关的 WebSocket 连接"""
    
    # 配置
    gateway_url = "ws://localhost:8000/ws/host/api/v1/ws/agent/test-agent-001"
    direct_url = "ws://localhost:8003/api/v1/ws/agent/test-agent-001"
    
    print("=" * 60)
    print("网关 WebSocket 转发测试")
    print("=" * 60)
    
    # 测试 1：通过网关连接
    print("\n[测试 1] 通过网关连接...")
    try:
        async with websockets.connect(gateway_url, ping_interval=None) as ws:
            print(f"✅ 连接成功: {gateway_url}")
            
            # 发送测试消息
            test_msg = {
                "type": "test",
                "timestamp": datetime.now().isoformat(),
                "data": "gateway_test"
            }
            await ws.send(json.dumps(test_msg))
            print(f"✅ 消息已发送: {test_msg}")
            
            # 接收响应
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"✅ 收到响应: {response}")
            except asyncio.TimeoutError:
                print("⚠️  未收到响应（超时），但连接正常")
    
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
    
    # 测试 2：直接连接
    print("\n[测试 2] 直接连接 host-service...")
    try:
        async with websockets.connect(direct_url, ping_interval=None) as ws:
            print(f"✅ 连接成功: {direct_url}")
            
            test_msg = {
                "type": "test",
                "timestamp": datetime.now().isoformat(),
                "data": "direct_test"
            }
            await ws.send(json.dumps(test_msg))
            print(f"✅ 消息已发送: {test_msg}")
            
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"✅ 收到响应: {response}")
            except asyncio.TimeoutError:
                print("⚠️  未收到响应（超时），但连接正常")
    
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_gateway_websocket())
```

### 运行测试

```bash
# 安装依赖
pip install websockets

# 确保网关和 host-service 正在运行
docker-compose up -d gateway-service host-service

# 运行测试
python test_gateway_websocket.py
```

## 📈 性能建议

### 网关 WebSocket 优化

1. **连接管理**
   - 及时关闭未使用的连接
   - 使用连接池管理多个连接
   - 设置合理的超时时间

2. **消息处理**
   - 避免过大的消息（>1MB）
   - 使用二进制格式而非 JSON 以提高性能
   - 实现消息压缩

3. **并发处理**
   - 网关可以处理多个并发 WebSocket 连接
   - 每个连接独立转发到后端服务
   - 共享 HTTP 连接池以提高效率

## 📝 更新历史

- **2025-10-25**: 网关 WebSocket 支持完整实现
  - ✅ 添加 WebSocket 路由处理器
  - ✅ 实现双向消息转发
  - ✅ 添加错误处理和日志
  - ✅ 编写使用指南和故障排查

## 🔗 相关文件

- [services/gateway-service/app/api/v1/endpoints/proxy.py](mdc:services/gateway-service/app/api/v1/endpoints/proxy.py) - WebSocket 路由处理器
- [services/gateway-service/app/services/proxy_service.py](mdc:services/gateway-service/app/services/proxy_service.py) - WebSocket 转发实现
- [services/host-service/tests/conftest.py](mdc:services/host-service/tests/conftest.py) - WebSocket 连接配置
- [services/host-service/tests/README.md](mdc:services/host-service/tests/README.md) - WebSocket 测试框架
