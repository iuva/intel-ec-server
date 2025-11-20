# 监控系统快速参考

## 🚀 快速启动

```bash
# 一键启动监控系统
./scripts/start_monitoring.sh

# 或手动启动
docker-compose up -d prometheus grafana
```

## 📊 访问地址

| 服务 | 地址 | 用途 | 凭据 |
|------|------|------|------|
| **Prometheus** | http://localhost:9090 | 指标采集和查询 | 无需认证 |
| **Grafana** | http://localhost:3000 | 数据可视化 | admin / ***REMOVED*** |

## 📈 主要指标

### 服务健康状态
```promql
up{job=~".*-service"}
```

### 请求速率 (RPS)
```promql
rate(http_requests_total{job=~".*-service"}[5m])
```

### 响应时间 (P95)
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=~".*-service"}[5m]))
```

### 错误率
```promql
rate(http_requests_total{job=~".*-service",status=~"5.."}[5m]) / rate(http_requests_total{job=~".*-service"}[5m]) * 100
```

## 🎯 常用操作

### 查看服务状态
```bash
docker-compose ps prometheus grafana
```

### 查看日志
```bash
# Prometheus 日志
docker-compose logs -f prometheus

# Grafana 日志
docker-compose logs -f grafana
```

### 重启服务
```bash
docker-compose restart prometheus grafana
```

### 停止服务
```bash
docker-compose stop prometheus grafana
```

## 🔍 Prometheus 查询示例

### 1. 查看所有服务状态
```promql
up
```

### 2. 查看特定服务的请求数
```promql
http_requests_total{service="gateway-service"}
```

### 3. 查看最近5分钟的平均响应时间
```promql
rate(http_request_duration_seconds_sum{job="gateway-service"}[5m]) / rate(http_request_duration_seconds_count{job="gateway-service"}[5m])
```

### 4. 查看错误请求数
```promql
http_requests_total{status=~"5.."}
```

### 5. 查看服务的CPU使用率
```promql
rate(process_cpu_seconds_total{job=~".*-service"}[5m]) * 100
```

## 📊 Grafana 仪表板

### 预配置仪表板

1. **Intel EC 微服务概览**
   - 服务健康状态
   - 请求速率 (RPS)
   - 响应时间 (P95)
   - 错误率

### 创建自定义仪表板

1. 登录 Grafana
2. 点击左侧菜单 "+" → "Dashboard"
3. 点击 "Add new panel"
4. 在 Query 中输入 PromQL 查询
5. 配置可视化选项
6. 保存仪表板

## 🔧 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| Prometheus 配置 | `infrastructure/prometheus/prometheus.yml` | 抓取配置 |
| Grafana 数据源 | `infrastructure/grafana/provisioning/datasources/` | 自动配置数据源 |
| Grafana 仪表板 | `infrastructure/grafana/dashboards/` | 预配置仪表板 |

## 🐛 故障排查

### Prometheus 无法启动

**检查配置文件**：
```bash
# 验证配置文件语法
docker run --rm -v $(pwd)/infrastructure/prometheus:/etc/prometheus prom/prometheus:v2.48.0 promtool check config /etc/prometheus/prometheus.yml
```

**查看日志**：
```bash
docker-compose logs prometheus
```

### Grafana 无法访问

**检查服务状态**：
```bash
docker-compose ps grafana
```

**重置管理员密码**：
```bash
docker-compose exec grafana grafana-cli admin reset-admin-***REMOVED***word new***REMOVED***word
```

### 指标数据不显示

**检查服务是否暴露 /metrics 端点**：
```bash
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics
```

**检查 Prometheus 目标状态**：
访问 http://localhost:9090/targets

### 仪表板显示 "No Data"

1. 检查 Prometheus 是否正在采集数据
2. 检查查询语句是否正确
3. 检查时间范围是否合适
4. 检查数据源配置是否正确

## 📚 相关资源

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [完整监控指南](prometheus-grafana-setup.md)

## 🎓 最佳实践

### 1. 指标命名规范

```
# 格式：<namespace>_<subsystem>_<name>_<unit>
http_requests_total          # 计数器
http_request_duration_seconds # 直方图
service_up                    # 仪表盘
```

### 2. 标签使用

```promql
# 好的标签
http_requests_total{service="gateway", method="GET", status="200"}

# 避免高基数标签
http_requests_total{user_id="12345"}  # ❌ 不推荐
```

### 3. 查询优化

```promql
# 使用 rate() 而不是 irate()
rate(http_requests_total[5m])

# 使用聚合减少数据量
sum(rate(http_requests_total[5m])) by (service)
```

### 4. 告警规则

```yaml
# 示例告警规则
groups:
  - name: service_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
```

## 💡 提示

- 📊 定期检查仪表板，了解系统运行状况
- 🔍 使用 Prometheus 的 Graph 功能测试查询
- 📈 根据业务需求创建自定义仪表板
- ⚠️ 设置合理的告警规则
- 💾 定期备份 Grafana 仪表板配置
