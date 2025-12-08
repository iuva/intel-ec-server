# MySQL/MariaDB 2000 并发快速配置指南

## 🚀 快速开始

### 步骤 1: 配置 MySQL/MariaDB 服务器

编辑 MySQL/MariaDB 的配置文件 `my.ini`（通常在 `C:\ProgramData\MySQL\MySQL Server X.X\` 或 `C:\Program Files\MariaDB X.X\data\`）：

```ini
[mysqld]
# 最大连接数（必须大于应用总连接数）
max_connections = 3000

# InnoDB 缓冲池大小（根据服务器内存调整，建议为物理内存的 50-70%）
innodb_buffer_pool_size = 8G

# 线程缓存大小
thread_cache_size = 300

# 表缓存大小
table_open_cache = 4000

# 连接超时时间
wait_timeout = 600
interactive_timeout = 600
```

**重启 MySQL/MariaDB 服务**使配置生效。

### 步骤 2: 配置 Windows 系统参数

**方法 1：使用 PowerShell 脚本（推荐）**

1. 以管理员身份打开 PowerShell
2. 运行配置脚本：

```powershell
cd scripts/windows
.\configure-mysql-2000-concurrency.ps1
```

**方法 2：手动配置**

1. 打开注册表编辑器（`regedit`）
2. 导航到：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters`
3. 创建或修改以下 DWORD 值：
   - `TcpNumConnections` = `16777214`
   - `MaxUserPort` = `65534`
   - `TcpTimedWaitDelay` = `30`
4. 重启系统

### 步骤 3: 配置应用程序

**方式 1：使用环境变量文件**

创建 `.env` 文件（或使用 `docs/performance/mysql-2000-concurrency-config-example.env`）：

```bash
# 数据库连接池配置
DB_POOL_SIZE=300
DB_MAX_OVERFLOW=500
DB_POOL_TIMEOUT=30.0
DB_CONNECT_TIMEOUT=10

# 网关服务 HTTP 客户端配置
HTTP_MAX_CONNECTIONS=2500
HTTP_MAX_KEEPALIVE_CONNECTIONS=1000
HTTP_TIMEOUT=30.0
HTTP_CONNECT_TIMEOUT=10.0
```

**方式 2：在 docker-compose.yml 中配置**

```yaml
services:
  gateway-service:
    environment:
      DB_POOL_SIZE: 500
      DB_MAX_OVERFLOW: 1000
      HTTP_MAX_CONNECTIONS: 2000
      HTTP_MAX_KEEPALIVE_CONNECTIONS: 800
      HTTP_TIMEOUT: 30.0
      HTTP_CONNECT_TIMEOUT: 10.0

  auth-service:
    environment:
      DB_POOL_SIZE: 500
      DB_MAX_OVERFLOW: 1000

  admin-service:
    environment:
      DB_POOL_SIZE: 500
      DB_MAX_OVERFLOW: 1000

  host-service:
    environment:
      DB_POOL_SIZE: 500
      DB_MAX_OVERFLOW: 1000
```

### 步骤 4: 验证配置

**验证 MySQL/MariaDB 配置**：

```sql
-- 查看最大连接数
SHOW VARIABLES LIKE 'max_connections';

-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';

-- 查看历史最大连接数
SHOW STATUS LIKE 'Max_used_connections';
```

**验证应用程序配置**：

查看应用程序日志，确认连接池配置已生效：

```json
{
  "pool_size": 300,
  "max_overflow": 500,
  "max_connections": 800,
  "status": "connected"
}
```

## 📊 配置说明

### 连接数计算

- **目标并发**: 2000 个并发用户
- **应用服务数量**: 4 个微服务（gateway, auth, admin, host）
- **每个服务并发数**: 500（2000 ÷ 4 = 500）
- **连接池大小**: 300（并发数 × 0.6，考虑连接复用）
- **每个服务总连接数**: 800（300 + 500 溢出）
- **所有服务总连接数**: 3200（4 × 800）
- **MySQL 最大连接数**: 3000（实际使用中，由于连接复用，实际连接数会远小于理论值）

### 关键配置参数

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `max_connections` | 3000 | MySQL 最大连接数 |
| `DB_POOL_SIZE` | 300 | 每个服务的基础连接池大小（并发数 × 0.6） |
| `DB_MAX_OVERFLOW` | 500 | 每个服务的最大溢出连接数（pool_size × 1.67） |
| `HTTP_MAX_CONNECTIONS` | 2500 | 网关服务的最大 HTTP 连接数（并发数 × 1.25） |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | 1000 | 网关服务的保持活动连接数（最大连接数 × 0.4） |
| `innodb_buffer_pool_size` | 8G | InnoDB 缓冲池大小（根据内存调整） |

## 🔍 监控和排查

### 监控连接数

```sql
-- 查看当前连接数
SELECT COUNT(*) AS current_connections FROM information_schema.PROCESSLIST;

-- 查看每个用户的连接数
SELECT USER, HOST, COUNT(*) AS connection_count
FROM information_schema.PROCESSLIST
GROUP BY USER, HOST
ORDER BY connection_count DESC;
```

### 常见问题

**问题 1：连接数达到上限**

```
Error: Too many connections
```

**解决方案**：
- 增加 `max_connections` 配置
- 检查是否有连接泄漏
- 优化应用程序连接池配置

**问题 2：连接超时**

```
Error: Connection timeout
```

**解决方案**：
- 增加 `connect_timeout` 配置
- 检查网络连接
- 检查防火墙规则

## 📚 详细文档

- [完整配置指南](mysql-2000-concurrency-windows-optimization.md)
- [配置示例文件](mysql-2000-concurrency-config-example.env)
- [Windows 配置脚本](../../scripts/windows/configure-mysql-2000-concurrency.ps1)

---

**最后更新**: 2025-01-29  
**适用版本**: MySQL 5.7+, MariaDB 10.3+, Windows Server 2016+

