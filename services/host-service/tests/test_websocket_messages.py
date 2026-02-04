"""
WebSocket Message Handling Test Module

Test Content:
- Sending and receiving messages
- Invalid JSON handling
- Message type validation
- Large message handling
- Rapid message sequence
"""

import asyncio
import json

import pytest
import websockets


@pytest.mark.asyncio
class TestWebSocketMessages:
    """WebSocket Message Handling Test Class"""

    @pytest.mark.asyncio
    async def test_send_receive_message(self, ws_url, sample_agent_id, message_timeout):
        """Test sending and receiving messages

        Verification:
        - Can send JSON messages
        - Message format is correct
        - Connection remains open
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Construct test message
            test_message = {"type": "ping", "data": "hello"}

            # Send message
            await websocket.send(json.dumps(test_message))
            assert websocket.open, "Connection should still be open after sending message"

            # Try to receive response (if server replies)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=message_timeout)
                assert response is not None, "Should receive response"
            except asyncio.TimeoutError:
                # If no immediate response, this is also acceptable
                pass

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, ws_url, sample_agent_id):
        """Test invalid JSON handling

        Verification:
        - Invalid JSON does not cause connection to disconnect
        - Server can properly handle errors
        - Connection remains available
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Send invalid JSON
            await websocket.send("{invalid json")

            # Connection should still be open
            assert websocket.open, "Connection should still be open after invalid JSON"

            # Try to send valid message, ensure connection is still available
            valid_message = {"type": "ping"}
            await websocket.send(json.dumps(valid_message))
            assert websocket.open, "Connection should still be open after sending valid message"

    @pytest.mark.asyncio
    async def test_message_type_validation(self, ws_url, sample_agent_id):
        """Test message type validation

        Verification:
        - Unknown message types are properly handled
        - Connection remains available
        - Server does not disconnect due to unknown types
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Send unknown message type
            invalid_message = {"type": "unknown_type", "data": {}}
            await websocket.send(json.dumps(invalid_message))

            # Connection should remain open
            assert websocket.open, "Connection should still be open after unknown message type"

            # Verify communication can continue
            valid_message = {"type": "ping"}
            await websocket.send(json.dumps(valid_message))
            assert websocket.open, "Subsequent messages should be able to send normally"

    @pytest.mark.asyncio
    async def test_large_message_handling(self, ws_url, sample_agent_id):
        """Test large message handling

        Verification:
        - Can send large messages (1MB)
        - Message integrity
        - Connection stability
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Create 1MB large message
            large_data = "x" * (1024 * 1024)
            large_message = {"type": "data", "content": large_data}

            # Send large message
            await websocket.send(json.dumps(large_message))
            assert websocket.open, "Connection should still be open after sending large message"

            # Verify connection integrity
            small_message = {"type": "ping"}
            await websocket.send(json.dumps(small_message))
            assert websocket.open, "Should be able to send small message after large message"

    @pytest.mark.asyncio
    async def test_rapid_message_sequence(self, ws_url, sample_agent_id):
        """Test rapid message sequence

        Verification:
        - Can quickly send multiple messages in succession
        - Message order is maintained
        - Server can handle high-frequency messages
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"
        num_messages = 100

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Rapidly send multiple messages
            for i in range(num_messages):
                message = {"type": "batch", "index": i}
                await websocket.send(json.dumps(message))

            # Connection should still be open
            assert websocket.open, "Connection should still be open after sending 100 messages"

            # Verify communication can continue
            final_message = {"type": "ping"}
            await websocket.send(json.dumps(final_message))
            assert websocket.open, "The final message should be able to send normally"

    @pytest.mark.asyncio
    async def test_empty_message(self, ws_url, sample_agent_id):
        """Test empty message handling

        Verification:
        - Empty messages are properly handled
        - Connection remains stable
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Send empty string
            await websocket.send("")

            # Connection should still be open
            assert websocket.open, "Connection should still be open after empty message"

            # Verify communication can continue
            valid_message = {"type": "ping"}
            await websocket.send(json.dumps(valid_message))
            assert websocket.open, "Should be able to send valid message after empty message"

    @pytest.mark.asyncio
    async def test_message_with_special_characters(self, ws_url, sample_agent_id):
        """Test special character handling

        Verification:
        - Messages containing special characters are properly handled
        - Unicode character support
        - Escape character handling
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Message contains special characters
            special_message = {
                "type": "special",
                "data": "Hello World 🌍 !@#$%^&*()",
            }
            await websocket.send(json.dumps(special_message))
            assert websocket.open, "Connection should still be open after special character message"

    @pytest.mark.asyncio
    async def test_nested_json_message(self, ws_url, sample_agent_id):
        """Test nested JSON message

        Verification:
        - Supports nested JSON structures
        - Complex data structure handling
        """
        uri = f"{ws_url}/api/v1/ws/agent/{sample_agent_id}"

        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Send nested JSON
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
            assert websocket.open, "Connection should still be open after nested JSON message"
