#!/usr/bin/env python3
"""测试负载均衡配置脚本

用于验证 Gateway 负载均衡配置是否正确
"""

import os
import sys
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.utils.service_discovery import ServiceDiscovery


async def test_service_discovery():
    """测试服务发现配置"""
    print("=" * 60)
    print("Gateway 负载均衡配置测试")
    print("=" * 60)
    print()

    # 检查环境变量
    print("1. 检查环境变量配置:")
    env_vars = {
        "HOST_SERVICE_INSTANCES": os.getenv("HOST_SERVICE_INSTANCES"),
        "AUTH_SERVICE_INSTANCES": os.getenv("AUTH_SERVICE_INSTANCES"),
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

    # 测试获取服务地址
    print("3. 测试服务地址获取（轮询 10 次）:")
    service_name = "host"
    print(f"   服务名称: {service_name}")
    print()

    for i in range(10):
        url = await discovery.get_service_url(service_name)
        print(f"   请求 {i+1:2d}: {url}")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("如果看到不同的地址轮询切换，说明配置成功！")
    print("如果所有请求都指向同一个地址，请检查：")
    print("1. 环境变量 HOST_SERVICE_INSTANCES 是否正确设置")
    print("2. Gateway 服务是否重启以加载新配置")
    print("3. 环境变量格式是否正确：IP:PORT,IP:PORT")


if __name__ == "__main__":
    asyncio.run(test_service_discovery())

