#!/bin/bash
# 验证 Prometheus 和 Grafana 监控配置

echo "🔍 验证监控系统配置"
echo "================================"
echo ""

# 检查 Prometheus
echo "📊 Prometheus 状态:"
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "  ✅ Prometheus 运行正常"
    
    # 检查目标状态
    echo ""
    echo "🎯 监控目标状态:"
    curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    targets = data['data']['activeTargets']
    up_count = sum(1 for t in targets if t['health'] == 'up')
    print(f'  总目标数: {len(targets)}')
    print(f'  在线目标: {up_count}')
    print(f'  离线目标: {len(targets) - up_count}')
    print('')
    print('  详细状态:')
    for t in targets:
        status = '✅' if t['health'] == 'up' else '❌'
        job = t['labels'].get('job', 'unknown')
        print(f'    {status} {job}: {t[\"health\"]}')
except:
    print('  ⚠️  无法解析目标状态')
" 2>/dev/null || echo "  ⚠️  无法获取目标状态"
else
    echo "  ❌ Prometheus 未运行"
fi

echo ""

# 检查 Grafana
echo "📈 Grafana 状态:"
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "  ✅ Grafana 运行正常"
    echo "  🌐 访问地址: http://localhost:3000"
    echo "  👤 默认账号: admin"
    echo "  🔑 默认密码: ***REMOVED***"
else
    echo "  ❌ Grafana 未运行"
fi

echo ""

# 检查服务指标端点
echo "🔌 服务指标端点:"
for port in 8000 8001 8002 8003; do
    service_name=$([ $port -eq 8000 ] && echo "Gateway" || [ $port -eq 8001 ] && echo "Auth" || [ $port -eq 8002 ] && echo "Admin" || echo "Host")
    if curl -s --max-time 2 http://localhost:$port/metrics > /dev/null 2>&1; then
        echo "  ✅ $service_name Service ($port): 可访问"
    else
        echo "  ❌ $service_name Service ($port): 不可访问"
    fi
done

echo ""
echo "✅ 监控系统验证完成！"
echo ""
echo "📚 快速链接:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000"
echo "  - 仪表板: http://localhost:3000/d/intel-cw-microservices"
