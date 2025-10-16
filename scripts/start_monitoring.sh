#!/bin/bash

# ==========================================
# 监控系统启动脚本
# ==========================================
# 用途：启动 Prometheus 和 Grafana 监控服务

echo "=========================================="
echo "启动 Prometheus + Grafana 监控系统"
echo "=========================================="
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误：Docker 未运行或无权限访问"
    exit 1
fi

# 检查配置文件是否存在
if [ ! -f "infrastructure/prometheus/prometheus.yml" ]; then
    echo "❌ 错误：Prometheus 配置文件不存在"
    echo "   请确保 infrastructure/prometheus/prometheus.yml 文件存在"
    exit 1
fi

# 创建必要的目录
echo "1. 创建必要的目录..."
mkdir -p infrastructure/grafana/provisioning/datasources
mkdir -p infrastructure/grafana/provisioning/dashboards
mkdir -p infrastructure/grafana/dashboards

# 启动 Prometheus
echo "2. 启动 Prometheus..."
docker-compose up -d prometheus

if [ $? -eq 0 ]; then
    echo "   ✅ Prometheus 启动成功"
else
    echo "   ❌ Prometheus 启动失败"
    exit 1
fi

# 等待 Prometheus 就绪
echo "3. 等待 Prometheus 就绪..."
for i in {1..30}; do
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo "   ✅ Prometheus 已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ⚠️  Prometheus 启动超时，但继续启动 Grafana"
    fi
    sleep 1
done

# 启动 Grafana
echo "4. 启动 Grafana..."
docker-compose up -d grafana

if [ $? -eq 0 ]; then
    echo "   ✅ Grafana 启动成功"
else
    echo "   ❌ Grafana 启动失败"
    exit 1
fi

# 等待 Grafana 就绪
echo "5. 等待 Grafana 就绪..."
for i in {1..30}; do
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo "   ✅ Grafana 已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ⚠️  Grafana 启动超时"
    fi
    sleep 1
done

# 显示服务状态
echo ""
echo "=========================================="
echo "✅ 监控系统启动完成！"
echo "=========================================="
echo ""
echo "📊 访问地址："
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana:    http://localhost:3000"
echo ""
echo "🔐 Grafana 登录信息："
echo "  - 用户名: admin"
echo "  - 密码:   ***REMOVED*** (可在 .env 中修改)"
echo ""
echo "📈 查看仪表板："
echo "  1. 访问 http://localhost:3000"
echo "  2. 使用上述凭据登录"
echo "  3. 点击左侧菜单 'Dashboards'"
echo "  4. 选择 'Intel EC 微服务概览'"
echo ""
echo "=========================================="
echo ""
echo "查看服务状态："
echo "  docker-compose ps prometheus grafana"
echo ""
echo "查看日志："
echo "  docker-compose logs -f prometheus grafana"
echo ""
echo "停止监控："
echo "  docker-compose stop prometheus grafana"
echo ""
echo "=========================================="
