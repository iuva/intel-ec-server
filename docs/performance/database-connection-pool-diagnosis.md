# 数据库连接池阻塞诊断指南

## 🔍 如何在日志中识别连接阻塞问题

### 1. 连接池状态监控日志

**日志格式**：
```
数据库连接池状态
{
  "pool_size": 200,
  "max_overflow": 500,
  "max_connections": 700,
  "checked_in": 50,
  "checked_out": 650,
  "overflow": 450,
  "invalid": 0,
  "total_connections": 700,
  "usage_percent": 92.86,
  "status": "connected"
}
```

**监控频率**：每30秒自动记录一次

**关键指标**：
- `usage_percent`: 连接池使用率
  - **< 80%**: 正常
  - **80-95%**: 警告（黄色日志）
  - **> 95%**: 严重警告（红色日志）

- `checked_out`: 当前使用中的连接数
  - 如果接近 `max_connections`，说明连接池即将耗尽

- `overflow`: 溢出连接数
  - 如果持续较高，说明基础连接池不足

### 2. 连接获取等待时间日志

**正常情况**（等待时间 < 0.5秒）：
```
DEBUG: 数据库连接获取
{
  "wait_time_seconds": 0.023,
  "pool_usage_percent": 45.2
}
```

**警告情况**（等待时间 0.5-1秒）：
```
WARNING: 数据库连接获取耗时较长
{
  "wait_time_seconds": 0.856,
  "pool_usage_percent": 78.5,
  "checked_out": 550,
  "max_connections": 700
}
```

**严重情况**（等待时间 > 1秒）：
```
WARNING: 数据库连接获取耗时较长
{
  "wait_time_seconds": 5.234,
  "pool_usage_percent": 95.7,
  "checked_out": 670,
  "max_connections": 700
}
```

**连接获取失败**：
```
ERROR: 数据库连接获取失败
{
  "wait_time_seconds": 30.0,
  "pool_usage_percent": 100.0,
  "checked_out": 700,
  "max_connections": 700,
  "error_type": "TimeoutError",
  "error_message": "Connection pool exhausted"
}
```

### 3. 查询开始/结束时的连接池状态

**查询开始时**（如果使用率 >= 80%）：
```
WARNING: 数据库连接池使用率较高，开始查询
{
  "usage_percent": 85.3,
  "checked_out": 597,
  "max_connections": 700
}
```

**查询完成时**（如果使用率 >= 80%）：
```
WARNING: 数据库连接池使用率较高，查询完成
{
  "usage_percent": 82.1,
  "checked_out": 575,
  "max_connections": 700
}
```

## 🔎 诊断步骤

### 步骤 1: 查看连接池状态日志

```bash
# 查看最近的连接池状态
docker-compose logs host-service | grep "数据库连接池状态" | tail -20

# 查看连接池使用率趋势
docker-compose logs host-service | grep "数据库连接池状态" | jq -r '.usage_percent' | tail -20
```

### 步骤 2: 查看连接获取等待时间

```bash
# 查看连接获取等待时间超过1秒的日志
docker-compose logs host-service | grep "数据库连接获取耗时较长" | tail -20

# 统计连接获取等待时间分布
docker-compose logs host-service | grep "数据库连接获取" | jq -r '.wait_time_seconds' | \
  awk '{if($1<0.5) a++; else if($1<1.0) b++; else c++} END {print "正常(<0.5s):", a, "警告(0.5-1s):", b, "严重(>1s):", c}'
```

### 步骤 3: 查看连接池耗尽事件

```bash
# 查看连接获取失败的日志
docker-compose logs host-service | grep "数据库连接获取失败" | tail -20

# 查看连接池使用率超过95%的日志
docker-compose logs host-service | grep "数据库连接池使用率过高" | tail -20
```

### 步骤 4: 分析长时间持有连接的请求

```bash
# 查看查询开始和结束时的连接池状态
docker-compose logs host-service | grep -E "(开始查询|查询完成)" | tail -40

# 分析单个请求的连接占用时间
docker-compose logs host-service | grep -A 5 "开始查询可用主机列表" | \
  grep -E "(开始查询|查询完成|连接池)" | tail -30
```

## 📊 常见问题诊断

### 问题 1: 连接池使用率持续 > 95%

**症状**：
```
数据库连接池使用率过高（严重）
{
  "usage_percent": 98.5,
  "checked_out": 690,
  "max_connections": 700
}
```

**可能原因**：
1. 并发请求数超过连接池容量
2. 请求长时间持有数据库连接
3. 数据库查询执行时间过长

**解决方案**：
1. 增加连接池大小（`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`）
2. 优化数据库查询，减少连接占用时间
3. 检查是否有长时间运行的查询

### 问题 2: 连接获取等待时间 > 5秒

**症状**：
```
WARNING: 数据库连接获取耗时较长
{
  "wait_time_seconds": 8.234,
  "pool_usage_percent": 99.2
}
```

**可能原因**：
1. 连接池已耗尽，请求在等待连接释放
2. 有请求长时间持有连接（可能是慢查询）

**解决方案**：
1. 检查慢查询日志
2. 优化长时间运行的查询
3. 增加连接池大小
4. 检查是否有连接泄漏（连接未正确关闭）

### 问题 3: 连接获取失败（TimeoutError）

**症状**：
```
ERROR: 数据库连接获取失败
{
  "wait_time_seconds": 30.0,
  "error_type": "TimeoutError",
  "error_message": "Connection pool exhausted"
}
```

**可能原因**：
1. 连接池完全耗尽
2. 所有连接都被长时间占用
3. 连接池配置的 `pool_timeout` 过短

**解决方案**：
1. 立即增加连接池大小
2. 检查并优化慢查询
3. 检查是否有连接泄漏
4. 考虑增加 `pool_timeout` 配置

## 🔧 实时监控命令

### 监控连接池状态（实时）

```bash
# 实时查看连接池状态日志
docker-compose logs -f host-service | grep --line-buffered "数据库连接池状态"

# 实时查看连接获取等待时间
docker-compose logs -f host-service | grep --line-buffered "数据库连接获取"
```

### 统计连接池使用情况

```bash
# 统计最近100条连接池状态日志的平均使用率
docker-compose logs host-service | grep "数据库连接池状态" | tail -100 | \
  jq -r '.usage_percent' | awk '{sum+=$1; count++} END {print "平均使用率:", sum/count "%"}'

# 统计连接获取等待时间分布
docker-compose logs host-service | grep "数据库连接获取" | \
  jq -r '.wait_time_seconds' | awk '{
    if($1<0.1) a++; 
    else if($1<0.5) b++; 
    else if($1<1.0) c++; 
    else if($1<5.0) d++; 
    else e++
  } END {
    print "等待时间分布:"
    print "  < 0.1s:", a
    print "  0.1-0.5s:", b
    print "  0.5-1.0s:", c
    print "  1.0-5.0s:", d
    print "  > 5.0s:", e
  }'
```

## 📈 性能指标阈值

### 正常指标
- 连接池使用率: < 80%
- 连接获取等待时间: < 0.5秒
- 连接获取失败率: < 0.1%

### 警告指标
- 连接池使用率: 80-95%
- 连接获取等待时间: 0.5-1秒
- 连接获取失败率: 0.1-1%

### 严重指标
- 连接池使用率: > 95%
- 连接获取等待时间: > 1秒
- 连接获取失败率: > 1%

## 🎯 优化建议

### 如果连接池使用率持续 > 80%

1. **立即优化**：
   - 增加连接池大小
   - 检查并优化慢查询
   - 检查是否有连接泄漏

2. **短期优化**：
   - 优化数据库查询逻辑
   - 减少数据库连接占用时间
   - 使用连接复用（已在代码中实现）

3. **长期优化**：
   - 引入 Redis 缓存，减少数据库查询
   - 优化数据库索引
   - 考虑读写分离

### 如果连接获取等待时间 > 1秒

1. **检查慢查询**：
   ```bash
   # 查看慢查询日志
   docker-compose logs host-service | grep "慢查询" | tail -20
   ```

2. **检查连接占用时间**：
   - 查看查询开始和结束时的连接池状态
   - 分析哪些查询占用连接时间最长

3. **优化查询逻辑**：
   - 减少循环中的数据库查询
   - 使用批量查询
   - 复用数据库会话

## 🔗 相关文档

- [服务性能优化方案](./service-optimization-plan.md)
- [k6 压测结果分析](./k6-load-test-analysis.md)
- [数据库连接池配置](../../shared/common/database.py)

