#!/bin/bash

# ==========================================
# Intel EC 微服务启动脚本
# ==========================================
# 用途: 启动所有微服务和基础设施组件
# 使用: ./scripts/start_services.sh [选项]
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
Intel EC 微服务启动脚本

用途:
    启动所有微服务和基础设施组件

使用方法:
    ./scripts/start_services.sh [选项]

选项:
    -h, --help              显示帮助信息
    -b, --build             重新构建镜像
    -d, --detach            后台运行（默认）
    -f, --foreground        前台运行
    --no-cache              构建时不使用缓存
    --pull                  构建前拉取最新基础镜像
    --only <service>        只启动指定服务
    --skip <service>        跳过指定服务

示例:
    ./scripts/start_services.sh                    # 启动所有服务
    ./scripts/start_services.sh -b                 # 重新构建并启动
    ./scripts/start_services.sh --only mysql       # 只启动MySQL
    ./scripts/start_services.sh --skip jaeger      # 跳过Jaeger服务

EOF
}

# 检查Docker是否运行
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker未运行，请启动Docker"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 检查docker-compose是否安装
check_docker_compose() {
    log_info "检查Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "Docker Compose检查通过"
}

# 检查.env文件
check_env_file() {
    log_info "检查环境变量配置..."
    
    if [ ! -f .env ]; then
        log_warning ".env文件不存在，从.env.example创建..."
        cp .env.example .env
        log_success "已创建.env文件，请根据需要修改配置"
    else
        log_success "环境变量配置文件存在"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p infrastructure/mysql/init
    mkdir -p logs
    
    log_success "目录创建完成"
}

# 清理旧容器和网络
cleanup_old_resources() {
    log_info "清理旧的容器和网络..."
    
    # 停止并删除旧容器
    docker-compose down --remove-orphans 2>/dev/null || true
    
    log_success "清理完成"
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
    local compose_args=""
    
    if [ "$DETACH" = true ]; then
        compose_args="$compose_args -d"
    fi
    
    log_info "启动服务..."
    
    if [ -n "$ONLY_SERVICE" ]; then
        log_info "只启动服务: $ONLY_SERVICE"
        docker-compose up $compose_args "$ONLY_SERVICE"
    elif [ -n "$SKIP_SERVICE" ]; then
        log_info "跳过服务: $SKIP_SERVICE"
        # 获取所有服务列表
        all_services=$(docker-compose config --services)
        # 过滤掉要跳过的服务
        services_to_start=$(echo "$all_services" | grep -v "^$SKIP_SERVICE$")
        docker-compose up $compose_args $services_to_start
    else
        docker-compose up $compose_args
    fi
    
    log_success "服务启动完成"
}

# 等待服务健康检查
wait_for_health() {
    if [ "$DETACH" = false ]; then
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

# 显示服务状态
show_status() {
    log_info "服务状态:"
    echo ""
    docker-compose ps
    echo ""
}

# 显示访问信息
show_access_info() {
    cat << EOF

${GREEN}==========================================
服务启动成功！
==========================================${NC}

${BLUE}基础设施服务:${NC}
  - MariaDB:        http://localhost:3306
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

${BLUE}健康检查:${NC}
  - Gateway:        http://localhost:8000/health
  - Auth Service:   http://localhost:8001/health
  - Admin Service:  http://localhost:8002/health
  - Host Service:   http://localhost:8003/health

${YELLOW}提示:${NC}
  - 查看日志: docker-compose logs -f [service_name]
  - 停止服务: ./scripts/stop_services.sh
  - 重启服务: ./scripts/restart_services.sh

EOF
}

# 主函数
main() {
    # 默认参数
    BUILD=false
    DETACH=true
    NO_CACHE=false
    PULL=false
    ONLY_SERVICE=""
    SKIP_SERVICE=""
    
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
            -d|--detach)
                DETACH=true
                shift
                ;;
            -f|--foreground)
                DETACH=false
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
            --skip)
                SKIP_SERVICE="$2"
                shift 2
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示启动信息
    echo ""
    log_info "==========================================
    log_info "Intel EC 微服务启动脚本"
    log_info "=========================================="
    echo ""
    
    # 执行启动流程
    check_docker
    check_docker_compose
    check_env_file
    create_directories
    
    if [ "$BUILD" = true ]; then
        cleanup_old_resources
        build_images
    fi
    
    start_services
    
    if [ "$DETACH" = true ]; then
        wait_for_health
        show_status
        show_access_info
    fi
    
    log_success "启动流程完成"
}

# 执行主函数
main "$@"
