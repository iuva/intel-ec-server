# Gateway 负载均衡故障排查指南

## 🔍 问题：配置了 HOST_SERVICE_INSTANCES 但没有轮询

### 排查步骤

#### 1. 检查环境变量是否设置

```bash
# 检查环境变量
echo $HOST_SERVICE_INSTANCES

# 应该输出类似：
# 127.0.0.1:8003,127.0.0.1:8004
```

**如果输出为空**，说明环境变量未设置，需要设置：

```bash
# 方式 1：临时设置（当前终端有效）
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"
export LOAD_BALANCE_STRATEGY="round_robin"

# 方式 2：使用 .env 文件（推荐）
echo "HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004" >> .env
echo "LOAD_BALANCE_STRATEGY=round_robin" >> .env
```

#### 2. 检查 Gateway 启动日志

启动 Gateway 时，应该看到类似日志：

```
✅ 加载本地多实例配置: host-service
instances_count: 2
instances: ['127.0.0.1:8003', '127.0.0.1:8004']
```

**如果没有看到这个日志**，说明环境变量在 Gateway 启动时未读取。

#### 3. 确保 Gateway 在设置环境变量后启动

**重要**：环境变量必须在 Gateway 启动**之前**设置！

```bash
# ✅ 正确：先设置环境变量，再启动
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# ❌ 错误：先启动，再设置环境变量（不会生效）
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 在另一个终端设置环境变量（不会生效！）
```

#### 4. 使用测试脚本验证配置

运行测试脚本：

```bash
# 设置环境变量
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"
export LOAD_BALANCE_STRATEGY="round_robin"

# 运行测试脚本
python scripts/test_load_balancing.py
```

应该看到输出：

```
请求  1: http://127.0.0.1:8003
请求  2: http://127.0.0.1:8004
请求  3: http://127.0.0.1:8003
请求  4: http://127.0.0.1:8004
...
```

#### 5. 检查 Gateway 日志

发送请求时，查看 Gateway 日志：

```bash
# 发送请求
curl -X POST "http://localhost:8000/api/v1/host/hosts/available" \
  -H "Content-Type: application/json" \
  -d '{"tc_id":"test","cycle_name":"test","user_name":"test","page_size":20}'
```

应该看到日志：

```
从本地配置获取服务地址: host-service -> http://127.0.0.1:8003
从本地配置获取服务地址: host-service -> http://127.0.0.1:8004
```

**如果看到 "使用后备服务地址"**，说明本地配置未加载。

## 🛠️ 常见问题及解决方案

### 问题 1：环境变量设置了但 Gateway 未读取

**原因**：
- Gateway 在设置环境变量之前启动
- 环境变量设置在不同的终端/进程

**解决**：
1. 停止 Gateway
2. 在同一终端设置环境变量
3. 在同一终端启动 Gateway

```bash
# 停止 Gateway（Ctrl+C）

# 设置环境变量
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"
export LOAD_BALANCE_STRATEGY="round_robin"

# 启动 Gateway（在同一终端）
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 问题 2：环境变量格式错误

**错误格式**：
```bash
# ❌ 错误：缺少端口
HOST_SERVICE_INSTANCES="127.0.0.1,127.0.0.1"

# ❌ 错误：使用空格分隔
HOST_SERVICE_INSTANCES="127.0.0.1:8003 127.0.0.1:8004"

# ❌ 错误：端口不是数字
HOST_SERVICE_INSTANCES="127.0.0.1:abc,127.0.0.1:8004"
```

**正确格式**：
```bash
# ✅ 正确：IP:PORT,IP:PORT
HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"

# ✅ 正确：可以包含空格（会自动trim）
HOST_SERVICE_INSTANCES="127.0.0.1:8003, 127.0.0.1:8004"
```

### 问题 3：Nacos 管理器存在但未连接

**现象**：
- Gateway 日志显示 "从 Nacos 获取服务地址" 但失败
- 然后使用后备地址而不是本地配置

**原因**：
- Nacos 管理器已初始化但连接失败
- 代码优先尝试 Nacos，失败后才检查本地配置

**解决**：
1. 禁用 Nacos（如果不需要）：
   ```bash
   export ENABLE_NACOS=false
   ```

2. 或者确保 Nacos 正常工作

### 问题 4：服务名称不匹配

**检查**：
- Gateway 使用短名称 `"host"` 调用
- 代码会映射为 `"host-service"`
- 环境变量必须是 `HOST_SERVICE_INSTANCES`（对应 `host-service`）

**验证**：
```bash
# 检查环境变量名称
env | grep HOST_SERVICE_INSTANCES

# 应该输出：
# HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004
```

## 📋 完整配置示例

### 本地开发环境（不使用 Nacos）

```bash
# 1. 设置环境变量
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"
export LOAD_BALANCE_STRATEGY="round_robin"
export ENABLE_NACOS=false  # 禁用 Nacos

# 2. 启动两个 host-service 实例
# 终端 1
cd services/host-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003

# 终端 2
cd services/host-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004

# 3. 启动 Gateway（在设置环境变量的同一终端）
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 使用 .env 文件（推荐）

创建 `.env` 文件：

```bash
# .env
HOST_SERVICE_INSTANCES=127.0.0.1:8003,127.0.0.1:8004
LOAD_BALANCE_STRATEGY=round_robin
ENABLE_NACOS=false
```

然后启动 Gateway：

```bash
# 使用 python-dotenv 加载 .env（如果已配置）
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔧 调试技巧

### 1. 启用详细日志

在 Gateway 启动时设置日志级别：

```bash
export LOG_LEVEL=DEBUG
cd services/gateway-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 检查服务发现实例状态

在 Gateway 代码中添加调试代码：

```python
# 在 proxy_service.py 的 get_service_url 方法中添加
logger.info(f"服务发现实例: {self.service_discovery}")
logger.info(f"本地实例配置: {self.service_discovery._local_instances}")
```

### 3. 使用测试脚本

```bash
# 设置环境变量
export HOST_SERVICE_INSTANCES="127.0.0.1:8003,127.0.0.1:8004"

# 运行测试
python scripts/test_load_balancing.py
```

## ✅ 验证清单

- [ ] 环境变量 `HOST_SERVICE_INSTANCES` 已设置
- [ ] 环境变量格式正确：`IP:PORT,IP:PORT`
- [ ] Gateway 在设置环境变量**之后**启动
- [ ] Gateway 启动日志显示 "✅ 加载本地多实例配置"
- [ ] 发送多个请求时，日志显示不同的地址
- [ ] 两个 host-service 实例都在运行

## 📞 如果仍然无法解决

1. 检查 Gateway 启动日志，查找 "加载本地多实例配置" 相关日志
2. 运行测试脚本 `python scripts/test_load_balancing.py` 验证配置
3. 检查环境变量是否在正确的进程中设置
4. 确认 Gateway 服务已重启以加载新配置

