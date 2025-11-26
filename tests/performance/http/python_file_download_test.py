#!/usr/bin/env python3
"""文件下载/断点续传性能测试脚本"""
import argparse
import asyncio
import time
from statistics import mean

import aiohttp


async def download(session: aiohttp.ClientSession, url: str, token: str, range_header: str | None) -> dict:
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    if range_header:
        headers['Range'] = range_header

    start = time.time()
    async with session.get(url, headers=headers) as resp:
        content = await resp.read()
        elapsed = time.time() - start
        return {
            'status': resp.status,
            'duration': elapsed,
            'size': len(content),
            'content_range': resp.headers.get('Content-Range'),
            'accept_ranges': resp.headers.get('Accept-Ranges'),
        }


async def run_test(args: argparse.Namespace) -> None:
    url = args.url.rstrip('/') + f"/api/v1/host/file/{args.filename}"
    token = args.token or ''

    async with aiohttp.ClientSession() as session:
        tasks = [download(session, url, token, None) for _ in range(args.requests)]
        results = await asyncio.gather(*tasks)

    durations = [r['duration'] for r in results if r['status'] in (200, 206)]
    if durations:
        avg = mean(durations)
        total_bytes = sum(r['size'] for r in results if r['status'] in (200, 206))
        throughput = total_bytes / sum(durations)
        print("文件下载性能：")
        print(f"  成功请求: {len(durations)}/{len(results)}")
        print(f"  平均耗时: {avg:.3f}s")
        print(f"  平均吞吐量: {throughput / 1024 / 1024:.2f} MB/s")

    if args.range:
        async with aiohttp.ClientSession() as session:
            result = await download(session, url, token, args.range)
            print("断点续传测试：")
            print(f"  状态码: {result['status']}")
            print(f"  Content-Range: {result['content_range']}")
            print(f"  Accept-Ranges: {result['accept_ranges']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Host Service 文件下载测试")
    parser.add_argument('--url', default='http://localhost:8003')
    parser.add_argument('--token', default='')
    parser.add_argument('--filename', required=True)
    parser.add_argument('--requests', type=int, default=20)
    parser.add_argument('--range', help='可选 Range 头, 例如 bytes=0-1048575')
    args = parser.parse_args()

    asyncio.run(run_test(args))


if __name__ == '__main__':
    main()
