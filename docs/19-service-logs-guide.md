# 服务日志查看指南

## 📋 概述

本文档说明如何查看各个微服务的运行日志。日志系统使用 **Loguru**，支持文件输出和控制台输出。

**最后更新**: 2025-11-01

---

## 📂 日志文件位置

### 本地启动（项目根目录）

当您**本地启动服务**时，日志文件存储在项目根目录下的 `logs/` 目录：

```
intel_ec_ms/
└── logs/
    ├── gateway-service.log              # 网关服务今天日志（正在写入）
    ├── gateway-service-2025-10-31.log   # 网关服务昨天日志（已归档）
    ├── gateway-service_error.log        # 网关服务今天错误日志
    ├── gateway-service_error-2025-10-31.log # 网关服务昨天错误日志
    ├── auth-service.log                 # 认证服务今天日志
    ├── auth-service-2025-10-31.log      # 认证服务昨天日志
    ├── host-service.log                 # 主机服务今天日志
    └── host-service-2025-10-31.log      # 主机服务昨天日志
```

**查看方法**：
```bash
# 查看今天的日志（实时，使用固定文件名）
tail -f logs/gateway-service.log
tail -f logs/auth-service.log
tail -f logs/host-service.log

# 查看昨天的日志（带日期后缀）
tail -f logs/gateway-service-2025-10-31.log

# 查看今天的错误日志
tail -f logs/gateway-service_error.log

# 查看昨天的错误日志
tail -f logs/gateway-service_error-2025-10-31.log

# 搜索所有日志文件的内容（包括历史和当前）
grep "ERROR" logs/gateway-service*.log

# 搜索特定日期的日志
grep "ERROR" logs/gateway-service-2025-10-31.log

# 查看所有日志文件列表
ls -lh logs/
```

### Docker 容器内（Docker 启动）

当使用 **Docker Compose 启动**时，日志文件存储在容器内的 `/app/logs` 目录：

```
/app/logs/
├── gateway-service.log          # 网关服务日志（所有级别）
├── gateway-service_error.log     # 网关服务错误日志（仅ERROR级别）
├── auth-service.log              # 认证服务日志（所有级别）
├── auth-service_error.log        # 认证服务错误日志（仅ERROR级别）
├── host-service.log              # 主机服务日志（所有级别）
└── host-service_error.log        # 主机服务错误日志（仅ERROR级别）
```

### 日志配置参数

- **本地启动日志目录**: `./logs/`（项目根目录下的logs文件夹）
- **Docker启动日志目录**: `/app/logs`（容器内）
- **自动检测**: 系统会自动检测运行环境并选择正确的日志目录
- **日志轮转**: **每天午夜 00:00 自动轮转**（按日期切片）
- **当天日志命名**: `{service_name}.log`（固定文件名，无日期后缀）
- **历史日志命名**: `{service_name}-YYYY-MM-DD.log`（轮转后添加日期后缀）
- **日志保留**: 保留 30 天（错误日志保留 1 个月）
- **压缩格式**: zip（旧日志自动压缩）

### 日志文件命名规则

当天日志使用固定文件名，历史日志添加日期后缀：

```
logs/
├── gateway-service.log                    # 今天的日志（正在写入，无日期后缀）
├── gateway-service-2025-10-31.log          # 昨天的日志（已归档，有日期后缀）
├── gateway-service_error.log               # 今天的错误日志（无日期后缀）
└── gateway-service_error-2025-10-31.log    # 昨天的错误日志（有日期后缀）
```

**特点**：
- ✅ 当天日志使用固定文件名，方便查看（`service.log`）
- ✅ 每天午夜自动轮转，旧日志自动添加日期后缀
- ✅ 历史日志文件名包含日期，便于查找和管理
- ✅ 旧日志自动压缩为 `.zip` 格式
- ✅ 超过保留期的日志自动删除

---

## 🔍 查看日志的方法

### 方法1：本地启动时查看日志文件（推荐）

当您**本地启动服务**时，直接在项目根目录查看日志文件：

```bash
# 查看今天的日志（使用固定文件名，无需日期）
tail -f logs/gateway-service.log
tail -f logs/auth-service.log
tail -f logs/host-service.log

# 查看昨天的日志（带日期后缀）
tail -f logs/gateway-service-2025-10-31.log

# 查看今天的错误日志（固定文件名）
tail -f logs/gateway-service_error.log

# 查看昨天的错误日志（带日期后缀）
tail -f logs/gateway-service_error-2025-10-31.log

# 查看所有日志文件列表
ls -lh logs/

# 搜索所有日志文件中的内容（包括今天和历史）
grep "ERROR" logs/gateway-service*.log

# 搜索特定日期的日志
grep "ERROR" logs/gateway-service-2025-10-31.log
grep "查询主机" logs/host-service-2025-10-31.log

# 查看今天日志的最近100行（使用固定文件名）
tail -n 100 logs/gateway-service.log

# 查看压缩的历史日志（需要先解压）
unzip -l logs/gateway-service-2025-10-30.log.zip
unzip -p logs/gateway-service-2025-10-30.log.zip | grep "ERROR"
```

**Windows 用户**可以使用 PowerShell：
```powershell
# 查看今天的日志（使用固定文件名）
Get-Content "logs\gateway-service.log" -Tail 50 -Wait

# 查看昨天的日志（带日期后缀）
Get-Content "logs\gateway-service-2025-10-31.log" -Tail 50 -Wait

# 搜索所有日志（包括今天和历史）
Get-ChildItem logs\gateway-service*.log | Select-String -Pattern "ERROR"

# 搜索特定日期的日志
Get-Content "logs\gateway-service-2025-10-31.log" | Select-String -Pattern "ERROR"
```

### 方法2：使用 Docker Compose 查看（Docker 启动时）

#### 查看所有服务日志
```bash
# 查看所有服务的实时日志
docker-compose logs -f

# 查看最近 100 行日志
docker-compose logs --tail=100

# 查看特定时间段的日志
docker-compose logs --since 30m
```

#### 查看单个服务日志
```bash
# 查看网关服务日志
docker-compose logs -f gateway-service

# 查看认证服务日志
docker-compose logs -f auth-service

# 查看主机服务日志
docker-compose logs -f host-service
```

#### 按日志级别过滤
```bash
# 查看错误日志
docker-compose logs gateway-service | grep -i error

# 查看警告日志
docker-compose logs auth-service | grep -i warning

# 查看包含特定关键词的日志
docker-compose logs host-service | grep "查询主机列表"
```

---

### 方法2：进入容器查看日志文件

#### 进入容器
```bash
# 进入网关服务容器
docker-compose exec gateway-service bash

# 进入认证服务容器
docker-compose exec auth-service bash

# 进入主机服务容器
docker-compose exec host-service bash
```

#### 查看日志文件
```bash
# 在容器内查看所有日志
tail -f /app/logs/gateway-service.log

# 查看错误日志
tail -f /app/logs/gateway-service_error.log

# 查看最近 100 行日志
tail -n 100 /app/logs/gateway-service.log

# 搜索日志内容
grep "ERROR" /app/logs/gateway-service.log

# 查看日志文件大小
ls -lh /app/logs/
```

---

### 方法3：挂载日志卷到本地（需要配置）

如果您需要在本地直接访问日志文件，可以在 `docker-compose.yml` 中为每个服务添加日志卷挂载：

```yaml
# 示例：为 gateway-service 添加日志卷挂载
gateway-service:
  volumes:
    - ./logs/gateway-service:/app/logs

# 示例：为 auth-service 添加日志卷挂载
auth-service:
  volumes:
    - ./logs/auth-service:/app/logs

# 示例：为 host-service 添加日志卷挂载
host-service:
  volumes:
    - ./logs/host-service:/app/logs
```

**配置后，日志文件会保存在本地**：
```
./logs/
├── gateway-service/
│   ├── gateway-service.log
│   └── gateway-service_error.log
├── auth-service/
│   ├── auth-service.log
│   └── auth-service_error.log
└── host-service/
    ├── host-service.log
    └── host-service_error.log
```

---

### 方法4：使用 Docker 命令查看（不使用 Compose）

```bash
# 查看容器日志
docker logs -f gateway-service

# 查看最近 100 行
docker logs --tail=100 gateway-service

# 查看特定时间段
docker logs --since 1h gateway-service

# 查看特定时间范围
docker logs --since "2025-11-01T10:00:00" --until "2025-11-01T11:00:00" gateway-service
```

---

## 📊 日志格式说明

### 控制台日志格式（带颜色）
```
2025-11-01 10:30:00.123 | INFO     | gateway-service | app.main:startup:45 | 服务启动完成
```

### 文件日志格式（纯文本）
```
2025-11-01 10:30:00.123 | INFO     | gateway-service | app.main:startup:45 | 服务启动完成
```

### 字段说明
- **时间戳**: `YYYY-MM-DD HH:mm:ss.SSS` 格式
- **日志级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **服务名称**: 服务标识符（gateway-service, auth-service, host-service）
- **位置信息**: `模块:函数:行号`
- **日志消息**: 实际日志内容

---

## 🔧 配置日志级别

### 通过环境变量配置

在 `docker-compose.yml` 中为每个服务设置 `LOG_LEVEL` 环境变量：

```yaml
gateway-service:
  environment:
    LOG_LEVEL: DEBUG  # 可选值: DEBUG, INFO, WARNING, ERROR, CRITICAL

auth-service:
  environment:
    LOG_LEVEL: INFO

host-service:
  environment:
    LOG_LEVEL: INFO
```

### 日志级别说明

- **DEBUG**: 详细调试信息（开发环境使用）
- **INFO**: 正常操作信息（生产环境推荐）
- **WARNING**: 警告信息（不影响功能）
- **ERROR**: 错误信息（需要关注）
- **CRITICAL**: 严重错误（系统无法正常运行）

---

## 📁 日志文件管理

### 日志轮转规则

- **轮转方式**: **按日期轮转**（每天午夜 00:00 自动生成新文件）
- **文件命名**: `{service_name}-YYYY-MM-DD.log`（包含日期）
- **保留时间**: 
  - 普通日志：30 天
  - 错误日志：1 个月
- **压缩格式**: zip（旧日志自动压缩）
- **自动清理**: 超过保留期的日志自动删除

### 日志文件示例

```
logs/
├── gateway-service.log                    # 今天的日志（正在写入，无日期后缀）
├── gateway-service-2025-10-31.log.zip     # 昨天的日志（已压缩，有日期后缀）
├── gateway-service-2025-10-30.log.zip     # 前天的日志（已压缩，有日期后缀）
├── gateway-service_error.log               # 今天的错误日志（无日期后缀）
└── gateway-service_error-2025-10-31.log.zip # 昨天的错误日志（已压缩，有日期后缀）
```

### 手动清理日志

#### Docker 环境
```bash
# 进入容器
docker-compose exec gateway-service bash

# 查看日志文件
ls -lh /app/logs/

# 删除特定日期的日志（谨慎操作）
rm /app/logs/gateway-service-2025-10-01.log.zip

# 删除所有压缩的历史日志（保留最近7天）
find /app/logs/ -name "*.zip" -mtime +7 -delete
```

#### 本地环境
```bash
# 在项目根目录查看日志文件
ls -lh logs/

# 删除特定日期的日志
rm logs/gateway-service-2025-10-01.log.zip

# 删除所有压缩的历史日志（保留最近7天）
find logs/ -name "*.zip" -mtime +7 -delete

# 查看日志文件大小统计
du -sh logs/*
```

---

## 🔍 日志搜索技巧

### 本地启动时搜索日志

```bash
# 搜索今天日志中的错误（使用固定文件名）
grep -i error logs/gateway-service.log

# 搜索所有日志中的错误（包括今天和历史）
grep -i error logs/gateway-service*.log

# 搜索特定日期的日志
grep "user_id.*123" logs/auth-service-2025-10-31.log

# 搜索多个关键词（AND关系）
grep "ERROR" logs/gateway-service.log | grep "database"

# 搜索多个关键词（OR关系）
grep -E "ERROR|WARNING" logs/auth-service.log

# 搜索特定时间段的日志（使用固定文件名）
grep "10:00:00\|10:59:59" logs/host-service.log

# 在压缩的历史日志中搜索
unzip -p logs/gateway-service-2025-10-30.log.zip | grep "ERROR"
```

### Docker 启动时搜索日志

```bash
# 搜索错误日志
docker-compose logs gateway-service | grep -i error

# 搜索特定用户的操作
docker-compose logs auth-service | grep "user_id.*123"

# 搜索特定时间段的日志
docker-compose logs --since "2025-11-01 10:00:00" --until "2025-11-01 11:00:00" host-service

# 搜索多个关键词（AND关系）
docker-compose logs gateway-service | grep "ERROR" | grep "database"

# 搜索多个关键词（OR关系）
docker-compose logs auth-service | grep -E "ERROR|WARNING"
```

### 使用 jq 处理 JSON 日志（如果启用）

如果将来启用 JSON 格式日志，可以使用 `jq` 工具：

```bash
# 安装 jq
# macOS: brew install jq
# Ubuntu: apt-get install jq

# 查看 JSON 格式日志
cat /app/logs/gateway-service.log | jq '.'

# 过滤错误日志
cat /app/logs/gateway-service.log | jq 'select(.level == "ERROR")'

# 提取特定字段
cat /app/logs/gateway-service.log | jq '.message, .extra'
```

---

## 🚀 快速命令参考

### 常用日志查看命令

```bash
# 实时查看所有服务日志
docker-compose logs -f

# 实时查看单个服务日志
docker-compose logs -f gateway-service

# 查看最近 50 行错误日志
docker-compose logs --tail=50 gateway-service | grep -i error

# 查看最近 1 小时的日志
docker-compose logs --since 1h gateway-service

# 进入容器查看日志文件
docker-compose exec gateway-service tail -f /app/logs/gateway-service.log

# 搜索包含特定关键词的日志
docker-compose logs host-service | grep "查询主机"
```

---

## ⚙️ 优化建议

### 1. 添加日志卷挂载（推荐）

在 `docker-compose.yml` 中为所有服务添加日志卷，便于本地查看和管理：

```yaml
gateway-service:
  volumes:
    - ./logs/gateway-service:/app/logs

auth-service:
  volumes:
    - ./logs/auth-service:/app/logs

host-service:
  volumes:
    - ./logs/host-service:/app/logs
```

### 2. 配置日志级别

根据环境设置合适的日志级别：

```yaml
# 开发环境
LOG_LEVEL: DEBUG

# 生产环境
LOG_LEVEL: INFO
```

### 3. 定期清理日志

建议设置定时任务清理旧的压缩日志文件，或使用日志管理工具（如 logrotate）。

---

## 📚 相关文档

- [快速开始指南](./00-quick-start.md) - 服务启动说明
- [部署指南](./03-deployment-guide.md) - 生产环境部署
- [监控快速参考](./07-monitoring-quick-reference.md) - 监控指标查看

---

## 🔗 相关资源

- [Loguru 官方文档](https://loguru.readthedocs.io/)
- [Docker Compose Logs 文档](https://docs.docker.com/compose/reference/logs/)
- [Docker Logs 文档](https://docs.docker.com/engine/reference/commandline/logs/)
