#!/bin/bash

# 测试OAuth2路径修复
echo "🔧 测试OAuth2路径修复"
echo "======================="

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

# 测试OAuth2管理后台令牌
echo ""
print_info "测试OAuth2管理后台令牌..."

CLIENT_ID="admin_client"
CLIENT_SECRET="admin_secret"
AUTH_HEADER=$(echo -n "${CLIENT_ID}:${CLIENT_SECRET}" | base64)

response=$(curl -s -X POST http://localhost:8000/api/v1/auth/oauth2/admin/token \
  -H "Authorization: Basic ${AUTH_HEADER}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=***REMOVED***&scope=admin")

if echo "$response" | grep -q '"code": 200'; then
    print_status "OAuth2管理后台令牌获取成功"
    echo "$response" | jq '.data.access_token // .data' 2>/dev/null || echo "$response"
else
    print_error "OAuth2管理后台令牌获取失败"
    echo "响应: $response"
fi

# 测试令牌内省
echo ""
print_info "测试令牌内省..."

if echo "$response" | grep -q '"code": 200'; then
    access_token=$(echo "$response" | jq -r '.data.access_token' 2>/dev/null)

    if [ "$access_token" != "null" ] && [ -n "$access_token" ]; then
        introspect_response=$(curl -s -X POST http://localhost:8000/api/v1/auth/oauth2/introspect \
          -H "Content-Type: application/x-www-form-urlencoded" \
          -d "token=${access_token}")

        if echo "$introspect_response" | grep -q '"active": true'; then
            print_status "令牌内省验证成功"
        else
            print_error "令牌内省验证失败"
            echo "响应: $introspect_response"
        fi
    else
        print_error "无法获取访问令牌"
    fi
else
    print_error "跳过令牌内省测试（令牌获取失败）"
fi

echo ""
print_info "OAuth2路径修复测试完成"
