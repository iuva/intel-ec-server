# Host Service 接口压测脚本

## 📋 概述

本目录包含 Host Service 所有接口的 k6 压测脚本，所有脚本均按照统一的性能指标设计。

## 🎯 性能指标要求

| 指标 | 要求值 | 说明 |
|------|--------|------|
| **处理能力** | 500并发用户 | 支持500个虚拟用户同时操作 |
| **响应延迟** | < 2秒 | 99%的请求响应时间 < 2秒 |
| **吞吐量** | 每小时10000次 | 单个接口每小时处理10000次请求 |
| **错误率** | < 1% | 请求失败率 < 1% |

## 📝 压测脚本列表

### 浏览器插件接口

1. **`k6_query_available_hosts.js`** - 查询可用主机列表
   - 接口：`POST /api/v1/host/hosts/available`
   - 环境变量：`K6_HOST_URL`（可选，默认：http://localhost:8003）

2. **`k6_vnc_connect.js`** - 获取 VNC 连接信息
   - 接口：`POST /api/v1/host/vnc/connect`
   - 环境变量：`K6_HOST_URL`, `K6_HOST_ID`（可选）

3. **`k6_vnc_report.js`** - 上报 VNC 连接结果
   - 接口：`POST /api/v1/host/vnc/report`
   - 环境变量：`K6_HOST_URL`, `K6_HOST_ID`（可选）

4. **`k6_hosts_release.js`** - 释放主机
   - 接口：`POST /api/v1/host/hosts/release`
   - 环境变量：`K6_HOST_URL`, `K6_HOST_ID`（可选）

5. **`k6_hosts_retry_vnc.js`** - 获取重试 VNC 列表
   - 接口：`POST /api/v1/host/hosts/retry-vnc`
   - 环境变量：`K6_HOST_URL`（可选）

### 管理后台接口（需要认证）

6. **`k6_admin_host_list.js`** - 查询主机列表
   - 接口：`GET /api/v1/host/admin/host/list`
   - 环境变量：`K6_HOST_URL`, `K6_ADMIN_TOKEN`（可选，未提供时会自动登录）

7. **`k6_admin_host_detail.js`** - 获取主机详情
   - 接口：`GET /api/v1/host/admin/host/{host_id}`
   - 环境变量：`K6_HOST_URL`, `K6_HOST_ID`, `K6_ADMIN_TOKEN`（可选）

### Agent 接口（需要认证）

8. **`k6_agent_hardware_report.js`** - 上报硬件信息
   - 接口：`POST /api/v1/host/agent/hardware/report`
   - 环境变量：`K6_HOST_URL`, `K6_AGENT_TOKEN`（必需）

9. **`k6_agent_testcase_report.js`** - 上报测试用例结果
   - 接口：`POST /api/v1/host/agent/testcase/report`
   - 环境变量：`K6_HOST_URL`, `K6_AGENT_TOKEN`（必需）

10. **`k6_agent_ota_latest.js`** - 获取最新 OTA 配置
    - 接口：`GET /api/v1/host/agent/ota/latest`
    - 环境变量：`K6_HOST_URL`（可选）

## 🚀 使用方法

### 基础执行

```bash
# 浏览器插件接口（无需认证）
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003

# 管理后台接口（自动登录）
k6 run k6_admin_host_list.js \
  --env K6_HOST_URL=http://localhost:8003

# Agent 接口（需要提供 token）
k6 run k6_agent_hardware_report.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --env K6_AGENT_TOKEN=your_agent_token
```

### 导出结果

```bash
# 导出 JSON 和 CSV 格式结果
k6 run k6_query_available_hosts.js \
  --env K6_HOST_URL=http://localhost:8003 \
  --out json=results/k6_results.json \
  --out csv=results/k6_results.csv
```

### 批量执行所有接口

```bash
# Linux/macOS
for script in k6_*.js; do
  echo "执行压测: $script"
  k6 run "$script" \
    --env K6_HOST_URL=http://localhost:8003 \
    --out json="results/${script%.js}_results.json"
done

# Windows PowerShell
Get-ChildItem k6_*.js | ForEach-Object {
  Write-Host "执行压测: $($_.Name)"
  k6 run $_.Name `
    --env K6_HOST_URL=http://localhost:8003 `
    --out json="results/$($_.BaseName)_results.json"
}
```

## ⚙️ 压测配置说明

所有脚本使用统一的压测配置：

### 阶段式压测

```javascript
stages: [
  { duration: '1m', target: 100 },   // 1分钟内增加到100并发
  { duration: '2m', target: 100 },   // 保持100并发2分钟
  { duration: '1m', target: 250 },   // 1分钟内增加到250并发
  { duration: '2m', target: 250 },   // 保持250并发2分钟
  { duration: '1m', target: 500 },   // 1分钟内增加到500并发
  { duration: '5m', target: 500 },   // 保持500并发5分钟（验证稳定性）
  { duration: '1m', target: 0 },     // 1分钟内降为0
]
```

### 性能阈值

```javascript
thresholds: {
  http_req_duration: [
    'p(50)<500',    // 50% 请求 < 500ms
    'p(95)<1500',   // 95% 请求 < 1.5秒
    'p(99)<2000',   // 99% 请求 < 2秒
    'max<3000',     // 最大响应时间 < 3秒
  ],
  http_req_failed: ['rate<0.01'],  // 错误率 < 1%
  http_reqs: ['rate>100'],         // 至少100 req/s
}
```

## 📊 结果分析

### 查看压测结果

```bash
# 查看 JSON 结果
cat results/k6_results.json | jq

# 查看 CSV 结果
cat results/k6_results.csv
```

### 使用 k6 报告分析工具

项目提供了专门的 k6 报告分析工具，可以自动解析 JSON 报告并生成详细的统计分析：

```bash
# 基础使用
python3 ../../scripts/analyze_k6_report.py results/k6_results.json

# 显示 Top 20 端点
python3 ../../scripts/analyze_k6_report.py results/k6_results.json -n 20

# 导出 JSON 格式的分析报告
python3 ../../scripts/analyze_k6_report.py results/k6_results.json \
  -o results/k6_analysis_report.json

# 生成 HTML 格式的专业报告（推荐，美观易读）
python3 ../../scripts/analyze_k6_report.py results/k6_results.json \
  --html results/k6_report.html

# 生成 Markdown 格式的报告
python3 ../../scripts/analyze_k6_report.py results/k6_results.json \
  --markdown results/k6_report.md

# 同时生成多种格式
python3 ../../scripts/analyze_k6_report.py results/k6_results.json \
  -o results/k6_analysis_report.json \
  --html results/k6_report.html \
  --markdown results/k6_report.md \
  -n 20
```

**分析工具功能**：

- ✅ **测试时长统计**：自动计算测试开始时间、结束时间和持续时间
- ✅ **HTTP 请求总体统计**：总请求数、成功/失败请求数、错误率
- ✅ **响应时间分析**：平均、最小、最大、P50、P95、P99 响应时间
- ✅ **按端点统计**：每个接口的详细性能指标
- ✅ **关键指标统计**：HTTP 请求数、迭代次数、虚拟用户数、数据传输量等
- ✅ **阈值检查**：自动检查性能阈值是否达标（P50、P95、P99、错误率等）

**分析报告示例**：

```
================================================================================
k6 压测报告分析
================================================================================

分析时间: 2025-01-29 14:30:00
报告文件: results/k6_results.json
数据点总数: 198781
指标数量: 15

--------------------------------------------------------------------------------
测试时长
--------------------------------------------------------------------------------
  开始时间: 2025-12-05T14:29:17.609491+08:00
  结束时间: 2025-12-05T14:35:23.123456+08:00
  持续时间: 6.1 分钟

--------------------------------------------------------------------------------
HTTP 请求总体统计
--------------------------------------------------------------------------------
  总请求数: 12,345
  成功请求: 12,300
  失败请求: 45
  错误率: 0.36%

  响应时间统计:
    平均: 64.32 ms
    最小: 12.45 ms
    最大: 1,234.56 ms
    P50:  58.23 ms
    P95:  128.45 ms
    P99:  256.78 ms

--------------------------------------------------------------------------------
按端点统计 (Top 10)
--------------------------------------------------------------------------------

1. query_available_hosts
   总请求数: 8,234
   成功请求: 8,200
   失败请求: 34
   错误率: 0.41%
   响应时间:
     平均: 63.25 ms
     P95:  125.34 ms
     P99:  245.67 ms
   状态码分布: 200: 8200, 500: 34
...
```

### 关键指标

- **总请求数**：压测期间发送的总请求数
- **成功请求数**：状态码为 200 的请求数
- **失败请求数**：状态码非 200 的请求数
- **错误率**：失败请求数 / 总请求数
- **平均响应时间**：所有请求的平均响应时间
- **P95 响应时间**：95% 请求的响应时间
- **P99 响应时间**：99% 请求的响应时间
- **RPS**：每秒请求数（Requests Per Second）

## 🔧 环境变量说明

| 环境变量 | 说明 | 默认值 | 必需 |
|---------|------|--------|------|
| `K6_HOST_URL` | Host Service 服务地址 | http://localhost:8003 | 否 |
| `K6_HOST_ID` | 主机ID（用于需要 host_id 的接口） | 1846486359367955051 | 否 |
| `K6_ADMIN_TOKEN` | 管理后台认证 Token | - | 否（未提供时自动登录） |
| `K6_AGENT_TOKEN` | Agent 认证 Token | - | 是（Agent 接口必需） |

## 📚 相关文档

- [完整压测方案文档](../../docs/34-api-load-testing-plan.md)
- [Windows 压测指南](./windows/README.md)
- [Linux 压测指南](./linux/README.md)

---

**最后更新**: 2025-01-29

