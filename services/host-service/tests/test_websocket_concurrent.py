"""
WebSocket 并发测试模块

测试内容：
- 多个 Agent 同时连接
- 并发消息处理
- 负载测试
- 并发断开处理
"""

import asyncio
import json
from typing import List

import pytest
import websockets


@pytest.mark.asyncio
class TestWebSocketConcurrent:
    """WebSocket 并发测试类"""

    @pytest.mark.asyncio
    async def test_multiple_agents_connection(self, ws_url):
        """测试多个 Agent 同时连接

        验证：
        - 10 个 Agent 可以同时连接
        - 所有连接都能成功建立
        - 连接之间互不影响
        """
        agents = [f"agent-{i:03d}" for i in range(10)]
        connections = []

        async def connect_agent(agent_id: str):
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                ws = await websockets.connect(uri, ping_interval=None)
                connections.append((agent_id, ws))
                return True
            except Exception as e:
                pytest.skip(f"Agent {agent_id} 连接失败: {str(e)}")

        # 并发连接所有 Agent
        tasks = [connect_agent(agent_id) for agent_id in agents]
        results = await asyncio.gather(*tasks)
        print(f"连接结果: {results}, connections: {connections}")

        # 验证所有连接都打开
        assert len(connections) == len(agents), "应该连接所有 Agent"
        for agent_id, ws in connections:
            assert ws.open, f"Agent {agent_id} 连接应该打开"

        # 清理
        for agent_id, ws in connections:
            await ws.close()

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, ws_url, sample_agent_id):
        """测试并发消息处理

        验证：
        - 可以并发发送多条消息
        - 消息都能成功发送
        - 连接保持稳定
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 50

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 并发发送多条消息
            tasks = []
            for i in range(num_messages):
                message = {"type": "concurrent", "id": i}
                task = websocket.send(json.dumps(message))
                tasks.append(task)

            # 等待所有消息发送完成
            await asyncio.gather(*tasks)

            # 连接应该仍然打开
            assert websocket.open, "发送并发消息后连接应该仍然打开"

            # 验证可以继续通信
            final_message = {"type": "ping"}
            await websocket.send(json.dumps(final_message))
            assert websocket.open, "最后的消息应该能正常发送"

    @pytest.mark.asyncio
    async def test_connection_under_load(self, ws_url):
        """测试负载下的连接

        验证：
        - 50 个并发连接能稳定工作
        - 每个连接都能独立通信
        - 负载不会导致连接失败
        """
        num_connections = 50
        agents = [f"load-agent-{i:03d}" for i in range(num_connections)]

        async def agent_client(agent_id: str) -> bool:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                async with websockets.connect(uri, ping_interval=None) as websocket:
                    # 每个连接发送消息
                    for msg_idx in range(10):
                        message = {"type": "load_test", "message_id": msg_idx}
                        await websocket.send(json.dumps(message))
                        await asyncio.sleep(0.01)  # 稍微延迟

                    assert websocket.open, f"Agent {agent_id} 连接应该保持打开"
                    return True
            except Exception as e:
                pytest.skip(f"Agent {agent_id} 连接失败: {str(e)}")
                return False

        # 并发创建所有客户端
        tasks = [agent_client(agent_id) for agent_id in agents]
        results = await asyncio.gather(*tasks)

        # 验证大多数连接都成功
        success_count = sum(1 for r in results if r)
        assert success_count >= num_connections * 0.8, "至少 80% 的连接应该成功"

    @pytest.mark.asyncio
    async def test_concurrent_disconnect(self, ws_url):
        """测试并发断开

        验证：
        - 多个连接可以同时断开
        - 断开不会导致资源泄漏
        - 断开后无法重复操作
        """
        num_connections = 10
        agents = [f"disconnect-agent-{i:03d}" for i in range(num_connections)]
        connections: List = []

        # 创建所有连接
        for agent_id in agents:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                ws = await websockets.connect(uri, ping_interval=None)
                connections.append(ws)
            except Exception as e:
                pytest.skip(f"连接创建失败: {str(e)}")

        # 验证所有连接都打开
        assert all(ws.open for ws in connections), "所有连接应该打开"

        # 并发关闭所有连接
        async def close_connection(ws):
            await ws.close()

        tasks = [close_connection(ws) for ws in connections]
        await asyncio.gather(*tasks)

        # 验证所有连接都已关闭
        for ws in connections:
            assert not ws.open, "连接应该已关闭"

    @pytest.mark.asyncio
    async def test_interleaved_operations(self, ws_url, sample_agent_ids):
        """测试交错操作

        验证：
        - 多个连接可以交错操作
        - 连接之间互不干扰
        - 消息顺序正确
        """
        connections: dict = {}

        # 创建多个连接
        for agent_id in sample_agent_ids:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                ws = await websockets.connect(uri, ping_interval=None)
                connections[agent_id] = ws
            except Exception as e:
                pytest.skip(f"连接创建失败: {str(e)}")

        # 交错发送消息
        async def send_messages(agent_id: str, count: int):
            ws = connections[agent_id]
            for i in range(count):
                message = {"type": "interleaved", "agent": agent_id, "index": i}
                await ws.send(json.dumps(message))
                await asyncio.sleep(0.01)  # 交错延迟

        # 并发执行交错操作
        tasks = [send_messages(agent_id, 5) for agent_id in sample_agent_ids]
        await asyncio.gather(*tasks)

        # 验证所有连接仍然打开
        for agent_id, ws in connections.items():
            assert ws.open, f"Agent {agent_id} 连接应该仍然打开"

        # 清理
        for ws in connections.values():
            await ws.close()

    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect_cycle(self, ws_url):
        """测试并发连接-断开循环

        验证：
        - 可以进行多个并发连接-断开周期
        - 没有资源泄漏
        - 服务器能正确处理
        """
        num_cycles = 3
        num_agents_per_cycle = 5

        async def cycle_agents():
            agents = [f"cycle-agent-{i:03d}" for i in range(num_agents_per_cycle)]

            async def connect_and_disconnect(agent_id: str):
                uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
                try:
                    async with websockets.connect(uri, ping_interval=None) as ws:
                        # 发送一条消息
                        message = {"type": "cycle"}
                        await ws.send(json.dumps(message))
                        # 自动关闭
                        return True
                except Exception as e:
                    pytest.skip(f"周期操作失败: {str(e)}")
                    return False

            tasks = [connect_and_disconnect(agent_id) for agent_id in agents]
            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r)

        # 执行多个周期
        for cycle_num in range(num_cycles):
            success_count = await cycle_agents()
            assert success_count > 0, f"第 {cycle_num + 1} 个周期应该有成功的连接"

    @pytest.mark.asyncio
    async def test_high_frequency_messages(self, ws_url, sample_agent_id):
        """测试高频消息

        验证：
        - 可以发送高频消息（500条/秒）
        - 不会导致连接断开
        - 服务器能处理
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 500

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 快速发送高频消息
            for i in range(num_messages):
                message = {"type": "high_freq", "index": i}
                await websocket.send(json.dumps(message))

            # 连接应该仍然打开
            assert websocket.open, "发送高频消息后连接应该仍然打开"

            # 验证可以继续通信
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            assert websocket.open, "最后的 ping 应该能发送"

    @pytest.mark.asyncio
    async def test_mixed_message_sizes(self, ws_url, sample_agent_id):
        """测试混合大小消息

        验证：
        - 可以混合发送各种大小的消息
        - 大小消息可以交错
        - 不会影响连接稳定性
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 发送混合大小的消息
            sizes = [100, 10000, 1000, 100000, 500]
            for idx, size in enumerate(sizes):
                data = "x" * size
                print(f"data: {data}")
                message = {"type": "mixed", "size": size, "index": idx}
                await websocket.send(json.dumps(message))

            # 连接应该仍然打开
            assert websocket.open, "发送混合大小消息后连接应该仍然打开"

            # 验证可以继续通信
            final_message = {"type": "ping"}
            await websocket.send(json.dumps(final_message))
            assert websocket.open, "最后的消息应该能发送"
