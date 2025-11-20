# Intel EC 微服务项目 - 快速开始指南

## 🚀 快速开始

### 前置要求

确保你的系统已安装：

- Python 3.8.10
- Docker 20.10+
- Docker Compose v2.0+
- Git

### 步骤 1: 克隆项目（如果需要）

```bash
git clone <repository-url>
cd intel-cw-ms
```

### 步骤 2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置外部 MySQL 和 Redis 连接信息
# 必须配置以下项：
# - MYSQL_HOST（您的 MySQL 主机地址）
# - MYSQL_PORT（MySQL 端口，默认 3306）
# - MYSQL_USER（MySQL 用户名）
# - MYSQL_PASSWORD（MySQL 密码）
# - MYSQL_DATABASE（数据库名称，默认 intel_cw）
# - REDIS_HOST（您的 Redis 主机地址）
# - REDIS_PORT（Redis 端口，默认 6379）
# - REDIS_PASSWORD（Redis 密码，如果有）
# - JWT_SECRET_KEY（JWT 密钥，至少 32 个字符）
```

**重要提示**: 本项目使用外部 MySQL 和 Redis 服务，不会在 Docker Compose 中启动这些服务。请确保您已有可用的 MySQL 和 Redis 实例。详细配置说明请参考 [外部服务配置指南](./external-services-config.md)。

### 步骤 3: 安装 Python 依赖（本地开发）

```bash
# 创建虚拟环境
python3.8 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发工具（可选）
pip install ruff mypy black pytest pytest-asyncio pytest-cov
```

### 步骤 4: 准备外部服务

确保您的外部 MySQL 和 Redis 服务正在运行：

```bash
# 测试 MySQL 连接
mysql -h your_mysql_host -P 3306 -u your_username -p

# 测试 Redis 连接
redis-cli -h your_redis_host -p 6379 -a your_***REMOVED***word ping
```

创建项目数据库：

```sql
CREATE DATABASE IF NOT EXISTS intel_cw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 步骤 5: 启动基础设施服务

```bash
# 启动 Nacos 和 Jaeger（不包括 MySQL 和 Redis）
docker-compose up -d nacos jaeger

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f nacos jaeger
```

> **⚠️ Nacos 启动故障排查**:
>
> 如果 Nacos 启动失败并提示 JWT Token 相关错误（如 "the length of must great than or equal 32 bytes"），请检查：
>
> 1. **确保 `.env` 文件存在**并包含正确的 `NACOS_AUTH_TOKEN` 配置
> 2. **令牌必须是 Base64 编码**且长度至少 32 字节
> 3. **使用提供的脚本生成新令牌**：
>
>    ```bash
>    ./scripts/generate_nacos_token.sh
>    ```
>
> 4. **将生成的令牌添加到 `.env` 文件**：
>
>    ```bash
>    NACOS_AUTH_TOKEN=生成的Base64令牌
>    ```
>
> 5. **重启 Nacos 服务**：
>
>    ```bash
>    docker-compose restart nacos
>    ```

### 步骤 6: 等待服务就绪

```bash
# 等待 Nacos 就绪
curl http://localhost:8848/nacos/v1/console/health/readiness

# 访问 Jaeger UI
open http://localhost:16686
```

### 步骤 7: 本地启动微服务（非 Docker 方式）

> **💡 提示**: 本地启动适用于开发调试，生产环境建议使用 Docker Compose。

#### 前提条件

1. **确保已安装依赖**：

   ```bash
   # 在项目根目录
   pip install -r requirements.txt
   
   # 安装各服务的依赖
   pip install -r services/gateway-service/requirements.txt
   pip install -r services/auth-service/requirements.txt
   pip install -r services/host-service/requirements.txt
   ```

2. **配置环境变量**：
   确保 `.env` 文件已正确配置（参考步骤 2）

   > **💡 重要说明**：
   > - 代码会在启动时**自动加载** `.env` 文件到环境变量
   > - `.env` 文件中的值会被加载为环境变量
   > - 如果系统环境变量中已有同名变量，**不会覆盖**（系统环境变量优先级更高）
   > - 如果 `.env` 文件不存在或无法加载，会使用代码中的默认值

3. **确保基础设施服务已启动**：

   ```bash
   # 启动数据库和基础设施服务
   docker-compose up -d mariadb nacos jaeger
   ```

4. **配置数据库连接地址（重要）**：

   由于本地启动的服务需要连接到 Docker 中的数据库，需要在 `.env` 文件中配置正确的数据库主机地址：

   ```bash
   # macOS/Windows Docker Desktop
   MARIADB_HOST=host.docker.internal
   MARIADB_PORT=3306
   
   # Linux（使用 Docker 网关）
   MARIADB_HOST=172.17.0.1
   MARIADB_PORT=3306
   
   # Redis 配置（如果 Redis 在 Docker 中）
   REDIS_HOST=host.docker.internal  # macOS/Windows
   # 或
   REDIS_HOST=172.17.0.1  # Linux
   REDIS_PORT=6379
   ```

   > **💡 提示**：如果不设置 `MARIADB_HOST` 和 `REDIS_HOST`，代码会自动检测运行环境：
   > - 在 Docker 容器内：自动使用容器名（`mariadb`、`redis`）
   > - 在本地环境：默认使用 `localhost`（需要数据库也在本地）
   >
   > 如果数据库在 Docker 中，**必须**显式设置上述环境变量。

#### 启动 Gateway Service (端口 8000)

```bash
# 进入 Gateway Service 目录
cd services/gateway-service

# 启动服务（开发模式，支持热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或者指定环境变量
SERVICE_PORT=8000 GATEWAY_SERVICE_PORT=8000 \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **⚠️ 重要：AUTH_SERVICE_URL 配置**
>
> 本地运行 Gateway 时，默认的 `http://auth-service:8001` 仅在 Docker 网络可解析。  
> 请在 `.env` 中显式添加：
>
> ```bash
> AUTH_SERVICE_URL=http://localhost:8001
> ```
>
> 修改后重启 Gateway，令牌验证才能转发到本地运行的 Auth Service。

**访问地址**:

- API 文档: <http://localhost:8000/docs>
- 健康检查: <http://localhost:8000/health>
- 指标端点: <http://localhost:8000/metrics>

#### 启动 Auth Service (端口 8001)

```bash
# 打开新的终端，进入 Auth Service 目录
cd services/auth-service

# 启动服务（开发模式，支持热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 或者指定环境变量
SERVICE_PORT=8001 AUTH_SERVICE_PORT=8001 \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**访问地址**:

- API 文档: <http://localhost:8001/docs>
- 健康检查: <http://localhost:8001/health>
- 指标端点: <http://localhost:8001/metrics>

#### 启动 Host Service (端口 8003)

```bash
# 打开新的终端，进入 Host Service 目录
cd services/host-service

# 启动服务（开发模式，支持热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# 或者指定环境变量
SERVICE_PORT=8003 HOST_SERVICE_PORT=8003 \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

**访问地址**:

- API 文档: <http://localhost:8003/docs>
- 健康检查: <http://localhost:8003/health>
- 指标端点: <http://localhost:8003/metrics>

#### 启动所有服务（使用终端多窗口）

建议为每个服务打开一个独立的终端窗口，便于查看日志和调试：

```bash
# 终端 1: Gateway Service
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2: Auth Service
cd services/auth-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 终端 3: Host Service
cd services/host-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

#### 环境变量配置

如果需要覆盖 `.env` 文件中的配置，可以在启动命令前设置环境变量：

```bash
# Gateway Service 示例（macOS/Windows - 连接 Docker 中的数据库）
MARIADB_HOST=host.docker.internal \
MARIADB_PORT=3306 \
MARIADB_USER=intel_user \
MARIADB_PASSWORD=intel_***REMOVED*** \
MARIADB_DATABASE=intel_cw \
REDIS_HOST=host.docker.internal \
REDIS_PORT=6379 \
NACOS_SERVER_ADDR=http://localhost:8848 \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Linux 示例（使用 Docker 网关）
MARIADB_HOST=172.17.0.1 \
REDIS_HOST=172.17.0.1 \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**重要说明**：

- **macOS/Windows**: 使用 `host.docker.internal` 连接 Docker 中的数据库
- **Linux**: 使用 `172.17.0.1`（Docker 默认网关）连接 Docker 中的数据库
- **本地数据库**: 如果数据库在本地（非 Docker），使用 `localhost`

#### 启动顺序建议

1. **首先启动基础设施服务**：

   ```bash
   docker-compose up -d nacos jaeger
   ```

2. **然后依次启动微服务**（建议顺序）：
   - Auth Service（认证服务）
   - Host Service（主机服务）
   - Gateway Service（网关服务，依赖其他服务）

#### 验证服务启动

```bash
# 检查所有服务是否正常运行
curl http://localhost:8000/health  # Gateway
curl http://localhost:8001/health  # Auth
curl http://localhost:8003/health  # Host

# 检查服务是否注册到 Nacos
curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=gateway-service
curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=auth-service
curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=host-service
```

#### 数据库连接问题排查

如果本地启动时无法连接数据库，请检查：

1. **确认数据库在 Docker 中运行**：

   ```bash
   docker-compose ps mariadb
   ```

2. **检查 `.env` 配置**：

   ```bash
   # macOS/Windows
   grep MARIADB_HOST .env
   # 应该显示: MARIADB_HOST=host.docker.internal
   
   # Linux
   grep MARIADB_HOST .env
   # 应该显示: MARIADB_HOST=172.17.0.1
   ```

3. **测试数据库连接**：

   ```bash
   # macOS/Windows
   mysql -h host.docker.internal -P 3306 -u intel_user -p
   
   # Linux
   mysql -h 172.17.0.1 -P 3306 -u intel_user -p
   ```

4. **查看服务日志**：
   服务启动时会在日志中显示使用的数据库连接地址，检查是否正确。

#### 环境变量加载机制

> **💡 重要说明**：
>
> 本地启动时，代码会自动加载 `.env` 文件，环境变量读取优先级为：
>
> 1. **系统环境变量**（最高优先级）- 命令行设置或 `export` 的变量
> 2. **`.env` 文件**（自动加载）- 应用启动时自动加载项目根目录的 `.env` 文件
> 3. **代码默认值**（最低优先级）- 如果都没有设置，使用代码中的默认值
>
> 详细说明请参考 [基础设施配置指南](./01-infrastructure-config.md)。

#### 常用启动参数说明

- `--host 0.0.0.0`: 监听所有网络接口（允许外部访问）
- `--port 8000`: 指定服务端口
- `--reload`: 开发模式，代码修改后自动重启（生产环境不要使用）
- `--log-level info`: 设置日志级别（可选：debug, info, warning, error）
- `--workers 4`: 生产模式，启动多个工作进程（开发模式不使用）

#### 停止服务

按 `Ctrl+C` 停止服务，或者直接关闭终端窗口。

## 📊 服务访问地址

### 基础设施服务

- **MySQL**: 您的外部 MySQL 服务地址（在 .env 中配置）
- **Redis**: 您的外部 Redis 服务地址（在 .env 中配置）
- **Nacos Console**: <http://localhost:8848/nacos>
  - 用户名: nacos
  - 密码: nacos
- **Jaeger UI**: <http://localhost:16686>
  - 当前使用内存存储（重启后数据会丢失）
  - 详细说明：[Jaeger 内存存储配置](jaeger-memory-storage.md)

### 监控系统

- **Prometheus**: <http://localhost:9090>
  - 指标采集和查询
- **Grafana**: <http://localhost:3000>
  - 用户名: admin
  - 密码: ***REMOVED***
  - 详细说明：[Prometheus + Grafana 监控指南](prometheus-grafana-setup.md)

### 微服务

- **Gateway Service**: <http://localhost:8000>
- **Auth Service**: <http://localhost:8001>
- **Host Service**: <http://localhost:8003>

## 🛠️ 开发工作流

### 代码质量检查

```bash
# Ruff 代码检查
ruff check services/ shared/

# Ruff 自动修复
ruff check --fix services/ shared/

# MyPy 类型检查
mypy services/ shared/

# Black 代码格式化
black services/ shared/

# 运行所有检查
ruff check services/ shared/ && mypy services/ shared/ && black --check services/ shared/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=services --cov=shared --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

## 🐳 Docker 操作

### 构建服务镜像

```bash
# 构建所有服务
docker-compose build

# 构建特定服务
docker-compose build gateway-service

# 强制重新构建（不使用缓存）
docker-compose build --no-cache
```

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 启动特定服务
docker-compose up -d gateway-service

# 查看日志
docker-compose logs -f gateway-service
```

### 停止和清理

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 停止并删除镜像
docker-compose down --rmi all
```

## 📝 开发建议

### 目录结构规范

每个微服务遵循以下结构：

```
service-name/
├── app/
│   ├── __init__.py
│   ├── main.py              # 应用入口
│   ├── api/v1/              # API 接口
│   ├── core/                # 核心配置
│   ├── models/              # 数据模型
│   ├── schemas/             # Pydantic 模式
│   └── services/            # 业务逻辑
├── Dockerfile
└── requirements.txt
```

### 代码规范

1. **类型注解**: 所有函数必须有类型注解
2. **中文注释**: 函数级注释使用中文
3. **代码格式**: 遵循 Black 格式化规范
4. **导入顺序**: 标准库 → 第三方库 → 本地模块

### Git 工作流

```bash
# 创建功能分支
git checkout -b feature/task-2-shared-modules

# 提交代码
git add .
git commit -m "feat: 实现共享模块数据库连接管理"

# 推送到远程
git push origin feature/task-2-shared-modules
```

## 🔍 故障排查

### MySQL 连接失败

```bash
# 检查外部 MySQL 服务状态
mysql -h your_mysql_host -P 3306 -u your_username -p

# 检查 .env 配置是否正确
cat .env | grep MYSQL

# 查看服务日志中的连接错误
docker-compose logs gateway-service | grep -i mysql
```

**常见问题**:

- 主机地址配置错误（macOS/Windows 使用 `host.docker.internal`，Linux 使用 `172.17.0.1` 或实际IP）
- 防火墙阻止连接
- MySQL 用户权限不足

详细解决方案请参考 [外部服务配置指南](./external-services-config.md#故障排查)。

### Redis 连接失败

```bash
# 检查外部 Redis 服务状态
redis-cli -h your_redis_host -p 6379 -a your_***REMOVED***word ping

# 检查 .env 配置是否正确
cat .env | grep REDIS

# 查看服务日志中的连接错误
docker-compose logs gateway-service | grep -i redis
```

### Nacos 启动失败

```bash
# 检查 Nacos 日志
docker-compose logs nacos

# 重启 Nacos
docker-compose restart nacos

# 检查 Nacos 健康状态
curl http://localhost:8848/nacos/v1/console/health/readiness
```

### 端口冲突

```bash
# 检查端口占用
lsof -i :8848  # Nacos
lsof -i :16686 # Jaeger
lsof -i :8000  # Gateway Service
lsof -i :8001  # Auth Service
lsof -i :8003  # Host Service

# 修改 docker-compose.yml 中的端口映射
```

## 📚 相关文档

- [外部服务配置指南](./external-services-config.md) - **必读**：配置外部 MySQL 和 Redis
- [项目设置文档](./project-setup.md)
- [部署指南](./deployment-guide.md)
- [代码质量设置](./code-quality-setup.md)
- [设计文档](../.kiro/specs/python-microservice-project/design.md)
- [需求文档](../.kiro/specs/python-microservice-project/requirements.md)
- [任务列表](../.kiro/specs/python-microservice-project/tasks.md)

## 🎯 下一步

1. **实现共享模块**（任务 2）
   - 数据库连接管理
   - Redis 缓存管理
   - 统一响应格式
   - 认证和安全工具

2. **实现认证服务**（任务 3）
   - 用户模型
   - JWT 认证
   - 登录/注销功能

3. **实现其他微服务**（任务 4-6）
   - Admin Service
   - Host Service
   - Gateway Service

## 💡 提示

- 使用 `docker-compose logs -f` 实时查看日志
- 使用 `docker-compose exec <service> bash` 进入容器调试
- 定期运行代码质量检查确保代码规范
- 提交前运行测试确保功能正常

---

**文档版本**: 1.1.0
**最后更新**: 2025-10-31
