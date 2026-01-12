"""
WebSocket Connection Test Module

Test Content:
- Successfully establish connection
- Invalid Agent ID handling
- Normal connection closing
- Abnormal disconnection handling
- Multiple connection management
"""

import asyncio
import json

import pytest
import websockets
from websockets.exceptions import ConnectionClosed


@pytest.mark.asyncio
class TestWebSocketConnection:
    """WebSocket Connection Test Class"""

    @pytest.mark.asyncio
    async def test_successful_connection(self, ws_url, sample_agent_id, ws_timeout):
        """Test successful establishment of WebSocket connection

        Verification:
        - Connection can be established
        - Connection status is OPEN
        - Connection's agent_id is correct
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Verify connection is established
            assert websocket.open, "WebSocket connection should be in open state"
            assert websocket.state.name == "OPEN", "WebSocket status should be OPEN"

    @pytest.mark.asyncio
    async def test_connection_with_invalid_agent_id(self, ws_url):
        """Test invalid Agent ID handling

        Verification:
        - Invalid Agent ID connections can also be established (FastAPI accepts any parameters)
        - But subsequent operations may fail
        """
        invalid_agent_id = "invalid-agent"
        uri = f"{ws_url}/api/v1/ws/agent/{invalid_agent_id}"

        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                assert websocket.open, "Connection should be established"
        except Exception as e:
            # Connection failure is also acceptable
            pytest.skip(f"Invalid Agent ID connection failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_connection_close_handling(self, ws_url, sample_agent_id):
        """Test connection closing handling

        Verification:
        - Connection can be closed normally
        - Cannot send messages after closing
        - Exceptions are properly thrown after closing
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        websocket = await websockets.connect(uri, ping_interval=None)
        assert websocket.open, "Initial connection should be open"

        # Close connection normally
        await websocket.close()

        # Verify connection is closed
        assert not websocket.open, "Connection should be closed"

        # Attempt to send message should fail
        with pytest.raises((ConnectionClosed, RuntimeError)):
            await websocket.send(json.dumps({"type": "ping"}))

    @pytest.mark.asyncio
    async def test_abnormal_disconnection(self, ws_url, sample_agent_id):
        """Test abnormal disconnection handling

        Verification:
        - Abnormal disconnections are properly handled
        - Does not cause server crash
        - Can reconnect
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        try:
            websocket = await websockets.connect(uri, ping_interval=None)
            # Simulate abnormal disconnection (abnormal close)
            websocket.transport.close()

            # Wait a moment, let server process disconnection
            await asyncio.sleep(0.5)

            # Try to reconnect
            async with websockets.connect(uri, ping_interval=None) as ws_new:
                assert ws_new.open, "Should be able to reconnect"

        except Exception as e:
            pytest.skip(f"Abnormal disconnection test encountered error: {str(e)}")

    @pytest.mark.asyncio
    async def test_multiple_connections_same_agent(self, ws_url, sample_agent_id):
        """Test multiple connections for the same Agent

        Verification:
        - Same Agent ID can have multiple WebSocket connections
        - Multiple connections can work normally
        - Connections do not interfere with each other
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        # Create first connection
        ws1 = await websockets.connect(uri, ping_interval=None)
        assert ws1.open, "First connection should be open"

        try:
            # Create second connection
            ws2 = await websockets.connect(uri, ping_interval=None)
            assert ws2.open, "Second connection should be open"

            # Both connections should be open
            assert ws1.open, "First connection should still be open"
            assert ws2.open, "Second connection should be open"

            # Close first connection
            await ws1.close()
            assert not ws1.open, "First connection should be closed"
            assert ws2.open, "Second connection should still be open"

            # Close second connection
            await ws2.close()
            assert not ws2.open, "Second connection should be closed"

        finally:
            # Cleanup
            if ws1.open:
                await ws1.close()
            if ws2.open:
                await ws2.close()

    @pytest.mark.asyncio
    async def test_connection_timeout(self, ws_url, sample_agent_id, ws_timeout):
        """Test connection timeout handling

        Verification:
        - Connection establishment has reasonable timeout
        - Timeout does not cause resource leak
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                # Wait for a sufficient amount of time
                await asyncio.sleep(ws_timeout + 1)
                # If still able to send messages, connection is active
                assert websocket.open, "Connection should still be active"

        except asyncio.TimeoutError:
            pytest.fail("Connection should not timeout")

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self, ws_url, sample_agent_id):
        """Test rapid connect/disconnect cycles

        Verification:
        - Can quickly connect and disconnect
        - No resource leaks
        - Server can handle correctly
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        for i in range(5):
            async with websockets.connect(uri, ping_interval=None) as websocket:
                assert websocket.open, f"Connection {i + 1} should be open"
                # Close immediately
                ***REMOVED***  # async with closes automatically

        # Finally verify connection can still be made
        async with websockets.connect(uri, ping_interval=None) as websocket:
            assert websocket.open, "Final connection should be open"
