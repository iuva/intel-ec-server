#!/bin/bash

# Pre-commit 钩子安装脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 主函数
main() {
    print_separator
    print_title "Pre-commit 钩子安装"
    print_separator
    echo ""
    
    # 检查是否安装了 pre-commit
    if ! command -v pre-commit &> /dev/null; then
        print_warning "Pre-commit 未安装，正在安装..."
        pip install pre-commit
        print_success "Pre-commit 安装完成"
    else
        print_success "Pre-commit 已安装"
    fi
    echo ""
    
    # 安装 Git 钩子
    print_title "安装 Git 钩子..."
    echo ""
    pre-commit install
    print_success "Git 钩子安装完成"
    echo ""
    
    # 运行一次检查
    print_title "运行初始检查（可能需要一些时间）..."
    echo ""
    print_warning "首次运行会下载和安装钩子依赖..."
    echo ""
    
    if pre-commit run --all-files; then
        print_success "所有检查通过！"
    else
        print_warning "存在一些问题，已自动修复部分问题"
        print_warning "请查看上述输出，手动修复剩余问题"
    fi
    echo ""
    
    print_separator
    print_title "Pre-commit 使用说明"
    print_separator
    echo ""
    echo "1. 提交代码时会自动运行检查"
    echo "2. 手动运行所有检查: pre-commit run --all-files"
    echo "3. 手动运行特定检查: pre-commit run <hook-id>"
    echo "4. 跳过检查提交: git commit --no-verify"
    echo "5. 更新钩子: pre-commit autoupdate"
    echo ""
    print_separator
}

# 运行主函数
main
