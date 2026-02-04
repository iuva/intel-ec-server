# Intel EC 微服务部署指南

## 概述

本文档提供了 Intel EC 微服务项目的完整部署指南，包括 Docker 容器化部署、服务管理脚本使用说明等。

## 部署架构

### 服务组件

#### 基础设施服务

- **Nacos 2.2.0**: 服务发现和配置中心，端口 8848（使用内置数据库）
- **Jaeger 1.54**: 分布式追踪系统，端口 16686 (UI)

#### 外部依赖服务

- **MySQL**: 使用您现有的 MySQL 服务（需要在 .env 中配置连接信息）
- **Redis**: 使用您现有的 Redis 服务（需要在 .env 中配置连接信息）

#### 微服务

- **Gateway Service**: API 网关，端口 8000
- **Auth Service**: 认证服务，端口 8001
- **Admin Service**: 管理服务，端口 8002
- **Host Service**: 主机服务，端口 8003

## Docker 镜像优化

### 多阶段构建

所有服务的 Dockerfile 都采用了多阶段构建策略，以优化镜像大小：

#### 阶段 1: 构建阶段

- 使用完整的构建工具（gcc, g++）
- 安装 Python 依赖到临时目录
- 不包含在最终镜像中

#### 阶段 2: 运行阶段

- 使用精简的基础镜像
- 只复制必要的运行时依赖
- 创建非 root 用户运行服务
- 配置健康检查

### 镜像大小对比

| 服务 | 优化前 | 优化后 | 减少 |
|------|--------|--------|------|
| Gateway Service | ~800MB | ~400MB | 50% |
| Auth Service | ~800MB | ~400MB | 50% |
| Host Service | ~800MB | ~400MB | 50% |

## 环境配置

### 环境变量

复制 `.env.example` 为 `.env` 并根据实际环境修改配置：

```bash
cp .env.example .env
```

### 关键配置项

#### 外部 MySQL 配置

```bash
# 配置您现有的 MySQL 服务连接信息
MYSQL_HOST=your_mysql_host          # MySQL 主机地址
MYSQL_PORT=3306                     # MySQL 端口
MYSQL_USER=your_username            # MySQL 用户名
MYSQL_PASSWORD=your_secure_password # MySQL 密码
MYSQL_DATABASE=intel_cw             # 数据库名称
```

**主机地址配置说明**:

- 宿主机服务（macOS/Windows）: `host.docker.internal`
- 宿主机服务（Linux）: `172.17.0.1` 或实际IP
- 远程服务器: 实际IP地址或域名

#### 外部 Redis 配置

```bash
# 配置您现有的 Redis 服务连接信息
REDIS_HOST=your_redis_host          # Redis 主机地址
REDIS_PORT=6379                     # Redis 端口
REDIS_PASSWORD=your_redis_password  # Redis 密码（如果有）
```

#### JWT 配置

```bash
JWT_SECRET_KEY=your_jwt_secret_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### 服务间调用配置

**用于服务间相互调用的地址配置**（与 `SERVICE_IP` 用于 Nacos 注册不同）：

```bash
# Gateway Service 配置（用于调用其他服务）
AUTH_SERVICE_IP=auth-service      # Docker 环境：使用服务名
AUTH_SERVICE_PORT=8001
HOST_SERVICE_IP=host-service      # Docker 环境：使用服务名
HOST_SERVICE_PORT=8003

# Auth Service 配置（用于调用其他服务）
GATEWAY_SERVICE_IP=gateway-service
GATEWAY_SERVICE_PORT=8000
HOST_SERVICE_IP=host-service
HOST_SERVICE_PORT=8003

# Host Service 配置（用于调用其他服务）
GATEWAY_SERVICE_IP=gateway-service
GATEWAY_SERVICE_PORT=8000
AUTH_SERVICE_IP=auth-service
AUTH_SERVICE_PORT=8001
```

**配置说明**:

- **Docker 环境**：在 `docker-compose.yml` 中，`*_SERVICE_IP` 应设置为对应的服务名（如 `auth-service`），Docker DNS 会自动解析
- **本地开发环境**：使用 `127.0.0.1` 或 `localhost`，脚本 `start_services_local.*` 会自动设置
- **优先级**：环境变量 > 自动检测（Docker 服务名 / `127.0.0.1`）

> **注意**：这些变量用于"如何访问其他服务"，与 `SERVICE_IP`（用于向 Nacos 注册自己的地址）是不同的概念。  
> 详细说明请参考 [SERVICE_IP 和 SERVICE_PORT 配置说明文档](./20-service-ip-port-config-explanation.md)

#### 服务注册配置

**用于向 Nacos 注册自己的地址**（每个服务需要知道自己的 IP 和端口）：

```bash
# 每个服务需要配置自己的 SERVICE_IP 和 SERVICE_PORT
SERVICE_IP=172.20.0.100    # Gateway Service 的 IP（Docker 环境）
SERVICE_PORT=8000          # Gateway Service 的端口

# 或者使用服务名（Docker 环境会自动检测）
# 本地开发环境会自动使用 127.0.0.1
```

**配置说明**:

- **Docker 环境**：建议明确配置 `SERVICE_IP`（对应 `docker-compose.yml` 中的 `ipv4_address`）
- **本地开发环境**：通常不需要配置，代码会自动使用 `127.0.0.1`
- **自动检测**：代码支持自动检测容器 IP，但明确配置更可靠

> 详细说明请参考 [SERVICE_IP 和 SERVICE_PORT 配置说明文档](./20-service-ip-port-config-explanation.md)

<!-- #### Nacos 配置

```bash
NACOS_SERVER_ADDR=http://nacos:8848
NACOS_NAMESPACE=public
NACOS_GROUP=DEFAULT_GROUP
``` -->

## 服务管理

### 使用 Docker Compose 管理服务

项目使用 Docker Compose 进行服务管理。所有服务管理操作都通过 `docker-compose` 命令完成。

### 启动服务

#### 基本启动（后台运行）

```bash
docker-compose up -d
```

#### 重新构建并启动

```bash
docker-compose up -d --build
```

#### 不使用缓存构建

```bash
docker-compose build --no-cache
docker-compose up -d
```

#### 只启动特定服务

```bash
docker-compose up -d mariadb redis nacos jaeger
docker-compose up -d auth-service
```

#### 前台运行（查看日志）

```bash
docker-compose up
```

### 停止服务

#### 基本停止

```bash
docker-compose down
```

#### 停止并删除数据卷

```bash
docker-compose down -v
```

⚠️ **警告**: 使用 `-v` 选项会删除所有数据卷，包括数据库数据！

#### 只停止特定服务

```bash
docker-compose stop mariadb
```

#### 设置停止超时时间

```bash
docker-compose stop --timeout 30
```

### 重启服务

#### 基本重启

```bash
docker-compose restart
```

#### 重新构建并重启

```bash
docker-compose up -d --build
```

#### 重启特定服务

```bash
docker-compose restart gateway-service
```

### 本地开发启动脚本

对于本地开发环境，可以使用以下脚本：

#### 启动本地服务（Linux/macOS）

```bash
./scripts/start_services_local.sh
```

#### 启动本地服务（Windows）

```bash
scripts\start_services_local.bat
```

这些脚本会自动设置必要的环境变量（如 `*_SERVICE_IP=127.0.0.1`），方便本地开发。

## Docker Compose 配置

### 服务依赖关系

所有微服务都依赖于基础设施服务：

```yaml
depends_on:
  mysql:
    condition: service_healthy
  redis:
    condition: service_healthy
  nacos:
    condition: service_healthy
  jaeger:
    condition: service_healthy
```

### 健康检查配置

每个服务都配置了健康检查：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 网络配置

所有服务运行在同一个 Docker 网络中：

```yaml
networks:
  intel-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 数据卷配置

持久化数据存储在 Docker 数据卷中：

```yaml
volumes:
  mysql_data:      # MySQL 数据
  redis_data:      # Redis 数据
  nacos_data:      # Nacos 数据
  nacos_logs:      # Nacos 日志
  jaeger_data:     # Jaeger 数据
```

### 服务间调用环境变量

在 `docker-compose.yml` 中，每个服务都需要配置其他服务的地址，用于服务间调用：

```yaml
services:
  gateway-service:
    environment:
      # 服务自身注册信息
      SERVICE_NAME: gateway-service
      SERVICE_PORT: 8000
      SERVICE_IP: 172.20.0.100
      
      # 服务间调用配置（用于调用其他服务）
      AUTH_SERVICE_IP: auth-service      # Docker 环境使用服务名
      AUTH_SERVICE_PORT: 8001
      HOST_SERVICE_IP: host-service
      HOST_SERVICE_PORT: 8003
      
  auth-service:
    environment:
      # 服务自身注册信息
      SERVICE_NAME: auth-service
      SERVICE_PORT: 8001
      SERVICE_IP: 172.20.0.101
      
      # 服务间调用配置
      GATEWAY_SERVICE_IP: gateway-service
      GATEWAY_SERVICE_PORT: 8000
      HOST_SERVICE_IP: host-service
      HOST_SERVICE_PORT: 8003
      
  host-service:
    environment:
      # 服务自身注册信息
      SERVICE_NAME: host-service
      SERVICE_PORT: 8003
      SERVICE_IP: 172.20.0.103
      
      # 服务间调用配置
      GATEWAY_SERVICE_IP: gateway-service
      GATEWAY_SERVICE_PORT: 8000
      AUTH_SERVICE_IP: auth-service
      AUTH_SERVICE_PORT: 8001
```

**配置说明**:

- **`*_SERVICE_IP`**：在 Docker 环境中使用服务名（如 `auth-service`），Docker DNS 会自动解析
- **`*_SERVICE_PORT`**：对应服务的端口号
- **自动回退**：如果未配置，代码会根据运行环境自动选择：
  - Docker 环境：使用服务名（如 `auth-service`）
  - 本地环境：使用 `127.0.0.1`

## 常用操作

### 查看服务状态

```bash
docker-compose ps
```

### 查看服务日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f gateway-service
docker-compose logs -f auth-service

# 查看最近100行日志
docker-compose logs --tail=100 gateway-service
```

### 进入容器

```bash
# 进入容器 shell
docker-compose exec gateway-service bash

# 以 root 用户进入
docker-compose exec -u root gateway-service bash
```

### 重启单个服务

```bash
docker-compose restart gateway-service
```

### 查看资源使用情况

```bash
docker stats
```

### 清理未使用的资源

```bash
# 清理停止的容器
docker container prune -f

# 清理未使用的镜像
docker image prune -f

# 清理未使用的网络
docker network prune -f

# 清理所有未使用的资源
docker system prune -f
```

## 故障排查

### 服务启动失败

1. **检查日志**

   ```bash
   docker-compose logs [service_name]
   ```

2. **检查端口占用**

   ```bash
   lsof -i :8000  # 检查端口是否被占用
   ```

3. **检查环境变量**

   ```bash
   docker-compose config  # 查看最终配置
   ```

### 数据库连接失败

1. **检查 MySQL 是否启动**

   ```bash
   docker-compose ps mysql
   ```

2. **检查 MySQL 日志**

   ```bash
   docker-compose logs mysql
   ```

3. **测试数据库连接**

   ```bash
   docker-compose exec mysql mysql -u root -p
   ```

### 服务间通信失败

1. **检查网络配置**

   ```bash
   docker network ls
   docker network inspect intel-cw-ms_intel-network
   ```

2. **测试服务连通性**

   ```bash
   docker-compose exec gateway-service ping auth-service
   docker-compose exec gateway-service curl http://auth-service:8001/health
   docker-compose exec gateway-service curl http://host-service:8003/health
   ```

3. **检查服务间调用环境变量**

   ```bash
   # 检查 Gateway Service 的环境变量
   docker-compose exec gateway-service env | grep SERVICE
   
   # 检查 Auth Service 的环境变量
   docker-compose exec auth-service env | grep SERVICE
   
   # 检查 Host Service 的环境变量
   docker-compose exec host-service env | grep SERVICE
   ```

4. **验证服务发现配置**

   ```bash
   # 检查服务是否正确注册到 Nacos
   curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=gateway-service
   curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=auth-service
   curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=host-service
   ```

5. **检查服务日志中的连接错误**

   ```bash
   # 查看 Gateway Service 日志中的连接错误
   docker-compose logs gateway-service | grep -i "connection\|timeout\|refused"
   
   # 查看 Auth Service 日志
   docker-compose logs auth-service | grep -i "connection\|timeout\|refused"
   ```

6. **本地开发环境特殊说明**

   如果是在本地开发环境（非 Docker），确保：

   - 使用 `start_services_local.*` 脚本启动服务（会自动设置 `*_SERVICE_IP=127.0.0.1`）
   - 或在 `.env` 文件中手动配置：

     ```bash
     AUTH_SERVICE_IP=127.0.0.1
     AUTH_SERVICE_PORT=8001
     HOST_SERVICE_IP=127.0.0.1
     HOST_SERVICE_PORT=8003
     ```

<!-- ### Nacos 注册失败

1. **检查 Nacos 是否启动**

   ```bash
   docker-compose ps nacos
   curl http://localhost:8848/nacos/v1/console/health/readiness
   ```

2. **检查服务日志**

   ```bash
   docker-compose logs nacos
   docker-compose logs gateway-service | grep -i nacos
   ``` -->

## 性能优化

### 资源限制

在 `docker-compose.yml` 中为服务设置资源限制：

```yaml
services:
  gateway-service:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 日志管理

配置日志轮转以避免日志文件过大：

```yaml
services:
  gateway-service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 安全建议

### 生产环境配置

1. **修改默认密码**
   - MySQL root 密码
   - Redis 密码
   - JWT 密钥

2. **使用 secrets 管理敏感信息**

   ```yaml
   secrets:
     mysql_root_password:
       file: ./secrets/mysql_root_password.txt
   ```

3. **限制端口暴露**
   - 只暴露必要的端口
   - 使用反向代理（Nginx）

4. **启用 TLS/SSL**
   - 配置 HTTPS
   - 使用证书加密通信

5. **定期更新镜像**

   ```bash
   docker-compose pull
   docker-compose up -d
   ```

## 备份和恢复

### 数据库备份

```bash
# 备份 MySQL 数据库
docker-compose exec mysql mysqldump -u root -p intel_cw > backup.sql

# 恢复数据库
docker-compose exec -T mysql mysql -u root -p intel_cw < backup.sql
```

### 数据卷备份

```bash
# 备份数据卷
docker run --rm -v intel-cw-ms_mysql_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/mysql_data_backup.tar.gz -C /data .

# 恢复数据卷
docker run --rm -v intel-cw-ms_mysql_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/mysql_data_backup.tar.gz -C /data
```

<!-- ## 监控和告警

### Prometheus 指标

访问各服务的 `/metrics` 端点：

- Gateway: <http://localhost:8000/metrics>
- Auth Service: <http://localhost:8001/metrics>
- Admin Service: <http://localhost:8002/metrics>
- Host Service: <http://localhost:8003/metrics>

### Jaeger 追踪

访问 Jaeger UI 查看分布式追踪：

<http://localhost:16686>

### 健康检查

访问各服务的 `/health` 端点：

- Gateway: <http://localhost:8000/health>
- Auth Service: <http://localhost:8001/health>
- Admin Service: <http://localhost:8002/health>
- Host Service: <http://localhost:8003/health> -->

## 升级和迁移

### 滚动更新

```bash
# 更新单个服务
docker-compose up -d --no-deps --build gateway-service

# 更新所有服务
docker-compose up -d --build
```

### 数据迁移

1. 备份当前数据
2. 停止服务
3. 更新配置
4. 启动服务
5. 验证数据

## 附录

### Docker Compose 常用命令参考

#### 启动相关命令

- `docker-compose up -d`: 后台启动所有服务
- `docker-compose up`: 前台启动所有服务（查看日志）
- `docker-compose up -d --build`: 重新构建并启动
- `docker-compose up -d <service>`: 只启动指定服务

#### 停止相关命令

- `docker-compose down`: 停止并删除容器
- `docker-compose down -v`: 停止并删除容器和数据卷
- `docker-compose stop`: 停止容器（不删除）
- `docker-compose stop <service>`: 停止指定服务

#### 重启相关命令

- `docker-compose restart`: 重启所有服务
- `docker-compose restart <service>`: 重启指定服务
- `docker-compose up -d --build`: 重新构建并重启

#### 日志查看命令

- `docker-compose logs -f`: 查看所有服务日志（实时）
- `docker-compose logs -f <service>`: 查看指定服务日志
- `docker-compose logs --tail=100 <service>`: 查看最近100行日志

#### 镜像构建命令

- `docker-compose build`: 构建所有服务镜像
- `docker-compose build --no-cache`: 不使用缓存构建
- `docker-compose build <service>`: 构建指定服务镜像

#### 其他实用命令

- `docker-compose ps`: 查看服务状态
- `docker-compose config`: 查看最终配置
- `docker-compose exec <service> <command>`: 在容器中执行命令

### 常见问题

**Q: 如何查看服务的实时日志？**

```bash
docker-compose logs -f [service_name]
```

**Q: 如何重置所有数据？**

```bash
docker-compose down -v
docker-compose up -d --build
```

**Q: 如何只启动基础设施服务？**

```bash
docker-compose up -d mysql redis nacos jaeger
```

**Q: 如何更新单个服务而不影响其他服务？**

```bash
docker-compose up -d --no-deps --build [service_name]
```
