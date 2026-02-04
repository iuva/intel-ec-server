"""
Pytest Configuration File - WebSocket Test Common Configuration
"""

import asyncio
import os

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop (session level)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def ws_url():
    """WebSocket connection URL - Using gateway forwarding"""
    # To use gateway, change to: "ws://localhost:8000/ws/host"
    # To connect directly to host-service, use: "ws://localhost:8003"
    return os.getenv("WEBSOCKET_URL", "ws://localhost:8003")


@pytest.fixture
def sample_agent_id():
    """Sample Agent ID"""
    return "agent-001"


@pytest.fixture
def sample_agent_ids():
    """Multiple Sample Agent IDs"""
    return [f"agent-{i:03d}" for i in range(5)]


@pytest.fixture
def ws_timeout():
    """WebSocket connection timeout (seconds)"""
    return 10.0


@pytest.fixture
def message_timeout():
    """Message reception timeout (seconds)"""
    return 5.0
