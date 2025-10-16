#!/bin/bash

# 生成微服务API文档的脚本
# Generate API documentation for microservices

set -e

echo "🔄 开始生成微服务API文档..."

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 项目根目录: $PROJECT_ROOT"

# 创建文档输出目录
DOCS_DIR="$PROJECT_ROOT/docs/api"
mkdir -p "$DOCS_DIR"

# 服务配置
SERVICES=(
    "gateway-service:8000:网关服务"
    "auth-service:8001:认证服务"
    "admin-service:8002:管理服务"
    "host-service:8003:主机服务"
)

# 检查服务是否运行
check_service() {
    local service_name=$1
    local port=$2
    local description=$3

    echo "🔍 检查 $description ($service_name:$port)..."

    if curl -s --max-time 5 "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $description 正在运行"
        return 0
    else
        echo "❌ $description 未运行或无响应"
        return 1
    fi
}

# 生成单个服务的文档
generate_service_docs() {
    local service_name=$1
    local port=$2
    local description=$3

    echo "📝 生成 $description 的API文档..."

    # OpenAPI JSON
    local json_file="$DOCS_DIR/${service_name}-openapi.json"
    if curl -s --max-time 10 "http://localhost:$port/openapi.json" > "$json_file" 2>/dev/null; then
        echo "✅ $description OpenAPI JSON 已生成: $json_file"
    else
        echo "❌ 无法获取 $description 的 OpenAPI JSON"
        return 1
    fi

    # 生成 HTML 文档 (可选)
    local html_file="$DOCS_DIR/${service_name}-docs.html"
    if command -v pandoc &> /dev/null; then
        # 如果有 pandoc，可以转换为 HTML
        echo "📄 转换为 HTML 格式..."
        # 这里可以添加更复杂的文档生成逻辑
    fi

    # 生成 Markdown 格式的端点列表
    generate_endpoint_markdown "$service_name" "$port" "$description" "$json_file"
}

# 生成端点 Markdown 文档
generate_endpoint_markdown() {
    local service_name=$1
    local port=$2
    local description=$3
    local json_file=$4

    local md_file="$DOCS_DIR/${service_name}-endpoints.md"

    echo "# $description API 端点文档" > "$md_file"
    echo "" >> "$md_file"
    echo "**生成时间**: $(date)" >> "$md_file"
    echo "**服务地址**: http://localhost:$port" >> "$md_file"
    echo "" >> "$md_file"

    # 使用 jq 解析 JSON 并生成 Markdown 表格
    if command -v jq &> /dev/null && [ -f "$json_file" ]; then
        echo "## API 端点列表" >> "$md_file"
        echo "" >> "$md_file"
        echo "| 方法 | 路径 | 描述 |" >> "$md_file"
        echo "|------|------|------|" >> "$md_file"

        # 解析 OpenAPI JSON 并生成表格
        jq -r '.paths | to_entries[] | .key as $path | .value | to_entries[] | select(.key != "parameters") | "\(.key | ascii_upcase) | \($path) | \(.value.summary // "N/A" | @html)"' "$json_file" >> "$md_file" 2>/dev/null || echo "⚠️  无法解析 JSON 生成表格" >> "$md_file"
    else
        echo "## 访问地址" >> "$md_file"
        echo "" >> "$md_file"
        echo "- **Swagger UI**: http://localhost:$port/docs" >> "$md_file"
        echo "- **ReDoc**: http://localhost:$port/redoc" >> "$md_file"
        echo "- **OpenAPI JSON**: http://localhost:$port/openapi.json" >> "$md_file"
    fi

    echo "" >> "$md_file"
    echo "## 健康检查" >> "$md_file"
    echo "" >> "$md_file"
    echo "- **端点**: http://localhost:$port/health" >> "$md_file"
    echo "- **监控**: http://localhost:$port/metrics" >> "$md_file"

    echo "✅ $description Markdown 文档已生成: $md_file"
}

# 生成汇总文档
generate_summary() {
    local summary_file="$DOCS_DIR/README.md"

    echo "# 微服务API文档汇总" > "$summary_file"
    echo "" >> "$summary_file"
    echo "**生成时间**: $(date)" >> "$summary_file"
    echo "**项目**: Intel EC 微服务系统" >> "$summary_file"
    echo "" >> "$summary_file"

    echo "## 服务列表" >> "$summary_file"
    echo "" >> "$summary_file"

    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_info"

        echo "### $description ($service_name)" >> "$summary_file"
        echo "" >> "$summary_file"
        echo "- **端口**: $port" >> "$summary_file"
        echo "- **Swagger UI**: http://localhost:$port/docs" >> "$summary_file"
        echo "- **ReDoc**: http://localhost:$port/redoc" >> "$summary_file"
        echo "- **OpenAPI JSON**: http://localhost:$port/openapi.json" >> "$summary_file"
        echo "- **健康检查**: http://localhost:$port/health" >> "$summary_file"
        echo "- **监控指标**: http://localhost:$port/metrics" >> "$summary_file"
        echo "" >> "$summary_file"
    done

    echo "## 文档文件" >> "$summary_file"
    echo "" >> "$summary_file"

    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_info"
        echo "- \`$service_name-openapi.json\` - $description OpenAPI 规范" >> "$summary_file"
        echo "- \`$service_name-endpoints.md\` - $description 端点列表" >> "$summary_file"
    done

    echo "" >> "$summary_file"
    echo "## 使用说明" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "1. 确保所有微服务正在运行" >> "$summary_file"
    echo "2. 在浏览器中访问对应服务的 /docs 路径查看交互式文档" >> "$summary_file"
    echo "3. 使用 /openapi.json 端点下载 API 规范" >> "$summary_file"
    echo "4. 使用生成的文档进行客户端代码生成或 API 测试" >> "$summary_file"

    echo "✅ 文档汇总已生成: $summary_file"
}

# 主函数
main() {
    echo "🎯 开始检查服务状态..."

    local running_services=()

    # 检查所有服务
    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_info"

        if check_service "$service_name" "$port" "$description"; then
            running_services+=("$service_info")
        fi
    done

    if [ ${#running_services[@]} -eq 0 ]; then
        echo "❌ 没有运行中的服务，无法生成文档"
        echo ""
        echo "💡 请先启动服务："
        echo "   docker-compose up -d gateway-service auth-service admin-service host-service"
        echo "   或者分别启动每个服务"
        exit 1
    fi

    echo ""
    echo "📋 生成文档中..."

    # 生成每个服务的文档
    for service_info in "${running_services[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_info"
        generate_service_docs "$service_name" "$port" "$description"
        echo ""
    done

    # 生成汇总文档
    generate_summary

    echo ""
    echo "🎉 文档生成完成！"
    echo "📁 输出目录: $DOCS_DIR"
    echo ""
    echo "📖 快速访问："
    echo "   网关服务: http://localhost:8000/docs"
    echo "   认证服务: http://localhost:8001/docs"
    echo "   管理服务: http://localhost:8002/docs"
    echo "   主机服务: http://localhost:8003/docs"
}

# 检查依赖
check_dependencies() {
    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        echo "⚠️  jq 未安装，某些功能可能受限"
        echo "   安装方法: brew install jq  # macOS"
        echo "   安装方法: apt install jq  # Ubuntu/Debian"
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "❌ 缺少必要的依赖: ${missing_deps[*]}"
        echo "请先安装这些工具后再运行脚本"
        exit 1
    fi
}

# 参数处理
case "${1:-}" in
    "--help"|"-h")
        echo "微服务API文档生成脚本"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --help, -h    显示帮助信息"
        echo "  --check       只检查服务状态，不生成文档"
        echo ""
        echo "功能:"
        echo "  - 检查所有微服务运行状态"
        echo "  - 下载 OpenAPI JSON 规范"
        echo "  - 生成端点列表 Markdown 文档"
        echo "  - 创建文档汇总"
        echo ""
        echo "输出目录: docs/api/"
        exit 0
        ;;
    "--check")
        echo "🔍 仅检查服务状态..."
        for service_info in "${SERVICES[@]}"; do
            IFS=':' read -r service_name port description <<< "$service_info"
            check_service "$service_name" "$port" "$description"
        done
        exit 0
        ;;
    "")
        # 默认行为
        ;;
    *)
        echo "❌ 未知选项: $1"
        echo "使用 '$0 --help' 查看帮助"
        exit 1
        ;;
esac

# 检查依赖
check_dependencies

# 执行主函数
main
