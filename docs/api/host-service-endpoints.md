# 主机服务 API 端点文档

**生成时间**: Wed Oct 15 19:14:34 CST 2025
**服务地址**: http://localhost:8003

## API 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
GET | /health | Health Check
GET | / | Root
GET | /metrics | Metrics
GET | /api/v1/hosts | 获取主机列表
POST | /api/v1/hosts | 注册主机
GET | /api/v1/hosts/{host_id} | 获取主机详情
PUT | /api/v1/hosts/{host_id} | 更新主机信息
DELETE | /api/v1/hosts/{host_id} | 删除主机
PATCH | /api/v1/hosts/{host_id}/status | 更新主机状态
GET | /api/v1/ws/connections | Get Active Connections
POST | /api/v1/ws/broadcast | Broadcast Message
GET | /{path} | Catch All Handler
OPTIONS | /{path} | Catch All Handler
PATCH | /{path} | Catch All Handler
PUT | /{path} | Catch All Handler
DELETE | /{path} | Catch All Handler
POST | /{path} | Catch All Handler
HEAD | /{path} | Catch All Handler

## 健康检查

- **端点**: http://localhost:8003/health
- **监控**: http://localhost:8003/metrics
