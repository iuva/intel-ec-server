# WebSocket 完整修复总结 (2025-10-28)

## 🎯 问题概述

Gateway WebSocket连接存在多个关键问题，阻止了WebSocket消息的正确转发。

## 🐛 问题清单

### 问题1: FastAPI WebSocket不支持async for
**症状**: `'async for' requires an object with __aiter__ method, got WebSocket`

**原因**: 错误地使用 `async for message in websocket` 来遍历FastAPI WebSocket对象，但FastAPI WebSocket不实现 `__aiter__` 方法

**修复**: 使用 `await websocket.receive_text()` 和 `await websocket.receive_bytes()` 来接收消息

```python
# ❌ 错误方式
async for message in source:
    await destination.send(message)

# ✅ 正确方式
while True:
    try:
        message = await source.receive_text()
    except RuntimeError:
        message = await source.receive_bytes()
    await destination.send(message)
```

---

### 问题2: 两种不同的WebSocket对象类型
**症状**: `'WebSocketClientProtocol' object has no attribute 'receive_text'`

**原因**: Gateway中存在两种WebSocket对象类型：
- **客户端 → Gateway**: FastAPI `WebSocket` (有 `receive_text()` / `send_text()`)
- **Gateway → 后端**: `websockets.WebSocketClientProtocol` (有 `recv()` / `send()`)

**架构图**:
```
┌────────┐         ┌─────────────┐         ┌──────────┐
│ 客户端  │ ←────→ │   Gateway   │ ←────→ │  后端服务  │
└────────┘  FastAPI  └─────────────┘ websockets └──────────┘
           WebSocket  Proxy Service Protocol
```

**修复**: 使用类型检测来选择正确的API

```python
# ✅ 正确的类型检测
is_fastapi_source = hasattr(source, 'receive_text')
is_fastapi_destination = hasattr(destination, 'send_text')

# ✅ FastAPI WebSocket (客户端)
if is_fastapi_source:
    message = await source.receive_text()
    await destination.send_text(message)

# ✅ websockets.WebSocketClientProtocol (后端)
else:
    message = await source.recv()
    await destination.send(message)
```

---

### 问题3: 不准确的类型检测
**症状**: `'WebSocketClientProtocol' object has no attribute 'send_text'`

**原因**: 之前的检测方式使用 `hasattr(destination, 'send')`，但两种WebSocket对象都有 `send()` 方法

**原始代码**:
```python
# ❌ 不准确
is_fastapi_destination = hasattr(destination, 'send') and not hasattr(destination, '_writer')
```

**修复**: 使用 `send_text()` 来区分，这是FastAPI WebSocket特有的

```python
# ✅ 准确的检测
is_fastapi_destination = hasattr(destination, 'send_text')
```

---

## 📊 API对比表

| 操作 | FastAPI WebSocket | websockets.WebSocketClientProtocol |
|------|---|----|
| 接收文本 | `receive_text()` | `recv()` (返回str/bytes) |
| 接收二进制 | `receive_bytes()` | `recv()` (返回str/bytes) |
| 发送文本 | `send_text(str)` | `send(str)` |
| 发送二进制 | `send_bytes(bytes)` | `send(bytes)` |
| 检查类型 | `hasattr(..., 'receive_text')` | `hasattr(..., 'recv')` |
| 特有方法 | `send_text()` | 无 |

---

## 🔧 完整修复代码

### 服务文件: `services/gateway-service/app/services/proxy_service.py`

```python
async def _forward_messages(
    self,
    source: Any,  # FastAPI WebSocket 或 websockets.WebSocketClientProtocol
    destination: Any,  # websockets.WebSocketClientProtocol 或 FastAPI WebSocket
    direction: str = "unknown",
) -> None:
    """转发消息流
    
    Args:
        source: 源 WebSocket (可能是FastAPI WebSocket或websockets.WebSocketClientProtocol)
        destination: 目标 WebSocket (可能是FastAPI WebSocket或websockets.WebSocketClientProtocol)
        direction: 转发方向（用于日志）
    """
    import websockets

    try:
        # ✅ 准确的类型检测
        is_fastapi_source = hasattr(source, 'receive_text')
        is_fastapi_destination = hasattr(destination, 'send_text')

        while True:
            try:
                message = None
                
                # ✅ 接收消息 - 根据source类型选择方法
                if is_fastapi_source:
                    # FastAPI WebSocket
                    try:
                        message = await source.receive_text()
                    except RuntimeError:
                        # 不是文本消息，尝试接收字节
                        message = await source.receive_bytes()
                else:
                    # websockets.WebSocketClientProtocol
                    message = await source.recv()
                
                # ✅ 发送消息 - 根据destination类型选择方法
                if is_fastapi_destination:
                    # FastAPI WebSocket
                    if isinstance(message, bytes):
                        await destination.send_bytes(message)
                    else:
                        await destination.send_text(message)
                else:
                    # websockets.WebSocketClientProtocol
                    await destination.send(message)

            except websockets.exceptions.ConnectionClosed:
                logger.info(f"消息转发中连接已关闭: {direction}")
                break
            except Exception as e:
                logger.error(f"消息转发失败 ({direction}): {e!s}")
                break

    except websockets.exceptions.ConnectionClosed:
        logger.debug(f"源连接已关闭: {direction}")
    except Exception as e:
        logger.error(f"转发异常 ({direction}): {e!s}")
    finally:
        with contextlib.suppress(Exception):
            # ✅ 通用的close方式 - 两种类型都支持
            await destination.close()
```

---

## ✅ 验证清单

- [x] 移除 `async for` 循环，使用 `while True` + `receive_text()`/`receive_bytes()`
- [x] 添加FastAPI WebSocket和websockets.WebSocketClientProtocol的区分逻辑
- [x] 使用 `hasattr(destination, 'send_text')` 准确检测FastAPI WebSocket
- [x] 为两种WebSocket对象使用正确的API
- [x] 异常处理支持两种连接关闭方式
- [x] 测试通过 - WebSocket消息正确转发

---

## 📈 改进历史

| 提交 | 问题 | 修复 |
|------|------|------|
| b02ef06 | async for 错误 | 改为 while True + receive_text/bytes |
| 2e40d44 | 不准确的类型检测 | 使用 send_text() 检测 |

---

## 🎓 学到的经验

1. **不同的WebSocket库有不同的API**: FastAPI WebSocket vs websockets库
2. **类型检测需要谨慎**: 使用库特有的方法来区分对象类型
3. **异常处理要完整**: websockets.exceptions.ConnectionClosed 需要特殊处理
4. **架构设计很重要**: Proxy模式需要支持多种底层实现

---

## 🚀 下一步

WebSocket完整流程现已修复：
- ✅ Token验证成功
- ✅ WebSocket连接建立
- ✅ 后端连接建立
- ✅ **消息正确转发**（已修复）

系统应该现在能够正确处理WebSocket连接和消息转发。

---

**修复时间**: 2025-10-28  
**修复者**: AI Assistant  
**状态**: ✅ 完成
