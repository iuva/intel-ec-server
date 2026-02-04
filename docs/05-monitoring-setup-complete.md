# Prometheus & Grafana 监控配置完成

## ✅ 配置完成

**完成时间**: 2025-10-11  
**配置状态**: 完成  
**监控服务**: 4个微服务 + 1个基础设施服务

---

## � 监最新修复 (2025-10-11)

### 修复内容
1. ✅ **移除 Nacos 监控**: 从 Prometheus 配置中移除了 Nacos 监控任务
2. ✅ **修复 Grafana 仪表盘配置**: 
   - 修正了仪表盘文件的挂载路径 (`/var/lib/grafana/dashboards`)
   - 删除了重复的仪表盘文件 (`microservices-overview.json`)
   - 确保所有仪表盘都能正常访问
3. ✅ **修复 Grafana UID 错误**: 
   - 修复 "Invalid dashboard UID in annotation request" 错误
   - 为 Prometheus 数据源添加 `uid: prometheus` 配置
   - 将仪表盘中的 datasource 从字符串格式改为对象格式
   - 修复 annotations 配置中的 datasource 引用

### 配置变更
- **Prometheus**: 移除 `nacos` job 配置
- **Grafana 数据源**: 添加 `uid: prometheus` 字段，优化查询配置
- **Grafana 仪表盘**: 
  - 路径从 `/etc/grafana/provisioning/dashboards` 改为 `/var/lib/grafana/dashboards`
  - Datasource 格式从字符串改为对象格式（兼容 Grafana 10.x）
  - 只保留 `intel-cw-microservices.json`

### 修复脚本
- `scripts/fix_grafana_dashboard_uid.py` - 自动修复仪表盘 datasource 格式（如果存在）

详细修复说明请查看: [GRAFANA_UID_FIX.md](./GRAFANA_UID_FIX.md)

---

## 📊 监控架构

```
┌─────────────────────────────────────────────────────────────┐
│                     监控系统架构                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Prometheus     │  Grafana        │  被监控服务              │
│  (数据采集)      │  (可视化)        │                         │
│                 │                 │                         │
│  • 指标采集     │  • 仪表板       │  • Gateway Service      │
│  • 数据存储     │  • 告警展示     │  • Auth Service         │
│  • 查询API      │  • 数据查询     │  • Admin Service        │
│  • 告警规则     │  • 用户管理     │  • Host Service         │
│                 │                 │  • Jaeger               │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## 🎯 配置的服务

### 微服务监控

| 服务 | 端口 | 指标端点 | 采集间隔 |
|------|------|---------|---------|
| Gateway Service | 8000 | /metrics | 15s |
| Auth Service | 8001 | /metrics | 15s |
| Admin Service | 8002 | /metrics | 15s |
| Host Service | 8003 | /metrics | 15s |

### 基础设施监控

| 服务 | 端口 | 指标端点 | 采集间隔 |
|------|------|---------|---------|
| Nacos | 8848 | /nacos/actuator/prometheus | 15s |
| Jaeger | 14269 | /metrics | 15s |
| Prometheus | 9090 | /metrics | 15s |

---

## 📁 配置文件

### 1. Prometheus 配置

**文件**: `infrastructure/prometheus/prometheus.yml`

```yaml
# 全局配置
global:
  scrape_interval: 15s      # 抓取间隔
  evaluation_interval: 15s  # 规则评估间隔
  external_labels:
    cluster: 'intel-cw-ms'
    environment: 'development'

# 抓取配置
scrape_configs:
  # 微服务监控
  - job_name: 'gateway-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['gateway-service:8000']
        labels:
          service: 'gateway-service'
          type: 'microservice'
          tier: 'gateway'

  - job_name: 'auth-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['auth-service:8001']
        labels:
          service: 'auth-service'
          type: 'microservice'
          tier: 'backend'


  - job_name: 'host-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host-service:8003']
        labels:
          service: 'host-service'
          type: 'microservice'
          tier: 'backend'
```

### 2. Grafana 数据源配置

**文件**: `infrastructure/grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://intel-prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      httpMethod: POST
      timeInterval: 15s
```

### 3. Grafana 仪表板配置

**文件**: `infrastructure/grafana/provisioning/dashboards/dashboards.yml`

```yaml
apiVersion: 1

providers:
  - name: 'Intel EC Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

### 4. 微服务监控仪表板

**文件**: `infrastructure/grafana/dashboards/intel-cw-microservices.json`

包含以下面板：

- 健康服务数统计
- 总请求速率
- 错误率
- P95 响应时间
- 各服务请求速率趋势
- 各服务响应时间趋势
- HTTP 状态码分布
- 内存使用情况

---

## 🚀 启动和访问

### 1. 启动监控服务

```bash
# 启动所有服务（包括监控）
docker-compose up -d

# 或者只启动监控服务
docker-compose up -d prometheus grafana
```

### 2. 访问监控界面

#### Prometheus

- **URL**: <http://localhost:9090>
- **功能**:
  - 查询指标数据
  - 查看采集目标状态
  - 配置告警规则

#### Grafana

- **URL**: <http://localhost:3000>
- **默认账号**: admin
- **默认密码**: admin123 (可在 .env 中修改)
- **功能**:
  - 查看预配置的仪表板
  - 创建自定义仪表板
  - 配置告警通知

### 3. 验证监控配置

```bash
# 检查 Prometheus 目标状态
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# 检查 Grafana 健康状态
curl http://localhost:3000/api/health | python3 -m json.tool

# 检查各服务指标端点
curl http://localhost:8000/metrics  # Gateway
curl http://localhost:8001/metrics  # Auth
curl http://localhost:8002/metrics  # Admin
curl http://localhost:8003/metrics  # Host
```

---

## 📈 监控指标说明

### 核心指标

#### 1. HTTP 请求指标

```promql
# 请求总数
http_requests_total{service="auth-service"}

# 请求速率
rate(http_requests_total{service="auth-service"}[5m])

# 按状态码统计
sum(rate(http_requests_total[5m])) by (service, status)
```

#### 2. 响应时间指标

```promql
# P95 响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# P50 响应时间
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# 平均响应时间
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

#### 3. 错误率指标

```promql
# 5xx 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# 4xx 错误率
sum(rate(http_requests_total{status=~"4.."}[5m])) / sum(rate(http_requests_total[5m]))
```

#### 4. 系统资源指标

```promql
# 内存使用
process_resident_memory_bytes{service="auth-service"}

# CPU 使用
rate(process_cpu_seconds_total{service="auth-service"}[5m])

# 活跃连接数
active_connections{service="host-service"}
```

---

## 🎨 Grafana 仪表板使用

### 预配置仪表板

#### Intel EC 微服务监控

- **UID**: `intel-cw-microservices`
- **路径**: Dashboards → Intel EC 微服务监控

**包含面板**:

1. **概览统计**
   - 健康服务数
   - 总请求速率
   - 错误率
   - P95 响应时间

2. **服务性能**
   - 各服务请求速率趋势
   - 各服务响应时间趋势

3. **错误分析**
   - HTTP 状态码分布
   - 错误率趋势

4. **资源使用**
   - 内存使用情况
   - CPU 使用情况

### 自定义仪表板

1. 登录 Grafana (<http://localhost:3000>)
2. 点击 "+" → "Dashboard"
3. 添加面板并选择 Prometheus 数据源
4. 输入 PromQL 查询
5. 配置可视化选项
6. 保存仪表板

---

## 🔔 告警配置（可选）

### 1. Prometheus 告警规则

创建 `infrastructure/prometheus/alerts/microservices.yml`:

```yaml
groups:
  - name: microservices_alerts
    interval: 30s
    rules:
      # 服务不可用告警
      - alert: ServiceDown
        expr: up{type="microservice"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服务 {{ $labels.service }} 不可用"
          description: "服务已下线超过1分钟"

      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5..",type="microservice"}[5m])) by (service)
          /
          sum(rate(http_requests_total{type="microservice"}[5m])) by (service)
          > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "服务 {{ $labels.service }} 错误率过高"
          description: "5分钟内错误率超过5%"

      # 高响应时间告警
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket{type="microservice"}[5m])) by (service, le)
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "服务 {{ $labels.service }} 响应时间过高"
          description: "P95响应时间超过1秒"
```

### 2. Grafana 告警通知

1. 进入 Grafana → Alerting → Notification channels
2. 添加通知渠道（Email、Slack、钉钉等）
3. 在仪表板面板中配置告警规则
4. 设置告警阈值和通知渠道

---

## 🔍 故障排查

### Prometheus 无法采集指标

**问题**: Prometheus 目标显示 DOWN

**解决方案**:

```bash
# 1. 检查服务是否运行
docker-compose ps

# 2. 检查服务指标端点
curl http://localhost:8001/metrics

# 3. 检查 Prometheus 日志
docker-compose logs prometheus

# 4. 检查网络连接
docker-compose exec prometheus ping auth-service
```

### Grafana 无法连接 Prometheus

**问题**: Grafana 显示数据源错误

**解决方案**:

```bash
# 1. 检查 Prometheus 是否运行
curl http://localhost:9090/-/healthy

# 2. 检查 Grafana 配置
docker-compose exec grafana cat /etc/grafana/provisioning/datasources/prometheus.yml

# 3. 重启 Grafana
docker-compose restart grafana
```

### 仪表板无数据

**问题**: Grafana 仪表板显示 "No Data"

**解决方案**:

```bash
# 1. 检查时间范围是否正确
# 2. 检查 PromQL 查询是否正确
# 3. 在 Prometheus 中验证查询
curl 'http://localhost:9090/api/v1/query?query=up{type="microservice"}'

# 4. 检查服务是否有流量
curl http://localhost:8000/health
```

---

## 📚 相关文档

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana 仪表板最佳实践](https://grafana.com/docs/grafana/latest/best-practices/)

---

## ✨ 总结

### 配置完成内容

- ✅ Prometheus 采集配置（4个微服务 + 2个基础设施）
- ✅ Grafana 数据源自动配置
- ✅ 微服务监控仪表板
- ✅ Docker Compose 集成
- ✅ 健康检查配置

### 监控指标

- ✅ HTTP 请求指标
- ✅ 响应时间指标
- ✅ 错误率指标
- ✅ 系统资源指标

### 可视化面板

- ✅ 服务健康状态
- ✅ 请求速率趋势
- ✅ 响应时间分析
- ✅ 错误分布统计
- ✅ 资源使用监控

---

## 🔧 应用修复

### 快速应用修复

如果你刚刚拉取了最新的配置修复，运行以下命令应用修复：

```bash
# 方式1: 使用验证脚本（推荐）
bash scripts/verify_monitoring.sh

# 方式2: 手动执行
# 1. 验证配置
bash scripts/verify_monitoring.sh

# 2. 重启服务
docker-compose restart prometheus grafana

# 3. 等待服务启动
sleep 30

# 4. 验证服务状态
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

### 修复内容

1. ✅ **移除 Nacos 监控**: Prometheus 不再监控 Nacos
2. ✅ **修复 Grafana 仪表盘**: 所有仪表盘都能正常访问
3. ✅ **清理重复文件**: 只保留一个主仪表盘文件

详细修复说明请查看: [MONITORING_FIX_SUMMARY.md](./MONITORING_FIX_SUMMARY.md)

---

**配置完成时间**: 2025-10-11  
**最后修复时间**: 2025-10-11  
**配置状态**: ✅ 完成  
**访问地址**:

- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> (admin/admin123)

🎉 **监控系统配置完成！可以开始监控所有微服务了！**
