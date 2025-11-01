#!/bin/bash
# 检查 Nacos 中服务注册的端口信息

echo "========================================="
echo "检查 Nacos 服务注册端口"
echo "========================================="
echo ""

NACOS_SERVER="${NACOS_SERVER:-localhost:8848}"
SERVICES=("gateway-service:8000" "auth-service:8001" "host-service:8003")

for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service expected_port <<< "$service_info"
    
    echo "📋 检查服务: $service (期望端口: $expected_port)"
    
    # 从 Nacos 获取服务实例信息
    response=$(docker exec intel-nacos curl -s "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=${service}&groupName=DEFAULT_GROUP&namespaceId=public" 2>/dev/null || echo '{"hosts":[]}')
    
    # 提取端口信息
    actual_port=$(echo "$response" | grep -o '"port":[0-9]*' | head -1 | grep -o '[0-9]*')
    actual_ip=$(echo "$response" | grep -o '"ip":"[^"]*"' | head -1 | grep -o '[0-9.]*')
    
    if [ -z "$actual_port" ]; then
        echo "  ❌ 未找到服务实例"
    elif [ "$actual_port" == "$expected_port" ]; then
        echo "  ✅ 端口正确: $actual_port (IP: $actual_ip)"
    else
        echo "  ❌ 端口错误: 实际 $actual_port, 期望 $expected_port (IP: $actual_ip)"
    fi
    
    echo ""
done

echo "========================================="
echo "检查完成"
echo "========================================="

