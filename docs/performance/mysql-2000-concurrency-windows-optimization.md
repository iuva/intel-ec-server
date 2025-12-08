# MySQL/MariaDB 2000 并发 Windows 服务器优化配置指南

## 🎯 目标

在 Windows 服务器上配置 MySQL/MariaDB 支持 **2000 并发连接**，确保系统稳定运行。

## 📊 配置概览

### 并发连接数计算

- **目标并发**: 2000 个并发用户
- **应用服务数量**: 假设 4 个微服务（gateway, auth, admin, host）
- **每个服务最大连接数**: 500（2000 ÷ 4 = 500）
- **MySQL 最大连接数**: 建议设置为 **2500-3000**（预留 25-50% 缓冲）

## 🔧 1. MySQL/MariaDB 服务器配置

### Windows 配置文件位置

- **MySQL**: `C:\ProgramData\MySQL\MySQL Server X.X\my.ini`
- **MariaDB**: `C:\Program Files\MariaDB X.X\data\my.ini` 或 `C:\ProgramData\MariaDB X.X\my.ini`

### 核心配置参数

```ini
[mysqld]
# ============================================
# 连接相关配置（关键）
# ============================================

# 最大连接数（必须大于应用总连接数）
# 2000 并发 + 4 个服务 × 500 连接 = 2000，建议设置为 3000
max_connections = 3000

# 每个连接的最大数据包大小（16MB）
max_allowed_packet = 16M

# 连接超时时间（秒）
connect_timeout = 10
wait_timeout = 600
interactive_timeout = 600

# ============================================
# 内存相关配置（根据服务器内存调整）
# ============================================

# InnoDB 缓冲池大小（建议设置为物理内存的 50-70%）
# 例如：16GB 内存服务器，设置为 8GB
innodb_buffer_pool_size = 8G

# InnoDB 日志文件大小（建议 256MB-1GB）
innodb_log_file_size = 512M

# InnoDB 日志缓冲区大小
innodb_log_buffer_size = 64M

# 查询缓存（MySQL 5.7 及以下版本，8.0+ 已移除）
# query_cache_size = 256M
# query_cache_type = 1

# 临时表大小限制
tmp_table_size = 256M
max_heap_table_size = 256M

# 排序缓冲区大小
sort_buffer_size = 2M
read_buffer_size = 2M
read_rnd_buffer_size = 4M

# ============================================
# 线程相关配置
# ============================================

# 线程缓存大小（建议设置为 max_connections 的 10%）
thread_cache_size = 300

# 线程栈大小
thread_stack = 256K

# ============================================
# InnoDB 引擎配置
# ============================================

# InnoDB 文件格式
innodb_file_format = Barracuda
innodb_file_per_table = 1

# InnoDB 刷新日志策略（性能优化）
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# InnoDB IO 线程数（建议设置为 CPU 核心数）
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# InnoDB 并发线程数
innodb_thread_concurrency = 0

# ============================================
# 表缓存配置
# ============================================

# 表缓存大小
table_open_cache = 4000
table_definition_cache = 2000

# ============================================
# 二进制日志配置（如果启用主从复制）
# ============================================

# 二进制日志过期时间（天）
expire_logs_days = 7

# 二进制日志大小
max_binlog_size = 512M

# ============================================
# 慢查询日志配置（性能监控）
# ============================================

# 启用慢查询日志
slow_query_log = 1
slow_query_log_file = C:/ProgramData/MySQL/MySQL Server X.X/Data/slow-query.log
long_query_time = 2

# ============================================
# 错误日志配置
# ============================================

# 错误日志文件
log_error = C:/ProgramData/MySQL/MySQL Server X.X/Data/error.log

# ============================================
# 字符集配置
# ============================================

character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# ============================================
# 网络配置
# ============================================

# 绑定地址（0.0.0.0 表示监听所有接口）
bind-address = 0.0.0.0

# 端口
port = 3306

# 最大数据包大小
max_allowed_packet = 16M
```

### 配置验证

重启 MySQL/MariaDB 服务后，执行以下 SQL 验证配置：

```sql
-- 查看最大连接数
SHOW VARIABLES LIKE 'max_connections';

-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';

-- 查看历史最大连接数
SHOW STATUS LIKE 'Max_used_connections';

-- 查看 InnoDB 缓冲池大小
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';

-- 查看线程缓存大小
SHOW VARIABLES LIKE 'thread_cache_size';
```

## 🔧 2. 应用程序连接池配置

### 环境变量配置

在 `.env` 文件或 `docker-compose.yml` 中配置：

```bash
# ============================================
# 数据库连接池配置（支持 2000 并发）
# ============================================

# 基础连接池大小（每个服务）
# 2000 并发 ÷ 4 个服务 = 500 并发/服务
# 连接池大小 = 并发数 × 0.4-0.6（考虑连接复用和峰值）
# 建议设置为 300，预留足够缓冲
DB_POOL_SIZE=300

# 最大溢出连接数
# 建议设置为 pool_size 的 1.5-2 倍，总连接数 = 300 + 500 = 800
DB_MAX_OVERFLOW=500

# 连接池超时时间（秒）
DB_POOL_TIMEOUT=30.0

# 连接超时时间（秒）
DB_CONNECT_TIMEOUT=10

# ============================================
# 网关服务 HTTP 客户端配置
# ============================================

# HTTP 客户端最大连接数（支持 2000 并发）
# 网关需要处理所有并发请求，设置为并发数的 1.2-1.5 倍
HTTP_MAX_CONNECTIONS=2500

# HTTP 客户端保持活动连接数
# 保持活动连接数 = 最大连接数的 30-50%，提高连接复用率
HTTP_MAX_KEEPALIVE_CONNECTIONS=1000

# HTTP 客户端超时时间（秒）
HTTP_TIMEOUT=30.0
HTTP_CONNECT_TIMEOUT=10.0
```

### Docker Compose 配置示例

```yaml
version: '3.8'

services:
  gateway-service:
    environment:
      # 数据库连接池配置
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500
      DB_POOL_TIMEOUT: 30.0
      DB_CONNECT_TIMEOUT: 10
      
      # HTTP 客户端配置
      HTTP_MAX_CONNECTIONS: 2500
      HTTP_MAX_KEEPALIVE_CONNECTIONS: 1000
      HTTP_TIMEOUT: 30.0
      HTTP_CONNECT_TIMEOUT: 10.0

  auth-service:
    environment:
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500
      DB_POOL_TIMEOUT: 30.0
      DB_CONNECT_TIMEOUT: 10

  admin-service:
    environment:
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500
      DB_POOL_TIMEOUT: 30.0
      DB_CONNECT_TIMEOUT: 10

  host-service:
    environment:
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500
      DB_POOL_TIMEOUT: 30.0
      DB_CONNECT_TIMEOUT: 10
```

## 🔧 3. Windows 系统资源优化

### 3.1 增加文件描述符限制

Windows 系统默认文件描述符限制可能不足，需要调整：

**方法 1：通过注册表调整（需要管理员权限）**

1. 打开注册表编辑器（`regedit`）
2. 导航到：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters`
3. 创建或修改以下 DWORD 值：
   - `TcpNumConnections` = `16777214`（十进制）
   - `MaxUserPort` = `65534`（十进制）
   - `TcpTimedWaitDelay` = `30`（十进制，秒）

**方法 2：通过 PowerShell 调整**

```powershell
# 以管理员身份运行 PowerShell

# 设置 TCP 连接数限制
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "TcpNumConnections" -Value 16777214 -PropertyType DWORD -Force

# 设置最大用户端口
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "MaxUserPort" -Value 65534 -PropertyType DWORD -Force

# 设置 TIME_WAIT 延迟
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "TcpTimedWaitDelay" -Value 30 -PropertyType DWORD -Force

# 重启系统使配置生效
Restart-Computer
```

### 3.2 调整 Windows 防火墙规则

确保 MySQL/MariaDB 端口（默认 3306）未被防火墙阻止：

```powershell
# 以管理员身份运行 PowerShell

# 允许 MySQL 端口（3306）入站连接
New-NetFirewallRule -DisplayName "MySQL Server" -Direction Inbound -LocalPort 3306 -Protocol TCP -Action Allow

# 查看防火墙规则
Get-NetFirewallRule -DisplayName "MySQL Server"
```

### 3.3 优化 Windows 网络参数

```powershell
# 以管理员身份运行 PowerShell

# 增加 TCP 连接队列大小
netsh int tcp set global autotuninglevel=normal
netsh int tcp set global chimney=enabled
netsh int tcp set global rss=enabled
netsh int tcp set global netdma=enabled

# 查看当前 TCP 参数
netsh int tcp show global
```

## 🔧 4. 数据库连接监控

### 4.1 实时监控连接数

```sql
-- 查看当前连接数
SELECT 
    COUNT(*) AS current_connections,
    VARIABLE_VALUE AS max_connections
FROM 
    information_schema.PROCESSLIST,
    information_schema.GLOBAL_VARIABLES
WHERE 
    VARIABLE_NAME = 'max_connections';

-- 查看每个用户的连接数
SELECT 
    USER,
    HOST,
    COUNT(*) AS connection_count
FROM 
    information_schema.PROCESSLIST
GROUP BY 
    USER, HOST
ORDER BY 
    connection_count DESC;

-- 查看连接详情
SELECT 
    ID,
    USER,
    HOST,
    DB,
    COMMAND,
    TIME,
    STATE,
    INFO
FROM 
    information_schema.PROCESSLIST
ORDER BY 
    TIME DESC;
```

### 4.2 监控连接池状态

应用程序日志中会定期输出连接池状态：

```json
{
  "pool_size": 300,
  "max_overflow": 500,
  "max_connections": 800,
  "checked_in": 270,
  "checked_out": 30,
  "overflow": 0,
  "total_connections": 300,
  "usage_percent": 37.5,
  "status": "connected"
}
```

**关键指标**：
- `usage_percent < 80%`: 正常
- `usage_percent >= 80%`: 警告，考虑增加连接池
- `usage_percent >= 95%`: 严重，必须增加连接池或优化查询

## 🔧 5. 性能优化建议

### 5.1 数据库查询优化

1. **添加索引**：确保常用查询字段有索引
2. **避免全表扫描**：使用 `EXPLAIN` 分析查询计划
3. **优化 JOIN 查询**：减少 JOIN 表数量，使用合适的 JOIN 类型
4. **使用分页查询**：避免一次性查询大量数据
5. **启用查询缓存**：MySQL 5.7 及以下版本

### 5.2 应用程序优化

1. **连接复用**：使用连接池，避免频繁创建/关闭连接
2. **事务优化**：减少事务时间，避免长事务
3. **批量操作**：使用批量插入/更新，减少数据库交互
4. **缓存策略**：使用 Redis 缓存热点数据
5. **异步处理**：耗时操作使用异步任务队列

### 5.3 监控和告警

1. **连接数监控**：设置告警阈值（如：连接数 > 2500）
2. **慢查询监控**：定期分析慢查询日志
3. **资源监控**：监控 CPU、内存、磁盘 I/O
4. **应用监控**：监控应用响应时间和错误率

## 📊 6. 配置验证清单

### MySQL/MariaDB 服务器配置

- [ ] `max_connections` 设置为 3000
- [ ] `innodb_buffer_pool_size` 设置为物理内存的 50-70%
- [ ] `thread_cache_size` 设置为 300
- [ ] `table_open_cache` 设置为 4000
- [ ] 慢查询日志已启用
- [ ] 错误日志已配置

### 应用程序配置

- [ ] `DB_POOL_SIZE` 设置为 300（每个服务）
- [ ] `DB_MAX_OVERFLOW` 设置为 500（每个服务）
- [ ] `HTTP_MAX_CONNECTIONS` 设置为 2500（网关服务）
- [ ] `HTTP_MAX_KEEPALIVE_CONNECTIONS` 设置为 1000（网关服务）
- [ ] 所有服务配置已更新

### Windows 系统配置

- [ ] TCP 连接数限制已调整
- [ ] 防火墙规则已配置
- [ ] 网络参数已优化
- [ ] 系统已重启使配置生效

### 监控和测试

- [ ] 连接数监控已配置
- [ ] 慢查询监控已启用
- [ ] 压力测试已执行
- [ ] 性能指标已记录

## 🚨 7. 常见问题排查

### 问题 1：连接数达到上限

**症状**：
```
Error: Too many connections
```

**解决方案**：
1. 增加 `max_connections` 配置
2. 检查是否有连接泄漏
3. 优化应用程序连接池配置

### 问题 2：连接超时

**症状**：
```
Error: Connection timeout
```

**解决方案**：
1. 增加 `connect_timeout` 配置
2. 检查网络连接
3. 检查防火墙规则

### 问题 3：内存不足

**症状**：
```
Error: Out of memory
```

**解决方案**：
1. 减少 `innodb_buffer_pool_size`
2. 优化查询，减少内存使用
3. 增加服务器内存

### 问题 4：响应时间慢

**症状**：
- 查询响应时间 > 2 秒
- 连接获取等待时间 > 1 秒

**解决方案**：
1. 优化慢查询
2. 增加连接池大小
3. 添加数据库索引
4. 使用缓存减少数据库查询

## 📚 8. 参考资源

- [MySQL 官方文档 - 连接管理](https://dev.mysql.com/doc/refman/8.0/en/connection-management.html)
- [MariaDB 官方文档 - 系统变量](https://mariadb.com/kb/en/server-system-variables/)
- [SQLAlchemy 连接池文档](https://docs.sqlalchemy.org/en/14/core/pooling.html)
- [Windows TCP/IP 参数优化](https://docs.microsoft.com/en-us/troubleshoot/windows-server/networking/description-tcp-features)

---

**最后更新**: 2025-01-29  
**适用版本**: MySQL 5.7+, MariaDB 10.3+, Windows Server 2016+  
**配置目标**: 支持 2000 并发连接

