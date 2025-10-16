#!/bin/bash

# ==========================================
# Intel EC 微服务停止脚本
# ==========================================
# 用途: 停止所有微服务和基础设施组件
# 使用: ./scripts/stop_services.sh [选项]
# ==========================================

set -e

# 颜色定义
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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
Intel EC 微服务停止脚本

用途:
    停止所有微服务和基础设施组件

使用方法:
    ./scripts/stop_services.sh [选项]

选项:
    -h, --help              显示帮助信息
    -v, --volumes           同时删除数据卷
    -r, --remove-orphans    删除孤立容器
    --only <service>        只停止指定服务
    --timeout <seconds>     设置停止超时时间（默认10秒）

示例:
    ./scripts/stop_services.sh                     # 停止所有服务
    ./scripts/stop_services.sh -v                  # 停止服务并删除数据卷
    ./scripts/stop_services.sh --only mysql        # 只停止MySQL
    ./scripts/stop_services.sh --timeout 30        # 设置30秒超时

EOF
}

# 检查Docker是否运行
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker未运行"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 检查docker-compose是否安装
check_docker_compose() {
    log_info "检查Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi
    
    log_success "Docker Compose检查通过"
}

# 显示当前运行的服务
show_running_services() {
    log_info "当前运行的服务:"
    echo ""
    docker-compose ps
    echo ""
}

# 停止服务
stop_services() {
    local compose_args=""
    
    if [ -n "$TIMEOUT" ]; then
        compose_args="$compose_args -t $TIMEOUT"
    fi
    
    log_info "停止服务..."
    
    if [ -n "$ONLY_SERVICE" ]; then
        log_info "只停止服务: $ONLY_SERVICE"
        docker-compose stop $compose_args "$ONLY_SERVICE"
    else
        docker-compose stop $compose_args
    fi
    
    log_success "服务停止完成"
}

# 删除容器
remove_containers() {
    local compose_args=""
    
    if [ "$REMOVE_ORPHANS" = true ]; then
        compose_args="$compose_args --remove-orphans"
    fi
    
    if [ "$REMOVE_VOLUMES" = true ]; then
        compose_args="$compose_args -v"
    fi
    
    log_info "删除容器..."
    
    if [ -n "$ONLY_SERVICE" ]; then
        docker-compose rm -f "$ONLY_SERVICE"
    else
        docker-compose down $compose_args
    fi
    
    log_success "容器删除完成"
}

# 清理未使用的资源
cleanup_resources() {
    log_info "清理未使用的Docker资源..."
    
    # 清理未使用的网络
    docker network prune -f 2>/dev/null || true
    
    # 清理未使用的镜像（可选）
    if [ "$CLEANUP_IMAGES" = true ]; then
        log_info "清理未使用的镜像..."
        docker image prune -f 2>/dev/null || true
    fi
    
    log_success "资源清理完成"
}

# 显示停止后的状态
show_final_status() {
    log_info "检查剩余容器..."
    
    local remaining=$(docker-compose ps -q | wc -l)
    
    if [ "$remaining" -eq 0 ]; then
        log_success "所有服务已停止"
    else
        log_warning "仍有 $remaining 个容器在运行"
        docker-compose ps
    fi
}

# 显示数据卷信息
show_volume_info() {
    if [ "$REMOVE_VOLUMES" = true ]; then
        log_warning "数据卷已删除，所有数据将丢失"
    else
        log_info "数据卷已保留，重启服务时数据将恢复"
        echo ""
        log_info "数据卷列表:"
        docker volume ls | grep "intel-cw-ms" || log_info "  无相关数据卷"
    fi
}

# 主函数
main() {
    # 默认参数
    REMOVE_VOLUMES=false
    REMOVE_ORPHANS=false
    CLEANUP_IMAGES=false
    ONLY_SERVICE=""
    TIMEOUT=10
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--volumes)
                REMOVE_VOLUMES=true
                shift
                ;;
            -r|--remove-orphans)
                REMOVE_ORPHANS=true
                shift
                ;;
            --cleanup-images)
                CLEANUP_IMAGES=true
                shift
                ;;
            --only)
                ONLY_SERVICE="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示停止信息
    echo ""
    log_info "=========================================="
    log_info "Intel EC 微服务停止脚本"
    log_info "=========================================="
    echo ""
    
    # 执行停止流程
    check_docker
    check_docker_compose
    show_running_services
    
    # 确认操作
    if [ "$REMOVE_VOLUMES" = true ]; then
        log_warning "警告: 即将删除所有数据卷，数据将永久丢失！"
        read -p "确认继续? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "操作已取消"
            exit 0
        fi
    fi
    
    stop_services
    remove_containers
    cleanup_resources
    
    echo ""
    show_final_status
    show_volume_info
    
    echo ""
    log_success "停止流程完成"
    echo ""
    
    # 显示提示信息
    cat << EOF
${BLUE}提示:${NC}
  - 重新启动服务: ./scripts/start_services.sh
  - 查看日志: docker-compose logs [service_name]
  - 清理所有资源: docker-compose down -v --remove-orphans

EOF
}

# 执行主函数
main "$@"
