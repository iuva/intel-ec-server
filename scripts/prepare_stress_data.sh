#!/usr/bin/env bash
# Host Service 压力测试数据准备脚本（示例）
# 作用：快速生成压力测试所需的示例数据和文件占位

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
DATA_DIR="$ROOT_DIR/tests/perf_data"
FILES_DIR="$DATA_DIR/files"

mkdir -p "$FILES_DIR"

# 生成示例 SQL/JSON 占位文件（真实环境中请替换为实际数据准备逻辑）
cat > "$DATA_DIR/prepare_hosts.sql" <<'SQL'
-- TODO: 在此添加批量插入 host_rec / host_exec_log 的 SQL 脚本
SQL

cat > "$DATA_DIR/sample_hosts.json" <<'JSON'
{
  "hosts": [
    {"id": "1846486359367955001", "state": 0},
    {"id": "1846486359367955002", "state": 0}
  ]
}
JSON

# 生成不同大小的占位文件供上传/下载测试使用
for size in 10 50 100; do
  dd if=/dev/urandom of="$FILES_DIR/test_${size}mb.bin" bs=1M count=$size status=none
  echo "创建测试文件: $FILES_DIR/test_${size}mb.bin"
done

echo "示例数据准备完成，路径: $DATA_DIR"
