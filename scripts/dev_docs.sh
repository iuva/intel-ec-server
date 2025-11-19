#!/bin/bash

# 开发环境快速启动服务并生成API文档
# Quick start services and generate API documentation for development

set -e

echo "🚀 Intel EC 微服务开发环境启动与文档生成"
echo "=============================================="

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 服务配置
SERVICES=(
    "gateway-service:8000:网关服务"
    "auth-service:8001:认证服务"
    "host-service:8003:主机服务"
)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查 Docker 和 docker-compose
check_docker() {
    print_step "检查 Docker 环境..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose 未安装，请先安装 docker-compose"
        exit 1
    fi

    print_status "Docker 环境检查通过"
}

# 启动基础设施服务
start_infrastructure() {
    print_step "启动基础设施服务 (MySQL, Redis, Nacos, Jaeger, Prometheus, Grafana)..."

    # 检查是否已有运行的容器
    if docker-compose ps | grep -q "Up"; then
        print_warning "检测到已有运行的服务，跳过启动"
        return
    fi

    # 启动基础设施
    docker-compose up -d mysql redis nacos jaeger prometheus grafana

    # 等待服务启动
    print_status "等待基础设施服务启动..."
    sleep 10

    # 检查关键服务
    if curl -s --max-time 5 http://localhost:8848/nacos/ > /dev/null 2>&1; then
        print_status "Nacos 服务启动成功"
    else
        print_warning "Nacos 服务可能未完全启动，请稍后检查"
    fi

    if curl -s --max-time 5 http://localhost:16686/ > /dev/null 2>&1; then
        print_status "Jaeger UI 启动成功"
    else
        print_warning "Jaeger UI 可能未完全启动，请稍后检查"
    fi
}

# 启动微服务
start_services() {
    print_step "启动微服务..."

    # 检查基础设施是否就绪
    if ! curl -s --max-time 5 http://localhost:3306 > /dev/null 2>&1; then
        print_warning "MySQL 可能未就绪，服务可能无法正常启动"
    fi

    if ! curl -s --max-time 5 http://localhost:6379 > /dev/null 2>&1; then
        print_warning "Redis 可能未就绪，服务可能无法正常启动"
    fi

    # 启动微服务（后台运行）
    print_status "启动网关服务..."
    cd services/gateway-service && python -m app.main &
    GATEWAY_PID=$!
    cd "$PROJECT_ROOT"

    print_status "启动认证服务..."
    cd services/auth-service && python -m app.main &
    AUTH_PID=$!
    cd "$PROJECT_ROOT"

    print_status "启动主机服务..."
    cd services/host-service && python -m app.main &
    HOST_PID=$!
    cd "$PROJECT_ROOT"

    # 等待服务启动
    print_status "等待微服务启动..."
    sleep 15

    # 检查服务健康状态
    check_services_health

    # 保存进程ID到文件
    echo $GATEWAY_PID > .service_pids
    echo $AUTH_PID >> .service_pids
    echo $ADMIN_PID >> .service_pids
    echo $HOST_PID >> .service_pids
}

# 检查服务健康状态
check_services_health() {
    print_step "检查服务健康状态..."

    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_info"

        if curl -s --max-time 5 "http://localhost:$port/health" > /dev/null 2>&1; then
            print_status "$description ($port) 健康检查通过"
        else
            print_warning "$description ($port) 健康检查失败"
        fi
    done
}

# 生成API文档
generate_docs() {
    print_step "生成API文档..."

    # 运行文档生成脚本
    ./scripts/generate_docs.sh
}

# 显示服务信息
show_service_info() {
    echo ""
    echo "🎉 所有服务启动完成！"
    echo "==============================="
    echo ""
    echo "📋 服务访问地址："
    echo ""

    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_info"
        echo "🔗 $description ($service_name)"
        echo "   📖 Swagger UI:    http://localhost:$port/docs"
        echo "   📄 ReDoc:         http://localhost:$port/redoc"
        echo "   🔧 OpenAPI JSON:  http://localhost:$port/openapi.json"
        echo "   💚 健康检查:      http://localhost:$port/health"
        echo "   📊 监控指标:      http://localhost:$port/metrics"
        echo ""
    done

    echo "🔗 基础设施服务："
    echo "   🗄️  MySQL:         localhost:3306"
    echo "   🗄️  Redis:         localhost:6379"
    echo "   🏷️  Nacos:         http://localhost:8848/nacos/"
    echo "   🔍 Jaeger UI:     http://localhost:16686/"
    echo "   📊 Prometheus:     http://localhost:9090/"
    echo "   📈 Grafana:        http://localhost:3000/ (admin/admin)"
    echo ""

    echo "📁 API文档文件位置："
    echo "   📂 docs/api/ - 包含所有服务的OpenAPI规范和端点文档"
    echo ""

    echo "🛑 停止服务："
    echo "   ./scripts/dev_docs.sh --stop"
    echo ""
}

# 停止服务
stop_services() {
    print_step "停止所有服务..."

    # 停止微服务
    if [ -f .service_pids ]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "停止进程 $pid"
                kill "$pid"
            fi
        done < .service_pids
        rm .service_pids
    fi

    # 停止基础设施
    print_status "停止基础设施服务..."
    docker-compose down

    print_status "所有服务已停止"
}

# 显示帮助
show_help() {
    echo "Intel EC 微服务开发环境管理脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --start       启动所有服务并生成文档 (默认)"
    echo "  --docs        只生成API文档"
    echo "  --check       检查服务健康状态"
    echo "  --stop        停止所有服务"
    echo "  --restart     重启所有服务"
    echo "  --help        显示帮助信息"
    echo ""
    echo "快速开始:"
    echo "  $0              # 启动所有服务并生成文档"
    echo "  $0 --docs       # 只生成API文档"
    echo "  $0 --stop       # 停止所有服务"
    echo ""
    echo "访问地址:"
    echo "  网关服务文档: http://localhost:8000/docs"
    echo "  认证服务文档: http://localhost:8001/docs"
    echo "  管理服务文档: http://localhost:8002/docs"
    echo "  主机服务文档: http://localhost:8003/docs"
}

# 主函数
main() {
    case "${1:-}" in
        "--help"|"-h")
            show_help
            exit 0
            ;;
        "--stop")
            stop_services
            exit 0
            ;;
        "--docs")
            check_docker
            generate_docs
            exit 0
            ;;
        "--check")
            check_services_health
            exit 0
            ;;
        "--restart")
            stop_services
            sleep 2
            main "--start"
            exit 0
            ;;
        "--start"|"")
            # 默认行为：启动所有服务
            check_docker
            start_infrastructure
            start_services
            generate_docs
            show_service_info
            ;;
        *)
            print_error "未知选项: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 捕获中断信号
trap 'echo ""; print_warning "收到中断信号，正在停止服务..."; stop_services; exit 1' INT TERM

# 执行主函数
main "$@"
