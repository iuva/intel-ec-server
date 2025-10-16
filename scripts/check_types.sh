#!/bin/bash
# Pyright 类型检查脚本
# 自动设置 PYTHONPATH 并运行 pyright

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 设置 PYTHONPATH 为项目根目录
export PYTHONPATH="$PROJECT_ROOT"

echo "🔍 运行 Pyright 类型检查..."
echo "📁 项目根目录: $PROJECT_ROOT"
echo "🐍 PYTHONPATH: $PYTHONPATH"
echo ""

# 运行 pyright
cd "$PROJECT_ROOT"
pyright services/ shared/ "$@"

# 保存退出码
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 类型检查通过！"
else
    echo "❌ 类型检查发现 ${EXIT_CODE} 个问题"
fi

exit $EXIT_CODE
