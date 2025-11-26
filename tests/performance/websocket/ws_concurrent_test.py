#!/usr/bin/env python3
"""WebSocket 并发压力测试脚本"""
import argparse
import asyncio
import json
import time

import websockets


async def worker(uri: str, agent_id: str, messages: int) -> dict:
    try:
        async with websockets.connect(f"{uri}&agent_id={agent_id}", ping_interval=None) as ws:
            start = time.time()
            for index in range(messages):
                await ws.send(json.dumps({"type": "load", "index": index, "agent": agent_id}))
            elapsed = time.time() - start
            return {"agent": agent_id, "status": "ok", "elapsed": elapsed}
    except Exception as exc:  # pragma: no cover - diagnostics
        return {"agent": agent_id, "status": "error", "error": str(exc)}


async def run_test(uri: str, connections: int, messages: int) -> None:
    tasks = [worker(uri, f"agent_{i:04d}", messages) for i in range(connections)]
    start_all = time.time()
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_all

    success = [r for r in results if r.get("status") == "ok"]
    failures = [r for r in results if r.get("status") != "ok"]

    total_messages = len(success) * messages
    throughput = total_messages / total_time if total_time else 0

    print("WebSocket 并发测试：")
    print(f"  连接数: {connections}")
    print(f"  成功连接: {len(success)}  失败: {len(failures)}")
    print(f"  总耗时: {total_time:.2f}s  吞吐量: {throughput:.2f} msg/sec")
    if failures:
        print("  失败示例:")
        for sample in failures[:3]:
            print(f"    - {sample}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Host Service WebSocket 并发测试")
    parser.add_argument("--url", default="ws://localhost:8003/api/v1/host/ws/host?token=TEST_TOKEN")
    parser.add_argument("--connections", type=int, default=100)
    parser.add_argument("--messages", type=int, default=50)
    args = parser.parse_args()

    asyncio.run(run_test(args.url, args.connections, args.messages))


if __name__ == "__main__":
    main()
