# Host Service 压力测试执行手册

> **配套文件**: [压力测试计划](./30-host-service-stress-testing-plan.md)

## 📋 目录

1. [测试前准备](#测试前准备)
2. [数据与脚本准备](#数据与脚本准备)
3. [单场景执行步骤](#单场景执行步骤)
4. [组合场景执行步骤](#组合场景执行步骤)
5. [数据采集与记录](#数据采集与记录)
6. [结果分析模板](#结果分析模板)
7. [报告输出](#报告输出)

---

## 测试前准备

### 1. 环境检查清单

| 项目 | 检查项 | 命令/方法 | 结果 |
|------|--------|-----------|------|
| 服务进程 | Host Service、Gateway Service | `docker ps` or `systemctl status` | ✅ |
| 数据库 | MariaDB 可连接 | `mysql -h ... -P ... -u ... -p` | ✅ |
| Redis | Redis 可连接 | `redis-cli -h ... ping` | ✅ |
| 监控 | Prometheus/Grafana 可访问 | 浏览器访问 | ✅ |
| 负载工具 | k6 / Locust / ab / wrk / Python 脚本 | `k6 version` 等 | ✅ |

### 2. 环境变量

```bash
export GATEWAY_URL="http://localhost:8000"
export HOST_URL="http://localhost:8003"
export HOST_API_URL="${GATEWAY_URL}/api/v1/host"
export PROMETHEUS_URL="http://localhost:9090"
export GRAFANA_URL="http://localhost:3000"
```

---

## 数据与脚本准备

### 1. 测试数据脚本

```bash
# scripts/prepare_stress_data.sh
bash scripts/prepare_stress_data.sh

# 内容示例：
# - 创建 5000 条模拟主机记录
# - 创建 10000 条 host_exec_log 记录
# - 创建 1000 条待审批记录
# - 生成 10MB / 50MB / 100MB 测试文件
```

### 2. 负载脚本目录

```
tests/performance/
├── README.md
├── http/
│   ├── k6_query_available_hosts.js
│   ├── k6_vnc_connect.js
│   ├── k6_admin_host_list.js
│   └── python_file_upload_test.py
├── websocket/
│   ├── ws_connection_test.py
│   ├── ws_throughput_test.py
│   └── ws_concurrent_test.py
└── mixed/
    └── k6_mixed_stress.js
```

---

## 单场景执行步骤

### SC-01 浏览器接口峰值

1. 启动 k6
   ```bash
   k6 run tests/performance/http/k6_query_available_hosts.js
   ```
2. 实时监控
   - Grafana 仪表板: `Host Service / HTTP Overview`
   - Prometheus 即时查询:
     ```promql
     rate(http_requests_total{service="host-service",endpoint="/api/v1/host/hosts/available"}[1m])
     ```
3. 记录数据
   - k6 输出日志
   - Grafana 截图
   - Prometheus CSV 导出

### SC-02 Agent 上报洪峰

1. 启动 Locust
   ```bash
   locust -f tests/performance/http/locust_agent_report.py --host=${HOST_API_URL}
   ```
2. Web UI 配置
   - 总用户数：2000
   - 生成速率：每秒 200 用户
3. 采集指标：数据库写入延迟、Redis 命中率

### SC-03 WebSocket 并发

1. 启动 Python 脚本
   ```bash
   python tests/performance/websocket/ws_concurrent_test.py --connections 3000 --messages 50
   ```
2. 监控指标
   - `active_connections{service="host-service"}`
   - `websocket_connections_total`
3. 核对日志（确保无 `Too many connections` 或内存告警）

### SC-04 文件上传洪峰

1. 准备测试文件：`10MB`, `50MB`, `100MB`
2. 运行脚本
   ```bash
   python tests/performance/http/python_file_upload_test.py --size 10 --concurrency 50 --requests 200
   ```
3. 监控磁盘 IO、网络带宽、响应时间

### SC-05 管理后台复杂查询

1. k6 脚本：
   ```bash
   k6 run tests/performance/http/k6_admin_host_list.js
   ```
2. 关注数据库查询耗时
   ```promql
   histogram_quantile(0.95, rate(db_query_duration_seconds_bucket{service="host-service",operation="select"}[5m]))
   ```

### SC-06 组合压力

1. 同时运行以下脚本：
   ```bash
   # HTTP + WebSocket + 文件
   k6 run tests/performance/mixed/k6_mixed_stress.js &
   python tests/performance/websocket/ws_concurrent_test.py --connections 1000 --messages 100 &
   python tests/performance/http/python_file_upload_test.py --size 10 --concurrency 20 --requests 100 &
   wait
   ```
2. 监控整体资源使用与错误率

---

## 数据采集与记录

### 1. 采集模板

| 时间 | 场景 | QPS | P95 响应时间 | 错误率 | CPU | 内存 | DB 连接 | 备注 |
|------|------|-----|--------------|--------|-----|------|---------|------|
| 10:00 | SC-01 | 980 | 420ms | 0.3% | 68% | 62% | 45/60 | 正常 |

### 2. Prometheus 导出

```bash
# 导出 5 分钟数据
curl -G "${PROMETHEUS_URL}/api/v1/query" \
  --data-urlencode 'query=rate(http_requests_total{service="host-service"}[5m])' \
  --data-urlencode "time=$(date +%s)" \
  > artifacts/prometheus/http_requests_total.json
```

### 3. Grafana 截图

- HTTP Dashboard (P95)
- WebSocket Dashboard (Active Connections)
- Resource Dashboard (CPU/Memory)

### 4. 日志收集

```bash
# 收集 Host Service 日志
docker logs host-service --since 30m > artifacts/logs/host-service.log

# 收集 Gateway 日志
docker logs gateway-service --since 30m > artifacts/logs/gateway-service.log
```

---

## 结果分析模板

### 1. 指标总结

```markdown
| 场景 | 峰值 QPS | P95 响应时间 | 错误率 | 崩溃点 | 备注 |
|------|----------|--------------|--------|--------|------|
| SC-01 | 1050 | 480ms | 0.4% | - | 正常 |
| SC-02 | 1850 | 620ms | 0.8% | - | 数据库压力增大 |
| SC-03 | - | - | - | 3200 连接 | 内存使用 78% |
```

### 2. 瓶颈定位

| 观察 | 可能原因 | 证据 | 建议 |
|------|----------|------|------|
| P95 > 1s (SC-02) | 数据库锁竞争 | `SHOW ENGINE INNODB STATUS` | 添加索引 / 优化 SQL |
| WebSocket 断开 | 内存回收延迟 | `active_connections` 图表 | 增加连接池清理频率 |

---

## 报告输出

### 1. 报告结构

```markdown
# Host Service 压力测试报告

## 1. 测试概述
- 时间 / 环境 / 工具 / 版本

## 2. 测试结果
- 各场景关键指标表
- 图表：响应时间、吞吐量、资源使用

## 3. 瓶颈分析
- 发现的问题与证据
- 根因分析

## 4. 优化建议
- 优先级 / 责任人 / 计划时间

## 5. 附件
- Prometheus 导出数据
- Grafana 截图
- 负载工具输出
- 服务日志
```

### 2. 交付物清单

| 交付物 | 路径 |
|--------|------|
| 测试报告 | `artifacts/reports/host-service-stress-test-report.md` |
| 原始指标数据 | `artifacts/prometheus/*.json` |
| 日志文件 | `artifacts/logs/*.log` |
| 截图 | `artifacts/screenshots/*.png` |
| 负载脚本 | `tests/performance/` |

---

**最后更新**: 2025-01-15  
**文档版本**: 1.0.0  
**维护者**: Host Service 测试团队

