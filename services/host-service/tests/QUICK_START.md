# 🚀 WebSocket 测试快速参考

## 📋 5 分钟快速开始

### 1️⃣ 安装 (1 分钟)
```bash
pip install websockets pytest-asyncio pytest-cov psutil
```

### 2️⃣ 启动服务 (1 分钟)
```bash
cd /Users/chiyeming/KiroProjects/intel_ec_ms
docker-compose up -d host-service
```

### 3️⃣ 运行测试 (1-3 分钟)

**最简单** - 运行所有测试:
```bash
pytest services/host-service/tests/ -v
```

**特定模块**:
```bash
pytest services/host-service/tests/test_websocket_connection.py -v
```

**单个测试**:
```bash
pytest services/host-service/tests/test_websocket_connection.py::TestWebSocketConnection::test_successful_connection -v
```

## 📚 常用命令速查

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

## 🧪 测试用例快速查找

### 连接相关
- `test_successful_connection` - 基础连接
- `test_multiple_connections_same_agent` - 多连接
- `test_connection_timeout` - 超时处理
- `test_rapid_connect_disconnect` - 快速操作

### 消息相关
- `test_send_receive_message` - 基础消息
- `test_large_message_handling` - 大消息 (1MB)
- `test_rapid_message_sequence` - 快速序列 (100条)
- `test_special_characters` - 特殊字符和 Unicode

### 并发相关
- `test_multiple_agents_connection` - 多 Agent 连接 (10个)
- `test_connection_under_load` - 负载测试 (50连接)
- `test_concurrent_messages` - 并发消息 (50条)
- `test_high_frequency_messages` - 高频消息 (500条)

### 性能相关
- `test_message_throughput` - 吞吐量 (>100 msg/sec)
- `test_connection_establishment_time` - 连接建立 (<1s)
- `test_message_latency` - 延迟 (<50ms)
- `test_memory_usage` - 内存 (<200MB增长)

## 🎯 典型场景

### 场景 A: 快速验证基础功能
```bash
# 1. 检查连接
pytest services/host-service/tests/test_websocket_connection.py::TestWebSocketConnection::test_successful_connection -v

# 2. 检查消息
pytest services/host-service/tests/test_websocket_messages.py::TestWebSocketMessages::test_send_receive_message -v

# 总时间: ~5 秒
```

### 场景 B: 全面功能测试
```bash
# 运行连接和消息测试
pytest services/host-service/tests/test_websocket_connection.py services/host-service/tests/test_websocket_messages.py -v

# 总时间: ~15 秒
```

### 场景 C: 完整集成测试
```bash
# 运行所有测试
pytest services/host-service/tests/ -v

# 总时间: ~2-3 分钟
```

### 场景 D: 性能基准测试
```bash
# 关闭其他服务，运行性能测试
docker-compose stop gateway-service auth-service admin-service
pytest services/host-service/tests/test_websocket_performance.py -v -s

# 总时间: ~30 秒
```

## 🔧 快速修复

### 问题: 连接超时
```bash
# 检查服务
docker-compose ps | grep host-service

# 查看日志
docker-compose logs host-service

# 重启
docker-compose restart host-service
```

### 问题: ImportError
```bash
# 安装缺失的包
pip install websockets pytest-asyncio psutil
```

### 问题: 性能测试失败
```bash
# 关闭其他服务
docker-compose stop gateway-service auth-service admin-service

# 重新运行
pytest services/host-service/tests/test_websocket_performance.py -v
```

## 📊 测试统计

```
总用例数: 35+
- 连接测试: 7 个
- 消息测试: 8 个  
- 并发测试: 7 个
- 性能测试: 6 个

总代码: 1,006 行
平均耗时: 2-3 分钟
```

## 🎓 文档链接

- **完整文档**: `README.md` - 详细的测试框架说明
- **配置文件**: `conftest.py` - pytest fixtures 定义
- **连接测试**: `test_websocket_connection.py`
- **消息测试**: `test_websocket_messages.py`
- **并发测试**: `test_websocket_concurrent.py`
- **性能测试**: `test_websocket_performance.py`

## 💡 提示

- 使用 `-v` 显示详细输出
- 使用 `-s` 显示打印语句
- 使用 `-k` 按关键字过滤
- 使用 `--lf` 运行失败的测试
- 使用 `--pdb` 进入调试器

---

**快速参考完成！祝测试顺利！** 🎉
