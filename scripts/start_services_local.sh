#!/bin/bash

# 本地开发启动脚本 - 跨平台版本 (Mac/Linux)
# 支持从 .env 文件加载环境变量
# 
# 使用方式：
#   1. ./scripts/start_services_local.sh all              # 显示所有启动命令
#   2. ./scripts/start_services_local.sh gateway          # 启动网关服务
#   3. ./scripts/start_services_local.sh auth             # 启动认证服务
#   4. ./scripts/start_services_local.sh admin            # 启动管理服务
#   5. ./scripts/start_services_local.sh host             # 启动主机服务
#   6. ./scripts/start_services_local.sh check            # 检查环境配置

set -e

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==================== 项目路径 ====================
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# ==================== 加载 .env 文件函数 ====================
load_env_file() {
    if [ -f "$ENV_FILE" ]; then
        echo -e "${BLUE}📋 从 .env 文件加载环境变量...${NC}"
        
        # 读取 .env 文件，过滤注释和空行，然后导出每个变量
        while IFS='=' read -r key value; do
            # 跳过注释和空行
            [[ "$key" =~ ^#.*$ ]] && continue
            [ -z "$key" ] && continue
            
            # 移除可能的引号
            value="${value%\'}"
            value="${value#\'}"
            
            # 导出环境变量到当前 shell
            export "$key"="$value"
        done < "$ENV_FILE"
        
        # 本地开发特定配置：设置服务主机地址为 localhost
        # Docker 启动时使用默认值（auth-service, host-service）
        echo -e "${BLUE}🔧 配置本地服务连接...${NC}"
        export SERVICE_HOST_AUTH="127.0.0.1"
        export SERVICE_HOST_HOST="127.0.0.1"
        
        # 本地开发特定配置：Jaeger 追踪端点
        # Docker 启动时使用 jaeger:4317，本地开发使用 localhost:4317
        export JAEGER_ENDPOINT="localhost:4317"
        
        echo -e "${GREEN}✓ 环境变量加载成功${NC}"
        echo -e "${GREEN}  • SERVICE_HOST_AUTH: $SERVICE_HOST_AUTH${NC}"
        echo -e "${GREEN}  • SERVICE_HOST_HOST: $SERVICE_HOST_HOST${NC}"
        echo -e "${GREEN}  • JAEGER_ENDPOINT: $JAEGER_ENDPOINT${NC}"
    else
        echo -e "${YELLOW}⚠️  警告：.env 文件不存在，使用默认环境变量${NC}"
    fi
}

# ==================== 虚拟环境激活函数 ====================
activate_venv() {
    if [ -d "$PROJECT_ROOT/venv" ]; then
        echo -e "${BLUE}🐍 激活虚拟环境...${NC}"
        source "$PROJECT_ROOT/venv/bin/activate"
        echo -e "${GREEN}✓ 虚拟环境激活成功${NC}"
    else
        echo -e "${RED}❌ 错误：虚拟环境不存在${NC}"
        echo "请先运行以下命令创建虚拟环境："
        echo "  python3.8 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
}

# ==================== 检查 MariaDB 连接 ====================
check_mariadb() {
    MARIADB_HOST="${MARIADB_HOST:-127.0.0.1}"
    MARIADB_PORT="${MARIADB_PORT:-3306}"
    MARIADB_USER="${MARIADB_USER:-intel_user}"
    MARIADB_PASSWORD="${MARIADB_PASSWORD:-intel_***REMOVED***}"
    
    echo -e "${BLUE}🗄️  检查 MariaDB 连接...${NC}"
    echo "主机: $MARIADB_HOST:$MARIADB_PORT"
    echo "用户: $MARIADB_USER"
    
    if command -v mysql &> /dev/null; then
        if mysql -h "$MARIADB_HOST" -P "$MARIADB_PORT" -u "$MARIADB_USER" -p"$MARIADB_PASSWORD" -e "SELECT VERSION();" &> /dev/null; then
            echo -e "${GREEN}✓ MariaDB 连接成功${NC}"
            return 0
        else
            echo -e "${RED}❌ MariaDB 连接失败${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  mysql 客户端未安装，跳过连接检查${NC}"
        return 0
    fi
}

# ==================== 检查 Docker 容器 ====================
check_docker_containers() {
    echo -e "${BLUE}🐳 检查 Docker 容器状态...${NC}"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
        echo ""
        
        # 检查关键容器
        local critical_containers=("mariadb" "redis" "nacos")
        for container in "${critical_containers[@]}"; do
            if docker-compose ps | grep -q "$container.*Up"; then
                echo -e "${GREEN}✓ $container 容器运行中${NC}"
            else
                echo -e "${RED}❌ $container 容器未运行${NC}"
            fi
        done
    else
        echo -e "${YELLOW}⚠️  docker-compose 未安装，跳过容器检查${NC}"
    fi
}

# ==================== 环境检查函数 ====================
check_environment() {
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}🔍 环境检查${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    
    # 检查 Python
    echo -e "${BLUE}📌 Python 版本检查${NC}"
    python3 --version
    echo ""
    
    # 检查虚拟环境
    echo -e "${BLUE}📌 虚拟环境检查${NC}"
    if [ -d "$PROJECT_ROOT/venv" ]; then
        echo -e "${GREEN}✓ 虚拟环境存在${NC}"
    else
        echo -e "${RED}❌ 虚拟环境不存在${NC}"
    fi
    echo ""
    
    # 检查 .env 文件
    echo -e "${BLUE}📌 .env 文件检查${NC}"
    if [ -f "$ENV_FILE" ]; then
        echo -e "${GREEN}✓ .env 文件存在${NC}"
        echo "关键环境变量："
        echo "  PYTHONPATH: $PYTHONPATH"
        echo "  MARIADB_HOST: ${MARIADB_HOST:-127.0.0.1}"
        echo "  MARIADB_PORT: ${MARIADB_PORT:-3306}"
    else
        echo -e "${YELLOW}⚠️  .env 文件不存在（可选）${NC}"
    fi
    echo ""
    
    # 检查 Docker
    check_docker_containers
    echo ""
    
    # 检查 MariaDB 连接
    check_mariadb
    echo ""
    
    echo -e "${BLUE}════════════════════════════════════════${NC}"
}

# ==================== 启动函数 ====================
start_service() {
    local service_name=$1
    local port=$2
    local service_dir=$3
    
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}🚀 启动 $service_name (端口: $port)${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo ""
    echo "服务目录: $service_dir"
    echo "工作目录: $PROJECT_ROOT/$service_dir"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""
    
    # 进入服务目录后启动（这样相对导入才能工作）
    cd "$PROJECT_ROOT"/"$service_dir"
    python -m uvicorn app.main:app --host 0.0.0.0 --port "$port" --reload
}

# ==================== 显示所有启动命令 ====================
show_all_commands() {
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}📌 本地开发启动指南${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  重要：必须在不同的终端中启动每个服务${NC}"
    echo ""
    echo "启动顺序（必须按此顺序）："
    echo ""
    echo -e "${GREEN}1️⃣  终端1 - Auth Service (8001):${NC}"
    echo "   cd \"$PROJECT_ROOT\""
    echo "   source venv/bin/activate"
    echo "   ./scripts/start_services_local.sh auth"
    echo ""
    echo -e "${GREEN}2️⃣  终端2 - Admin Service (8002):${NC}"
    echo "   cd \"$PROJECT_ROOT\""
    echo "   source venv/bin/activate"
    echo "   ./scripts/start_services_local.sh admin"
    echo ""
    echo -e "${GREEN}3️⃣  终端3 - Host Service (8003):${NC}"
    echo "   cd \"$PROJECT_ROOT\""
    echo "   source venv/bin/activate"
    echo "   ./scripts/start_services_local.sh host"
    echo ""
    echo -e "${GREEN}4️⃣  终端4 - Gateway Service (8000) [最后启动]:${NC}"
    echo "   cd \"$PROJECT_ROOT\""
    echo "   source venv/bin/activate"
    echo "   ./scripts/start_services_local.sh gateway"
    echo ""
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${YELLOW}💡 快速启动技巧${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo "如果已配置 PYTHONPATH，可以用简化命令："
    echo "   cd services/auth-service && uvicorn app.main:app --port 8001 --reload"
    echo ""
}

# ==================== 主程序 ====================
main() {
    # 加载 .env 文件
    load_env_file
    echo ""
    
    # 激活虚拟环境
    activate_venv
    echo ""
    
    # 设置 PYTHONPATH
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
    echo -e "${GREEN}✓ PYTHONPATH 已设置为: $PYTHONPATH${NC}"
    echo ""
    
    # 检查参数
    if [ $# -eq 0 ]; then
        echo -e "${YELLOW}使用方式：${NC}"
        echo "  $0 check               # 检查环境配置"
        echo "  $0 all                 # 显示所有启动命令"
        echo "  $0 gateway             # 启动网关服务 (8000)"
        echo "  $0 auth                # 启动认证服务 (8001)"
        echo "  $0 admin               # 启动管理服务 (8002)"
        echo "  $0 host                # 启动主机服务 (8003)"
        exit 1
    fi
    
    case "$1" in
        check)
            check_environment
            ;;
        all)
            show_all_commands
            ;;
        gateway)
            start_service "Gateway Service" "8000" "services/gateway-service"
            ;;
        auth)
            start_service "Auth Service" "8001" "services/auth-service"
            ;;
        host)
            start_service "Host Service" "8003" "services/host-service"
            ;;
        *)
            echo -e "${RED}❌ 未知的命令: $1${NC}"
            echo "支持的命令: check, all, gateway, auth, host"
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@"
