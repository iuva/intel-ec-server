#!/bin/bash
# tests/performance/http/linux/run_load_test.sh
# Linux 压测执行脚本

HOST_URL="${K6_HOST_URL:-http://localhost:8003}"
TEST_ENV="${K6_ENV:-local}"
RESULTS_DIR="results"

# 创建结果目录
mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "Linux 压测脚本"
echo "========================================"
echo "目标服务: $HOST_URL"
echo "测试环境: $TEST_ENV"
echo "结果目录: $RESULTS_DIR"
echo "========================================"

# 选择压测工具
echo ""
echo "请选择压测工具:"
echo "1. k6"
echo "2. Locust (Web UI)"
echo "3. Locust (Headless)"
echo "4. wrk"
echo ""
read -p "请输入选项 (1-4): " TOOL

case $TOOL in
  1)
    echo ""
    echo "执行 k6 压测..."
    export K6_HOST_URL="$HOST_URL"
    export K6_ENV="$TEST_ENV"
    k6 run tests/performance/http/linux/k6_load_test_linux.js \
      --out json="$RESULTS_DIR/linux_k6_results.json" \
      --out csv="$RESULTS_DIR/linux_k6_results.csv"
    ;;
  2)
    echo ""
    echo "启动 Locust Web UI..."
    locust -f tests/performance/http/linux/locust_load_test_linux.py \
      --host="$HOST_URL" \
      --web-host=0.0.0.0 \
      --web-port=8089
    ;;
  3)
    echo ""
    echo "执行 Locust 无UI压测..."
    locust -f tests/performance/http/linux/locust_load_test_linux.py \
      --host="$HOST_URL" \
      --users=200 \
      --spawn-rate=20 \
      --run-time=5m \
      --headless \
      --html="$RESULTS_DIR/linux_locust_report.html" \
      --csv="$RESULTS_DIR/linux_locust_results"
    ;;
  4)
    echo ""
    echo "执行 wrk 压测..."
    wrk -t4 -c200 -d30s \
      -s tests/performance/http/linux/wrk_post.lua \
      --latency \
      --timeout 30s \
      "$HOST_URL/api/v1/host/hosts/available" \
      > "$RESULTS_DIR/linux_wrk_results.txt"
    ;;
  *)
    echo "无效选项！"
    exit 1
    ;;
esac

echo ""
echo "========================================"
echo "压测完成！"
echo "结果文件保存在: $RESULTS_DIR"
echo "========================================"

