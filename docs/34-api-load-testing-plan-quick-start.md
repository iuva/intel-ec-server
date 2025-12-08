# 500并发响应时间<2秒快速实施指南

## 🎯 目标

- **并发数**: 500 个虚拟用户
- **响应时间**: P99 < 2秒
- **错误率**: < 1%
- **吞吐量**: > 100 req/s

## ⚡ 快速实施步骤（5分钟）

### 步骤1：配置数据库连接池（已自动优化）

代码已更新，默认值已优化为：
- `DB_POOL_SIZE=100`（基础连接池）
- `DB_MAX_OVERFLOW=200`（最大溢出连接）
- **总连接数 = 300**（足够支持500并发）

**无需手动配置，代码已自动应用！**

如果需要自定义，在 `docker-compose.yml` 中添加：

```yaml
services:
  host-service:
    environment:
      DB_POOL_SIZE: 100
      DB_MAX_OVERFLOW: 200
```

### 步骤2：直接访问 Host Service（不使用 Gateway）

```bash
# ✅ 正确：直接访问 Host Service
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

**重要**: 不要使用 `http://localhost:8000`（Gateway），直接使用 `http://localhost:8003`（Host Service）

### 步骤3：添加数据库索引（可选，但强烈推荐）

```bash
# 连接到数据库
docker-compose exec mariadb mysql -u intel_user -pintel_***REMOVED*** intel_cw

# 执行索引创建
CREATE INDEX IF NOT EXISTS idx_host_rec_filter ON host_rec(appr_state, host_state, tcp_state, del_flag);
CREATE INDEX IF NOT EXISTS idx_host_rec_hardware_id ON host_rec(hardware_id);
CREATE INDEX IF NOT EXISTS idx_host_rec_created_time ON host_rec(created_time);
```

### 步骤4：重启服务应用配置

```bash
# 重启 Host Service 以应用新的连接池配置
docker-compose restart host-service

# 查看日志确认配置已应用
docker-compose logs -f host-service | grep "数据库连接"
```

### 步骤5：执行压测

```bash
cd tests/performance/http

# 执行压测（500并发，响应时间<2秒）
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

## 📊 预期结果

### 优化前
- P95: 32秒 ❌
- P99: 40秒 ❌
- 吞吐量: 39 req/s ❌

### 优化后（预期）
- P50: < 300ms ✅
- P95: < 1.5秒 ✅
- P99: < 2秒 ✅
- 吞吐量: > 200 req/s ✅

## 🔍 验证优化效果

### 1. 检查数据库连接池配置

```bash
# 查看服务日志，确认连接池配置
docker-compose logs host-service | grep -i "pool_size\|max_overflow"
```

### 2. 监控数据库连接数

```bash
# 查看当前数据库连接数
docker-compose exec mariadb mysql -u intel_user -pintel_***REMOVED*** -e "SHOW STATUS LIKE 'Threads_connected';"
```

### 3. 查看压测结果

```bash
# 查看 k6 输出结果
cat results/k6_results.json | jq 'select(.type=="Point" and .metric=="http_req_duration") | .data.value' | sort -n | tail -100
```

## 🚨 如果仍然不达标

### 进一步优化选项

#### 1. 增加数据库最大连接数

```yaml
# docker-compose.yml
services:
  mariadb:
    environment:
      MYSQL_MAX_CONNECTIONS: 500  # 确保足够大
```

#### 2. 添加 Redis 缓存（需要代码修改）

在 `host_discovery_service.py` 中添加查询结果缓存：

```python
# 缓存可用主机列表（5分钟）
cache_key = f"available_hosts:{tc_id}:{cycle_name}:{user_name}"
cached_result = await redis_manager.get(cache_key)
if cached_result:
    return json.loads(cached_result)
```

#### 3. 优化外部 API 调用

如果硬件接口调用慢，考虑：
- 增加 HTTP 客户端连接池
- 设置合理的超时时间
- 实现请求重试机制

#### 4. 使用多进程部署

```bash
# 使用多个 worker 进程
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8003 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

## 📋 完整优化清单

参考详细优化文档：`docs/34-api-load-testing-plan-performance-optimization.md`

### 已自动应用 ✅
- [x] 数据库连接池优化（pool_size=100, max_overflow=200）
- [x] 压测脚本优化（减少思考时间）

### 需要手动配置 ⚠️
- [ ] 直接访问 Host Service（不使用 Gateway）
- [ ] 添加数据库索引（强烈推荐）
- [ ] 重启服务应用配置

### 可选优化 🔧
- [ ] 添加 Redis 缓存
- [ ] 优化外部 API 调用
- [ ] 使用多进程部署
- [ ] 增加数据库最大连接数

## 🎯 关键要点

1. **直接访问 Host Service** - 避免 Gateway 带来的延迟
2. **数据库连接池已优化** - 代码已自动应用，无需手动配置
3. **添加数据库索引** - 显著提升查询性能
4. **逐步增加并发** - 压测脚本已优化，逐步增加到500并发

---

**最后更新**: 2025-01-29

