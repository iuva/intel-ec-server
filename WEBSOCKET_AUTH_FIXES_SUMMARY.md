# WebSocket 认证令牌问题 - 修复总结

## 🎯 问题描述

您遇到的问题是 WebSocket 连接时收到 **"WebSocket 连接缺少认证令牌"** 警告，最终导致 403 Forbidden 错误，虽然您在 `Authorization` 头中传入了 token。

## 🔍 根本原因

问题分为**两个层面**：

### 第一层：HTTP 中间件层 (AuthMiddleware)
- **原因**: `/ws/` 路径未被识别为应该在中间件级别允许通过的 WebSocket 路由
- **结果**: WebSocket 升级请求在到达路由处理器前就被中间件拒绝

### 第二层：WebSocket 路由层 (websocket_proxy)
- **原因**: Authorization 头格式检查严格，缺少任何 "Bearer " 前缀都会导致 token 提取失败
- **结果**: 即使通过了中间件，token 也无法被正确提取

## ✅ 已应用的修复

### 修复 1: AuthMiddleware 添加 WebSocket 路由处理

**文件**: `services/gateway-service/app/middleware/auth_middleware.py`

**更改内容**:
```python
class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        
        # ... existing code ...
        
        # ✅ 新增：WebSocket 路由前缀配置
        self.websocket_prefixes = {
            "/api/v1/ws/",
            "/ws/",
        }
    
    async def dispatch(self, request: Request, call_next):
        # ...
        
        # ✅ 新增：WebSocket 路由特殊处理
        is_websocket = self._is_websocket_path(request.url.path)
        if is_websocket:
            logger.info("WebSocket 路由，允许通过中间件")
            return await call_next(request)
        
        # ... 继续处理非 WebSocket 请求 ...
    
    def _is_websocket_path(self, path: str) -> bool:
        """检查是否为 WebSocket 路由路径 - 新增方法"""
        clean_path = path.split("?")[0]
        for prefix in self.websocket_prefixes:
            if clean_path.startswith(prefix):
                return True
        return False
```

**作用**:
- 允许 `/ws/` 和 `/api/v1/ws/` 路径通过 HTTP 中间件
- WebSocket 升级请求可以正常进行
- 具体的认证在路由级别进行，而不是中间件级别

### 修复 2: websocket_proxy 改进 Token 提取日志

**文件**: `services/gateway-service/app/api/v1/endpoints/proxy.py`

**更改内容**:
- 添加详细的 DEBUG 日志记录 token 提取过程
- 当 Authorization 头格式不正确时显示警告
- 在最终无法找到 token 时提供更详细的信息（列出所有可用的头）

**日志改进前后对比**:

```
❌ 之前（日志不足）:
WARNING: WebSocket 连接缺少认证令牌

✅ 之后（详细日志）:
DEBUG: 从查询参数成功提取 token
    或者
DEBUG: 检查 Authorization 头
    auth_header_present: true
    auth_header_prefix: "Bearer eyJhbGciOi..."
DEBUG: 从 Authorization 头成功提取 token

或者

WARNING: Authorization 头格式不正确（缺少 Bearer 前缀）
    expected_format: "Bearer <token>"
    got: "eyJhbGciOi..."
```

## 🧪 验证修复

### 快速测试

```bash
# 1. 进入项目目录
cd /Users/chiyeming/KiroProjects/intel_ec_ms

# 2. 运行完整的 WebSocket 测试套件
python test_websocket_correct.py

# 3. 查看测试输出
```

### 手动测试

```bash
# 获取 token
TOKEN=$(curl -X POST http://localhost:8001/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","***REMOVED***word":"admin@123"}' \
  | jq -r '.data.access_token')

echo "Token: ${TOKEN:0:50}..."

# 使用 websockets 库测试（Python）
python -c "
import asyncio, websockets, json

async def test():
    headers = {'Authorization': f'Bearer {os.environ.get(\"TOKEN\")}'}
    async with websockets.connect('ws://localhost:8000/api/v1/ws/host/agent/agent-123', extra_headers=headers) as ws:
        print('✅ 连接成功!')

asyncio.run(test())
"
```

## 📊 修复影响范围

| 文件 | 修改类型 | 影响 |
|---|---|---|
| `auth_middleware.py` | 新增方法 + 逻辑修改 | 所有 WebSocket 连接 |
| `proxy.py` | 增强日志 | 调试和监控 |
| `test_websocket_correct.py` | 完全重写 | 测试和验证 |

## 🐛 常见错误排查

### 错误 1: "缺少认证令牌"

**原因**: Authorization 头格式错误

**检查方法**:
```python
# ❌ 错误
headers = {"Authorization": token}

# ✅ 正确
headers = {"Authorization": f"Bearer {token}"}  # 注意有空格！
```

**查看日志中的 "auth_header_prefix" 字段**:
- 如果显示 token 而不是 "Bearer ...", 说明缺少前缀
- 如果显示 "Bearer " 后面有 token，说明格式正确

### 错误 2: "403 Forbidden"

**原因**: WebSocket 升级前被 HTTP 中间件拒绝

**验证修复**:
检查 `auth_middleware.py` 中是否有 `websocket_prefixes` 和 `_is_websocket_path` 方法

### 错误 3: "认证令牌无效或已过期"

**原因**: token 确实无效

**解决**:
```bash
# 重新获取 token
curl -X POST http://localhost:8001/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","***REMOVED***word":"admin@123"}'
```

## 📋 检查清单

在使用这些修复前，请确保：

- [ ] 已更新 `auth_middleware.py` 添加 WebSocket 路由处理
- [ ] 已更新 `proxy.py` 添加详细日志
- [ ] 已运行 `test_websocket_correct.py` 进行验证
- [ ] Authorization 头格式正确: `Bearer <token>`
- [ ] 所有微服务已重启
- [ ] 查看日志确认 token 被正确提取

## 🎯 后续步骤

1. **立即验证**:
   ```bash
   python test_websocket_correct.py
   ```

2. **检查日志**:
   ```bash
   docker-compose logs gateway-service | grep -i websocket
   ```

3. **如果仍有问题**:
   - 检查 Authorization 头格式是否为 `Bearer <token>`
   - 确认 token 是否有效和未过期
   - 查看详细日志中的 `auth_header_prefix` 字段

## 📚 相关文档

- `WEBSOCKET_AUTH_DEBUG_GUIDE.md` - 详细的诊断指南
- `test_websocket_correct.py` - 完整的测试脚本
- `services/gateway-service/app/middleware/auth_middleware.py` - 修改后的中间件
- `services/gateway-service/app/api/v1/endpoints/proxy.py` - 修改后的代理路由

---

**修复时间**: 2025-10-28
**状态**: ✅ 修复完成
**测试状态**: 等待您的验证
**联系方式**: 查看文档中的问题排查部分

