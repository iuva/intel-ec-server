# 组件开关配置文档

## 🎯 概述

本项目提供了统一的组件开关配置，可以通过环境变量一键控制 Nacos、Jaeger、Prometheus 等组件的启用/关闭。

## 📋 支持的组件开关

| 组件 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| **Nacos** | `ENABLE_NACOS` | `true` | 服务发现和注册 |
| **Jaeger** | `ENABLE_JAEGER` | `true` | 分布式追踪 |
| **Prometheus** | `ENABLE_PROMETHEUS` | `true` | 监控指标收集 |

## 🔧 配置方式

### 方式1：.env 文件（推荐，本地开发）

在项目根目录创建 `.env` 文件（可参考 `.env.example`）：

```bash
# .env 文件
# 组件开关配置
ENABLE_NACOS=true
ENABLE_JAEGER=true
ENABLE_PROMETHEUS=true

# 或者禁用某个组件
# ENABLE_JAEGER=false
```

**说明**：
- `.env` 文件会在服务启动时自动加载
- 适用于本地开发和测试环境
- 不会被提交到 Git（已在 `.gitignore` 中）

### 方式2：docker-compose.yml（Docker 环境）

Docker Compose **会自动读取项目根目录的 `.env` 文件**，无需额外配置。

#### 方法A：使用 .env 文件（推荐）

在项目根目录的 `.env` 文件中配置：

```bash
# .env 文件
ENABLE_NACOS=true
ENABLE_JAEGER=true
ENABLE_PROMETHEUS=true
```

Docker Compose 会自动读取这些变量并传递给容器。

#### 方法B：在 docker-compose.yml 中直接设置

```yaml
# docker-compose.yml
services:
  gateway-service:
    environment:
      # 从 .env 文件读取，如果不存在则使用默认值
      ENABLE_NACOS: ${ENABLE_NACOS:-true}
      ENABLE_JAEGER: ${ENABLE_JAEGER:-true}
      ENABLE_PROMETHEUS: ${ENABLE_PROMETHEUS:-true}
      
  auth-service:
    environment:
      # 可以单独为某个服务设置不同的值
      ENABLE_NACOS: ${ENABLE_NACOS:-true}
      ENABLE_JAEGER: ${ENABLE_JAEGER:-false}  # 禁用 Jaeger
      ENABLE_PROMETHEUS: ${ENABLE_PROMETHEUS:-true}
```

**说明**：
- `${ENABLE_NACOS:-true}` 表示：如果 `.env` 文件中有 `ENABLE_NACOS`，使用该值；否则使用默认值 `true`
- Docker Compose 会自动读取项目根目录的 `.env` 文件
- 所有服务都会读取相同的 `.env` 文件配置

### 方式3：代码配置

在服务主文件中直接配置：

```python
from shared.app import ServiceConfig

# 创建配置时指定开关
config = ServiceConfig(
    service_name="my-service",
    enable_nacos=True,
    enable_jaeger=False,  # 禁用 Jaeger
    enable_prometheus=True,
)
```

## 📁 .env 文件配置示例

### 完整配置示例

创建项目根目录的 `.env` 文件：

```bash
# ==========================================
# 组件开关配置
# ==========================================
# Nacos 服务发现开关
ENABLE_NACOS=true

# Jaeger 分布式追踪开关
ENABLE_JAEGER=true

# Prometheus 监控指标开关
ENABLE_PROMETHEUS=true

# ==========================================
# 其他配置...
# ==========================================
```

### 快速禁用所有监控组件

```bash
# .env 文件
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false
```

### 仅启用 Nacos

```bash
# .env 文件
ENABLE_NACOS=true
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false
```

**注意**：`.env` 文件会在服务启动时自动加载，无需手动导入。

## 📝 环境变量值说明

支持以下值表示**启用**（不区分大小写）：
- `true` / `True` / `TRUE`
- `1`
- `yes` / `Yes` / `YES`
- `on` / `On` / `ON`
- `enabled` / `Enabled` / `ENABLED`

其他任何值都表示**禁用**。

## 🚀 使用示例

### 示例1：禁用所有监控组件（开发环境）

**方式A：使用 .env 文件**
```bash
# .env 文件
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false
```

**方式B：使用 .env 文件（Docker 环境）**
```bash
# .env 文件（Docker Compose 会自动读取）
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false
```

然后启动 Docker 服务：
```bash
docker-compose up -d
```

**效果**：
- ✅ 服务正常启动和运行
- ❌ 不注册到 Nacos
- ❌ 不发送追踪数据到 Jaeger
- ❌ 不收集 Prometheus 指标
- ❌ `/metrics` 端点不可用

### 示例2：仅启用 Nacos（最小化配置）

**方式A：使用 .env 文件**
```bash
# .env 文件
ENABLE_NACOS=true
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false
```

**方式B：使用 .env 文件（Docker 环境）**
```bash
# .env 文件
ENABLE_NACOS=true
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false
```

然后启动 Docker 服务：
```bash
docker-compose up -d
```

**效果**：
- ✅ 服务注册到 Nacos
- ❌ 不发送追踪数据
- ❌ 不收集监控指标

### 示例3：仅启用 Prometheus（监控场景）

**方式A：使用 .env 文件**
```bash
# .env 文件
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=true
```

**方式B：使用 .env 文件（Docker 环境）**
```bash
# .env 文件
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=true
```

然后启动 Docker 服务：
```bash
docker-compose up -d
```

**效果**：
- ✅ 收集 Prometheus 指标
- ✅ `/metrics` 端点可用
- ❌ 不注册到 Nacos
- ❌ 不发送追踪数据

## 🔍 验证配置

### 查看服务启动日志

服务启动时会输出组件状态：

```
✅ Prometheus 指标收集中间件已启用
✅ Prometheus metrics 路由已启用
Jaeger 追踪已禁用（ENABLE_JAEGER=false 或未配置端点）
Nacos 服务发现已禁用（ENABLE_NACOS=false）
```

### 检查端点

```bash
# 检查 Prometheus 指标端点（仅在启用时可用）
curl http://localhost:8000/metrics

# 检查健康检查端点（始终可用）
curl http://localhost:8000/health
```

### 检查 Nacos 注册

```bash
# 访问 Nacos 控制台
http://localhost:8848/nacos

# 查看服务列表（仅在启用 Nacos 时可见）
```

## ⚠️ 注意事项

### 1. 组件依赖关系

- **Grafana** 依赖 **Prometheus**：如果禁用 Prometheus，Grafana 将无法获取数据
- **服务发现** 依赖 **Nacos**：如果禁用 Nacos，Gateway 将无法动态发现服务

### 2. 性能影响

- **禁用 Jaeger**：减少追踪开销，提升性能
- **禁用 Prometheus**：减少指标收集开销，提升性能
- **禁用 Nacos**：无法动态服务发现，需使用静态配置

### 3. 生产环境建议

生产环境建议启用所有组件：
```yaml
ENABLE_NACOS: "true"
ENABLE_JAEGER: "true"
ENABLE_PROMETHEUS: "true"
```

### 4. 开发环境建议

开发环境可以禁用部分组件以提升性能：
```yaml
ENABLE_NACOS: "true"      # 保留服务发现
ENABLE_JAEGER: "false"    # 禁用追踪（可选）
ENABLE_PROMETHEUS: "true" # 保留监控
```

## 📚 相关文件

- [shared/app/service_factory.py](../shared/app/service_factory.py) - 服务配置和生命周期管理
- [shared/app/application.py](../shared/app/application.py) - FastAPI 应用创建
- [shared/utils/env_loader.py](../shared/utils/env_loader.py) - .env 文件加载工具
- [services/*/app/main.py](../services/) - 服务主文件

## 💡 快速开始

### 在 .env 文件中配置组件开关

1. **创建或编辑项目根目录的 `.env` 文件**：
   ```bash
   # 如果文件不存在，创建它
   touch .env
   ```

2. **添加组件开关配置**：
   ```bash
   # .env 文件内容
   # ==========================================
   # 组件开关配置
   # ==========================================
   # Nacos 服务发现开关（默认：启用）
   ENABLE_NACOS=true
   
   # Jaeger 分布式追踪开关（默认：启用）
   ENABLE_JAEGER=true
   
   # Prometheus 监控指标开关（默认：启用）
   ENABLE_PROMETHEUS=true
   ```

3. **启动服务**，配置会自动生效：
   ```bash
   # 服务启动时会自动加载 .env 文件
   python services/gateway-service/app/main.py
   ```

### .env 文件完整示例

```bash
# ==========================================
# 组件开关配置
# ==========================================
ENABLE_NACOS=true
ENABLE_JAEGER=true
ENABLE_PROMETHEUS=true

# ==========================================
# 服务配置
# ==========================================
GATEWAY_SERVICE_NAME=gateway-service
GATEWAY_SERVICE_PORT=8000
AUTH_SERVICE_NAME=auth-service
AUTH_SERVICE_PORT=8001

# ==========================================
# 数据库配置
# ==========================================
MARIADB_HOST=mariadb
MARIADB_PORT=3306
MARIADB_USER=intel_user
MARIADB_PASSWORD=intel_***REMOVED***
MARIADB_DATABASE=intel_cw

REDIS_HOST=redis
REDIS_PORT=6379

# ==========================================
# Nacos 配置
# ==========================================
NACOS_SERVER_ADDR=172.20.0.12:8848
NACOS_USERNAME=nacos
NACOS_PASSWORD=nacos

# ==========================================
# Jaeger 配置
# ==========================================
JAEGER_ENDPOINT=jaeger:4317

# ==========================================
# JWT 配置
# ==========================================
JWT_SECRET_KEY=your-secret-key-here
```

**注意**：
- **本地开发**：`.env` 文件会在服务启动时自动加载（通过 `ensure_env_loaded()`）
- **Docker 环境**：Docker Compose 会自动读取项目根目录的 `.env` 文件，并传递给容器
- 所有服务主文件（`services/*/app/main.py`）都会在启动时调用 `ensure_env_loaded()`
- `.env` 文件不会被提交到 Git（已在 `.gitignore` 中）

## 🐳 Docker 环境配置说明

### Docker Compose 自动读取 .env 文件

Docker Compose **默认会自动读取**项目根目录的 `.env` 文件，无需额外配置。

**工作原理**：
1. Docker Compose 启动时，会自动查找项目根目录的 `.env` 文件
2. 读取 `.env` 文件中的环境变量
3. 在 `docker-compose.yml` 中使用 `${VARIABLE:-default}` 语法引用这些变量
4. 将环境变量传递给容器

**示例**：

```bash
# .env 文件（项目根目录）
ENABLE_NACOS=true
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=true
```

```yaml
# docker-compose.yml（已配置，无需修改）
services:
  gateway-service:
    environment:
      # 从 .env 文件读取，如果不存在则使用默认值 true
      ENABLE_NACOS: ${ENABLE_NACOS:-true}
      ENABLE_JAEGER: ${ENABLE_JAEGER:-true}
      ENABLE_PROMETHEUS: ${ENABLE_PROMETHEUS:-true}
```

**验证 Docker 环境配置**：

```bash
# 1. 创建 .env 文件
echo "ENABLE_JAEGER=false" >> .env

# 2. 启动 Docker 服务
docker-compose up -d gateway-service

# 3. 查看容器环境变量（验证配置是否生效）
docker-compose exec gateway-service env | grep ENABLE

# 4. 查看服务日志（确认组件状态）
docker-compose logs gateway-service | grep -i "jaeger\|prometheus\|nacos"
```

**输出示例**：
```
ENABLE_NACOS=true
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=true
```

服务日志中会显示：
```
Jaeger 追踪已禁用（ENABLE_JAEGER=false 或未配置端点）
✅ Prometheus 指标收集中间件已启用
Nacos 服务发现已启用
```

## 🔄 更新历史

- **2025-01-29**: 初始版本，添加组件开关配置功能
- **核心特性**:
  - 支持环境变量配置
  - 支持代码配置
  - 默认启用所有组件
  - 完整的日志输出

