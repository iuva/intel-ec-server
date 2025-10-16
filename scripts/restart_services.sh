#!/bin/bash

# ==========================================
# Intel EC 微服务重启脚本
# ==========================================
# 用途: 重启所有微服务和基础设施组件
# 使用: ./scripts/restart_services.sh [选项]
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
Intel EC 微服务重启脚本

用途:
    重启所有微服务和基础设施组件

使用方法:
    ./scripts/restart_services.sh [选项]

选项:
    -h, --help              显示帮助信息
    -b, --build             重新构建镜像
    --no-cache              构建时不使用缓存
    --pull                  构建前拉取最新基础镜像
    --only <service>        只重启指定服务
    --timeout <seconds>     设置停止超时时间（默认10秒）
    --quick                 快速重启（不等待健康检查）

示例:
    ./scripts/restart_services.sh                  # 重启所有服务
    ./scripts/restart_services.sh -b               # 重新构建并重启
    ./scripts/restart_services.sh --only mysql     # 只重启MySQL
    ./scripts/restart_services.sh --quick          # 快速重启

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

# 显示当前服务状态
show_current_status() {
    log_info "当前服务状态:"
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

# 构建镜像
build_images() {
    local build_args=""
    
    if [ "$NO_CACHE" = true ]; then
        build_args="$build_args --no-cache"
    fi
    
    if [ "$PULL" = true ]; then
        build_args="$build_args --pull"
    fi
    
    log_info "开始构建Docker镜像..."
    
    if [ -n "$ONLY_SERVICE" ]; then
        log_info "只构建服务: $ONLY_SERVICE"
        docker-compose build $build_args "$ONLY_SERVICE"
    else
        docker-compose build $build_args
    fi
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    if [ -n "$ONLY_SERVICE" ]; then
        log_info "只启动服务: $ONLY_SERVICE"
        docker-compose up -d "$ONLY_SERVICE"
    else
        docker-compose up -d
    fi
    
    log_success "服务启动完成"
}

# 等待服务健康检查
wait_for_health() {
    if [ "$QUICK" = true ]; then
        log_info "跳过健康检查（快速模式）"
        return
    fi
    
    log_info "等待服务健康检查..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # 检查所有服务的健康状态
        local unhealthy=$(docker-compose ps | grep -E "(starting|unhealthy)" | wc -l)
        
        if [ "$unhealthy" -eq 0 ]; then
            log_success "所有服务健康检查通过"
            return
        fi
        
        log_info "等待服务启动... ($attempt/$max_attempts)"
        sleep 5
    done
    
    log_warning "部分服务可能未完全启动，请检查服务状态"
}

# 显示重启后的状态
show_final_status() {
    log_info "重启后服务状态:"
    echo ""
    docker-compose ps
    echo ""
}

# 显示访问信息
show_access_info() {
    cat << EOF

${GREEN}==========================================
服务重启成功！
==========================================${NC}

${BLUE}基础设施服务:${NC}
  - MySQL:          http://localhost:3306
  - Redis:          http://localhost:6379
  - Nacos:          http://localhost:8848
  - Jaeger UI:      http://localhost:16686

${BLUE}微服务:${NC}
  - Gateway:        http://localhost:8000
  - Auth Service:   http://localhost:8001
  - Admin Service:  http://localhost:8002
  - Host Service:   http://localhost:8003

${BLUE}API文档:${NC}
  - Gateway:        http://localhost:8000/docs
  - Auth Service:   http://localhost:8001/docs
  - Admin Service:  http://localhost:8002/docs
  - Host Service:   http://localhost:8003/docs

${YELLOW}提示:${NC}
  - 查看日志: docker-compose logs -f [service_name]
  - 停止服务: ./scripts/stop_services.sh

EOF
}

# 主函数
main() {
    # 默认参数
    BUILD=false
    NO_CACHE=false
    PULL=false
    ONLY_SERVICE=""
    TIMEOUT=10
    QUICK=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -b|--build)
                BUILD=true
                shift
                ;;
            --no-cache)
                NO_CACHE=true
                shift
                ;;
            --pull)
                PULL=true
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
            --quick)
                QUICK=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示重启信息
    echo ""
    log_info "=========================================="
    log_info "Intel EC 微服务重启脚本"
    log_info "=========================================="
    echo ""
    
    # 执行重启流程
    check_docker
    check_docker_compose
    show_current_status
    
    stop_services
    
    if [ "$BUILD" = true ]; then
        build_images
    fi
    
    start_services
    wait_for_health
    
    echo ""
    show_final_status
    show_access_info
    
    log_success "重启流程完成"
}

# 执行主函数
main "$@"
