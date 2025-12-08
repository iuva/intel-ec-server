# Windows 压测脚本使用说明

## 📋 概述

本目录包含适用于 Windows 平台的压测脚本和工具。

## 🛠️ 工具安装

### k6 安装

```powershell
# 方式1：使用 Chocolatey（推荐）
choco install k6

# 方式2：使用 Scoop
scoop install k6

# 验证安装
k6 version
```


## 📝 脚本说明

### k6_load_test_windows.js

k6 压测脚本，适用于 Windows 平台。

**特点**：
- 降低并发数（30-50 VUs），适配 Windows 系统限制
- 增加等待时间，降低系统压力
- 支持环境变量配置

**使用方法**：

```powershell
# 设置环境变量
$env:K6_HOST_URL = "http://localhost:8003"
$env:K6_ENV = "local"

# 执行压测
k6 run k6_load_test_windows.js

# 导出结果
k6 run k6_load_test_windows.js --out json=results/k6_results.json
```

### run_load_test.bat

Windows 批处理脚本，提供交互式压测执行。

**使用方法**：

```cmd
run_load_test.bat
```

脚本会提示选择压测工具（k6 或 Locust），并自动执行相应的压测。

## ⚙️ 参数配置

| 参数 | Windows 推荐值 | 说明 |
|------|---------------|------|
| **k6 VUs** | 30-50 | Windows 文件描述符限制较低 |
| **k6 并发连接** | 50-100 | 避免系统资源耗尽 |
| **请求超时** | 30s | Windows 网络栈较慢 |

## 🔧 系统优化

```powershell
# 1. 增加 TCP 连接数限制
netsh int tcp set global autotuninglevel=normal
netsh int tcp set global chimney=enabled
netsh int tcp set global rss=enabled

# 2. 关闭 Windows Defender 实时保护（测试时）
Set-MpPreference -DisableRealtimeMonitoring $true

# 3. 设置电源计划为高性能
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

## 📊 结果文件

压测结果会保存在 `results/` 目录下：

- `k6_results.json` - k6 JSON 格式结果
- `k6_results.csv` - k6 CSV 格式结果

## 🆘 常见问题

### Q1: k6 压测时连接数不够怎么办？

**A**: Windows 默认文件描述符限制较高，通常不需要调整。如果遇到问题，可以降低并发数。

### Q2: 如何查看压测结果？

**A**: 
- 查看控制台输出
- 查看 JSON 结果文件：`results/k6_results.json`
- 查看 CSV 结果文件：`results/k6_results.csv`

---

**最后更新**: 2025-01-29

