# 接口压测方案文档

## 📋 概述

本文档提供 Intel EC 微服务系统的完整接口压测方案，包括技术栈选择、参数配置、测试场景、监控指标和结果分析方法。

## 🎯 压测目标

| 目标 | 说明 |
|------|------|
| **性能基准** | 建立各接口的性能基准线（响应时间、吞吐量） |
| **容量规划** | 确定系统最大承载能力，为扩容提供依据 |
| **瓶颈识别** | 识别系统性能瓶颈（CPU、内存、数据库、网络） |
| **稳定性验证** | 验证系统在高负载下的稳定性和恢复能力 |
| **优化验证** | 验证性能优化效果 |

---

## 🛠️ 技术栈选择

### k6 压测工具

**选择理由**：

- ✅ 脚本化，易于版本控制和 CI/CD 集成
- ✅ 内置丰富的性能指标（响应时间、吞吐量、错误率）
- ✅ 支持多种压测模式（ramp-up、constant、spike）
- ✅ 支持多场景并发执行
- ✅ 输出格式友好（JSON、CSV、InfluxDB）
- ✅ 跨平台支持（Windows、Linux、macOS）

**安装方式**：

```bash
# macOS
brew install k6

# Linux (Ubuntu/Debian)
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Linux (CentOS/RHEL)
sudo yum install https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.rpm

# Windows
# 方式1：使用 Chocolatey
choco install k6

# 方式2：使用 Scoop
scoop install k6

# 方式3：手动下载安装
# 访问 https://github.com/grafana/k6/releases
# 下载 k6-v0.47.0-windows-amd64.zip
# 解压到 C:\k6，添加到系统 PATH

# 验证安装
k6 version
```

---

## 📊 k6 压测参数配置

#### 基础参数配置

```javascript
export const options = {
  // ========== 虚拟用户配置 ==========
  vus: 100,                    // 虚拟用户数（并发数）
  duration: '5m',              // 压测持续时间
  
  // ========== 阶段式压测（推荐） ==========
  stages: [
    { duration: '30s', target: 50 },   // 30秒内增加到50并发
    { duration: '1m', target: 50 },    // 保持50并发1分钟
    { duration: '30s', target: 100 },  // 30秒内增加到100并发
    { duration: '2m', target: 100 },   // 保持100并发2分钟
    { duration: '30s', target: 0 },   // 30秒内降到0
  ],
  
  // ========== 恒定速率压测 ==========
  // executor: 'constant-arrival-rate',
  // rate: 100,                  // 每秒100个请求
  // timeUnit: '1s',
  // duration: '5m',
  // preAllocatedVUs: 50,        // 预分配虚拟用户数
  // maxVUs: 200,                // 最大虚拟用户数
  
  // ========== 阈值配置 ==========
  thresholds: {
    // 响应时间阈值
    http_req_duration: [
      'p(50)<200',   // 50% 请求 < 200ms
      'p(95)<500',   // 95% 请求 < 500ms
      'p(99)<1000',  // 99% 请求 < 1000ms
      'max<2000',    // 最大响应时间 < 2000ms
    ],
    
    // 错误率阈值
    http_req_failed: ['rate<0.01'],  // 错误率 < 1%
    
    // 吞吐量阈值
    http_reqs: ['rate>100'],         // 请求速率 > 100 req/s
    
    // 迭代时间阈值
    iteration_duration: ['p(95)<1000'],
  },
  
  // ========== 超时配置 ==========
  httpReq: {
    timeout: '30s',              // HTTP 请求超时时间
  },
  
  // ========== 标签配置 ==========
  tags: {
    test_type: 'load_test',
    service: 'host-service',
  },
};
```

#### 多场景并发配置

```javascript
export const options = {
  scenarios: {
    // 场景1：浏览器接口压测
    browser_api: {
      executor: 'ramping-arrival-rate',
      startRate: 20,              // 起始速率：20 req/s
      timeUnit: '1s',
      stages: [
        { target: 100, duration: '1m' },  // 1分钟内增加到100 req/s
        { target: 200, duration: '2m' },  // 2分钟内增加到200 req/s
        { target: 100, duration: '1m' },  // 1分钟内降到100 req/s
      ],
      preAllocatedVUs: 50,
      maxVUs: 300,
      exec: 'browserApi',
      tags: { scenario: 'browser_api' },
    },
    
    // 场景2：管理后台接口压测
    admin_api: {
      executor: 'constant-arrival-rate',
      rate: 30,                   // 恒定速率：30 req/s
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 20,
      maxVUs: 100,
      exec: 'adminApi',
      tags: { scenario: 'admin_api' },
    },
    
    // 场景3：Agent 上报压测
    agent_report: {
      executor: 'shared-iterations',
      vus: 200,                   // 200个虚拟用户
      iterations: 10000,          // 总共10000次迭代
      exec: 'agentReport',
      tags: { scenario: 'agent_report' },
    },
  },
  
  thresholds: {
    'http_req_duration{scenario:browser_api}': ['p(95)<500'],
    'http_req_duration{scenario:admin_api}': ['p(95)<1000'],
    'http_req_failed': ['rate<0.01'],
  },
};
```

---

## 🎬 压测场景设计

### 场景1：基线测试（Baseline Test）

**目标**：建立性能基准线

**配置**：

```javascript
// k6 配置
export const options = {
  stages: [
    { duration: '1m', target: 10 },   // 10并发，1分钟
    { duration: '2m', target: 10 },    // 保持10并发，2分钟
    { duration: '30s', target: 0 },   // 降为0
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],
    http_req_failed: ['rate<0.001'],
  },
};
```

**预期指标**：

- 平均响应时间：< 150ms
- P95 响应时间：< 200ms
- 错误率：< 0.1%

---

### 场景2：负载测试（Load Test）

**目标**：验证正常负载下的性能

**配置**：

```javascript
export const options = {
  stages: [
    { duration: '2m', target: 50 },    // 逐步增加到50并发
    { duration: '5m', target: 50 },    // 保持50并发5分钟
    { duration: '2m', target: 100 },  // 增加到100并发
    { duration: '5m', target: 100 },   // 保持100并发5分钟
    { duration: '2m', target: 0 },    // 降为0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};
```

**预期指标**：

- 平均响应时间：< 300ms
- P95 响应时间：< 500ms
- P99 响应时间：< 1000ms
- QPS：> 500
- 错误率：< 1%

---

### 场景3：压力测试（Stress Test）

**目标**：找到系统崩溃点

**配置**：

```javascript
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // 正常负载
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },  // 逐步增加
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },  // 继续增加
    { duration: '5m', target: 300 },
    { duration: '2m', target: 400 },  // 接近极限
    { duration: '5m', target: 400 },
    { duration: '10m', target: 400 }, // 保持极限负载
    { duration: '2m', target: 0 },    // 恢复
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 放宽要求
    http_req_failed: ['rate<0.1'],     // 允许更多错误
  },
};
```

**预期指标**：

- 识别性能拐点
- 记录最大承载能力
- 观察系统恢复能力

---

### 场景4：峰值测试（Spike Test）

**目标**：验证突增负载下的系统表现

**配置**：

```javascript
export const options = {
  stages: [
    { duration: '1m', target: 50 },    // 正常负载
    { duration: '30s', target: 500 }, // 突然增加到500并发
    { duration: '1m', target: 500 },  // 保持峰值1分钟
    { duration: '1m', target: 50 },   // 快速降回正常
    { duration: '1m', target: 0 },   // 降为0
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
  },
};
```

**预期指标**：

- 验证系统弹性
- 观察响应时间变化
- 验证自动恢复能力

---

### 场景5：浸泡测试（Soak Test）

**目标**：检测长时间运行下的内存泄漏和性能衰退

**配置**：

```javascript
export const options = {
  stages: [
    { duration: '5m', target: 100 },   // 达到目标负载
    { duration: '2h', target: 100 },   // 保持2小时
    { duration: '5m', target: 0 },    // 降为0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};
```

**监控重点**：

- 内存使用趋势
- CPU使用趋势
- 响应时间趋势
- 数据库连接数

---

### 场景6：混合场景测试（Mixed Scenario Test）

**目标**：模拟真实生产环境的多场景并发

**配置**：

```javascript
export const options = {
  scenarios: {
    // 浏览器接口：高频、无认证
    browser_api: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      timeUnit: '1s',
      stages: [
        { target: 200, duration: '2m' },
        { target: 200, duration: '5m' },
      ],
      preAllocatedVUs: 100,
      maxVUs: 300,
      exec: 'browserApi',
    },
    
    // 管理后台：中频、需认证
    admin_api: {
      executor: 'constant-arrival-rate',
      rate: 30,
      timeUnit: '1s',
      duration: '7m',
      preAllocatedVUs: 20,
      maxVUs: 100,
      exec: 'adminApi',
    },
    
    // Agent上报：高频、简单请求
    agent_report: {
      executor: 'shared-iterations',
      vus: 200,
      iterations: 50000,
      exec: 'agentReport',
    },
  },
  
  thresholds: {
    'http_req_duration{scenario:browser_api}': ['p(95)<500'],
    'http_req_duration{scenario:admin_api}': ['p(95)<1000'],
    'http_req_failed': ['rate<0.01'],
  },
};
```

---

## 📈 监控指标

### 1. 应用层指标

#### HTTP 接口指标

| 指标 | PromQL 查询 | 说明 |
|------|------------|------|
| **请求总数** | `http_requests_total{service="host-service"}` | 累计请求数 |
| **请求速率** | `rate(http_requests_total{service="host-service"}[5m])` | 每秒请求数（RPS） |
| **响应时间（P95）** | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="host-service"}[5m]))` | 95%请求的响应时间 |
| **响应时间（P99）** | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service="host-service"}[5m]))` | 99%请求的响应时间 |
| **错误率** | `rate(http_requests_total{service="host-service",status=~"5.."}[5m]) / rate(http_requests_total{service="host-service"}[5m])` | 5xx错误占比 |
| **成功率** | `rate(http_requests_total{service="host-service",status=~"2.."}[5m]) / rate(http_requests_total{service="host-service"}[5m])` | 2xx响应占比 |

#### WebSocket 指标

| 指标 | PromQL 查询 | 说明 |
|------|------------|------|
| **活跃连接数** | `active_connections{service="host-service"}` | 当前活跃连接数 |
| **连接总数** | `websocket_connections_total{service="host-service"}` | 累计连接数 |
| **连接建立速率** | `rate(websocket_connections_total{service="host-service"}[5m])` | 每秒新建连接数 |
| **消息吞吐量** | `rate(websocket_messages_total{service="host-service"}[5m])` | 每秒消息数 |

### 2. 系统资源指标

| 指标 | 监控方式 | 目标值 |
|------|---------|--------|
| **CPU 使用率** | `process_cpu_seconds_total` | < 70% |
| **内存使用率** | `process_resident_memory_bytes` | < 80% |
| **磁盘IO** | `node_disk_io_time_seconds_total` | < 80% |
| **网络带宽** | `node_network_receive_bytes_total` | < 80% |

### 3. 数据库指标

| 指标 | PromQL 查询 | 目标值 |
|------|------------|--------|
| **查询响应时间** | `histogram_quantile(0.95, rate(db_query_duration_seconds_bucket{service="host-service"}[5m]))` | < 100ms |
| **活跃连接数** | `db_connections_active{service="host-service"}` | < 80%池容量 |
| **查询速率** | `rate(db_queries_total{service="host-service"}[5m])` | 监控趋势 |

### 4. 告警阈值

```yaml
# prometheus/alerts/performance_alerts.yml
groups:
  - name: performance_alerts
    rules:
      # 响应时间告警
      - alert: HighResponseTime
        expr: |
          histogram_quantile(0.95, 
            rate(http_request_duration_seconds_bucket{service="host-service"}[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过高"
          description: "P95 响应时间超过 1 秒，当前值: {{ $value }}s"
      
      # 错误率告警
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{service="host-service",status=~"5.."}[5m]) /
          rate(http_requests_total{service="host-service"}[5m]) > 0.01
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "错误率过高"
          description: "错误率超过 1%，当前值: {{ $value | humanizePercentage }}"
      
      # CPU使用率告警
      - alert: HighCPUUsage
        expr: |
          rate(process_cpu_seconds_total{service="host-service"}[5m]) * 100 > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CPU使用率过高"
          description: "CPU使用率超过 85%，当前值: {{ $value }}%"
      
      # 内存使用率告警
      - alert: HighMemoryUsage
        expr: |
          process_resident_memory_bytes{service="host-service"} / 
          node_memory_MemTotal_bytes * 100 > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率超过 85%，当前值: {{ $value }}%"
      
      # 数据库连接数告警
      - alert: HighDatabaseConnections
        expr: |
          db_connections_active{service="host-service"} / 
          db_connections_max{service="host-service"} * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据库连接数过高"
          description: "数据库连接数超过 80%，当前值: {{ $value }}%"
```

---

## 📊 压测脚本示例

### 性能指标要求

所有接口压测脚本均按照以下性能指标设计：

| 指标 | 要求值 | 说明 |
|------|--------|------|
| **处理能力** | 500并发用户 | 支持500个虚拟用户同时操作 |
| **响应延迟** | < 2秒 | 99%的请求响应时间 < 2秒 |
| **吞吐量** | 每小时10000次 | 单个接口每小时处理10000次请求 |
| **错误率** | < 1% | 请求失败率 < 1% |

### 接口压测脚本列表

#### 浏览器插件接口

1. **`k6_query_available_hosts.js`** - 查询可用主机列表
   - 接口：`POST /api/v1/host/hosts/available`
   - 性能指标：500并发，响应时间<2秒

2. **`k6_vnc_connect.js`** - 获取 VNC 连接信息
   - 接口：`POST /api/v1/host/vnc/connect`
   - 性能指标：500并发，响应时间<2秒

3. **`k6_vnc_report.js`** - 上报 VNC 连接结果
   - 接口：`POST /api/v1/host/vnc/report`
   - 性能指标：500并发，响应时间<2秒

4. **`k6_hosts_release.js`** - 释放主机
   - 接口：`POST /api/v1/host/hosts/release`
   - 性能指标：500并发，响应时间<2秒

5. **`k6_hosts_retry_vnc.js`** - 获取重试 VNC 列表
   - 接口：`POST /api/v1/host/hosts/retry-vnc`
   - 性能指标：500并发，响应时间<2秒

#### 管理后台接口

6. **`k6_admin_host_list.js`** - 查询主机列表（需认证）
   - 接口：`GET /api/v1/host/admin/host/list`
   - 性能指标：500并发，响应时间<2秒

7. **`k6_admin_host_detail.js`** - 获取主机详情（需认证）
   - 接口：`GET /api/v1/host/admin/host/{host_id}`
   - 性能指标：500并发，响应时间<2秒

#### Agent 接口

8. **`k6_agent_hardware_report.js`** - 上报硬件信息（需认证）
   - 接口：`POST /api/v1/host/agent/hardware/report`
   - 性能指标：500并发，响应时间<2秒

9. **`k6_agent_testcase_report.js`** - 上报测试用例结果（需认证）
   - 接口：`POST /api/v1/host/agent/testcase/report`
   - 性能指标：500并发，响应时间<2秒

10. **`k6_agent_ota_latest.js`** - 获取最新 OTA 配置
    - 接口：`GET /api/v1/host/agent/ota/latest`
    - 性能指标：500并发，响应时间<2秒

### 脚本执行示例

```bash
# 浏览器插件接口压测
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003

k6 run tests/performance/http/k6_vnc_connect.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_HOST_ID=1846486359367955051

# 管理后台接口压测（需要提供 token）
k6 run tests/performance/http/k6_admin_host_list.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_ADMIN_TOKEN=your_admin_token

# Agent 接口压测（需要提供 token）
k6 run tests/performance/http/k6_agent_hardware_report.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_AGENT_TOKEN=your_agent_token

# 导出结果
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

### 1. k6 完整压测脚本示例

以下是一个符合性能指标要求的完整压测脚本示例：

```javascript
// tests/performance/http/k6_query_available_hosts.js
// 查询可用主机列表接口压测脚本
// 性能指标：500并发，响应时间<2秒，每小时10000次请求

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const URL = `${HOST}/api/v1/host/hosts/available`;

export const options = {
  // 阶段式压测：逐步增加到500并发
  stages: [
    { duration: '1m', target: 100 },   // 1分钟内增加到100并发
    { duration: '2m', target: 100 },   // 保持100并发2分钟
    { duration: '1m', target: 250 },   // 1分钟内增加到250并发
    { duration: '2m', target: 250 },   // 保持250并发2分钟
    { duration: '1m', target: 500 },   // 1分钟内增加到500并发
    { duration: '5m', target: 500 },   // 保持500并发5分钟（验证稳定性）
    { duration: '1m', target: 0 },     // 1分钟内降为0
  ],
  
  thresholds: {
    // 响应时间阈值：所有请求 < 2秒
    http_req_duration: [
      'p(50)<500',    // 50% 请求 < 500ms
      'p(95)<1500',   // 95% 请求 < 1.5秒
      'p(99)<2000',   // 99% 请求 < 2秒
      'max<3000',     // 最大响应时间 < 3秒
    ],
    
    // 错误率阈值：< 1%
    http_req_failed: ['rate<0.01'],
    
    // 吞吐量阈值：确保达到性能要求
    http_reqs: ['rate>100'],  // 至少100 req/s
  },
  
  httpReq: {
    timeout: '30s',
  },
};

export default function () {
  const payload = JSON.stringify({
    tc_id: `test_case_${__VU}_${__ITER}`,
    cycle_name: 'test_cycle_001',
    user_name: `test_user_${__VU}`,
    page_size: 20,
    last_id: null,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'query_available_hosts' },
  };

  const res = http.post(URL, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'response has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data !== undefined;
      } catch {
        return false;
      }
    },
  });

  // 模拟用户思考时间：1-3秒随机
  sleep(Math.random() * 2 + 1);
}
```

---

## 📋 压测执行流程

### 1. 压测前准备

```bash
# 1. 检查服务状态
curl http://localhost:8003/health
curl http://localhost:8000/health
curl http://localhost:8001/health

# 2. 检查数据库连接
mysql -h 127.0.0.1 -P 3306 -u intel_user -p

# 3. 检查Redis连接
redis-cli -h 127.0.0.1 -p 6379 ping

# 4. 准备测试数据
python scripts/prepare_stress_data.py

# 5. 启动监控
docker-compose up -d prometheus grafana
```

### 2. 执行压测

```bash
# 浏览器插件接口压测
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003

k6 run tests/performance/http/k6_vnc_connect.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_HOST_ID=1846486359367955051

# 管理后台接口压测（需要提供 token）
k6 run tests/performance/http/k6_admin_host_list.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_ADMIN_TOKEN=your_admin_token

# Agent 接口压测（需要提供 token）
k6 run tests/performance/http/k6_agent_hardware_report.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_AGENT_TOKEN=your_agent_token

# 导出结果
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

### 3. 实时监控

```bash
# 查看Prometheus指标
curl http://localhost:9090/api/v1/query?query=rate\(http_requests_total\{service=\"host-service\"\}\[5m\]\)

# 查看Grafana仪表板
open http://localhost:3000

# 查看服务日志
tail -f logs/host-service.log

# 查看Docker容器资源
docker stats host-service gateway-service
```

### 4. 结果分析

#### 4.1 导出 k6 测试结果

```bash
# k6输出JSON结果
k6 run script.js --out json=results/k6_results.json

# 同时导出 JSON 和 CSV 格式
k6 run script.js \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

#### 4.2 使用 k6 报告分析工具

**基础使用**：

```bash
# 在控制台显示分析结果
python3 scripts/analyze_k6_report.py results/k6_results.json

# 显示 Top 20 端点
python3 scripts/analyze_k6_report.py results/k6_results.json -n 20
```

**生成专业报告**：

```bash
# 生成 HTML 格式的专业报告（推荐，美观易读）
python3 scripts/analyze_k6_report.py results/k6_results.json \
  --html results/k6_report.html

# 生成 Markdown 格式的报告（适合文档和版本控制）
python3 scripts/analyze_k6_report.py results/k6_results.json \
  --markdown results/k6_report.md

# 导出 JSON 格式的分析报告（适合程序化处理）
python3 scripts/analyze_k6_report.py results/k6_results.json \
  -o results/k6_analysis_report.json

# 同时生成多种格式（推荐）
python3 scripts/analyze_k6_report.py results/k6_results.json \
  -n 20 \
  -o results/k6_analysis_report.json \
  --html results/k6_report.html \
  --markdown results/k6_report.md
```

**查看报告**：

```bash
# 在浏览器中打开 HTML 报告（推荐）
open results/k6_report.html
# 或
xdg-open results/k6_report.html  # Linux
start results/k6_report.html      # Windows

# 查看 Markdown 报告
cat results/k6_report.md

# 查看 JSON 报告
cat results/k6_analysis_report.json | jq
```

#### 4.3 报告格式说明

**HTML 报告特点**：
- 🎨 **现代化设计**：紫色渐变头部，专业美观
- 📊 **统计卡片**：网格布局展示关键指标，颜色编码（绿色=成功，红色=失败）
- 📋 **数据表格**：清晰的表格展示端点性能，支持悬停高亮
- 📱 **响应式布局**：适配桌面和移动设备
- ✅ **阈值检查**：直观的通过/失败状态显示

**Markdown 报告特点**：
- 📝 **结构化格式**：清晰的表格和标题组织
- ✅ **状态图标**：直观显示检查结果
- 🔍 **易于阅读**：适合文档记录和版本控制
- 📧 **易于分享**：可直接在邮件或文档中使用

**JSON 报告特点**：
- 🔧 **程序化处理**：适合自动化分析和集成
- 📊 **数据导入**：可导入到其他分析工具
- 🔄 **API 集成**：适合与其他系统集成

#### 4.4 k6 报告分析工具功能

- ✅ **多种报告格式**：支持 JSON、HTML（美观可视化）、Markdown 格式
- ✅ **测试时长统计**：自动计算测试开始时间、结束时间和持续时间
- ✅ **HTTP 请求总体统计**：总请求数、成功/失败请求数、错误率
- ✅ **响应时间分析**：平均、最小、最大、P50、P95、P99 响应时间
- ✅ **按端点统计**：每个接口的详细性能指标和状态码分布
- ✅ **关键指标统计**：HTTP 请求数、迭代次数、虚拟用户数、数据传输量等
- ✅ **阈值检查**：自动检查性能阈值是否达标（P50、P95、P99、错误率等）
- ✅ **专业美观**：HTML 报告采用现代化设计，支持响应式布局

详细使用方法请参考：[k6 报告分析工具使用指南](../../scripts/README_analyze_k6_report.md)

---

## 📊 k6 报告分析工具详细说明

### 工具概述

`analyze_k6_report.py` 是项目提供的专业 k6 压测报告分析工具，支持生成多种格式的专业报告，帮助团队快速理解和分析压测结果。

### 报告格式对比

| 格式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **HTML** | 团队展示、会议汇报、存档记录 | 美观直观、响应式设计、颜色编码 | 需要浏览器打开 |
| **Markdown** | 文档集成、版本控制、邮件分享 | 易于编辑、版本控制友好、纯文本 | 需要 Markdown 渲染器 |
| **JSON** | 程序化处理、CI/CD 集成、数据导入 | 结构化数据、易于解析、自动化友好 | 不易直接阅读 |

### HTML 报告特性

HTML 报告采用现代化设计，包含以下特性：

1. **视觉设计**
   - 紫色渐变头部，突出报告标题
   - 统计卡片网格布局，清晰展示关键指标
   - 颜色编码：绿色（成功）、红色（失败）、黄色（警告）

2. **数据展示**
   - 响应式表格，支持悬停高亮
   - 统计卡片展示关键指标
   - 阈值检查结果可视化

3. **用户体验**
   - 响应式布局，适配桌面和移动设备
   - 清晰的层次结构
   - 易于阅读和理解

### 使用示例

#### 示例 1：快速分析

```bash
# 运行压测
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json

# 生成 HTML 报告
python3 scripts/analyze_k6_report.py results/k6_results.json \
  --html results/k6_report.html

# 在浏览器中查看
open results/k6_report.html
```

#### 示例 2：完整分析流程

```bash
# 1. 运行压测
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json

# 2. 生成所有格式的报告
python3 scripts/analyze_k6_report.py results/k6_results.json \
  -n 20 \
  -o results/k6_analysis_report.json \
  --html results/k6_report.html \
  --markdown results/k6_report.md

# 3. 查看报告
open results/k6_report.html          # HTML 报告（推荐）
cat results/k6_report.md              # Markdown 报告
cat results/k6_analysis_report.json | jq  # JSON 报告
```

#### 示例 3：CI/CD 集成

```bash
# 在 CI/CD 流程中生成报告
python3 scripts/analyze_k6_report.py results/k6_results.json \
  --html reports/k6_report_$(date +%Y%m%d_%H%M%S).html \
  --markdown reports/k6_report_$(date +%Y%m%d_%H%M%S).md

# 上传到报告服务器或存储
# scp reports/k6_report_*.html user@server:/var/www/reports/
```

### 报告内容说明

#### 1. 测试时长统计

- **开始时间**：压测开始的时间戳
- **结束时间**：压测结束的时间戳
- **持续时间**：自动计算的测试时长（秒/分钟/小时）

#### 2. HTTP 请求总体统计

- **总请求数**：压测期间发送的总请求数
- **成功请求**：状态码为 200 的请求数
- **失败请求**：状态码非 200 的请求数
- **错误率**：失败请求数 / 总请求数

#### 3. 响应时间分析

- **平均响应时间**：所有请求的平均响应时间
- **最小/最大响应时间**：响应时间的极值
- **P50/P95/P99**：百分位数响应时间，用于评估性能分布

#### 4. 按端点统计

- **端点排名**：按请求数排序的端点列表
- **性能指标**：每个端点的详细性能数据
- **状态码分布**：各状态码的请求数量

#### 5. 阈值检查结果

自动检查以下性能阈值：
- P50 < 500ms
- P95 < 1500ms
- P99 < 2000ms
- Max < 3000ms
- 错误率 < 1%

### 最佳实践

1. **报告命名规范**
   ```bash
   # 使用时间戳命名，便于版本管理
   k6_report_20251206_143000.html
   k6_report_20251206_143000.md
   ```

2. **报告存储**
   - HTML 报告：存储在 `reports/html/` 目录
   - Markdown 报告：存储在 `reports/markdown/` 目录
   - JSON 报告：存储在 `reports/json/` 目录

3. **定期归档**
   - 按日期组织报告
   - 保留历史报告用于对比分析
   - 定期清理过期报告

4. **团队协作**
   - HTML 报告用于团队会议和展示
   - Markdown 报告用于文档和邮件分享
   - JSON 报告用于自动化分析和告警

---

## 📊 压测报告模板

### 报告结构

```markdown
# 接口压测报告

## 1. 测试概述
- 测试时间: 2025-01-29 10:00:00 - 11:00:00
- 测试环境: 本地开发环境
- 测试工具: k6 v0.47.0
- 测试场景: 负载测试

## 2. 测试配置
- 目标服务: Host Service (http://localhost:8003)
- 压测模式: 阶段式压测
- 最大并发: 200 VUs
- 持续时间: 21分钟

## 3. 测试结果摘要

### 3.1 总体指标
| 指标 | 结果 | 目标值 | 状态 |
|------|------|--------|------|
| 总请求数 | 125,000 | - | ✅ |
| 成功请求数 | 124,875 | - | ✅ |
| 失败请求数 | 125 | - | ✅ |
| 错误率 | 0.1% | < 1% | ✅ |
| 平均响应时间 | 245ms | < 300ms | ✅ |
| P95 响应时间 | 485ms | < 500ms | ✅ |
| P99 响应时间 | 890ms | < 1000ms | ✅ |
| 峰值RPS | 1,250 | > 1000 | ✅ |

### 3.2 分阶段结果
| 阶段 | 并发数 | 平均响应时间 | P95响应时间 | RPS | 错误率 |
|------|--------|------------|------------|-----|--------|
| 阶段1 (50并发) | 50 | 180ms | 320ms | 450 | 0.05% |
| 阶段2 (100并发) | 100 | 220ms | 420ms | 850 | 0.08% |
| 阶段3 (200并发) | 200 | 280ms | 520ms | 1,200 | 0.12% |

### 3.3 资源使用情况
| 资源 | 峰值使用率 | 平均使用率 | 状态 |
|------|-----------|-----------|------|
| CPU | 72% | 58% | ✅ |
| 内存 | 68% | 55% | ✅ |
| 数据库连接 | 45/100 | 35/100 | ✅ |
| 网络带宽 | 65% | 50% | ✅ |

## 4. 接口详细结果

### 4.1 POST /api/v1/host/hosts/available
| 指标 | 结果 |
|------|------|
| 请求数 | 100,000 |
| 平均响应时间 | 230ms |
| P95响应时间 | 450ms |
| P99响应时间 | 850ms |
| 错误率 | 0.08% |
| RPS | 950 |

### 4.2 POST /api/v1/host/vnc/connect
| 指标 | 结果 |
|------|------|
| 请求数 | 25,000 |
| 平均响应时间 | 280ms |
| P95响应时间 | 520ms |
| P99响应时间 | 950ms |
| 错误率 | 0.15% |
| RPS | 300 |

## 5. 性能瓶颈分析

### 5.1 发现的问题
1. **数据库查询慢**: 部分复杂查询响应时间超过500ms
2. **内存使用偏高**: 高并发时内存使用率达到68%
3. **连接池不足**: 峰值时数据库连接数接近50%

### 5.2 优化建议
1. 优化数据库查询，添加索引
2. 增加数据库连接池大小
3. 优化内存使用，及时释放资源

## 6. 结论
- ✅ 系统在200并发下表现稳定
- ✅ 所有关键指标均达到目标值
- ⚠️ 需要优化数据库查询性能
- ✅ 建议生产环境配置：4核8GB，连接池100
```

---

## 🔧 压测脚本管理

### 目录结构

```
tests/performance/
├── README.md                          # 压测脚本说明
├── http/                              # HTTP接口压测
│   ├── k6_query_available_hosts.js   # 查询可用主机列表（浏览器插件）
│   ├── k6_vnc_connect.js             # 获取 VNC 连接信息（浏览器插件）
│   ├── k6_vnc_report.js              # 上报 VNC 连接结果（浏览器插件）
│   ├── k6_hosts_release.js           # 释放主机（浏览器插件）
│   ├── k6_hosts_retry_vnc.js         # 获取重试 VNC 列表（浏览器插件）
│   ├── k6_admin_host_list.js         # 查询主机列表（管理后台）
│   ├── k6_admin_host_detail.js       # 获取主机详情（管理后台）
│   ├── k6_agent_hardware_report.js   # 上报硬件信息（Agent）
│   ├── k6_agent_testcase_report.js   # 上报测试用例结果（Agent）
│   ├── k6_agent_ota_latest.js        # 获取最新 OTA 配置（Agent）
│   ├── windows/                       # Windows 平台脚本
│   │   ├── README.md                 # Windows 使用说明
│   │   ├── k6_load_test_windows.js   # Windows k6 压测脚本
│   │   └── run_load_test.bat         # Windows 批处理执行脚本
│   └── linux/                         # Linux 平台脚本
│       ├── README.md                 # Linux 使用说明
│       ├── k6_load_test_linux.js     # Linux k6 压测脚本
│       └── run_load_test.sh          # Linux Shell 执行脚本
├── websocket/                         # WebSocket压测
│   ├── ws_connection_test.py         # 连接测试
│   ├── ws_throughput_test.py         # 吞吐量测试
│   └── ws_concurrent_test.py         # 并发连接测试
├── mixed/                             # 混合场景压测
│   └── k6_mixed_stress.js            # 混合压力测试
└── utils/                             # 工具脚本
    ├── analyze_results.py            # 结果分析脚本
    ├── generate_report.py            # 报告生成脚本
    └── prepare_test_data.py          # 测试数据准备
```

---

## 📚 相关文档

- [性能测试文档](./29-host-service-performance-testing.md) - 详细的性能测试指南
- [压力测试计划](./30-host-service-stress-testing-plan.md) - 压力测试策略
- [压力测试执行手册](./30-host-service-stress-testing-execution.md) - 执行步骤
- [WebSocket测试指南](./24-testing-websocket.md) - WebSocket测试方法

---

## 🪟 Windows 压测方案

### 1. 工具安装

#### k6 安装

```powershell
# 方式1：使用 Chocolatey（推荐）
choco install k6

# 方式2：使用 Scoop
scoop install k6

# 方式3：手动下载安装
# 访问 https://github.com/grafana/k6/releases
# 下载 k6-v0.47.0-windows-amd64.zip
# 解压到 C:\k6，添加到系统 PATH

# 验证安装
k6 version
```

#### wrk 安装（Windows 需要 WSL 或编译）

```powershell
# 方式1：使用 WSL（推荐）
wsl --install
# 在 WSL 中安装 wrk
wsl sudo apt-get install wrk

# 方式2：使用预编译版本
# 下载 https://github.com/wg/wrk/releases
# 解压后使用 wrk.exe
```

### 2. Windows 压测脚本

#### k6 压测脚本（Windows 版本）

```javascript
// tests/performance/http/windows/k6_load_test_windows.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自定义指标
const errorRate = new Rate('errors');
const customTrend = new Trend('custom_response_time');

// Windows 环境变量读取
const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const TOKEN = __ENV.K6_ADMIN_TOKEN || '';

export const options = {
  // Windows 系统建议降低并发数（文件描述符限制）
  stages: [
    { duration: '2m', target: 30 },    // 逐步增加到30并发
    { duration: '5m', target: 30 },    // 保持30并发5分钟
    { duration: '2m', target: 50 },    // 增加到50并发
    { duration: '5m', target: 50 },    // 保持50并发5分钟
    { duration: '2m', target: 0 },     // 降为0
  ],
  
  thresholds: {
    http_req_duration: [
      'p(50)<200',   // 50% 请求 < 200ms
      'p(95)<500',   // 95% 请求 < 500ms
      'p(99)<1000',  // 99% 请求 < 1000ms
    ],
    http_req_failed: ['rate<0.01'],    // 错误率 < 1%
    http_reqs: ['rate>50'],            // 请求速率 > 50 req/s
    errors: ['rate<0.01'],             // 自定义错误率 < 1%
  },
  
  // Windows 特殊配置
  httpReq: {
    timeout: '30s',
    // Windows 下建议启用连接复用
    noConnectionReuse: false,
  },
  
  tags: {
    test_type: 'load_test',
    service: 'host-service',
    platform: 'windows',
    environment: __ENV.K6_ENV || 'local',
  },
};

export function setup() {
  // 压测前准备：获取token、准备数据等
  const loginUrl = `${HOST}/api/v1/auth/admin/login`;
  const loginPayload = JSON.stringify({
    username: 'admin',
    ***REMOVED***word: '***REMOVED***',
  });
  
  const loginRes = http.post(loginUrl, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  if (loginRes.status === 200) {
    const loginData = JSON.parse(loginRes.body);
    return { token: loginData.data.access_token };
  }
  
  return { token: TOKEN };
}

export default function (data) {
  const token = data.token;
  
  // 场景1：查询可用主机列表
  const queryUrl = `${HOST}/api/v1/host/hosts/available`;
  const queryPayload = JSON.stringify({
    tc_id: `test_case_${__VU}_${__ITER}`,
    cycle_name: 'test_cycle',
    user_name: 'test_user',
    page_size: 20,
  });
  
  const queryRes = http.post(queryUrl, queryPayload, {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'query_available_hosts' },
  });
  
  const querySuccess = check(queryRes, {
    '查询状态码200': (r) => r.status === 200,
    '查询响应时间<500ms': (r) => r.timings.duration < 500,
    '响应包含data字段': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data !== undefined;
      } catch {
        return false;
      }
    },
  });
  
  errorRate.add(!querySuccess);
  customTrend.add(queryRes.timings.duration);
  
  sleep(1);
  
  // 场景2：获取VNC连接信息（需要认证）
  if (token) {
    const vncUrl = `${HOST}/api/v1/host/vnc/connect`;
    const vncPayload = JSON.stringify({
      id: '1846486359367955051',
    });
    
    const vncRes = http.post(vncUrl, vncPayload, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      tags: { endpoint: 'get_vnc_connection' },
    });
    
    check(vncRes, {
      'VNC状态码200': (r) => r.status === 200,
    });
  }
  
  sleep(1);
}

export function teardown(data) {
  // 压测后清理
  console.log('压测完成，开始清理...');
}
```

### 3. Windows 执行命令

#### PowerShell 执行脚本

```powershell
# k6 压测执行
$env:K6_HOST_URL = "http://localhost:8003"
$env:K6_ENV = "local"
k6 run tests/performance/http/windows/k6_load_test_windows.js

# k6 压测（带输出）
k6 run tests/performance/http/windows/k6_load_test_windows.js `
  --out json=results/windows_k6_results.json `
  --out csv=results/windows_k6_results.csv


#### Windows 批处理脚本

```batch
@echo off
REM tests/performance/http/windows/run_load_test.bat
REM Windows 压测执行脚本

set HOST_URL=http://localhost:8003
set TEST_ENV=local
set RESULTS_DIR=results

REM 创建结果目录
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%

echo ========================================
echo Windows 压测脚本
echo ========================================
echo 目标服务: %HOST_URL%
echo 测试环境: %TEST_ENV%
echo 结果目录: %RESULTS_DIR%
echo ========================================

echo.
echo 执行 k6 压测...
set K6_HOST_URL=%HOST_URL%
set K6_ENV=%TEST_ENV%
k6 run tests/performance/http/windows/k6_load_test_windows.js --out json=%RESULTS_DIR%/k6_results.json --out csv=%RESULTS_DIR%/k6_results.csv

echo.
echo ========================================
echo 压测完成！
echo 结果文件保存在: %RESULTS_DIR%
echo ========================================
pause
```

### 4. Windows 参数配置建议

| 参数 | Windows 推荐值 | 说明 |
|------|---------------|------|
| **k6 VUs** | 30-50 | Windows 文件描述符限制较低 |
| **k6 并发连接** | 50-100 | 避免系统资源耗尽 |
| **请求超时** | 30s | Windows 网络栈较慢 |

### 5. Windows 系统优化

```powershell
# 1. 增加 TCP 连接数限制
netsh int tcp set global autotuninglevel=normal
netsh int tcp set global chimney=enabled
netsh int tcp set global rss=enabled

# 2. 检查文件描述符限制（需要管理员权限）
# Windows 默认限制较高，通常不需要调整

# 3. 关闭 Windows Defender 实时保护（测试时）
Set-MpPreference -DisableRealtimeMonitoring $true

# 4. 设置电源计划为高性能
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

---

## 🐧 Linux 压测方案

### 1. 工具安装

#### k6 安装

```bash
# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# CentOS/RHEL
sudo yum install https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.rpm

# 验证安装
k6 version
```

### 2. Linux 压测脚本

#### k6 压测脚本（Linux 版本）

```javascript
// tests/performance/http/linux/k6_load_test_linux.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自定义指标
const errorRate = new Rate('errors');
const customTrend = new Trend('custom_response_time');

// Linux 环境变量读取
const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const TOKEN = __ENV.K6_ADMIN_TOKEN || '';

export const options = {
  // Linux 系统可以支持更高的并发数
  stages: [
    { duration: '2m', target: 100 },   // 逐步增加到100并发
    { duration: '5m', target: 100 },   // 保持100并发5分钟
    { duration: '2m', target: 200 },   // 增加到200并发
    { duration: '5m', target: 200 },   // 保持200并发5分钟
    { duration: '2m', target: 300 },   // 增加到300并发
    { duration: '5m', target: 300 },   // 保持300并发5分钟
    { duration: '2m', target: 0 },     // 降为0
  ],
  
  thresholds: {
    http_req_duration: [
      'p(50)<200',   // 50% 请求 < 200ms
      'p(95)<500',   // 95% 请求 < 500ms
      'p(99)<1000',  // 99% 请求 < 1000ms
    ],
    http_req_failed: ['rate<0.01'],    // 错误率 < 1%
    http_reqs: ['rate>200'],           // 请求速率 > 200 req/s
    errors: ['rate<0.01'],             // 自定义错误率 < 1%
  },
  
  // Linux 特殊配置
  httpReq: {
    timeout: '30s',
    noConnectionReuse: false,
  },
  
  tags: {
    test_type: 'load_test',
    service: 'host-service',
    platform: 'linux',
    environment: __ENV.K6_ENV || 'local',
  },
};

export function setup() {
  // 压测前准备：获取token、准备数据等
  const loginUrl = `${HOST}/api/v1/auth/admin/login`;
  const loginPayload = JSON.stringify({
    username: 'admin',
    ***REMOVED***word: '***REMOVED***',
  });
  
  const loginRes = http.post(loginUrl, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  if (loginRes.status === 200) {
    const loginData = JSON.parse(loginRes.body);
    return { token: loginData.data.access_token };
  }
  
  return { token: TOKEN };
}

export default function (data) {
  const token = data.token;
  
  // 场景1：查询可用主机列表
  const queryUrl = `${HOST}/api/v1/host/hosts/available`;
  const queryPayload = JSON.stringify({
    tc_id: `test_case_${__VU}_${__ITER}`,
    cycle_name: 'test_cycle',
    user_name: 'test_user',
    page_size: 20,
  });
  
  const queryRes = http.post(queryUrl, queryPayload, {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'query_available_hosts' },
  });
  
  const querySuccess = check(queryRes, {
    '查询状态码200': (r) => r.status === 200,
    '查询响应时间<500ms': (r) => r.timings.duration < 500,
    '响应包含data字段': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data !== undefined;
      } catch {
        return false;
      }
    },
  });
  
  errorRate.add(!querySuccess);
  customTrend.add(queryRes.timings.duration);
  
  sleep(1);
  
  // 场景2：获取VNC连接信息（需要认证）
  if (token) {
    const vncUrl = `${HOST}/api/v1/host/vnc/connect`;
    const vncPayload = JSON.stringify({
      id: '1846486359367955051',
    });
    
    const vncRes = http.post(vncUrl, vncPayload, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      tags: { endpoint: 'get_vnc_connection' },
    });
    
    check(vncRes, {
      'VNC状态码200': (r) => r.status === 200,
    });
  }
  
  sleep(1);
}

export function teardown(data) {
  // 压测后清理
  console.log('压测完成，开始清理...');
}
```

### 3. Linux 执行命令

#### Bash 执行脚本

```bash
#!/bin/bash
# tests/performance/http/linux/run_load_test.sh
# Linux 压测执行脚本

HOST_URL="${K6_HOST_URL:-http://localhost:8003}"
TEST_ENV="${K6_ENV:-local}"
RESULTS_DIR="results"

# 创建结果目录
mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "Linux 压测脚本"
echo "========================================"
echo "目标服务: $HOST_URL"
echo "测试环境: $TEST_ENV"
echo "结果目录: $RESULTS_DIR"
echo "========================================"

echo ""
echo "执行 k6 压测..."
export K6_HOST_URL="$HOST_URL"
export K6_ENV="$TEST_ENV"
k6 run tests/performance/http/linux/k6_load_test_linux.js \
  --out json="$RESULTS_DIR/linux_k6_results.json" \
  --out csv="$RESULTS_DIR/linux_k6_results.csv"

echo ""
echo "========================================"
echo "压测完成！"
echo "结果文件保存在: $RESULTS_DIR"
echo "========================================"
```

#### 使用示例

```bash
# 赋予执行权限
chmod +x tests/performance/http/linux/run_load_test.sh

# 执行脚本
./tests/performance/http/linux/run_load_test.sh

# 或直接执行 k6
export K6_HOST_URL=http://localhost:8003
export K6_ENV=local
k6 run tests/performance/http/linux/k6_load_test_linux.js
```

### 4. Linux 参数配置建议

| 参数 | Linux 推荐值 | 说明 |
|------|-------------|------|
| **k6 VUs** | 100-500 | Linux 支持高并发 |
| **k6 并发连接** | 200-1000 | 充分利用系统资源 |
| **请求超时** | 30s | 标准超时时间 |

### 5. Linux 系统优化

```bash
# 1. 增加文件描述符限制
ulimit -n 65535

# 永久设置（编辑 /etc/security/limits.conf）
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 2. 优化 TCP 参数
sudo sysctl -w net.core.somaxconn=65535
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=65535
sudo sysctl -w net.ipv4.ip_local_port_range="10000 65535"

# 永久设置（编辑 /etc/sysctl.conf）
cat <<EOF | sudo tee -a /etc/sysctl.conf
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=65535
net.ipv4.ip_local_port_range=10000 65535
EOF

sudo sysctl -p

# 3. 优化网络参数
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
sudo sysctl -w net.ipv4.tcp_fin_timeout=30
sudo sysctl -w net.ipv4.tcp_keepalive_time=600

# 4. 检查系统资源
free -h
df -h
top
htop  # 需要安装: sudo apt-get install htop

# 5. 监控网络连接
netstat -an | grep ESTABLISHED | wc -l
ss -s
```

### 6. Linux 分布式压测

#### k6 云压测（k6 Cloud）

```bash
# 登录 k6 Cloud
k6 login cloud

# 运行云压测
k6 cloud tests/performance/http/linux/k6_load_test_linux.js

# 或使用环境变量
export K6_CLOUD_TOKEN=your-token
k6 cloud tests/performance/http/linux/k6_load_test_linux.js
```

---

## 📊 Windows vs Linux 对比

| 特性 | Windows | Linux |
|------|---------|-------|
| **推荐工具** | k6 | k6 |
| **最大并发数** | 30-50 VUs | 100-500 VUs |
| **文件描述符** | 默认较高 | 需要优化（65535） |
| **网络性能** | 中等 | 优秀 |
| **系统资源** | 占用较高 | 占用较低 |
| **分布式压测** | k6 Cloud | k6 Cloud |
| **脚本执行** | PowerShell/Batch | Bash |
| **推荐场景** | 开发测试、小规模压测 | 生产压测、大规模压测 |

---

## 🆘 常见问题

### Q1: k6 压测时连接数不够怎么办？

**A**: 增加系统文件描述符限制：

```bash
# macOS / Linux
ulimit -n 65535

# 或在脚本中设置
export const options = {
  // ... 其他配置
  httpReq: {
    timeout: '30s',
  },
  // 增加连接池大小
  noConnectionReuse: false,
};
```

### Q2: k6 如何实现分布式压测？

**A**: 使用 k6 Cloud 或 k6 Operator：

```bash
# k6 Cloud 分布式压测
k6 login cloud
k6 cloud script.js

# 或使用 k6 Operator (Kubernetes)
kubectl apply -f k6-operator.yaml
```

### Q3: 如何导出压测结果？

**A**:

```bash
# k6导出JSON
k6 run script.js --out json=results.json

# k6导出CSV
k6 run script.js --out csv=results.csv

# k6导出InfluxDB
k6 run script.js --out influxdb=http://localhost:8086/k6

# k6导出多个格式
k6 run script.js --out json=results.json --out csv=results.csv
```

### Q4: 如何分析 k6 压测报告？

**A**: 使用项目提供的 k6 报告分析工具：

```bash
# 基础使用 - 分析 JSON 报告
python3 scripts/analyze_k6_report.py tests/performance/http/results/k6_results.json

# 显示 Top 20 端点
python3 scripts/analyze_k6_report.py results/k6_results.json -n 20

# 导出 JSON 格式的分析报告
python3 scripts/analyze_k6_report.py results/k6_results.json \
  -o results/k6_analysis_report.json

# 生成 HTML 格式的专业报告（推荐，美观易读）
python3 scripts/analyze_k6_report.py results/k6_results.json \
  --html results/k6_report.html

# 生成 Markdown 格式的报告
python3 scripts/analyze_k6_report.py results/k6_results.json \
  --markdown results/k6_report.md

# 同时生成多种格式
python3 scripts/analyze_k6_report.py results/k6_results.json \
  -o results/k6_analysis_report.json \
  --html results/k6_report.html \
  --markdown results/k6_report.md \
  -n 20
```

**分析工具功能**：

- ✅ **多种报告格式**：支持 JSON、HTML（美观可视化）、Markdown 格式
- ✅ **测试时长统计**：自动计算测试开始时间、结束时间和持续时间
- ✅ **HTTP 请求总体统计**：总请求数、成功/失败请求数、错误率
- ✅ **响应时间分析**：平均、最小、最大、P50、P95、P99 响应时间
- ✅ **按端点统计**：每个接口的详细性能指标和状态码分布
- ✅ **关键指标统计**：HTTP 请求数、迭代次数、虚拟用户数、数据传输量等
- ✅ **阈值检查**：自动检查性能阈值是否达标（P50、P95、P99、错误率等）
- ✅ **专业美观**：HTML 报告采用现代化设计，支持响应式布局

**完整使用流程**：

```bash
# 1. 运行压测并导出 JSON 报告
k6 run tests/performance/http/k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=tests/performance/http/results/k6_results.json

# 2. 使用分析工具生成多种格式的报告
python3 scripts/analyze_k6_report.py \
  tests/performance/http/results/k6_results.json \
  -n 20 \
  -o tests/performance/http/results/k6_analysis_report.json \
  --html tests/performance/http/results/k6_report.html \
  --markdown tests/performance/http/results/k6_report.md

# 3. 查看分析报告
# 在浏览器中打开 HTML 报告（推荐，最直观）
open tests/performance/http/results/k6_report.html

# 或查看 Markdown 报告
cat tests/performance/http/results/k6_report.md

# 或查看 JSON 报告（程序化处理）
cat tests/performance/http/results/k6_analysis_report.json | jq
```

**报告使用建议**：

- 📊 **HTML 报告**：用于团队展示、会议汇报、存档记录
- 📝 **Markdown 报告**：用于文档集成、版本控制、邮件分享
- 🔧 **JSON 报告**：用于自动化分析、CI/CD 集成、数据导入
