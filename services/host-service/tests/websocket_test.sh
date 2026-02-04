#!/bin/bash

echo "========================================"
echo "Host-Service Complete Test"
echo "========================================"
echo ""

# 1. Admin Login
echo "📝 Step 1: Admin Login"

# Check if ***REMOVED***word is provided via environment variable
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ Error: ADMIN_PASSWORD environment variable is not set."
    echo "Usage: ADMIN_PASSWORD=your_***REMOVED***word ./websocket_test.sh"
    exit 1
else
    echo "🔒 Using provided ADMIN_PASSWORD from environment."
fi

ADMIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"admin\", \"***REMOVED***word\": \"$ADMIN_PASSWORD\"}")

ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | jq -r '.data.access_token')
echo "✅ Admin Token: ${ADMIN_TOKEN:0:50}..."
echo ""

# 2. Get active Hosts
echo "📝 Step 2: Get active Host list"
curl -s -X GET "http://localhost:8000/api/v1/host/ws/hosts" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
echo ""

# 3. Device Login
echo "📝 Step 3: Device Login"
DEVICE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/device/login" \
  -H "Content-Type: application/json" \
  -d '{"hardware_id": "HW-TEST-001", "mg_id": "MG-001"}')

DEVICE_TOKEN=$(echo $DEVICE_RESPONSE | jq -r '.data.access_token')
echo "✅ Device Token: ${DEVICE_TOKEN:0:50}..."
echo ""

# 4. WebSocket connection prompt
echo "📝 Step 4: Test WebSocket connection"
echo "Use the following path:"
echo "ws://localhost:8000/api/v1/ws/host-service/host?token=$DEVICE_TOKEN"
echo ""
echo "Test command:"
echo "wscat -c 'ws://localhost:8000/api/v1/ws/host-service/host?token=$DEVICE_TOKEN'"
echo ""
echo "========================================"
echo "✅ Test completed"
echo "========================================"