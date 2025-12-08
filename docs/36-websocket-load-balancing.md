# WebSocket 负载均衡和会话粘性

## ✅ 状态：已实现会话粘性

**WebSocket 会话粘性功能已实现**，确保同一个 `host_id` 的连接总是路由到同一个实例。

## 🎯 问题概述

当启动多个 `host-service` 实例并使用负载均衡时，WebSocket 连接可能会遇到以下问题：

1. **连接分配到不同实例**：同一个客户端的 WebSocket 连接可能被分配到不同的实例
2. **重连时实例切换**：客户端重连时可能连接到不同的实例
3. **状态不一致**：不同实例之间的连接状态可能不一致

**✅ 已解决**：通过实现基于 `host_id` 的会话粘性，确保同一 `host_id` 总是路由到同一实例。

## ⚠️ 当前实现的影响

### 问题分析

在当前的实现中，`forward_websocket` 方法每次建立连接时都会调用 `get_service_url`：

```python
# services/gateway-service/app/services/proxy_service.py
resolved_service_url = service_url
if not resolved_service_url:
    resolved_service_url = await self.get_service_url(service_name)  # 使用轮询
```

**影响**：
- 如果使用轮询负载均衡，每次 WebSocket 连接可能被分配到不同的实例
- 同一个 `host_id` 的连接可能在不同实例之间切换

### 现有保护机制

虽然存在上述问题，但系统有保护机制：

1. **重复连接处理**：`AgentWebSocketManager` 会检测并断开重复连接
   ```python
   # 如果同一个 agent_id 已有连接，先断开旧连接
   if agent_id in self.active_connections:
       await self.disconnect(agent_id)
   ```

2. **连接状态同步**：每个实例独立管理连接，不会相互干扰

## ✅ 解决方案：WebSocket 会话粘性

### 方案 1：基于 host_id 的会话粘性（推荐）

为 WebSocket 连接实现基于 `host_id` 的会话粘性，确保同一个 `host_id` 的连接总是路由到同一个实例。

#### 实现原理

1. **哈希算法**：使用 `host_id` 的哈希值选择实例
2. **一致性哈希**：确保实例变化时最小化连接迁移
3. **连接缓存**：缓存 `host_id` 到实例的映射

#### 代码实现

修改 `ServiceDiscovery` 类，添加 WebSocket 专用的服务选择方法：

```python
# shared/utils/service_discovery.py

def get_websocket_service_url(self, service_name: str, session_key: str) -> str:
    """获取 WebSocket 服务 URL（支持会话粘性）
    
    Args:
        service_name: 服务名称
        session_key: 会话键（如 host_id），用于会话粘性
    
    Returns:
        服务 URL
    """
    # 获取所有实例
    instances = self._get_all_instances(service_name)
    
    if not instances:
        return self._get_fallback_url(service_name)
    
    # 使用会话键的哈希值选择实例
    hash_value = hash(session_key)
    selected_index = hash_value % len(instances)
    selected_instance = instances[selected_index]
    
    return f"http://{selected_instance['ip']}:{selected_instance['port']}"
```

修改 `ProxyService.forward_websocket` 方法：

```python
# services/gateway-service/app/services/proxy_service.py

async def forward_websocket(
    self,
    service_name: str,
    path: str,
    client_websocket: Any,
    service_url: Optional[str] = None,
    session_key: Optional[str] = None,  # 新增：会话键
) -> None:
    """转发 WebSocket 连接（支持会话粘性）"""
    
    # 如果提供了会话键，使用会话粘性选择实例
    if session_key and self.service_discovery:
        resolved_service_url = await self.service_discovery.get_websocket_service_url(
            service_name, session_key
        )
    elif not service_url:
        resolved_service_url = await self.get_service_url(service_name)
    else:
        resolved_service_url = service_url
    
    # ... 其余代码保持不变
```

### 方案 2：使用 Nginx/IPVS 的会话粘性

在网关层使用 Nginx 或 IPVS 的会话粘性功能：

```nginx
# nginx.conf
upstream host_service {
    ip_hash;  # 基于客户端 IP 的会话粘性
    server 127.0.0.1:8003;
    server 127.0.0.1:8004;
}
```

**优点**：
- 无需修改代码
- 性能好

**缺点**：
- 需要额外的代理层
- 基于 IP 的粘性可能不够精确（同一 NAT 后的多个客户端）

### 方案 3：使用 Redis 共享连接状态

使用 Redis 存储连接状态，所有实例共享：

```python
# 连接时存储映射
redis.set(f"websocket:host_id:{host_id}:instance", instance_id)

# 重连时获取映射
instance_id = redis.get(f"websocket:host_id:{host_id}:instance")
```

**优点**：
- 状态共享
- 支持实例故障转移

**缺点**：
- 需要 Redis
- 增加延迟

## 🔧 推荐实现：基于 host_id 的哈希选择

### 实现步骤

1. **修改 ServiceDiscovery**：添加 WebSocket 专用方法
2. **修改 ProxyService**：在转发 WebSocket 时使用会话键
3. **提取 host_id**：从 WebSocket 连接中提取 `host_id` 作为会话键

### 代码修改

#### 1. 修改 ServiceDiscovery

```python
# shared/utils/service_discovery.py

async def get_websocket_service_url(
    self, 
    service_name: str, 
    session_key: str
) -> str:
    """获取 WebSocket 服务 URL（支持会话粘性）
    
    使用 session_key 的哈希值选择实例，确保同一个 session_key
    总是路由到同一个实例。
    
    Args:
        service_name: 服务名称
        session_key: 会话键（如 host_id）
    
    Returns:
        服务 URL
    """
    # 优先级 1: 从 Nacos 获取实例
    if self.nacos_manager:
        instances = await self._get_instances_from_nacos(service_name)
        if instances:
            selected_instance = self._select_instance_by_hash(instances, session_key)
            if selected_instance:
                url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
                logger.info(
                    f"WebSocket 会话粘性选择（Nacos）: {service_name} -> {url}",
                    extra={
                        "session_key": session_key,
                        "selected_ip": selected_instance['ip'],
                        "selected_port": selected_instance['port'],
                    },
                )
                return url
    
    # 优先级 2: 从本地配置获取实例
    local_instances = self._get_local_instances(service_name)
    if local_instances:
        selected_instance = self._select_instance_by_hash(local_instances, session_key)
        if selected_instance:
            url = f"http://{selected_instance['ip']}:{selected_instance['port']}"
            logger.info(
                f"WebSocket 会话粘性选择（本地）: {service_name} -> {url}",
                extra={
                    "session_key": session_key,
                    "selected_ip": selected_instance['ip'],
                    "selected_port": selected_instance['port'],
                },
            )
            return url
    
    # 优先级 3: 后备地址
    return self._get_fallback_url(service_name)

def _select_instance_by_hash(
    self, 
    instances: List[Dict[str, Any]], 
    session_key: str
) -> Dict[str, Any]:
    """基于会话键的哈希值选择实例
    
    Args:
        instances: 实例列表
        session_key: 会话键
    
    Returns:
        选中的实例
    """
    if not instances:
        return None
    
    if len(instances) == 1:
        return instances[0]
    
    # 使用会话键的哈希值选择实例
    hash_value = hash(session_key)
    selected_index = abs(hash_value) % len(instances)
    selected_instance = instances[selected_index]
    
    logger.debug(
        f"基于哈希选择实例",
        extra={
            "session_key": session_key,
            "hash_value": hash_value,
            "selected_index": selected_index,
            "total_instances": len(instances),
            "selected_ip": selected_instance['ip'],
            "selected_port": selected_instance['port'],
        },
    )
    
    return selected_instance
```

#### 2. 修改 ProxyService

```python
# services/gateway-service/app/services/proxy_service.py

async def forward_websocket(
    self,
    service_name: str,
    path: str,
    client_websocket: Any,
    service_url: Optional[str] = None,
    session_key: Optional[str] = None,  # 新增：会话键
) -> None:
    """转发 WebSocket 连接（支持会话粘性）"""
    
    # ... 前面的代码保持不变 ...
    
    # ✅ 如果提供了会话键，使用会话粘性选择实例
    if session_key and self.service_discovery:
        try:
            resolved_service_url = await self.service_discovery.get_websocket_service_url(
                service_name, session_key
            )
            logger.info(
                "使用会话粘性选择 WebSocket 实例",
                extra={
                    "service_name": service_name,
                    "session_key": session_key,
                    "selected_url": resolved_service_url,
                },
            )
        except Exception as e:
            logger.warning(
                "会话粘性选择失败，使用默认方式",
                extra={"error": str(e)},
            )
            resolved_service_url = await self.get_service_url(service_name)
    elif not service_url:
        resolved_service_url = await self.get_service_url(service_name)
    else:
        resolved_service_url = service_url
    
    # ... 其余代码保持不变 ...
```

#### 3. 修改 WebSocket 端点

```python
# services/gateway-service/app/api/v1/endpoints/proxy.py

@router.websocket("/ws/{hostname}/{apiurl:path}")
async def websocket_proxy(
    websocket: WebSocket = ...,
    hostname: str = Path(...),
    apiurl: str = Path(...),
    proxy_service: ProxyService = Depends(get_proxy_service_ws),
) -> None:
    # ... 前面的代码保持不变 ...
    
    # ✅ 提取 host_id 作为会话键
    session_key = None
    try:
        # 从查询参数或 token 中提取 host_id
        host_id_param = websocket.query_params.get("host_id")
        if host_id_param:
            session_key = host_id_param
        elif user_id:
            session_key = str(user_id)
    except Exception:
        ***REMOVED***
    
    # ... 转发 WebSocket 时传递 session_key ...
    await proxy_service.forward_websocket(
        service_name=service_short_name,
        path=backend_path,
        client_websocket=websocket,
        session_key=session_key,  # 传递会话键
    )
```

## 📊 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| 基于 host_id 哈希 | 实现简单，无需额外组件 | 实例变化时可能迁移连接 | ⭐⭐⭐⭐⭐ |
| Nginx/IPVS 粘性 | 无需修改代码，性能好 | 需要额外代理层，基于 IP 不够精确 | ⭐⭐⭐⭐ |
| Redis 共享状态 | 状态共享，支持故障转移 | 需要 Redis，增加延迟 | ⭐⭐⭐ |

## ✅ 已实现：WebSocket 会话粘性

### 实现状态

✅ **已完成**：基于 `host_id` 的哈希选择已实现

### 功能说明

1. **会话粘性**：同一个 `host_id` 的 WebSocket 连接总是路由到同一个实例
2. **哈希算法**：使用 `host_id` 的哈希值选择实例，确保一致性
3. **自动提取**：从 WebSocket 连接中自动提取 `host_id` 作为会话键

### 使用方法

无需额外配置，系统会自动：
1. 从 WebSocket 连接中提取 `host_id`
2. 使用 `host_id` 的哈希值选择实例
3. 确保同一 `host_id` 总是路由到同一实例

### 测试验证

运行测试脚本验证功能：

```bash
# 设置环境变量
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"

# 运行测试
python scripts/test_websocket_sticky.py
```

应该看到输出：

```
Host ID: host_001
  请求 1: http://127.0.0.1:8003
  请求 2: http://127.0.0.1:8003
  请求 3: http://127.0.0.1:8003
  ✅ 会话粘性正常：总是路由到 http://127.0.0.1:8003
```

## 🚀 实施建议

### 当前状态

✅ **已实现**：WebSocket 会话粘性功能已实现并可用

### 后续优化

1. **一致性哈希**：考虑使用一致性哈希算法，减少实例变化时的连接迁移
2. **监控指标**：添加会话粘性相关的监控指标
3. **性能优化**：优化哈希算法性能

## 📝 注意事项

1. **实例变化**：如果实例数量变化，部分连接可能需要迁移
2. **故障转移**：实例故障时，连接需要重新建立
3. **负载均衡**：会话粘性可能影响负载均衡的均匀性

## 🔗 相关文档

- [Gateway 负载均衡配置](./35-gateway-load-balancing.md)
- [WebSocket 连接和断线处理](./31-websocket-connection-disconnection-logic.md)
- [WebSocket 消息类型](./32-websocket-message-types.md)

