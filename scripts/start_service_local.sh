#!/bin/bash
# 本地开发启动脚本
export PYTHONPATH="/Users/chiyeming/KiroProjects/intel_ec_ms:${PYTHONPATH}"
source /Users/chiyeming/KiroProjects/intel_ec_ms/venv/bin/activate

if [ $# -eq 0 ]; then
    echo "使用方式："
    echo "  ./scripts/start_service_local.sh gateway   # 启动网关服务 (8000)"
    echo "  ./scripts/start_service_local.sh auth      # 启动认证服务 (8001)"
    echo "  ./scripts/start_service_local.sh admin     # 启动管理服务 (8002)"
    echo "  ./scripts/start_service_local.sh host      # 启动主机服务 (8003)"
    exit 1
fi

service=$1

case $service in
    gateway)
        echo "🚀 启动 Gateway Service (端口: 8000)..."
        python -m uvicorn services.gateway-service.app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    auth)
        echo "🚀 启动 Auth Service (端口: 8001)..."
        python -m uvicorn services.auth-service.app.main:app --host 0.0.0.0 --port 8001 --reload
        ;;
    admin)
        echo "🚀 启动 Admin Service (端口: 8002)..."
        python -m uvicorn services.admin-service.app.main:app --host 0.0.0.0 --port 8002 --reload
        ;;
    host)
        echo "🚀 启动 Host Service (端口: 8003)..."
        python -m uvicorn services.host-service.app.main:app --host 0.0.0.0 --port 8003 --reload
        ;;
    *)
        echo "❌ 未知的服务: $service"
        echo "支持的服务: gateway, auth, admin, host"
        exit 1
        ;;
esac
