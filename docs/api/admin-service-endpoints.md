# 管理服务 API 端点文档

**生成时间**: Wed Oct 15 19:14:34 CST 2025
**服务地址**: http://localhost:8002

## API 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
GET | /health | Health Check
GET | /metrics | Metrics
GET | /api/v1/users | List Users
POST | /api/v1/users | Create User
GET | /api/v1/users/{user_id} | Get User
PUT | /api/v1/users/{user_id} | Update User
DELETE | /api/v1/users/{user_id} | Delete User
GET | / | Root
PUT | /{path} | Catch All Handler
GET | /{path} | Catch All Handler
POST | /{path} | Catch All Handler
PATCH | /{path} | Catch All Handler
HEAD | /{path} | Catch All Handler
DELETE | /{path} | Catch All Handler
OPTIONS | /{path} | Catch All Handler

## 健康检查

- **端点**: http://localhost:8002/health
- **监控**: http://localhost:8002/metrics
