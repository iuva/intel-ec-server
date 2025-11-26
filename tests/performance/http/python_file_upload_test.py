#!/usr/bin/env python3
"""文件上传性能测试示例脚本"""
import argparse
import asyncio
import os
import time
from statistics import mean, median

import aiohttp


def create_test_file(path: str, size_mb: int) -> None:
    with open(path, "wb") as f:
        f.write(b"0" * size_mb * 1024 * 1024)


async def upload_file(session: aiohttp.ClientSession, url: str, token: str, file_path: str) -> float:
    start_time = time.time()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = aiohttp.FormData()
    data.add_field("file", open(file_path, "rb"), filename=os.path.basename(file_path))
    async with session.post(url, data=data, headers=headers) as resp:
        await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"upload failed: {resp.status}")
    return time.time() - start_time


async def run_test(args: argparse.Namespace) -> None:
    url = args.url.rstrip("/") + "/api/v1/host/file/upload"
    token = args.token or ""
    file_path = args.file
    created_temp = False

    if not file_path:
        file_path = f"tmp_upload_{args.size}mb.bin"
        create_test_file(file_path, args.size)
        created_temp = True

    durations = []
    semaphore = asyncio.Semaphore(args.concurrency)

    async with aiohttp.ClientSession() as session:
        async def worker() -> None:
            async with semaphore:
                durations.append(await upload_file(session, url, token, file_path))

        await asyncio.gather(*(worker() for _ in range(args.requests)))

    if created_temp:
        os.remove(file_path)

    avg = mean(durations)
    med = median(durations)
    mx = max(durations)
    mn = min(durations)

    print("上传性能统计：")
    print(f"  请求数: {len(durations)}")
    print(f"  平均: {avg:.3f}s  中位数: {med:.3f}s  最快: {mn:.3f}s  最慢: {mx:.3f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Host Service 文件上传性能测试")
    parser.add_argument("--url", default=os.getenv("PERF_HOST_URL", "http://localhost:8003"))
    parser.add_argument("--token", default=os.getenv("PERF_ADMIN_TOKEN", ""))
    parser.add_argument("--size", type=int, default=10, help="生成临时文件大小(MB)")
    parser.add_argument("--file", help="使用已有文件")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(run_test(args))


if __name__ == "__main__":
    main()
