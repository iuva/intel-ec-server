#!/bin/bash

echo "========================================"
echo "Host-Service 完整测试"
echo "========================================"
echo ""

# 1. 管理员登录
echo "📝 步骤 1: 管理员登录"
ADMIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "***REMOVED***word": "***REMOVED***"}')

ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | jq -r '.data.access_token')
echo "✅ Admin Token: ${ADMIN_TOKEN:0:50}..."
echo ""

# 2. 获取活跃 Host
echo "📝 步骤 2: 获取活跃 Host 列表"
curl -s -X GET "http://localhost:8000/api/v1/host/ws/hosts" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
echo ""

# 3. 设备登录
echo "📝 步骤 3: 设备登录"
DEVICE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/device/login" \
  -H "Content-Type: application/json" \
  -d '{"hardware_id": "HW-TEST-001", "mg_id": "MG-001"}')

DEVICE_TOKEN=$(echo $DEVICE_RESPONSE | jq -r '.data.access_token')
echo "✅ Device Token: ${DEVICE_TOKEN:0:50}..."
echo ""

# 4. WebSocket 连接提示
echo "📝 步骤 4: 测试 WebSocket 连接"
echo "使用以下路径:"
echo "ws://localhost:8000/api/v1/ws/host-service/host?token=$DEVICE_TOKEN"
echo ""
echo "测试命令:"
echo "wscat -c 'ws://localhost:8000/api/v1/ws/host-service/host?token=$DEVICE_TOKEN'"
echo ""
echo "========================================"
echo "✅ 测试完成"
echo "========================================"