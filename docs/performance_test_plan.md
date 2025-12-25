# 性能测试方案文档

## 1. 测试目的
验证 Host Service 在高并发场景下的稳定性与性能表现，确保核心业务接口满足 **500 并发** 下 **响应时间 <= 2s** 的性能指标。

本方案针对以下核心功能进行压测：
1. 浏览器端 - 可用主机列表查询
2. 浏览器端 - 可恢复主机列表查询 (Retry VNC List)
3. WebSocket - Agent 状态变更
4. Agent 端 - 硬件信息上报
5. Agent 端 - 获取最新版本

---

## 2. 测试环境

### 2.1 服务配置 (预期)
*   **CPU**: 4 Core (推荐 Intel Xeon 或同级)
*   **Memory**: 8GB+
*   **Network**: 千兆内网
*   **OS**: Linux (Ubuntu 20.04/22.04)
*   **Service**: FastAPI (Uvicorn workers >= 4)

### 2.2 数据库配置 (预期)
*   **Type**: MariaDB / MySQL 8.0
*   **CPU**: 4 Core
*   **Memory**: 16GB (InnoDB Buffer Pool >= 8GB)
*   **Max Connections**: >= 2000

### 2.3 测试工具
*   **工具**: k6 (Go语言编写的现代化压测工具)
*   **版本**: v0.45.0+

---

## 3. 测试策略

### 3.1 负载模型
*   **并发用户数 (VU)**: 500
*   **压测模式**: Ramp-up (阶梯式加压) -> Stable (稳定运行) -> Ramp-down (减压)
*   **持续时间**:
    *   Setup: 30s (0 -> 500 VU)
    *   Run: 3m (保持 500 VU)
    *   Teardown: 30s (500 -> 0 VU)

### 3.2 结果期望 / SLA
*   **P95 Response Time**: <= 2000ms (2s)
*   **Error Rate**: < 1%
*   **Requests Per Second (RPS)**: 根据业务复杂度，预期单接口 > 500 RPS

---

## 4. 数据准备

为满足 500 并发测试，需预先生成足量数据以避免数据争用(Data Contention)导致锁等待。

| 场景 | 数据需求 | 样本量建议 | 备注 |
| :--- | :--- | :--- | :--- |
| **可用列表查询** | `host_rec` (host_state=0, appr_state=1) | 5,000 条 | 保证分页查询有足够数据 |
| **可恢复列表查询**| `host_exec_log` (case_state!=2), `host_rec` | 5,000 条 | 模拟大量失败任务 |
| **WebSocket** | `host_rec` (对应 host_id) | 1,000 个 | 每个 VU 模拟 1 个 Agent 连接 |
| **硬件上报** | `host_rec` (对应 token) | 1,000 个 | 每个 VU 使用不同 Token |
| **版本获取** | `sys_conf` (key='ota') | 1-5 条 | 静态配置，少量即可 |

### 4.1 预计产生数据
*   **日志表**: 压测期间 `host_exec_log` 可能增加数万条记录。
*   **硬件表**: `host_hw_rec` 可能产生大量历史版本记录。

---

## 5. 测试场景详细设计

### 5.1 浏览器 - 可用列表查询
*   **接口**: `POST /api/v1/browser/host/available`
*   **参数**:
    ```json
    {
      "tc_id": "perf_test_001",
      "cycle_name": "perf_cycle",
      "user_name": "load_tester",
      "page_size": 20,
      "email": "test_${__VU}@example.com"
    }
    ```
*   **逻辑**: 模拟用户打开“可用主机”页面，频繁刷新或翻页。
*   **脚本**: `tests/performance/scenarios/available_list.js`

### 5.2 浏览器 - 可恢复列表查询 (Retry VNC)
*   **接口**: `POST /api/v1/browser/host/retry-vnc`
*   **参数**: `{"user_id": "user_${__VU}"}`
*   **逻辑**: 模拟用户查询需要重试 VNC 连接的主机列表。
*   **脚本**: `tests/performance/scenarios/recoverable_list.js`

### 5.3 WebSocket - Agent 状态变更
*   **接口**: `ws://<host>:<port>/api/v1/agent/ws/host`
*   **认证**: `Authorization: Bearer <JWT Token>`
*   **消息**:
    ```json
    { "type": "status_update", "status": "busy" }
    ```
*   **逻辑**: 建立长连接，并在连接保持期间定期发送状态变更。
*   **脚本**: `tests/performance/scenarios/websocket_status.js`

### 5.4 HTTP - Agent 硬件发生变更
*   **接口**: `POST /api/v1/agent/hardware/report`
*   **参数**: 包含完整 `dmr_config` 的大 JSON。
*   **逻辑**: 模拟 Agent 检测到硬件变更并上报。此接口计算量大（Diff逻辑）。
*   **脚本**: `tests/performance/scenarios/hardware_change.js`

### 5.5 HTTP Agent - 获取最新版本
*   **接口**: `GET /api/v1/agent/ota/latest`
*   **逻辑**: 极高频调用，模拟大规模 Agent 轮询更新。
*   **脚本**: `tests/performance/scenarios/latest_version.js`

---

## 6. 执行与报告

所有脚本均位于 `tests/performance/` 目录下。

### 6.1 运行测试
请确保已安装 k6。

```bash
# 运行单个场景
k6 run tests/performance/scenarios/available_list.js

# 运行所有场景 (组合)
k6 run tests/performance/main.js
```

### 6.2 生成 HTML 报告
使用 `k6-reporter` 生成美观的 HTML 报告。

**脚本位置**: `tests/performance/report_generator.sh`

```bash
# 给予执行权限
chmod +x tests/performance/report_generator.sh

# 执行测试并生成报告
./tests/performance/report_generator.sh available_list
```

生成的报告将位于 `tests/performance/reports/` 目录。
