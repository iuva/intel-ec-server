# VNC Report 接口 401 错误修复

## 🐛 问题描述

调用 `/api/v1/host/vnc/report` 接口时返回 401 Unauthorized 错误。

## 🔍 问题分析

### 正确的接口路径

根据路由配置，VNC report 接口有两个：

1. **浏览器插件接口**（不需要认证）:
   - **路径**: `/api/v1/host/hosts/vnc/report`
   - **路由配置**: `browser_vnc.router` 注册到 `/hosts/vnc` 前缀
   - **认证**: Gateway 配置了 `/api/v1/host/hosts` 为浏览器插件路径，不需要认证

2. **Agent 接口**（需要认证）:
   - **路径**: `/api/v1/host/agent/vnc/report`
   - **路由配置**: `agent_report.router` 注册到 `/agent` 前缀
   - **认证**: 使用 `get_current_agent` 依赖注入，需要 JWT token

### 错误的路径

如果访问 `/api/v1/host/vnc/report`（缺少 `hosts` 或 `agent`），这个路径：
- **不存在**：没有对应的路由处理器
- **会被要求认证**：Gateway 不会识别为浏览器插件接口

## ✅ 解决方案

### 方案 1: 使用正确的路径（推荐）

**浏览器插件调用**:
```bash
# ✅ 正确：使用完整的浏览器插件路径
POST /api/v1/host/hosts/vnc/report
```

**Agent 调用**:
```bash
# ✅ 正确：使用 Agent 路径，需要提供 JWT token
POST /api/v1/host/agent/vnc/report
Authorization: Bearer <device_token>
```

### 方案 2: 检查 Gateway 日志

如果使用的是正确路径但仍然报 401，检查 Gateway 日志：

```bash
# 查看 Gateway 认证中间件日志
docker-compose logs gateway-service | grep -E "浏览器插件接口|路径不是公开路径|令牌验证"
```

**期望看到**:
```
浏览器插件接口，跳过认证检查
  path: /api/v1/host/hosts/vnc/report
  matched_prefix: /api/v1/host/hosts
```

**如果看到**:
```
路径不是公开路径，需要认证
  path: /api/v1/host/vnc/report
```
说明路径不正确，缺少 `hosts` 部分。

## 📋 路径对照表

| 接口类型 | 正确路径 | 错误路径 | 认证要求 |
|---------|---------|---------|---------|
| 浏览器插件 VNC Report | `/api/v1/host/hosts/vnc/report` | `/api/v1/host/vnc/report` | ❌ 不需要 |
| Agent VNC Report | `/api/v1/host/agent/vnc/report` | `/api/v1/host/vnc/report` | ✅ 需要 JWT token |
| 浏览器插件 VNC Connect | `/api/v1/host/hosts/vnc/connect` | `/api/v1/host/vnc/connect` | ❌ 不需要 |
| 浏览器插件可用主机列表 | `/api/v1/host/hosts/available` | `/api/v1/host/available` | ❌ 不需要 |

## 🔧 路由配置说明

### Host Service 路由配置

```python
# services/host-service/app/api/v1/__init__.py

# 浏览器插件路由
api_router.include_router(
    browser_hosts.router, 
    prefix="/hosts", 
    tags=["浏览器插件-主机管理"]
)
api_router.include_router(
    browser_vnc.router, 
    prefix="/hosts/vnc",  # ✅ 注意：前缀是 /hosts/vnc
    tags=["浏览器插件-VNC连接管理"]
)

# Agent 路由
api_router.include_router(
    agent_report.router, 
    prefix="/agent", 
    tags=["Agent-硬件信息上报"]
)
```

### Gateway 浏览器插件路径配置

```python
# services/gateway-service/app/middleware/auth_middleware.py

self.browser_plugin_prefixes = [
    "/api/v1/host/hosts",  # ✅ 浏览器插件路径前缀
]
```

## 🧪 测试验证

### 测试 1: 浏览器插件接口（不需要认证）

```bash
# ✅ 正确路径
curl -X POST http://localhost:8000/api/v1/host/hosts/vnc/report \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123",
    "tc_id": "test_001",
    "cycle_name": "cycle_1",
    "user_name": "test_user",
    "host_id": "456",
    "connection_status": "success",
    "connection_time": "2025-01-30T10:00:00Z"
  }'
```

**期望响应**: 200 OK（不需要认证）

### 测试 2: Agent 接口（需要认证）

```bash
# ✅ 正确路径，需要 JWT token
curl -X POST http://localhost:8000/api/v1/host/agent/vnc/report \
  -H "Authorization: Bearer <device_token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**期望响应**: 200 OK（需要有效的 JWT token）

### 测试 3: 错误路径（会报 401 或 404）

```bash
# ❌ 错误路径（缺少 hosts）
curl -X POST http://localhost:8000/api/v1/host/vnc/report \
  -H "Content-Type: application/json" \
  -d '{}'
```

**期望响应**: 401 Unauthorized 或 404 Not Found

## 📋 检查清单

- [ ] 确认使用的是正确的路径 `/api/v1/host/hosts/vnc/report`
- [ ] 如果是浏览器插件调用，确认路径包含 `hosts`
- [ ] 如果是 Agent 调用，确认路径是 `/api/v1/host/agent/vnc/report` 并提供 JWT token
- [ ] 检查 Gateway 日志，确认路径是否被识别为浏览器插件接口
- [ ] 确认 Host Service 路由配置正确

## 🔗 相关文件

- `services/host-service/app/api/v1/__init__.py` - 路由配置
- `services/host-service/app/api/v1/endpoints/browser_vnc.py` - 浏览器插件 VNC 接口
- `services/host-service/app/api/v1/endpoints/agent_report.py` - Agent VNC 接口
- `services/gateway-service/app/middleware/auth_middleware.py` - Gateway 认证中间件

---

**最后更新**: 2025-01-30
**问题状态**: 路径错误导致 401
**解决方案**: 使用正确的路径 `/api/v1/host/hosts/vnc/report`

