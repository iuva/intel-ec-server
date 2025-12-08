#!/usr/bin/env python3
"""测试 WebSocket 会话粘性脚本

验证同一个 host_id 的 WebSocket 连接总是路由到同一个实例
"""

import os
import sys
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.utils.service_discovery import ServiceDiscovery


async def test_websocket_sticky():
    """测试 WebSocket 会话粘性"""
    print("=" * 60)
    print("WebSocket 会话粘性测试")
    print("=" * 60)
    print()

    # 检查环境变量
    print("1. 检查环境变量配置:")
    env_vars = {
        "HOST_SERVICE_INSTANCES": os.getenv("HOST_SERVICE_INSTANCES"),
        "LOAD_BALANCE_STRATEGY": os.getenv("LOAD_BALANCE_STRATEGY", "round_robin"),
    }

    for key, value in env_vars.items():
        status = "✅ 已设置" if value else "❌ 未设置"
        print(f"   {key}: {value if value else '(未设置)'} {status}")

    print()

    # 创建服务发现实例
    print("2. 初始化服务发现:")
    discovery = ServiceDiscovery(
        nacos_manager=None,  # 不使用 Nacos
        cache_ttl=30,
        load_balance_strategy=env_vars["LOAD_BALANCE_STRATEGY"],
    )

    print(f"   负载均衡策略: {discovery.load_balance_strategy}")
    print(f"   本地实例配置: {discovery._local_instances}")
    print()

    # 测试会话粘性
    print("3. 测试 WebSocket 会话粘性（同一 host_id 应该路由到同一实例）:")
    service_name = "host-service"
    test_host_ids = ["host_001", "host_002", "host_003"]

    print(f"   服务名称: {service_name}")
    print(f"   测试 host_id: {test_host_ids}")
    print()

    # 每个 host_id 测试多次，应该总是路由到同一个实例
    for host_id in test_host_ids:
        print(f"   Host ID: {host_id}")
        instance_urls = []
        for i in range(5):
            url = await discovery.get_websocket_service_url(service_name, host_id)
            instance_urls.append(url)
            print(f"     请求 {i+1}: {url}")

        # 验证是否总是路由到同一个实例
        unique_urls = set(instance_urls)
        if len(unique_urls) == 1:
            print(f"   ✅ 会话粘性正常：总是路由到 {unique_urls.pop()}")
        else:
            print(f"   ❌ 会话粘性失败：路由到多个实例 {unique_urls}")
        print()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("如果每个 host_id 总是路由到同一个实例，说明会话粘性工作正常！")
    print("如果同一个 host_id 路由到不同实例，请检查配置。")


if __name__ == "__main__":
    asyncio.run(test_websocket_sticky())

