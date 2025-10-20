#!/usr/bin/env python3
"""
检查admin服务启动状态和数据库连接

确保admin服务能够正常连接数据库并启动
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
from urllib.parse import quote_plus


async def check_mariadb_connection() -> Dict[str, Any]:
    """检查MariaDB连接"""
    print("🔍 检查MariaDB连接...")

    try:
        # 获取数据库配置（模拟admin服务）
        mariadb_host = os.getenv("MARIADB_HOST", "mariadb")
        mariadb_port = os.getenv("MARIADB_PORT", "3306")
        mariadb_user = os.getenv("MARIADB_USER", "intel_user")
        mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
        mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")

        mariadb_***REMOVED***word_encoded = quote_plus(mariadb_***REMOVED***word)
        mariadb_url = f"mysql+aiomysql://{mariadb_user}:{mariadb_***REMOVED***word_encoded}@{mariadb_host}:{mariadb_port}/{mariadb_database}"

        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(mariadb_url, echo=False)

        async with engine.begin() as conn:
            # 检查数据库是否存在
            result = await conn.execute(text("SELECT DATABASE() as db_name"))
            db_name = result.scalar()
            print(f"✅ 连接数据库: {db_name}")

            # 检查sys_user表是否存在
            result = await conn.execute(text("SHOW TABLES LIKE 'sys_user'"))
            table_exists = result.fetchone() is not None

            if table_exists:
                print("✅ sys_user表存在")

                # 检查表中的记录数
                result = await conn.execute(text("SELECT COUNT(*) FROM sys_user WHERE del_flag = 0"))
                count = result.scalar()
                print(f"✅ 表中有 {count} 条有效记录")

                # 检查表结构
                result = await conn.execute(text("DESCRIBE sys_user"))
                columns = result.fetchall()
                print(f"✅ 表结构完整，共有 {len(columns)} 个字段")

                return {
                    "status": "success",
                    "database": db_name,
                    "table_exists": True,
                    "record_count": count,
                    "column_count": len(columns)
                }
            else:
                print("❌ sys_user表不存在")
                print("🔧 请运行: python -m services.admin_service.create_tables")

                # 显示现有表
                result = await conn.execute(text("SHOW TABLES"))
                tables = result.fetchall()
                if tables:
                    print("现有表:")
                    for table in tables[:5]:  # 只显示前5个
                        print(f"  - {table[0]}")

                return {
                    "status": "table_missing",
                    "database": db_name,
                    "table_exists": False
                }

    except Exception as e:
        print(f"❌ MariaDB连接失败: {e}")

        # 提供故障排除建议
        if "Can't connect to MySQL server" in str(e):
            print("🔧 故障排除:")
            print("  1. 确保MariaDB服务正在运行: docker-compose ps mariadb")
            print("  2. 检查网络连接: telnet mariadb 3306")
            print("  3. 验证环境变量: echo $MARIADB_HOST")

        elif "Access denied" in str(e):
            print("🔧 故障排除:")
            print("  1. 检查数据库用户权限")
            print("  2. 验证密码是否正确")
            print("  3. 确认用户是否存在: mysql -u intel_user -p")

        elif "Unknown database" in str(e):
            print("🔧 故障排除:")
            print("  1. 确保数据库已创建: docker-compose exec mariadb mysql -e 'SHOW DATABASES;'")
            print("  2. 创建数据库: docker-compose exec mariadb mysql -e 'CREATE DATABASE intel_cw;'")

        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

    finally:
        try:
            await engine.dispose()
        except:
            ***REMOVED***


async def check_redis_connection() -> Dict[str, Any]:
    """检查Redis连接"""
    print("\n🔍 检查Redis连接...")

    try:
        import redis.asyncio as redis

        # 获取Redis配置
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_***REMOVED***word = os.getenv("REDIS_PASSWORD", "")
        redis_db = int(os.getenv("REDIS_DB", "2"))

        # 连接Redis
        if redis_***REMOVED***word:
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                ***REMOVED***word=redis_***REMOVED***word,
                db=redis_db,
                socket_connect_timeout=5
            )
        else:
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                socket_connect_timeout=5
            )

        # 测试连接
        pong = await r.ping()
        if pong:
            print("✅ Redis连接成功")

            # 检查数据库号
            current_db = await r.connection.db
            print(f"✅ 使用数据库: {current_db}")

            return {
                "status": "success",
                "database": current_db
            }

    except Exception as e:
        print(f"❌ Redis连接失败: {e}")

        if "Connection refused" in str(e):
            print("🔧 故障排除:")
            print("  1. 确保Redis服务正在运行: docker-compose ps redis")
            print("  2. 检查网络连接: telnet redis 6379")

        return {
            "status": "error",
            "error": str(e)
        }


async def check_admin_service_health() -> Dict[str, Any]:
    """检查admin服务健康状态"""
    print("\n🔍 检查admin服务健康状态...")

    try:
        # admin服务通常运行在8002端口
        admin_url = os.getenv("ADMIN_SERVICE_URL", "http://localhost:8002")

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 检查健康端点
            health_url = f"{admin_url}/health"
            response = await client.get(health_url)

            if response.status_code == 200:
                print("✅ admin服务健康检查通过")
                try:
                    health_data = response.json()
                    return {
                        "status": "success",
                        "health_data": health_data
                    }
                except:
                    return {
                        "status": "success",
                        "health_data": "无法解析JSON"
                    }
            else:
                print(f"❌ admin服务健康检查失败: {response.status_code}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "response": response.text[:200]
                }

    except httpx.RequestError as e:
        print(f"❌ 无法连接admin服务: {e}")
        print("🔧 故障排除:")
        print("  1. 确保admin服务正在运行: docker-compose ps admin-service")
        print("  2. 检查服务端口: docker-compose logs admin-service")
        print("  3. 验证环境变量: echo $ADMIN_SERVICE_URL")
        return {
            "status": "error",
            "error": str(e)
        }


async def test_admin_users_api() -> Dict[str, Any]:
    """测试admin服务的用户列表API"""
    print("\n🔍 测试admin服务用户列表API...")

    try:
        # admin服务通常运行在8002端口
        admin_url = os.getenv("ADMIN_SERVICE_URL", "http://localhost:8002")

        # 使用测试令牌（需要一个有效的JWT令牌）
        # 这里使用一个示例令牌，实际使用时需要替换为有效的令牌
        test_token = os.getenv("TEST_JWT_TOKEN", "")

        if not test_token:
            print("⚠️  未设置TEST_JWT_TOKEN环境变量，跳过API测试")
            return {"status": "skipped", "reason": "no_test_token"}

        headers = {
            "Authorization": f"Bearer {test_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 测试用户列表API
            api_url = f"{admin_url}/api/v1/users?page=0&page_size=1"
            response = await client.get(api_url, headers=headers)

            if response.status_code == 200:
                print("✅ admin服务用户列表API正常")
                try:
                    data = response.json()
                    return {
                        "status": "success",
                        "data": data
                    }
                except:
                    return {
                        "status": "success",
                        "data": "无法解析JSON"
                    }
            elif response.status_code == 401:
                print("❌ 认证失败 - 令牌无效")
                return {
                    "status": "auth_error",
                    "status_code": 401
                }
            else:
                print(f"❌ API调用失败: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"错误内容: {response.text[:200]}")

                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "response": response.text[:200]
                }

    except Exception as e:
        print(f"❌ API测试异常: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def main():
    """主函数"""
    print("🚀 admin服务启动状态检查")
    print("=" * 60)

    # 检查MariaDB连接和表状态
    mariadb_result = await check_mariadb_connection()

    # 检查Redis连接
    redis_result = await check_redis_connection()

    # 检查admin服务健康状态
    health_result = await check_admin_service_health()

    # 测试用户列表API
    api_result = await test_admin_users_api()

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 检查结果总结")
    print("=" * 60)

    checks = [
        ("MariaDB连接", mariadb_result),
        ("Redis连接", redis_result),
        ("Admin服务健康", health_result),
        ("用户列表API", api_result)
    ]

    all_***REMOVED***ed = True

    for check_name, result in checks:
        status = result.get("status", "unknown")
        if status == "success":
            print(f"✅ {check_name}: 通过")
        elif status == "skipped":
            print(f"⚠️  {check_name}: 跳过 ({result.get('reason', '未知原因')})")
        else:
            print(f"❌ {check_name}: 失败")
            all_***REMOVED***ed = False

    print("\n" + "=" * 60)

    if all_***REMOVED***ed:
        print("🎉 所有检查通过！admin服务应该可以正常工作")
        return True
    else:
        print("❌ 发现问题，请根据上述信息进行修复")
        print("\n🔧 常见修复步骤:")
        print("1. 启动基础设施服务: docker-compose up -d mariadb redis")
        print("2. 创建数据库表: python -m services.admin_service.create_tables")
        print("3. 启动admin服务: docker-compose up -d admin-service")
        print("4. 检查服务日志: docker-compose logs admin-service")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
