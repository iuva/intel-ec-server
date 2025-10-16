# Jaeger 内存存储配置说明

## 配置变更

为了避免权限问题和简化部署，我们将 Jaeger 配置从 **Badger 持久化存储** 改为 **内存存储**。

## 配置对比

### 之前的配置（Badger 存储）

```yaml
jaeger:
  environment:
    SPAN_STORAGE_TYPE: badger
    BADGER_EPHEMERAL: "false"
    BADGER_DIRECTORY_VALUE: /badger/data
    BADGER_DIRECTORY_KEY: /badger/key
  volumes:
    - jaeger_data:/badger
```

**问题**：
- ❌ 需要配置数据卷权限
- ❌ 容器用户权限问题导致启动失败
- ❌ 需要额外的权限修复脚本

### 当前配置（内存存储）

```yaml
jaeger:
  environment:
    SPAN_STORAGE_TYPE: memory
    MEMORY_MAX_TRACES: 10000
    LOG_LEVEL: info
  # 不需要 volumes
```

**优点**：
- ✅ 无需配置权限
- ✅ 启动速度快
- ✅ 性能最佳
- ✅ 适合开发和测试环境

**缺点**：
- ⚠️ 重启后追踪数据会丢失
- ⚠️ 内存占用较大（取决于 MEMORY_MAX_TRACES）

## 适用场景

### 内存存储（当前配置）

**推荐用于**：
- ✅ 开发环境
- ✅ 测试环境
- ✅ 演示环境
- ✅ 短期调试

**不推荐用于**：
- ❌ 生产环境（需要长期保存追踪数据）
- ❌ 需要历史数据分析的场景

### 如果需要持久化存储

如果您需要在生产环境中使用持久化存储，有以下选项：

#### 选项 1：Badger 存储（需要权限配置）

```yaml
jaeger:
  user: "1000:1000"  # 使用非 root 用户
  environment:
    SPAN_STORAGE_TYPE: badger
    BADGER_EPHEMERAL: "false"
    BADGER_DIRECTORY_VALUE: /badger/data
    BADGER_DIRECTORY_KEY: /badger/key
  volumes:
    - jaeger_data:/badger
```

**配置步骤**：
1. 停止 Jaeger：`docker-compose stop jaeger`
2. 修复权限：
   ```bash
   docker run --rm \
     -v intel_ec_ms_jaeger_data:/badger \
     alpine:latest \
     sh -c "chown -R 1000:1000 /badger && mkdir -p /badger/data /badger/key"
   ```
3. 重启 Jaeger：`docker-compose up -d jaeger`

#### 选项 2：Elasticsearch 存储（推荐生产环境）

```yaml
# 添加 Elasticsearch 服务
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  ports:
    - "9200:9200"

# 配置 Jaeger 使用 Elasticsearch
jaeger:
  environment:
    SPAN_STORAGE_TYPE: elasticsearch
    ES_SERVER_URLS: http://elasticsearch:9200
  depends_on:
    - elasticsearch
```

**优点**：
- ✅ 强大的搜索和分析能力
- ✅ 可扩展性好
- ✅ 适合大规模部署
- ✅ 支持长期数据保留

#### 选项 3：Cassandra 存储（大规模生产环境）

```yaml
# 添加 Cassandra 服务
cassandra:
  image: cassandra:4.1
  environment:
    - CASSANDRA_CLUSTER_NAME=jaeger
  ports:
    - "9042:9042"

# 配置 Jaeger 使用 Cassandra
jaeger:
  environment:
    SPAN_STORAGE_TYPE: cassandra
    CASSANDRA_SERVERS: cassandra
    CASSANDRA_KEYSPACE: jaeger_v1_dc1
  depends_on:
    - cassandra
```

## 配置参数说明

### 内存存储参数

| 参数 | 说明 | 默认值 | 推荐值 |
|------|------|--------|--------|
| `MEMORY_MAX_TRACES` | 最大追踪数量 | 10000 | 10000-50000 |
| `LOG_LEVEL` | 日志级别 | info | info/debug |

### 内存使用估算

- 每个 trace 约占用 1-10 KB（取决于 span 数量）
- `MEMORY_MAX_TRACES=10000` 约占用 10-100 MB 内存
- `MEMORY_MAX_TRACES=50000` 约占用 50-500 MB 内存

## 监控和维护

### 查看 Jaeger 状态

```bash
# 检查容器状态
docker-compose ps jaeger

# 查看日志
docker-compose logs -f jaeger

# 访问 UI
open http://localhost:16686
```

### 查看内存使用

```bash
# 查看容器资源使用
docker stats intel-jaeger

# 查看详细信息
docker inspect intel-jaeger | jq '.[0].HostConfig.Memory'
```

### 清理追踪数据

使用内存存储时，重启容器即可清理所有数据：

```bash
docker-compose restart jaeger
```

## 性能对比

| 存储类型 | 启动速度 | 查询性能 | 写入性能 | 持久化 | 配置复杂度 |
|---------|---------|---------|---------|--------|-----------|
| **内存** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐⭐⭐⭐ |
| **Badger** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ⭐⭐⭐ |
| **Elasticsearch** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | ⭐⭐ |
| **Cassandra** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ⭐ |

## 常见问题

### Q: 为什么选择内存存储？

**A**: 内存存储是最简单、最快速的方案，适合开发和测试环境。无需配置权限，启动即用。

### Q: 数据会丢失吗？

**A**: 是的，重启容器后所有追踪数据会丢失。如果需要持久化，请使用 Badger、Elasticsearch 或 Cassandra。

### Q: 如何增加存储容量？

**A**: 修改 `MEMORY_MAX_TRACES` 参数：

```yaml
environment:
  MEMORY_MAX_TRACES: 50000  # 增加到 50000
```

### Q: 内存存储会影响性能吗？

**A**: 不会，内存存储性能最佳。但需要注意内存使用量。

### Q: 如何切换到持久化存储？

**A**: 参考上面的"如果需要持久化存储"部分，选择合适的存储方案。

## 相关资源

- [Jaeger 官方文档](https://www.jaegertracing.io/docs/)
- [Jaeger 存储选项](https://www.jaegertracing.io/docs/deployment/#storage-backends)
- [Docker Compose 配置](../docker-compose.yml)

---

**最后更新**: 2025-01-29
**当前配置**: 内存存储
**适用环境**: 开发/测试
