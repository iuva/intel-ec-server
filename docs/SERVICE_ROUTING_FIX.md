# 网关服务路由修复文档 - 支持本地和 Docker 两种启动

## 🎯 问题分析

在本地启动网关服务时，出现以下错误：

```
转发请求: POST http://auth-service:8001/api/v1/device/login
HTTP 请求失败，1.0秒后重试
```

**根本原因**：
- 网关服务的服务路由硬编码为 Docker 主机名（`auth-service`, `admin-service`, `host-service`）
- 本地开发环境无法解析这些 Docker 容器名称
- 导致 HTTP 连接失败，请求被重试多次后最终返回 503 错误

## ✅ 解决方案

### 修改1：proxy_service.py - 支持环境变量配置

```python
def __init__(self):
    """初始化代理服务
    
    支持两种启动方式：
    1. Docker: 使用服务名（auth-service, admin-service, host-service）
    2. 本地开发: 使用 localhost + 端口
    """
    import os
    
    # 检测运行环境
    service_host_auth = os.getenv("SERVICE_HOST_AUTH", "auth-service")
    service_host_admin = os.getenv("SERVICE_HOST_ADMIN", "admin-service")
    service_host_host = os.getenv("SERVICE_HOST_HOST", "host-service")
    
    # 服务路由映射表
    self.service_routes = {
        "auth": f"http://{service_host_auth}:8001",
        "admin": f"http://{service_host_admin}:8002",
        "host": f"http://{service_host_host}:8003",
    }
```

### 修改2：start_services_local.sh - 本地启动脚本

```bash
# 本地开发特定配置：设置服务主机地址为 localhost
export SERVICE_HOST_AUTH="127.0.0.1"
export SERVICE_HOST_ADMIN="127.0.0.1"
export SERVICE_HOST_HOST="127.0.0.1"
```

### 修改3：start_services_local.bat - Windows 启动脚本

```batch
REM 本地开发特定配置：设置服务主机地址为 localhost
set "SERVICE_HOST_AUTH=127.0.0.1"
set "SERVICE_HOST_ADMIN=127.0.0.1"
set "SERVICE_HOST_HOST=127.0.0.1"
```

## 🏃 工作原理

### Docker 环境（生产）

```
docker-compose up
├─ 网关服务 (gateway-service:8000)
│  └─ SERVICE_HOST_AUTH = "auth-service" (默认)
│     转发: http://auth-service:8001
│
├─ 认证服务 (auth-service:8001)
│  └─ Docker 网络可以解析 auth-service
│
├─ 管理服务 (admin-service:8002)
│  └─ Docker 网络可以解析 admin-service
│
└─ 主机服务 (host-service:8003)
   └─ Docker 网络可以解析 host-service
```

### 本地开发环境

```
./scripts/start_services_local.sh gateway
├─ 网关服务 (localhost:8000)
│  └─ SERVICE_HOST_AUTH = "127.0.0.1" (启动脚本设置)
│     转发: http://127.0.0.1:8001
│
├─ 认证服务 (localhost:8001)
│  └─ 本地 Python 进程，可以通过 127.0.0.1 访问
│
├─ 管理服务 (localhost:8002)
│  └─ 本地 Python 进程，可以通过 127.0.0.1 访问
│
└─ 主机服务 (localhost:8003)
   └─ 本地 Python 进程，可以通过 127.0.0.1 访问
```

## 🚀 使用方法

### Docker 启动（生产环境）

```bash
# Docker Compose 自动使用 docker-compose.yml，无需设置任何环境变量
docker-compose up -d

# 网关自动连接到其他容器
# 访问: http://localhost:8000/api/v1/auth/device/login
```

### 本地启动（开发环境）

```bash
# 终端1: 启动认证服务
./scripts/start_services_local.sh auth

# 终端2: 启动管理服务
./scripts/start_services_local.sh admin

# 终端3: 启动主机服务
./scripts/start_services_local.sh host

# 终端4: 启动网关服务（启动脚本会自动设置 SERVICE_HOST_* = 127.0.0.1）
./scripts/start_services_local.sh gateway

# 现在可以正常访问网关 API
curl http://localhost:8000/api/v1/auth/device/login
```

### Windows 本地启动

```batch
REM 在 Command Prompt 中执行

REM 终端1: 启动认证服务
start_services_local.bat auth

REM 终端2: 启动管理服务
start_services_local.bat admin

REM 终端3: 启动主机服务
start_services_local.bat host

REM 终端4: 启动网关服务
start_services_local.bat gateway
```

## 🔧 环境变量配置

### 自动配置（推荐）

启动脚本会自动设置正确的环境变量：
- **本地开发**：`SERVICE_HOST_AUTH=127.0.0.1`
- **Docker**：使用默认值 `SERVICE_HOST_AUTH=auth-service`

### 手动配置

如果需要手动配置，可以在启动前设置：

```bash
# Linux/Mac
export SERVICE_HOST_AUTH="127.0.0.1"
export SERVICE_HOST_ADMIN="127.0.0.1"
export SERVICE_HOST_HOST="127.0.0.1"
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Windows
set SERVICE_HOST_AUTH=127.0.0.1
set SERVICE_HOST_ADMIN=127.0.0.1
set SERVICE_HOST_HOST=127.0.0.1
cd services\gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 验证方法

### 1. 查看服务启动日志

```
🔧 配置本地服务连接...
✓ 环境变量加载成功
  • SERVICE_HOST_AUTH: 127.0.0.1
  • SERVICE_HOST_ADMIN: 127.0.0.1
  • SERVICE_HOST_HOST: 127.0.0.1
```

### 2. 查看网关日志

```
服务路由配置: {'auth': 'http://127.0.0.1:8001', 'admin': 'http://127.0.0.1:8002', 'host': 'http://127.0.0.1:8003'}
```

### 3. 测试 API 请求

```bash
# 测试网关代理
curl -X POST http://localhost:8000/api/v1/auth/device/login \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test"}'

# 应该看到来自 auth-service 的响应，而不是连接超时错误
```

## ✨ 主要特性

| 特性 | Docker | 本地开发 |
|-----|--------|--------|
| 网关服务 | gateway-service:8000 | localhost:8000 |
| 认证服务 | http://auth-service:8001 | http://127.0.0.1:8001 |
| 管理服务 | http://admin-service:8002 | http://127.0.0.1:8002 |
| 主机服务 | http://host-service:8003 | http://127.0.0.1:8003 |
| 环境变量设置 | docker-compose.yml | 启动脚本自动设置 |

## 🛠️ 技术细节

### 为什么使用环境变量？

1. **灵活性**：支持多种部署场景
2. **易于维护**：不需要修改代码
3. **向后兼容**：Docker 使用默认值，无需改动
4. **开发友好**：启动脚本自动处理

### 默认值的作用

```python
service_host_auth = os.getenv("SERVICE_HOST_AUTH", "auth-service")
#                           ↓                        ↓
#                    环境变量名称              Docker 默认值
```

- 如果设置了环境变量，使用环境变量的值
- 如果没有设置，使用默认值 `auth-service`（Docker 兼容）

## 📋 检查清单

在启动本地服务前，确保：

- [ ] 所有后端服务都已停止（运行 `pkill -f uvicorn`）
- [ ] 虚拟环境已激活
- [ ] 使用启动脚本而不是直接运行 `uvicorn`
- [ ] 按照推荐顺序启动（auth → admin → host → gateway）
- [ ] 查看日志中是否显示了服务主机为 `127.0.0.1`

## 🚨 故障排查

### 网关无法连接到其他服务

```
HTTP 请求失败，1.0秒后重试
后端服务返回业务错误: auth
```

**解决步骤**：
1. 检查 `SERVICE_HOST_*` 环境变量是否设置为 `127.0.0.1`
2. 验证其他服务是否在对应端口运行（8001, 8002, 8003）
3. 查看网关日志，确认 `服务路由配置` 显示正确的主机地址

### Docker 启动失败

```
无法连接到 http://127.0.0.1:8001
```

**原因**：在 Docker 中使用了本地启动脚本设置的 `127.0.0.1`

**解决方案**：
- 使用 `docker-compose up` 启动（不使用启动脚本）
- 或者在 docker-compose.yml 中明确设置默认值

## 📝 更新历史

- **2025-10-20**: 初始实现
  - 添加环境变量支持到 proxy_service.py
  - 更新启动脚本自动配置本地环境
  - 支持 Mac/Linux 和 Windows

---

**最后更新**: 2025-10-20
**作用范围**: 本地开发和 Docker 生产环境
**兼容性**: ✅ 100% 向后兼容，无需修改 Docker 配置
