# 认证服务 API 端点文档

**生成时间**: Wed Oct 15 19:14:34 CST 2025
**服务地址**: http://localhost:8001

## API 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
GET | /health | Health Check
GET | /metrics | Metrics
GET | /test | Test Endpoint
POST | /api/v1/auth/refresh | Refresh Token
POST | /api/v1/auth/introspect | Introspect Token
POST | /api/v1/auth/logout | Logout
POST | /api/v1/oauth2/admin/token | Admin Token
POST | /api/v1/oauth2/device/token | Device Token
POST | /api/v1/oauth2/introspect | Introspect Token
POST | /api/v1/oauth2/revoke | Revoke Token
GET | / | Root

## 健康检查

- **端点**: http://localhost:8001/health
- **监控**: http://localhost:8001/metrics
