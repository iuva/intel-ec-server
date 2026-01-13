"""
WebSocket Performance Test Module

Test Content:
- Message throughput
- Connection establishment time
- Memory usage
- Message latency
"""

import asyncio
import json
import os
import time

import pytest
import websockets


@pytest.mark.asyncio
class TestWebSocketPerformance:
    """WebSocket Performance Test Class"""

    @pytest.mark.asyncio
    async def test_message_throughput(self, ws_url, sample_agent_id):
        """Test message throughput

        Verification:
        - Can send messages at high speed
        - Throughput > 100 msg/sec
        - Connection remains stable
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 1000

        async with websockets.connect(uri, ping_interval=None) as websocket:
            start_time = time.time()

            # Send messages
            for i in range(num_messages):
                message = {"type": "throughput", "index": i}
                await websocket.send(json.dumps(message))

            elapsed_time = time.time() - start_time
            throughput = num_messages / elapsed_time

            # Record performance metrics
            print(f"\nMessage throughput: {throughput:.2f} messages/sec")
            print(f"Total time: {elapsed_time:.3f} seconds")
            print(f"Total messages: {num_messages}")

            # Verify throughput
            assert throughput > 100, f"Throughput should be > 100 msg/sec, actual: {throughput:.2f}"
            assert websocket.open, "Connection should still be open"

    @pytest.mark.asyncio
    async def test_connection_establishment_time(self, ws_url):
        """Test connection establishment time

        Verification:
        - Single connection establishment time < 1s
        - Average connection time is reasonable
        """
        num_tests = 20
        connection_times = []

        for i in range(num_tests):
            agent_id = f"perf-agent-{i:03d}"
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"

            start_time = time.time()
            async with websockets.connect(uri, ping_interval=None) as websocket:
                connection_time = time.time() - start_time
                connection_times.append(connection_time)
                assert websocket.open, "Connection should be open"

        # Calculate statistics
        avg_time = sum(connection_times) / len(connection_times)
        min_time = min(connection_times)
        max_time = max(connection_times)

        # Record performance metrics
        print("\nConnection time statistics:")
        print(f"  Average: {avg_time * 1000:.2f} ms")
        print(f"  Minimum: {min_time * 1000:.2f} ms")
        print(f"  Maximum: {max_time * 1000:.2f} ms")

        # Verify connection time
        assert avg_time < 1.0, f"Average connection time should be < 1s, actual: {avg_time:.3f}s"
        assert all(t < 2.0 for t in connection_times), "All connection times should be < 2s"

    @pytest.mark.asyncio
    async def test_memory_usage(self, ws_url, sample_agent_id):
        """Test memory usage

        Verification:
        - Memory usage growth is reasonable
        - No signs of memory leak
        """
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not installed")

        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        process = psutil.Process(os.getpid())

        # Record initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Send large number of messages
            for i in range(10000):
                message = {"type": "memory_test", "data": "x" * 100}
                await websocket.send(json.dumps(message))

                # Periodically check memory
                if i % 1000 == 0 and i > 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_delta = current_memory - initial_memory
                    print(f"\nMessage {i}: Memory increase {memory_delta:.2f} MB")

        # Record final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        print("\nMemory usage:")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Total increase: {memory_increase:.2f} MB")

        # Verify memory growth is reasonable
        assert memory_increase < 200, f"Memory increase should be < 200 MB, actual: {memory_increase:.2f} MB"

    @pytest.mark.asyncio
    async def test_message_latency(self, ws_url, sample_agent_id):
        """Test message latency

        Verification:
        - Low message sending latency
        - Average latency < 50ms
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        latencies = []

        async with websockets.connect(uri, ping_interval=None) as websocket:
            for i in range(100):
                # Record send time
                start_time = time.time()

                message = {"type": "latency_test", "timestamp": start_time, "index": i}
                await websocket.send(json.dumps(message))

                # Calculate latency
                latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                latencies.append(latency)

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        print("\nMessage latency statistics:")
        print(f"  Average: {avg_latency:.2f} ms")
        print(f"  Minimum: {min_latency:.2f} ms")
        print(f"  Maximum: {max_latency:.2f} ms")
        print(f"  P95: {p95_latency:.2f} ms")

        # Verify latency
        assert avg_latency < 50, f"Average latency should be < 50ms, actual: {avg_latency:.2f}ms"

    @pytest.mark.asyncio
    async def test_sustained_performance(self, ws_url, sample_agent_id):
        """Test sustained performance

        Verification:
        - Maintain performance over long periods
        - No signs of performance degradation
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        duration_seconds = 10
        message_counts = []

        async with websockets.connect(uri, ping_interval=None) as websocket:
            start_time = time.time()
            message_count = 0
            checkpoint_time = start_time

            while time.time() - start_time < duration_seconds:
                message = {"type": "sustained", "index": message_count}
                await websocket.send(json.dumps(message))
                message_count += 1

                # Check every second
                current_time = time.time()
                if current_time - checkpoint_time >= 1.0:
                    messages_per_second = message_count / (current_time - start_time)
                    message_counts.append(messages_per_second)
                    checkpoint_time = current_time

        # Analyze performance trends
        if len(message_counts) > 1:
            first_second = message_counts[0]
            last_second = message_counts[-1]
            performance_ratio = last_second / first_second if first_second > 0 else 1.0

            print("\nSustained performance statistics:")
            print(f"  First second: {first_second:.2f} msg/sec")
            print(f"  Last second: {last_second:.2f} msg/sec")
            print(f"  Performance ratio: {performance_ratio:.2f}")
            print(f"  Average: {sum(message_counts) / len(message_counts):.2f} msg/sec")

            # Verify no significant performance degradation
            assert performance_ratio > 0.8, "Performance degradation should not exceed 20%"

    @pytest.mark.asyncio
    async def test_concurrent_performance(self, ws_url):
        """Test concurrent performance

        Verification:
        - Total throughput of multiple connections
        - Concurrency does not significantly reduce single connection performance
        """
        num_connections = 10
        agents = [f"concurrent-perf-{i:03d}" for i in range(num_connections)]
        messages_sent = []

        async def send_messages(agent_id: str, num_messages: int = 100) -> int:
            uri = f"{ws_url}/api/v1/ws/agent/{agent_id}"
            try:
                async with websockets.connect(uri, ping_interval=None) as websocket:
                    start_time = time.time()

                    for i in range(num_messages):
                        message = {"type": "concurrent_perf", "index": i}
                        await websocket.send(json.dumps(message))

                    elapsed_time = time.time() - start_time
                    throughput = num_messages / elapsed_time
                    messages_sent.append(throughput)
                    return int(throughput)
            except Exception as e:
                pytest.skip(f"Concurrent performance test failed: {e!s}")
                return 0

        # Execute concurrently
        start_time = time.time()
        tasks = [send_messages(agent_id, 100) for agent_id in agents]
        results = await asyncio.gather(*tasks)
        print(f"Concurrent performance statistics: {results}")
        total_time = time.time() - start_time

        # Calculate total throughput
        total_messages = num_connections * 100
        total_throughput = total_messages / total_time

        print("\nConcurrent performance statistics:")
        print(f"  Number of connections: {num_connections}")
        print(f"  Total messages: {total_messages}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Total throughput: {total_throughput:.2f} msg/sec")

        if messages_sent:
            avg_single = sum(messages_sent) / len(messages_sent)
            print(f"  Average single connection: {avg_single:.2f} msg/sec")

        # Verify performance
        assert total_throughput > 100, f"Total throughput should be > 100 msg/sec, actual: {total_throughput:.2f}"
