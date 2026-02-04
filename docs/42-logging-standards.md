# 日志系统规范

## 概述

本文档定义了项目日志系统的统一规范，包括日志级别使用标准、结构化日志格式、性能追踪和请求上下文管理。

## 技术架构

### 核心组件

1. **`shared/common/loguru_config.py`** - Loguru 日志配置模块
2. **`shared/utils/logging_utils.py`** - 共享日志工具函数
3. **`shared/middleware/request_context_middleware.py`** - 请求上下文中间件

### 日志流程

```
请求进入 → RequestContextMiddleware (生成 request_id)
        → 业务逻辑 (使用日志工具记录)
        → loguru patcher (自动注入请求上下文)
        → 日志输出 (控制台 + 文件)
```

## 日志级别规范

### 级别定义

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| **DEBUG** | 开发调试信息、详细流程追踪 | 数据库查询 SQL、请求参数详情 |
| **INFO** | 正常业务操作、重要流程节点 | 用户登录成功、主机创建完成 |
| **WARNING** | 异常但不影响功能的情况 | API 调用重试、缓存未命中 |
| **ERROR** | 需要处理的错误 | 数据库连接失败、外部服务超时 |
| **CRITICAL** | 系统不可用 | 服务启动失败、关键组件崩溃 |

### 使用示例

```python
from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# DEBUG: 仅在开发环境使用
logger.debug("处理请求参数", extra={"params": params})

# INFO: 正常业务操作
logger.info("用户登录成功", extra={"user_id": user_id, "username": username})

# WARNING: 异常但可恢复
logger.warning("缓存未命中，回退到数据库查询", extra={"cache_key": key})

# ERROR: 需要关注的错误
logger.error("数据库连接失败", extra={"error": str(e)}, exc_info=True)

# CRITICAL: 系统级错误
logger.critical("服务启动失败", extra={"reason": reason})
```

## 共享日志工具

### 导入方式

```python
from shared.utils.logging_utils import (
    log_operation_start,
    log_operation_completed,
    log_operation_failed,
    log_request_received,
    log_request_completed,
    log_db_query,
    log_external_api_call,
    timed_operation,
    log_websocket_connect,
    log_auth_success,
    log_service_startup,
)
```

### 操作日志

```python
# 记录操作开始
log_operation_start("创建用户", extra={"username": "admin"})

# 记录操作完成（带耗时）
log_operation_completed("创建用户", duration_ms=150.5, extra={"user_id": 123})

# 记录操作失败（默认包含完整堆栈信息）
log_operation_failed("创建用户", error=e, duration_ms=50.0)

# 如果不需要堆栈信息（如已知的业务错误）
log_operation_failed("创建用户", error=e, include_traceback=False)
```

### 通用错误日志

```python
from shared.utils.logging_utils import log_error, log_warning

# 记录错误（默认包含完整堆栈信息）
try:
    risky_operation()
except Exception as e:
    log_error("执行风险操作失败", error=e, extra={"user_id": 123})

# 记录警告
log_warning("配置值过大", extra={"config_key": "max_connections", "value": 10000})
```

> **注意**: 所有错误日志函数（`log_error`、`log_operation_failed`、`log_db_error`、`log_external_api_error`）
> 默认会打印完整的堆栈信息。如果不需要堆栈信息，可以设置 `include_traceback=False`。

### 请求日志

```python
# 记录请求接收
log_request_received("query_available_hosts", extra={"page": 1, "page_size": 20})

# 记录请求完成
log_request_completed("query_available_hosts", duration_ms=200.0, extra={"count": 50})
```

### 数据库日志

```python
# 记录数据库查询（自动根据耗时选择日志级别）
log_db_query("select", "users", duration_ms=15.5, rows_affected=10)   # DEBUG: 正常查询
log_db_query("select", "users", duration_ms=600.0, rows_affected=10)  # INFO: 较慢查询 (>500ms)
log_db_query("select", "users", duration_ms=1500.0, rows_affected=10) # WARNING: 慢查询 (>1s)

# 记录数据库错误（默认包含完整堆栈信息）
log_db_error("update", "users", error=e)
```

### 外部 API 日志

```python
# 记录外部 API 调用
log_external_api_call("POST", "http://api.example.com/users", status_code=200, duration_ms=150.0)

# 记录外部 API 错误（默认包含完整堆栈信息）
log_external_api_error("POST", "http://api.example.com/users", error=e, duration_ms=5000.0)
```

### 性能追踪

```python
# 异步性能追踪
async with timed_operation("数据库查询", logger) as ctx:
    result = await db.execute(query)
print(f"耗时: {ctx.elapsed_ms}ms")

# 同步性能追踪
with timed_operation_sync("数据处理", logger) as ctx:
    process_data(data)
```

### WebSocket 日志

```python
# 连接日志
log_websocket_connect(client_id="host_123", remote_addr="192.168.1.1")

# 断开日志
log_websocket_disconnect(client_id="host_123", reason="timeout")

# 消息日志
log_websocket_message(client_id="host_123", message_type="heartbeat", direction="recv")
```

### 认证日志

```python
# 认证成功
log_auth_success(user_id="123", username="admin", auth_type="login")

# 认证失败
log_auth_failure(reason="invalid_password", username="admin")
```

### 服务日志

```python
# 服务启动
log_service_startup("gateway-service", version="1.0.0", host="0.0.0.0", port=8000)

# 服务关闭
log_service_shutdown("gateway-service", reason="graceful_shutdown")
```

## 请求上下文

### 中间件配置

所有服务的 `main.py` 中已添加 `RequestContextMiddleware`：

```python
from shared.middleware.request_context_middleware import RequestContextMiddleware

# 添加到应用（在 UnifiedExceptionMiddleware 之后）
app.add_middleware(RequestContextMiddleware)
```

### 获取上下文信息

```python
from shared.middleware.request_context_middleware import (
    get_request_id,
    get_user_id,
    get_username,
    get_client_ip,
    get_request_context,
)

# 获取当前请求 ID
request_id = get_request_id()

# 获取当前用户
user_id = get_user_id()

# 获取完整上下文
context = get_request_context()
# 返回: {"request_id": "xxx", "user_id": "123", "path": "/api/v1/users", ...}
```

### 自动注入

`loguru_config.py` 中的 patcher 会自动将请求上下文注入到日志的 extra 字段中，无需手动添加。

## 日志格式

### 控制台输出格式

```
2025-01-07 10:30:45.123 INFO     [gateway-service] app.services.proxy:forward_request:278 - 转发请求到后端服务: GET http://host-service:8003/api/v1/host/hosts
额外信息:
{
  "request_id": "abc123def456",
  "service_name": "host",
  "method": "GET",
  "path": "hosts"
}
```

### 文件输出

- **普通日志**: `logs/{service_name}.log`
- **错误日志**: `logs/{service_name}_error.log`

### 日志轮转

- **轮转时间**: 每天午夜 (00:00)
- **保留时间**: 30 天
- **压缩格式**: zip

## 最佳实践

### 1. 使用结构化日志

```python
# ✅ 正确：使用 extra 字段
logger.info("用户登录成功", extra={
    "user_id": user_id,
    "username": username,
    "ip_address": ip,
    "login_method": "password"
})

# ❌ 错误：直接拼接字符串
logger.info(f"用户 {username}(ID: {user_id}) 从 {ip} 登录成功")
```

### 2. 避免过度日志

```python
# ❌ 错误：每次循环都记录
for item in items:
    logger.debug(f"处理项目: {item}")

# ✅ 正确：只记录开始和结束
logger.info("开始批量处理", extra={"count": len(items)})
for item in items:
    process(item)
logger.info("批量处理完成", extra={"count": len(items)})
```

### 3. 错误日志包含堆栈

```python
# ✅ 正确：包含堆栈信息
try:
    risky_operation()
except Exception as e:
    logger.error("操作失败", extra={"error": str(e)}, exc_info=True)
```

### 4. 敏感信息脱敏

```python
# ✅ 正确：脱敏 token
token_preview = token[:8] + "..." if len(token) > 8 else token
logger.info("验证令牌", extra={"token_preview": token_preview})

# ❌ 错误：记录完整 token
logger.info("验证令牌", extra={"token": token})
```

### 5. 使用适当的日志级别

```python
# ❌ 错误：业务错误使用 ERROR
if user_not_found:
    logger.error("用户不存在")  # 这是正常的业务情况

# ✅ 正确：业务错误使用 WARNING 或 INFO
if user_not_found:
    logger.warning("用户不存在", extra={"username": username})
```

## 环境变量配置

| 变量 | 说明 | 默认值 |
|-----|------|-------|
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DEBUG` | 启用 DEBUG 模式 | `false` |

### 动态调整日志级别

```python
from shared.common.loguru_config import set_log_level

# 运行时调整日志级别
set_log_level("DEBUG")
```

## 性能考虑

1. **DEBUG 日志**: 仅在开发环境启用，生产环境使用 INFO 及以上
2. **日志异步**: Loguru 默认异步写入，不阻塞主线程
3. **缓冲区**: 文件日志使用缓冲区，减少 I/O 操作
4. **轮转清理**: 自动清理旧日志，避免磁盘空间占用过大

## 更新历史

- **2025-01-07**: 初始版本
  - 创建 `shared/utils/logging_utils.py` 共享日志工具模块
  - 创建 `shared/middleware/request_context_middleware.py` 请求上下文中间件
  - 增强 `loguru_config.py` 添加请求上下文自动注入
  - 优化所有服务日志，清理不必要的 DEBUG 日志
  - 更新 host-service `logging_helpers.py` 重导出共享模块函数

