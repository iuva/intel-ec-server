# WebSocket 格式升级指南

## 📢 重要更新

网关现在支持 **新的简化 WebSocket 地址格式**，同时保持向后兼容！

---

## 🎯 新旧格式对比

### 🆕 新格式（推荐）✨

```
ws://localhost:8000/{service_short_name}/{path}
```

**示例:**
```
ws://localhost:8000/host/ws/agent/agent-123
ws://localhost:8000/auth/ws/...
ws://localhost:8000/admin/ws/...
```

**优势:**
- ✅ 更短、更简洁
- ✅ 易于记忆和使用
- ✅ 与 REST API 风格一致
- ✅ 减少输入错误

---

### 🔄 旧格式（仍支持）

```
ws://localhost:8000/ws/{service_name}/{path}
```

**示例:**
```
ws://localhost:8000/ws/host-service/ws/agent/agent-123
ws://localhost:8000/ws/auth-service/ws/...
ws://localhost:8000/ws/admin-service/ws/...
```

**注意:** 旧格式仍完全支持，不需要立即迁移

---

## 📋 服务简名映射表

| 简名 | 完整服务名 | 端口 | 示例 |
|------|----------|------|------|
| `host` | `host-service` | 8003 | `/host/ws/agent/agent-123` |
| `auth` | `auth-service` | 8001 | `/auth/ws/...` |
| `admin` | `admin-service` | 8002 | `/admin/ws/...` |

---

## 🚀 立即升级

### Python 客户端

```python
import asyncio
import websockets

async def main():
    # ✅ 使用新格式
    uri = "ws://localhost:8000/host/ws/agent/agent-123"
    
    async with websockets.connect(uri) as ws:
        await ws.send("hello")
        print(await ws.recv())

asyncio.run(main())
```

### JavaScript 客户端

```javascript
// ✅ 使用新格式
const ws = new WebSocket('ws://localhost:8000/host/ws/agent/agent-123');

ws.onopen = () => ws.send("hello");
ws.onmessage = (e) => console.log(e.data);
ws.onerror = (e) => console.error(e);
```

### cURL 测试

```bash
# 使用新格式测试连接
websocat ws://localhost:8000/host/ws/agent/agent-123

# 如果没有 websocat，可以用 wscat (npm install -g wscat)
wscat -c ws://localhost:8000/host/ws/agent/agent-123
```

---

## ✅ 迁移检查清单

- [ ] 更新所有硬编码的 WebSocket URL
- [ ] 更新文档和示例
- [ ] 更新测试脚本
- [ ] 验证新旧格式都能正常工作
- [ ] 在团队中分享新格式信息

---

## 🎓 技术实现详情

### 网关路由配置

在 `services/gateway-service/app/api/v1/endpoints/proxy.py` 中:

```python
# 新路由（简化格式）
@router.websocket("/{service_short_name}/{path:path}")
async def websocket_proxy_short(
    websocket: WebSocket,
    service_short_name: str,
    path: str,
    proxy_service: ProxyService = Depends(get_proxy_service),
):
    """支持简化格式的 WebSocket 代理"""
    # 将简称映射到完整服务名
    # 例如: host -> host-service
    # ...

# 旧路由（完整格式，向后兼容）
@router.websocket("/ws/{service_name}/{path:path}")
async def websocket_proxy(websocket, service_name, path, ...):
    """支持完整格式的 WebSocket 代理"""
    # ...
```

### 路由匹配优先级

FastAPI 按照**第一个匹配**来处理路由，所以：

1. **新格式路由优先处理**: `/{service_short_name}/{path:path}`
2. **旧格式路由次之**: `/ws/{service_name}/{path:path}`
3. **通用代理路由最后**: `/{service_name}/{subpath:path}` (HTTP)

---

## 📊 路由转发流程

```
客户端请求
    ↓
ws://localhost:8000/host/ws/agent/agent-123
    ↓
网关路由匹配 (新格式: /{service_short_name}/{path:path})
    ↓
service_short_name = "host"
path = "ws/agent/agent-123"
    ↓
查询映射表: host → host-service
    ↓
转发到后端: ws://host-service:8003/api/v1/ws/agent/agent-123
    ↓
Host Service WebSocket 端点处理
    ↓
消息双向转发给客户端
```

---

## 🔍 常见问题

### Q: 我应该立即升级吗？
**A:** 不需要！旧格式仍完全支持。可以逐步升级您的代码。

### Q: 升级会有什么影响？
**A:** 完全没有负面影响！两种格式可以共存使用。

### Q: 有没有性能差异？
**A:** 没有。两种格式使用相同的后端代码，性能相同。

### Q: 我想同时支持两种格式怎么办？
**A:** 完全可以！客户端可以根据场景选择任一格式使用。

### Q: 如何测试新格式是否工作？
**A:** 运行提供的测试脚本: `python test_websocket_correct.py`

---

## 📚 相关文档

- [WEBSOCKET_QUICK_START.md](./WEBSOCKET_QUICK_START.md) - 快速开始指南（已更新）
- [WEBSOCKET_403_DIAGNOSIS.md](./WEBSOCKET_403_DIAGNOSIS.md) - 问题诊断指南
- [services/gateway-service/app/services/WEBSOCKET_INTEGRATION.md](./services/gateway-service/app/services/WEBSOCKET_INTEGRATION.md) - 完整集成指南

---

## 🎉 总结

| 方面 | 旧格式 | 新格式 |
|------|--------|--------|
| 格式 | `/ws/{service_name}/{path}` | `/{short_name}/{path}` |
| 示例 | `/ws/host-service/ws/agent/123` | `/host/ws/agent/123` |
| 长度 | 长 | 短 ✨ |
| 易读性 | 良好 | 优秀 ✨ |
| 向后兼容 | N/A | ✅ 完全支持 |
| 推荐使用 | 可选 | ✅ 推荐 |

---

**更新日期**: 2025-10-25
**版本**: 1.0
**状态**: 生效中 ✅
