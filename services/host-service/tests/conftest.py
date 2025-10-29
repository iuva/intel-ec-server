"""
Pytest 配置文件 - WebSocket 测试通用配置
"""

import asyncio
import os

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（会话级别）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def ws_url():
    """WebSocket 连接 URL - 使用网关转发"""
    # 如果要使用网关，请改为: "ws://localhost:8000/ws/host"
    # 如果要直接连接 host-service，使用: "ws://localhost:8003"
    return os.getenv("WEBSOCKET_URL", "ws://localhost:8003")


@pytest.fixture
def sample_agent_id():
    """示例 Agent ID"""
    return "agent-001"


@pytest.fixture
def sample_agent_ids():
    """多个示例 Agent IDs"""
    return [f"agent-{i:03d}" for i in range(5)]


@pytest.fixture
def ws_timeout():
    """WebSocket 连接超时时间（秒）"""
    return 10.0


@pytest.fixture
def message_timeout():
    """消息接收超时时间（秒）"""
    return 5.0
