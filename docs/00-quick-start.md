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

### 微服务（待实现后可用）

- **Gateway Service**: <http://localhost:8000>
- **Auth Service**: <http://localhost:8001>
- **Admin Service**: <http://localhost:8002>
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
lsof -i :8000  # Gateway
lsof -i :8001  # Auth Service

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

**文档版本**: 1.0.0
**最后更新**: 2025-10-10
