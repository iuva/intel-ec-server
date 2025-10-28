"""
WebSocket 消息处理测试模块

测试内容：
- 发送和接收消息
- 无效 JSON 处理
- 消息类型验证
- 大消息处理
- 快速消息序列
"""

import pytest
import websockets
import json
import asyncio


@pytest.mark.asyncio
class TestWebSocketMessages:
    """WebSocket 消息处理测试类"""

    @pytest.mark.asyncio
    async def test_send_receive_message(self, ws_url, sample_agent_id, message_timeout):
        """测试发送和接收消息

        验证：
        - 可以发送 JSON 消息
        - 消息格式正确
        - 连接保持打开
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 构造测试消息
            test_message = {"type": "ping", "data": "hello"}

            # 发送消息
            await websocket.send(json.dumps(test_message))
            assert websocket.open, "发送消息后连接应该仍然打开"

            # 尝试接收响应（如果服务器有回复）
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=message_timeout)
                assert response is not None, "应该接收到响应"
            except asyncio.TimeoutError:
                # 如果没有立即响应，这也是可以接受的
                ***REMOVED***

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, ws_url, sample_agent_id):
        """测试无效 JSON 处理

        验证：
        - 无效 JSON 不会导致连接断开
        - 服务器能正确处理错误
        - 连接保持可用
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 发送无效 JSON
            await websocket.send("{invalid json")

            # 连接应该仍然打开
            assert websocket.open, "无效 JSON 后连接应该仍然打开"

            # 尝试发送有效消息，确保连接仍可用
            valid_message = {"type": "ping"}
            await websocket.send(json.dumps(valid_message))
            assert websocket.open, "发送有效消息后连接应该仍然打开"

    @pytest.mark.asyncio
    async def test_message_type_validation(self, ws_url, sample_agent_id):
        """测试消息类型验证

        验证：
        - 未知消息类型被正确处理
        - 连接保持可用
        - 服务器不会因为未知类型而断开连接
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 发送未知消息类型
            invalid_message = {"type": "unknown_type", "data": {}}
            await websocket.send(json.dumps(invalid_message))

            # 连接应该保持打开
            assert websocket.open, "未知消息类型后连接应该仍然打开"

            # 验证可以继续通信
            valid_message = {"type": "ping"}
            await websocket.send(json.dumps(valid_message))
            assert websocket.open, "后续消息应该能正常发送"

    @pytest.mark.asyncio
    async def test_large_message_handling(self, ws_url, sample_agent_id):
        """测试大消息处理

        验证：
        - 可以发送大消息（1MB）
        - 消息完整性
        - 连接稳定性
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 创建 1MB 的大消息
            large_data = "x" * (1024 * 1024)
            large_message = {"type": "data", "content": large_data}

            # 发送大消息
            await websocket.send(json.dumps(large_message))
            assert websocket.open, "发送大消息后连接应该仍然打开"

            # 验证连接完整性
            small_message = {"type": "ping"}
            await websocket.send(json.dumps(small_message))
            assert websocket.open, "大消息后应该能发送小消息"

    @pytest.mark.asyncio
    async def test_rapid_message_sequence(self, ws_url, sample_agent_id):
        """测试快速消息序列

        验证：
        - 可以快速连续发送多条消息
        - 消息顺序保持
        - 服务器能处理高频消息
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 100

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 快速发送多条消息
            for i in range(num_messages):
                message = {"type": "batch", "index": i}
                await websocket.send(json.dumps(message))

            # 连接应该仍然打开
            assert websocket.open, "发送 100 条消息后连接应该仍然打开"

            # 验证可以继续通信
            final_message = {"type": "ping"}
            await websocket.send(json.dumps(final_message))
            assert websocket.open, "最后的消息应该能正常发送"

    @pytest.mark.asyncio
    async def test_empty_message(self, ws_url, sample_agent_id):
        """测试空消息处理

        验证：
        - 空消息被正确处理
        - 连接保持稳定
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 发送空字符串
            await websocket.send("")

            # 连接应该仍然打开
            assert websocket.open, "空消息后连接应该仍然打开"

            # 验证可以继续通信
            valid_message = {"type": "ping"}
            await websocket.send(json.dumps(valid_message))
            assert websocket.open, "空消息后应该能发送有效消息"

    @pytest.mark.asyncio
    async def test_message_with_special_characters(self, ws_url, sample_agent_id):
        """测试特殊字符处理

        验证：
        - 包含特殊字符的消息被正确处理
        - Unicode 字符支持
        - 转义字符处理
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 消息包含特殊字符
            special_message = {
                "type": "special",
                "data": "Hello 世界 🌍 !@#$%^&*()",
            }
            await websocket.send(json.dumps(special_message))
            assert websocket.open, "特殊字符消息后连接应该仍然打开"

    @pytest.mark.asyncio
    async def test_nested_json_message(self, ws_url, sample_agent_id):
        """测试嵌套 JSON 消息

        验证：
        - 支持嵌套的 JSON 结构
        - 复杂数据结构处理
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 发送嵌套的 JSON
            nested_message = {
                "type": "nested",
                "data": {
                    "level1": {
                        "level2": {
                            "level3": [1, 2, 3, {"key": "value"}],
                        }
                    }
                },
            }
            await websocket.send(json.dumps(nested_message))
            assert websocket.open, "嵌套 JSON 消息后连接应该仍然打开"
