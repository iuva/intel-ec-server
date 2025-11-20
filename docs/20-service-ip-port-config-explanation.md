# SERVICE_IP 和 SERVICE_PORT 配置说明

## 🎯 为什么需要 SERVICE_IP 和 SERVICE_PORT？

### Nacos 的双重作用

Nacos 在微服务架构中有两个不同的作用：

#### 1. 服务发现（从 Nacos 获取其他服务的地址）✅ 已实现自动获取

**场景**：Gateway Service 需要调用 Auth Service

```python
# 从 Nacos 动态获取 auth-service 的地址
auth_url = await service_discovery.get_service_url("auth-service")
# 返回: http://172.20.0.101:8001（从 Nacos 自动获取）
```

**说明**：这个过程是**动态的**，不需要配置，代码会自动从 Nacos 获取。

#### 2. 服务注册（向 Nacos 注册自己的地址）⚠️ 需要 SERVICE_IP 和 SERVICE_PORT

**场景**：服务启动时，需要告诉 Nacos "我是谁，我在哪里"

```python
# 服务启动时，向 Nacos 注册自己
await nacos_manager.register_service(
    service_name="gateway-service",
    ip="172.20.0.100",  # ⚠️ 需要 SERVICE_IP
    port=8000,          # ⚠️ 需要 SERVICE_PORT
)
```

**说明**：这个过程需要**知道自己的地址**，因为其他服务需要从 Nacos 发现你的地址。

### 类比理解

```
服务发现 = 在"电话簿"中查找别人的电话号码（动态获取）
服务注册 = 把自己的电话号码写到"电话簿"里（需要自己的信息）
```

## 🌐 服务间调用专用变量

为了兼容 Docker 网络和本地开发环境，所有服务在调用彼此前需要通过以下变量构建后备地址：

| 变量 | 作用 | Docker 默认值 | 本地默认值 |
| --- | --- | --- | --- |
| `GATEWAY_SERVICE_IP` / `GATEWAY_SERVICE_PORT` | 指向网关（供 host/auth 调用） | `gateway-service:8000` | `127.0.0.1:8000` |
| `AUTH_SERVICE_IP` / `AUTH_SERVICE_PORT` | 指向认证服务（供 gateway/host 调用） | `auth-service:8001` | `127.0.0.1:8001` |
| `HOST_SERVICE_IP` / `HOST_SERVICE_PORT` | 指向主机服务（供 gateway 调用） | `host-service:8003` | `127.0.0.1:8003` |

- **本地开发**：脚本 `start_services_local.*` 会自动将这些变量设置为 `127.0.0.1`，无需手动修改。
- **Docker 环境**：在 `docker-compose.yml` 中将 `*_SERVICE_IP` 设置为对应的服务名（如 `auth-service`），即可通过 Docker DNS 互相访问。
- **优先级**：`*_SERVICE_IP` + `*_SERVICE_PORT` > 自动检测（Docker 服务名 / `127.0.0.1`）。

> 这些变量仅用于“如何访问其他服务”，与自身在 Nacos 中注册使用的 `SERVICE_IP`、`SERVICE_PORT` 互不影响。

## 🤖 自动检测功能（已实现）

### 当前实现的自动检测逻辑

项目已经实现了**智能自动检测**功能，同时兼容 Docker 和本地启动：

```python
# shared/utils/docker_detection.py
def resolve_service_ip() -> str:
    """解析服务自身 IP 地址（用于向 Nacos 注册）"""
    
    # 优先级1：环境变量 SERVICE_IP（如果设置了，直接使用）
    if os.getenv("SERVICE_IP"):
        return os.getenv("SERVICE_IP")
    
    # 优先级2：自动检测
    if is_running_in_docker():
        # Docker 环境：从网络接口自动获取容器 IP
        # 例如：172.20.0.100, 172.20.0.101 等
        return auto_detect_container_ip()
    else:
        # 本地环境：使用 127.0.0.1
        return "127.0.0.1"
```

### 配置优先级

```
优先级（从高到低）：
1. 环境变量 SERVICE_IP（如果设置了，直接使用）✅ 推荐
2. Docker 环境：自动从网络接口获取容器 IP ✅ 已实现
3. 本地环境：127.0.0.1 ✅ 默认值
```

## 📋 配置建议

### Docker 环境（推荐配置）

虽然代码可以自动检测，但为了**可靠性**，建议在 `docker-compose.yml` 中明确配置：

```yaml
services:
  gateway-service:
    environment:
      SERVICE_NAME: gateway-service
      SERVICE_PORT: 8000
      GATEWAY_SERVICE_PORT: 8000
      SERVICE_IP: 172.20.0.100  # ✅ 推荐：明确配置（对应 ipv4_address）
    networks:
      intel-network:
        ipv4_address: 172.20.0.100  # ✅ 必须：静态 IP 配置
```

**为什么推荐配置？**
- 自动检测可能在某些网络配置下失败
- 静态 IP 配置更加可靠和可预测
- 避免自动检测失败导致的警告日志

### 本地启动环境（可选配置）

**本地启动时**，代码会自动使用 `127.0.0.1`，**通常不需要配置**。

```bash
# .env 文件（可选，通常不需要）
SERVICE_IP=127.0.0.1  # 默认值，可以不写
GATEWAY_SERVICE_PORT=8000  # 需要配置，因为代码需要知道服务端口
```

**为什么本地启动通常不需要 SERVICE_IP？**
- 本地启动时，所有服务都在同一台机器上（127.0.0.1）
- 服务间调用可以通过端口映射访问
- Nacos 中注册为 127.0.0.1:8000 也是合理的

## 🔄 两种使用场景对比

### 场景对比表

| 场景 | SERVICE_IP 作用 | 是否必须 | 自动检测支持 |
|------|----------------|---------|-------------|
| **服务注册** | 告诉 Nacos "我的地址是 X.X.X.X:PORT" | ✅ 必须 | ✅ 已支持 |
| **服务发现** | 从 Nacos 获取其他服务地址 | ❌ 不需要 | ✅ 已实现 |

### 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                   服务启动流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 服务启动                                                  │
│     ↓                                                         │
│  2. 读取配置                                                  │
│     - SERVICE_IP（自动检测或环境变量）                        │
│     - SERVICE_PORT（环境变量）                               │
│     ↓                                                         │
│  3. 向 Nacos 注册自己                                        │
│     register_service(                                        │
│       service_name="gateway-service",                        │
│       ip=SERVICE_IP,        # ← 使用自动检测或配置的 IP      │
│       port=SERVICE_PORT      # ← 从环境变量读取              │
│     )                                                         │
│     ↓                                                         │
│  4. 其他服务可以从 Nacos 发现此服务                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   服务调用流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Gateway 需要调用 Auth Service                            │
│     ↓                                                         │
│  2. 从 Nacos 动态获取 Auth Service 地址                      │
│     auth_url = await discovery.get_service_url("auth-service")│
│     # 返回: http://172.20.0.101:8001（自动获取）            │
│     ↓                                                         │
│  3. 使用获取到的地址调用服务                                  │
│     response = await httpx.get(f"{auth_url}/api/v1/users")   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ 实际配置示例

### Docker Compose 配置（推荐）

```yaml
# docker-compose.yml
services:
  gateway-service:
    environment:
      # 服务基本信息（必须）
      SERVICE_NAME: gateway-service
      SERVICE_PORT: 8000
      GATEWAY_SERVICE_PORT: 8000
      
      # 服务注册 IP（推荐配置，代码也会自动检测）
      SERVICE_IP: 172.20.0.100  # ✅ 推荐：明确配置
      
      # 其他配置...
    networks:
      intel-network:
        ipv4_address: 172.20.0.100  # ✅ 必须：静态 IP
```

### 本地启动配置（可选）

```bash
# .env 文件（项目根目录）
# 本地启动时，通常只需要配置端口，IP 会自动使用 127.0.0.1

GATEWAY_SERVICE_PORT=8000  # ✅ 必须：代码需要知道服务端口
# SERVICE_IP=127.0.0.1     # ✅ 可选：默认值，可以不写

AUTH_SERVICE_PORT=8001     # ✅ 必须
# SERVICE_IP=127.0.0.1     # ✅ 可选：默认值

HOST_SERVICE_PORT=8003     # ✅ 必须
# SERVICE_IP=127.0.0.1     # ✅ 可选：默认值
```

## 📝 总结

### 为什么需要 SERVICE_IP 和 SERVICE_PORT？

**答案**：用于**服务注册**（告诉 Nacos "我是谁，我在哪里"），而不是服务发现（从 Nacos 获取其他服务地址）。

### 自动检测功能

- ✅ **已实现**：代码可以自动检测 Docker 容器 IP
- ✅ **已实现**：本地环境自动使用 127.0.0.1
- ✅ **推荐**：Docker 环境仍然建议配置 SERVICE_IP，确保可靠性

### 配置建议

| 环境 | SERVICE_IP 配置 | SERVICE_PORT 配置 | 说明 |
|------|----------------|-------------------|------|
| **Docker** | ✅ 推荐配置 | ✅ 必须配置 | 确保可靠性和可预测性 |
| **本地启动** | ❌ 通常不需要 | ✅ 必须配置 | 自动使用 127.0.0.1 |

### 关键理解

```
服务发现 ≠ 服务注册

服务发现：从 Nacos 获取其他服务地址（✅ 已自动实现）
服务注册：向 Nacos 注册自己的地址（⚠️ 需要 SERVICE_IP 和 SERVICE_PORT）
```

---

**最后更新**: 2025-11-03
**核心要点**: SERVICE_IP 和 SERVICE_PORT 用于服务注册，代码已支持自动检测，Docker 环境推荐明确配置

