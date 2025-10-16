#!/bin/bash
# 创建 MariaDB 数据库脚本

echo "🔧 创建 MariaDB 数据库..."

# 从 .env 文件读取配置
source .env

# 创建数据库
mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

if [ $? -eq 0 ]; then
    echo "✅ 数据库创建成功: ${MYSQL_DATABASE}"
else
    echo "❌ 数据库创建失败"
    exit 1
fi

# 验证数据库
mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" -e "SHOW DATABASES LIKE '${MYSQL_DATABASE}';"

echo "✅ 完成！"
