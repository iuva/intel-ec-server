#!/bin/bash

# 代码质量自动修复脚本
# 自动修复 Ruff 和 Black 可以修复的问题

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

# 打印警告消息
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 主函数
main() {
    print_separator
    print_title "Intel EC 微服务项目 - 代码质量自动修复"
    print_separator
    echo ""
    
    # 1. Ruff 自动修复（代码检查 + 导入排序）
    print_title "1. 运行 Ruff 自动修复..."
    echo ""
    ruff check --fix $SERVICES_DIR/ $SHARED_DIR/
    print_success "Ruff 自动修复完成"
    echo ""
    
    # 2. Ruff 格式化（替代 Black）
    print_title "2. 运行 Ruff 格式化..."
    echo ""
    ruff format $SERVICES_DIR/ $SHARED_DIR/
    print_success "Ruff 格式化完成"
    echo ""
    
    print_separator
    print_success "代码质量自动修复完成！"
    print_warning "请运行 'bash scripts/check_quality.sh' 验证修复结果"
    print_separator
}

# 运行主函数
main
