# WebSocket 快速开始指南

## ⚡ 30 秒快速上手

### 正确的地址（简化格式 ✨ 推荐）

```
ws://localhost:8000/host/ws/agent/agent-123
                    ↑    ↑
                    |    |
              服务简名  路径
```

**支持的服务简名:**
- `host` → host-service
- `auth` → auth-service  
- `admin` → admin-service

### Python 连接示例

```python
import asyncio
import websockets

async def main():
    # ✅ 新格式（推荐）
    uri = "ws://localhost:8000/host/ws/agent/agent-123"
    
    # 或者旧格式（仍支持）
    # uri = "ws://localhost:8000/ws/host-service/ws/agent/agent-123"
    
    async with websockets.connect(uri) as ws:
        await ws.send("hello")
        print(await ws.recv())

asyncio.run(main())
```

### JavaScript 连接示例

```javascript
// ✅ 新格式（推荐）
const ws = new WebSocket('ws://localhost:8000/host/ws/agent/agent-123');

// 或者旧格式（仍支持）
// const ws = new WebSocket('ws://localhost:8000/ws/host-service/ws/agent/agent-123');

ws.onopen = () => ws.send("hello");
ws.onmessage = (e) => console.log(e.data);
```

---

## 🔑 关键点

| 项目 | 说明 |
|------|------|
| **协议** | `ws://` (非 `http://`) |
| **主机** | `localhost:8000` (网关地址) |
| **新路由格式** | `/{service_short_name}/{path}` |
| **简化示例** | `/host/ws/agent/agent-123` |
| **旧路由格式** | `/ws/{service_name}/{path}` (仍支持) |
| **认证** | Authorization 请求头或 token 查询参数 |

---

## 📌 常见问题

### Q: 收到 403 错误？
**A:** 确保路径格式正确：
- ✅ 正确: `/host/ws/agent/agent-123` (必须以 `ws/` 开头)
- ❌ 错误: `/host/agent/agent-123` (缺少 `ws/` 前缀)

### Q: 收到"Unknown service"错误？
**A:** 检查服务简名是否有效。支持的服务：
- `host` (host-service)
- `auth` (auth-service)
- `admin` (admin-service)

### Q: 收到 401 错误？
**A:** 需要提供有效的 JWT token。使用 Authorization 请求头或查询参数

### Q: 收到 502 错误？
**A:** 后端服务可能未运行。检查：
```bash
docker-compose ps host-service
docker-compose logs host-service
```

### Q: 无法连接？
**A:** 网关可能未运行。检查：
```bash
docker-compose ps gateway-service
docker-compose logs gateway-service
```

---

## 🧪 快速测试

```bash
# 运行测试脚本
python test_websocket_correct.py
```

---

## 📍 地址组成 - 新格式

```
ws://localhost:8000/host/ws/agent/agent-123
│     │            │    │  │     │          │
│     │            │    │  │     │          └─ agent_id
│     │            │    │  │     └──────────── agent 标识
│     │            │    │  └───────────────── WebSocket 路径
│     │            │    └────────────────── 后端路径前缀
│     │            └──────────────────────── 服务简名（host）
│     └────────────────────────────────────── 网关地址
└──────────────────────────────────────────── WebSocket 协议
```

---

## 📍 地址组成 - 旧格式（仍支持）

```
ws://localhost:8000/ws/host-service/ws/agent/agent-123
│     │            │  │            │  │     │          │
│     │            │  │            │  │     │          └─ agent_id
│     │            │  │            │  │     └──────────── agent 标识
│     │            │  │            │  └───────────────── WebSocket 路径
│     │            │  │            └────────────────── 后端服务路径
│     │            │  └────────────────────────────── 服务完整名
│     │            └─────────────────────────────── 网关路由前缀
│     └──────────────────────────────────────────── 网关地址
└──────────────────────────────────────────────── WebSocket 协议
```

---

## ✅ 检查清单

在连接前检查：

- [ ] 网关运行在 localhost:8000
- [ ] 后端服务运行正常
- [ ] 使用正确的地址格式（新格式: `/host/...`）
- [ ] 路径必须以 `ws/` 开头
- [ ] 使用正确的服务简名 (host/auth/admin)
- [ ] 如需认证，准备好 JWT token
- [ ] 使用 `ws://` 不是 `http://`

---

## 🔐 带认证的连接

### Python

```python
import asyncio
import websockets

async def connect_with_auth():
    uri = "ws://localhost:8000/host/ws/agent/agent-123"
    token = "your-jwt-token"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with websockets.connect(uri, extra_headers=headers.items()) as ws:
        await ws.send("authenticated message")
        print(await ws.recv())

asyncio.run(connect_with_auth())
```

### JavaScript (浏览器)

```javascript
const token = "your-jwt-token";
const ws = new WebSocket(
  `ws://localhost:8000/host/ws/agent/agent-123?token=${token}`
);

ws.onopen = () => ws.send("authenticated message");
ws.onmessage = (e) => console.log(e.data);
```

---

## 🚀 支持的格式总结

### 新格式（推荐）✨
```
ws://localhost:8000/{service_short_name}/{path}
ws://localhost:8000/host/ws/agent/agent-123
ws://localhost:8000/auth/ws/...
ws://localhost:8000/admin/ws/...
```

### 旧格式（仍支持）
```
ws://localhost:8000/ws/{service_name}/{path}
ws://localhost:8000/ws/host-service/ws/agent/agent-123
```

---

## 📚 下一步

- 详细诊断: [WEBSOCKET_403_DIAGNOSIS.md](./WEBSOCKET_403_DIAGNOSIS.md)
- 集成指南: [services/gateway-service/app/services/WEBSOCKET_INTEGRATION.md](./services/gateway-service/app/services/WEBSOCKET_INTEGRATION.md)
- 认证详情: [services/gateway-service/app/services/WEBSOCKET_AUTH_EXAMPLES.md](./services/gateway-service/app/services/WEBSOCKET_AUTH_EXAMPLES.md)

---

**一句话总结**: 使用 `ws://localhost:8000/host/ws/agent/{agentId}` 的简化格式即可连接！🎉
