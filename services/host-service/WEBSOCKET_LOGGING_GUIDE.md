# WebSocket 消息日志指南

## 📊 日志概览

WebSocket Manager 现在会记录所有消息的详细内容，便于调试和追踪通讯过程。

## 📥 接收消息日志

### 日志格式
```json
{
  "level": "INFO",
  "message": "📥 接收消息",
  "extra": {
    "agent_id": "host-001",
    "message_type": "heartbeat",
    "message_content": {
      "type": "heartbeat",
      "timestamp": "2025-10-28T10:00:00Z"
    },
    "timestamp": "2025-10-28T10:00:00.123456Z"
  }
}
```

### 日志示例

#### 心跳消息
```
2025-10-28 10:00:00.123 | INFO | 📥 接收消息 | agent_id=host-001 | message_type=heartbeat | message_content={'type': 'heartbeat', 'timestamp': '2025-10-28T10:00:00Z'}
```

#### 状态更新消息
```
2025-10-28 10:01:00.456 | INFO | 📥 接收消息 | agent_id=host-001 | message_type=status_update | message_content={'type': 'status_update', 'status': 'running', 'cpu': 45.2, 'memory': 60.5}
```

#### 命令响应消息
```
2025-10-28 10:02:00.789 | INFO | 📥 接收消息 | agent_id=host-001 | message_type=command_response | message_content={'type': 'command_response', 'command_id': 'cmd-123', 'success': true, 'result': {'output': 'Success'}}
```

## 📤 发送消息日志

### 日志格式
```json
{
  "level": "INFO",
  "message": "📤 发送消息",
  "extra": {
    "host_id": "host-001",
    "message_type": "command",
    "message_content": {
      "type": "command",
      "command_id": "cmd-123",
      "command": "restart",
      "args": {"service": "nginx"}
    },
    "timestamp": "2025-10-28T10:03:00.123456Z"
  }
}
```

### 日志示例

#### 发送命令消息
```
2025-10-28 10:03:00.123 | INFO | 📤 发送消息 | host_id=host-001 | message_type=command | message_content={'type': 'command', 'command_id': 'cmd-123', 'command': 'restart', 'args': {'service': 'nginx'}}
```

#### 发送心跳确认
```
2025-10-28 10:04:00.456 | INFO | 📤 发送消息 | host_id=host-001 | message_type=heartbeat_ack | message_content={'type': 'heartbeat_ack', 'message': '心跳已接收', 'timestamp': '2025-10-28T10:04:00Z'}
```

#### 发送错误消息
```
2025-10-28 10:05:00.789 | INFO | 📤 发送消息 | host_id=host-001 | message_type=error | message_content={'type': 'error', 'message': '未知消息类型: invalid_type', 'timestamp': '2025-10-28T10:05:00Z'}
```

## 📢 广播消息日志

### 开始广播日志
```json
{
  "level": "INFO",
  "message": "📢 开始广播消息",
  "extra": {
    "message_type": "notification",
    "message_content": {
      "type": "notification",
      "title": "系统维护通知",
      "message": "系统将在30分钟后进行维护"
    },
    "target_count": 10,
    "exclude_host": null,
    "timestamp": "2025-10-28T10:06:00.123456Z"
  }
}
```

### 广播完成日志
```json
{
  "level": "INFO",
  "message": "✅ 广播完成: 成功 8/10",
  "extra": {
    "message_type": "notification",
    "success_count": 8,
    "failed_count": 2
  }
}
```

### 日志示例
```
2025-10-28 10:06:00.123 | INFO | 📢 开始广播消息 | message_type=notification | target_count=10 | message_content={'type': 'notification', 'title': '系统维护通知', 'message': '系统将在30分钟后进行维护'}

2025-10-28 10:06:00.456 | INFO | 📤 发送消息 | host_id=host-001 | message_type=notification | ...
2025-10-28 10:06:00.457 | INFO | 📤 发送消息 | host_id=host-002 | message_type=notification | ...
...
2025-10-28 10:06:00.789 | WARNING | 广播失败的Host: ['host-007', 'host-009']

2025-10-28 10:06:00.800 | INFO | ✅ 广播完成: 成功 8/10 | success_count=8 | failed_count=2
```

## ❌ 错误日志

### 发送失败日志
```json
{
  "level": "ERROR",
  "message": "❌ 发送消息失败",
  "extra": {
    "host_id": "host-005",
    "message_type": "command",
    "error": "WebSocket connection closed"
  }
}
```

### 日志示例
```
2025-10-28 10:07:00.123 | ERROR | ❌ 发送消息失败 | host_id=host-005 | message_type=command | error=WebSocket connection closed
```

## 🔍 日志过滤和查询

### 查看特定Host的消息
```bash
# 查看host-001的所有消息
docker-compose logs host-service | grep "host-001"

# 查看host-001接收的消息
docker-compose logs host-service | grep "📥 接收消息" | grep "host-001"

# 查看host-001发送的消息
docker-compose logs host-service | grep "📤 发送消息" | grep "host-001"
```

### 查看特定消息类型
```bash
# 查看所有心跳消息
docker-compose logs host-service | grep "message_type=heartbeat"

# 查看所有命令消息
docker-compose logs host-service | grep "message_type=command"

# 查看所有广播消息
docker-compose logs host-service | grep "📢 开始广播消息"
```

### 查看错误消息
```bash
# 查看所有发送失败
docker-compose logs host-service | grep "❌ 发送消息失败"

# 查看所有ERROR级别日志
docker-compose logs host-service | grep "ERROR"
```

### 实时监控
```bash
# 实时监控WebSocket消息
docker-compose logs -f host-service | grep -E "(📥|📤|📢)"

# 实时监控特定Host
docker-compose logs -f host-service | grep "host-001"
```

## 📊 日志分析示例

### 完整的消息流转示例

```
# 1. 客户端连接
2025-10-28 10:00:00.000 | INFO | WebSocket 连接已建立 | agent_id=host-001 | total_connections=1

# 2. 服务器发送欢迎消息
2025-10-28 10:00:00.100 | INFO | 📤 发送消息 | host_id=host-001 | message_type=welcome | message_content={'type': 'welcome', 'agent_id': 'host-001', 'message': 'WebSocket 连接已建立'}

# 3. 客户端发送心跳
2025-10-28 10:00:30.000 | INFO | 📥 接收消息 | agent_id=host-001 | message_type=heartbeat | message_content={'type': 'heartbeat', 'timestamp': '2025-10-28T10:00:30Z'}

# 4. 服务器回复心跳确认
2025-10-28 10:00:30.100 | INFO | 📤 发送消息 | host_id=host-001 | message_type=heartbeat_ack | message_content={'type': 'heartbeat_ack', 'message': '心跳已接收'}

# 5. 客户端发送状态更新
2025-10-28 10:01:00.000 | INFO | 📥 接收消息 | agent_id=host-001 | message_type=status_update | message_content={'type': 'status_update', 'status': 'running', 'cpu': 45.2}

# 6. 服务器广播通知
2025-10-28 10:02:00.000 | INFO | 📢 开始广播消息 | message_type=notification | target_count=5
2025-10-28 10:02:00.100 | INFO | 📤 发送消息 | host_id=host-001 | message_type=notification | ...
2025-10-28 10:02:00.500 | INFO | ✅ 广播完成: 成功 5/5

# 7. 客户端断开连接
2025-10-28 10:10:00.000 | INFO | WebSocket 正常断开: host-001
2025-10-28 10:10:00.100 | INFO | WebSocket 连接已断开 | agent_id=host-001 | total_connections=0
```

## 🛠️ 调试技巧

### 1. 追踪特定消息的完整流程
```bash
# 追踪命令cmd-123的完整流程
docker-compose logs host-service | grep "cmd-123"
```

### 2. 统计消息类型分布
```bash
# 统计各类消息数量
docker-compose logs host-service | grep "message_type=" | awk -F'message_type=' '{print $2}' | awk '{print $1}' | sort | uniq -c
```

### 3. 监控消息失败率
```bash
# 查看最近的失败消息
docker-compose logs host-service --tail=100 | grep "❌"

# 统计失败次数
docker-compose logs host-service | grep -c "❌ 发送消息失败"
```

### 4. 性能分析
```bash
# 查看高频消息（可能影响性能）
docker-compose logs host-service --since 1h | grep -E "(📥|📤)" | wc -l

# 每分钟消息量
docker-compose logs host-service --since 1h | grep -E "(📥|📤)" | head -60
```

## 📝 日志配置

### 日志级别调整

如果日志太多，可以在 `shared/common/loguru_config.py` 中调整日志级别：

```python
# 调整为WARNING级别（只记录警告和错误）
logger.add(
    sys.stdout,
    level="WARNING",  # 改为WARNING
    format=log_format,
)
```

### 日志文件配置

如果需要将日志保存到文件：

```python
# 添加文件日志
logger.add(
    "logs/websocket_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
)
```

## 🎯 最佳实践

1. **开发环境**: 使用 `INFO` 级别，记录所有消息详情
2. **生产环境**: 考虑使用 `WARNING` 级别，只记录异常情况
3. **调试问题**: 临时启用 `DEBUG` 级别，获取更详细的信息
4. **性能监控**: 定期分析日志，识别高频消息和性能瓶颈
5. **日志归档**: 定期清理旧日志，避免磁盘空间不足

---

**最后更新**: 2025-10-28
**相关文件**: 
- `services/host-service/app/services/websocket_manager.py`
- `shared/common/loguru_config.py`

