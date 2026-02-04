# Gateway Service

## Overview

Gateway Service is the system's API gateway, responsible for unified request entry, route forwarding, load balancing, and authentication validation.

## Core Functions

- **Route Forwarding**: Forward client requests to corresponding backend microservices
- **Load Balancing**: Load balancing based on Nacos service discovery
- **Authentication Validation**: Unified JWT token validation
- **Rate Limiting & Circuit Breaking**: Protect backend services from overload
- **Request Logging**: Record all requests ***REMOVED***ing through the gateway

## Tech Stack

- **Python**: 3.8.10
- **Web Framework**: FastAPI 0.116.1
- **HTTP Client**: httpx
- **Service Discovery**: Nacos
- **Cache**: Redis
- **Monitoring**: Prometheus + Jaeger

## Directory Structure

```text
gateway-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application entry
│   ├── api/                    # API interfaces
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           └── proxy.py    # Proxy endpoints
│   ├── core/                   # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   └── exceptions.py       # Custom exceptions
│   ├── middleware/             # Middleware
│   │   ├── __init__.py
│   │   └── auth_middleware.py  # Authentication middleware
│   └── services/               # Business logic
│       ├── __init__.py
│       ├── proxy_service.py    # Proxy service
│       └── load_balancer.py    # Load balancer
├── Dockerfile
├── requirements.txt
└── README.md
```

## Environment Variables

```bash
# Service configuration
SERVICE_NAME=gateway-service
SERVICE_PORT=8000
SERVICE_IP=172.20.0.100

# Nacos Configuration
NACOS_SERVER_ADDR=http://intel-nacos:8848

# Redis Configuration
REDIS_URL=redis://intel-redis:6379/0

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256

# Authentication Service Configuration
AUTH_SERVICE_URL=http://auth-service:8001             # Gateway default address for HTTP requests
AUTH_SERVICE_BASE_URL=http://localhost:8001          # ✅ Optional: Priority address for WebSocket authentication (automatically fallback when not set)

# Logging Configuration
LOG_LEVEL=INFO
```

## Starting the Service

### Local Development

> **💡 Tip**: When starting locally, the code will automatically load the `.env` file from the project root directory.

> **💡 提示**: 本地启动时，代码会自动加载项目根目录的 `.env` 文件。

```bash
# Install dependencies
pip install -r requirements.txt

# Start service (development mode, supports hot reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Environment Variable Configuration**:
- If the database is in Docker, you need to set in the `.env` file:
  ```bash
  # macOS/Windows
  MARIADB_HOST=host.docker.internal
  REDIS_HOST=host.docker.internal
  
  # Linux
  MARIADB_HOST=172.17.0.1
  REDIS_HOST=172.17.0.1
  ```
- For detailed configuration instructions, please refer to [Quick Start Guide](../../docs/00-quick-start.md) and [Infrastructure Configuration Guide](../../docs/01-infrastructure-config.md)

### Docker Deployment

```bash
# Build image
docker build -t gateway-service:latest .

# Run container
docker run -d \
  --name gateway-service \
  -p 8000:8000 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  -e REDIS_URL=redis://redis:6379/0 \
  gateway-service:latest
```

### Docker Compose

```bash
# Start all services
docker-compose up -d gateway-service

# View logs
docker-compose logs -f gateway-service
```

## API Endpoints

### Health Check

```bash
GET /health
```

### Prometheus Metrics

```bash
GET /metrics
```

### Proxy Forwarding

```bash
# Generic proxy endpoint
GET/POST/PUT/DELETE /{service_name}/{path:path}

# Example
GET /auth-service/api/v1/auth/introspect
GET /host-service/api/v1/host/admin/host/list
```

## Service Route Mapping

| Service Name | Backend Address | Description |
|---------|---------|------|
| auth-service | `http://auth-service:8001` | Authentication service |
| host-service | `http://host-service:8003` | Host service |

## Authentication Flow

1. Client request carries JWT token
2. Gateway validates token validity (by calling auth-service)
3. After validation, forwards request to backend service
4. Returns backend service response

## WebSocket Authentication Instructions

- Gateway will extract WebSocket tokens from the following locations in order:
  1. Query parameter `?token=xxx`
  2. `Authorization: Bearer xxx` header
  3. Custom header `X-Token` / `token`
- When validating Token, it will try the following authentication service addresses in order (automatically fallback when request fails):
  1. Address specified by `AUTH_SERVICE_BASE_URL` environment variable
  2. `auth-service` address obtained through service discovery
  3. `http://auth-service:8001`
  4. `http://localhost:8001`
  5. `http://127.0.0.1:8001`
- Therefore, in local development environment, just ensure the authentication service runs on port `8001` to complete WebSocket authentication.

## Load Balancing Strategy

- **Service Discovery**: Obtain service instance list from Nacos
- **Load Balancing Algorithm**: Weighted random selection
- **Health Checks**: Automatically remove unhealthy instances

## Monitoring Metrics

- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request response time
- `active_connections`: Active connections count
- `service_discovery_errors`: Service discovery error count

## Troubleshooting

### Service Registration Failure

```bash
# Check Nacos connection
curl http://nacos:8848/nacos/v1/ns/operator/metrics

# View service logs
docker-compose logs gateway-service
```

### Authentication Failure

```bash
# Check auth-service connection
curl http://auth-service:8001/health

# Validate JWT token
curl -X POST http://auth-service:8001/api/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -d '{"token": "your-token-here"}'
```

### Request Forwarding Failure

```bash
# Check backend service status
curl http://host-service:8003/health

# View Nacos service list
curl http://nacos:8848/nacos/v1/ns/instance/list?serviceName=host-service
```

## Development Guide

### Adding New Service Routes

Edit `app/services/proxy_service.py`:

```python
self.service_routes = {
    "auth-service": "http://auth-service:8001",
    "host-service": "http://host-service:8003",
    "new-service": "http://new-service:8004",  # Add new service
}
```

### Custom Authentication Logic

Edit `app/middleware/auth_middleware.py`:

```python
# Add public paths
public_paths = {
    "/",
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/new-public-path",  # Add new public path
}
```

## Related Documents

- [Project Overview Guidelines](../../.cursor/rules/project-overview.mdc)
- [Microservice Architecture Guidelines](../../.cursor/rules/microservice-architecture.mdc)
- [API Design Guidelines](../../.cursor/rules/api-design-standards.mdc)
- [Authentication Security Guidelines](../../.cursor/rules/auth-security.mdc)

## Version History

- **v1.0.0** (2025-01-29): Initial version
  - Basic route forwarding functionality
  - Nacos service discovery integration
  - JWT authentication middleware
  - Health check and monitoring endpoints
