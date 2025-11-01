#!/bin/bash
# 释放主机 API 测试脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# API 基础 URL
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_ENDPOINT="${BASE_URL}/api/v1/host/hosts/release"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}释放主机 API 测试${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# 1. 获取 JWT Token
echo -e "${GREEN}步骤 1: 获取 JWT Token${NC}"
echo "正在登录..."

TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "***REMOVED***" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=***REMOVED***")

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

# 2. 测试释放主机（示例参数）
echo -e "${GREEN}步骤 2: 测试释放主机${NC}"
echo "请求 URL: $API_ENDPOINT"

# 默认参数，可以通过环境变量修改
USER_ID="${USER_ID:-adb1852278641262sdf097}"
HOST_LIST="${HOST_LIST:-1852278641262084097,1852278641262084098}"

# 将逗号分隔的 host_list 转换为 JSON 数组
IFS=',' read -ra HOSTS <<< "$HOST_LIST"
HOST_JSON="["
for i in "${!HOSTS[@]}"; do
  if [ $i -gt 0 ]; then
    HOST_JSON+=","
  fi
  HOST_JSON+="\"${HOSTS[$i]}\""
done
HOST_JSON+="]"

echo "测试参数:"
echo "  user_id: $USER_ID"
echo "  host_list: $HOST_JSON"
echo ""

# 构建请求 Body
REQUEST_BODY=$(cat <<EOF
{
  "user_id": "$USER_ID",
  "host_list": $HOST_JSON
}
EOF
)

echo "请求 Body:"
echo "$REQUEST_BODY" | jq '.' 2>/dev/null || echo "$REQUEST_BODY"
echo ""

echo "发送请求..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_ENDPOINT" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")

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
  
  # 提取更新数量（逻辑删除）
  UPDATED_COUNT=$(echo "$BODY" | jq -r '.updated_count' 2>/dev/null || echo "unknown")
  echo -e "${GREEN}更新记录数（逻辑删除）: $UPDATED_COUNT${NC}"
  
  if [ "$UPDATED_COUNT" = "0" ]; then
    echo -e "${YELLOW}提示: 没有更新任何记录（可能记录不存在或已删除）${NC}"
  else
    echo -e "${GREEN}提示: 成功逻辑删除 $UPDATED_COUNT 条记录（del_flag = 1）${NC}"
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
echo "  1. 修改 user_id: USER_ID=your_user_id ./scripts/test_release_hosts_api.sh"
echo "  2. 修改 host_list: HOST_LIST=host1,host2,host3 ./scripts/test_release_hosts_api.sh"
echo "  3. 修改 API 地址: BASE_URL=http://your-host:port ./scripts/test_release_hosts_api.sh"
echo ""

# 4. 其他测试场景示例
echo "其他测试场景:"
echo ""
echo "# 测试释放单个主机"
echo "HOST_LIST=1852278641262084097 ./scripts/test_release_hosts_api.sh"
echo ""
echo "# 测试释放多个主机"
echo "HOST_LIST=host1,host2,host3,host4 ./scripts/test_release_hosts_api.sh"
echo ""
echo "# 测试不同用户"
echo "USER_ID=another_user HOST_LIST=host1,host2 ./scripts/test_release_hosts_api.sh"
echo ""

# 5. 验证数据库（可选）
echo "验证数据库记录已逻辑删除（可选）:"
echo ""
echo "docker exec -it intel-mariadb mysql -u root -p"
echo "USE intel_cw_db;"
echo "# 查看被逻辑删除的记录（del_flag = 1）"
echo "SELECT * FROM host_exec_log WHERE user_id = '$USER_ID' AND host_id IN ($HOST_LIST) AND del_flag = 1;"
echo ""

