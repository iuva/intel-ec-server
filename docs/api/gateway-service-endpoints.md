# 网关服务 API 端点文档

**生成时间**: Wed Oct 15 19:14:34 CST 2025
**服务地址**: http://localhost:8000

## API 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
DELETE | /api/v1/{service_name}/{path} | Proxy Request
POST | /api/v1/{service_name}/{path} | Proxy Request
PUT | /api/v1/{service_name}/{path} | Proxy Request
GET | /api/v1/{service_name}/{path} | Proxy Request
PATCH | /api/v1/{service_name}/{path} | Proxy Request
GET | /api/v1/services | List Services
GET | /api/v1/services/{service_name}/health | Check Service Health
OPTIONS | /api/v1/{path} | Catch All Handler
DELETE | /api/v1/{path} | Catch All Handler
POST | /api/v1/{path} | Catch All Handler
PUT | /api/v1/{path} | Catch All Handler
GET | /api/v1/{path} | Catch All Handler
PATCH | /api/v1/{path} | Catch All Handler
HEAD | /api/v1/{path} | Catch All Handler
GET | / | Root
GET | /health | Health Check
GET | /health/detailed | Detailed Health Check
GET | /metrics | Metrics
OPTIONS | /{path} | Catch All Root Handler
DELETE | /{path} | Catch All Root Handler
POST | /{path} | Catch All Root Handler
PUT | /{path} | Catch All Root Handler
GET | /{path} | Catch All Root Handler
PATCH | /{path} | Catch All Root Handler
HEAD | /{path} | Catch All Root Handler

## 健康检查

- **端点**: http://localhost:8000/health
- **监控**: http://localhost:8000/metrics
