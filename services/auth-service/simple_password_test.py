"""
简单的密码加密测试

直接演示密码哈希和验证功能
"""

# 模拟密码加密功能（基于现有的实现）
from ***REMOVED***lib.context import CryptContext

# 创建密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_admin_***REMOVED***word(plain_***REMOVED***word: str) -> str:
    """哈希管理后台用户密码"""
    return pwd_context.hash(plain_***REMOVED***word)


def verify_admin_***REMOVED***word(plain_***REMOVED***word: str, hashed_***REMOVED***word: str) -> bool:
    """验证管理后台用户密码"""
    try:
        return pwd_context.verify(plain_***REMOVED***word, hashed_***REMOVED***word)
    except (ValueError, TypeError):
        return False


def test_***REMOVED***word_hashing():
    """测试密码哈希和验证功能"""
    print("=" * 50)
    print("测试密码哈希和验证功能")
    print("=" * 50)

    # 测试用例数据
    test_cases = [
        ("***REMOVED***", "管理员默认密码"),
        ("***REMOVED***!", "包含特殊字符的密码"),
        ("123456", "纯数字密码"),
        ("MySecurePass2024", "强密码"),
        ("测试密码123", "包含中文的密码"),
    ]

    print("开始测试密码哈希功能...")

    for plain_***REMOVED***word, description in test_cases:
        print(f"\n测试密码: {description}")

        # 1. 测试密码哈希
        hashed = hash_admin_***REMOVED***word(plain_***REMOVED***word)
        print(f"  明文密码: {plain_***REMOVED***word}")
        print(f"  哈希结果: {hashed}")

        # 验证哈希结果不为空
        assert hashed, "哈希结果不能为空"
        assert len(hashed) > 20, "哈希结果长度异常"

        # 2. 测试密码验证 - 正确密码
        is_valid = verify_admin_***REMOVED***word(plain_***REMOVED***word, hashed)
        print(f"  正确密码验证: {'✅ 通过' if is_valid else '❌ 失败'}")
        assert is_valid, f"正确密码验证失败: {plain_***REMOVED***word}"

        # 3. 测试密码验证 - 错误密码
        wrong_***REMOVED***words = [plain_***REMOVED***word + "wrong", "wrong" + plain_***REMOVED***word, "completely_wrong_***REMOVED***word"]

        for wrong_***REMOVED***word in wrong_***REMOVED***words:
            is_invalid = verify_admin_***REMOVED***word(wrong_***REMOVED***word, hashed)
            assert not is_invalid, f"错误密码验证失败: 错误密码 '{wrong_***REMOVED***word}' 被误判为正确"

        print("  错误密码验证: ✅ 通过")
        print(f"  ✅ {description} 测试通过")

    # 4. 测试哈希一致性（相同密码应产生不同哈希）
    print("\n测试哈希一致性...")
    ***REMOVED***word = "consistency_test"
    hash1 = hash_admin_***REMOVED***word(***REMOVED***word)
    hash2 = hash_admin_***REMOVED***word(***REMOVED***word)

    # bcrypt每次哈希都应该不同（包含随机盐）
    print(f"  哈希1: {hash1}")
    print(f"  哈希2: {hash2}")
    print(f"  哈希是否相同: {'❌ 相同（不符合安全要求）' if hash1 == hash2 else '✅ 不同（符合安全要求）'}")

    # 但验证应该都通过
    verify1 = verify_admin_***REMOVED***word(***REMOVED***word, hash1)
    verify2 = verify_admin_***REMOVED***word(***REMOVED***word, hash2)
    print(f"  哈希1验证: {'✅ 通过' if verify1 else '❌ 失败'}")
    print(f"  哈希2验证: {'✅ 通过' if verify2 else '❌ 失败'}")

    assert verify1 and verify2, "哈希验证失败"

    print("\n🎉 密码哈希和验证功能测试全部通过！")


def demo_***REMOVED***word_usage():
    """演示密码加密功能的使用方法"""
    print("\n" + "=" * 60)
    print("密码加密功能使用演示")
    print("=" * 60)

    print("\n1. 哈希密码示例:")
    plain_***REMOVED***word = "MyAdminPassword123!"
    hashed = hash_admin_***REMOVED***word(plain_***REMOVED***word)
    print(f"   原始密码: {plain_***REMOVED***word}")
    print(f"   哈希结果: {hashed}")

    print("\n2. 验证密码示例:")
    is_correct = verify_admin_***REMOVED***word(plain_***REMOVED***word, hashed)
    is_wrong = verify_admin_***REMOVED***word("wrong_***REMOVED***word", hashed)
    print(f"   正确密码验证: {is_correct} ✅")
    print(f"   错误密码验证: {is_wrong} ❌")

    print("\n3. 安全特性:")
    print("   • 使用bcrypt算法，提供盐值和自适应哈希")
    print("   • 每次哈希结果不同，提高安全性")
    print("   • 计算成本高，防止暴力破解")

    print("\n4. 使用场景:")
    print("   • 用户注册时哈希密码存储")
    print("   • 用户登录时验证密码")
    print("   • 密码重置功能")

    print("\n✅ 演示完成")


def main():
    """主函数"""
    print("🚀 开始密码加密功能测试\n")

    try:
        # 测试密码哈希和验证功能
        test_***REMOVED***word_hashing()

        # 演示功能使用
        demo_***REMOVED***word_usage()

        print("\n" + "=" * 50)
        print("🎉 密码测试完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
