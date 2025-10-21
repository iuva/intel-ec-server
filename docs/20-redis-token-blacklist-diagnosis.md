# Redis Token 黑名单诊断指南

## 📌 问题描述

**症状**：同一个 `refresh_token` 仍然可以进行多次刷新

**预期行为**：第二次使用应该返回 `401 UNAUTHORIZED` (AUTH_REFRESH_TOKEN_REUSED)

## 🎯 根本原因分析

### 架构设计

Token 黑名单使用 Redis 缓存实现一次性使用机制：

```
┌─────────────────┐
│  Login Request  │
└────────┬────────┘
         ↓
    ✅ Success
         ↓
    返回 access_token + refresh_token
         ↓
┌─────────────────────────────────────┐
│ 用户第一次使用 refresh_token 续期    │
└────────┬────────────────────────────┘
         ↓
   ✅ 检查黑名单 → None (未使用)
         ↓
   ✅ 刷新成功，返回新 token
         ↓
   ✅ 将 refresh_token 加入 Redis 黑名单
         ↓
┌─────────────────────────────────────┐
│ 用户第二次使用相同的 refresh_token   │
└────────┬────────────────────────────┘
         ↓
   ❌ 检查黑名单 → True (已使用)
         ↓
   ❌ 拒绝请求 (AUTH_REFRESH_TOKEN_REUSED)
```

### 问题流程

当 **Redis 连接失败** 时：

```
┌─────────────────┐
│  Login Request  │
└────────┬────────┘
         ↓
┌──────────────────────────────┐
│ Redis 连接初始化              │
├──────────────────────────────┤
│ ❌ 连接失败（网络错误、密码  │
│    错误等）                  │
└────────┬─────────────────────┘
         ↓
get_cache() 返回 None (默认行为)
         ↓
if is_blacklisted: → False (None 是假值)
         ↓
🚨 黑名单检查完全失效！
         ↓
Token 可以被无限次使用
```

## 📋 分步诊断

### 第一步：检查环境变量

```bash
# 查看 Redis 配置
env | grep REDIS_

# 或从 docker-compose 检查
docker-compose config | grep -A 10 "environment:" | grep REDIS_
```

**预期输出**：
```
REDIS_HOST=your.redis.host        # 外部 Redis 地址
REDIS_PORT=6379                   # Redis 端口
REDIS_PASSWORD=your_***REMOVED***word      # Redis 密码（如果有）
REDIS_DB=1                        # 使用的数据库号
```

**可能的问题**：
- ❌ `REDIS_HOST` 为空或指向内部网络
- ❌ `REDIS_PORT` 不对
- ❌ `REDIS_PASSWORD` 错误
- ❌ `REDIS_DB` 与其他服务冲突

### 第二步：测试 Redis 连接

```bash
# 安装 Redis 客户端（如果没有）
sudo apt-get install redis-tools  # Debian/Ubuntu
brew install redis                 # macOS

# 连接到 Redis
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD

# 测试连接
PING

# 应该返回: PONG
```

**可能的问题**：
```
❌ Could not connect to Redis at ...: Connection refused
   → Redis 服务未启动或地址不对

❌ WRONGPASS invalid username-***REMOVED***word pair
   → Redis 密码错误

❌ (no messages)
   → Redis 绑定地址不允许外部连接
   → 检查 Redis 配置: grep "bind" /etc/redis/redis.conf
```

### 第三步：查看服务启动日志

```bash
# 查看 auth-service 启动日志
docker-compose logs auth-service 2>&1 | head -100

# 查看 Redis 连接相关的日志
docker-compose logs auth-service | grep -i redis

# 查看完整的初始化日志
docker-compose logs auth-service | grep -i "init\|connect\|redis"
```

**正常日志**（Redis 连接成功）：
```
[INFO] 初始化数据库连接
[INFO] Redis连接成功: redis://...
[INFO] auth-service 服务启动完成
```

**异常日志**（Redis 连接失败）：
```
[ERROR] Redis连接失败: Connection refused
[WARNING] Redis连接失败，降级到无缓存模式
[INFO] auth-service 服务启动完成
```

### 第四步：检查 Redis 中是否有黑名单数据

```bash
# 连接到 Redis
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD

# 查看所有黑名单 key
KEYS "refresh_token_blacklist:*"

# 查看某个 token 的黑名单状态
GET "refresh_token_blacklist:your_token_here"

# 应该返回: "true" (如果 token 已被使用)
#           (nil)   (如果 token 未被使用或不存在)
```

### 第五步：启用 DEBUG 日志并测试

```bash
# 1. 重启服务（启用 DEBUG 日志）
docker-compose restart auth-service

# 2. 等待服务启动完成
sleep 5

# 3. 登录获取 token
curl -X POST http://localhost:8001/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "***REMOVED***word": "***REMOVED***"
  }'

# 保存 refresh_token（从响应中提取）
TOKEN="your_refresh_token_here"

# 4. 第一次续期（应该成功）
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$TOKEN\"}"

# 5. 查看日志（应该看到 is_blacklisted: False）
docker-compose logs auth-service | grep "检查 token 黑名单" | tail -1

# 6. 第二次续期（应该失败）
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$TOKEN\"}"

# 7. 查看日志（应该看到 is_blacklisted: True）
docker-compose logs auth-service | grep "检查 token 黑名单" | tail -1
```

**预期日志输出**：

```
✅ 正常情况（Redis 连接成功）

第一次续期：
[DEBUG] 检查 token 黑名单
  operation: refresh_token
  blacklist_key: refresh_token_blacklist:eyJh... (前50字符)
  is_blacklisted: False

[INFO] 令牌刷新成功
  operation: refresh_token
  user_id: 123
  username: admin

第二次续期：
[DEBUG] 检查 token 黑名单
  operation: refresh_token
  blacklist_key: refresh_token_blacklist:eyJh... (前50字符)
  is_blacklisted: True

[WARNING] 刷新令牌已被使用过，拒绝重复使用
  operation: refresh_token
  error_code: AUTH_REFRESH_TOKEN_REUSED
  user_id: 123

---

❌ 异常情况（Redis 连接失败）

第一次续期：
[DEBUG] 检查 token 黑名单
  operation: refresh_token
  blacklist_key: refresh_token_blacklist:eyJh... (前50字符)
  is_blacklisted: None  ← ⚠️ 问题开始

[INFO] 令牌刷新成功
  operation: refresh_token
  user_id: 123
  username: admin

第二次续期：
[DEBUG] 检查 token 黑名单
  operation: refresh_token
  blacklist_key: refresh_token_blacklist:eyJh... (前50字符)
  is_blacklisted: None  ← ⚠️ 仍然是 None

[INFO] 令牌刷新成功   ← ⚠️ 应该被拒绝但没有！
  operation: refresh_token
  user_id: 123
  username: admin
```

## 🛠️ 常见问题及解决方案

### 问题 1: Redis 连接拒绝

**症状**：
```
Connection refused at 192.168.1.100:6379
```

**原因**：
- Redis 服务未启动
- Redis 配置中的 `bind` 地址不包括当前访问的地址

**解决方案**：
```bash
# 1. 检查 Redis 是否运行
ps aux | grep redis-server

# 2. 如果未运行，启动 Redis
redis-server /etc/redis/redis.conf

# 3. 检查 Redis 绑定配置
grep "^bind" /etc/redis/redis.conf

# 4. 如果需要允许外部连接，修改为
bind 0.0.0.0
# 或
bind 0.0.0.0 ::1

# 5. 重启 Redis
systemctl restart redis-server
# 或
sudo service redis-server restart
```

### 问题 2: 密码错误

**症状**：
```
WRONGPASS invalid username-***REMOVED***word pair
```

**原因**：
- REDIS_PASSWORD 环境变量设置错误
- Redis 密码不匹配

**解决方案**：
```bash
# 1. 查看实际的 Redis 密码
grep "^require***REMOVED***" /etc/redis/redis.conf

# 2. 更新环境变量
export REDIS_PASSWORD="correct_***REMOVED***word"

# 3. 或在 docker-compose.yml 中更新
services:
  auth-service:
    environment:
      REDIS_PASSWORD: "correct_***REMOVED***word"

# 4. 重启服务
docker-compose restart auth-service
```

### 问题 3: 防火墙阻止

**症状**：
```
Connection timeout at 192.168.1.100:6379
```

**原因**：
- 防火墙规则阻止了 Redis 端口

**解决方案**：
```bash
# 1. 检查防火墙状态
sudo firewall-cmd --state
sudo ufw status

# 2. 允许 Redis 端口
# Ubuntu/Debian (UFW)
sudo ufw allow 6379/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=6379/tcp
sudo firewall-cmd --reload

# 3. 验证规则已添加
sudo firewall-cmd --list-ports
```

### 问题 4: 错误的数据库号

**症状**：
```
[DEBUG] 检查 token 黑名单 is_blacklisted: None (始终为 None)
Redis 中看不到任何 refresh_token_blacklist:* key
```

**原因**：
- REDIS_DB 号选择错误
- 多个服务使用相同的数据库号导致冲突

**解决方案**：
```bash
# 1. 查看可用的数据库
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD

# 在 redis-cli 中执行
INFO keyspace

# 2. 选择不同的数据库
# 每个 Redis 有 16 个数据库 (0-15)
# auth-service 使用 DB 1
# 其他服务使用 DB 2, 3 等

# 3. 检查和修改 .env 或 docker-compose.yml
REDIS_DB=1  # auth-service
REDIS_DB=2  # 其他服务
```

### 问题 5: TTL 设置不正确

**症状**：
```
[DEBUG] 检查 token 黑名单 is_blacklisted: False (第一次)
但第二次仍然是 False (应该是 True)
Redis 中的 token 键立即过期
```

**原因**：
- Token 过期时间计算错误
- TTL 设置为 0 或负数

**解决方案**：
```python
# 检查代码中的 TTL 设置
import time

exp = payload.get("exp", 0)
ttl = max(1, int(exp - time.time()))  # 确保 TTL 至少为 1 秒

# 验证 TTL 是否为正数
assert ttl > 0, f"TTL 应该为正数，当前值: {ttl}"

await set_cache(blacklist_key, True, expire=ttl)
```

## 📊 诊断决策树

```
同一个 token 可无限次续期
    ↓
查看日志中 is_blacklisted 的值
    ├─→ None
    │   ↓
    │   Redis 连接失败
    │   ├─→ 检查网络连接
    │   ├─→ 检查 REDIS_HOST/PORT
    │   ├─→ 检查 REDIS_PASSWORD
    │   └─→ 检查防火墙
    │
    ├─→ False (第二次仍是 False)
    │   ↓
    │   set_cache() 失败
    │   ├─→ 检查 Redis 权限
    │   ├─→ 检查 Redis 磁盘空间
    │   └─→ 检查 Redis 内存配置
    │
    └─→ False (但应该是 True)
        ↓
        TTL 设置不正确
        ├─→ Token 过期时间计算错误
        └─→ TTL 设置为 0 或负数
```

## ✅ 验证修复

修复完 Redis 连接问题后，运行以下验证：

```bash
# 1. 重启服务
docker-compose restart auth-service

# 2. 等待启动完成
sleep 10

# 3. 查看启动日志
docker-compose logs auth-service | grep -i redis

# 应该看到:
# [INFO] Redis连接成功: redis://...

# 4. 运行完整的测试
# （见第四步的测试流程）

# 5. 验证黑名单数据已保存
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD
KEYS "refresh_token_blacklist:*"

# 应该看到已使用过的 token keys
```

## 📞 获取帮助

如果问题仍未解决，请收集以下信息：

```bash
# 1. Redis 版本和配置
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD info server
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD config get "*"

# 2. 服务日志
docker-compose logs auth-service > /tmp/auth_service.log

# 3. Redis 中的数据
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD --scan --pattern "refresh_token_blacklist:*"

# 4. 环境变量
docker-compose config | grep -E "(REDIS_|DB_|PASS)" | head -20
```

---

**最后更新**: 2025-10-21
**相关文档**: 
- [Token 刷新指南](./TOKEN_RENEWAL_GUIDE.md)
- [Redis 配置最佳实践](./README.md#-redis-配置)
