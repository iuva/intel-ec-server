#!/bin/bash

# 日志格式检查脚本
# 用于检查项目中的日志记录是否符合统一标准

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "日志格式检查工具"
echo "========================================="
echo ""

# 检查 1: 查找使用 f-string 格式化的日志
echo -e "${YELLOW}检查 1: 查找使用 f-string 格式化的日志${NC}"
echo "----------------------------------------"

FSTRING_LOGS=$(grep -rn 'logger\.\(info\|debug\|warning\|error\|critical\)(f"' services/ shared/ 2>/dev/null | \
    grep -v "\.pyc" | \
    grep -v "__pycache__" | \
    grep -v "\.git" || true)

if [ -z "$FSTRING_LOGS" ]; then
    echo -e "${GREEN}✓ 未发现使用 f-string 格式化的日志${NC}"
else
    echo -e "${RED}✗ 发现使用 f-string 格式化的日志:${NC}"
    echo "$FSTRING_LOGS"
    echo ""
fi

# 检查 2: 查找缺少 extra 参数的日志（排除已知的正确格式）
echo ""
echo -e "${YELLOW}检查 2: 查找可能缺少结构化信息的日志${NC}"
echo "----------------------------------------"

# 这个检查会有一些误报，因为有些日志可能在下一行有 extra 参数
MISSING_EXTRA=$(grep -rn 'logger\.\(info\|warning\|error\)(' services/ shared/ 2>/dev/null | \
    grep -v "extra=" | \
    grep -v "\.pyc" | \
    grep -v "__pycache__" | \
    grep -v "\.git" | \
    grep -v "LOGGING" | \
    head -20 || true)

if [ -z "$MISSING_EXTRA" ]; then
    echo -e "${GREEN}✓ 所有日志都使用了结构化格式${NC}"
else
    echo -e "${YELLOW}⚠ 发现可能缺少结构化信息的日志（前20条）:${NC}"
    echo "$MISSING_EXTRA"
    echo ""
    echo -e "${YELLOW}注意: 这可能包含误报，请手动检查${NC}"
fi

# 检查 3: 查找 ERROR 日志是否包含 exc_info
echo ""
echo -e "${YELLOW}检查 3: 查找可能缺少 exc_info 的 ERROR 日志${NC}"
echo "----------------------------------------"

MISSING_EXC_INFO=$(grep -rn 'logger\.error(' services/ shared/ 2>/dev/null | \
    grep -v "exc_info=" | \
    grep -v "\.pyc" | \
    grep -v "__pycache__" | \
    grep -v "\.git" | \
    grep -v "LOGGING" | \
    head -15 || true)

if [ -z "$MISSING_EXC_INFO" ]; then
    echo -e "${GREEN}✓ 所有 ERROR 日志都包含 exc_info${NC}"
else
    echo -e "${YELLOW}⚠ 发现可能缺少 exc_info 的 ERROR 日志（前15条）:${NC}"
    echo "$MISSING_EXC_INFO"
    echo ""
    echo -e "${YELLOW}注意: 并非所有 ERROR 日志都需要 exc_info，请根据情况判断${NC}"
fi

# 检查 4: 统计日志使用情况
echo ""
echo -e "${YELLOW}检查 4: 日志使用统计${NC}"
echo "----------------------------------------"

INFO_COUNT=$(grep -r 'logger\.info(' services/ shared/ 2>/dev/null | grep -v "\.pyc" | grep -v "__pycache__" | wc -l || echo "0")
DEBUG_COUNT=$(grep -r 'logger\.debug(' services/ shared/ 2>/dev/null | grep -v "\.pyc" | grep -v "__pycache__" | wc -l || echo "0")
WARNING_COUNT=$(grep -r 'logger\.warning(' services/ shared/ 2>/dev/null | grep -v "\.pyc" | grep -v "__pycache__" | wc -l || echo "0")
ERROR_COUNT=$(grep -r 'logger\.error(' services/ shared/ 2>/dev/null | grep -v "\.pyc" | grep -v "__pycache__" | wc -l || echo "0")
CRITICAL_COUNT=$(grep -r 'logger\.critical(' services/ shared/ 2>/dev/null | grep -v "\.pyc" | grep -v "__pycache__" | wc -l || echo "0")

TOTAL_COUNT=$((INFO_COUNT + DEBUG_COUNT + WARNING_COUNT + ERROR_COUNT + CRITICAL_COUNT))

echo "INFO:     $INFO_COUNT"
echo "DEBUG:    $DEBUG_COUNT"
echo "WARNING:  $WARNING_COUNT"
echo "ERROR:    $ERROR_COUNT"
echo "CRITICAL: $CRITICAL_COUNT"
echo "----------------------------------------"
echo "总计:     $TOTAL_COUNT"

# 检查 5: 查找可能包含敏感信息的日志
echo ""
echo -e "${YELLOW}检查 5: 查找可能包含敏感信息的日志${NC}"
echo "----------------------------------------"

<<<<<<< HEAD
SENSITIVE_LOGS=$(grep -rn 'logger\.\(info\|debug\|warning\|error\).*\(***REMOVED***word\|secret\|token\|key\)' services/ shared/ 2>/dev/null | \
    grep -v "\.pyc" | \
    grep -v "__pycache__" | \
    grep -v "\.git" | \
    grep -v "***REMOVED***word_hash" | \
=======
SENSITIVE_LOGS=$(grep -rn 'logger\.\(info\|debug\|warning\|error\).*\(***REMOVED***word\|secret\|token\|key\)' services/ shared/ 2>/dev/null | \
    grep -v "\.pyc" | \
    grep -v "__pycache__" | \
    grep -v "\.git" | \
    grep -v "***REMOVED***word_hash" | \
>>>>>>> 8582c20 (chore(project-setup): 更新项目配置和文档结构)
    grep -v "secret_key" | \
    grep -v "JWT_SECRET_KEY" | \
    grep -v "# " || true)

if [ -z "$SENSITIVE_LOGS" ]; then
    echo -e "${GREEN}✓ 未发现可能包含敏感信息的日志${NC}"
else
    echo -e "${RED}✗ 发现可能包含敏感信息的日志:${NC}"
    echo "$SENSITIVE_LOGS"
    echo ""
    echo -e "${RED}警告: 请确保不要在日志中记录密码、密钥等敏感信息${NC}"
fi

# 总结
echo ""
echo "========================================="
echo "检查完成"
echo "========================================="
echo ""
echo "建议:"
echo "1. 查看 shared/common/LOGGING_STANDARDS.md 了解日志标准"
echo "2. 查看 shared/common/LOGGING_MIGRATION_GUIDE.md 了解迁移指南"
echo "3. 使用结构化日志格式，包含 operation 和相关上下文信息"
echo "4. ERROR 日志应包含 exc_info=True 以记录完整堆栈"
echo "5. 避免在日志中记录敏感信息"
echo ""
