#!/bin/bash

# 测试OAuth 2.0端点的脚本
# Test OAuth 2.0 endpoints

set -e

echo "🔐 测试OAuth 2.0认证端点"
echo "=========================="

# 配置
GATEWAY_URL="http://localhost:8000"
AUTH_SERVICE_URL="http://localhost:8001"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 检查服务状态
check_services() {
    print_info "检查服务状态..."

    # 检查网关服务
    if curl -s --max-time 5 "${GATEWAY_URL}/health" > /dev/null 2>&1; then
        print_status "网关服务运行正常"
    else
        print_error "网关服务不可用"
        exit 1
    fi

    # 检查认证服务
    if curl -s --max-time 5 "${AUTH_SERVICE_URL}/health" > /dev/null 2>&1; then
        print_status "认证服务运行正常"
    else
        print_error "认证服务不可用"
        exit 1
    fi
}

# 测试管理后台令牌
test_admin_token() {
    print_info "测试管理后台令牌端点..."

    # 准备测试数据
    CLIENT_ID="admin_client"
    CLIENT_SECRET="admin_secret"
    USERNAME="admin"
    PASSWORD="***REMOVED***"

    # Base64编码认证头
    AUTH_HEADER=$(echo -n "${CLIENT_ID}:${CLIENT_SECRET}" | base64)

    # 发送请求
    response=$(curl -s -X POST "${GATEWAY_URL}/api/v1/auth/oauth2/admin/token" \
        -H "Authorization: Basic ${AUTH_HEADER}" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=***REMOVED***word&username=${USERNAME}&***REMOVED***word=${PASSWORD}&scope=admin")

    # 解析响应
    if echo "$response" | jq -e '.code == 200' > /dev/null 2>&1; then
        print_status "管理后台令牌获取成功"

        # 提取访问令牌
        access_token=$(echo "$response" | jq -r '.data.access_token')
        if [ "$access_token" != "null" ] && [ -n "$access_token" ]; then
            print_status "访问令牌已获取"
            echo "$access_token" > /tmp/access_token.txt
        else
            print_error "无法提取访问令牌"
        fi
    else
        print_error "管理后台令牌获取失败"
        echo "响应: $response"
        return 1
    fi
}

# 测试令牌验证
test_token_introspect() {
    print_info "测试令牌验证..."

    if [ ! -f /tmp/access_token.txt ]; then
        print_error "没有可用的访问令牌"
        return 1
    fi

    access_token=$(cat /tmp/access_token.txt)

    # 发送内省请求
    response=$(curl -s -X POST "${GATEWAY_URL}/api/v1/auth/oauth2/introspect" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${access_token}")

    if echo "$response" | jq -e '.code == 200 and .data.active == true' > /dev/null 2>&1; then
        print_status "令牌验证成功"
    else
        print_error "令牌验证失败"
        echo "响应: $response"
        return 1
    fi
}

# 测试设备令牌
test_device_token() {
    print_info "测试设备令牌端点..."

    CLIENT_ID="device_client"
    CLIENT_SECRET="device_secret"
    DEVICE_ID="device001"
    DEVICE_SECRET="device_secret123"

    # Base64编码认证头
    AUTH_HEADER=$(echo -n "${CLIENT_ID}:${CLIENT_SECRET}" | base64)

    # 发送请求
    response=$(curl -s -X POST "${GATEWAY_URL}/api/v1/auth/oauth2/device/token" \
        -H "Authorization: Basic ${AUTH_HEADER}" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=client_credentials&device_id=${DEVICE_ID}&device_secret=${DEVICE_SECRET}&scope=device")

    if echo "$response" | jq -e '.code == 200' > /dev/null 2>&1; then
        print_status "设备令牌获取成功"
    else
        print_warning "设备令牌获取失败（可能是设备不存在）"
        echo "响应: $response"
    fi
}

# 测试直接访问认证服务
test_direct_auth_service() {
    print_info "测试直接访问认证服务..."

    response=$(curl -s "${AUTH_SERVICE_URL}/api/v1/oauth2/admin/token" \
        -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=***REMOVED***")

    if echo "$response" | jq -e '.code == 200' > /dev/null 2>&1; then
        print_status "直接访问认证服务成功"
    else
        print_error "直接访问认证服务失败"
        echo "响应: $response"
    fi
}

# 清理临时文件
cleanup() {
    rm -f /tmp/access_token.txt
}

# 主函数
main() {
    echo "开始OAuth 2.0端点测试..."
    echo ""

    # 检查依赖
    if ! command -v curl &> /dev/null; then
        print_error "需要安装curl"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        print_error "需要安装jq"
        exit 1
    fi

    # 注册清理函数
    trap cleanup EXIT

    # 执行测试
    check_services
    echo ""

    test_admin_token
    echo ""

    if [ -f /tmp/access_token.txt ]; then
        test_token_introspect
        echo ""
    fi

    test_device_token
    echo ""

    test_direct_auth_service
    echo ""

    print_status "OAuth 2.0端点测试完成！"
}

# 执行主函数
main "$@"
