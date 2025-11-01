#!/bin/bash
# 批量构建所有微服务 Docker 镜像

set -e

echo "🚀 开始构建所有微服务..."
echo ""

# 定义服务列表
services=("gateway-service" "auth-service" "host-service")

# 构建计数
success_count=0
failed_count=0
failed_services=()

# 记录开始时间
start_time=$(date +%s)

# 遍历构建每个服务
for service in "${services[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 正在构建: $service"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    service_start=$(date +%s)
    
    if docker-compose build --no-cache $service; then
        service_end=$(date +%s)
        duration=$((service_end - service_start))
        echo "✅ $service 构建成功 (耗时: ${duration}秒)"
        ((success_count++))
    else
        service_end=$(date +%s)
        duration=$((service_end - service_start))
        echo "❌ $service 构建失败 (耗时: ${duration}秒)"
        ((failed_count++))
        failed_services+=("$service")
    fi
    
    echo ""
done

# 记录结束时间
end_time=$(date +%s)
total_duration=$((end_time - start_time))

# 显示构建总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 构建总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 成功: $success_count 个服务"
echo "❌ 失败: $failed_count 个服务"
echo "⏱️  总耗时: ${total_duration}秒"
echo ""

# 如果有失败的服务，列出来
if [ $failed_count -gt 0 ]; then
    echo "❌ 失败的服务:"
    for service in "${failed_services[@]}"; do
        echo "  - $service"
    done
    echo ""
    exit 1
fi

# 显示镜像列表
echo "📦 已构建的镜像:"
docker images | grep "intel-cw-ms" | grep -E "(gateway|admin|auth|host)"
echo ""

echo "🎉 所有服务构建完成！"
echo ""
echo "💡 下一步操作:"
echo "  1. 启动所有服务: docker-compose up -d"
echo "  2. 查看服务状态: docker-compose ps"
echo "  3. 查看服务日志: docker-compose logs -f [service-name]"
echo ""
