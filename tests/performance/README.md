# k6 性能测试文档与使用教程

本文档详细介绍了性能测试环境的配置、Windows 下的安装方法、核心测试场景说明以及 `common.js` 的配置参数详解。

---

## 1. 核心配置文件 (`tests/performance/utils/common.js`)

`common.js` 是所有性能测试脚本的基础配置文件，集中管理了测试的基础路径、负载策略、默认并发数以及常用的工具函数。

### 1.1 关键配置项说明

**基础路径**
```javascript
export const BASE_URL = 'http://localhost:8000'; // 被测服务地址，根据实际环境修改
```

**动态并发控制**
项目支持通过环境变量 `MAX_VUS` 动态调整最大并发数，默认值为 **100**。

```javascript
// 获取环境变量 MAX_VUS，如果未设置则默认为 100
const MAX_VUS = __ENV.MAX_VUS ? parseInt(__ENV.MAX_VUS) : 100;
```

**负载场景策略 (Ramping VUs)**
默认采用 `ramping-vus`（负载阶梯爬升）执行器：

```javascript
export const DEFAULT_OPTIONS = {
    scenarios: {
        ramp_up_scenario: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: MAX_VUS }, // Setup: 30秒内爬升到最大并发
                { duration: '1m', target: MAX_VUS },  // Run: 持续最大并发压测 1 分钟
                { duration: '30s', target: 0 },       // Teardown: 30秒内逐渐降压归零
            ],
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<3000'], // 阈值：95% 的请求响应需小于 3秒
        http_req_failed: ['rate<0.01'],    // 阈值：错误率需低于 1%
    },
};
```

---

## 2. Windows 安装 k6 教程

### 方法一：使用包管理器 (推荐 - 需 scoop 或 choco)

**使用 Scoop:**
打开 PowerShell，执行：
```powershell
scoop install k6
```

**使用 Chocolatey:**
打开 PowerShell (管理员身份)，执行：
```powershell
choco install k6
```

### 方法二：使用官方安装包 (最简单)
1.  下载最新的 MSI 安装程序：[k6-latest-amd64.msi](https://dl.k6.io/msi/k6-latest-amd64.msi)
2.  双击运行安装程序，按照提示完成安装。

### 方法三：直接下载二进制文件
1.  访问 [k6 GitHub Releases 页面](https://github.com/grafana/k6/releases)。
2.  下载最新的 `k6-vX.X.X-windows-amd64.zip`。
3.  解压文件，将 `k6.exe` 所在的文件夹路径添加到系统的 **环境变量 (Path)** 中。

### 验证安装
打开命令提示符 (CMD) 或 PowerShell，输入：
```bash
k6 version
```

---

## 3. 测试场景说明

以下为项目核心性能测试场景及其详细说明：

| 场景文件 | 功能描述 | 请求路径 | 方法 | 关键参数 | 预期目标 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **available_list.js** | **可用主机查询**<br>模拟用户并发查询可用的云主机列表。 | `/api/v1/host/hosts/available` | POST | `tc_id`, `cycle_name`, `page_size` | 状态码 200,<br>响应 < 2s |
| **hardware_change.js** | **硬件变更上报**<br>模拟 Agent 上报主机硬件配置信息（含 Token）。 | `/api/v1/host/agent/hardware/report` | POST | `name`, `dmr_config`, `tags`, **Headers:** `Authorization` | 状态码 200,<br>响应 < 2s |
| **latest_version.js** | **最新版本检查**<br>模拟 Agent 高频轮询最新版本配置。 | `/api/v1/host/agent/ota/latest` | GET | 无 | 状态码 200,<br>响应 < 2s,<br>含配置数据 |
| **recoverable_list.js** | **可恢复列表查询**<br>模拟查询之前异常断开可恢复连接的主机。 | `/api/v1/host/hosts/retry-vnc` | POST | `user_id` | 状态码 200,<br>响应 < 2s |
| **websocket_status.js** | **WS 状态同步**<br>模拟 Agent 通过 WebSocket 连接并实时上报状态。 | `/api/v1/host/ws/host` | WS | Query Param: `token` | 连接成功 (101),<br>收到 ACK 消息 |

---

## 4. 测试运行教程

### 4.1 运行单个测试场景

在项目根目录下打开终端，运行以下命令（以 `available_list.js` 为例）：

```bash
# 基本运行 (默认并发 100)
k6 run tests/performance/scenarios/available_list.js
```

### 4.2 自定义并发数配置

通过 `-e` 参数传递 `MAX_VUS` 变量来覆盖默认并发数。

**示例：使用 1000 并发运行测试**

```bash
# Windows PowerShell / CMD / Mac / Linux 通用
k6 run -e MAX_VUS=1000 tests/performance/scenarios/available_list.js
```

### 4.3 运行结果分析

测试结束后，终端会输出汇总报告，重点关注以下指标：

*   **http_req_duration**: 请求耗时 (avg=平均, p(95)=95%的请求耗时)。**目标：p(95) < 3000ms**
*   **http_req_failed**: 请求失败率。**目标：< 1.00%**
*   **vus**: 当前并发虚拟用户数。

### 4.4 生成 HTML 可视化报告

脚本已配置 `handleSummary`，运行后会在同级目录自动生成 HTML 报告文件（如 `result.html`或其他命名），直接用浏览器打开即可查看精美的性能图表。
