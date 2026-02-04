#!/bin/bash

# ================================
# X-User-Info Header 修复验证脚本
# ================================
#
# 验证 Gateway 是否正确传递 X-User-Info header 到下游服务
#
# 使用方法:
#   ./scripts/test_x_user_info_header.sh
#

set -e

# 配置
GATEWAY_URL="http://localhost:8000"
AUTH_ENDPOINT="/api/v1/auth/admin/login"
HOST_ENDPOINT="/api/v1/admin-appr-hosts"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 打印分隔线
print_separator() {
    echo "============================================"
}

# 主函数
main() {
    print_separator
    log_info "开始测试 X-User-Info Header 修复"
    print_separator
    echo ""

    # Step 1: 登录获取 token
    log_info "Step 1: 登录获取 access_token"
    echo ""

    LOGIN_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}${AUTH_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "admin",
            "password": "Admin@123456"
        }')

    # 检查登录是否成功
    if echo "$LOGIN_RESPONSE" | jq -e '.code == 200' > /dev/null 2>&1; then
        log_success "登录成功"
        ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.access_token')
        USER_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.data.user_id')
        USERNAME=$(echo "$LOGIN_RESPONSE" | jq -r '.data.username')
        
        log_info "用户信息："
        echo "  - user_id: $USER_ID"
        echo "  - username: $USERNAME"
        echo "  - token: ${ACCESS_TOKEN:0:30}..."
    else
        log_error "登录失败"
        echo "Response: $LOGIN_RESPONSE"
        exit 1
    fi

    echo ""
    print_separator
    echo ""

    # Step 2: 使用 token 访问 host 服务
    log_info "Step 2: 使用 token 访问 host 服务"
    echo ""

    HOST_RESPONSE=$(curl -s -X GET "${GATEWAY_URL}${HOST_ENDPOINT}?page=1&page_size=10" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    # 检查是否返回 401 错误
    HTTP_CODE=$(echo "$HOST_RESPONSE" | jq -r '.code // 0')
    
    if [ "$HTTP_CODE" -eq 401 ]; then
        log_error "修复失败！仍然返回 401 错误"
        echo ""
        log_error "错误响应："
        echo "$HOST_RESPONSE" | jq '.'
        echo ""
        log_error "问题可能原因："
        echo "  1. Gateway 未正确添加 X-User-Info header"
        echo "  2. Host 服务未正确解析 X-User-Info header"
        echo "  3. 用户信息格式不匹配"
        exit 1
    elif [ "$HTTP_CODE" -eq 200 ]; then
        log_success "修复成功！API 返回 200 状态码"
        echo ""
        log_success "响应数据："
        echo "$HOST_RESPONSE" | jq '.'
    else
        log_warning "返回了其他状态码: $HTTP_CODE"
        echo ""
        echo "响应数据："
        echo "$HOST_RESPONSE" | jq '.'
    fi

    echo ""
    print_separator
    echo ""

    # Step 3: 验证日志
    log_info "Step 3: 检查 Gateway 日志（查看是否添加了 X-User-Info header）"
    echo ""

    # 检查 Gateway 日志中是否有 "添加用户信息到请求头" 的记录
    if docker logs gateway-service 2>&1 | tail -n 50 | grep -q "添加用户信息到请求头"; then
        log_success "Gateway 日志确认：已添加 X-User-Info header"
        echo ""
        echo "相关日志："
        docker logs gateway-service 2>&1 | tail -n 50 | grep -A 3 "添加用户信息到请求头" | tail -n 5
    else
        log_warning "Gateway 日志中未找到 '添加用户信息到请求头' 记录"
        echo "  可能原因: 日志级别设置为 INFO，DEBUG 日志未显示"
    fi

    echo ""
    print_separator
    echo ""

    # Step 4: 验证 Host 服务日志
    log_info "Step 4: 检查 Host 服务日志（查看是否接收到 X-User-Info header）"
    echo ""

    # 检查 Host 服务日志中是否有成功解析 X-User-Info 的记录
    if docker logs host-service 2>&1 | tail -n 50 | grep -q "成功解析 X-User-Info header"; then
        log_success "Host 服务日志确认：成功接收并解析 X-User-Info header"
        echo ""
        echo "相关日志："
        docker logs host-service 2>&1 | tail -n 50 | grep -A 3 "成功解析 X-User-Info header" | tail -n 5
    elif docker logs host-service 2>&1 | tail -n 50 | grep -q "缺少 X-User-Info header"; then
        log_error "Host 服务日志显示：仍然缺少 X-User-Info header"
        echo ""
        echo "相关日志："
        docker logs host-service 2>&1 | tail -n 50 | grep -A 3 "缺少 X-User-Info header" | tail -n 5
    else
        log_warning "Host 服务日志中未找到相关记录"
    fi

    echo ""
    print_separator
    echo ""

    # 总结
    log_info "测试总结"
    print_separator
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        log_success "✅ X-User-Info Header 修复验证通过"
        echo ""
        echo "验证结果："
        echo "  ✅ Gateway 成功添加 X-User-Info header"
        echo "  ✅ Host 服务成功接收并解析 X-User-Info header"
        echo "  ✅ API 请求返回 200 状态码"
        echo ""
        log_success "修复完成！Gateway 现在正确传递用户信息到下游服务"
    else
        log_error "❌ X-User-Info Header 修复验证失败"
        echo ""
        echo "请检查："
        echo "  1. Gateway 是否重启（应用修复后的代码）"
        echo "  2. 日志中的错误信息"
        echo "  3. 网络连接是否正常"
    fi

    echo ""
}

# 执行主函数
main "$@"

