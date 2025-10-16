#!/bin/bash

# Intel EC 微服务项目 - 环境验证脚本
# 用于验证项目基础设施是否正确搭建

set -e

echo "=========================================="
echo "Intel EC 微服务项目 - 环境验证"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 已安装"
        return 0
    else
        echo -e "${RED}✗${NC} $1 未安装"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 存在"
        return 0
    else
        echo -e "${RED}✗${NC} $1 不存在"
        return 1
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 目录存在"
        return 0
    else
        echo -e "${RED}✗${NC} $1 目录不存在"
        return 1
    fi
}

# 1. 检查必需的命令
echo "1. 检查必需的命令..."
check_command python3
check_command docker
check_command docker-compose
echo ""

# 2. 检查 Python 版本
echo "2. 检查 Python 版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [[ $PYTHON_VERSION == 3.8.* ]]; then
    echo -e "${GREEN}✓${NC} Python 版本: $PYTHON_VERSION (符合要求)"
else
    echo -e "${YELLOW}⚠${NC} Python 版本: $PYTHON_VERSION (建议使用 3.8.10)"
fi
echo ""

# 3. 检查项目结构
echo "3. 检查项目目录结构..."
check_directory "services/gateway-service"
check_directory "services/auth-service"
check_directory "services/admin-service"
check_directory "services/host-service"
check_directory "shared"
check_directory "infrastructure"
check_directory "scripts"
check_directory "docs"
echo ""

# 4. 检查配置文件
echo "4. 检查配置文件..."
check_file "requirements.txt"
check_file "pyproject.toml"
check_file ".env.example"
check_file ".gitignore"
check_file ".dockerignore"
check_file "docker-compose.yml"
echo ""

# 5. 检查 Dockerfile
echo "5. 检查 Dockerfile..."
check_file "services/gateway-service/Dockerfile"
check_file "services/auth-service/Dockerfile"
check_file "services/admin-service/Dockerfile"
check_file "services/host-service/Dockerfile"
check_file "infrastructure/docker/Dockerfile.base"
echo ""

# 6. 检查环境变量
echo "6. 检查环境变量配置..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env 文件存在"
else
    echo -e "${YELLOW}⚠${NC} .env 文件不存在，请从 .env.example 复制"
    echo "   运行: cp .env.example .env"
fi
echo ""

# 7. 检查 Docker 服务
echo "7. 检查 Docker 服务状态..."
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker 服务运行中"
    
    # 检查容器状态
    if docker-compose ps &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker Compose 可用"
        
        # 列出运行中的容器
        RUNNING_CONTAINERS=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)
        if [ $RUNNING_CONTAINERS -gt 0 ]; then
            echo -e "${GREEN}✓${NC} 有 $RUNNING_CONTAINERS 个容器正在运行"
            docker-compose ps
        else
            echo -e "${YELLOW}⚠${NC} 没有运行中的容器"
            echo "   运行: docker-compose up -d"
        fi
    fi
else
    echo -e "${RED}✗${NC} Docker 服务未运行"
    echo "   请启动 Docker 服务"
fi
echo ""

# 8. 检查端口占用
echo "8. 检查端口占用..."
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}⚠${NC} 端口 $1 已被占用"
        return 1
    else
        echo -e "${GREEN}✓${NC} 端口 $1 可用"
        return 0
    fi
}

check_port 3306  # MySQL
check_port 6379  # Redis
check_port 8848  # Nacos
check_port 16686 # Jaeger
check_port 8000  # Gateway
check_port 8001  # Auth
check_port 8002  # Admin
check_port 8003  # Host
echo ""

# 9. 总结
echo "=========================================="
echo "验证完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 如果 .env 文件不存在，请复制并配置："
echo "   cp .env.example .env"
echo ""
echo "2. 安装 Python 依赖："
echo "   pip install -r requirements.txt"
echo ""
echo "3. 启动基础设施服务："
echo "   docker-compose up -d mysql redis nacos jaeger"
echo ""
echo "4. 查看服务状态："
echo "   docker-compose ps"
echo ""
echo "5. 查看日志："
echo "   docker-compose logs -f"
echo ""
echo "详细文档请参考："
echo "- docs/quick-start.md"
echo "- docs/project-setup.md"
echo ""
