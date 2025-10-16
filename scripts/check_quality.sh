#!/bin/bash

# 代码质量检查脚本
# 集成 Ruff、MyPy、Black 检查

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查目录
SERVICES_DIR="services"
SHARED_DIR="shared"

# 统计变量
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 打印分隔线
print_separator() {
    echo -e "${BLUE}========================================${NC}"
}

# 打印标题
print_title() {
    echo -e "${BLUE}$1${NC}"
}

# 打印成功消息
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 打印错误消息
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 打印警告消息
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 运行检查
run_check() {
    local check_name=$1
    local check_command=$2
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    print_separator
    print_title "运行检查: $check_name"
    echo ""
    
    if eval "$check_command"; then
        print_success "$check_name 检查通过"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        print_error "$check_name 检查失败"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# 主函数
main() {
    print_separator
    print_title "Intel EC 微服务项目 - 代码质量检查"
    print_separator
    echo ""
    
    # 检查是否安装了必要的工具
    print_title "检查工具安装状态..."
    echo ""
    
    if ! command -v ruff &> /dev/null; then
        print_error "Ruff 未安装，请运行: pip install ruff"
        exit 1
    fi
    print_success "Ruff 已安装（代码检查 + 格式化 + 导入排序）"
    
    if ! command -v mypy &> /dev/null; then
        print_error "MyPy 未安装，请运行: pip install mypy"
        exit 1
    fi
    print_success "MyPy 已安装"
    
    echo ""
    
    # 1. Ruff 代码检查
    run_check "Ruff 代码检查" "ruff check $SERVICES_DIR/ $SHARED_DIR/" || true
    echo ""
    
    # 2. Ruff 格式检查（替代 Black）
    run_check "Ruff 格式检查" "ruff format --check $SERVICES_DIR/ $SHARED_DIR/" || true
    echo ""
    
    # 3. MyPy 类型检查（仅检查shared模块，服务模块由于命名问题跳过）
    run_check "MyPy 类型检查" "mypy $SHARED_DIR/" || true
    echo ""
    
    # 打印总结
    print_separator
    print_title "检查总结"
    print_separator
    echo ""
    echo -e "总检查数: ${BLUE}$TOTAL_CHECKS${NC}"
    echo -e "通过: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "失败: ${RED}$FAILED_CHECKS${NC}"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        print_success "所有代码质量检查通过！"
        print_separator
        exit 0
    else
        print_error "存在 $FAILED_CHECKS 个检查失败"
        print_warning "请修复上述问题后重新运行检查"
        print_separator
        exit 1
    fi
}

# 运行主函数
main
