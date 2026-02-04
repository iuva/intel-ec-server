#!/bin/bash
# 重试 VNC 列表 API 测试脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# API 基础 URL
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_ENDPOINT="${BASE_URL}/api/v1/host/hosts/retry-vnc"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}重试 VNC 列表 API 测试${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# 1. 获取 JWT Token
echo -e "${GREEN}步骤 1: 获取 JWT Token${NC}"
echo "正在登录..."

ADMIN_CLIENT_SECRET="${ADMIN_CLIENT_SECRET:-admin_secret}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-***REMOVED***}"

if [ "$ADMIN_CLIENT_SECRET" = "admin_secret" ]; then
    echo -e "${YELLOW}提示: 使用默认 admin_client_secret (可通过 ADMIN_CLIENT_SECRET 环境变量设置)${NC}"
fi

TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "admin_client:$ADMIN_CLIENT_SECRET" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=$ADMIN_PASSWORD")

# 提取 access_token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"\(.*\)"/\1/')

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}错误: 无法获取 Token${NC}"
  echo "响应内容: $TOKEN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✓ Token 获取成功${NC}"
echo "Token: ${ACCESS_TOKEN:0:50}..."
echo ""

# 2. 测试获取重试 VNC 列表（示例 user_id）
echo -e "${GREEN}步骤 2: 测试获取重试 VNC 列表${NC}"
echo "请求 URL: $API_ENDPOINT"

# 默认 user_id，可以通过环境变量修改
USER_ID="${USER_ID:-1852278641262084097}"

echo "测试参数:"
echo "  user_id: $USER_ID"
echo ""

echo "发送请求..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_ENDPOINT" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\"}")

# 提取 HTTP 状态码和响应体
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP 状态码: $HTTP_STATUS"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
  echo -e "${GREEN}✓ 请求成功！${NC}"
  echo ""
  echo "响应内容:"
  echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
  echo ""
  
  # 提取主机总数
  TOTAL=$(echo "$BODY" | jq -r '.total' 2>/dev/null || echo "unknown")
  echo -e "${GREEN}主机总数: $TOTAL${NC}"
  
  if [ "$TOTAL" = "0" ]; then
    echo -e "${YELLOW}提示: 没有需要重试的 VNC 连接${NC}"
  else
    echo ""
    echo "主机列表:"
    echo "$BODY" | jq -r '.hosts[] | "  - Host ID: \(.host_id), IP: \(.host_ip), User: \(.user_name)"' 2>/dev/null || echo "  解析失败"
  fi
else
  echo -e "${RED}✗ 请求失败！${NC}"
  echo ""
  echo "错误响应:"
  echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
fi

echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}测试完成${NC}"
echo -e "${YELLOW}========================================${NC}"

# 3. 显示使用提示
echo ""
echo "使用提示:"
echo "  1. 修改 user_id: USER_ID=your_user_id ./scripts/test_retry_vnc_api.sh"
echo "  2. 修改 API 地址: BASE_URL=http://your-host:port ./scripts/test_retry_vnc_api.sh"
echo ""

# 4. 其他测试场景示例
echo "其他测试场景:"
echo ""
echo "# 测试不存在的用户"
echo "USER_ID=nonexistent_user ./scripts/test_retry_vnc_api.sh"
echo ""
echo "# 测试多个用户"
echo "for uid in user1 user2 user3; do"
echo "  USER_ID=\$uid ./scripts/test_retry_vnc_api.sh"
echo "done"
echo ""

