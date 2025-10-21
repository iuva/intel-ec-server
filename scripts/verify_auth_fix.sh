#!/bin/bash

# 验证 Gateway Token 认证修复
# 使用方法: ./scripts/verify_auth_fix.sh

set -e

echo "=================================="
echo "🔍 验证 Gateway Token 认证修复"
echo "=================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查 Gateway Service 是否运行
echo "第1步: 检查 Gateway Service..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Gateway Service 未运行 (http://localhost:8000/health)${NC}"
    echo "   请启动 Gateway Service"
    exit 1
fi
echo -e "${GREEN}✅ Gateway Service 运行正常${NC}"

# 2. 检查 Auth Service 是否运行
echo ""
echo "第2步: 检查 Auth Service..."
if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Auth Service 未运行 (http://localhost:8001/health)${NC}"
    echo "   请启动 Auth Service"
    exit 1
fi
echo -e "${GREEN}✅ Auth Service 运行正常${NC}"

# 3. 检查 introspect 端点是否存在
echo ""
echo "第3步: 检查 introspect 端点..."
INTROSPECT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8001/api/v1/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "test_token"}')

HTTP_CODE=$(echo "$INTROSPECT_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$INTROSPECT_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "405" ] || [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✅ Introspect 端点存在 (状态码: $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Introspect 端点不存在或无法访问 (状态码: $HTTP_CODE)${NC}"
    echo "   响应: $RESPONSE_BODY"
    exit 1
fi

# 4. 获取 token
echo ""
echo "第4步: 获取 token..."
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/device/login \
  -H "Content-Type: application/json" \
  -d '{"mg_id": "test_device_001", "host_ip": "127.0.0.1", "username": "testuser"}')

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ 无法获取 token${NC}"
    echo "   响应: $TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ 成功获取 token${NC}"
echo "   Token (前50个字符): ${TOKEN:0:50}..."

# 5. 使用 token 验证认证
echo ""
echo "第5步: 通过 Gateway 使用 token 验证..."
AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/v1/admin/users?page=1 \
  -H "Authorization: Bearer $TOKEN")

AUTH_HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n 1)
AUTH_BODY=$(echo "$AUTH_RESPONSE" | head -n -1)

if [ "$AUTH_HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Token 认证成功！可以访问受保护资源${NC}"
    echo -e "${GREEN}   状态码: $AUTH_HTTP_CODE${NC}"
else
    echo -e "${YELLOW}⚠️  Token 认证返回状态码: $AUTH_HTTP_CODE${NC}"
    if [ "$AUTH_HTTP_CODE" = "401" ]; then
        echo -e "${RED}   这表示认证仍然失败${NC}"
        echo -e "${YELLOW}   可能原因:${NC}"
        echo "   1. Gateway Service 还在使用旧代码，需要重启"
        echo "   2. Auth Service 的 introspect 端点有问题"
        echo ""
        echo "   请执行:"
        echo "   - 停止 Gateway Service (Ctrl+C)"
        echo "   - 重新启动 Gateway Service"
        exit 1
    fi
fi

echo ""
echo "=================================="
echo -e "${GREEN}🎉 所有检查通过！Token 认证已修复${NC}"
echo "=================================="
