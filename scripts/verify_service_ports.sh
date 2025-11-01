#!/bin/bash
# 验证所有服务端口配置和运行状态

echo "========================================="
echo "微服务端口验证工具"
echo "========================================="
echo ""

echo "1️⃣ 检查服务环境变量配置"
echo "---"

for service in gateway-service auth-service host-service; do
    echo "📋 $service:"
    docker exec $service env 2>/dev/null | grep -E "SERVICE_PORT|SERVICE_IP|SERVICE_NAME" | sed 's/^/    /'
    echo ""
done

echo "2️⃣ 检查服务运行端口"
echo "---"

docker-compose ps gateway-service auth-service host-service | tail -n +2 | awk '{print $1, $NF}' | while read name ports; do
    echo "📋 $name: $ports"
done

echo ""
echo "========================================="
echo "验证完成"
echo "========================================="

