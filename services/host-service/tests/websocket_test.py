#!/usr/bin/env python3
"""Host WebSocket Client"""

import asyncio
import json
import sys
import time

import websockets

# ✅ Change to your actual device token
DEVICE_TOKEN = "YOUR_DEVICE_TOKEN_HERE"

# ✅ Correct WebSocket path (fixed)
WS_URL = f"ws://localhost:8000/api/v1/ws/host-service/host?token={DEVICE_TOKEN}"


async def host_websocket_client():
    """Host WebSocket Client"""

    print(f"🔄 Connecting to: {WS_URL}")
    print("=" * 70)

    try:
        async with websockets.connect(WS_URL, ping_interval=None) as websocket:
            print("✅ WebSocket connection established successfully")
            print("=" * 70)

            # Send initial heartbeat
            heartbeat = {"type": "heartbeat", "data": {"timestamp": int(time.time()), "source": "python-client"}}
            await websocket.send(json.dumps(heartbeat))
            print(f"💓 Sending heartbeat: {json.dumps(heartbeat, indent=2)}")

            # Start heartbeat task
            heartbeat_task = asyncio.create_task(send_heartbeat_loop(websocket))

            # Receive message loop
            async for message in websocket:
                data = json.loads(message)
                print("\n📥 Received message:")
                print(json.dumps(data, indent=2))

                # Process command
                if data.get("type") == "command":
                    print(f"\n⚡ Executing command: {data.get('command')}")

                    # Send response
                    response = {
                        "type": "command_response",
                        "command_id": data.get("command_id"),
                        "status": "success",
                        "result": "Command execution completed",
                        "timestamp": int(time.time()),
                    }
                    await websocket.send(json.dumps(response))
                    print("\n📤 Sending response:")
                    print(json.dumps(response, indent=2))

            # Cancel heartbeat task
            heartbeat_task.cancel()

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ Connection failed: HTTP {e.status_code}")
        if e.status_code == 403:
            print("   Reason: Token is invalid or expired")
            print("   Solution: Please re-acquire device Token")
        print("=" * 70)
        sys.exit(1)
    except websockets.exceptions.ConnectionClosed:
        print("\n⚠️ WebSocket connection closed")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("=" * 70)
        sys.exit(1)


async def send_heartbeat_loop(websocket):
    """Send heartbeat periodically"""
    while True:
        await asyncio.sleep(30)  # Send every 30 seconds

        try:
            heartbeat = {"type": "heartbeat", "data": {"timestamp": int(time.time()), "source": "python-client"}}
            await websocket.send(json.dumps(heartbeat))
            print(f"\n💓 Sending heartbeat: {heartbeat['data']['timestamp']}")
        except Exception as e:
            print(f"\n❌ Heartbeat sending failed: {e}")
            break


if __name__ == "__main__":
    if DEVICE_TOKEN == "YOUR_DEVICE_TOKEN_HERE":
        print("❌ Please set DEVICE_TOKEN first")
        print("=" * 70)
        print("\nSteps to acquire Token:")
        print("1. Run device login:")
        print('   curl -X POST "http://localhost:8000/api/v1/auth/device/login" \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"hardware_id": "HW-TEST-001", "mg_id": "MG-001"}\'')
        print("\n2. Copy the returned access_token")
        print("3. Modify the DEVICE_TOKEN variable in script")
        print("=" * 70)
        sys.exit(1)

    print("=== Host WebSocket Client ===")
    print(f"Connection address: {WS_URL}")
    print("=" * 70)

    try:
        asyncio.run(host_websocket_client())
    except KeyboardInterrupt:
        print("\n\n👋 Manual interruption, exiting program")
        print("=" * 70)
