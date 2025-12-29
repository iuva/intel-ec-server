# CORS 错误诊断和解决方案

## 问题描述

前端访问 `/api/v1/host/hosts/vnc/report` 接口时出现 CORS 报错。

## 当前配置分析

### Gateway Service CORS 配置

Gateway 已经配置了 CORS 中间件（`services/gateway-service/app/main.py`）：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Host Service CORS 配置

Host Service 也配置了 CORS 中间件（`services/host-service/app/main.py`）：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 认证中间件 OPTIONS 处理

Gateway 的认证中间件已经处理了 OPTIONS 预检请求（`services/gateway-service/app/middleware/auth_middleware.py`）：

```python
# ✅ 处理 OPTIONS 预检请求（CORS 预检请求）
# OPTIONS 请求应该直接通过，由 CORS 中间件处理
if request.method == "OPTIONS":
    logger.debug(
        "OPTIONS 预检请求，跳过认证检查",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    return await call_next(request)
```

## 可能的原因

### 1. 中间件执行顺序问题

在 FastAPI 中，中间件的执行顺序是**后添加的先执行**（LIFO - Last In First Out）。

当前 Gateway 的中间件添加顺序：
1. CORS 中间件（第 142 行）
2. 认证中间件（第 151 行）
3. 统一异常处理中间件（第 159 行）

**执行顺序**（从外到内）：
1. 统一异常处理中间件（最先执行）
2. 认证中间件
3. CORS 中间件（最后执行）

**问题**：虽然认证中间件已经处理了 OPTIONS 请求，但如果 CORS 中间件在最后执行，它可能无法正确处理响应头。

### 2. CORS 中间件配置冲突

`allow_origins=["*"]` 和 `allow_credentials=True` 同时使用会导致 CORS 错误。

**原因**：当 `allow_credentials=True` 时，`allow_origins` 不能是 `["*"]`，必须指定具体的域名。

### 3. 响应头未正确设置

如果后端服务（Host Service）在响应中没有正确设置 CORS 头，即使 Gateway 设置了，也可能被覆盖。

## 解决方案

### 方案 1：修复 CORS 配置（推荐）

修改 Gateway 的 CORS 配置，明确指定允许的来源：

```python
# 从环境变量读取允许的来源（支持多个，用逗号分隔）
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
if "*" in allowed_origins and len(allowed_origins) == 1:
    # 如果只有 "*"，则不允许 credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # ⚠️ 修改：不允许 credentials
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 如果指定了具体域名，允许 credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### 方案 2：调整中间件顺序

将 CORS 中间件放在最后添加（最先执行）：

```python
# ✅ 先添加其他中间件
app.add_middleware(AuthMiddleware)
app.add_middleware(UnifiedExceptionMiddleware)

# ✅ 最后添加 CORS 中间件（确保最先执行）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # ⚠️ 如果使用 "*"，必须设为 False
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 方案 3：在代理服务中手动添加 CORS 头

在 `ProxyService` 中手动添加 CORS 响应头：

```python
# 在 proxy_service.py 的代理响应处理中添加
response_headers = dict(response.headers)
response_headers["Access-Control-Allow-Origin"] = "*"
response_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
response_headers["Access-Control-Allow-Headers"] = "*"
response_headers["Access-Control-Allow-Credentials"] = "false"
```

## 推荐解决方案

**推荐使用方案 1 + 方案 2 的组合**：

1. 修复 CORS 配置，解决 `allow_origins=["*"]` 和 `allow_credentials=True` 的冲突
2. 调整中间件顺序，确保 CORS 中间件最先执行

## 验证步骤

1. **检查浏览器控制台**：
   - 查看具体的 CORS 错误信息
   - 检查响应头中是否包含 `Access-Control-Allow-Origin`

2. **检查 OPTIONS 预检请求**：
   ```bash
   curl -X OPTIONS http://localhost:8000/api/v1/host/hosts/vnc/report \
     -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -v
   ```

3. **检查实际请求**：
   ```bash
   curl -X POST http://localhost:8000/api/v1/host/hosts/vnc/report \
     -H "Origin: http://localhost:3000" \
     -H "Content-Type: application/json" \
     -d '{"user_id":"123","tc_id":"test","cycle_name":"test","user_name":"test","host_id":"123","connection_status":"success","connection_time":"2025/01/30 10:00:00"}' \
     -v
   ```

## 环境变量配置

如果使用方案 1，可以在 `.env` 或 `docker-compose.yml` 中配置：

```bash
# 允许的来源（多个用逗号分隔）
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,https://yourdomain.com

# 或者允许所有来源（但不允许 credentials）
# CORS_ALLOWED_ORIGINS=*
```

## 相关文件

- `services/gateway-service/app/main.py` - Gateway CORS 配置
- `services/host-service/app/main.py` - Host Service CORS 配置
- `services/gateway-service/app/middleware/auth_middleware.py` - 认证中间件 OPTIONS 处理
- `services/gateway-service/app/services/proxy_service.py` - 代理服务

