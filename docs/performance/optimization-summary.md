# 性能优化总结 - 2000并发支持

## ✅ 已完成的优化

### 1. 网关服务配置优化

**文件**: `services/gateway-service/app/core/config.py`

**优化内容**:
- `http_max_connections`: 100 → **2500**（支持2000并发，预留25%缓冲）
- `http_max_keepalive_connections`: 20 → **1000**（提高连接复用率）
- `http_timeout`: 15.0s → **30.0s**（给后端更多处理时间）
- `http_connect_timeout`: 5.0s → **10.0s**（增加连接建立超时）

### 2. 数据库连接池配置优化

**文件**: `shared/common/database.py` 和 `shared/app/service_factory.py`

**优化内容**:
- `pool_size`: 50 → **300**（基础连接池大小，并发数 × 0.6）
- `max_overflow`: 100 → **500**（最大溢出连接数，pool_size × 1.67）
- **最大连接数**: 150 → **800**（每个服务支持800连接，4个服务总计3200）

### 3. 数据库查询逻辑优化

**文件**: `services/host-service/app/services/host_discovery_service.py`

**优化内容**:
- ✅ 在循环外创建数据库会话，复用连接
- ✅ 新增 `_filter_available_hosts_in_session` 方法，接受已有会话
- ✅ 减少数据库连接占用时间
- ✅ 避免循环中重复创建连接

**优化前**：
```python
for iteration in range(max_iterations):
    # 每次循环都创建新会话
    available_hosts = await self._filter_available_hosts(hardware_ids)
```

**优化后**：
```python
# 在循环外创建会话，复用连接
async with session_factory() as session:
    for iteration in range(max_iterations):
        # 复用同一个会话
        available_hosts = await self._filter_available_hosts_in_session(session, hardware_ids)
```

### 4. 连接池监控功能

**文件**: `shared/common/database.py`

**新增功能**:
- ✅ `get_pool_status()`: 获取连接池状态信息
- ✅ `log_pool_status()`: 记录连接池状态到日志
- ✅ `_create_monitored_session_factory()`: 监控连接获取时间
- ✅ 自动记录连接获取等待时间
- ✅ 根据使用率自动调整日志级别

**监控指标**:
- 连接池使用率（usage_percent）
- 当前使用中的连接数（checked_out）
- 空闲连接数（checked_in）
- 溢出连接数（overflow）
- 连接获取等待时间（wait_time_seconds）

### 5. 定期监控任务

**文件**: `shared/app/service_factory.py`

**新增功能**:
- ✅ 服务启动时自动启动连接池监控任务
- ✅ 每30秒自动记录连接池状态
- ✅ 服务关闭时自动停止监控任务

## 📊 优化效果预期

### 配置优化效果

| 配置项 | 优化前 | 优化后 | 改善 |
|--------|--------|--------|------|
| **网关最大连接数** | 100 | 2500 | +2400% |
| **网关保持连接数** | 20 | 1000 | +4900% |
| **数据库最大连接数** | 150 | 800 | +433% |
| **数据库基础连接池** | 50 | 300 | +500% |
| **数据库溢出连接数** | 100 | 500 | +400% |

### 查询逻辑优化效果

- **连接占用时间**: 减少 80-90%（从循环中多次创建连接改为复用单个连接）
- **连接池压力**: 显著降低（单个请求只占用1个连接，而不是多次占用）
- **查询性能**: 预计提升 20-30%（减少连接创建开销）

## 🔍 诊断功能

### 1. 连接池状态监控

**自动监控**：每30秒记录一次连接池状态

**日志示例**：
```json
{
  "message": "数据库连接池状态",
  "pool_size": 300,
  "max_overflow": 500,
  "max_connections": 800,
  "checked_in": 50,
  "checked_out": 750,
  "usage_percent": 93.75
}
```

### 2. 连接获取等待时间监控

**自动监控**：每次获取连接时记录等待时间

**日志示例**：
```json
{
  "message": "数据库连接获取耗时较长",
  "wait_time_seconds": 2.345,
  "pool_usage_percent": 95.2,
  "checked_out": 760,
  "max_connections": 800
}
```

### 3. 查询开始/结束时的连接池状态

**自动监控**：当连接池使用率 >= 80% 时记录

**日志示例**：
```json
{
  "message": "数据库连接池使用率较高，开始查询",
  "usage_percent": 85.3,
  "checked_out": 682,
  "max_connections": 800
}
```

## 📝 如何查看日志

### 查看连接池状态

```bash
# 实时查看连接池状态
docker-compose logs -f host-service | grep "数据库连接池状态"

# 查看连接池使用率趋势
docker-compose logs host-service | grep "数据库连接池状态" | \
  jq -r '.usage_percent' | tail -20
```

### 查看连接获取等待时间

```bash
# 查看连接获取等待时间超过1秒的日志
docker-compose logs host-service | grep "数据库连接获取耗时较长" | tail -20

# 统计连接获取等待时间分布
docker-compose logs host-service | grep "数据库连接获取" | \
  jq -r '.wait_time_seconds' | awk '{
    if($1<0.5) a++; 
    else if($1<1.0) b++; 
    else c++
  } END {
    print "正常(<0.5s):", a, "警告(0.5-1s):", b, "严重(>1s):", c
  }'
```

### 查看连接池耗尽事件

```bash
# 查看连接获取失败的日志
docker-compose logs host-service | grep "数据库连接获取失败" | tail -20

# 查看连接池使用率超过95%的日志
docker-compose logs host-service | grep "数据库连接池使用率过高" | tail -20
```

## 🎯 下一步行动

### 1. 重启服务

```bash
# 重启服务使配置生效
docker-compose restart gateway-service host-service

# 验证服务启动成功
docker-compose logs -f host-service | grep -E "(启动成功|连接池监控任务已启动)"
```

### 2. 运行压测

```bash
# 运行2000并发压测
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8000 \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

### 3. 监控日志

```bash
# 实时监控连接池状态
docker-compose logs -f host-service | grep --line-buffered "数据库连接池"

# 实时监控连接获取等待时间
docker-compose logs -f host-service | grep --line-buffered "数据库连接获取"
```

### 4. 分析结果

根据日志分析：
- 连接池使用率是否正常（< 80%）
- 连接获取等待时间是否正常（< 0.5秒）
- 是否有连接池耗尽事件
- 是否有长时间持有连接的请求

## 📊 实际测试结果分析

### 优化前后关键指标对比

| 指标 | 优化前 | 优化后 | 改善幅度 | 状态 |
|------|--------|--------|----------|------|
| **错误率** | 81.00% | **44.16%** | ✅ **降低 45%** | ⚠️ 仍需优化 |
| **p50 响应时间** | 18.2s | **16.64s** | ✅ 降低 9% | ⚠️ 仍需优化 |
| **p95 响应时间** | 29.99s | **30s** | ⚠️ 基本无变化 | ❌ 需优化 |
| **p99 响应时间** | 30s | **30s** | ⚠️ 基本无变化 | ❌ 需优化 |
| **平均响应时间** | 17.54s | **13.39s** | ✅ 降低 24% | ⚠️ 仍需优化 |
| **成功请求平均响应时间** | - | **9.02s** | ✅ 可接受 | ⚠️ 仍需优化 |
| **成功请求中位数响应时间** | - | **3.71s** | ✅ 良好 | ✅ 可接受 |
| **吞吐量** | 16.24 req/s | **23.37 req/s** | ✅ 提升 44% | ⚠️ 仍需优化 |

### 成功请求性能分析

**关键发现**：
- 成功请求的平均响应时间为 **9.02s**，中位数为 **3.71s**
- 说明成功请求的性能其实还可以，但大量请求超时导致整体性能差
- 错误率 44.16% 仍然很高，主要是超时错误

### 已实施的优化

#### 1. 循环逻辑优化 ✅

**问题**：
- 提前退出条件位置错误，导致即使已收集足够数据仍继续循环
- 单个请求可能执行 50+ 次循环

**修复**：
- 在循环开始就检查是否已收集足够数据，立即退出
- 移除重复的提前退出检查
- 优化循环流程，避免不必要的执行

**效果**：
- 错误率从 81% 降低到 44.16%
- 平均响应时间从 17.54s 降低到 13.39s

#### 2. 日志优化 ✅

**问题**：
- 每次循环都记录 INFO 级别日志
- 0.6 秒内产生 50+ 条日志，导致日志爆炸

**修复**：
- Mock 日志从 `INFO` 降为 `DEBUG`
- 只在第一次或每 10 次调用时记录日志
- 循环日志也优化为每 10 次记录一次

**效果**：
- 日志量减少 90%+
- 降低系统开销

### ⚠️ 剩余问题

#### 1. 错误率仍然很高（44.16%）

**错误类型分布**：
- `request timeout`: 大量请求超时（30秒超时）
- `connection reset by peer`: 连接被重置
- `dial: i/o timeout`: 连接建立超时

**可能原因**：
1. **后端服务响应时间过长**：成功请求平均 9.02s，接近超时阈值
2. **网关连接数不足**：需要确认配置是否正确应用
3. **数据库连接池压力**：高并发下可能耗尽连接池
4. **服务实例数不足**：单实例无法处理 500 并发

#### 2. 响应时间仍然较长

**问题**：
- p95 和 p99 响应时间仍然接近 30s（超时阈值）
- 说明大量请求接近或达到超时

**可能原因**：
1. **循环逻辑仍需优化**：虽然修复了提前退出，但循环次数可能仍然较多
2. **数据库查询慢**：需要检查查询性能
3. **外部接口调用慢**：Mock 数据虽然快，但实际接口可能慢

#### 3. 吞吐量不足

**问题**：
- 吞吐量仅 23.37 req/s，远低于目标 100 req/s

**可能原因**：
1. **单实例限制**：单实例无法处理高并发
2. **连接池限制**：数据库连接池可能成为瓶颈
3. **网关限制**：网关可能无法处理高并发

### 🛠️ 进一步优化建议

#### 短期优化（立即实施）

1. **验证网关配置是否正确应用**
   - 检查 `ProxyService` 是否使用了正确的配置值
   - 确认 `http_client_config` 是否正确传递

2. **优化循环逻辑**
   - 进一步减少循环次数
   - 考虑使用更高效的分页策略

3. **增加服务实例数**
   - 启动多个 host-service 实例
   - 使用负载均衡分发请求

#### 中期优化（1-2周）

1. **实现结果缓存**
   - 对查询结果进行短期缓存（1-5分钟）
   - 减少重复的外部接口调用和数据库查询

2. **优化数据库查询**
   - 检查索引是否合理
   - 优化批量查询逻辑
   - 考虑使用缓存减少数据库查询

3. **监控和诊断**
   - 添加详细的性能监控
   - 记录每个步骤的耗时
   - 识别性能瓶颈

#### 长期优化（1个月）

1. **架构优化**
   - 考虑引入 Redis 缓存层
   - 实现数据预加载和预热机制
   - 考虑使用消息队列处理耗时操作

2. **性能测试和调优**
   - 定期进行负载测试
   - 根据测试结果持续优化
   - 建立性能基准和告警机制

### 📈 预期改进效果

#### 应用所有优化后

| 指标 | 当前值 | 预期值 | 改进幅度 |
|------|--------|--------|----------|
| **错误率** | 44.16% | < 5% | **88%+** |
| **p50 响应时间** | 16.64s | < 2s | **88%+** |
| **p95 响应时间** | 30s | < 5s | **83%+** |
| **吞吐量** | 23.37 req/s | > 100 req/s | **300%+** |

---

## 🚀 MySQL/MariaDB 2000 并发快速配置

### 快速开始步骤

#### 步骤 1: 配置 MySQL/MariaDB 服务器

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

#### 步骤 2: 配置 Windows 系统参数

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

#### 步骤 3: 配置应用程序

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
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500
      HTTP_MAX_CONNECTIONS: 2500
      HTTP_MAX_KEEPALIVE_CONNECTIONS: 1000
      HTTP_TIMEOUT: 30.0
      HTTP_CONNECT_TIMEOUT: 10.0

  auth-service:
    environment:
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500

  host-service:
    environment:
      DB_POOL_SIZE: 300
      DB_MAX_OVERFLOW: 500
```

#### 步骤 4: 验证配置

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

### 配置说明

#### 连接数计算

- **目标并发**: 2000 个并发用户
- **应用服务数量**: 4 个微服务（gateway, auth, admin, host）
- **每个服务并发数**: 500（2000 ÷ 4 = 500）
- **连接池大小**: 300（并发数 × 0.6，考虑连接复用）
- **每个服务总连接数**: 800（300 + 500 溢出）
- **所有服务总连接数**: 3200（4 × 800）
- **MySQL 最大连接数**: 3000（实际使用中，由于连接复用，实际连接数会远小于理论值）

#### 关键配置参数

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `max_connections` | 3000 | MySQL 最大连接数 |
| `DB_POOL_SIZE` | 300 | 每个服务的基础连接池大小（并发数 × 0.6） |
| `DB_MAX_OVERFLOW` | 500 | 每个服务的最大溢出连接数（pool_size × 1.67） |
| `HTTP_MAX_CONNECTIONS` | 2500 | 网关服务的最大 HTTP 连接数（并发数 × 1.25） |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | 1000 | 网关服务的保持活动连接数（最大连接数 × 0.4） |
| `innodb_buffer_pool_size` | 8G | InnoDB 缓冲池大小（根据内存调整） |

### Windows 系统优化配置

#### 1. 增加文件描述符限制

**通过注册表调整（需要管理员权限）**：

1. 打开注册表编辑器（`regedit`）
2. 导航到：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters`
3. 创建或修改以下 DWORD 值：
   - `TcpNumConnections` = `16777214`（十进制）
   - `MaxUserPort` = `65534`（十进制）
   - `TcpTimedWaitDelay` = `30`（十进制，秒）

**通过 PowerShell 调整**：

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

#### 2. 调整 Windows 防火墙规则

确保 MySQL/MariaDB 端口（默认 3306）未被防火墙阻止：

```powershell
# 以管理员身份运行 PowerShell

# 允许 MySQL 端口（3306）入站连接
New-NetFirewallRule -DisplayName "MySQL Server" -Direction Inbound -LocalPort 3306 -Protocol TCP -Action Allow

# 查看防火墙规则
Get-NetFirewallRule -DisplayName "MySQL Server"
```

#### 3. 优化 Windows 网络参数

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

### 监控和排查

#### 监控连接数

```sql
-- 查看当前连接数
SELECT COUNT(*) AS current_connections FROM information_schema.PROCESSLIST;

-- 查看每个用户的连接数
SELECT USER, HOST, COUNT(*) AS connection_count
FROM information_schema.PROCESSLIST
GROUP BY USER, HOST
ORDER BY connection_count DESC;
```

#### 常见问题

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

### 配置验证清单

#### MySQL/MariaDB 服务器配置

- [ ] `max_connections` 设置为 3000
- [ ] `innodb_buffer_pool_size` 设置为物理内存的 50-70%
- [ ] `thread_cache_size` 设置为 300
- [ ] `table_open_cache` 设置为 4000
- [ ] 慢查询日志已启用
- [ ] 错误日志已配置

#### 应用程序配置

- [ ] `DB_POOL_SIZE` 设置为 300（每个服务）
- [ ] `DB_MAX_OVERFLOW` 设置为 500（每个服务）
- [ ] `HTTP_MAX_CONNECTIONS` 设置为 2500（网关服务）
- [ ] `HTTP_MAX_KEEPALIVE_CONNECTIONS` 设置为 1000（网关服务）
- [ ] 所有服务配置已更新

#### Windows 系统配置

- [ ] TCP 连接数限制已调整
- [ ] 防火墙规则已配置
- [ ] 网络参数已优化
- [ ] 系统已重启使配置生效

---

## 🔗 相关文档

- [服务性能优化方案](./service-optimization-plan.md)
- [数据库连接池阻塞诊断指南](./database-connection-pool-diagnosis.md)
- [k6 压测结果分析](./k6-load-test-analysis.md)
- [接口压测方案](../34-api-load-testing-plan.md)

---

**最后更新**: 2025-01-29  
**文档版本**: 2.1.0（合并2000并发配置指南）

