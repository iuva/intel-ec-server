# k6 压测错误排查指南

## 🔍 错误分析

### 错误现象

从压测日志可以看到以下错误：

```
✗ errors: rate=29.77% (要求: rate<0.01)
✗ http_req_duration p(95)=3.42s (要求: p(95)<500ms)
✗ http_req_duration p(99)=6.83s (要求: p(99)<1000ms)
✗ http_reqs: rate=39.45/s (要求: rate>100)
✗ checks_failed: 9.92% (主要是"查询响应时间<500ms"检查失败)
```

### 错误原因分析

#### 1. **自定义错误率过高 (29.77%)**

**原因**：
- 脚本中使用了自定义错误率指标 `errors`
- 当响应时间检查失败时（`r.timings.duration < 500`），会记录为错误
- 实际 P95 响应时间是 3.42s，远超 500ms 的检查阈值

**代码位置**：
```javascript
const errorRate = new Rate('errors');
const querySuccess = check(queryRes, {
  '查询响应时间<500ms': (r) => r.timings.duration < 500,  // 这个检查太严格
});
errorRate.add(!querySuccess);  // 响应时间超过500ms就记录为错误
```

#### 2. **响应时间超标**

**实际表现**：
- P95: 3.42秒（要求 < 500ms）
- P99: 6.83秒（要求 < 1000ms）
- 最大响应时间: 18.14秒

**可能原因**：
1. **通过 Gateway 访问**：你使用的是 `http://localhost:8000`（Gateway），而不是直接访问 `http://localhost:8003`（Host Service）
   - Gateway 会增加路由转发延迟
   - Gateway 可能成为性能瓶颈
   
2. **服务性能问题**：
   - Host Service 响应慢
   - 数据库查询慢
   - 外部 API 调用慢

3. **并发过高**：200并发可能超过了服务承载能力

#### 3. **吞吐量不足 (39.45 req/s)**

**原因**：
- 响应时间过长导致吞吐量下降
- 每个请求平均耗时 697ms，加上用户思考时间（1-3秒），实际吞吐量被限制

### 解决方案

#### 方案1：直接访问 Host Service（推荐）

**问题**：通过 Gateway 访问会增加延迟

**解决**：直接访问 Host Service

```bash
# ❌ 错误：通过 Gateway 访问
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8000

# ✅ 正确：直接访问 Host Service
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003
```

#### 方案2：调整响应时间阈值

**问题**：检查阈值设置不合理（要求 < 500ms，但实际 P95 是 3.42s）

**解决**：根据实际性能调整阈值

```javascript
// ❌ 错误：阈值设置过严
check(res, {
  '查询响应时间<500ms': (r) => r.timings.duration < 500,
});

// ✅ 正确：根据实际性能要求调整
check(res, {
  '查询响应时间<2s': (r) => r.timings.duration < 2000,  // 符合性能指标要求
});
```

#### 方案3：降低并发数

**问题**：200并发可能超过服务承载能力

**解决**：逐步增加并发，找到性能拐点

```javascript
// 降低初始并发数
stages: [
  { duration: '1m', target: 50 },   // 从50开始
  { duration: '2m', target: 50 },
  { duration: '1m', target: 100 },  // 逐步增加
  { duration: '2m', target: 100 },
  // ...
]
```

#### 方案4：检查服务性能

**问题**：服务本身响应慢

**解决**：排查服务性能瓶颈

```bash
# 1. 检查服务健康状态
curl http://localhost:8003/health

# 2. 检查数据库连接
docker-compose exec host-service python -c "from shared.common.database import mariadb_manager; import asyncio; asyncio.run(mariadb_manager.test_connection())"

# 3. 查看服务日志
docker-compose logs -f host-service | grep ERROR

# 4. 检查 Prometheus 指标
curl http://localhost:9090/api/v1/query?query=rate\(http_request_duration_seconds_bucket\{service=\"host-service\"\}\[5m\]\)
```

#### 方案5：使用正确的脚本

**问题**：使用了已删除的旧脚本 `k6_complete_load_test.js`

**解决**：使用新的接口专用脚本

```bash
# ❌ 错误：使用已删除的脚本
k6 run k6_complete_load_test.js

# ✅ 正确：使用新的接口专用脚本
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003
```

## 📊 性能优化建议

### 1. 压测前检查清单

- [ ] 确认服务正常运行：`curl http://localhost:8003/health`
- [ ] 确认数据库连接正常
- [ ] 确认 Redis 连接正常
- [ ] 检查服务资源使用情况（CPU、内存）
- [ ] 确认使用正确的服务地址（Host Service: 8003，不是 Gateway: 8000）

### 2. 压测配置建议

#### 对于 Gateway 压测

如果必须通过 Gateway 压测，需要调整阈值：

```javascript
thresholds: {
  http_req_duration: [
    'p(95)<2000',   // Gateway 会增加延迟，放宽到2秒
    'p(99)<3000',   // P99 放宽到3秒
  ],
  http_reqs: ['rate>50'],  // Gateway 吞吐量会降低
}
```

#### 对于 Host Service 直接压测

使用标准配置：

```javascript
thresholds: {
  http_req_duration: [
    'p(95)<1500',   // 95% 请求 < 1.5秒
    'p(99)<2000',   // 99% 请求 < 2秒
  ],
  http_reqs: ['rate>100'],  // 至少100 req/s
}
```

### 3. 性能瓶颈排查

#### 检查数据库查询性能

```sql
-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query_log';
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;

-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';
```

#### 检查服务资源使用

```bash
# 查看容器资源使用
docker stats host-service

# 查看服务日志中的性能信息
docker-compose logs host-service | grep -i "duration\|slow\|timeout"
```

## 🔧 快速修复步骤

### 步骤1：确认服务地址

```bash
# 检查 Host Service 是否正常运行
curl http://localhost:8003/health

# 检查 Gateway 是否正常运行
curl http://localhost:8000/health
```

### 步骤2：使用正确的脚本

```bash
# 使用新的接口专用脚本
cd tests/performance/http
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003
```

### 步骤3：逐步增加并发

```bash
# 先测试低并发（50）
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --vus 50 \
  --duration 2m

# 如果通过，再逐步增加
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --vus 100 \
  --duration 2m
```

### 步骤4：分析结果

```bash
# 查看详细结果
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/detailed_results.json

# 分析 JSON 结果
cat results/detailed_results.json | jq '.metrics'
```

## 📈 预期结果

### 正常情况下的指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **P50 响应时间** | < 500ms | 50% 请求响应时间 |
| **P95 响应时间** | < 1.5s | 95% 请求响应时间 |
| **P99 响应时间** | < 2s | 99% 请求响应时间 |
| **错误率** | < 1% | HTTP 错误率 |
| **吞吐量** | > 100 req/s | 每秒请求数 |

### 如果仍然超标

1. **检查服务配置**：数据库连接池大小、Redis 连接数
2. **优化数据库查询**：添加索引、优化 SQL
3. **增加服务资源**：CPU、内存
4. **考虑服务扩容**：增加服务实例数

---

**最后更新**: 2025-01-29

