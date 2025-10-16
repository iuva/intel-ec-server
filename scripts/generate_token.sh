#!/bin/bash

# ==========================================
# Nacos 认证令牌生成脚本
# ==========================================
# 用途：生成符合 Nacos 要求的 Base64 编码的认证令牌
# 要求：密钥长度至少 32 字节，必须是 Base64 编码

echo "=========================================="
echo "Nacos 认证令牌生成工具"
echo "=========================================="
echo ""

# 检查是否提供了自定义密钥
if [ -n "$1" ]; then
    SECRET_KEY="$1"
else
    # 生成随机的32字节密钥
    SECRET_KEY=$(openssl rand -base64 32 | tr -d '\n')
    echo "生成随机密钥: $SECRET_KEY"
fi

# 检查密钥长度
KEY_LENGTH=${#SECRET_KEY}
if [ $KEY_LENGTH -lt 32 ]; then
    echo "❌ 错误：密钥长度不足 32 字节（当前: $KEY_LENGTH 字节）"
    echo "请提供至少 32 个字符的密钥"
    exit 1
fi

# 生成 Base64 编码的令牌
NACOS_TOKEN=$(echo -n "$SECRET_KEY" | base64 | tr -d '\n')

echo ""
echo "=========================================="
echo "✅ 生成成功！"
echo "=========================================="
echo ""
echo "原始密钥: $SECRET_KEY"
echo "密钥长度: $KEY_LENGTH 字节"
echo ""
echo "Base64 编码的 Nacos 令牌:"
echo "$NACOS_TOKEN"
echo ""
echo "=========================================="
echo "使用方法："
echo "=========================================="
echo ""
echo "1. 在 .env 文件中设置："
echo "   NACOS_AUTH_TOKEN=$NACOS_TOKEN"
echo ""
echo "2. 或在 docker-compose.yml 中直接使用："
echo "   NACOS_AUTH_TOKEN: $NACOS_TOKEN"
echo ""
echo "=========================================="
