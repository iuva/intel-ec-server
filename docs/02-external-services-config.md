# 外部服务配置指南

## 概述

本项目已配置为使用外部的 MariaDB 和 Redis 服务，而不是在 Docker Compose 中启动这些服务。您需要配置连接信息以连接到您现有的 MariaDB 和 Redis 实例。

## 配置步骤

### 1. 创建环境变量文件

复制示例配置文件并修改为您的实际配置：

```bash
cp .env.example .env
```

### 2. 配置 MariaDB 连接

在 `.env` 文件中配置您的 MariaDB 连接信息：

```bash
# MariaDB 配置
MARIADB_HOST=your_mariadb_host    # MariaDB 主机地址
MARIADB_PORT=3306                 # MariaDB 端口
MARIADB_USER=your_username        # MariaDB 用户名
MARIADB_PASSWORD=your_***REMOVED***word    # MariaDB 密码
MARIADB_DATABASE=intel_cw         # 数据库名称
```

#### MariaDB 主机地址配置说明

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

**场景 3: MariaDB 运行在其他 Docker 容器**

```bash
MARIADB_HOST=mariadb_container_name  # 容器名称
# 或
MARIADB_HOST=172.20.0.10  # 容器IP地址
```

### 3. 配置 Redis 连接

在 `.env` 文件中配置您的 Redis 连接信息：

```bash
# Redis 配置
REDIS_HOST=your_redis_host        # Redis 主机地址
REDIS_PORT=6379                   # Redis 端口
REDIS_PASSWORD=                   # Redis 密码（如果没有密码，留空）
REDIS_DB=0                        # Redis 数据库编号
```

#### Redis 主机地址配置说明

配置方式与 MariaDB 相同，根据您的 Redis 部署位置选择：

- **宿主机**: `host.docker.internal` (macOS/Windows) 或 `172.17.0.1` (Linux)
- **远程服务器**: 实际IP地址或域名
- **其他容器**: 容器名称或容器IP

### 4. 配置 JWT 密钥

设置一个强密码作为 JWT 密钥（至少32个字符）：

```bash
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-min-32-chars
```

## 数据库初始化

### 创建数据库

在您的 MariaDB 服务器上创建项目数据库：

```sql
CREATE DATABASE IF NOT EXISTS intel_cw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 创建用户并授权（可选）

如果需要创建专用用户：

```sql
-- 创建用户
CREATE USER 'intel_user'@'%' IDENTIFIED BY 'your_***REMOVED***word';

-- 授予权限
GRANT ALL PRIVILEGES ON intel_cw.* TO 'intel_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;
```

### 初始化表结构

项目中的各个服务会在启动时自动创建所需的表结构。如果需要手动初始化，可以运行：

```bash
# 进入服务目录
cd services/auth-service

# 运行表创建脚本
python create_tables.py
```

对其他服务重复此操作：
- `services/admin-service/create_tables.py`
- `services/host-service/create_tables.py`

## Redis 配置

### Redis 数据库分配

不同的服务使用不同的 Redis 数据库编号：

- **Gateway Service**: DB 0
- **Auth Service**: DB 1
- **Admin Service**: DB 2
- **Host Service**: DB 3

这些配置已在 `docker-compose.yml` 中设置，无需手动修改。

### Redis 密码配置

如果您的 Redis 设置了密码：

```bash
REDIS_PASSWORD=your_redis_***REMOVED***word
```

如果没有密码，保持为空：

```bash
REDIS_PASSWORD=
```

## 网络配置

### Docker 网络模式

项目使用自定义桥接网络 `intel-network`，子网为 `172.20.0.0/16`。

### 防火墙配置

如果 MariaDB 或 Redis 运行在远程服务器上，确保防火墙允许以下端口：

- **MariaDB**: 3306
- **Redis**: 6379

### 安全建议

1. **不要在生产环境中使用默认密码**
2. **使用强密码**（至少16个字符，包含大小写字母、数字和特殊字符）
3. **限制数据库访问IP**（仅允许应用服务器访问）
4. **启用 SSL/TLS 连接**（生产环境）
5. **定期备份数据库**

## 验证配置

### 1. 测试 MariaDB 连接

从容器内测试 MariaDB 连接：

```bash
# 启动一个临时容器测试连接
docker run -it --rm --network intel-network mariadb:10.11 \
  mariadb -h your_mariadb_host -P 3306 -u your_username -p
```

### 2. 测试 Redis 连接

从容器内测试 Redis 连接：

```bash
# 启动一个临时容器测试连接
docker run -it --rm --network intel-network redis:6.2-alpine \
  redis-cli -h your_redis_host -p 6379 -a your_***REMOVED***word ping
```

### 3. 查看服务日志

启动服务后查看日志，确认连接成功：

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f gateway-service
docker-compose logs -f auth-service
```

## 故障排查

### 问题 1: 无法连接到 MariaDB

**错误信息**: `Can't connect to MariaDB server`

**解决方案**:
1. 检查 MariaDB 服务是否运行
2. 检查 `MARIADB_HOST` 配置是否正确
3. 检查防火墙是否允许 3306 端口
4. 检查 MariaDB 用户权限（允许从 Docker 容器IP连接）

### 问题 2: 无法连接到 Redis

**错误信息**: `Error connecting to Redis`

**解决方案**:
1. 检查 Redis 服务是否运行
2. 检查 `REDIS_HOST` 配置是否正确
3. 检查 Redis 密码是否正确
4. 检查防火墙是否允许 6379 端口

### 问题 3: 权限被拒绝

**错误信息**: `Access denied for user`

**解决方案**:
1. 检查用户名和密码是否正确
2. 检查用户是否有访问数据库的权限
3. 检查用户是否允许从 Docker 容器IP连接

```sql
-- 查看用户权限
SHOW GRANTS FOR 'your_username'@'%';

-- 如果需要，重新授权
GRANT ALL PRIVILEGES ON intel_cw.* TO 'your_username'@'%';
FLUSH PRIVILEGES;
```

## 配置示例

### 示例 1: 本地开发环境（macOS）

```bash
# .env
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123
MYSQL_DATABASE=intel_cw

REDIS_HOST=host.docker.internal
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

JWT_SECRET_KEY=dev-secret-key-for-local-development-only
DEBUG=true
LOG_LEVEL=DEBUG
```

### 示例 2: 生产环境（远程服务器）

```bash
# .env
MYSQL_HOST=192.168.1.200
MYSQL_PORT=3306
MYSQL_USER=intel_prod_user
MYSQL_PASSWORD=StrongPassword123!@#
MYSQL_DATABASE=intel_cw_prod

REDIS_HOST=192.168.1.201
REDIS_PORT=6379
REDIS_PASSWORD=RedisStrongPassword456!@#
REDIS_DB=0

JWT_SECRET_KEY=production-super-secret-jwt-key-min-32-characters-long
DEBUG=false
LOG_LEVEL=INFO
```

## 相关文档

- [快速开始指南](quick-start.md)
- [部署指南](deployment-guide.md)
- [项目设置指南](project-setup.md)

---

**最后更新**: 2025-01-29
**维护者**: Intel EC 开发团队
