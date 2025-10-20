# 监控指标增强说明

## 📊 概述

本次增强为监控指标系统添加了更多业务维度的指标收集能力，提供了更细粒度的性能监控和问题诊断功能。

## 🎯 增强内容

### 1. 新增业务指标

#### 业务操作响应时间
```python
business_operation_duration_seconds
```
- **类型**: Histogram
- **标签**: `operation`, `service`
- **用途**: 记录各类业务操作的耗时分布
- **桶配置**: 0.001s ~ 10s，适合大多数业务场景

#### 业务操作进行中数量
```python
business_operations_in_progress
```
- **类型**: Gauge
- **标签**: `operation`, `service`
- **用途**: 实时监控正在执行的业务操作数量
- **应用**: 识别性能瓶颈和并发问题

#### 用户会话操作
```python
user_sessions_total
```
- **类型**: Counter
- **标签**: `action`, `service`
- **用途**: 跟踪用户会话生命周期（login, logout, refresh, expire）

#### 认证操作
```python
auth_operations_total
```
- **类型**: Counter
- **标签**: `operation`, `status`, `service`
- **用途**: 监控认证相关操作的成功率和失败率

#### 数据验证错误
```python
validation_errors_total
```
- **类型**: Counter
- **标签**: `field`, `error_type`, `service`
- **用途**: 跟踪数据验证失败的字段和错误类型

### 2. 增强现有指标

#### 添加服务维度标签

所有主要指标都添加了 `service` 标签，支持多服务环境下的指标区分：

- `http_requests_total`: 添加 `service` 标签
- `http_request_duration_seconds`: 添加 `service` 标签
- `http_request_size_bytes`: 添加 `service` 标签
- `http_response_size_bytes`: 添加 `service` 标签
- `business_operations_total`: 添加 `service` 标签
- `active_connections`: 添加 `service` 标签

### 3. 新增功能方法

#### MetricsCollector 新增方法

##### record_user_session()
```python
metrics_collector.record_user_session(
    action="login",
    service="auth-service"
)
```
记录用户会话操作。

##### record_auth_operation()
```python
metrics_collector.record_auth_operation(
    operation="login",
    status="success",
    service="auth-service"
)
```
记录认证操作及其结果。

##### record_validation_error()
```python
metrics_collector.record_validation_error(
    field="username",
    error_type="required",
    service="api-service"
)
```
记录数据验证错误。

##### track_operation_in_progress()
```python
with metrics_collector.track_operation_in_progress("data_processing"):
    # 执行业务操作
    await process_data()
```
使用上下文管理器自动跟踪操作进度和耗时。

### 4. 性能优化

#### 服务名称缓存
- `MetricsCollector` 初始化时保存服务名称
- 避免每次调用时传递服务名称参数
- 减少标签字符串创建开销

#### 可选参数设计
- 所有新增的 `service` 参数都是可选的
- 默认使用初始化时的服务名称
- 支持覆盖特定调用的服务名称

#### 上下文管理器
- `OperationTracker` 自动管理进行中的操作计数
- 自动记录操作耗时和结果
- 减少手动代码编写

## 📈 使用场景

### 场景 1: 监控业务操作性能

```python
from shared.common.decorators import monitor_operation

@monitor_operation("host_create", record_duration=True)
async def create_host(host_data):
    # 自动记录操作耗时和成功/失败状态
    return await db.create_host(host_data)
```

**Grafana 查询示例**:
```promql
# 查看 host_create 操作的 P95 耗时
histogram_quantile(0.95, 
  rate(business_operation_duration_seconds_bucket{operation="host_create"}[5m])
)

# 查看 host_create 操作的成功率
rate(business_operations_total{operation="host_create",status="success"}[5m])
/
rate(business_operations_total{operation="host_create"}[5m])
```

### 场景 2: 监控用户会话

```python
# 用户登录时
metrics_collector.record_user_session("login", "auth-service")

# 用户登出时
metrics_collector.record_user_session("logout", "auth-service")
```

**Grafana 查询示例**:
```promql
# 每分钟登录次数
rate(user_sessions_total{action="login"}[1m]) * 60

# 活跃会话数（登录 - 登出）
sum(rate(user_sessions_total{action="login"}[5m])) 
- 
sum(rate(user_sessions_total{action="logout"}[5m]))
```

### 场景 3: 监控认证失败

```python
try:
    await authenticate_user(credentials)
    metrics_collector.record_auth_operation("login", "success")
except AuthError:
    metrics_collector.record_auth_operation("login", "failed")
    raise
```

**Grafana 查询示例**:
```promql
# 认证失败率
rate(auth_operations_total{status="failed"}[5m])
/
rate(auth_operations_total[5m])

# 认证失败次数告警
rate(auth_operations_total{status="failed"}[5m]) > 10
```

### 场景 4: 监控数据验证错误

```python
from pydantic import ValidationError

try:
    user = UserCreate(**data)
except ValidationError as e:
    for error in e.errors():
        field = str(error["loc"][0])
        error_type = error["type"]
        metrics_collector.record_validation_error(field, error_type)
    raise
```

**Grafana 查询示例**:
```promql
# 最常见的验证错误字段
topk(10, sum by (field) (
  rate(validation_errors_total[5m])
))

# 按错误类型分组
sum by (error_type) (
  rate(validation_errors_total[5m])
)
```

### 场景 5: 跟踪并发操作

```python
with metrics_collector.track_operation_in_progress("batch_processing"):
    # 自动增加进行中计数
    await process_batch(items)
    # 自动减少进行中计数并记录耗时
```

**Grafana 查询示例**:
```promql
# 当前正在执行的操作数
business_operations_in_progress{operation="batch_processing"}

# 操作排队情况（如果超过阈值可能需要扩容）
business_operations_in_progress > 10
```

## 🔧 配置建议

### Prometheus 抓取配置

```yaml
scrape_configs:
  - job_name: 'microservices'
    scrape_interval: 15s
    static_configs:
      - targets:
        - 'gateway-service:8000'
        - 'auth-service:8001'
        - 'admin-service:8002'
        - 'host-service:8003'
```

### Grafana 仪表板建议

#### 业务操作面板
- **操作耗时分布**: Histogram 热力图
- **操作成功率**: Gauge 显示百分比
- **操作 QPS**: Graph 显示每秒操作数
- **进行中操作数**: Gauge 显示当前并发

#### 用户会话面板
- **登录/登出趋势**: Graph 显示时间序列
- **活跃会话数**: Gauge 显示当前活跃数
- **会话过期率**: Graph 显示过期趋势

#### 认证监控面板
- **认证成功率**: Gauge 显示百分比
- **认证失败趋势**: Graph 显示失败次数
- **认证操作分布**: Pie chart 显示操作类型占比

#### 数据验证面板
- **Top 验证错误字段**: Bar chart
- **验证错误类型分布**: Pie chart
- **验证错误趋势**: Graph 显示时间序列

## 📊 告警规则建议

### 业务操作告警

```yaml
groups:
  - name: business_operations
    rules:
      # 操作失败率过高
      - alert: HighOperationFailureRate
        expr: |
          rate(business_operations_total{status="failed"}[5m])
          /
          rate(business_operations_total[5m])
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "业务操作失败率过高"
          description: "{{ $labels.operation }} 操作失败率超过 10%"
      
      # 操作耗时过长
      - alert: SlowOperations
        expr: |
          histogram_quantile(0.95,
            rate(business_operation_duration_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "业务操作响应缓慢"
          description: "{{ $labels.operation }} P95 耗时超过 5 秒"
      
      # 操作并发过高
      - alert: HighConcurrency
        expr: business_operations_in_progress > 100
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "业务操作并发过高"
          description: "{{ $labels.operation }} 并发数超过 100"
```

### 认证告警

```yaml
  - name: authentication
    rules:
      # 认证失败率过高
      - alert: HighAuthFailureRate
        expr: |
          rate(auth_operations_total{status="failed"}[5m])
          /
          rate(auth_operations_total[5m])
          > 0.2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "认证失败率过高"
          description: "认证失败率超过 20%，可能存在攻击"
```

### 数据验证告警

```yaml
  - name: validation
    rules:
      # 验证错误激增
      - alert: ValidationErrorSpike
        expr: |
          rate(validation_errors_total[5m])
          >
          rate(validation_errors_total[5m] offset 1h) * 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据验证错误激增"
          description: "验证错误数量是 1 小时前的 2 倍以上"
```

## 🎯 最佳实践

### 1. 使用装饰器自动监控

优先使用 `@monitor_operation` 装饰器，自动处理指标收集：

```python
@monitor_operation("user_create", record_duration=True)
@handle_service_errors("创建用户失败", "USER_CREATE_FAILED")
async def create_user(user_data):
    return await db.create_user(user_data)
```

### 2. 合理使用上下文管理器

对于复杂的业务流程，使用上下文管理器跟踪进度：

```python
with metrics_collector.track_operation_in_progress("data_migration"):
    await migrate_data()
```

### 3. 记录关键业务事件

在关键业务节点记录指标：

```python
# 用户注册
metrics_collector.record_user_session("register", "auth-service")

# 支付完成
metrics_collector.record_business_operation("payment_complete", "success")
```

### 4. 监控数据质量

记录验证错误帮助改进数据质量：

```python
try:
    validate_input(data)
except ValidationError as e:
    for error in e.errors():
        metrics_collector.record_validation_error(
            field=str(error["loc"][0]),
            error_type=error["type"]
        )
    raise
```

### 5. 服务标签一致性

确保服务名称在整个应用中保持一致：

```python
# 在应用启动时初始化
from shared.monitoring.metrics import init_metrics

init_metrics(
    service_name="user-service",
    service_version="1.0.0",
    environment="production"
)
```

## 📝 迁移指南

### 现有代码迁移

如果你的代码已经使用了旧版本的 `record_business_operation`，无需修改，新版本向后兼容：

```python
# 旧版本（仍然有效）
metrics_collector.record_business_operation("operation_name", "success")

# 新版本（推荐，包含耗时）
metrics_collector.record_business_operation(
    operation="operation_name",
    status="success",
    duration=0.123
)
```

### 添加服务标签

建议在应用启动时设置服务名称：

```python
# main.py
from shared.monitoring.metrics import init_metrics

app = FastAPI()

@app.on_event("startup")
async def startup():
    init_metrics(
        service_name="my-service",
        service_version="1.0.0",
        environment="production"
    )
```

## 🔍 故障排查

### 指标未显示

1. 检查 Prometheus 是否正常抓取指标端点
2. 确认服务已正确初始化指标收集器
3. 验证 Grafana 数据源配置

### 指标数值异常

1. 检查标签值是否正确
2. 确认时间范围选择是否合适
3. 验证 PromQL 查询语法

### 性能影响

1. 指标收集对性能影响极小（< 1ms）
2. 如有性能问题，检查是否有过多的唯一标签值
3. 考虑调整 Prometheus 抓取间隔

---

**版本**: 1.0.0  
**更新日期**: 2025-10-16  
**维护者**: 开发团队
