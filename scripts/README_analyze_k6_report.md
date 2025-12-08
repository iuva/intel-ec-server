# k6 报告分析工具使用指南

## 📋 概述

`analyze_k6_report.py` 是一个专门用于分析 k6 压测工具导出的 JSON 格式报告的工具。它可以自动解析报告文件，生成详细的统计分析，包括测试时长、HTTP 请求统计、响应时间分析、端点性能指标等。

## 🚀 快速开始

### 基础使用

```bash
# 分析 k6 JSON 报告
python3 scripts/analyze_k6_report.py tests/performance/http/results/k6_results.json
```

### 显示 Top N 端点

```bash
# 显示 Top 20 端点
python3 scripts/analyze_k6_report.py results/k6_results.json -n 20
```

### 导出多种格式的报告

```bash
# 导出 JSON 格式的分析报告
python3 scripts/analyze_k6_report.py results/k6_results.json \
  -o results/k6_analysis_report.json

# 生成 HTML 格式的专业报告（推荐）
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

## 📊 报告格式

### HTML 报告（推荐）

HTML 报告提供美观的可视化界面，包含：
- 🎨 现代化的渐变设计和响应式布局
- 📊 统计卡片展示关键指标
- 📋 详细的表格展示端点性能
- ✅ 直观的阈值检查结果
- 📱 支持移动端查看

### Markdown 报告

Markdown 报告适合：
- 📝 文档记录和版本控制
- 📧 邮件分享和团队协作
- 🔍 易于阅读和编辑
- 📚 集成到项目文档

### JSON 报告

JSON 报告适合：
- 🔧 程序化处理和自动化分析
- 📊 数据导入到其他工具
- 🔄 API 集成和数据交换

## 📊 功能特性

### 1. 测试时长统计

- 自动计算测试开始时间、结束时间和持续时间
- 支持多种时长格式显示（秒、分钟、小时）

### 2. HTTP 请求总体统计

- **总请求数**：压测期间发送的总请求数
- **成功请求数**：状态码为 200 的请求数
- **失败请求数**：状态码非 200 的请求数
- **错误率**：失败请求数 / 总请求数

### 3. 响应时间分析

- **平均响应时间**：所有请求的平均响应时间
- **最小/最大响应时间**：响应时间的极值
- **百分位数**：P50、P75、P90、P95、P99 响应时间

### 4. 按端点统计

- 每个接口的详细性能指标
- 状态码分布统计
- 按请求数排序，快速识别热点接口

### 5. 关键指标统计

- HTTP 请求数
- 迭代次数
- 虚拟用户数（VUs）
- 数据传输量（发送/接收）

### 6. 阈值检查

自动检查性能阈值是否达标：
- P50 < 500ms
- P95 < 1500ms
- P99 < 2000ms
- Max < 3000ms
- 错误率 < 1%

## 📝 使用示例

### 完整工作流程

```bash
# 1. 运行 k6 压测并导出 JSON 报告
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

# 3. 查看报告
# 在浏览器中打开 HTML 报告
open tests/performance/http/results/k6_report.html

# 或查看 Markdown 报告
cat tests/performance/http/results/k6_report.md

# 或查看 JSON 报告
cat tests/performance/http/results/k6_analysis_report.json | jq
```

### 报告预览

#### HTML 报告特点

HTML 报告采用现代化设计，包含：

- **渐变头部**：紫色渐变背景，突出报告标题
- **统计卡片**：网格布局展示关键指标，不同颜色表示不同状态
  - 🟢 绿色：成功/正常指标
  - 🔴 红色：失败/异常指标
  - 🟡 黄色：警告指标
- **数据表格**：清晰的表格展示端点性能数据，支持悬停高亮
- **响应式设计**：适配桌面和移动设备
- **阈值检查**：直观的通过/失败状态显示

#### Markdown 报告特点

Markdown 报告包含：

- **清晰的表格**：易于阅读的数据表格
- **状态图标**：✅ 和 ❌ 直观显示检查结果
- **代码格式**：端点名称使用代码格式突出显示
- **结构化内容**：使用标题和分隔线组织内容

#### 控制台输出示例

```
================================================================================
k6 压测报告分析
================================================================================

分析时间: 2025-12-06 17:13:24
报告文件: tests/performance/http/results/k6_results.json
数据点总数: 198864
指标数量: 16

--------------------------------------------------------------------------------
测试时长
--------------------------------------------------------------------------------
  开始时间: 2025-12-05T14:29:17.609491+08:00
  结束时间: 2025-12-05T14:33:18.184746+08:00
  持续时间: 4.0 分钟

--------------------------------------------------------------------------------
HTTP 请求总体统计
--------------------------------------------------------------------------------
  总请求数: 12,399
  成功请求: 12,399
  失败请求: 0
  错误率: 0.00%

  响应时间统计:
    平均: 456.30 ms
    最小: 40.63 ms
    最大: 3096.21 ms
    P50:  335.62 ms
    P95:  1260.51 ms
    P99:  2029.64 ms

--------------------------------------------------------------------------------
按端点统计 (Top 10)
--------------------------------------------------------------------------------

1. query_available_hosts
   总请求数: 12,399
   成功请求: 12,399
   失败请求: 0
   错误率: 0.00%
   响应时间:
     平均: 456.30 ms
     P95:  1260.51 ms
     P99:  2029.64 ms
   状态码分布: 200: 12399

--------------------------------------------------------------------------------
阈值检查结果
--------------------------------------------------------------------------------
  P50 < 500ms: ✅ 通过
  P95 < 1500ms: ✅ 通过
  P99 < 2000ms: ❌ 失败
  Max < 3000ms: ❌ 失败
  错误率 < 1%: ✅ 通过
```

## 🔧 命令行参数

| 参数 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `json_file` | k6 JSON 报告文件路径 | 是 | - |
| `-n, --top-n` | 显示 Top N 端点 | 否 | 10 |
| `-o, --output` | 输出 JSON 报告文件路径 | 否 | - |
| `--html` | 生成 HTML 格式报告（指定输出文件路径） | 否 | - |
| `--markdown` | 生成 Markdown 格式报告（指定输出文件路径） | 否 | - |

## 📚 相关文档

- [k6 压测脚本使用指南](../../tests/performance/http/README.md)
- [完整压测方案文档](../../docs/34-api-load-testing-plan.md)
- [慢查询分析工具](../../scripts/analyze_slow_queries.py)

## 🐛 故障排查

### 问题1: 文件不存在

**错误信息**: `FileNotFoundError: 报告文件不存在`

**解决方案**: 检查文件路径是否正确，确保 k6 已成功导出 JSON 报告

### 问题2: JSON 格式错误

**错误信息**: `json.JSONDecodeError`

**解决方案**: 确保 k6 报告文件格式正确，使用 `k6 run script.js --out json=results.json` 导出

### 问题3: 模块导入错误

**错误信息**: `ModuleNotFoundError: No module named 'shared'`

**解决方案**: 确保从项目根目录运行脚本，或检查 Python 路径配置

---

**最后更新**: 2025-12-06

