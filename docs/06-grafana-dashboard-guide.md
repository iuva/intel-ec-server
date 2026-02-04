# Grafana 仪表板使用指南

## 🎨 访问 Grafana

### 登录信息
- **URL**: http://localhost:3000
- **用户名**: admin
- **密码**: admin123 (可在 .env 中通过 GRAFANA_ADMIN_PASSWORD 修改)

---

## 📊 预配置仪表板

### Intel EC 微服务监控仪表板

**访问路径**: Dashboards → Intel EC 微服务监控  
**直接链接**: http://localhost:3000/d/intel-cw-microservices

#### 仪表板面板说明

##### 1. 概览统计（顶部）

**健康服务数**
- 显示当前在线的微服务数量
- 查询: `count(up{type="microservice"} == 1)`
- 阈值: 绿色=正常，红色=服务下线

**总请求速率**
- 显示所有服务的总请求速率（请求/秒）
- 查询: `sum(rate(http_requests_total{type="microservice"}[5m]))`
- 单位: reqps (requests per second)

**错误率**
- 显示5xx错误占总请求的百分比
- 查询: `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- 阈值: 绿色<1%, 黄色<5%, 红色≥5%

**P95 响应时间**
- 显示95%请求的响应时间
- 查询: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
- 阈值: 绿色<0.5s, 黄色<1s, 红色≥1s

##### 2. 服务性能（中部）

**各服务请求速率**
- 时间序列图，显示每个服务的请求速率趋势
- 查询: `sum(rate(http_requests_total{type="microservice"}[5m])) by (service)`
- 图例: 每个服务一条线

**各服务响应时间**
- 时间序列图，显示每个服务的P95和P50响应时间
- 查询: 
  - P95: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le))`
  - P50: `histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le))`

##### 3. 错误分析（底部）

**HTTP 状态码分布**
- 堆叠面积图，显示各服务的HTTP状态码分布
- 查询: `sum(rate(http_requests_total{type="microservice"}[5m])) by (service, status)`
- 颜色: 2xx=绿色, 4xx=黄色, 5xx=红色

**内存使用**
- 时间序列图，显示各服务的内存使用情况
- 查询: `process_resident_memory_bytes{type="microservice"}`
- 单位: bytes

---

## 🎯 常用 PromQL 查询

### 服务可用性

```promql
# 服务在线状态
up{type="microservice"}

# 在线服务数量
count(up{type="microservice"} == 1)

# 服务在线率
avg(up{type="microservice"})
```

### 请求指标

```promql
# 总请求数
sum(http_requests_total{type="microservice"})

# 请求速率（5分钟）
rate(http_requests_total{type="microservice"}[5m])

# 按服务统计请求速率
sum(rate(http_requests_total{type="microservice"}[5m])) by (service)

# 按端点统计请求速率
sum(rate(http_requests_total{type="microservice"}[5m])) by (endpoint)
```

### 响应时间

```promql
# P95 响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# P99 响应时间
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# 平均响应时间
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# 按服务统计P95响应时间
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le))
```

### 错误率

```promql
# 5xx 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# 4xx 错误率
sum(rate(http_requests_total{status=~"4.."}[5m])) / sum(rate(http_requests_total[5m]))

# 按服务统计错误率
sum(rate(http_requests_total{status=~"5..",type="microservice"}[5m])) by (service) 
/ 
sum(rate(http_requests_total{type="microservice"}[5m])) by (service)
```

### 系统资源

```promql
# 内存使用
process_resident_memory_bytes{type="microservice"}

# CPU 使用率
rate(process_cpu_seconds_total{type="microservice"}[5m])

# 活跃连接数
active_connections{type="microservice"}

# 数据库连接池
db_connections_active{type="microservice"}
```

---

## 🎨 创建自定义仪表板

### 步骤1: 创建新仪表板

1. 登录 Grafana (http://localhost:3000)
2. 点击左侧菜单 "+" → "Dashboard"
3. 点击 "Add new panel"

### 步骤2: 配置面板

1. **选择可视化类型**
   - Time series: 时间序列图
   - Stat: 统计数值
   - Gauge: 仪表盘
   - Bar chart: 柱状图
   - Table: 表格

2. **输入 PromQL 查询**
   - 在 "Metrics browser" 中输入查询
   - 使用上面的常用查询作为参考

3. **配置显示选项**
   - 标题、描述
   - 单位、阈值
   - 图例、颜色

4. **保存面板**
   - 点击右上角 "Apply"

### 步骤3: 保存仪表板

1. 点击右上角保存图标
2. 输入仪表板名称
3. 选择文件夹（可选）
4. 点击 "Save"

---

## 📈 推荐的监控面板

### 1. 服务概览仪表板

**面板配置**:
- 服务在线状态（Stat）
- 总请求速率（Stat）
- 总错误率（Stat）
- P95响应时间（Stat）
- 各服务请求趋势（Time series）
- 各服务错误趋势（Time series）

### 2. 性能分析仪表板

**面板配置**:
- 响应时间分布（Heatmap）
- 慢请求Top 10（Table）
- 各端点响应时间（Time series）
- 数据库查询时间（Time series）
- Redis操作时间（Time series）

### 3. 错误分析仪表板

**面板配置**:
- 错误率趋势（Time series）
- 错误类型分布（Pie chart）
- 错误日志（Logs）
- 异常堆栈（Table）

### 4. 资源监控仪表板

**面板配置**:
- CPU使用率（Time series）
- 内存使用（Time series）
- 网络流量（Time series）
- 磁盘I/O（Time series）
- 数据库连接池（Gauge）

---

## 🔔 配置告警

### 步骤1: 配置通知渠道

1. 进入 Grafana → Alerting → Notification channels
2. 点击 "Add channel"
3. 选择通知类型：
   - Email
   - Slack
   - 钉钉 (DingTalk)
   - 企业微信 (WeChat Work)
   - Webhook

### 步骤2: 创建告警规则

1. 在仪表板面板中点击标题 → Edit
2. 切换到 "Alert" 标签
3. 点击 "Create Alert"
4. 配置告警条件：
   - 查询条件
   - 阈值
   - 评估间隔
5. 选择通知渠道
6. 保存

### 推荐的告警规则

#### 服务不可用告警
```
条件: up{type="microservice"} == 0
持续时间: 1分钟
严重程度: Critical
通知: 立即通知
```

#### 高错误率告警
```
条件: 错误率 > 5%
持续时间: 5分钟
严重程度: Warning
通知: 延迟5分钟通知
```

#### 高响应时间告警
```
条件: P95响应时间 > 1秒
持续时间: 5分钟
严重程度: Warning
通知: 延迟5分钟通知
```

#### 高内存使用告警
```
条件: 内存使用 > 80%
持续时间: 10分钟
严重程度: Warning
通知: 延迟10分钟通知
```

---

## 🔧 高级配置

### 变量配置

在仪表板设置中添加变量，实现动态过滤：

```
变量名: service
类型: Query
查询: label_values(up{type="microservice"}, service)
用途: 在面板中使用 $service 过滤特定服务
```

### 模板化查询

使用变量的查询示例：
```promql
# 使用 $service 变量
rate(http_requests_total{service="$service"}[5m])

# 使用 $__interval 自动调整时间窗口
rate(http_requests_total[$__interval])
```

### 链接和导航

在面板中添加链接：
1. 编辑面板 → Links
2. 添加链接到相关仪表板或外部系统
3. 使用变量传递上下文

---

## 📚 最佳实践

### 1. 仪表板设计

- ✅ 使用清晰的面板标题和描述
- ✅ 合理组织面板布局（从概览到详细）
- ✅ 使用一致的颜色方案
- ✅ 添加适当的阈值和告警
- ✅ 使用变量实现动态过滤

### 2. 查询优化

- ✅ 使用合适的时间范围（避免过长）
- ✅ 使用 rate() 而不是 increase() 计算速率
- ✅ 使用 by() 进行分组聚合
- ✅ 避免过于复杂的查询

### 3. 性能优化

- ✅ 设置合理的刷新间隔（10s-30s）
- ✅ 限制查询的时间范围
- ✅ 使用缓存减少查询负载
- ✅ 避免在单个仪表板中添加过多面板

---

## 🎯 监控目标

### 当前监控的服务

| 服务 | 端口 | 状态 | 指标端点 |
|------|------|------|---------|
| Gateway Service | 8000 | ✅ UP | /metrics |
| Auth Service | 8001 | ✅ UP | /metrics |
| Admin Service | 8002 | ✅ UP | /metrics |
| Host Service | 8003 | ✅ UP | /metrics |
| Jaeger | 14269 | ✅ UP | /metrics |
| Prometheus | 9090 | ✅ UP | /metrics |
| Nacos | 8848 | ⚠️ DOWN | /nacos/actuator/prometheus |

**注意**: Nacos 的 Prometheus 端点可能需要额外配置才能启用。

---

## 🔍 故障排查

### 仪表板无数据

**问题**: 面板显示 "No Data"

**解决方案**:
1. 检查时间范围是否正确（右上角时间选择器）
2. 在 Prometheus 中验证查询: http://localhost:9090/graph
3. 检查服务是否有流量（访问服务端点生成指标）
4. 检查 Prometheus 目标状态: http://localhost:9090/targets

### 数据源连接失败

**问题**: Grafana 无法连接 Prometheus

**解决方案**:
```bash
# 1. 检查 Prometheus 是否运行
curl http://localhost:9090/-/healthy

# 2. 检查 Grafana 数据源配置
docker-compose exec grafana cat /etc/grafana/provisioning/datasources/prometheus.yml

# 3. 测试数据源连接
# 在 Grafana UI: Configuration → Data Sources → Prometheus → Test

# 4. 重启 Grafana
docker-compose restart grafana
```

### 仪表板未自动加载

**问题**: 预配置的仪表板没有出现

**解决方案**:
```bash
# 1. 检查仪表板文件是否存在
ls -la infrastructure/grafana/dashboards/

# 2. 检查 provisioning 配置
cat infrastructure/grafana/provisioning/dashboards/dashboards.yml

# 3. 检查 Grafana 日志
docker-compose logs grafana | grep -i dashboard

# 4. 重启 Grafana
docker-compose restart grafana
```

---

## 📖 扩展阅读

### Grafana 文档
- [Grafana 官方文档](https://grafana.com/docs/grafana/latest/)
- [面板配置指南](https://grafana.com/docs/grafana/latest/panels/)
- [告警配置指南](https://grafana.com/docs/grafana/latest/alerting/)

### Prometheus 文档
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [指标类型说明](https://prometheus.io/docs/concepts/metric_types/)
- [最佳实践](https://prometheus.io/docs/practices/)

---

## ✨ 总结

### 配置完成内容
- ✅ Prometheus 数据源自动配置
- ✅ 微服务监控仪表板
- ✅ 8个监控面板
- ✅ 6个服务指标采集

### 监控覆盖
- ✅ 服务健康状态
- ✅ 请求速率和响应时间
- ✅ 错误率和状态码分布
- ✅ 系统资源使用

### 访问信息
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **仪表板**: http://localhost:3000/d/intel-cw-microservices

---

**配置完成时间**: 2025-10-11  
**配置状态**: ✅ 完成  
**监控服务数**: 6个（4个微服务 + 2个基础设施）

🎉 **Grafana 仪表板配置完成！可以开始监控所有微服务了！**
