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
| Admin Service | ~800MB | ~400MB | 50% |
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
MYSQL_PASSWORD=your_secure_***REMOVED***word # MySQL 密码
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
REDIS_PASSWORD=your_redis_***REMOVED***word  # Redis 密码（如果有）
```

#### JWT 配置

```bash
JWT_SECRET_KEY=your_jwt_secret_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Nacos 配置

```bash
NACOS_SERVER_ADDR=http://nacos:8848
NACOS_NAMESPACE=public
NACOS_GROUP=DEFAULT_GROUP
```

## 服务管理脚本

### 启动服务

#### 基本启动

```bash
./scripts/start_services.sh
```

#### 重新构建并启动

```bash
./scripts/start_services.sh -b
```

#### 不使用缓存构建

```bash
./scripts/start_services.sh -b --no-cache
```

#### 只启动特定服务

```bash
./scripts/start_services.sh --only mysql
./scripts/start_services.sh --only auth-service
```

#### 跳过特定服务

```bash
./scripts/start_services.sh --skip jaeger
```

#### 前台运行（查看日志）

```bash
./scripts/start_services.sh -f
```

### 停止服务

#### 基本停止

```bash
./scripts/stop_services.sh
```

#### 停止并删除数据卷

```bash
./scripts/stop_services.sh -v
```

⚠️ **警告**: 使用 `-v` 选项会删除所有数据，包括数据库数据！

#### 只停止特定服务

```bash
./scripts/stop_services.sh --only mysql
```

#### 设置停止超时时间

```bash
./scripts/stop_services.sh --timeout 30
```

### 重启服务

#### 基本重启

```bash
./scripts/restart_services.sh
```

#### 重新构建并重启

```bash
./scripts/restart_services.sh -b
```

#### 快速重启（跳过健康检查）

```bash
./scripts/restart_services.sh --quick
```

#### 只重启特定服务

```bash
./scripts/restart_services.sh --only gateway-service
```

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
   docker-compose exec gateway-service ping mysql
   docker-compose exec gateway-service curl http://auth-service:8001/health
   ```

### Nacos 注册失败

1. **检查 Nacos 是否启动**

   ```bash
   docker-compose ps nacos
   curl http://localhost:8848/nacos/v1/console/health/readiness
   ```

2. **检查服务日志**

   ```bash
   docker-compose logs nacos
   docker-compose logs gateway-service | grep -i nacos
   ```

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
     mysql_root_***REMOVED***word:
       file: ./secrets/mysql_root_***REMOVED***word.txt
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

## 监控和告警

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
- Host Service: <http://localhost:8003/health>

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

### 脚本选项参考

#### start_services.sh

- `-h, --help`: 显示帮助信息
- `-b, --build`: 重新构建镜像
- `-d, --detach`: 后台运行（默认）
- `-f, --foreground`: 前台运行
- `--no-cache`: 构建时不使用缓存
- `--pull`: 构建前拉取最新基础镜像
- `--only <service>`: 只启动指定服务
- `--skip <service>`: 跳过指定服务

#### stop_services.sh

- `-h, --help`: 显示帮助信息
- `-v, --volumes`: 同时删除数据卷
- `-r, --remove-orphans`: 删除孤立容器
- `--only <service>`: 只停止指定服务
- `--timeout <seconds>`: 设置停止超时时间

#### restart_services.sh

- `-h, --help`: 显示帮助信息
- `-b, --build`: 重新构建镜像
- `--no-cache`: 构建时不使用缓存
- `--pull`: 构建前拉取最新基础镜像
- `--only <service>`: 只重启指定服务
- `--timeout <seconds>`: 设置停止超时时间
- `--quick`: 快速重启（不等待健康检查）

### 常见问题

**Q: 如何查看服务的实时日志？**

```bash
docker-compose logs -f [service_name]
```

**Q: 如何重置所有数据？**

```bash
./scripts/stop_services.sh -v
./scripts/start_services.sh -b
```

**Q: 如何只启动基础设施服务？**

```bash
docker-compose up -d mysql redis nacos jaeger
```

**Q: 如何更新单个服务而不影响其他服务？**

```bash
docker-compose up -d --no-deps --build [service_name]
```

---

**最后更新**: 2025-01-29
**版本**: 1.0.0
**维护者**: Intel EC 开发团队
