# Host Service 压力测试计划

## 📋 目录

- [文档说明](#文档说明)
- [测试目标](#测试目标)
- [范围与优先级](#范围与优先级)
- [测试环境](#测试环境)
- [关键指标](#关键指标)
- [压力模型设计](#压力模型设计)
- [场景定义](#场景定义)
- [监控与告警](#监控与告警)
- [风险与应对](#风险与应对)
- [交付物](#交付物)

---

## 文档说明

- **适用对象**: Host Service 测试、开发、运维团队
- **覆盖内容**: 压力测试策略、场景、指标、监控、风险
- **配套文档**: [Host Service 压力测试执行手册](./30-host-service-stress-testing-execution.md)

---

## 测试目标

| 目标 | 说明 |
|------|------|
| **识别瓶颈** | 找出 Host Service 在极端负载下的性能瓶颈（CPU、内存、数据库、网络等） |
| **验证稳定性** | 验证服务在高负载和持续压力下的稳定性及自动恢复能力 |
| **建立容量基线** | 明确单实例的最大承载能力，为容量规划提供依据 |
| **验证自动化监控** | 验证 Prometheus、Grafana、告警规则在压力场景下的有效性 |

---

## 范围与优先级

| 模块 | 说明 | 优先级 |
|------|------|--------|
| 浏览器插件接口 | `/hosts/*`, `/vnc/*`，请求量大、无认证 | ★★★★★ |
| Agent HTTP API | `/agent/*`，硬件上报频率高 | ★★★★☆ |
| 管理后台接口 | `/admin/*`，低频但查询复杂 | ★★★☆☆ |
| 文件管理 | `/file/*`，涉及大文件上传/下载 | ★★★☆☆ |
| WebSocket | `/ws/*`，长连接、消息洪峰 | ★★★★★ |

---

## 测试环境

### 1. 硬件配置

| 组件 | 配置 |
|------|------|
| Host Service | 4C / 8GB / 100GB SSD |
| Gateway Service | 4C / 8GB / 100GB SSD |
| MariaDB | 8C / 16GB / 200GB SSD |
| Redis | 4C / 8GB / 100GB SSD |

### 2. 网络拓扑

```
Load Generator  →  Gateway Service  →  Host Service  →  MariaDB / Redis
                         │
                         └─ Prometheus / Grafana
```

### 3. 软件版本

- Host Service: FastAPI 0.116.1
- Python: 3.8.10
- MariaDB: 10.11
- Redis: 6.0+
- Prometheus: 2.53+
- Grafana: 11.0+

---

## 关键指标

| 指标 | 说明 | 目标 |
|------|------|------|
| **响应时间** | 平均 / P95 / P99 | P95 < 1s |
| **吞吐量** | 请求数 / 秒 (RPS) | 峰值 ≥ 2000 |
| **失败率** | 错误请求占比 | < 1% |
| **CPU 使用率** | Host Service 实例 | < 80% |
| **内存使用率** | Host Service 实例 | < 80% |
| **数据库连接** | MariaDB 活跃连接 | < 80% 池容量 |
| **WebSocket 活跃连接** | 并发连接总数 | ≥ 3000 |

---

## 压力模型设计

### 1. 压力类型

| 类型 | 说明 | 目的 |
|------|------|------|
| **Baseline** | 正常负载（生产日常） | 验证基线性能 |
| **Load** | 逐步增加负载 | 观察性能曲线 |
| **Stress** | 超出设计负载 | 找到崩溃点 |
| **Spike** | 突增负载 | 验证弹性与恢复能力 |
| **Soak** | 长时间恒定压力 | 检测内存泄漏与性能衰退 |

### 2. 加压策略

| 策略 | 描述 |
|------|------|
| **渐进式 (Step Ramp)** | 每 2 分钟增加一定并发，直到峰值 |
| **锯齿形 (Sawtooth)** | 交替升压和降压，模拟真实波动 |
| **脉冲式 (Pulse)** | 短时间内瞬间升到高并发，再迅速下降 |

---

## 场景定义

| 场景 ID | 名称 | 目标 |
|---------|------|------|
| SC-01 | 浏览器接口峰值 | 1000 RPS，验证无认证接口抗压能力 |
| SC-02 | Agent 上报洪峰 | 2000 RPS，模拟大量硬件同时上报 |
| SC-03 | WebSocket 并发 | 3000 并发连接，持续 15 分钟 |
| SC-04 | 文件上传洪峰 | 100 并发上传 10MB 文件 |
| SC-05 | 管理后台复杂查询 | 100 并发执行多条件查询 |
| SC-06 | 组合压力 | HTTP + WebSocket + 文件操作混合 |

---

## 监控与告警

### 1. 监控项

| 类别 | 指标 |
|------|------|
| HTTP | `http_requests_total`, `http_request_duration_seconds` |
| WebSocket | `active_connections`, `websocket_connections_total` |
| 数据库 | `db_query_duration_seconds`, `db_connections_active` |
| 系统 | CPU、内存、磁盘、网络 |

### 2. 告警阈值

| 指标 | 阈值 | 动作 |
|------|------|------|
| P95 响应时间 | > 1s 持续 5 分钟 | 发送警报 |
| 错误率 | > 1% 持续 3 分钟 | 升级警报 |
| WebSocket 连接 | > 95% 容量 | 评估扩容 |
| CPU 使用率 | > 85% 持续 10 分钟 | 分析负载 |

---

## 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 压力导致服务不可用 | 测试环境宕机 | 使用隔离环境，配置自动重启 |
| 数据库过载 | 影响其他服务 | 启用只读实例，设置限流 |
| 日志爆量 | 磁盘占满 | 启用日志轮转，实时监控磁盘 |
| WebSocket 连接泄漏 | 资源耗尽 | 定期清理断开连接，监控连接池 |

---

## 交付物

| 交付物 | 说明 |
|--------|------|
| 压力测试计划 (本文件) | 场景、指标、风险等总体规划 |
| [压力测试执行手册](./30-host-service-stress-testing-execution.md) | 详细步骤、脚本、数据收集 |
| 压力测试数据包 | 原始指标、日志、截图 |
| 压力测试报告 | 结果总结、瓶颈分析、优化建议 |

---

## 📋 执行手册

### 测试前准备

#### 1. 环境检查清单

| 项目 | 检查项 | 命令/方法 | 结果 |
|------|--------|-----------|------|
| 服务进程 | Host Service、Gateway Service | `docker ps` or `systemctl status` | ✅ |
| 数据库 | MariaDB 可连接 | `mysql -h ... -P ... -u ... -p` | ✅ |
| Redis | Redis 可连接 | `redis-cli -h ... ping` | ✅ |
| 监控 | Prometheus/Grafana 可访问 | 浏览器访问 | ✅ |
| 负载工具 | k6 / Locust / ab / wrk / Python 脚本 | `k6 version` 等 | ✅ |

#### 2. 环境变量

```bash
export GATEWAY_URL="http://localhost:8000"
export HOST_URL="http://localhost:8003"
export HOST_API_URL="${GATEWAY_URL}/api/v1/host"
export PROMETHEUS_URL="http://localhost:9090"
export GRAFANA_URL="http://localhost:3000"
```

### 数据与脚本准备

#### 1. 测试数据脚本

```bash
# scripts/prepare_stress_data.sh
bash scripts/prepare_stress_data.sh

# 内容示例：
# - 创建 5000 条模拟主机记录
# - 创建 10000 条 host_exec_log 记录
# - 创建 1000 条待审批记录
# - 生成 10MB / 50MB / 100MB 测试文件
```

#### 2. 负载脚本目录

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

### 单场景执行步骤

#### SC-01 浏览器接口峰值

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

#### SC-02 Agent 上报洪峰

1. 启动 Locust
   ```bash
   locust -f tests/performance/http/locust_agent_report.py --host=${HOST_API_URL}
   ```
2. Web UI 配置
   - 总用户数：2000
   - 生成速率：每秒 200 用户
3. 采集指标：数据库写入延迟、Redis 命中率

#### SC-03 WebSocket 并发

1. 启动 Python 脚本
   ```bash
   python tests/performance/websocket/ws_concurrent_test.py --connections 3000 --messages 50
   ```
2. 监控指标
   - `active_connections{service="host-service"}`
   - `websocket_connections_total`
3. 核对日志（确保无 `Too many connections` 或内存告警）

#### SC-04 文件上传洪峰

1. 准备测试文件：`10MB`, `50MB`, `100MB`
2. 运行脚本
   ```bash
   python tests/performance/http/python_file_upload_test.py --size 10 --concurrency 50 --requests 200
   ```
3. 监控磁盘 IO、网络带宽、响应时间

#### SC-05 管理后台复杂查询

1. k6 脚本：
   ```bash
   k6 run tests/performance/http/k6_admin_host_list.js
   ```
2. 关注数据库查询耗时
   ```promql
   histogram_quantile(0.95, rate(db_query_duration_seconds_bucket{service="host-service",operation="select"}[5m]))
   ```

#### SC-06 组合压力

1. 同时运行以下脚本：
   ```bash
   # HTTP + WebSocket + 文件
   k6 run tests/performance/mixed/k6_mixed_stress.js &
   python tests/performance/websocket/ws_concurrent_test.py --connections 1000 --messages 100 &
   python tests/performance/http/python_file_upload_test.py --size 10 --concurrency 20 --requests 100 &
   wait
   ```
2. 监控整体资源使用与错误率

### 数据采集与记录

#### 1. 采集模板

| 时间 | 场景 | QPS | P95 响应时间 | 错误率 | CPU | 内存 | DB 连接 | 备注 |
|------|------|-----|--------------|--------|-----|------|---------|------|
| 10:00 | SC-01 | 980 | 420ms | 0.3% | 68% | 62% | 45/60 | 正常 |

#### 2. Prometheus 导出

```bash
# 导出 5 分钟数据
curl -G "${PROMETHEUS_URL}/api/v1/query" \
  --data-urlencode 'query=rate(http_requests_total{service="host-service"}[5m])' \
  --data-urlencode "time=$(date +%s)" \
  > artifacts/prometheus/http_requests_total.json
```

#### 3. Grafana 截图

- HTTP Dashboard (P95)
- WebSocket Dashboard (Active Connections)
- Resource Dashboard (CPU/Memory)

#### 4. 日志收集

```bash
# 收集 Host Service 日志
docker logs host-service --since 30m > artifacts/logs/host-service.log

# 收集 Gateway 日志
docker logs gateway-service --since 30m > artifacts/logs/gateway-service.log
```

### 结果分析模板

#### 1. 指标总结

```markdown
| 场景 | 峰值 QPS | P95 响应时间 | 错误率 | 崩溃点 | 备注 |
|------|----------|--------------|--------|--------|------|
| SC-01 | 1050 | 480ms | 0.4% | - | 正常 |
| SC-02 | 1850 | 620ms | 0.8% | - | 数据库压力增大 |
| SC-03 | - | - | - | 3200 连接 | 内存使用 78% |
```

#### 2. 瓶颈定位

| 观察 | 可能原因 | 证据 | 建议 |
|------|----------|------|------|
| P95 > 1s (SC-02) | 数据库锁竞争 | `SHOW ENGINE INNODB STATUS` | 添加索引 / 优化 SQL |
| WebSocket 断开 | 内存回收延迟 | `active_connections` 图表 | 增加连接池清理频率 |

### 报告输出

#### 1. 报告结构

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

#### 2. 交付物清单

| 交付物 | 路径 |
|--------|------|
| 测试报告 | `artifacts/reports/host-service-stress-test-report.md` |
| 原始指标数据 | `artifacts/prometheus/*.json` |
| 日志文件 | `artifacts/logs/*.log` |
| 截图 | `artifacts/screenshots/*.png` |
| 负载脚本 | `tests/performance/` |

---

**最后更新**: 2025-01-29  
**文档版本**: 2.0.0（合并执行手册）  
**维护者**: Host Service 测试团队