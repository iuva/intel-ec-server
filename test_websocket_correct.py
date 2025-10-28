"""
测试 WebSocket 连接 - 正确的地址格式

此脚本测试通过网关连接到 Host Service 的 WebSocket 端点
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    """测试 WebSocket 连接"""
    
    # ✅ 新格式（推荐）
    uri = "ws://localhost:8000/host/ws/agent/agent-123"
    
    # 或者旧格式（仍支持）
    # uri = "ws://localhost:8000/ws/host-service/ws/agent/agent-123"
    
    print(f"🚀 尝试连接到: {uri}")
    print()
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功!")
            print()
            
            # 发送测试消息
            test_message = json.dumps({"type": "ping", "data": "hello"})
            print(f"📤 发送消息: {test_message}")
            await websocket.send(test_message)
            
            # 接收响应（设置超时）
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 收到响应: {response}")
                print()
                print("✅ 测试成功!")
                return 0
            except asyncio.TimeoutError:
                print("⏱️  等待响应超时（可能是正常的，取决于服务器实现）")
                return 0
                
    except ConnectionRefusedError:
        print("❌ 连接被拒绝")
        print("   - 检查网关服务是否运行: docker-compose ps gateway-service")
        print("   - 检查地址是否正确: ws://localhost:8000/ws/host-service/ws/agent/agent-123")
        return 1
    except websockets.exceptions.InvalidStatusException as e:
        print(f"❌ WebSocket 握手失败: {e}")
        print(f"   - HTTP 状态码: {e.status_code if hasattr(e, 'status_code') else 'unknown'}")
        print("   - 可能的原因:")
        print("     1. 地址错误 (应该是 /ws/host-service/ws/agent/agent-123)")
        print("     2. 认证问题 (需要在 header 中提供 token)")
        print("     3. 路由不存在")
        return 1
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
        return 1


async def test_with_auth_header():
    """测试带认证头的 WebSocket 连接"""
    
    uri = "ws://localhost:8000/ws/host-service/ws/agent/agent-123"
    
    # 这是一个示例 token（如果需要认证）
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print(f"🚀 尝试带认证头连接到: {uri}")
    print()
    
    try:
        async with websockets.connect(
            uri,
            extra_headers=headers.items()
        ) as websocket:
            print("✅ WebSocket 连接成功（带认证）!")
            return 0
    except Exception as e:
        print(f"❌ 带认证的连接失败: {type(e).__name__}: {e}")
        return 1


def main():
    """主函数"""
    print("=" * 70)
    print("WebSocket 连接测试")
    print("=" * 70)
    print()
    
    # 测试 1: 基础连接
    print("【测试 1】无认证的基础连接")
    print("-" * 70)
    result1 = asyncio.run(test_websocket())
    print()
    print()
    
    # 测试 2: 带认证头的连接
    print("【测试 2】带认证头的连接")
    print("-" * 70)
    result2 = asyncio.run(test_with_auth_header())
    print()
    print()
    
    # 总结
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    
    if result1 == 0:
        print("✅ 基础连接: 成功")
    else:
        print("❌ 基础连接: 失败")
    
    if result2 == 0:
        print("✅ 认证连接: 成功")
    else:
        print("❌ 认证连接: 失败")
    
    print()
    print("📋 正确的地址格式:")
    print("   ws://localhost:8000/ws/{service_name}/{path}")
    print()
    print("📋 例子:")
    print("   ws://localhost:8000/ws/host-service/ws/agent/agent-123")
    print()


if __name__ == "__main__":
    main()
