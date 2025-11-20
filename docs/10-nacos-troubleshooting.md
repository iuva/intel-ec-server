# Nacos 服务发现故障排查指南

## 常见问题

### 1. JWT Token 配置错误

#### 错误信息

```
java.lang.IllegalArgumentException: the length of must great than or equal 32 bytes; 
And the secret key must be encoded by base64
```

或

```
io.jsonwebtoken.io.DecodingException: Illegal base64 character: '-'
```

#### 原因分析

- Nacos 2.2.0+ 版本启用了认证功能
- `NACOS_AUTH_TOKEN` 必须满足以下要求：
  1. **长度至少 32 字节**
  2. **必须是 Base64 编码格式**
  3. **不能包含非法的 Base64 字符**（如 `-`）

#### 解决方案

**方法 1：使用提供的脚本生成令牌（推荐）**

```bash
# 生成随机令牌
./scripts/generate_token.sh

# 或使用自定义密钥生成
./scripts/generate_token.sh "your-custom-secret-key-at-least-32-bytes"
```

脚本会输出类似以下内容：

```
==========================================
✅ 生成成功！
==========================================

原始密钥: your-custom-secret-key-at-least-32-bytes
密钥长度: 44 字节

Base64 编码的 Nacos 令牌:
eW91ci1jdXN0b20tc2VjcmV0LWtleS1hdC1sZWFzdC0zMi1ieXRlcw==

==========================================
使用方法：
==========================================

1. 在 .env 文件中设置：
   NACOS_AUTH_TOKEN=eW91ci1jdXN0b20tc2VjcmV0LWtleS1hdC1sZWFzdC0zMi1ieXRlcw==
```

**方法 2：手动生成令牌**

```bash
# 使用 openssl 生成随机密钥并编码
echo -n "ThisIsASecretKeyForNacosAuthAtLeast32Bytes" | base64

# 输出示例：
# VGhpc0lzQVNlY3JldEtleUZvck5hY29zQXV0aEF0TGVhc3QzMkJ5dGVz
```

**方法 3：使用 Python 生成**

```python
import base64
import secrets

# 生成32字节的随机密钥
secret_key = secrets.token_urlsafe(32)
print(f"原始密钥: {secret_key}")

# Base64 编码
token = base64.b64encode(secret_key.encode()).decode()
print(f"Nacos Token: {token}")
```

#### 配置步骤

1. **创建或编辑 `.env` 文件**：

   ```bash
   cp .env.example .env
   vim .env
   ```

2. **添加或更新 `NACOS_AUTH_TOKEN`**：

   ```bash
   # Nacos 认证令牌（Base64 编码）
   NACOS_AUTH_TOKEN=VGhpc0lzQVNlY3JldEtleUZvck5hY29zQXV0aEF0TGVhc3QzMkJ5dGVz
   ```

3. **重启 Nacos 服务**：

   ```bash
   docker-compose restart nacos
   ```

4. **验证启动成功**：

   ```bash
   # 查看日志
   docker-compose logs -f nacos
   
   # 检查健康状态
   curl http://localhost:8848/nacos/v1/console/health/readiness
   ```

### 2. Nacos 无法启动

#### 检查步骤

1. **查看容器状态**：

   ```bash
   docker-compose ps nacos
   ```

2. **查看详细日志**：

   ```bash
   docker-compose logs nacos
   ```

3. **检查端口占用**：

   ```bash
   # 检查 8848 端口
   lsof -i :8848
   
   # 或使用 netstat
   netstat -an | grep 8848
   ```

4. **检查内存和资源**：

   ```bash
   docker stats intel-nacos
   ```

### 3. 服务注册失败

#### 常见原因

1. **Nacos 服务未就绪**
   - 等待 Nacos 完全启动（约 30-60 秒）
   - 检查健康检查状态

2. **网络连接问题**
   - 确保服务在同一 Docker 网络中
   - 检查 `NACOS_SERVER_ADDR` 配置

3. **认证配置不匹配**
   - 确保客户端和服务端使用相同的认证配置

#### 解决方案

```bash
# 1. 检查 Nacos 健康状态
curl http://localhost:8848/nacos/v1/console/health/readiness

# 2. 检查网络连接
docker network inspect intel_ec_ms_intel-network

# 3. 测试服务注册
curl -X POST 'http://localhost:8848/nacos/v1/ns/instance' \
  -d 'serviceName=test-service&ip=127.0.0.1&port=8080'
```

## 配置参考

### Docker Compose 配置

```yaml
nacos:
  image: nacos/nacos-server:v2.2.0
  container_name: intel-nacos
  restart: unless-stopped
  environment:
    MODE: standalone
    PREFER_HOST_MODE: hostname
    EMBEDDED_STORAGE: embedded
    NACOS_AUTH_ENABLE: "true"
    # 使用环境变量或默认值
    NACOS_AUTH_TOKEN: ${NACOS_AUTH_TOKEN:-VGhpc0lzQVNlY3JldEtleUZvck5hY29zQXV0aEF0TGVhc3QzMkJ5dGVz}
    NACOS_AUTH_IDENTITY_KEY: nacos
    NACOS_AUTH_IDENTITY_VALUE: nacos
    JVM_XMS: 512m
    JVM_XMX: 512m
    JVM_XMN: 256m
  ports:
    - "8848:8848"
    - "9848:9848"
  volumes:
    - nacos_data:/home/nacos/data
    - nacos_logs:/home/nacos/logs
  networks:
    - intel-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8848/nacos/v1/console/health/readiness"]
    interval: 15s
    timeout: 10s
    retries: 5
    start_period: 60s
```

### 环境变量说明

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `MODE` | 运行模式 | `standalone` | 是 |
| `EMBEDDED_STORAGE` | 使用内置数据库 | `embedded` | 是 |
| `NACOS_AUTH_ENABLE` | 启用认证 | `true` | 是 |
| `NACOS_AUTH_TOKEN` | 认证令牌（Base64） | - | 是 |
| `NACOS_AUTH_IDENTITY_KEY` | 认证身份键 | `nacos` | 是 |
| `NACOS_AUTH_IDENTITY_VALUE` | 认证身份值 | `nacos` | 是 |
| `JVM_XMS` | JVM 初始堆大小 | `512m` | 否 |
| `JVM_XMX` | JVM 最大堆大小 | `512m` | 否 |

## 最佳实践

### 1. 生产环境配置

```bash
# 生成强随机令牌
./scripts/generate_token.sh

# 在 .env 文件中配置
NACOS_AUTH_TOKEN=生成的强随机令牌

# 增加 JVM 内存（根据实际需求）
JVM_XMS=1g
JVM_XMX=2g
```

### 2. 安全建议

- ✅ **使用强随机令牌**：不要使用默认值
- ✅ **定期更换令牌**：建议每季度更换一次
- ✅ **限制网络访问**：仅允许必要的服务访问 Nacos
- ✅ **启用 HTTPS**：生产环境使用 HTTPS 访问
- ✅ **备份配置**：定期备份 Nacos 数据

### 3. 监控和维护

```bash
# 查看 Nacos 状态
curl http://localhost:8848/nacos/v1/console/health/readiness

# 查看已注册服务
curl http://localhost:8848/nacos/v1/ns/service/list?pageNo=1&pageSize=10

# 查看服务实例
curl http://localhost:8848/nacos/v1/ns/instance/list?serviceName=your-service

# 查看 Nacos 日志
docker-compose logs -f nacos

# 查看 Nacos 数据卷
docker volume inspect intel_ec_ms_nacos_data
```

## 相关资源

- [Nacos 官方文档](https://nacos.io/zh-cn/docs/what-is-nacos.html)
- [Nacos 认证配置](https://nacos.io/zh-cn/docs/auth.html)
- [Docker Compose 配置](../docker-compose.yml)
- [环境变量配置](./.env.example)

---

**最后更新**: 2025-01-29
**适用版本**: Nacos 2.2.0+
