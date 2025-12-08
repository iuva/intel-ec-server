# Gateway 负载均衡配置指南

## 🎯 概述

Gateway 服务支持多种负载均衡策略，可以自动在多个服务实例之间分配请求负载。

## 📋 支持的负载均衡策略

### 1. 轮询（Round Robin）- 默认策略

**特点**：
- 按顺序依次选择服务实例
- 确保每个实例获得相等的请求量
- 适合实例性能相近的场景

**配置**：
```bash
LOAD_BALANCE_STRATEGY=round_robin
```

### 2. 随机（Random）

**特点**：
- 随机选择服务实例
- 适合实例性能相近的场景

**配置**：
```bash
LOAD_BALANCE_STRATEGY=random
```

### 3. 加权随机（Weighted Random）

**特点**：
- 根据实例权重进行随机选择
- 权重越高，被选中的概率越大
- 适合实例性能不同的场景

**配置**：
```bash
LOAD_BALANCE_STRATEGY=weighted_random
```

**注意**：权重需要在 Nacos 中配置每个服务实例的 `weight` 字段。

## 🚀 快速开始

### 方式一：使用 Nacos 服务发现（生产环境推荐）

#### 1. 启动多个 host-service 实例

```bash
# 实例 1（端口 8003）
cd services/host-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003

# 实例 2（端口 8004）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

#### 2. 配置环境变量

在 `docker-compose.yml` 或 `.env` 文件中：

```yaml
services:
  gateway-service:
    environment:
      # 负载均衡策略（可选值：round_robin, random, weighted_random）
      LOAD_BALANCE_STRATEGY: round_robin
```

#### 3. 确保服务注册到 Nacos

两个 host-service 实例都需要注册到 Nacos：

```bash
# 实例 1
HOST_SERVICE_NAME=host-service
HOST_SERVICE_PORT=8003
HOST_SERVICE_IP=172.20.0.103

# 实例 2
HOST_SERVICE_NAME=host-service
HOST_SERVICE_PORT=8004
HOST_SERVICE_IP=172.20.0.104
```

### 方式二：本地开发环境（无需 Nacos）

#### 1. 启动多个 host-service 实例

```bash
# 终端 1：实例 1（端口 8003）
cd services/host-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003

# 终端 2：实例 2（端口 8004）
cd services/host-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

#### 2. 配置 Gateway 环境变量

在启动 Gateway 前设置环境变量：

```bash
# 方式 1：使用 .env 文件
echo "HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004" >> .env
echo "LOAD_BALANCE_STRATEGY=round_robin" >> .env

# 方式 2：直接设置环境变量
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"
export LOAD_BALANCE_STRATEGY="round_robin"

# 启动 Gateway
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**环境变量格式说明**：
- `HOST_SERVICE_INSTANCES`: 多个实例地址，用逗号分隔
  - 格式：`IP:PORT,IP:PORT`
  - 示例：`127.0.0.1:8003,127.0.0.1:8004`
- `AUTH_SERVICE_INSTANCES`: Auth 服务的多个实例（如果需要）
- `LOAD_BALANCE_STRATEGY`: 负载均衡策略（默认：`round_robin`）

#### 3. 验证本地轮询

发送多个请求，观察 Gateway 日志：

```bash
# 发送 10 个请求
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/host/hosts/available" \
    -H "Content-Type: application/json" \
    -d '{"tc_id":"test","cycle_name":"test","user_name":"test","page_size":20}'
  echo ""
done
```

在 Gateway 日志中应该看到请求被轮询分发：

```
从本地配置获取服务地址: host-service -> http://127.0.0.1:8003
从本地配置获取服务地址: host-service -> http://127.0.0.1:8004
从本地配置获取服务地址: host-service -> http://127.0.0.1:8003
从本地配置获取服务地址: host-service -> http://127.0.0.1:8004
...
```

## 🔍 验证负载均衡

### 使用 Nacos 时

#### 1. 检查 Nacos 服务列表

访问 Nacos 控制台或使用 API：

```bash
curl "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=host-service"
```

应该看到两个实例：
```json
{
  "hosts": [
    {
      "ip": "172.20.0.103",
      "port": 8003,
      "healthy": true,
      "weight": 1.0
    },
    {
      "ip": "172.20.0.104",
      "port": 8004,
      "healthy": true,
      "weight": 1.0
    }
  ]
}
```

#### 2. 测试请求分发

发送多个请求，观察日志：

```bash
# 发送 10 个请求
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/host/hosts/available" \
    -H "Content-Type: application/json" \
    -d '{"tc_id":"test","cycle_name":"test","user_name":"test","page_size":20}'
  echo ""
done
```

在 Gateway 日志中应该看到请求被分发到不同的实例：

```
从 Nacos 获取服务地址: host-service -> http://172.20.0.103:8003
从 Nacos 获取服务地址: host-service -> http://172.20.0.104:8004
从 Nacos 获取服务地址: host-service -> http://172.20.0.103:8003
从 Nacos 获取服务地址: host-service -> http://172.20.0.104:8004
...
```

### 本地开发（无 Nacos）时

#### 1. 检查环境变量配置

```bash
echo $HOST_SERVICE_INSTANCES
# 应该输出: 127.0.0.1:8003,127.0.0.1:8004
```

#### 2. 测试请求分发

发送多个请求，观察 Gateway 日志：

```bash
# 发送 10 个请求
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/host/hosts/available" \
    -H "Content-Type: application/json" \
    -d '{"tc_id":"test","cycle_name":"test","user_name":"test","page_size":20}'
  echo ""
done
```

在 Gateway 日志中应该看到请求被轮询分发：

```
从本地配置获取服务地址: host-service -> http://127.0.0.1:8003
从本地配置获取服务地址: host-service -> http://127.0.0.1:8004
从本地配置获取服务地址: host-service -> http://127.0.0.1:8003
从本地配置获取服务地址: host-service -> http://127.0.0.1:8004
...
```

## 📊 轮询算法工作原理

### 实现原理

1. **获取实例列表**：
   - 优先从 Nacos 获取所有健康的服务实例
   - 如果没有 Nacos，从环境变量 `*_SERVICE_INSTANCES` 读取本地实例配置
   - 最后回退到单个后备地址
2. **维护计数器**：为每个服务维护一个轮询索引
3. **选择实例**：根据索引选择实例，然后递增索引
4. **循环使用**：索引达到列表长度时重置为 0

### 代码示例

```python
# 轮询选择逻辑
def _select_instance_round_robin(self, instances, service_name):
    # 初始化或获取当前索引
    if service_name not in self._round_robin_index:
        self._round_robin_index[service_name] = 0
    
    current_index = self._round_robin_index[service_name]
    
    # 选择实例
    selected_instance = instances[current_index % len(instances)]
    
    # 更新索引（下次使用下一个实例）
    self._round_robin_index[service_name] = (current_index + 1) % len(instances)
    
    return selected_instance
```

## ⚙️ 高级配置

### 缓存配置

服务实例列表会被缓存，默认缓存时间 30 秒：

```python
# 在 gateway-service/app/main.py 中
service_discovery = init_service_discovery(
    cache_ttl=30,  # 缓存时间（秒）
    load_balance_strategy="round_robin",
)
```

### 健康检查

只有健康的实例才会被选中：

- Nacos 会自动标记不健康的实例
- 不健康的实例会被自动排除
- 实例恢复健康后会自动加入负载均衡

## 🐛 故障排查

### 问题 1：请求总是路由到同一个实例

**原因**：
- 缓存未过期，一直使用缓存的实例
- 只有一个实例注册到 Nacos 或配置在环境变量中
- 本地开发时未配置 `*_SERVICE_INSTANCES` 环境变量

**解决**：
1. **使用 Nacos 时**：
   - 检查 Nacos 中是否有多个实例
   - 等待缓存过期（默认 30 秒）或重启 Gateway
   - 检查两个实例是否都正常注册到 Nacos
2. **本地开发时**：
   - 检查是否设置了 `HOST_SERVICE_INSTANCES` 环境变量
   - 确认环境变量格式正确：`127.0.0.1:8003,127.0.0.1:8004`
   - 重启 Gateway 服务使配置生效

### 问题 2：负载不均衡

**原因**：
- 使用了随机策略而非轮询
- 实例权重不同

**解决**：
1. 确认 `LOAD_BALANCE_STRATEGY=round_robin`
2. 检查 Nacos 中实例的权重配置

### 问题 3：服务发现失败

**原因**：
- Nacos 未启动或不可达
- 服务未注册到 Nacos
- 本地开发时未配置环境变量

**解决**：
1. **使用 Nacos 时**：
   - 检查 Nacos 连接状态
   - 检查服务注册日志
   - Gateway 会自动回退到后备地址（Docker 服务名或 localhost）
2. **本地开发时**：
   - 配置 `HOST_SERVICE_INSTANCES` 环境变量支持多实例轮询
   - 如果未配置，Gateway 会使用单个后备地址（`127.0.0.1:8003`）

## 📝 最佳实践

1. **使用轮询策略**：适合大多数场景，确保负载均衡
2. **监控实例健康**：确保不健康的实例被及时排除
3. **合理设置缓存**：缓存时间过短会增加 Nacos 压力，过长会影响实例发现
4. **配置实例权重**：如果实例性能不同，使用加权随机策略
5. **本地开发**：使用环境变量配置多实例，无需启动 Nacos 即可测试负载均衡
6. **生产环境**：使用 Nacos 服务发现，自动管理实例健康状态

## 🔗 相关文档

- [Nacos 服务发现配置规范](../.cursor/rules/nacos-configuration.mdc)
- [Gateway 服务文档](../services/gateway-service/README.md)
- [API 负载测试计划](./34-api-load-testing-plan.md)

