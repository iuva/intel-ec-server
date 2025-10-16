#!/bin/bash

###############################################################################
# 缓存清理脚本
#
# 功能：
#   - 递归清理各级目录下的缓存文件和目录
#   - 支持多种编程语言和工具的缓存
#   - 提供详细的清理报告
#   - 支持预览模式（干运行）
#
# 使用方式：
#   ./scripts/clean_cache.sh                 # 清理当前项目
#   ./scripts/clean_cache.sh --dry-run       # 预览模式
#   ./scripts/clean_cache.sh --aggressive    # 激进模式
#   ./scripts/clean_cache.sh --help          # 显示帮助
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 默认配置
DRY_RUN=false
AGGRESSIVE=false
TARGET_DIR="."
DELETED_COUNT=0
FREED_SPACE=0

# 基础缓存模式（目录和文件）
CACHE_DIRS=(
    "__pycache__"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    ".tox"
    "htmlcov"
    ".coverage"
    "build"
    "dist"
    ".build"
    "logs"
    "tmp"
    "temp"
    ".tmp"
    ".temp"
)

CACHE_FILES=(
    "*.pyc"
    "*.pyo"
    "*.pyd"
    "*.log"
    "*.swp"
    "*.swo"
    "*~"
    ".DS_Store"
    "Thumbs.db"
    "npm-debug.log"
    "yarn-error.log"
)

# 激进模式额外清理的模式
AGGRESSIVE_DIRS=(
    "node_modules"
    ".npm"
    ".yarn"
    ".pnpm-store"
    ".next"
    ".nuxt"
    ".output"
    ".vercel"
    ".cache"
    "target"
)

AGGRESSIVE_FILES=(
    "*.sqlite"
    "*.sqlite3"
    "*.db"
    "*.bak"
    "*.backup"
    "*.orig"
)

# 保护目录（永远不删除）
PROTECTED_DIRS=(
    ".git"
    ".svn"
    ".hg"
    "venv"
    "env"
    ".venv"
)

###############################################################################
# 辅助函数
###############################################################################

print_header() {
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# 获取文件或目录大小（字节）
get_size() {
    local path="$1"
    if [[ -d "$path" ]]; then
        du -sk "$path" 2>/dev/null | cut -f1 || echo "0"
    elif [[ -f "$path" ]]; then
        stat -f%z "$path" 2>/dev/null || stat -c%s "$path" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# 格式化文件大小
format_size() {
    local size=$1
    if (( size < 1024 )); then
        echo "${size}B"
    elif (( size < 1048576 )); then
        echo "$(( size / 1024 ))KB"
    elif (( size < 1073741824 )); then
        echo "$(( size / 1048576 ))MB"
    else
        echo "$(( size / 1073741824 ))GB"
    fi
}

# 检查路径是否受保护
is_protected() {
    local path="$1"
    local name=$(basename "$path")
    
    for protected in "${PROTECTED_DIRS[@]}"; do
        if [[ "$name" == "$protected" ]]; then
            return 0  # 受保护
        fi
    done
    
    return 1  # 不受保护
}

# 删除目录
delete_dir() {
    local dir="$1"
    local rel_path="${dir#$TARGET_DIR/}"
    
    if is_protected "$dir"; then
        return
    fi
    
    local size=$(get_size "$dir")
    size_kb=$((size))
    
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "  ${YELLOW}[预览]${NC} 目录: $rel_path ($(format_size $size_kb))"
    else
        if rm -rf "$dir" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} 删除目录: $rel_path ($(format_size $size_kb))"
            ((DELETED_COUNT++))
            ((FREED_SPACE+=size_kb))
        else
            print_error "无法删除目录: $rel_path"
        fi
    fi
}

# 删除文件
delete_file() {
    local file="$1"
    local rel_path="${file#$TARGET_DIR/}"
    
    local size=$(get_size "$file")
    size_kb=$((size / 1024))
    
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "  ${YELLOW}[预览]${NC} 文件: $rel_path ($(format_size $size_kb))"
    else
        if rm -f "$file" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} 删除文件: $rel_path ($(format_size $size_kb))"
            ((DELETED_COUNT++))
            ((FREED_SPACE+=size_kb))
        else
            print_error "无法删除文件: $rel_path"
        fi
    fi
}

# 清理缓存目录
clean_cache_dirs() {
    local patterns=("${CACHE_DIRS[@]}")
    
    if [[ "$AGGRESSIVE" == true ]]; then
        patterns+=("${AGGRESSIVE_DIRS[@]}")
    fi
    
    print_info "扫描缓存目录..."
    
    for pattern in "${patterns[@]}"; do
        while IFS= read -r -d '' dir; do
            delete_dir "$dir"
        done < <(find "$TARGET_DIR" -type d -name "$pattern" -print0 2>/dev/null)
    done
}

# 清理缓存文件
clean_cache_files() {
    local patterns=("${CACHE_FILES[@]}")
    
    if [[ "$AGGRESSIVE" == true ]]; then
        patterns+=("${AGGRESSIVE_FILES[@]}")
    fi
    
    print_info "扫描缓存文件..."
    
    for pattern in "${patterns[@]}"; do
        while IFS= read -r -d '' file; do
            delete_file "$file"
        done < <(find "$TARGET_DIR" -type f -name "$pattern" -print0 2>/dev/null)
    done
}

# 显示帮助信息
show_help() {
    cat << EOF
🧹 缓存清理脚本

使用方式:
    $0 [选项]

选项:
    -d, --dry-run       预览模式，显示要删除的文件但不实际删除
    -a, --aggressive    激进模式，清理更多类型的缓存（包括 node_modules）
    -p, --path PATH     指定要清理的目录路径（默认：当前目录）
    -h, --help          显示此帮助信息

示例:
    $0                      # 清理当前目录
    $0 --dry-run            # 预览模式
    $0 --aggressive         # 激进模式
    $0 --path /some/path    # 清理指定目录

清理的缓存类型:
    - Python: __pycache__, *.pyc, .pytest_cache, .mypy_cache
    - Node.js: node_modules (激进模式), *.log
    - 构建产物: build, dist, target
    - IDE: .DS_Store, *.swp, Thumbs.db
    - 临时文件: tmp, temp, *.log

保护的目录:
    .git, .svn, .hg, venv, env, .venv

EOF
}

# 显示总结
show_summary() {
    echo ""
    print_header "清理总结"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_warning "预览模式 - 未实际删除文件"
    else
        print_success "删除项目: $DELETED_COUNT"
        print_success "释放空间: $(format_size $FREED_SPACE)"
    fi
    
    echo ""
    print_success "清理完成!"
}

###############################################################################
# 主程序
###############################################################################

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -a|--aggressive)
            AGGRESSIVE=true
            shift
            ;;
        -p|--path)
            TARGET_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 检查目标目录是否存在
if [[ ! -d "$TARGET_DIR" ]]; then
    print_error "目录不存在: $TARGET_DIR"
    exit 1
fi

# 转换为绝对路径
TARGET_DIR=$(cd "$TARGET_DIR" && pwd)

# 显示配置信息
print_header "缓存清理脚本"
echo -e "📁 清理路径: ${CYAN}$TARGET_DIR${NC}"
echo -e "🔍 预览模式: ${CYAN}$([ "$DRY_RUN" == true ] && echo "是" || echo "否")${NC}"
echo -e "⚡ 激进模式: ${CYAN}$([ "$AGGRESSIVE" == true ] && echo "是" || echo "否")${NC}"
echo ""

# 确认删除（非预览模式）
if [[ "$DRY_RUN" == false ]]; then
    echo -ne "${YELLOW}⚠  确定要删除缓存文件吗? (y/N): ${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_warning "已取消操作"
        exit 0
    fi
    echo ""
fi

print_info "开始清理..."
echo ""

# 执行清理
clean_cache_dirs
clean_cache_files

# 显示总结
show_summary
