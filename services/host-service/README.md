# Host Service (主机服务)

## 概述

Host Service 是 Intel EC 微服务架构中的主机管理服务，提供主机注册、状态管理和 WebSocket 实时通信功能。

## 核心功能

- **主机管理**: 主机注册、查询、状态更新
- **WebSocket 通信**: 与 Agent 进行实时双向通信
- **状态监控**: 实时监控主机状态和心跳
- **消息广播**: 支持向所有连接的 Agent 广播消息

## 技术栈

- **Python**: 3.8.10
- **Web 框架**: FastAPI 0.116.1
- **数据库**: MariaDB 10.11 (SQLAlchemy 异步 ORM)
- **缓存**: Redis 6.0+
- **服务发现**: Nacos
- **分布式追踪**: Jaeger + OpenTelemetry
- **日志**: Loguru
- **WebSocket**: FastAPI WebSocket 支持

## 端口配置

- **HTTP 服务**: 8003
- **WebSocket**: ws://localhost:8003/ws/agent/{agent_id}

## API 端点

### HTTP 端点

- `GET /health` - 健康检查
- `GET /metrics` - Prometheus 监控指标
- `GET /api/v1/hosts` - 获取主机列表
- `POST /api/v1/hosts` - 注册新主机
- `GET /api/v1/hosts/{host_id}` - 获取主机详情
- `PATCH /api/v1/hosts/{host_id}/status` - 更新主机状态

### WebSocket 端点

- `WS /ws/agent/{agent_id}` - Agent WebSocket 连接

## 环境变量

```bash
# 服务配置
SERVICE_NAME=host-service
SERVICE_PORT=8003
SERVICE_IP=127.0.0.1

# 数据库配置
MYSQL_URL=mysql+aiomysql://root:***REMOVED***word@localhost:3306/intel_cw

# Redis 配置
REDIS_URL=redis://localhost:6379/3

# Nacos 配置
NACOS_SERVER_ADDR=http://localhost:8848

# Jaeger 配置
JAEGER_ENDPOINT=http://localhost:4318/v1/traces

# JWT 配置
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
```

## 本地开发

### 安装依赖

```bash
cd services/host-service
pip install -r requirements.txt
```

### 启动服务

> **💡 提示**: 本地启动时，代码会自动加载项目根目录的 `.env` 文件。

```bash
# 开发模式（支持热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# 生产模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003
```

**环境变量配置**:
- 如果数据库在 Docker 中，需要在 `.env` 文件中设置：
  ```bash
  # macOS/Windows
  MARIADB_HOST=host.docker.internal
  
  # Linux
  MARIADB_HOST=172.17.0.1
  ```
- 详细配置说明请参考 [快速开始指南](../../docs/00-quick-start.md#步骤-7-本地启动微服务非-docker-方式)

### 访问文档

- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

## Docker 部署

### 构建镜像

```bash
docker build -t host-service:latest -f services/host-service/Dockerfile .
```

### 运行容器

```bash
docker run -d \
  --name host-service \
  -p 8003:8003 \
  -e MYSQL_URL=mysql+aiomysql://root:***REMOVED***word@mysql:3306/intel_cw \
  -e REDIS_URL=redis://redis:6379/3 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  host-service:latest
```

## WebSocket 使用示例

### Python 客户端

```python
import asyncio
import websockets
import json

async def connect_agent():
    uri = "ws://localhost:8003/ws/agent/agent-001"
    
    async with websockets.connect(uri) as websocket:
        # 发送消息
        await websocket.send(json.dumps({
            "type": "heartbeat",
            "agent_id": "agent-001",
            "status": "online"
        }))
        
        # 接收消息
        response = await websocket.recv()
        print(f"收到消息: {response}")

asyncio.run(connect_agent())
```

### JavaScript 客户端

```javascript
const ws = new WebSocket('ws://localhost:8003/ws/agent/agent-001');

ws.onopen = () => {
    console.log('WebSocket 连接已建立');
    
    // 发送消息
    ws.send(JSON.stringify({
        type: 'heartbeat',
        agent_id: 'agent-001',
        status: 'online'
    }));
};

ws.onmessage = (event) => {
    console.log('收到消息:', event.data);
};

ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
    console.log('WebSocket 连接已关闭');
};
```

## 数据模型

### Host (主机)

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

## 监控和日志

### 健康检查

```bash
curl http://localhost:8003/health
```

### Prometheus 指标

```bash
curl http://localhost:8003/metrics
```

### 日志查看

```bash
# Docker 日志
docker logs -f host-service

# 本地日志
tail -f logs/app.log
```

## 故障排查

### 服务无法启动

1. 检查数据库连接
2. 检查 Redis 连接
3. 检查端口占用
4. 查看日志文件

### WebSocket 连接失败

1. 检查防火墙设置
2. 验证 agent_id 格式
3. 检查网络连接
4. 查看服务日志

### Nacos 注册失败

1. 检查 Nacos 服务状态
2. 验证网络连接
3. 检查服务配置
4. 查看心跳日志

## 开发规范

- 遵循 PEP 8 代码规范
- 使用类型注解
- 编写中文注释
- 实现单元测试
- 通过代码质量检查 (Ruff, MyPy)

## 相关文档

- [项目总体规范](../../.cursor/rules/project-overview.mdc)
- [微服务架构规范](../../.cursor/rules/microservice-architecture.mdc)
- [API 设计规范](../../.cursor/rules/api-design-standards.mdc)
- [WebSocket 通信规范](../../docs/websocket-guide.md)

## 许可证

MIT License
