# Host Service

## Overview

Host Service is the host management service in the Intel EC microservices architecture, providing host registration, state management, and WebSocket real-time communication functionality.

## Core Functions

- **Host Management**: Host registration, query, and status updates
- **WebSocket Communication**: Real-time bidirectional communication with Agents
- **Status Monitoring**: Real-time monitoring of host status and heartbeats
- **Message Broadcasting**: Supports broadcasting messages to all connected Agents

## Tech Stack

- **Python**: 3.8.10
- **Web Framework**: FastAPI 0.116.1
- **Database**: MariaDB 10.11 (SQLAlchemy async ORM)
- **Cache**: Redis 6.0+
- **Service Discovery**: Nacos
- **Distributed Tracing**: Jaeger + OpenTelemetry
- **Logging**: Loguru
- **WebSocket**: FastAPI WebSocket support

## Port Configuration

- **HTTP Service**: 8003
- **WebSocket**: ws://localhost:8003/ws/agent/{agent_id}

## API Endpoints

### HTTP Endpoints

- `GET /health` - Health check
- `GET /metrics` - Prometheus monitoring metrics
- `GET /api/v1/hosts` - Get host list
- `POST /api/v1/hosts` - Register new host
- `GET /api/v1/hosts/{host_id}` - Get host details
- `PATCH /api/v1/hosts/{host_id}/status` - Update host status

### WebSocket Endpoints

- `WS /ws/agent/{agent_id}` - Agent WebSocket connection

## Environment Variables

```bash
# Service configuration
SERVICE_NAME=host-service
SERVICE_PORT=8003
SERVICE_IP=127.0.0.1

# Database configuration
MYSQL_URL=mysql+aiomysql://root:***REMOVED***word@localhost:3306/intel_cw

# Redis configuration
REDIS_URL=redis://localhost:6379/3

# Nacos configuration
NACOS_SERVER_ADDR=http://localhost:8848

# Jaeger configuration
JAEGER_ENDPOINT=http://localhost:4318/v1/traces

# JWT configuration
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
```

## Local Development

### Install Dependencies

```bash
cd services/host-service
pip install -r requirements.txt
```

### Start Service

> **💡 Tip**: When starting locally, the code will automatically load the `.env` file from the project root directory.

```bash
# Development mode (supports hot reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003
```

**Environment Variable Configuration**:
- If the database is in Docker, you need to set in the `.env` file:
  ```bash
  # macOS/Windows
  MARIADB_HOST=host.docker.internal
  
  # Linux
  MARIADB_HOST=172.17.0.1
  ```
- For detailed configuration instructions, please refer to [Quick Start Guide](../../docs/00-quick-start.md)

### Access Documentation

- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

## Docker Deployment

### Build Image

```bash
docker build -t host-service:latest -f services/host-service/Dockerfile .
```

### Run Container

```bash
docker run -d \
  --name host-service \
  -p 8003:8003 \
  -e MYSQL_URL=mysql+aiomysql://root:***REMOVED***word@mysql:3306/intel_cw \
  -e REDIS_URL=redis://redis:6379/3 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  host-service:latest
```

## WebSocket Usage Examples

### Python Client

```python
import asyncio
import websockets
import json

async def connect_agent():
    uri = "ws://localhost:8003/ws/agent/agent-001"
    
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "type": "heartbeat",
            "agent_id": "agent-001",
            "status": "online"
        }))
        
        # Receive message
        response = await websocket.recv()
        print(f"Received message: {response}")

asyncio.run(connect_agent())
```

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8003/ws/agent/agent-001');

ws.onopen = () => {
    console.log('WebSocket connection established');
    
    // Send message
    ws.send(JSON.stringify({
        type: 'heartbeat',
        agent_id: 'agent-001',
        status: 'online'
    }));
};

ws.onmessage = (event) => {
    console.log('Received message:', event.data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('WebSocket connection closed');
};
```

## Data Models

### Host

```python
{
    "id": 1,
    "host_id": "host-001",
    "hostname": "server-01",
    "ip_address": "192.168.1.100",
    "os_type": "Linux",
    "os_version": "Ubuntu 20.04",
    "status": "online",
    "last_heartbeat": "2025-01-29T10:00:00Z",
    "created_time": "2025-01-29T09:00:00Z",
    "updated_time": "2025-01-29T10:00:00Z"
}
```

## Monitoring and Logging

### Health Check

```bash
curl http://localhost:8003/health
```

### Prometheus Metrics

```bash
curl http://localhost:8003/metrics
```

### Log Viewing

```bash
# Docker logs
docker logs -f host-service

# Local logs
tail -f logs/app.log
```

## Troubleshooting

### Service Cannot Start

1. Check database connection
2. Check Redis connection
3. Check port occupation
4. View log files

### WebSocket Connection Failed

1. Check firewall settings
2. Verify agent_id format
3. Check network connection
4. View service logs

### Nacos Registration Failed

1. Check Nacos service status
2. Verify network connection
3. Check service configuration
4. View heartbeat logs

## Development Guidelines

- Follow PEP 8 code standards
- Use type annotations
- Write English comments
- Implement unit tests
- Pass code quality checks (Ruff, MyPy)

## Related Documents

- [Project Overview Guidelines](../../.cursor/rules/project-overview.mdc)
- [Microservice Architecture Guidelines](../../.cursor/rules/microservice-architecture.mdc)
- [API Design Guidelines](../../.cursor/rules/api-design-standards.mdc)
- [WebSocket Communication Guidelines](../../docs/websocket-guide.md)

## License

MIT License
