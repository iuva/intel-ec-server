# SQL性能监控和慢查询定位系统

## 概述

SQL性能监控系统自动监控所有SQL查询的执行时间，检测并记录超过阈值的慢查询，帮助快速定位性能瓶颈。

## 功能特性

- **自动监控**: 使用SQLAlchemy事件监听器，自动监控所有SQL查询，无需修改现有代码
- **慢查询检测**: 自动检测超过阈值的慢查询（默认2秒）
- **详细记录**: 记录SQL语句、参数、执行时间、表名、操作类型、调用堆栈等信息
- **Prometheus集成**: 集成Prometheus指标收集，实时监控慢查询趋势
- **分析工具**: 提供命令行工具分析慢查询日志，生成统计报告

## 配置说明

### 环境变量

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `ENABLE_SQL_MONITORING` | 是否启用SQL性能监控 | `true` |
| `SLOW_QUERY_THRESHOLD` | 慢查询阈值（秒） | `2.0` |

### 配置示例

```bash
# 启用SQL监控，设置慢查询阈值为2秒
export ENABLE_SQL_MONITORING=true
export SLOW_QUERY_THRESHOLD=2.0

# 禁用SQL监控
export ENABLE_SQL_MONITORING=false

# 设置更严格的慢查询阈值（1秒）
export SLOW_QUERY_THRESHOLD=1.0
```

## 监控指标

### Prometheus指标

系统会自动收集以下Prometheus指标：

#### `db_slow_queries_total`
慢查询总数计数器

**标签**:
- `operation`: 操作类型（select, insert, update, delete等）
- `table`: 表名
- `service`: 服务名称
- `sql_hash`: SQL哈希值（用于去重）

#### `db_slow_query_duration_seconds`
慢查询响应时间直方图

**标签**: 同 `db_slow_queries_total`

**Buckets**: `[2.0, 3.0, 5.0, 10.0, 15.0, 30.0, 60.0]` 秒

### 查询示例

```promql
# 查询最近5分钟的慢查询总数
sum(rate(db_slow_queries_total[5m])) by (service, table, operation)

# 查询平均慢查询耗时
sum(rate(db_slow_query_duration_seconds_sum[5m])) / sum(rate(db_slow_query_duration_seconds_count[5m]))

# 查询特定表的慢查询
sum(rate(db_slow_queries_total[5m])) by (operation) {table="host_rec"}
```

## 日志记录

### 慢查询日志格式

当检测到慢查询时，系统会记录WARNING级别的日志，包含以下信息：

```json
{
  "sql": "SELECT * FROM host_rec WHERE del_flag = 0 AND host_state = 1",
  "duration_ms": 2500.5,
  "duration_seconds": 2.5005,
  "operation": "select",
  "table": "host_rec",
  "sql_hash": "a1b2c3d4",
  "parameters": null,
  "stack_trace": [
    "services/host-service/app/services/browser_host_service.py:68 in get_host_by_id",
    "services/host-service/app/api/v1/endpoints/browser_hosts.py:45 in get_host"
  ]
}
```

### 日志位置

慢查询日志会记录到服务的标准日志文件中：
- 开发环境: `logs/{service_name}.log`
- 生产环境: 根据日志配置输出

## 慢查询分析工具

### 使用方法

```bash
# 分析日志文件，显示Top 10慢查询
python scripts/analyze_slow_queries.py logs/host-service.log

# 显示Top 20慢查询
python scripts/analyze_slow_queries.py logs/host-service.log -n 20

# 生成JSON报告
python scripts/analyze_slow_queries.py logs/host-service.log -o report.json
```

### 分析报告内容

分析工具会生成以下统计信息：

1. **耗时统计**: 总耗时、平均耗时、最大耗时、最小耗时
2. **按操作类型统计**: SELECT、INSERT、UPDATE、DELETE等操作的慢查询分布
3. **按表统计**: 各个表的慢查询次数和平均耗时
4. **Top N慢查询**: 最慢的N条查询详情
5. **相同SQL执行统计**: 相同SQL的不同执行次数和耗时

### 报告示例

```
================================================================================
慢查询分析报告
================================================================================

分析时间: 2025-01-29 10:30:00
日志文件: logs/host-service.log
总慢查询数: 45

--------------------------------------------------------------------------------
耗时统计
--------------------------------------------------------------------------------
  总耗时: 125000.50 ms (125.00 s)
  平均耗时: 2777.78 ms (2.78 s)
  最大耗时: 8500.00 ms (8.50 s)
  最小耗时: 2001.25 ms (2.00 s)

--------------------------------------------------------------------------------
按操作类型统计
--------------------------------------------------------------------------------
  SELECT      - 次数:    35, 平均耗时:  2500.00 ms
  UPDATE      - 次数:     8, 平均耗时:  3000.00 ms
  INSERT      - 次数:     2, 平均耗时:  5000.00 ms

--------------------------------------------------------------------------------
按表统计
--------------------------------------------------------------------------------
  host_rec                  - 次数:    25, 平均耗时:  2800.00 ms
  host_exec_log             - 次数:    15, 平均耗时:  2500.00 ms
  sys_user                  - 次数:     5, 平均耗时:  3000.00 ms

--------------------------------------------------------------------------------
Top 10 慢查询
--------------------------------------------------------------------------------

1. 耗时: 8500.00 ms (8.50 s)
   操作: SELECT
   表: host_rec
   SQL哈希: a1b2c3d4
   时间: 2025-01-29 10:25:30.123456
   SQL: SELECT * FROM host_rec WHERE del_flag = 0 AND host_state = 1 AND appr_state = 2...
   调用栈: services/host-service/app/services/browser_host_service.py:68 -> services/host-service/app/api/v1/endpoints/browser_hosts.py:45
```

## 性能影响

### 监控开销

- **正常查询**: 监控开销可忽略不计（仅时间戳记录）
- **慢查询**: 额外的日志记录和指标收集，但使用异步处理，不阻塞主流程

### 最佳实践

1. **合理设置阈值**: 根据业务需求设置慢查询阈值，避免记录过多正常查询
2. **定期分析**: 定期使用分析工具分析慢查询日志，识别性能瓶颈
3. **监控告警**: 在Grafana中配置慢查询告警，及时发现性能问题
4. **优化慢查询**: 根据分析结果优化慢查询，添加索引、优化SQL等

## 故障排查

### 慢查询未记录

1. **检查配置**: 确认 `ENABLE_SQL_MONITORING=true`
2. **检查阈值**: 确认查询耗时是否超过阈值
3. **检查日志级别**: 确认日志级别包含WARNING
4. **检查引擎**: 确认SQLAlchemy引擎已正确初始化

### 监控指标缺失

1. **检查Prometheus**: 确认Prometheus服务正常运行
2. **检查指标端点**: 访问 `/metrics` 端点查看指标
3. **检查标签**: 确认指标标签配置正确

### 分析工具无法解析日志

1. **检查日志格式**: 确认日志使用Loguru格式
2. **检查编码**: 确认日志文件使用UTF-8编码
3. **检查权限**: 确认有读取日志文件的权限

## 集成示例

### 在服务中使用

SQL性能监控会在服务启动时自动启用，无需额外代码：

```python
# services/host-service/app/main.py
from shared.app.service_factory import create_service_app

app = create_service_app(
    service_name="host-service",
    # SQL监控会自动启用，使用环境变量配置
)
```

### 手动启用监控

如果需要手动控制SQL监控：

```python
from shared.common.database import mariadb_manager

await mariadb_manager.connect(
    database_url="mysql+aiomysql://user:pass@host:port/db",
    enable_sql_monitoring=True,
    slow_query_threshold=2.0,
    service_name="host-service",
)
```

## 相关文档

- [监控指标收集规范](../.cursor/rules/microservice-monitoring.mdc)
- [数据库规范](../.cursor/rules/mariadb-database.mdc)
- [Grafana监控配置](../.cursor/rules/grafana-monitoring.mdc)

## 更新历史

- **2025-01-29**: 初始版本，实现SQL性能监控和慢查询检测功能

