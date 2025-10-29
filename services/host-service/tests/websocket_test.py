#!/usr/bin/env python3
"""Host WebSocket 客户端"""

import asyncio
import websockets
import json
import time
import sys

# ✅ 修改为你的实际设备 token
DEVICE_TOKEN = "YOUR_DEVICE_TOKEN_HERE"

# ✅ 正确的 WebSocket 路径（修复后）
WS_URL = f"ws://localhost:8000/api/v1/ws/host-service/host?token={DEVICE_TOKEN}"


async def host_websocket_client():
    """Host WebSocket 客户端"""

    print(f"🔄 正在连接到: {WS_URL}")
    print("=" * 70)

    try:
        async with websockets.connect(WS_URL, ping_interval=None) as websocket:
            print("✅ WebSocket 连接成功建立")
            print("=" * 70)

            # 发送初始心跳
            heartbeat = {"type": "heartbeat", "data": {"timestamp": int(time.time()), "source": "python-client"}}
            await websocket.send(json.dumps(heartbeat))
            print(f"💓 发送心跳: {json.dumps(heartbeat, indent=2)}")

            # 启动心跳任务
            heartbeat_task = asyncio.create_task(send_heartbeat_loop(websocket))

            # 接收消息循环
            async for message in websocket:
                data = json.loads(message)
                print(f"\n📥 收到消息:")
                print(json.dumps(data, indent=2))

                # 处理命令
                if data.get("type") == "command":
                    print(f"\n⚡ 执行命令: {data.get('command')}")

                    # 发送响应
                    response = {
                        "type": "command_response",
                        "command_id": data.get("command_id"),
                        "status": "success",
                        "result": "命令执行完成",
                        "timestamp": int(time.time()),
                    }
                    await websocket.send(json.dumps(response))
                    print(f"\n📤 发送响应:")
                    print(json.dumps(response, indent=2))

            # 取消心跳任务
            heartbeat_task.cancel()

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ 连接失败: HTTP {e.status_code}")
        if e.status_code == 403:
            print("   原因: Token 无效或已过期")
            print("   解决: 请重新获取设备 Token")
        print("=" * 70)
        sys.exit(1)
    except websockets.exceptions.ConnectionClosed:
        print("\n⚠️ WebSocket 连接已关闭")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("=" * 70)
        sys.exit(1)


async def send_heartbeat_loop(websocket):
    """定时发送心跳"""
    while True:
        await asyncio.sleep(30)  # 每30秒发送一次

        try:
            heartbeat = {"type": "heartbeat", "data": {"timestamp": int(time.time()), "source": "python-client"}}
            await websocket.send(json.dumps(heartbeat))
            print(f"\n💓 发送心跳: {heartbeat['data']['timestamp']}")
        except Exception as e:
            print(f"\n❌ 心跳发送失败: {e}")
            break


if __name__ == "__main__":
    if DEVICE_TOKEN == "YOUR_DEVICE_TOKEN_HERE":
        print("❌ 请先设置 DEVICE_TOKEN")
        print("=" * 70)
        print("\n获取 Token 的步骤:")
        print("1. 运行设备登录:")
        print('   curl -X POST "http://localhost:8000/api/v1/auth/device/login" \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"hardware_id": "HW-TEST-001", "mg_id": "MG-001"}\'')
        print("\n2. 复制返回的 access_token")
        print("3. 修改脚本中的 DEVICE_TOKEN 变量")
        print("=" * 70)
        sys.exit(1)

    print("=== Host WebSocket 客户端 ===")
    print(f"连接地址: {WS_URL}")
    print("=" * 70)

    try:
        asyncio.run(host_websocket_client())
    except KeyboardInterrupt:
        print("\n\n👋 手动中断，退出程序")
        print("=" * 70)
