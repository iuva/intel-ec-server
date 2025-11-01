# Gateway Service (网关服务)

## 概述

Gateway Service 是系统的 API 网关，负责统一的请求入口、路由转发、负载均衡和认证验证。

## 核心功能

- **路由转发**: 将客户端请求转发到对应的后端微服务
- **负载均衡**: 基于 Nacos 服务发现的负载均衡
- **认证验证**: 统一的 JWT 令牌验证
- **限流熔断**: 保护后端服务免受过载
- **请求日志**: 记录所有通过网关的请求

## 技术栈

- **Python**: 3.8.10
- **Web 框架**: FastAPI 0.116.1
- **HTTP 客户端**: httpx
- **服务发现**: Nacos
- **缓存**: Redis
- **监控**: Prometheus + Jaeger

## 目录结构

```text
gateway-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 应用入口
│   ├── api/                    # API 接口
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           └── proxy.py    # 代理端点
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   └── exceptions.py       # 自定义异常
│   ├── middleware/             # 中间件
│   │   ├── __init__.py
│   │   └── auth_middleware.py  # 认证中间件
│   └── services/               # 业务逻辑
│       ├── __init__.py
│       ├── proxy_service.py    # 代理服务
│       └── load_balancer.py    # 负载均衡器
├── Dockerfile
├── requirements.txt
└── README.md
```

## 环境变量

```bash
# 服务配置
SERVICE_NAME=gateway-service
SERVICE_PORT=8000
SERVICE_IP=172.20.0.100

# Nacos 配置
NACOS_SERVER_ADDR=http://intel-nacos:8848

# Redis 配置
REDIS_URL=redis://intel-redis:6379/0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# 认证服务配置
AUTH_SERVICE_URL=http://auth-service:8001

# 日志配置
LOG_LEVEL=INFO
```

## 启动服务

### 本地开发

> **💡 提示**: 本地启动时，代码会自动加载项目根目录的 `.env` 文件。

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（开发模式，支持热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**环境变量配置**:
- 如果数据库在 Docker 中，需要在 `.env` 文件中设置：
  ```bash
  # macOS/Windows
  MARIADB_HOST=host.docker.internal
  REDIS_HOST=host.docker.internal
  
  # Linux
  MARIADB_HOST=172.17.0.1
  REDIS_HOST=172.17.0.1
  ```
- 详细配置说明请参考 [快速开始指南](../../docs/00-quick-start.md) 和 [基础设施配置指南](../../docs/01-infrastructure-config.md)

### Docker 部署

```bash
# 构建镜像
docker build -t gateway-service:latest .

# 运行容器
docker run -d \
  --name gateway-service \
  -p 8000:8000 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  -e REDIS_URL=redis://redis:6379/0 \
  gateway-service:latest
```

### Docker Compose

```bash
# 启动所有服务
docker-compose up -d gateway-service

# 查看日志
docker-compose logs -f gateway-service
```

## API 端点

### 健康检查

```bash
GET /health
```

### Prometheus 指标

```bash
GET /metrics
```

### 代理转发

```bash
# 通用代理端点
GET/POST/PUT/DELETE /{service_name}/{path:path}

# 示例
GET /auth-service/api/v1/auth/introspect
POST /admin-service/api/v1/users
```

## 服务路由映射

| 服务名称 | 后端地址 | 说明 |
|---------|---------|------|
| auth-service | `http://auth-service:8001` | 认证服务 |
| admin-service | `http://admin-service:8002` | 管理服务 |
| host-service | `http://host-service:8003` | 主机服务 |

## 认证流程

1. 客户端请求携带 JWT token
2. 网关验证 token 有效性（调用 auth-service）
3. 验证通过后转发请求到后端服务
4. 返回后端服务响应

## 负载均衡策略

- **服务发现**: 从 Nacos 获取服务实例列表
- **负载均衡算法**: 加权随机选择
- **健康检查**: 自动剔除不健康的实例

## 监控指标

- `http_requests_total`: HTTP 请求总数
- `http_request_duration_seconds`: 请求响应时间
- `active_connections`: 活跃连接数
- `service_discovery_errors`: 服务发现错误数

## 故障排查

### 服务注册失败

```bash
# 检查 Nacos 连接
curl http://nacos:8848/nacos/v1/ns/operator/metrics

# 查看服务日志
docker-compose logs gateway-service
```

### 认证失败

```bash
# 检查 auth-service 连接
curl http://auth-service:8001/health

# 验证 JWT token
curl -X POST http://auth-service:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "your-token-here"}'
```

### 请求转发失败

```bash
# 检查后端服务状态
curl http://admin-service:8002/health

# 查看 Nacos 服务列表
curl http://nacos:8848/nacos/v1/ns/instance/list?serviceName=admin-service
```

## 开发指南

### 添加新的服务路由

编辑 `app/services/proxy_service.py`:

```python
self.service_routes = {
    "auth-service": "http://auth-service:8001",
    "admin-service": "http://admin-service:8002",
    "host-service": "http://host-service:8003",
    "new-service": "http://new-service:8004",  # 添加新服务
}
```

### 自定义认证逻辑

编辑 `app/middleware/auth_middleware.py`:

```python
# 添加公开路径
public_paths = {
    "/",
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/new-public-path",  # 添加新的公开路径
}
```

## 相关文档

- [项目总体规范](../../.cursor/rules/project-overview.mdc)
- [微服务架构规范](../../.cursor/rules/microservice-architecture.mdc)
- [API 设计规范](../../.cursor/rules/api-design-standards.mdc)
- [认证安全规范](../../.cursor/rules/auth-security.mdc)

## 版本历史

- **v1.0.0** (2025-01-29): 初始版本
  - 基础路由转发功能
  - Nacos 服务发现集成
  - JWT 认证中间件
  - 健康检查和监控端点
