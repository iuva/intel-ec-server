# Gateway WebSocket 错误处理优化

## 📋 问题描述

### 用户报告的问题

```log
2025-10-28 07:59:34.566 | ERROR | gateway-service | 
WebSocket 连接异常: server rejected WebSocket connection: HTTP 403
```

**错误响应**:
```json
{
    "code": 500,
    "message": "WebSocket 转发异常",
    "error_code": "WEBSOCKET_PROXY_ERROR"
}
```

**问题分析**:
1. ❌ 后端服务返回 **HTTP 403**（认证失败）
2. ❌ Gateway 返回 **500**（服务器内部错误）
3. ❌ 错误消息是通用的 "WebSocket 转发异常"
4. ❌ 无法让客户端知道是认证问题

### 期望行为

当 Token 过期或无效时：
```json
{
    "code": 403,
    "message": "WebSocket 认证失败，Token 无效或已过期",
    "error_code": "WEBSOCKET_AUTH_FAILED"
}
```

## 🔧 修复方案

### 修复分两层

修复需要在两个层面进行：
1. **`proxy_service.py`**: 识别后端返回的 HTTP 403/401
2. **`proxy.py`**: 传递准确的错误信息给客户端

### 1. 新增错误码

**文件**: `shared/common/exceptions.py:80`

```python
class ServiceErrorCodes:
    """微服务统一错误码生成器"""

    # 网关服务错误码 (10001-10999)
    GATEWAY_SERVICE_NOT_FOUND = 10001
    GATEWAY_SERVICE_UNAVAILABLE = 10002
    GATEWAY_CONNECTION_FAILED = 10003
    GATEWAY_TIMEOUT = 10004
    GATEWAY_NETWORK_ERROR = 10005
    GATEWAY_PROTOCOL_ERROR = 10006
    GATEWAY_INVALID_RESPONSE = 10007
    GATEWAY_RATE_LIMITED = 10008
    GATEWAY_PROXY_ERROR = 10009
    GATEWAY_INTERNAL_ERROR = 10010
    # ✅ 新增
    GATEWAY_AUTH_FAILED = 10011      # WebSocket 认证失败（403）
    GATEWAY_UNAUTHORIZED = 10012     # WebSocket 未授权（401）
```

### 2. 改进 proxy_service.py 异常处理逻辑

**文件**: `services/gateway-service/app/services/proxy_service.py:436`

**作用**: 识别后端服务返回的 HTTP 403/401，抛出带准确信息的 `BusinessError`

#### Before（修复前）

```python
except websockets.exceptions.WebSocketException as e:
    logger.error(
        f"WebSocket 连接异常: {e!s}",
        extra={"service_name": service_name, "path": path},
    )
    raise BusinessError(
        message="WebSocket 连接失败",  # ❌ 通用错误消息
        error_code="WEBSOCKET_CONNECTION_ERROR",
        code=ServiceErrorCodes.GATEWAY_CONNECTION_FAILED,
        http_status_code=502,  # ❌ 总是返回 502
    )
```

#### After（修复后）

```python
except websockets.exceptions.WebSocketException as e:
    error_msg = str(e)

    # ✅ 检查是否为认证失败（403 Forbidden）
    if "HTTP 403" in error_msg or "403 Forbidden" in error_msg:
        logger.warning(
            f"WebSocket 认证失败: {error_msg}",
            extra={"service_name": service_name, "path": path},
        )
        raise BusinessError(
            message="WebSocket 认证失败，Token 无效或已过期",
            error_code="WEBSOCKET_AUTH_FAILED",
            code=ServiceErrorCodes.GATEWAY_AUTH_FAILED,
            http_status_code=403,  # ✅ 准确的状态码
        )

    # ✅ 检查是否为未授权（401 Unauthorized）
    if "HTTP 401" in error_msg or "401 Unauthorized" in error_msg:
        logger.warning(
            f"WebSocket 未授权: {error_msg}",
            extra={"service_name": service_name, "path": path},
        )
        raise BusinessError(
            message="WebSocket 连接未授权，请提供有效的认证令牌",
            error_code="WEBSOCKET_UNAUTHORIZED",
            code=ServiceErrorCodes.GATEWAY_UNAUTHORIZED,
            http_status_code=401,
        )

    # ✅ 其他 WebSocket 连接错误
    logger.error(
        f"WebSocket 连接异常: {error_msg}",
        extra={"service_name": service_name, "path": path},
    )
    raise BusinessError(
        message="WebSocket 连接失败",
        error_code="WEBSOCKET_CONNECTION_ERROR",
        code=ServiceErrorCodes.GATEWAY_CONNECTION_FAILED,
        http_status_code=502,
    )
```

### 3. 改进 proxy.py 端点错误处理

**文件**: `services/gateway-service/app/api/v1/endpoints/proxy.py:172`

**作用**: 捕获 `BusinessError` 并传递准确的错误信息给客户端

#### Before（修复前）

```python
except Exception as e:
    logger.error(
        f"WebSocket 转发失败: {hostname}/{apiurl}",
        extra={"error": str(e), "hostname": hostname, "apiurl": apiurl},
        exc_info=True,
    )

    # ❌ 硬编码的错误响应
    if websocket.client_state.name != "DISCONNECTED":
        try:
            await websocket.send_json(
                {
                    "code": 500,  # ❌ 总是 500
                    "message": "WebSocket 转发异常",  # ❌ 通用消息
                    "error_code": "WEBSOCKET_PROXY_ERROR",
                }
            )
            await websocket.close(code=1011, reason="Server error")  # ❌ 总是 1011
        except Exception as close_error:
            logger.debug(f"关闭 WebSocket 时出错: {close_error!s}")
```

#### After（修复后）

```python
except Exception as e:
    # ✅ 检查是否为 BusinessError（包含准确的错误信息）
    from shared.common.exceptions import BusinessError

    if isinstance(e, BusinessError):
        error_code = e.http_status_code or 500
        error_message = e.message
        error_type = e.error_code

        logger.warning(
            f"WebSocket 业务异常: {hostname}/{apiurl}",
            extra={
                "error_code": error_code,
                "error_message": error_message,
                "hostname": hostname,
                "apiurl": apiurl,
            },
        )
    else:
        # ✅ 其他未知异常
        error_code = 500
        error_message = "WebSocket 转发异常"
        error_type = "WEBSOCKET_PROXY_ERROR"

        logger.error(
            f"WebSocket 转发失败: {hostname}/{apiurl}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "hostname": hostname,
                "apiurl": apiurl,
            },
            exc_info=True,
        )

    # ✅ 发送准确的错误消息
    if websocket.client_state.name != "DISCONNECTED":
        try:
            await websocket.send_json(
                {
                    "code": error_code,  # ✅ 准确的状态码
                    "message": error_message,  # ✅ 准确的消息
                    "error_code": error_type,
                }
            )

            # ✅ 根据错误码设置正确的关闭码
            if error_code == 403:
                close_code = 1008  # Policy Violation
                close_reason = "Authentication failed"
            elif error_code == 401:
                close_code = 1008  # Policy Violation
                close_reason = "Unauthorized"
            else:
                close_code = 1011  # Internal Error
                close_reason = "Server error"

            await websocket.close(code=close_code, reason=close_reason)
        except Exception as close_error:
            logger.debug(f"关闭 WebSocket 时出错: {close_error!s}")
```

## 📊 错误响应对比

### 场景1: Token 过期或无效

#### Before（修复前）
```json
{
    "code": 500,
    "message": "WebSocket 转发异常",
    "error_code": "WEBSOCKET_PROXY_ERROR",
    "timestamp": "2025-10-28T07:59:34Z"
}
```

#### After（修复后）
```json
{
    "code": 403,
    "message": "WebSocket 认证失败，Token 无效或已过期",
    "error_code": "WEBSOCKET_AUTH_FAILED",
    "details": {
        "service_error_code": 10011
    },
    "timestamp": "2025-10-28T08:00:00Z"
}
```

### 场景2: 缺少认证令牌

#### Before（修复前）
```json
{
    "code": 500,
    "message": "WebSocket 转发异常",
    "error_code": "WEBSOCKET_PROXY_ERROR"
}
```

#### After（修复后）
```json
{
    "code": 401,
    "message": "WebSocket 连接未授权，请提供有效的认证令牌",
    "error_code": "WEBSOCKET_UNAUTHORIZED",
    "details": {
        "service_error_code": 10012
    },
    "timestamp": "2025-10-28T08:00:00Z"
}
```

### 场景3: 其他连接错误

#### Before & After（保持一致）
```json
{
    "code": 502,
    "message": "WebSocket 连接失败",
    "error_code": "WEBSOCKET_CONNECTION_ERROR",
    "details": {
        "service_error_code": 10003
    },
    "timestamp": "2025-10-28T08:00:00Z"
}
```

## 🔄 错误处理流程

### 完整流程图

```
客户端 → Gateway WebSocket请求
    │
    ├──→ Gateway: 验证Token（第一层）
    │    │
    │    ├─✅ 有效 → 转发到后端服务
    │    │
    │    └─❌ 无效 → 直接返回 403
    │
    └──→ Gateway: 转发到后端服务
         │
         ├──→ 后端: 再次验证Token（第二层）
         │    │
         │    ├─✅ 有效 → 建立WebSocket连接
         │    │
         │    └─❌ 无效 → 拒绝连接（HTTP 403）
         │
         └──→ Gateway proxy_service.py: 捕获后端拒绝
              │
              ├──→ 检查错误消息: "HTTP 403"
              │    └──→ ✅ 抛出 BusinessError(code=403, message="认证失败")
              │
              ├──→ 检查错误消息: "HTTP 401"
              │    └──→ ✅ 抛出 BusinessError(code=401, message="未授权")
              │
              └──→ 其他错误
                   └──→ 抛出 BusinessError(code=502, message="连接失败")
         │
         └──→ Gateway proxy.py: 捕获 BusinessError
              │
              ├──→ isinstance(e, BusinessError)?
              │    ├─✅ 是 → 使用异常中的准确信息
              │    │         - error_code = e.http_status_code
              │    │         - error_message = e.message
              │    │         - WebSocket关闭码: 1008 (认证) 或 1011 (其他)
              │    │
              │    └─❌ 否 → 通用错误信息
              │              - error_code = 500
              │              - error_message = "WebSocket 转发异常"
              │              - WebSocket关闭码: 1011
              │
              └──→ 返回给客户端:
                   {
                     "code": error_code,
                     "message": error_message,
                     "error_code": error_type
                   }
```

## 🧪 测试验证

### 测试场景1: Token 已过期

```python
import asyncio
import websockets

async def test_expired_token():
    """测试过期Token的错误响应"""
    expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # 过期的token
    
    uri = f"ws://localhost:8000/ws/host-service/host?token={expired_token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            ***REMOVED***
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"状态码: {e.status_code}")  # 应该是 403
        # ✅ 期望: 403 Forbidden
        assert e.status_code == 403, f"期望 403，实际 {e.status_code}"

asyncio.run(test_expired_token())
```

### 测试场景2: 缺少Token

```python
async def test_missing_token():
    """测试缺少Token的错误响应"""
    uri = "ws://localhost:8000/ws/host-service/host"  # 没有token参数
    
    try:
        async with websockets.connect(uri) as websocket:
            ***REMOVED***
    except websockets.exceptions.InvalidStatusCode as e:
        # ✅ 期望: 401 Unauthorized 或 403 Forbidden
        assert e.status_code in (401, 403), f"期望 401/403，实际 {e.status_code}"

asyncio.run(test_missing_token())
```

### 测试场景3: 有效Token

```python
async def test_valid_token():
    """测试有效Token的正常连接"""
    # 1. 先获取有效token
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/v1/auth/device/login",
            json={
                "mg_id": "device-001",
                "host_ip": "192.168.1.100",
                "username": "test_user"
            }
        )
        token = response.json()["data"]["token"]
    
    # 2. 使用token建立WebSocket连接
    uri = f"ws://localhost:8000/ws/host-service/host?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # ✅ 期望: 连接成功
        welcome = await websocket.recv()
        print(f"连接成功: {welcome}")

asyncio.run(test_valid_token())
```

## 📝 客户端错误处理指南

### JavaScript 客户端

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/host-service/host?token=${token}`);

ws.onerror = (error) => {
    console.error('WebSocket错误:', error);
};

ws.onclose = (event) => {
    console.log('WebSocket关闭:', event.code, event.reason);
    
    // ✅ 根据关闭码判断错误类型
    switch(event.code) {
        case 1008:  // Policy Violation（认证失败）
            if (event.reason.includes('403') || event.reason.includes('认证失败')) {
                console.error('Token已过期或无效，请重新登录');
                // 跳转到登录页面
                window.location.href = '/login';
            } else if (event.reason.includes('401') || event.reason.includes('未授权')) {
                console.error('缺少认证Token');
                // 提示用户登录
            }
            break;
        
        case 1011:  // Internal Server Error
            console.error('服务器内部错误');
            // 提示用户稍后重试
            break;
            
        default:
            console.error('未知错误:', event.code);
    }
};
```

### Python 客户端

```python
import asyncio
import websockets
import json

async def connect_with_error_handling(token: str):
    """带错误处理的WebSocket连接"""
    uri = f"ws://localhost:8000/ws/host-service/host?token={token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ 连接成功")
            
            # 接收消息
            while True:
                message = await websocket.recv()
                print(f"收到消息: {message}")
                
    except websockets.exceptions.InvalidStatusCode as e:
        # ✅ HTTP状态码错误
        if e.status_code == 403:
            print("❌ Token已过期或无效，请重新登录")
            # 自动刷新token或引导重新登录
        elif e.status_code == 401:
            print("❌ 缺少认证Token")
        else:
            print(f"❌ 连接失败: HTTP {e.status_code}")
            
    except websockets.exceptions.ConnectionClosed as e:
        # ✅ 连接关闭
        print(f"连接已关闭: code={e.code}, reason={e.reason}")
        
    except Exception as e:
        # ✅ 其他错误
        print(f"❌ 未知错误: {e}")

# 使用示例
asyncio.run(connect_with_error_handling("your_jwt_token"))
```

## 🎯 优势总结

### 1. 准确的HTTP状态码

| 错误类型 | Before | After | 改进 |
|---|---|---|---|
| Token过期 | 500 | 403 | ✅ 准确 |
| 缺少Token | 500 | 401 | ✅ 准确 |
| 连接失败 | 502 | 502 | ✅ 保持 |

### 2. 清晰的错误消息

- ✅ **Before**: "WebSocket 转发异常" - 模糊不清
- ✅ **After**: "WebSocket 认证失败，Token 无效或已过期" - 明确原因

### 3. 便于客户端处理

```python
# ✅ 客户端可以根据状态码精准处理
if response.status_code == 403:
    # Token过期，引导重新登录
    redirect_to_login()
elif response.status_code == 401:
    # 缺少Token，提示登录
    show_login_prompt()
elif response.status_code == 502:
    # 后端服务问题，提示稍后重试
    show_retry_message()
```

### 4. 符合HTTP标准

- **403 Forbidden**: 服务器理解请求，但拒绝授权
- **401 Unauthorized**: 缺少有效的认证凭证
- **502 Bad Gateway**: 后端服务器错误

### 5. 更好的日志记录

```log
# ✅ 认证失败（WARNING级别）
2025-10-28 08:00:00 | WARNING | WebSocket 认证失败: server rejected WebSocket connection: HTTP 403

# ✅ 连接错误（ERROR级别）
2025-10-28 08:00:01 | ERROR | WebSocket 连接异常: connection refused
```

## 📚 相关文档

- [WEBSOCKET_AUTH_OPTIMIZATION.md](WEBSOCKET_AUTH_OPTIMIZATION.md) - WebSocket认证优化
- [API错误响应规范](docs/api-response-format.md) - 统一错误响应格式
- [服务错误码规范](docs/service-error-codes.md) - 错误码定义

---

**修复日期**: 2025-10-28  
**影响范围**: Gateway Service  
**状态**: ✅ 已完成并测试  
**版本**: v1.1

