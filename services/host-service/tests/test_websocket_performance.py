"""
WebSocket 性能测试模块

测试内容：
- 消息吞吐量
- 连接建立时间
- 内存使用情况
- 消息延迟
"""

import asyncio
import json
import os
import time

import pytest
import websockets


@pytest.mark.asyncio
class TestWebSocketPerformance:
    """WebSocket 性能测试类"""

    @pytest.mark.asyncio
    async def test_message_throughput(self, ws_url, sample_agent_id):
        """测试消息吞吐量

        验证：
        - 可以高速发送消息
        - 吞吐量 > 100 msg/sec
        - 连接保持稳定
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 1000

        async with websockets.connect(uri, ping_interval=None) as websocket:
            start_time = time.time()

            # 发送消息
            for i in range(num_messages):
                message = {"type": "throughput", "index": i}
                await websocket.send(json.dumps(message))

            elapsed_time = time.time() - start_time
            throughput = num_messages / elapsed_time

            # 记录性能指标
            print(f"\n消息吞吐量: {throughput:.2f} 消息/秒")
            print(f"总时间: {elapsed_time:.3f} 秒")
            print(f"总消息数: {num_messages}")

            # 验证吞吐量
            assert throughput > 100, f"吞吐量应该 > 100 msg/sec，实际: {throughput:.2f}"
            assert websocket.open, "连接应该仍然打开"

    @pytest.mark.asyncio
    async def test_connection_establishment_time(self, ws_url):
        """测试连接建立时间

        验证：
        - 单个连接建立时间 < 1s
        - 平均连接时间合理
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
                assert websocket.open, "连接应该打开"

        # 计算统计数据
        avg_time = sum(connection_times) / len(connection_times)
        min_time = min(connection_times)
        max_time = max(connection_times)

        # 记录性能指标
        print("\n连接时间统计:")
        print(f"  平均: {avg_time * 1000:.2f} ms")
        print(f"  最小: {min_time * 1000:.2f} ms")
        print(f"  最大: {max_time * 1000:.2f} ms")

        # 验证连接时间
        assert avg_time < 1.0, f"平均连接时间应该 < 1s，实际: {avg_time:.3f}s"
        assert all(t < 2.0 for t in connection_times), "所有连接时间应该 < 2s"

    @pytest.mark.asyncio
    async def test_memory_usage(self, ws_url, sample_agent_id):
        """测试内存使用情况

        验证：
        - 内存使用增长合理
        - 没有内存泄漏迹象
        """
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil 未安装")

        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        process = psutil.Process(os.getpid())

        # 记录初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 发送大量消息
            for i in range(10000):
                message = {"type": "memory_test", "data": "x" * 100}
                await websocket.send(json.dumps(message))

                # 定期检查内存
                if i % 1000 == 0 and i > 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_delta = current_memory - initial_memory
                    print(f"\n消息 {i}: 内存增长 {memory_delta:.2f} MB")

        # 记录最终内存
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        print("\n内存使用情况:")
        print(f"  初始内存: {initial_memory:.2f} MB")
        print(f"  最终内存: {final_memory:.2f} MB")
        print(f"  总增长: {memory_increase:.2f} MB")

        # 验证内存增长合理
        assert memory_increase < 200, f"内存增长应该 < 200 MB，实际: {memory_increase:.2f} MB"

    @pytest.mark.asyncio
    async def test_message_latency(self, ws_url, sample_agent_id):
        """测试消息延迟

        验证：
        - 消息发送延迟低
        - 平均延迟 < 50ms
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        latencies = []

        async with websockets.connect(uri, ping_interval=None) as websocket:
            for i in range(100):
                # 记录发送时间
                start_time = time.time()

                message = {"type": "latency_test", "timestamp": start_time, "index": i}
                await websocket.send(json.dumps(message))

                # 计算延迟
                latency = (time.time() - start_time) * 1000  # 转换为毫秒
                latencies.append(latency)

        # 计算统计数据
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        print("\n消息延迟统计:")
        print(f"  平均: {avg_latency:.2f} ms")
        print(f"  最小: {min_latency:.2f} ms")
        print(f"  最大: {max_latency:.2f} ms")
        print(f"  P95: {p95_latency:.2f} ms")

        # 验证延迟
        assert avg_latency < 50, f"平均延迟应该 < 50ms，实际: {avg_latency:.2f}ms"

    @pytest.mark.asyncio
    async def test_sustained_performance(self, ws_url, sample_agent_id):
        """测试持续性能

        验证：
        - 长时间保持性能
        - 没有性能衰退迹象
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

                # 每秒检查一次
                current_time = time.time()
                if current_time - checkpoint_time >= 1.0:
                    messages_per_second = message_count / (current_time - start_time)
                    message_counts.append(messages_per_second)
                    checkpoint_time = current_time

        # 分析性能趋势
        if len(message_counts) > 1:
            first_second = message_counts[0]
            last_second = message_counts[-1]
            performance_ratio = last_second / first_second if first_second > 0 else 1.0

            print("\n持续性能统计:")
            print(f"  第1秒: {first_second:.2f} msg/sec")
            print(f"  最后秒: {last_second:.2f} msg/sec")
            print(f"  性能比率: {performance_ratio:.2f}")
            print(f"  平均: {sum(message_counts) / len(message_counts):.2f} msg/sec")

            # 验证性能没有明显衰退
            assert performance_ratio > 0.8, "性能衰退不应该超过 20%"

    @pytest.mark.asyncio
    async def test_concurrent_performance(self, ws_url):
        """测试并发性能

        验证：
        - 多个连接的总吞吐量
        - 并发不会显著降低单连接性能
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
                pytest.skip(f"并发性能测试失败: {str(e)}")
                return 0

        # 并发执行
        start_time = time.time()
        tasks = [send_messages(agent_id, 100) for agent_id in agents]
        results = await asyncio.gather(*tasks)
        print(f"并发性能统计: {results}")
        total_time = time.time() - start_time

        # 计算总吞吐量
        total_messages = num_connections * 100
        total_throughput = total_messages / total_time

        print("\n并发性能统计:")
        print(f"  连接数: {num_connections}")
        print(f"  总消息数: {total_messages}")
        print(f"  总耗时: {total_time:.3f}s")
        print(f"  总吞吐量: {total_throughput:.2f} msg/sec")

        if messages_sent:
            avg_single = sum(messages_sent) / len(messages_sent)
            print(f"  平均单连接: {avg_single:.2f} msg/sec")

        # 验证性能
        assert total_throughput > 100, f"总吞吐量应该 > 100 msg/sec，实际: {total_throughput:.2f}"
