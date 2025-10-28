# WebSocket 403 Forbidden 及 Auth-Service 404 问题诊断报告

## 问题历程

### 第一阶段 (已解决): WebSocket 403 Token验证失败
**症状**: WebSocket连接返回403，网关日志显示token验证失败

**根本原因**: `shared/common/websocket_auth.py`中的`verify_token_string()`函数提取token的user_id时返回None

**修复**:
✅ 改进websocket_auth.py中的token验证逻辑
✅ 添加详细DEBUG日志
✅ 显式检查user_id是否为None

### 第二阶段 (部分解决): Auth-Service 所有路由返回404
**症状**: 所有API端点返回404 Not Found，无论是登录还是introspect都失败

**根本原因**: UnifiedExceptionMiddleware在lifespan启动后被添加，触发了"Cannot add middleware after an application has started"错误

**修复尝试**:
✅ 将UnifiedExceptionMiddleware添加从lifespan.startup中移到FastAPI app创建后
✅ 修改所有4个service的main.py文件
✅ 更新exception_handler.py移除中间件添加代码

### 第三阶段 (未解决): 即使修复后路由仍返回404

**诡异现象**:
- 路由在app.routes中存在 (len(app.routes) == 13)
- /health 和 / 端点正常工作
- /api/v1/auth/* 所有路由返回404
- 新添加的 /test-route 也返回404
- 移除所有中间件后仍返回404

**诊断排查**:
✅ 验证路由正确注册 → 成功
✅ 检查PYTHONPATH和文件路径 → 正确
✅ 禁用所有中间件 → 仍然404
✅ 禁用setup_exception_handling → 仍然404
✅ Dockerfile文件复制 → 正确

**最可能的根本原因**:
1. **Lifespan启动过程中的异常被隐藏**: ServiceLifecycleManager.startup()可能发生异常但被silently caught
2. **FastAPI 应用状态被破坏**: 某个初始化步骤间接导致路由表损坏
3. **容器中的多个app对象**: uvicorn加载的app与我们调试的app不同

## 待诊断的代码区域

### 优先级1: shared/app/service_factory.py

关键代码（第243-246行）:
```python
exception_handlers = create_exception_handlers()
for exc_class, handler in exception_handlers.items():
    app.add_exception_handler(exc_class, handler)
```

**需要检查**:
- create_exception_handlers()函数的实现
- 异常处理器注册是否成功
- 是否有异常被catch-all中间件捕获

### 优先级2: shared/app/service_factory.py startup() 方法

整个startup()方法（第190-260行）可能在某处导致问题

### 优先级3: 日志系统初始化

shared/common/loguru_config.py configure_logger() 可能影响应用状态

## 建议的修复方案

### 方案A: 绕过 setup_exception_handling

在每个service的main.py中:
1. 直接注册异常处理器而不是调用setup_exception_handling
2. 跳过通过shared的全局配置

### 方案B: 修复 setup_exception_handling

诊断出具体是哪个异常处理器导致问题，移除或修复它

### 方案C: 简化 ServiceLifecycleManager

检查startup()方法是否有某个步骤导致应用破坏，可能需要从startup()中移除某些初始化

## 修改文件清单

**已修改**:
- ✅ shared/common/websocket_auth.py (WebSocket token验证改进)
- ✅ shared/app/exception_handler.py (移除中间件添加)
- ✅ services/auth-service/app/main.py (中间件添加时机修复)
- ✅ services/gateway-service/app/main.py (中间件添加时机修复)
- ✅ services/admin-service/app/main.py (中间件添加时机修复)
- ✅ services/host-service/app/main.py (中间件添加时机修复)

**临时修改（用于诊断）**:
- ⚠️ services/auth-service/app/main.py 第82行和第89行已注释（禁用middleware和setup_exception_handling）

## 立即行动项

1. **恢复被注释的代码**: 
   - 解注释 Prometheus中间件
   - 解注释 UnifiedExceptionMiddleware
   - 解注释 setup_exception_handling

2. **调试output级联添加**:
   - 在startup()中添加日志追踪每个初始化步骤
   - 在create_exception_handlers()中添加日志
   - 在app.add_exception_handler()后添加验证

3. **测试各service状态**:
   - gateway-service: 应该可以代理
   - auth-service: 应该能登录
   - admin-service和host-service: 依赖auth-service

## 参考日志

最后的HTTP请求日志:
```
2025-10-28 05:44:09
POST /api/v1/auth/admin/login
Response: 404 Not Found
Error Code: RESOURCE_NOT_FOUND
```

App启动日志（显示所有初始化成功）:
```
auth-service 启动中...
初始化数据库连接...
数据库连接初始化成功
初始化Jaeger追踪...
Jaeger 追踪初始化成功
初始化监控指标...
监控指标初始化成功
注册异常处理器...
异常处理器注册成功
初始化Nacos服务发现...
Nacos 服务注册和心跳检测启动成功
auth-service 启动成功
Application startup complete
```

## 下一步调试建议

如果issue继续存在，建议:
1. 添加通用日志来追踪所有route注册
2. 在FastAPI启动后dump所有routes
3. 在uvicorn启动时添加--log-level debug
4. 检查是否有其他FastAPI instance被创建

---

**最后更新**: 2025-10-28 05:44
**诊断阶段**: 第三阶段 (未完全解决)
**状态**: WebSocket认证改进已完成，auth-service 404问题需进一步诊断
