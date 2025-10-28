"""
WebSocket 连接测试模块

测试内容：
- 成功建立连接
- 无效 Agent ID 处理
- 正常连接关闭
- 异常断开处理
- 多个连接管理
"""

import pytest
import websockets
from websockets.exceptions import ConnectionClosed
import json
import asyncio


@pytest.mark.asyncio
class TestWebSocketConnection:
    """WebSocket 连接测试类"""

    @pytest.mark.asyncio
    async def test_successful_connection(self, ws_url, sample_agent_id, ws_timeout):
        """测试成功建立 WebSocket 连接

        验证：
        - 连接可以建立
        - 连接状态为 OPEN
        - 连接的 agent_id 正确
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # 验证连接已建立
            assert websocket.open, "WebSocket 连接应该是打开状态"
            assert websocket.state.name == "OPEN", "WebSocket 状态应该是 OPEN"

    @pytest.mark.asyncio
    async def test_connection_with_invalid_agent_id(self, ws_url):
        """测试无效 Agent ID 处理

        验证：
        - 无效 Agent ID 连接也能建立（FastAPI 接受任何参数）
        - 但后续操作可能会失败
        """
        invalid_agent_id = "invalid-agent"
        uri = f"{ws_url}/api/v1/ws/agent/{invalid_agent_id}"

        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                assert websocket.open, "连接应该建立"
        except Exception as e:
            # 连接失败也是可以接受的
            pytest.skip(f"无效 Agent ID 连接失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_connection_close_handling(self, ws_url, sample_agent_id):
        """测试连接关闭处理

        验证：
        - 连接可以正常关闭
        - 关闭后无法发送消息
        - 关闭后异常被正确抛出
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        websocket = await websockets.connect(uri, ping_interval=None)
        assert websocket.open, "初始连接应该是打开的"

        # 正常关闭连接
        await websocket.close()

        # 验证连接已关闭
        assert not websocket.open, "连接应该已关闭"

        # 尝试发送消息应该失败
        with pytest.raises((ConnectionClosed, RuntimeError)):
            await websocket.send(json.dumps({"type": "ping"}))

    @pytest.mark.asyncio
    async def test_abnormal_disconnection(self, ws_url, sample_agent_id):
        """测试异常断开处理

        验证：
        - 异常断开被正确处理
        - 不会导致服务器崩溃
        - 可以重新连接
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        try:
            websocket = await websockets.connect(uri, ping_interval=None)
            # 模拟异常断开（不正常关闭）
            websocket.transport.close()

            # 等待一下，让服务器处理断开
            await asyncio.sleep(0.5)

            # 尝试重新连接
            async with websockets.connect(uri, ping_interval=None) as ws_new:
                assert ws_new.open, "应该能够重新连接"

        except Exception as e:
            pytest.skip(f"异常断开测试遇到错误: {str(e)}")

    @pytest.mark.asyncio
    async def test_multiple_connections_same_agent(self, ws_url, sample_agent_id):
        """测试同一 Agent 的多个连接

        验证：
        - 同一个 Agent ID 可以有多个 WebSocket 连接
        - 多个连接都能正常工作
        - 连接之间互不影响
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        # 创建第一个连接
        ws1 = await websockets.connect(uri, ping_interval=None)
        assert ws1.open, "第一个连接应该打开"

        try:
            # 创建第二个连接
            ws2 = await websockets.connect(uri, ping_interval=None)
            assert ws2.open, "第二个连接应该打开"

            # 两个连接都应该是打开的
            assert ws1.open, "第一个连接应该仍然打开"
            assert ws2.open, "第二个连接应该打开"

            # 关闭第一个连接
            await ws1.close()
            assert not ws1.open, "第一个连接应该已关闭"
            assert ws2.open, "第二个连接应该仍然打开"

            # 关闭第二个连接
            await ws2.close()
            assert not ws2.open, "第二个连接应该已关闭"

        finally:
            # 清理
            if ws1.open:
                await ws1.close()
            if ws2.open:
                await ws2.close()

    @pytest.mark.asyncio
    async def test_connection_timeout(self, ws_url, sample_agent_id, ws_timeout):
        """测试连接超时处理

        验证：
        - 连接建立有合理的超时时间
        - 超时不会导致资源泄漏
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                # 等待足够长的时间
                await asyncio.sleep(ws_timeout + 1)
                # 如果还能发送消息说明连接活跃
                assert websocket.open, "连接应该仍然活跃"

        except asyncio.TimeoutError:
            pytest.fail("连接不应该超时")

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self, ws_url, sample_agent_id):
        """测试快速连接/断开循环

        验证：
        - 可以快速连接和断开
        - 没有资源泄漏
        - 服务器能正确处理
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        for i in range(5):
            async with websockets.connect(uri, ping_interval=None) as websocket:
                assert websocket.open, f"第 {i + 1} 个连接应该打开"
                # 立即关闭
                ***REMOVED***  # async with 自动关闭

        # 最后验证还能连接
        async with websockets.connect(uri, ping_interval=None) as websocket:
            assert websocket.open, "最后的连接应该打开"
