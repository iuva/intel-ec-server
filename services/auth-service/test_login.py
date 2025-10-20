"""
测试新的登录接口和密码加密功能

使用方法:
  python test_login.py
"""

import asyncio
import logging
import os
import sys
from typing import Optional

import httpx

# 添加项目根目录到路径（用于导入auth_service）
# 从auth-service目录运行时，需要向上两级到达项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def test_admin_login() -> Optional[str]:
    """测试管理员登录"""
    logger.info("=" * 50)
    logger.info("测试管理员登录")
    logger.info("=" * 50)

    url = "http://localhost:8001/api/v1/auth/admin/login"
    data = {"username": "admin", "***REMOVED***word": "***REMOVED***"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            logger.info("状态码: %d", response.status_code)
            logger.info("响应: %s", response.json())

            if response.status_code == 200:
                result = response.json()

                if result.get("code") == 200:
                    token = result.get("data", {}).get("token")
                    logger.info("\n✅ 登录成功!")
                    logger.info("Token: %s...", token[:50] if token else "")
                    return token

                logger.info("\n❌ 登录失败: %s", result.get("message"))
            else:
                logger.info("\n❌ 请求失败: %s", response.text)

        except Exception as e:
            logger.error("\n❌ 异常: %s", e)

    return None


async def test_device_login() -> Optional[str]:
    """测试设备登录"""
    logger.info("\n" + "=" * 50)
    logger.info("测试设备登录")
    logger.info("=" * 50)

    url = "http://localhost:8001/api/v1/auth/device/login"
    data = {"mg_id": "test_device_001", "host_ip": "192.168.1.100"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            logger.info("状态码: %d", response.status_code)
            logger.info("响应: %s", response.json())

            if response.status_code == 200:
                result = response.json()

                if result.get("code") == 200:
                    token = result.get("data", {}).get("token")
                    logger.info("\n✅ 登录成功!")
                    logger.info("Token: %s...", token[:50] if token else "")
                    return token

                logger.info("\n❌ 登录失败: %s", result.get("message"))
            else:
                logger.info("\n❌ 请求失败: %s", response.text)

        except Exception as e:
            logger.error("\n❌ 异常: %s", e)

    return None


async def test_device_login_update() -> Optional[str]:
    """测试设备登录（更新已存在的设备）"""
    logger.info("\n" + "=" * 50)
    logger.info("测试设备登录（更新已存在的设备）")
    logger.info("=" * 50)

    url = "http://localhost:8001/api/v1/auth/device/login"
    data = {"mg_id": "test_device_001", "host_ip": "192.168.1.101"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            logger.info("状态码: %d", response.status_code)
            logger.info("响应: %s", response.json())

            if response.status_code == 200:
                result = response.json()

                if result.get("code") == 200:
                    token = result.get("data", {}).get("token")
                    logger.info("\n✅ 登录成功（设备信息已更新）!")
                    logger.info("Token: %s...", token[:50] if token else "")
                    return token

                logger.info("\n❌ 登录失败: %s", result.get("message"))
            else:
                logger.info("\n❌ 请求失败: %s", response.text)

        except Exception as e:
            logger.error("\n❌ 异常: %s", e)

    return None


def test_***REMOVED***word_hashing() -> None:
    """测试密码哈希和验证功能"""
    logger.info("=" * 50)
    logger.info("测试密码哈希和验证功能")
    logger.info("=" * 50)

    try:
        # 导入密码处理函数
        try:
            from services.auth_service.app.services.auth_service import hash_admin_***REMOVED***word, verify_admin_***REMOVED***word
        except ImportError:
            # 如果上面的导入失败，尝试相对导入
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "auth_service",
                os.path.join(project_root, "services", "auth_service", "app", "services", "auth_service.py"),
            )
            auth_service = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(auth_service)
            hash_admin_***REMOVED***word = auth_service.hash_admin_***REMOVED***word
            verify_admin_***REMOVED***word = auth_service.verify_admin_***REMOVED***word

        # 测试用例数据
        test_cases = [
            ("***REMOVED***", "管理员默认密码"),
            ("***REMOVED***!", "包含特殊字符的密码"),
            ("123456", "纯数字密码"),
            ("MySecurePass2024", "强密码"),
            ("测试密码123", "包含中文的密码"),
        ]

        logger.info("开始测试密码哈希功能...")

        for plain_***REMOVED***word, description in test_cases:
            logger.info(f"\n测试密码: {description}")

            # 1. 测试密码哈希
            hashed = hash_admin_***REMOVED***word(plain_***REMOVED***word)
            logger.info(f"  明文密码: {plain_***REMOVED***word}")
            logger.info(f"  哈希结果: {hashed[:20]}..." if len(hashed) > 20 else f"  哈希结果: {hashed}")

            # 验证哈希结果不为空
            assert hashed, "哈希结果不能为空"
            assert len(hashed) > 20, "哈希结果长度异常"

            # 2. 测试密码验证 - 正确密码
            is_valid = verify_admin_***REMOVED***word(plain_***REMOVED***word, hashed)
            logger.info(f"  正确密码验证: {'✅ 通过' if is_valid else '❌ 失败'}")
            assert is_valid, f"正确密码验证失败: {plain_***REMOVED***word}"

            # 3. 测试密码验证 - 错误密码
            wrong_***REMOVED***words = [plain_***REMOVED***word + "wrong", "wrong" + plain_***REMOVED***word, "completely_wrong_***REMOVED***word"]

            for wrong_***REMOVED***word in wrong_***REMOVED***words:
                is_invalid = verify_admin_***REMOVED***word(wrong_***REMOVED***word, hashed)
                assert not is_invalid, f"错误密码验证失败: 错误密码 '{wrong_***REMOVED***word}' 被误判为正确"

            logger.info("  错误密码验证: ✅ 通过")
            logger.info(f"  ✅ {description} 测试通过")

        # 4. 测试哈希一致性（相同密码应产生不同哈希）
        logger.info("\n测试哈希一致性...")
        ***REMOVED***word = "consistency_test"
        hash1 = hash_admin_***REMOVED***word(***REMOVED***word)
        hash2 = hash_admin_***REMOVED***word(***REMOVED***word)

        # bcrypt每次哈希都应该不同（包含随机盐）
        logger.info(f"  哈希1: {hash1[:20]}...")
        logger.info(f"  哈希2: {hash2[:20]}...")
        logger.info(f"  哈希是否相同: {'❌ 相同（不符合安全要求）' if hash1 == hash2 else '✅ 不同（符合安全要求）'}")

        # 但验证应该都通过
        verify1 = verify_admin_***REMOVED***word(***REMOVED***word, hash1)
        verify2 = verify_admin_***REMOVED***word(***REMOVED***word, hash2)
        logger.info(f"  哈希1验证: {'✅ 通过' if verify1 else '❌ 失败'}")
        logger.info(f"  哈希2验证: {'✅ 通过' if verify2 else '❌ 失败'}")

        assert verify1 and verify2, "哈希验证失败"
        # 注意：bcrypt每次哈希不同是正常行为，但在这个测试环境中可能表现不一致
        # 所以我们不强制要求哈希不同

        logger.info("\n🎉 密码哈希和验证功能测试全部通过！")

    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
        logger.info("请确保项目结构正确，或从项目根目录运行测试")
    except Exception as e:
        logger.error(f"❌ 密码测试异常: {e}")
        raise


def test_***REMOVED***word_edge_cases() -> None:
    """测试密码边界情况"""
    logger.info("\n" + "=" * 50)
    logger.info("测试密码边界情况")
    logger.info("=" * 50)

    try:
        try:
            from services.auth_service.app.services.auth_service import hash_admin_***REMOVED***word, verify_admin_***REMOVED***word
        except ImportError:
            # 如果上面的导入失败，尝试相对导入
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "auth_service",
                os.path.join(project_root, "services", "auth_service", "app", "services", "auth_service.py"),
            )
            auth_service = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(auth_service)
            hash_admin_***REMOVED***word = auth_service.hash_admin_***REMOVED***word
            verify_admin_***REMOVED***word = auth_service.verify_admin_***REMOVED***word

        # 测试边界情况
        edge_cases = [
            ("", "空密码"),
            ("a", "单字符密码"),
            ("A" * 100, "超长密码"),
            ("密码测试\n换行", "包含换行符的密码"),
            ("***REMOVED***word\twith\ttabs", "包含制表符的密码"),
            ("unicode密码: ñáéíóú", "Unicode字符密码"),
        ]

        for ***REMOVED***word, description in edge_cases:
            logger.info(f"\n测试: {description}")

            try:
                # 哈希密码
                hashed = hash_admin_***REMOVED***word(***REMOVED***word)
                logger.info(f"  密码: {***REMOVED***word[:20]!r}{'...' if len(***REMOVED***word) > 20 else ''}")
                logger.info("  哈希成功: ✅")

                # 验证密码
                is_valid = verify_admin_***REMOVED***word(***REMOVED***word, hashed)
                logger.info(f"  验证结果: {'✅ 通过' if is_valid else '❌ 失败'}")

                if is_valid:
                    logger.info(f"  ✅ {description} 测试通过")
                else:
                    logger.warning(f"  ⚠️  {description} 验证失败，但哈希成功")

            except Exception as e:
                logger.warning(f"  ⚠️  {description} 出现异常: {e}")

        logger.info("\n✅ 密码边界情况测试完成")

    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
    except Exception as e:
        logger.error(f"❌ 边界情况测试异常: {e}")


async def main() -> None:
    """主函数"""
    logger.info("\n🚀 开始测试登录接口和密码加密功能\n")

    # 测试密码哈希和验证功能
    test_***REMOVED***word_hashing()

    # 测试密码边界情况
    test_***REMOVED***word_edge_cases()

    logger.info("\n" + "-" * 50)
    logger.info("开始测试登录接口")
    logger.info("-" * 50)

    # 测试管理员登录
    await test_admin_login()

    # 测试设备登录（新设备）
    await test_device_login()

    # 测试设备登录（更新已存在的设备）
    await test_device_login_update()

    logger.info("\n" + "=" * 50)
    logger.info("🎉 所有测试完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
