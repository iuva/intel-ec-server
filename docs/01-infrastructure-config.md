# 基础设施配置指南

## 📋 概述

本文档详细说明如何配置项目所需的外部基础设施服务，包括 MariaDB 数据库、Redis 缓存、Nacos 服务发现和 Jaeger 分布式追踪。

## 🗄️ 数据库配置

### MariaDB 配置

项目使用外部 MariaDB 10.11 数据库，需要在 `.env` 文件中配置连接信息。

#### 1. 创建 `.env` 文件

```bash
# 复制示例配置文件
cp .env.example .env
```

#### 2. 配置 MariaDB 连接信息

在 `.env` 文件中配置您的 MariaDB 连接信息：

```bash
# MariaDB 配置
MARIADB_HOST=your_mariadb_host    # MariaDB 主机地址
MARIADB_PORT=3306                 # MariaDB 端口
MARIADB_USER=your_username        # MariaDB 用户名
MARIADB_PASSWORD=your_***REMOVED***word    # MariaDB 密码
MARIADB_DATABASE=intel_cw         # 数据库名称

# MariaDB SSL/TLS 配置（可选）
MARIADB_SSL_ENABLED=false         # 是否启用 SSL 加密连接
MARIADB_SSL_CA=./infrastructure/mysql/ssl/ca-cert.pem  # CA 证书路径
MARIADB_SSL_CERT=./infrastructure/mysql/ssl/client-cert.pem  # 客户端证书路径
MARIADB_SSL_KEY=./infrastructure/mysql/ssl/client-key.pem    # 客户端私钥路径
MARIADB_SSL_VERIFY_CERT=true      # 是否验证服务器证书（生产环境建议 true）
MARIADB_SSL_VERIFY_IDENTITY=false # 是否验证服务器身份
```

#### 3. 主机地址配置说明

根据 MariaDB 的部署位置选择合适的主机地址：

**场景 1: MariaDB 运行在宿主机上**

- **macOS/Windows Docker Desktop**:

  ```bash
  MARIADB_HOST=host.docker.internal
  ```

- **Linux**:

  ```bash
  MARIADB_HOST=172.17.0.1  # Docker 默认网关
  # 或使用宿主机实际IP
  MARIADB_HOST=192.168.1.100
  ```

**场景 2: MariaDB 运行在远程服务器**

```bash
MARIADB_HOST=192.168.1.200  # 远程服务器IP
# 或
MARIADB_HOST=mariadb.example.com  # 域名
```

**场景 3: MariaDB 运行在 Docker 容器中（本地启动时）**

本地启动服务连接 Docker 中的数据库：

```bash
# macOS/Windows
MARIADB_HOST=host.docker.internal

# Linux
MARIADB_HOST=172.17.0.1
```

**场景 4: MariaDB 运行在 Docker 容器中（Docker 启动时）**

Docker 容器内启动服务时，使用容器名：

```bash
# Docker Compose 会自动使用容器名
MARIADB_HOST=mariadb  # 或通过环境变量覆盖
```

#### 4. 数据库初始化

创建项目数据库：

```sql
CREATE DATABASE IF NOT EXISTS intel_cw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

创建用户并授权（可选）：

```sql
-- 创建用户
CREATE USER 'intel_user'@'%' IDENTIFIED BY 'intel_***REMOVED***';

-- 授权
GRANT ALL PRIVILEGES ON intel_cw.* TO 'intel_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;
```

### Redis 配置

项目使用外部 Redis 服务作为缓存，配置方式与 MariaDB 相同。

#### 1. 配置 Redis 连接信息

在 `.env` 文件中配置：

```bash
# Redis 配置
REDIS_HOST=your_redis_host        # Redis 主机地址
REDIS_PORT=6379                   # Redis 端口
REDIS_PASSWORD=                   # Redis 密码（如果没有密码，留空）
REDIS_DB=0                        # Redis 数据库编号
REDIS_USERNAME=                   # Redis 用户名（可选）
```

#### 2. 主机地址配置说明

配置方式与 MariaDB 相同，根据 Redis 部署位置选择：

- **宿主机**: `host.docker.internal` (macOS/Windows) 或 `172.17.0.1` (Linux)
- **远程服务器**: 实际IP地址或域名
- **Docker 容器**: `redis`（容器内）或 `host.docker.internal`（本地启动）

## 🔧 服务发现配置

### Nacos 配置

Nacos 用于服务注册与发现，可以通过 Docker Compose 启动。

#### 1. 启动 Nacos

```bash
# 启动 Nacos 服务
docker-compose up -d nacos

# 验证 Nacos 是否正常运行
curl http://localhost:8848/nacos/v1/console/health/readiness
```

#### 2. 访问 Nacos 控制台

- **控制台地址**: <http://localhost:8848/nacos>
- **默认用户名**: `nacos`
- **默认密码**: `nacos`

#### 3. 配置 Nacos 连接

在 `.env` 文件中配置（可选，有默认值）：

```bash
# Nacos 配置
NACOS_SERVER_ADDR=http://localhost:8848  # 本地启动时
# 或
NACOS_SERVER_ADDR=http://nacos:8848      # Docker 容器内

NACOS_USERNAME=nacos
NACOS_PASSWORD=nacos
NACOS_NAMESPACE=public
NACOS_GROUP=DEFAULT_GROUP
```

#### 4. SERVICE_IP 和 SERVICE_PORT 配置说明

> **重要说明**: SERVICE_IP 和 SERVICE_PORT 用于**服务注册**（告诉 Nacos 自己的地址），而不是服务发现（从 Nacos 获取其他服务地址）。

**详细说明**: 请参考 [SERVICE_IP 和 SERVICE_PORT 配置说明文档](./20-service-ip-port-config-explanation.md)

**快速理解**:
- ✅ **服务发现**：代码已经自动实现，从 Nacos 动态获取其他服务地址
- ⚠️ **服务注册**：需要 SERVICE_IP 和 SERVICE_PORT，用于向 Nacos 注册自己的地址

**自动检测功能**:
- ✅ Docker 环境：代码会自动检测容器 IP（也可通过环境变量配置）
- ✅ 本地环境：自动使用 127.0.0.1

**推荐配置**:
- Docker 环境：在 `docker-compose.yml` 中明确配置 SERVICE_IP（确保可靠性）
- 本地启动：通常不需要配置 SERVICE_IP（自动使用 127.0.0.1）

## 📊 分布式追踪配置

### Jaeger 配置

Jaeger 用于分布式追踪，可以通过 Docker Compose 启动。

#### 1. 启动 Jaeger

```bash
# 启动 Jaeger 服务
docker-compose up -d jaeger

# 验证 Jaeger 是否正常运行
curl http://localhost:16686/api/services
```

#### 2. 访问 Jaeger UI

- **UI 地址**: <http://localhost:16686>
- 当前使用内存存储（重启后数据会丢失）

#### 3. 配置 Jaeger 连接

在 `.env` 文件中配置（可选）：

```bash
# Jaeger 配置
JAEGER_ENDPOINT=localhost:4317      # 本地启动时（gRPC）
# 或
JAEGER_ENDPOINT=jaeger:4317         # Docker 容器内（gRPC）
```

## 🔐 安全配置

### JWT 密钥配置

设置一个强密码作为 JWT 密钥（至少32个字符）：

```bash
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-min-32-chars
```

### Nacos 认证 Token（可选）

如果启用了 Nacos 认证，需要在 `.env` 文件中配置：

```bash
# 生成 Nacos Token（至少 32 字节的 Base64 编码字符串）
NACOS_AUTH_TOKEN=your-base64-encoded-token-here
```

使用脚本生成 Token：

```bash
./scripts/generate_token.sh
```

## 🔌 外部服务 API 配置

### 硬件服务 API 配置

Host Service 需要调用外部硬件服务 API，需要在 `.env` 文件中配置：

```bash
# 硬件服务 API 配置
HARDWARE_API_URL=http://hardware-service:8000
```

#### 配置说明

- **环境变量**: `HARDWARE_API_URL`
- **默认值**: `http://hardware-service:8000`
- **用途**: 用于调用外部硬件服务的 API 接口（新增/修改硬件配置）

#### 不同环境的配置

**本地开发环境**（服务运行在本地）：
```bash
HARDWARE_API_URL=http://localhost:8000
```

**Docker 环境**（服务运行在 Docker 容器中）：
```bash
HARDWARE_API_URL=http://hardware-service:8000
```

**生产环境**（使用实际的服务地址）：
```bash
HARDWARE_API_URL=https://hardware-api.example.com
```

#### Mock 模式（开发测试）

如果外部硬件服务不可用，可以启用 Mock 模式：

```bash
# 启用 Mock 模式（返回模拟数据，不实际调用外部接口）
USE_HARDWARE_MOCK=true
```

#### SSL 证书验证配置

如果外部硬件服务使用 HTTPS 且证书验证失败，可以配置 SSL 验证选项：

```bash
# HTTP 客户端 SSL 验证配置
HTTP_CLIENT_VERIFY_SSL=true   # 是否验证 SSL 证书（默认 true，生产环境建议启用）
```

**配置说明**：

- **环境变量**: `HTTP_CLIENT_VERIFY_SSL`
- **默认值**: `true`（启用 SSL 证书验证）
- **用途**: 控制 HTTP 客户端是否验证 HTTPS 请求的 SSL 证书

**不同环境的配置**：

**开发/测试环境**（跳过证书验证）：
```bash
# 跳过 SSL 证书验证（仅用于开发/测试环境）
HTTP_CLIENT_VERIFY_SSL=false
```

**生产环境**（启用证书验证）：
```bash
# 启用 SSL 证书验证（生产环境推荐）
HTTP_CLIENT_VERIFY_SSL=true
```

**注意事项**：

- ⚠️ **安全警告**：在生产环境中禁用 SSL 证书验证会降低安全性，建议仅在开发/测试环境使用
- 如果遇到 `certificate_verify_failed` 错误，优先检查证书配置，而不是禁用验证
- 对于自签名证书，可以考虑配置自定义 CA 证书（需要修改代码支持）

## ✅ 配置验证

### 验证数据库连接

```bash
# 测试 MariaDB 连接
mysql -h your_mariadb_host -P 3306 -u your_username -p

# 测试 Redis 连接
redis-cli -h your_redis_host -p 6379 -a your_***REMOVED***word ping
```

### 验证服务配置

使用项目提供的验证脚本：

```bash
# 验证所有配置
./scripts/verify_setup.sh

# 验证外部数据库连接
./scripts/verify_setup.sh
```

## 🐛 常见问题

### 问题 1: 本地启动无法连接 Docker 中的数据库

**症状**: 本地启动服务时提示数据库连接失败

**原因**: 本地环境无法解析 Docker 容器名

**解决方案**:

1. 在 `.env` 文件中设置正确的数据库主机地址：

   ```bash
   # macOS/Windows
   MARIADB_HOST=host.docker.internal
   
   # Linux
   MARIADB_HOST=172.17.0.1
   ```

2. 确保 Docker 容器正在运行：

   ```bash
   docker-compose ps mariadb
   ```

### 问题 2: Docker 容器内无法连接外部数据库

**症状**: Docker 容器内服务无法连接外部数据库

**原因**: 网络配置或防火墙问题

**解决方案**:

1. 检查防火墙规则
2. 确保数据库允许来自 Docker 网络的连接
3. 使用宿主机的实际IP地址而非 `localhost`

### 问题 3: Nacos 服务注册失败

**症状**: 服务无法注册到 Nacos

**原因**: Nacos 未启动或配置错误

**解决方案**:

1. 检查 Nacos 是否运行：

   ```bash
   docker-compose ps nacos
   ```

2. 检查 Nacos 健康状态：

   ```bash
   curl http://localhost:8848/nacos/v1/console/health/readiness
   ```

3. 检查 Nacos 配置是否正确

详细故障排除请参考 [Nacos 故障排除指南](./10-nacos-troubleshooting.md)。

## 📚 相关文档

- [快速开始指南](./00-quick-start.md) - 包含环境变量配置步骤
- [本地启动指南](./00-quick-start.md#步骤-7-本地启动微服务非-docker-方式) - 本地启动配置说明
- [Nacos 故障排除](./10-nacos-troubleshooting.md) - Nacos 常见问题
- [部署指南](./03-deployment-guide.md) - 生产环境配置

