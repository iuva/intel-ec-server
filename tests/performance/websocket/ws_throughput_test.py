#!/usr/bin/env python3
"""WebSocket 消息吞吐量测试脚本"""
import argparse
import asyncio
import json
import time

import websockets


async def run_test(uri: str, messages: int) -> None:
    async with websockets.connect(uri, ping_interval=None) as ws:
        start = time.time()
        for index in range(messages):
            await ws.send(json.dumps({"type": "perf", "index": index}))
        elapsed = time.time() - start

    throughput = messages / elapsed if elapsed else 0
    print("WebSocket 消息吞吐量：")
    print(f"  消息数: {messages}")
    print(f"  总耗时: {elapsed:.3f}s")
    print(f"  吞吐量: {throughput:.2f} msg/sec")


def main() -> None:
    parser = argparse.ArgumentParser(description="Host Service WebSocket 吞吐量测试")
    parser.add_argument("--url", default="ws://localhost:8003/api/v1/host/ws/host?token=TEST_TOKEN")
    parser.add_argument("--messages", type=int, default=1000)
    args = parser.parse_args()

    asyncio.run(run_test(args.url, args.messages))


if __name__ == "__main__":
    main()
