#!/bin/bash
# Nacos 服务注册验证脚本
# 用于验证微服务是否正确注册到 Nacos

set -e

NACOS_SERVER="${NACOS_SERVER:-localhost:8848}"
SERVICES=("gateway-service" "auth-service" "host-service")

echo "========================================="
echo "Nacos 服务注册验证脚本"
echo "========================================="
echo ""
echo "Nacos 服务器: ${NACOS_SERVER}"
echo ""

# 检查 Nacos 服务器是否可用
echo "1️⃣ 检查 Nacos 服务器健康状态..."
if curl -s -f "http://${NACOS_SERVER}/nacos/v1/console/health/readiness" > /dev/null; then
    echo "✅ Nacos 服务器健康检查通过"
else
    echo "❌ Nacos 服务器不可用"
    exit 1
fi

echo ""

# 验证每个服务的注册状态
for service in "${SERVICES[@]}"; do
    echo "2️⃣ 验证服务: ${service}"
    
    # 获取服务实例列表
    response=$(curl -s "http://${NACOS_SERVER}/nacos/v1/ns/instance/list?serviceName=${service}&groupName=DEFAULT_GROUP&namespaceId=public")
    
    # 检查是否有健康的实例
    hosts=$(echo "$response" | grep -o '"hosts":\[[^]]*\]' || echo "")
    
    if [ -z "$hosts" ] || [ "$hosts" == '"hosts":[]' ]; then
        echo "   ❌ 服务未注册或没有健康实例"
        continue
    fi
    
    # 提取 IP 和端口
    ip=$(echo "$response" | grep -o '"ip":"[^"]*"' | head -1 | cut -d'"' -f4)
    port=$(echo "$response" | grep -o '"port":[0-9]*' | head -1 | cut -d':' -f2)
    healthy=$(echo "$response" | grep -o '"healthy":[a-z]*' | head -1 | cut -d':' -f2)
    
    echo "   ✅ 服务注册成功"
    echo "      - IP: ${ip}"
    echo "      - 端口: ${port}"
    echo "      - 健康状态: ${healthy}"
    
    # 验证 IP 格式（应该是 172.20.0.x）
    if [[ "$ip" =~ ^172\.20\.0\.[0-9]+$ ]]; then
        echo "      ✅ IP 格式正确（静态 IP）"
    else
        echo "      ⚠️ IP 格式异常（期望: 172.20.0.x，实际: ${ip}）"
    fi
    
    # 验证端口号
    expected_ports=("8000" "8001" "8003")
    case "$service" in
        "gateway-service") expected_port="${expected_ports[0]}" ;;
        "auth-service") expected_port="${expected_ports[1]}" ;;
        "host-service") expected_port="${expected_ports[2]}" ;;
    esac
    
    if [ "$port" == "$expected_port" ]; then
        echo "      ✅ 端口号正确 (${port})"
    else
        echo "      ⚠️ 端口号异常（期望: ${expected_port}，实际: ${port}）"
    fi
    
    echo ""
done

echo "========================================="
echo "验证完成"
echo "========================================="

