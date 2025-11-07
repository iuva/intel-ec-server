# WebSocket 测试完整指南

## 📚 概述

这是 Intel EC Host Service 的 WebSocket 接口完整测试框架。包含 **35+ 个测试用例**，覆盖连接、消息、并发和性能等全方位场景。

## 📂 文件结构

```text
services/host-service/tests/
├── __init__.py                      # 测试包初始化
├── conftest.py                      # pytest 配置和 fixtures
├── test_websocket_connection.py    # 连接测试 (7个用例)
├── test_websocket_messages.py      # 消息处理测试 (8个用例)
├── test_websocket_concurrent.py    # 并发测试 (7个用例)
├── test_websocket_performance.py   # 性能测试 (6个用例)
└── fixtures/
    └── __init__.py                  # fixtures 包初始化
```

## 🧪 测试用例总览

### 1️⃣ 连接测试 (test_websocket_connection.py) - 7 个用例

| 测试名称 | 功能 | 验证内容 |
|---------|-----|--------|
| `test_successful_connection` | ✅ 成功连接 | 连接建立、状态正确 |
| `test_connection_with_invalid_agent_id` | ⚠️ 无效 Agent ID | 错误处理、连接反应 |
| `test_connection_close_handling` | 🔌 关闭处理 | 正常关闭、无法重复操作 |
| `test_abnormal_disconnection` | 💥 异常断开 | 异常恢复、重连能力 |
| `test_multiple_connections_same_agent` | 🔀 多连接 | 同 Agent 多连接管理 |
| `test_connection_timeout` | ⏱️ 超时处理 | 超时不断开、活动性 |
| `test_rapid_connect_disconnect` | ⚡ 快速操作 | 快速连接/断开循环 |

**代码行数**: 185 行 | **覆盖范围**: 连接生命周期

### 2️⃣ 消息测试 (test_websocket_messages.py) - 8 个用例

| 测试名称 | 功能 | 验证内容 |
|---------|-----|--------|
| `test_send_receive_message` | 📤 发送/接收 | 消息格式、连接保活 |
| `test_invalid_json_message` | ❌ 无效 JSON | 错误容错、连接复原 |
| `test_message_type_validation` | 🔍 类型验证 | 未知类型处理 |
| `test_large_message_handling` | 📦 大消息处理 | 1MB 消息、完整性 |
| `test_rapid_message_sequence` | 🚀 快速序列 | 100 条/次、顺序保证 |
| `test_empty_message` | 🔳 空消息 | 空字符串处理 |
| `test_message_with_special_characters` | 🌍 特殊字符 | Unicode、转义符 |
| `test_nested_json_message` | 🎁 嵌套 JSON | 复杂结构支持 |

**代码行数**: 213 行 | **覆盖范围**: 消息完整性和格式

### 3️⃣ 并发测试 (test_websocket_concurrent.py) - 7 个用例

| 测试名称 | 功能 | 验证内容 |
|---------|-----|--------|
| `test_multiple_agents_connection` | 👥 多 Agent 连接 | 10 个并发连接 |
| `test_concurrent_messages` | 📨 并发消息 | 50 条并发发送 |
| `test_connection_under_load` | 🔥 负载测试 | 50 连接、各 10 消息 |
| `test_concurrent_disconnect` | 🔌 并发断开 | 10 连接同时关闭 |
| `test_interleaved_operations` | 🔄 交错操作 | 多连接交错消息 |
| `test_concurrent_connect_disconnect_cycle` | 🔁 周期循环 | 3 个周期、5 连接/次 |
| `test_high_frequency_messages` | ⚡ 高频消息 | 500 条/连接 |
| `test_mixed_message_sizes` | 📏 混合大小 | 各种大小消息交错 |

**代码行数**: 286 行 | **覆盖范围**: 并发和负载

### 4️⃣ 性能测试 (test_websocket_performance.py) - 6 个用例

| 测试名称 | 功能 | 性能指标 |
|---------|-----|--------|
| `test_message_throughput` | 📊 吞吐量 | > 100 msg/sec |
| `test_connection_establishment_time` | ⏱️ 连接建立 | < 1s 平均 |
| `test_memory_usage` | 💾 内存使用 | < 200 MB 增长 |
| `test_message_latency` | 📍 消息延迟 | < 50ms 平均 |
| `test_sustained_performance` | 📈 持续性能 | 无 > 20% 衰退 |
| `test_concurrent_performance` | 🚀 并发吞吐 | > 100 msg/sec 总计 |

**代码行数**: 266 行 | **覆盖范围**: 性能基准

## 📊 统计数据

```text
总代码行数:  1,006 行
测试用例数:    35+ 个
Fixtures:       5 个
覆盖场景:    连接 / 消息 / 并发 / 性能 / 负载
```

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
# 在项目根目录
pip install websockets pytest-asyncio pytest-cov psutil

# 或从 requirements.txt
pip install -r requirements.txt
```

### 2️⃣ 启动 Host Service

```bash
cd /Users/chiyeming/KiroProjects/intel_ec_ms
docker-compose up -d host-service

# 检查服务状态
docker-compose logs -f host-service | grep "WebSocket"
```

### 3️⃣ 运行测试

#### 全部测试

```bash
# 从项目根目录
pytest services/host-service/tests/ -v

# 显示详细输出
pytest services/host-service/tests/ -vv --tb=short

# 显示打印语句
pytest services/host-service/tests/ -v -s
```

#### 单个模块

```bash
# 连接测试
pytest services/host-service/tests/test_websocket_connection.py -v

# 消息测试
pytest services/host-service/tests/test_websocket_messages.py -v

# 并发测试
pytest services/host-service/tests/test_websocket_concurrent.py -v

# 性能测试
pytest services/host-service/tests/test_websocket_performance.py -v
```

#### 单个测试用例

```bash
# 运行特定测试
pytest services/host-service/tests/test_websocket_connection.py::TestWebSocketConnection::test_successful_connection -v

# 运行包含特定关键字的测试
pytest services/host-service/tests/ -k "connection" -v

# 运行不包含特定关键字的测试
pytest services/host-service/tests/ -k "not performance" -v
```

## 📈 生成报告

### 覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest services/host-service/tests/ \
  --cov=services/host-service/app \
  --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 性能报告

```bash
# 显示最慢的 10 个测试
pytest services/host-service/tests/ --durations=10

# 显示所有测试耗时
pytest services/host-service/tests/ --durations=0
```

## 🔧 常用命令速查

| 需求 | 命令 |
|-----|------|
| 运行所有测试 | `pytest services/host-service/tests/ -v` |
| 运行连接测试 | `pytest services/host-service/tests/test_websocket_connection.py -v` |
| 运行消息测试 | `pytest services/host-service/tests/test_websocket_messages.py -v` |
| 运行并发测试 | `pytest services/host-service/tests/test_websocket_concurrent.py -v` |
| 运行性能测试 | `pytest services/host-service/tests/test_websocket_performance.py -v` |
| 显示打印输出 | `pytest services/host-service/tests/ -v -s` |
| 显示性能 | `pytest services/host-service/tests/ --durations=10` |
| 生成覆盖率 | `pytest services/host-service/tests/ --cov=services/host-service/app --cov-report=html` |
| 运行失败的测试 | `pytest services/host-service/tests/ --lf` |
| 关键字过滤 | `pytest services/host-service/tests/ -k "connection" -v` |
| 进入调试器 | `pytest services/host-service/tests/ --pdb` |

## ⚠️ 故障排查

### 问题 1: WebSocket 连接超时

```text
错误: asyncio.TimeoutError: Timeout waiting for WebSocket connection
```

**解决方案**:

```bash
# 1. 检查 host-service 是否运行
docker-compose ps | grep host-service

# 2. 检查日志
docker-compose logs host-service

# 3. 重启服务
docker-compose restart host-service
```

### 问题 2: 导入错误 (ImportError)

```text
错误: ModuleNotFoundError: No module named 'websockets'
```

**解决方案**:

```bash
# 安装缺失的依赖
pip install websockets pytest-asyncio
```

### 问题 3: 测试超时

```text
错误: asyncio.TimeoutError: wait_for if hung
```

**解决方案**:

```bash
# 增加超时时间（在 conftest.py 中修改）
# 或运行单个测试：
pytest services/host-service/tests/test_websocket_connection.py::TestWebSocketConnection::test_connection_timeout --timeout=60
```

### 问题 4: 性能测试失败

```text
错误: AssertionError: 吞吐量应该 > 100 msg/sec
```

**原因**: 系统负载高

**解决方案**:

```bash
# 1. 检查系统资源
top -l 1 | head -20

# 2. 减少其他运行的服务
docker-compose stop gateway-service auth-service admin-service

# 3. 重新运行测试
pytest services/host-service/tests/test_websocket_performance.py -v
```

## 💡 最佳实践

### 1️⃣ 测试隔离

- 每个测试应该独立运行
- 不依赖其他测试的结果
- 自动清理资源

```python
# ✅ 好
async with websockets.connect(uri) as ws:
    # 测试逻辑
    ***REMOVED***  # 自动关闭

# ❌ 不好
ws = await websockets.connect(uri)
# 如果测试失败，连接不会关闭
```

### 2️⃣ 清晰的断言消息

```python
# ✅ 好
assert websocket.open, f"连接应该打开，实际状态: {websocket.state}"

# ❌ 不好
assert websocket.open
```

### 3️⃣ 适当的超时

```python
# ✅ 好
async with websockets.connect(uri, ping_interval=None) as ws:
    message = await asyncio.wait_for(ws.recv(), timeout=5.0)

# ❌ 不好
message = await ws.recv()  # 可能无限等待
```

---

**最后更新**: 2025-10-25  
**维护者**: Intel EC 团队

