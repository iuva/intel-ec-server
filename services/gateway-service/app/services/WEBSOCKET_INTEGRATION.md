# WebSocket 高级特性集成指南

## 🎯 完整集成示例

### 1. 在 WebSocket 端点集成所有高级特性

```python
# services/host-service/app/api/v1/endpoints/websocket.py
"""
WebSocket 端点集成示例 - 包含所有高级特性
"""

import os
import sys
from typing import Dict, Any

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
    )
    from shared.common.loguru_config import get_logger

from fastapi import WebSocket, WebSocketDisconnect
from app.services.websocket_features import (
    WebSocketFeaturesManager,
    HeartbeatManager,
    RateLimiter,
    MessageCompressor,
)

logger = get_logger(__name__)

# 初始化高级特性管理器
features_manager = WebSocketFeaturesManager(
    heartbeat_interval=30.0,      # 30秒心跳间隔
    heartbeat_timeout=10.0,       # 10秒超时
    max_messages=100,             # 60秒内最多100条消息
    window_size=60.0,             # 60秒时间窗口
    max_message_size=1024 * 1024, # 1MB最大消息
    compression_threshold=1024,   # 1KB以上压缩
)


async def websocket_agent_endpoint(websocket: WebSocket, agent_id: str):
    """Agent WebSocket 连接端点 - 集成所有高级特性

    Args:
        websocket: WebSocket 连接
        agent_id: Agent ID
    """
    await websocket.accept()

    try:
        # 1. 注册心跳检测
        async def send_heartbeat():
            """发送心跳消息"""
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
            })

        features_manager.heartbeat_manager.register_connection(agent_id, send_heartbeat)

        logger.info(f"Agent 已连接: {agent_id}")

        # 2. 消息处理循环
        while True:
            # 接收消息
            raw_message = await websocket.receive_text()

            # 2.1 检查速率限制
            can_proceed, error_msg = await features_manager.rate_limiter.check_rate_limit(
                agent_id, len(raw_message.encode("utf-8"))
            )

            if not can_proceed:
                logger.warning(f"速率限制: {agent_id} - {error_msg}")
                await websocket.send_json({
                    "type": "error",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": error_msg,
                })
                continue

            # 2.2 解压消息
            message_text = await features_manager.compressor.decompress_message(raw_message)

            if not message_text:
                logger.warning(f"消息解压失败: {agent_id}")
                await websocket.send_json({
                    "type": "error",
                    "code": "DECOMPRESSION_FAILED",
                    "message": "消息解压失败",
                })
                continue

            # 2.3 处理业务逻辑
            logger.info(f"收到消息: {agent_id} - {message_text[:100]}")

            # 模拟业务处理
            response = {
                "type": "message",
                "data": f"Echo: {message_text}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 2.4 压缩响应
            import json
            response_text = json.dumps(response)
            is_compressed, compressed_response = await features_manager.compressor.compress_message(
                response_text
            )

            # 2.5 发送响应
            if is_compressed:
                await websocket.send_text(compressed_response)
            else:
                await websocket.send_text(response_text)

    except WebSocketDisconnect:
        logger.info(f"Agent 已断开连接: {agent_id}")
    except Exception as e:
        logger.error(f"WebSocket 异常: {agent_id} - {str(e)}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })
    finally:
        # 清理资源
        features_manager.heartbeat_manager.unregister_connection(agent_id)
        features_manager.rate_limiter.cleanup_connection(agent_id)

        logger.info(f"Agent 资源已清理: {agent_id}")


# 健康检查端点 - 返回特性管理器统计
async def websocket_stats():
    """获取 WebSocket 统计信息"""
    return {
        "features": features_manager.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

### 2. 在路由中注册端点

```python
# services/host-service/app/api/v1/endpoints/__init__.py
from fastapi import APIRouter
from app.api.v1.endpoints.websocket import websocket_agent_endpoint, websocket_stats

router = APIRouter()

# WebSocket 端点
router.websocket_route("/ws/agent/{agent_id}")(websocket_agent_endpoint)

# 统计信息端点
router.get("/websocket/stats")(websocket_stats)
```

## 📊 监控和统计

### 1. 获取实时统计

```python
# 获取所有功能的统计信息
stats = features_manager.get_stats()

# 输出示例
{
    "heartbeat": {
        "active_connections": 15
    },
    "rate_limiter": {
        "tracked_connections": 15
    },
    "compressor": {
        "total_messages": 1500,
        "compressed_count": 1200,
        "uncompressed_count": 300,
        "compression_rate": 80.0,
        "compression_ratio": 0.45,
        "bytes_original": 5000000,
        "bytes_compressed": 2250000,
        "bytes_saved": 2750000
    }
}
```

### 2. 单个连接的统计

```python
# 心跳统计
heartbeat_stats = features_manager.heartbeat_manager.get_stats(agent_id)
# {
#     "total_heartbeats": 100,
#     "successful_heartbeats": 98,
#     "failed_heartbeats": 2,
#     "success_rate": 0.98,
#     "average_response_time_ms": 15.5,
#     "last_heartbeat_time": "2025-10-24T10:00:00Z"
# }

# 速率限制统计
rate_stats = features_manager.rate_limiter.get_stats(agent_id)
# {
#     "message_count": 45,
#     "max_messages": 100,
#     "percentage": 45.0,
#     "total_bytes": 250000,
#     "max_size_bytes": 1048576
# }
```

## 🧪 测试用例

### 1. 心跳检测测试

```python
# tests/test_websocket_heartbeat.py
import pytest
from services.gateway_service.app.services.websocket_features import HeartbeatManager
import asyncio

@pytest.mark.asyncio
async def test_heartbeat_registration():
    """测试心跳注册"""
    manager = HeartbeatManager(interval=1.0, timeout=5.0)

    # 模拟发送心跳
    heartbeat_count = 0

    async def mock_send_heartbeat():
        nonlocal heartbeat_count
        heartbeat_count += 1

    # 注册连接
    manager.register_connection("test-agent", mock_send_heartbeat)

    # 等待几个心跳周期
    await asyncio.sleep(2.5)

    # 验证心跳已发送
    assert heartbeat_count >= 2, f"期望至少2次心跳，实际{heartbeat_count}"

    # 验证统计信息
    stats = manager.get_stats("test-agent")
    assert stats is not None
    assert stats["total_heartbeats"] >= 2

    # 清理
    manager.unregister_connection("test-agent")
```

### 2. 速率限制测试

```python
# tests/test_websocket_rate_limit.py
import pytest
from services.gateway_service.app.services.websocket_features import RateLimiter

@pytest.mark.asyncio
async def test_rate_limit():
    """测试速率限制"""
    limiter = RateLimiter(max_messages=5, window_size=60.0, max_size_bytes=1024)

    # 正常消息应该通过
    for i in range(5):
        can_proceed, error = await limiter.check_rate_limit("test-agent", 100)
        assert can_proceed, f"消息 {i} 应该通过限制"

    # 超过限制的消息应该被拒绝
    can_proceed, error = await limiter.check_rate_limit("test-agent", 100)
    assert not can_proceed, "第6条消息应该被拒绝"
    assert "频率" in error, f"错误消息应包含'频率'，实际: {error}"

    # 超大消息应该被拒绝
    can_proceed, error = await limiter.check_rate_limit("test-agent-2", 2048)
    assert not can_proceed, "超大消息应该被拒绝"
    assert "大小" in error, f"错误消息应包含'大小'，实际: {error}"

    # 清理
    limiter.cleanup_connection("test-agent")
    limiter.cleanup_connection("test-agent-2")
```

### 3. 消息压缩测试

```python
# tests/test_websocket_compression.py
import pytest
import json
from services.gateway_service.app.services.websocket_features import MessageCompressor

@pytest.mark.asyncio
async def test_message_compression():
    """测试消息压缩"""
    compressor = MessageCompressor(compression_threshold=100)

    # 小消息不压缩
    small_msg = "Hello, World!"
    is_compressed, result = await compressor.compress_message(small_msg)
    assert not is_compressed, "小消息应不压缩"
    assert result == small_msg, "小消息应原样返回"

    # 大消息应压缩
    large_msg = "x" * 1000
    is_compressed, result = await compressor.compress_message(large_msg)
    assert is_compressed, "大消息应压缩"
    
    # 验证可以解压
    decompressed = await compressor.decompress_message(result)
    assert decompressed == large_msg, "解压后应与原消息相同"

    # 验证统计
    stats = compressor.get_stats()
    assert stats["total_messages"] == 2
    assert stats["compressed_count"] == 1
    assert stats["compression_ratio"] < 1.0, "压缩比应小于1"
```

## 🚀 性能优化建议

### 1. 心跳配置优化

```python
# 开发环境：频繁心跳便于测试
dev_config = {
    "heartbeat_interval": 10.0,
    "heartbeat_timeout": 5.0,
}

# 生产环境：降低心跳频率以减少流量
prod_config = {
    "heartbeat_interval": 60.0,      # 60秒
    "heartbeat_timeout": 30.0,       # 30秒
}
```

### 2. 速率限制配置优化

```python
# 宽松限制（测试/开发）
loose_config = {
    "max_messages": 1000,           # 1000条/60秒
    "window_size": 60.0,
    "max_message_size": 10 * 1024 * 1024,  # 10MB
}

# 严格限制（生产）
strict_config = {
    "max_messages": 100,            # 100条/60秒
    "window_size": 60.0,
    "max_message_size": 1024 * 1024,  # 1MB
}
```

### 3. 压缩配置优化

```python
# 低压缩阈值：更多消息被压缩（高CPU占用）
aggressive_config = {
    "compression_threshold": 256,   # 256字节以上压缩
}

# 高压缩阈值：减少压缩（低CPU占用）
conservative_config = {
    "compression_threshold": 10 * 1024,  # 10KB以上压缩
}
```

## 📈 监控指标导出

### 1. Prometheus 指标集成

```python
from prometheus_client import Counter, Gauge, Histogram

# WebSocket 连接指标
websocket_connections = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
    ["service"]
)

# 消息指标
websocket_messages = Counter(
    "websocket_messages_total",
    "Total WebSocket messages processed",
    ["service", "type"]
)

# 压缩指标
websocket_compression = Gauge(
    "websocket_compression_ratio",
    "WebSocket compression ratio",
    ["service"]
)

# 心跳指标
websocket_heartbeats = Counter(
    "websocket_heartbeats_total",
    "Total WebSocket heartbeats",
    ["service", "status"]
)

# 速率限制指标
websocket_rate_limit_exceeded = Counter(
    "websocket_rate_limit_exceeded_total",
    "WebSocket rate limit exceeded count",
    ["service"]
)
```

### 2. Grafana 仪表板查询

```promql
# 活跃连接数
count(websocket_connections_active{service="host-service"})

# 消息处理速率
rate(websocket_messages_total{service="host-service"}[5m])

# 压缩效率
avg(websocket_compression_ratio{service="host-service"})

# 心跳成功率
rate(websocket_heartbeats_total{service="host-service",status="success"}[5m]) 
/ 
rate(websocket_heartbeats_total{service="host-service"}[5m])

# 速率限制触发率
rate(websocket_rate_limit_exceeded_total{service="host-service"}[5m])
```

## 🔍 故障排查

### 1. 心跳失败

**症状**: 连接经常断开

**诊断**:
```python
# 检查心跳统计
stats = features_manager.heartbeat_manager.get_stats(agent_id)
success_rate = stats["successful_heartbeats"] / stats["total_heartbeats"]

if success_rate < 0.95:
    logger.warning(f"心跳成功率低: {success_rate:.2%}")
```

**解决**:
- 增加心跳间隔
- 检查网络连接
- 增加心跳超时时间

### 2. 消息被拒绝

**症状**: 收到速率限制错误

**诊断**:
```python
stats = features_manager.rate_limiter.get_stats(agent_id)
if stats["percentage"] > 90:
    logger.warning(f"接近限制: {stats['percentage']:.1f}%")
```

**解决**:
- 减少消息发送频率
- 增加时间窗口大小
- 合并多条消息为一条

### 3. 压缩失效

**症状**: 压缩率低于预期

**诊断**:
```python
stats = features_manager.compressor.get_stats()
logger.info(f"压缩率: {stats['compression_rate']:.1f}%")
logger.info(f"压缩比: {stats['compression_ratio']:.2f}")
```

**解决**:
- 降低压缩阈值
- 检查消息内容是否重复
- 使用更高效的消息编码

## 📋 最佳实践检查清单

- [ ] 所有 WebSocket 端点都集成了心跳检测
- [ ] 速率限制已根据业务需求配置
- [ ] 消息压缩已启用并监控效率
- [ ] 所有统计信息已集成到监控系统
- [ ] 性能测试已完成
- [ ] 故障恢复机制已实现
- [ ] 日志记录已完整

## 🎉 总结

WebSocket 高级特性包括：

✅ **心跳检测** - 自动检测死连接
✅ **速率限制** - 防止洪泛攻击
✅ **消息压缩** - 减少带宽占用
✅ **性能监控** - 完整的统计指标
✅ **故障恢复** - 自动清理和恢复

所有特性都已完成实现和集成！ 🚀
