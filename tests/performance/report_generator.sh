#!/bin/bash
# 性能测试执行与报告生成脚本

# 检查 k6 是否安装
if ! command -v k6 &> /dev/null; then
    echo "Error: k6 could not be found. Please install it first."
    echo "Install guide: https://k6.io/docs/get-started/installation"
    exit 1
fi

SCENARIO=$1

if [ -z "$SCENARIO" ]; then
    echo "Usage: ./report_generator.sh <scenario_name>"
    echo "Example: ./report_generator.sh available_list"
    echo ""
    echo "Available scenarios:"
    ls tests/performance/scenarios | sed 's/.js//' | sed 's/^/- /'
    exit 1
fi

# 支持不带 .js 后缀
if [[ "$SCENARIO" != *".js" ]]; then
    SCRIPT="tests/performance/scenarios/${SCENARIO}.js"
else
    SCRIPT="tests/performance/scenarios/${SCENARIO}"
fi

if [ ! -f "$SCRIPT" ]; then
    echo "Error: Script $SCRIPT not found."
    exit 1
fi

echo "============================================="
echo "Running performance test: $SCENARIO"
echo "Target VU: 500 (Check script options for details)"
echo "============================================="

# 确保报告目录存在
mkdir -p tests/performance/reports

# 运行 k6
# 注意: handleSummary 在脚本中定义，会自动生成 report_timestamp.html
k6 run "$SCRIPT" --quiet

echo ""
echo "============================================="
echo "Test finished."
echo "Check reports in: tests/performance/reports/"
ls -lh tests/performance/reports/ | head -n 5
echo "============================================="
