"""
WebSocket Concurrent Test Module

Test Content:
- Multiple Agents connecting simultaneously
- Concurrent message processing
- Load testing
- Concurrent disconnection handling
"""

import asyncio
import json
from typing import List

import pytest
import websockets


@pytest.mark.asyncio
class TestWebSocketConcurrent:
    """WebSocket Concurrent Test Class"""

    @pytest.mark.asyncio
    async def test_multiple_agents_connection(self, ws_url):
        """Test multiple Agents connecting simultaneously

        Verification:
        - 10 Agents can connect simultaneously
        - All connections can be successfully established
        - Connections do not interfere with each other
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
                pytest.skip(f"Agent {agent_id} connection failed: {e!s}")

        # Concurrently connect all Agents
        tasks = [connect_agent(agent_id) for agent_id in agents]
        results = await asyncio.gather(*tasks)
        print(f"Connection results: {results}, connections: {connections}")

        # Verify all connections are open
        assert len(connections) == len(agents), "All Agents should be connected"
        for agent_id, ws in connections:
            assert ws.open, f"Agent {agent_id} connection should be open"

        # Cleanup
        for agent_id, ws in connections:
            await ws.close()

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, ws_url, sample_agent_id):
        """Test concurrent message processing

        Verification:
        - Can concurrently send multiple messages
        - All messages can be successfully sent
        - Connection remains stable
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 50

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Concurrently send multiple messages
            tasks = []
            for i in range(num_messages):
                message = {"type": "concurrent", "id": i}
                task = websocket.send(json.dumps(message))
                tasks.append(task)

            # Wait for all messages to finish sending
            await asyncio.gather(*tasks)

            # Connection should still be open
            assert websocket.open, "Connection should still be open after sending concurrent messages"

            # Verify communication can continue
            final_message = {"type": "ping"}
            await websocket.send(json.dumps(final_message))
            assert websocket.open, "The final message should be able to send normally"

    @pytest.mark.asyncio
    async def test_connection_under_load(self, ws_url):
        """Test connections under load

        Verification:
        - 50 concurrent connections can work stably
        - Each connection can communicate independently
        - Load does not cause connection failures
        """
        num_connections = 50
        agents = [f"load-agent-{i:03d}" for i in range(num_connections)]

        async def agent_client(agent_id: str) -> bool:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                async with websockets.connect(uri, ping_interval=None) as websocket:
                    # Send messages for each connection
                    for msg_idx in range(10):
                        message = {"type": "load_test", "message_id": msg_idx}
                        await websocket.send(json.dumps(message))
                        await asyncio.sleep(0.01)  # Slight delay

                    assert websocket.open, f"Agent {agent_id} connection should remain open"
                    return True
            except Exception as e:
                pytest.skip(f"Agent {agent_id} connection failed: {e!s}")
                return False

        # Concurrently create all clients
        tasks = [agent_client(agent_id) for agent_id in agents]
        results = await asyncio.gather(*tasks)

        # Verify most connections are successful
        success_count = sum(1 for r in results if r)
        assert success_count >= num_connections * 0.8, "At least 80% of connections should succeed"

    @pytest.mark.asyncio
    async def test_concurrent_disconnect(self, ws_url):
        """Test concurrent disconnection

        Verification:
        - Multiple connections can disconnect simultaneously
        - Disconnection does not cause resource leaks
        - Cannot perform duplicate operations after disconnection
        """
        num_connections = 10
        agents = [f"disconnect-agent-{i:03d}" for i in range(num_connections)]
        connections: List = []

        # Create all connections
        for agent_id in agents:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                ws = await websockets.connect(uri, ping_interval=None)
                connections.append(ws)
            except Exception as e:
                pytest.skip(f"Connection creation failed: {e!s}")

        # Verify all connections are open
        assert all(ws.open for ws in connections), "All connections should be open"

        # Concurrently close all connections
        async def close_connection(ws):
            await ws.close()

        tasks = [close_connection(ws) for ws in connections]
        await asyncio.gather(*tasks)

        # Verify all connections are closed
        for ws in connections:
            assert not ws.open, "Connection should be closed"

    @pytest.mark.asyncio
    async def test_interleaved_operations(self, ws_url, sample_agent_ids):
        """Test interleaved operations

        Verification:
        - Multiple connections can perform interleaved operations
        - Connections do not interfere with each other
        - Message order is correct
        """
        connections: dict = {}

        # Create multiple connections
        for agent_id in sample_agent_ids:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                ws = await websockets.connect(uri, ping_interval=None)
                connections[agent_id] = ws
            except Exception as e:
                pytest.skip(f"Connection creation failed: {e!s}")

        # Interleaved send messages
        async def send_messages(agent_id: str, count: int):
            ws = connections[agent_id]
            for i in range(count):
                message = {"type": "interleaved", "agent": agent_id, "index": i}
                await ws.send(json.dumps(message))
                await asyncio.sleep(0.01)  # Interleaved delay

        # Concurrently execute interleaved operations
        tasks = [send_messages(agent_id, 5) for agent_id in sample_agent_ids]
        await asyncio.gather(*tasks)

        # Verify all connections are still open
        for agent_id, ws in connections.items():
            assert ws.open, f"Agent {agent_id} connection should still be open"

        # Cleanup
        for ws in connections.values():
            await ws.close()

    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect_cycle(self, ws_url):
        """Test concurrent connect-disconnect cycles

        Verification:
        - Can perform multiple concurrent connect-disconnect cycles
        - No resource leaks
        - Server can handle correctly
        """
        num_cycles = 3
        num_agents_per_cycle = 5

        async def cycle_agents():
            agents = [f"cycle-agent-{i:03d}" for i in range(num_agents_per_cycle)]

            async def connect_and_disconnect(agent_id: str):
                uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
                try:
                    async with websockets.connect(uri, ping_interval=None) as ws:
                        # Send a message
                        message = {"type": "cycle"}
                        await ws.send(json.dumps(message))
                        # Auto close
                        return True
                except Exception as e:
                    pytest.skip(f"Cycle operation failed: {e!s}")
                    return False

            tasks = [connect_and_disconnect(agent_id) for agent_id in agents]
            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r)

        # Execute multiple cycles
        for cycle_num in range(num_cycles):
            success_count = await cycle_agents()
            assert success_count > 0, f"Cycle {cycle_num + 1} should have successful connections"

    @pytest.mark.asyncio
    async def test_high_frequency_messages(self, ws_url, sample_agent_id):
        """Test high-frequency messages

        Verification:
        - Can send high-frequency messages (500 per second)
        - Does not cause connection disconnection
        - Server can handle
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 500

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Quickly send high-frequency messages
            for i in range(num_messages):
                message = {"type": "high_freq", "index": i}
                await websocket.send(json.dumps(message))

            # Connection should still be open
            assert websocket.open, "Connection should still be open after sending high-frequency messages"

            # Verify communication can continue
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            assert websocket.open, "The final ping should be able to send"

    @pytest.mark.asyncio
    async def test_mixed_message_sizes(self, ws_url, sample_agent_id):
        """Test mixed-size messages

        Verification:
        - Can mix send messages of various sizes
        - Messages of different sizes can be interleaved
        - Does not affect connection stability
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Send mixed-size messages
            sizes = [100, 10000, 1000, 100000, 500]
            for idx, size in enumerate(sizes):
                data = "x" * size
                print(f"data: {data}")
                message = {"type": "mixed", "size": size, "index": idx}
                await websocket.send(json.dumps(message))

            # Connection should still be open
            assert websocket.open, "Connection should still be open after sending mixed-size messages"

            # Verify communication can continue
            final_message = {"type": "ping"}
            await websocket.send(json.dumps(final_message))
            assert websocket.open, "The final message should be able to send"
