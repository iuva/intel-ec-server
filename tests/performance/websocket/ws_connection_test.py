#!/usr/bin/env python3
"""WebSocket 连接建立时间测试脚本"""
import argparse
import asyncio
import time
from statistics import mean, median

import websockets


async def test_connections(uri: str, count: int) -> None:
    results = []
    for _ in range(count):
        start = time.time()
        try:
            async with websockets.connect(uri, ping_interval=None):
                results.append(time.time() - start)
        except Exception as exc:  # pragma: no cover - diagnostics
            print(f"连接失败: {exc}")

    if not results:
        print("没有成功的连接")
        return

    print("WebSocket 连接建立时间：")
    print(f"  测试次数: {len(results)}")
    print(f"  平均: {mean(results) * 1000:.2f} ms")
    print(f"  中位数: {median(results) * 1000:.2f} ms")
    print(f"  最快: {min(results) * 1000:.2f} ms")
    print(f"  最慢: {max(results) * 1000:.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Host Service WebSocket 连接性能测试")
    parser.add_argument("--url", default="ws://localhost:8003/api/v1/host/ws/host?token=TEST_TOKEN")
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()

    asyncio.run(test_connections(args.url, args.count))


if __name__ == "__main__":
    main()
