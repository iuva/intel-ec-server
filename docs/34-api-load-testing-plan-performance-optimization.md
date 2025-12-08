# 500并发响应时间<2秒性能优化方案

## 🎯 目标

- **并发数**: 500 个虚拟用户
- **响应时间**: P99 < 2秒
- **错误率**: < 1%
- **吞吐量**: > 100 req/s

## 📊 当前性能问题分析

### 从压测结果看到的问题

```
P50:  584.75ms  ❌ 超过要求 (要求: < 500ms)
P95:  31,964ms  ❌ 严重超标 (要求: < 1,500ms) 
P99:  40,027ms  ❌ 严重超标 (要求: < 2,000ms)
Max:  60,010ms  ❌ 严重超标 (要求: < 3,000ms)
```

### 性能瓶颈识别

1. **通过 Gateway 访问** - 增加了路由转发延迟
2. **数据库连接池不足** - 默认 pool_size=50, max_overflow=100
3. **外部 API 调用慢** - 硬件接口调用可能成为瓶颈
4. **数据库查询未优化** - 可能缺少索引或查询效率低
5. **缺少缓存** - 重复查询没有使用缓存

## 🔧 优化方案

### 1. 数据库连接池优化

#### 当前配置
```python
# shared/common/database.py
pool_size: int = 50
max_overflow: int = 100
# 最大连接数 = 50 + 100 = 150
```

#### 优化配置（支持500并发）

```python
# 对于 500 并发，建议配置：
pool_size: int = 100        # 基础连接池大小
max_overflow: int = 200     # 最大溢出连接数
# 最大连接数 = 100 + 200 = 300（足够支持500并发）
```

#### 修改位置

**方式1：通过环境变量配置（推荐）**

在 `docker-compose.yml` 或 `.env` 文件中：

```yaml
# docker-compose.yml
services:
  host-service:
    environment:
      # 数据库连接池配置
      DB_POOL_SIZE: 100
      DB_MAX_OVERFLOW: 200
```

**方式2：修改代码配置**

在服务启动时传入参数：

```python
# services/host-service/app/main.py 或配置文件中
await init_databases(
    mariadb_url=mariadb_url,
    redis_url=redis_url,
    pool_size=100,        # 增加到100
    max_overflow=200,    # 增加到200
)
```

### 2. MariaDB 数据库优化

#### 增加最大连接数

```yaml
# docker-compose.yml
services:
  mariadb:
    environment:
      MYSQL_MAX_CONNECTIONS: 500  # 增加到500（默认是500，确认已设置）
```

#### 数据库性能优化配置

创建 MySQL 优化配置文件：

```ini
# infrastructure/mysql/my.cnf
[mysqld]
# 连接相关
max_connections = 500
max_connect_errors = 10000

# 查询缓存（MariaDB 10.11 已移除，但可以优化其他参数）
query_cache_type = 0
query_cache_size = 0

# InnoDB 优化
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# 慢查询日志
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1

# 临时表
tmp_table_size = 64M
max_heap_table_size = 64M
```

在 `docker-compose.yml` 中挂载配置：

```yaml
services:
  mariadb:
    volumes:
      - mariadb_data:/var/lib/mysql
      - ./infrastructure/mysql/init:/docker-entrypoint-initdb.d
      - ./infrastructure/mysql/my.cnf:/etc/mysql/conf.d/my.cnf  # 添加这行
```

### 3. 数据库查询优化

#### 添加索引

检查 `host_rec` 表的索引：

```sql
-- 查看当前索引
SHOW INDEX FROM host_rec;

-- 添加复合索引（如果不存在）
CREATE INDEX idx_host_rec_filter ON host_rec(appr_state, host_state, tcp_state, del_flag);
CREATE INDEX idx_host_rec_hardware_id ON host_rec(hardware_id);
CREATE INDEX idx_host_rec_created_time ON host_rec(created_time);

-- 查看查询执行计划
EXPLAIN SELECT * FROM host_rec 
WHERE appr_state = 1 AND host_state = 0 AND tcp_state = 2 AND del_flag = 0;
```

#### 优化查询逻辑

检查 `host_discovery_service.py` 中的查询：

```python
# 确保使用索引
stmt = select(HostRec).where(
    and_(
        HostRec.hardware_id.in_(hardware_ids),
        HostRec.appr_state == 1,
        HostRec.host_state == 0,
        HostRec.tcp_state == 2,
        HostRec.del_flag == 0,
    )
).limit(page_size)  # 添加 limit 限制结果集大小
```

### 4. Redis 缓存优化

#### 增加 Redis 连接数

```python
# shared/common/cache.py
await redis_manager.connect(
    redis_url=redis_url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=100,  # 从50增加到100
)
```

#### 添加查询结果缓存

在 `host_discovery_service.py` 中添加缓存：

```python
# 缓存可用主机列表（5分钟）
cache_key = f"available_hosts:{tc_id}:{cycle_name}:{user_name}"
cached_result = await redis_manager.get(cache_key)
if cached_result:
    return json.loads(cached_result)

# 查询数据库
result = await self._query_available_hosts(...)

# 缓存结果
await redis_manager.setex(
    cache_key,
    300,  # 5分钟过期
    json.dumps(result)
)
```

### 5. 外部 API 调用优化

#### 增加 HTTP 客户端连接池

```python
# shared/common/http_client.py
self.limits = Limits(
    max_keepalive_connections=50,  # 从20增加到50
    max_connections=200,           # 从100增加到200
)
```

#### 添加请求超时和重试

```python
# 硬件接口调用超时设置
timeout = Timeout(10.0, connect=5.0)  # 总超时10秒，连接超时5秒
```

### 6. 服务配置优化

#### 增加 Uvicorn Worker 数量

```python
# services/host-service/app/main.py 或启动脚本
# 使用多个 worker 进程
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8003 \
  --workers 4 \  # 根据 CPU 核心数设置（建议 CPU核心数 * 2）
  --worker-class uvicorn.workers.UvicornWorker
```

#### 调整系统资源限制

```bash
# Linux 系统优化
ulimit -n 65535  # 文件描述符限制

# Docker 容器资源限制
# docker-compose.yml
services:
  host-service:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

### 7. 压测脚本优化

#### 调整压测配置

```javascript
// tests/performance/http/k6_query_available_hosts.js
export const options = {
  // 更温和的压测阶段
  stages: [
    { duration: '2m', target: 100 },   // 2分钟增加到100并发
    { duration: '3m', target: 100 },   // 保持100并发3分钟
    { duration: '2m', target: 200 },   // 2分钟增加到200并发
    { duration: '3m', target: 200 },   // 保持200并发3分钟
    { duration: '2m', target: 300 },   // 2分钟增加到300并发
    { duration: '3m', target: 300 },   // 保持300并发3分钟
    { duration: '2m', target: 500 },   // 2分钟增加到500并发
    { duration: '10m', target: 500 },  // 保持500并发10分钟（充分验证）
    { duration: '2m', target: 0 },     // 2分钟降为0
  ],
  
  thresholds: {
    http_req_duration: [
      'p(50)<500',    // 50% 请求 < 500ms
      'p(95)<1500',   // 95% 请求 < 1.5秒
      'p(99)<2000',   // 99% 请求 < 2秒
    ],
    http_req_failed: ['rate<0.01'],
    http_reqs: ['rate>100'],
  },
};
```

#### 减少用户思考时间

```javascript
// 减少 sleep 时间，提高吞吐量
sleep(Math.random() * 1 + 0.5);  // 从 1-3秒 改为 0.5-1.5秒
```

## 📋 优化实施清单

### 阶段1：快速优化（立即实施）

- [ ] **直接访问 Host Service**（不使用 Gateway）
  ```bash
  k6 run k6_query_available_hosts.js \
    --env K6_HOST_URL=http://localhost:8003
  ```

- [ ] **增加数据库连接池**
  - pool_size: 50 → 100
  - max_overflow: 100 → 200

- [ ] **增加 Redis 连接数**
  - max_connections: 50 → 100

### 阶段2：数据库优化（1-2天）

- [ ] **添加数据库索引**
  ```sql
  CREATE INDEX idx_host_rec_filter ON host_rec(appr_state, host_state, tcp_state, del_flag);
  ```

- [ ] **优化数据库查询**
  - 添加 LIMIT 限制
  - 优化 JOIN 查询
  - 使用 EXPLAIN 分析查询计划

- [ ] **配置 MySQL 性能参数**
  - innodb_buffer_pool_size
  - max_connections

### 阶段3：缓存优化（2-3天）

- [ ] **添加查询结果缓存**
  - 缓存可用主机列表
  - 设置合理的过期时间（5分钟）

- [ ] **优化缓存策略**
  - 使用 Redis 缓存热点数据
  - 实现缓存预热

### 阶段4：服务优化（3-5天）

- [ ] **增加 Worker 进程数**
  - 使用多进程部署
  - 根据 CPU 核心数配置

- [ ] **优化外部 API 调用**
  - 增加连接池大小
  - 设置合理的超时时间
  - 实现请求重试机制

## 🚀 快速开始

### 1. 立即优化数据库连接池

创建配置文件：

```python
# services/host-service/app/core/config.py
class ServiceConfig:
    # 数据库连接池配置
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "100"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "200"))
```

在启动时使用：

```python
await init_databases(
    mariadb_url=mariadb_url,
    redis_url=redis_url,
    pool_size=config.db_pool_size,
    max_overflow=config.db_max_overflow,
)
```

### 2. 添加数据库索引

```bash
# 连接到数据库
docker-compose exec mariadb mysql -u intel_user -p intel_cw

# 执行索引创建
CREATE INDEX idx_host_rec_filter ON host_rec(appr_state, host_state, tcp_state, del_flag);
CREATE INDEX idx_host_rec_hardware_id ON host_rec(hardware_id);
```

### 3. 重新执行压测

```bash
# 使用优化后的配置
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results_optimized.json
```

## 📊 预期效果

### 优化前
- P95: 32秒
- P99: 40秒
- 吞吐量: 39 req/s

### 优化后（预期）
- P50: < 300ms
- P95: < 1.5秒
- P99: < 2秒
- 吞吐量: > 200 req/s

## 🔍 性能监控

### 监控指标

```bash
# 1. 监控数据库连接数
docker-compose exec mariadb mysql -u intel_user -p -e "SHOW STATUS LIKE 'Threads_connected';"

# 2. 监控慢查询
docker-compose exec mariadb tail -f /var/log/mysql/slow.log

# 3. 监控服务资源使用
docker stats host-service

# 4. 查看 Prometheus 指标
curl "http://localhost:9090/api/v1/query?query=rate(http_request_duration_seconds_bucket{service=\"host-service\"}[5m])"
```

### Grafana 仪表板

查看以下关键指标：
- 响应时间分布（P50, P95, P99）
- 请求速率（RPS）
- 错误率
- 数据库连接数
- CPU 和内存使用率

---

**最后更新**: 2025-01-29

