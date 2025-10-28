# WebSocket 高级特性使用指南

## 🎯 高级特性概览

网关 WebSocket 支持以下高级特性，为企业级应用提供完整的功能：

### 📋 特性列表

| 特性 | 说明 | 用途 |
|------|------|------|
| **认证中间件** | JWT 令牌验证和权限检查 | 保护 WebSocket 连接安全 |
| **连接池** | WebSocket 连接复用和缓存 | 提升性能，减少延迟 |
| **心跳检测** | 定期 ping/pong 消息 | 检测连接活跃性 |
| **速率限制** | 限制消息发送频率 | 防止洪泛攻击 |
| **消息压缩** | Gzip 压缩支持 | 减少带宽占用 |
| **性能监控** | 完整的统计指标收集 | 监控和优化 WebSocket 服务 |

## 🔐 认证中间件

### 概述

提供 JWT 令牌验证和权限检查功能，支持多种令牌提供方式。

### 使用方式

#### 方式 1：强制认证

```python
from fastapi import WebSocket, WebSocketException
from services.gateway_service.app.middleware.websocket_auth_middleware import WebSocketAuthMiddleware
from shared.common.security import JWTManager

# 初始化认证中间件
jwt_manager = JWTManager()
auth_middleware = WebSocketAuthMiddleware(jwt_manager)

@app.websocket("/ws/authenticated/{agent_id}")
async def websocket_authenticated(websocket: WebSocket, agent_id: str):
    # 强制认证（require_auth=True）
    user_info = await auth_middleware.authenticate(websocket, require_auth=True)
    if not user_info:
        await websocket.close(code=1008, reason="认证失败")
        return
    
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # 处理消息
    finally:
        await websocket.close()
```

#### 方式 2：可选认证

```python
@app.websocket("/ws/optional/{agent_id}")
async def websocket_optional(websocket: WebSocket, agent_id: str):
    # 可选认证（require_auth=False）
    user_info = await auth_middleware.authenticate(websocket, require_auth=False)
    
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if user_info:
                # 认证用户
                ***REMOVED***
            else:
                # 匿名用户
                ***REMOVED***
    finally:
        await websocket.close()
```

#### 方式 3：令牌提供方式

```python
# 方式 A：查询参数
# ws://localhost:8000/ws/host?token=<jwt_token>

# 方式 B：Authorization 请求头
# Authorization: Bearer <jwt_token>
```

### 权限检查

```python
@app.websocket("/ws/admin/{agent_id}")
async def websocket_admin(websocket: WebSocket, agent_id: str):
    user_info = await auth_middleware.authenticate(websocket, require_auth=True)
    
    # 检查权限
    try:
        await auth_middleware.check_permissions(
            user_info,
            required_permissions=["admin:host:manage"]
        )
    except AuthorizationError as e:
        await websocket.close(code=1008, reason=str(e))
        return
    
    await websocket.accept()
    # ... 继续处理
```

## 💾 连接池管理

### 概述

实现 WebSocket 连接的高效复用和资源管理。

### 主要特性

- **连接复用**: 自动检测可用连接并复用
- **自动清理**: 定期清理过期和失效连接
- **性能监控**: 跟踪命中率和连接统计

### 使用示例

```python
from services.gateway_service.app.services.websocket_connection_pool import WebSocketConnectionPool

# 初始化连接池
pool = WebSocketConnectionPool(
    max_connections_per_service=10,  # 每个服务最多 10 个连接
    idle_timeout=300,                 # 5 分钟空闲超时
    max_lifetime=3600,                # 1 小时最大生命周期
)

# 启动后台任务
await pool.start_background_tasks()

# 获取连接
async def get_backend_connection(service_url: str):
    connection = await pool.get_connection(service_url)
    try:
        # 使用连接
        await connection.send_json({"type": "ping"})
        response = await connection.recv()
    finally:
        # 释放连接回池
        await pool.release_connection(service_url, connection, reusable=True)

# 获取统计信息
stats = pool.get_stats()
print(f"连接池统计: {stats}")
# 输出示例:
# {
#     'total_connections': 5,
#     'pools': {'http://host-service:8003': {'size': 5, 'active': 4}},
#     'stats': {'total_created': 12, 'total_closed': 7, 'total_reused': 25, ...},
#     'hit_rate': 0.8333
# }

# 停止后台任务
await pool.stop_background_tasks()

# 关闭所有连接
await pool.close_all()
```

## 💓 心跳检测

### 概述

发送定期 ping 消息以验证连接的活跃性，快速检测死连接。

### 配置

```python
from services.gateway_service.app.services.websocket_features import HeartbeatManager

# 初始化心跳管理器
heartbeat = HeartbeatManager(
    interval=30.0,    # 每 30 秒发送一次 ping
    timeout=10.0,     # 10 秒响应超时
)
```

### 使用示例

```python
@app.websocket("/ws/host/api/v1/ws/agent/{agent_id}")
async def websocket_agent(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    try:
        # 定义发送心跳的函数
        async def send_heartbeat():
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # 注册心跳检测
        heartbeat.register_connection(agent_id, send_heartbeat)
        
        # 处理消息
        while True:
            data = await websocket.receive_json()
            
            # 处理 pong 响应
            if data.get("type") == "pong":
                logger.debug(f"收到 pong 响应: {agent_id}")
                continue
            
            # 处理其他消息类型
            response = await process_message(data)
            await websocket.send_json(response)
    
    finally:
        # 注销心跳检测
        heartbeat.unregister_connection(agent_id)
        await websocket.close()
```

## 🚦 速率限制

### 概述

限制 WebSocket 消息发送速率，防止洪泛攻击和 DDoS。

### 配置

```python
from services.gateway_service.app.services.websocket_features import RateLimiter

rate_limiter = RateLimiter(
    max_messages=100,           # 时间窗口内最多 100 条消息
    window_size=60.0,           # 60 秒时间窗口
    max_size_bytes=1024*1024,   # 单条消息最大 1MB
)
```

### 使用示例

```python
@app.websocket("/ws/host/api/v1/ws/agent/{agent_id}")
async def websocket_agent(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 检查速率限制
            message_str = json.dumps(data)
            is_allowed, error_msg = await rate_limiter.check_rate_limit(
                agent_id,
                len(message_str.encode('utf-8'))
            )
            
            if not is_allowed:
                await websocket.send_json({
                    "type": "error",
                    "message": error_msg,
                })
                continue
            
            # 处理消息
            response = await process_message(data)
            await websocket.send_json(response)
    
    finally:
        # 清理速率限制数据
        rate_limiter.cleanup_connection(agent_id)
        await websocket.close()
```

### 获取统计信息

```python
# 获取特定连接的限制状态
stats = rate_limiter.get_stats(agent_id)
print(f"速率限制统计: {stats}")
# 输出示例:
# {
#     'message_count': 45,
#     'max_messages': 100,
#     'percentage': 45.0,
#     'total_bytes': 45000,
#     'max_size_bytes': 1048576,
# }
```

## 🗜️ 消息压缩

### 概述

使用 Gzip 算法压缩消息，显著减少带宽占用，特别是在大消息场景下。

### 配置

```python
from services.gateway_service.app.services.websocket_features import MessageCompressor

compressor = MessageCompressor(
    compression_threshold=1024,  # 消息大于 1KB 时才压缩
)
```

### 使用示例

```python
@app.websocket("/ws/host/api/v1/ws/agent/{agent_id}")
async def websocket_agent(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            raw_data = await websocket.receive_text()
            
            # 尝试解压缩
            message = await compressor.decompress_message(raw_data)
            if not message:
                logger.error("消息解压失败")
                continue
            
            # 处理消息
            response = await process_message(message)
            response_str = json.dumps(response)
            
            # 压缩并发送响应
            compressed_response, was_compressed = await compressor.compress_message(response_str)
            await websocket.send_text(compressed_response)
            
            if was_compressed:
                logger.debug(f"消息已压缩: {agent_id}")
    
    finally:
        await websocket.close()
```

### 获取统计信息

```python
stats = compressor.get_stats()
print(f"压缩统计: {stats}")
# 输出示例:
# {
#     'total_messages': 1000,
#     'compressed_count': 750,
#     'uncompressed_count': 250,
#     'compression_rate': 75.0,
#     'bytes_saved': 500000,
# }
```

## 🎯 高级特性集成

### 完整示例

```python
from services.gateway_service.app.services.websocket_features import WebSocketFeaturesManager
from services.gateway_service.app.middleware.websocket_auth_middleware import WebSocketAuthMiddleware
from services.gateway_service.app.services.websocket_connection_pool import WebSocketConnectionPool

# 初始化所有特性
features = WebSocketFeaturesManager(
    heartbeat_interval=30.0,
    max_messages_per_minute=100,
    enable_compression=True,
    compression_threshold=1024,
)

auth = WebSocketAuthMiddleware(jwt_manager)
pool = WebSocketConnectionPool()

@app.on_event("startup")
async def startup():
    """启动时初始化"""
    await pool.start_background_tasks()

@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    await pool.stop_background_tasks()
    await pool.close_all()

@app.websocket("/ws/{service_name}/{path:path}")
async def websocket_proxy(websocket: WebSocket, service_name: str, path: str):
    # 认证
    user_info = await auth.authenticate(websocket, require_auth=False)
    await websocket.accept()
    
    connection_id = f"{service_name}_{path}"
    
    try:
        # 注册心跳
        async def send_ping():
            await websocket.send_json({"type": "ping"})
        
        features.heartbeat_manager.register_connection(connection_id, send_ping)
        
        while True:
            # 接收消息
            raw_data = await websocket.receive_text()
            
            # 检查速率限制
            is_allowed, error = await features.rate_limiter.check_rate_limit(
                connection_id,
                len(raw_data.encode('utf-8'))
            )
            if not is_allowed:
                await websocket.send_json({"type": "error", "message": error})
                continue
            
            # 解压缩
            message = await features.compressor.decompress_message(raw_data)
            if not message:
                continue
            
            # 转发到后端（使用连接池）
            backend_url = f"ws://{service_name}:8003{path}"
            backend_conn = await pool.get_connection(backend_url)
            
            try:
                await backend_conn.send(message)
                response = await backend_conn.recv()
                
                # 压缩并发送响应
                compressed, _ = await features.compressor.compress_message(response)
                await websocket.send_text(compressed)
            
            finally:
                await pool.release_connection(backend_url, backend_conn)
    
    finally:
        features.heartbeat_manager.unregister_connection(connection_id)
        features.rate_limiter.cleanup_connection(connection_id)
        await websocket.close()
```

## 📊 监控和统计

### 获取全局统计

```python
# 连接池统计
pool_stats = pool.get_stats()
print(f"连接池: {pool_stats}")

# 速率限制统计
ratelimit_stats = features.rate_limiter.get_stats(connection_id)
print(f"速率限制: {ratelimit_stats}")

# 压缩统计
compression_stats = features.compressor.get_stats()
print(f"压缩: {compression_stats}")

# 所有特性统计
all_stats = features.get_stats()
print(f"所有特性: {all_stats}")
```

### Prometheus 指标导出

```python
from prometheus_client import Gauge, Counter

# 定义指标
websocket_connections = Gauge("websocket_connections", "WebSocket 连接数", ["service"])
websocket_messages_total = Counter("websocket_messages_total", "消息总数", ["service"])
websocket_bytes_compressed = Counter("websocket_bytes_compressed", "压缩字节数", ["service"])

# 定期导出统计
async def export_stats():
    while True:
        await asyncio.sleep(60)
        
        stats = pool.get_stats()
        for service, pool_info in stats["pools"].items():
            websocket_connections.labels(service=service).set(pool_info["active"])
        
        compression_stats = features.compressor.get_stats()
        websocket_bytes_compressed.labels(service="all").inc(
            compression_stats["bytes_saved"]
        )
```

## 🚀 性能优化建议

### 1. 连接池配置优化

```python
# 开发环境
pool = WebSocketConnectionPool(
    max_connections_per_service=5,
    idle_timeout=120,
    max_lifetime=600,
)

# 生产环境
pool = WebSocketConnectionPool(
    max_connections_per_service=50,
    idle_timeout=300,
    max_lifetime=3600,
)
```

### 2. 速率限制调优

```python
# 严格限制（防止攻击）
rate_limiter = RateLimiter(
    max_messages=50,
    max_size_bytes=512*1024,  # 512KB
)

# 宽松限制（高吞吐量）
rate_limiter = RateLimiter(
    max_messages=1000,
    max_size_bytes=10*1024*1024,  # 10MB
)
```

### 3. 压缩阈值调优

```python
# 激进压缩（更低延迟）
compressor = MessageCompressor(compression_threshold=512)

# 保守压缩（更好兼容性）
compressor = MessageCompressor(compression_threshold=2048)
```

## 📝 最佳实践

1. **认证**: 总是在接受连接前进行认证
2. **心跳**: 对长连接启用心跳检测
3. **限制**: 根据场景选择合适的速率限制
4. **压缩**: 对大消息启用压缩以降低带宽
5. **监控**: 定期检查统计指标以优化配置
6. **清理**: 确保断开连接时进行必要的清理

## 🔗 相关文件

- [websocket_auth_middleware.py](mdc:services/gateway-service/app/middleware/websocket_auth_middleware.py)
- [websocket_connection_pool.py](mdc:services/gateway-service/app/services/websocket_connection_pool.py)
- [websocket_features.py](mdc:services/gateway-service/app/services/websocket_features.py)
- [proxy.py](mdc:services/gateway-service/app/api/v1/endpoints/proxy.py)
