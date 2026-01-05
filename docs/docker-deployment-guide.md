# Docker 部署完整指南

## 📋 目录

- [环境准备](#环境准备)
- [环境变量配置](#环境变量配置)
- [Docker Compose 部署](#docker-compose-部署)
- [单独服务部署](#单独服务部署)
- [常用操作命令](#常用操作命令)
- [故障排查](#故障排查)

---

## 环境准备

### Windows 环境准备

#### 1. 安装 Docker Desktop

1. **下载 Docker Desktop**
   - 访问 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - 下载并安装 Docker Desktop
   - 确保启用 WSL 2 后端（推荐）

2. **系统要求**
   - Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 或更高版本)
   - Windows 11 64-bit: Home 或 Pro 版本
   - 启用 Hyper-V 和容器 Windows 功能
   - 至少 4GB RAM（推荐 8GB 或更多）

3. **验证安装**
   ```powershell
   # 打开 PowerShell 或 CMD
   docker --version
   docker-compose --version
   ```

#### 2. 配置 Docker Desktop

1. **设置资源限制**
   - 打开 Docker Desktop
   - 进入 Settings → Resources
   - 建议配置：
     - CPUs: 4 核或更多
     - Memory: 8GB 或更多
     - Swap: 2GB
     - Disk image size: 至少 60GB

2. **启用 WSL 2 集成**
   - Settings → Resources → WSL Integration
   - 启用 "Enable integration with my default WSL distro"
   - 选择要集成的 WSL 发行版

#### 3. 安装 Git（如果未安装）

1. 下载并安装 [Git for Windows](https://git-scm.com/download/win)
2. 验证安装：
   ```powershell
   git --version
   ```

#### 4. 克隆项目代码

```powershell
# 在 PowerShell 或 CMD 中执行
cd C:\Projects
git clone <repository-url>
cd intel_ec_ms
```

---

### Linux 环境准备

#### 1. 安装 Docker Engine

**Ubuntu/Debian 系统：**

```bash
# 1. 更新 apt 包索引
sudo apt-get update

# 2. 安装必要的依赖包
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 3. 添加 Docker 官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. 设置 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 7. 将当前用户添加到 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER

# 8. 重新登录或执行以下命令使组权限生效
newgrp docker
```

**CentOS/RHEL 系统：**

```bash
# 1. 安装必要的依赖包
sudo yum install -y yum-utils

# 2. 添加 Docker 仓库
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

# 3. 安装 Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 5. 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker
```

**验证安装：**

```bash
# 验证 Docker 版本
docker --version
docker compose version

# 验证 Docker 服务状态
sudo systemctl status docker

# 测试 Docker 运行
docker run hello-world
```

#### 2. 配置 Docker（可选）

**配置 Docker 守护进程：**

```bash
# 创建或编辑 Docker 守护进程配置文件
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

# 重启 Docker 服务使配置生效
sudo systemctl restart docker
```

**配置资源限制（可选）：**

```bash
# 编辑 systemd 服务文件
sudo systemctl edit docker

# 添加以下内容：
[Service]
LimitNOFILE=65536
LimitNPROC=65536

# 重新加载并重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 3. 安装 Git（如果未安装）

**Ubuntu/Debian：**

```bash
sudo apt-get update
sudo apt-get install -y git
```

**CentOS/RHEL：**

```bash
sudo yum install -y git
```

**验证安装：**

```bash
git --version
```

#### 4. 克隆项目代码

```bash
# 在终端中执行
cd ~/projects
git clone <repository-url>
cd intel_ec_ms
```

#### 5. 安装必要的工具（可选）

```bash
# Ubuntu/Debian
sudo apt-get install -y curl wget vim

# CentOS/RHEL
sudo yum install -y curl wget vim
```

---

## 环境变量配置

### `.env` 文件示例

在项目根目录创建 `.env` 文件，包含以下配置：

```bash
# ==========================================
# 服务基础配置
# ==========================================
# Gateway Service
SERVICE_NAME=gateway-service
SERVICE_PORT=8000
GATEWAY_SERVICE_PORT=8000
GATEWAY_SERVICE_IP=172.20.0.100

# Auth Service
AUTH_SERVICE_NAME=auth-service
AUTH_SERVICE_PORT=8001
AUTH_SERVICE_IP=172.20.0.101

# Host Service
HOST_SERVICE_NAME=host-service
HOST_SERVICE_PORT=8003
HOST_SERVICE_IP=172.20.0.103

# ==========================================
# 数据库配置 (MariaDB)
# ==========================================
MARIADB_HOST=intel-mariadb
MARIADB_PORT=3306
MARIADB_USER=intel_user
MARIADB_PASSWORD=your_mariadb_***REMOVED***word_here
MARIADB_DATABASE=intel_cw

# ==========================================
# Redis 配置
# ==========================================
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_***REMOVED***word_here
REDIS_DB=0
AUTH_REDIS_DB=1
HOST_REDIS_DB=3

# ==========================================
# Nacos 服务发现配置
# ==========================================
NACOS_SERVER_ADDR=http://nacos:8848
NACOS_USERNAME=nacos
NACOS_PASSWORD=nacos
NACOS_NAMESPACE=public
NACOS_GROUP=DEFAULT_GROUP

# ==========================================
# Jaeger 分布式追踪配置
# ==========================================
JAEGER_ENDPOINT=jaeger:4317

# ==========================================
# 组件开关配置
# ==========================================
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false

# ==========================================
# JWT 配置
# ==========================================
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ==========================================
# 应用配置
# ==========================================
DEBUG=false
LOG_LEVEL=INFO

# ==========================================
# Host Service 特定配置
# ==========================================
USE_HARDWARE_MOCK=false
FILE_UPLOAD_DIR=/app/uploads

# ==========================================
# ⚠️ 重要警告
# ==========================================
# 请勿在 .env 文件中设置 PYTHONPATH，否则会覆盖 Docker 容器内的 Python 路径，
# 导致 "No module named uvicorn" 等错误。
# 如果必须设置，请确保在 docker run 命令中显式覆盖它：
# -e PYTHONPATH=/install/lib/python3.8/site-packages:/app

```

### 环境变量说明

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `SERVICE_PORT` | Gateway 服务端口 | 8000 | 否 |
| `AUTH_SERVICE_PORT` | Auth 服务端口 | 8001 | 否 |
| `HOST_SERVICE_PORT` | Host 服务端口 | 8003 | 否 |
| `MARIADB_PASSWORD` | MariaDB 密码 | - | **是** |
| `REDIS_HOST` | Redis 主机地址 | - | **是** |
| `REDIS_PASSWORD` | Redis 密码 | - | **是** |
| `JWT_SECRET_KEY` | JWT 密钥 | - | **是** |
| `GATEWAY_SERVICE_IP` | Gateway 服务 IP | 172.20.0.100 | 否 |
| `AUTH_SERVICE_IP` | Auth 服务 IP | 172.20.0.101 | 否 |
| `HOST_SERVICE_IP` | Host 服务 IP | 172.20.0.103 | 否 |

### 创建 `.env` 文件

**Windows PowerShell:**
```powershell
# 在项目根目录执行
# 如果存在 .env.example，复制它
if (Test-Path .env.example) {
    Copy-Item .env.example .env
} else {
    # 创建新的 .env 文件
    New-Item -Path .env -ItemType File
}

# 使用文本编辑器编辑 .env 文件
notepad .env
```

**Windows CMD:**
```cmd
REM 如果存在 .env.example，复制它
if exist .env.example (
    copy .env.example .env
) else (
    REM 创建新的 .env 文件
    type nul > .env
)

REM 使用文本编辑器编辑 .env 文件
notepad .env
```

**Linux:**
```bash
# 在项目根目录执行
# 如果存在 .env.example，复制它
if [ -f .env.example ]; then
    cp .env.example .env
else
    # 创建新的 .env 文件
    touch .env
fi

# 使用文本编辑器编辑 .env 文件
vim .env
# 或使用 nano
# nano .env
```

**注意：** 如果项目中没有 `.env.example` 文件，请参考上面的 [`.env` 文件示例](#env-文件示例) 手动创建。

---

## Docker Compose 部署

### 方式一：一键部署（推荐）

#### 1. 构建并启动所有服务

**Windows PowerShell:**
```powershell
# 在项目根目录执行
docker-compose up -d --build
```

**Linux:**
```bash
# 在项目根目录执行
docker compose up -d --build
# 或使用旧版本命令
# docker-compose up -d --build
```

**命令说明：**
- `up`: 创建并启动容器
- `-d`: 后台运行（detached mode）
- `--build`: 构建镜像（如果镜像不存在或代码有更新）

**注意：** Docker Compose V2 使用 `docker compose`（无连字符），V1 使用 `docker-compose`（有连字符）。如果系统安装的是 V2，请使用 `docker compose`。

#### 2. 查看服务状态

**Windows PowerShell:**
```powershell
# 查看所有服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f gateway-service
docker-compose logs -f auth-service
docker-compose logs -f host-service
```

**Linux:**
```bash
# 查看所有服务状态
docker compose ps

# 查看服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f gateway-service
docker compose logs -f auth-service
docker compose logs -f host-service
```

#### 3. 验证服务健康

**Windows PowerShell:**
```powershell
# 检查 Gateway 服务
curl http://localhost:8000/health

# 检查 Auth 服务
curl http://localhost:8001/health

# 检查 Host 服务
curl http://localhost:8003/health
```

**Linux:**
```bash
# 检查 Gateway 服务
curl http://localhost:8000/health

# 检查 Auth 服务
curl http://localhost:8001/health

# 检查 Host 服务
curl http://localhost:8003/health

# 如果没有安装 curl，可以使用 wget
wget -qO- http://localhost:8000/health
```

### 方式二：分步部署

#### 1. 仅构建镜像（不启动）

**Windows PowerShell:**
```powershell
docker-compose build
```

**Linux:**
```bash
docker compose build
```

#### 2. 启动服务（使用已构建的镜像）

**Windows PowerShell:**
```powershell
docker-compose up -d
```

**Linux:**
```bash
docker compose up -d
```

#### 3. 停止服务

**Windows PowerShell:**
```powershell
# 停止所有服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、数据卷
docker-compose down -v
```

**Linux:**
```bash
# 停止所有服务
docker compose stop

# 停止并删除容器
docker compose down

# 停止并删除容器、网络、数据卷
docker compose down -v
```

### 方式三：仅启动特定服务

**Windows PowerShell:**
```powershell
# 仅启动 Gateway 服务
docker-compose up -d gateway-service

# 仅启动 Gateway 和 Auth 服务
docker-compose up -d gateway-service auth-service
```

**Linux:**
```bash
# 仅启动 Gateway 服务
docker compose up -d gateway-service

# 仅启动 Gateway 和 Auth 服务
docker compose up -d gateway-service auth-service
```

---

## 单独服务部署

### Gateway Service 单独部署

#### 1. 构建镜像

```powershell
# 在项目根目录执行
docker build -f services/gateway-service/Dockerfile -t intel-cw-ms/gateway-service:latest .
```

#### 2. 运行容器

```powershell
docker run -d \
  --name gateway-service \
  --network intel-network \
  --ip 172.20.0.100 \
  -p 8000:8000 \
  --env-file .env \
  -e SERVICE_NAME=gateway-service \
  -e SERVICE_PORT=8000 \
  -e GATEWAY_SERVICE_PORT=8000 \
  -e GATEWAY_SERVICE_IP=172.20.0.100 \
  -e AUTH_SERVICE_IP=auth-service \
  -e AUTH_SERVICE_PORT=8001 \
  -e HOST_SERVICE_IP=host-service \
  -e HOST_SERVICE_PORT=8003 \
  -e MARIADB_HOST=intel-mariadb \
  -e MARIADB_PORT=3306 \
  -e MARIADB_USER=intel_user \
  -e MARIADB_PASSWORD=${MARIADB_PASSWORD} \
  -e MARIADB_DATABASE=intel_cw \
  -e REDIS_HOST=${REDIS_HOST} \
  -e REDIS_PORT=${REDIS_PORT} \
  -e REDIS_PASSWORD=${REDIS_PASSWORD} \
  -e REDIS_DB=0 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  -e NACOS_USERNAME=nacos \
  -e NACOS_PASSWORD=nacos \
  -e NACOS_NAMESPACE=public \
  -e NACOS_GROUP=DEFAULT_GROUP \
  -e JAEGER_ENDPOINT=jaeger:4317 \
  -e ENABLE_NACOS=false \
  -e ENABLE_JAEGER=false \
  -e ENABLE_PROMETHEUS=false \
  -e JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  -e PYTHONPATH=/install/lib/python3.8/site-packages:/app \
  --restart unless-stopped \
  --ulimit nofile=4096:8192 \
  intel-cw-ms/gateway-service:latest
```

**简化版本（使用 env-file）:**

```powershell
# 首先创建网络（如果不存在）
docker network create --subnet=172.20.0.0/16 intel-network

# 运行容器
docker run -d \
  --name gateway-service \
  --network intel-network \
  --ip 172.20.0.100 \
  -p 8000:8000 \
  --env-file .env \
  -e PYTHONPATH=/install/lib/python3.8/site-packages:/app \
  --restart unless-stopped \
  --ulimit nofile=4096:8192 \
  intel-cw-ms/gateway-service:latest
```

#### 3. 查看日志

```powershell
docker logs -f gateway-service
```

#### 4. 停止和删除容器

```powershell
# 停止容器
docker stop gateway-service

# 删除容器
docker rm gateway-service

# 停止并删除
docker rm -f gateway-service
```

### Auth Service 单独部署

#### 1. 构建镜像

```powershell
docker build -f services/auth-service/Dockerfile -t intel-cw-ms/auth-service:latest .
```

#### 2. 运行容器

```powershell
# 创建网络（如果不存在）
docker network create --subnet=172.20.0.0/16 intel-network

# 运行容器
docker run -d \
  --name auth-service \
  --network intel-network \
  --ip 172.20.0.101 \
  -p 8001:8001 \
  --env-file .env \
  -e SERVICE_NAME=auth-service \
  -e SERVICE_PORT=8001 \
  -e AUTH_SERVICE_PORT=8001 \
  -e AUTH_SERVICE_IP=172.20.0.101 \
  -e GATEWAY_SERVICE_IP=gateway-service \
  -e GATEWAY_SERVICE_PORT=8000 \
  -e HOST_SERVICE_IP=host-service \
  -e HOST_SERVICE_PORT=8003 \
  -e MARIADB_HOST=intel-mariadb \
  -e MARIADB_PORT=3306 \
  -e MARIADB_USER=intel_user \
  -e MARIADB_PASSWORD=${MARIADB_PASSWORD} \
  -e MARIADB_DATABASE=intel_cw \
  -e REDIS_HOST=${REDIS_HOST} \
  -e REDIS_PORT=${REDIS_PORT} \
  -e REDIS_PASSWORD=${REDIS_PASSWORD} \
  -e REDIS_DB=1 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  -e NACOS_USERNAME=nacos \
  -e NACOS_PASSWORD=nacos \
  -e NACOS_NAMESPACE=public \
  -e NACOS_GROUP=DEFAULT_GROUP \
  -e JAEGER_ENDPOINT=jaeger:4317 \
  -e ENABLE_NACOS=false \
  -e ENABLE_JAEGER=false \
  -e ENABLE_PROMETHEUS=false \
  -e JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  -e JWT_ALGORITHM=HS256 \
  -e JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  -e JWT_REFRESH_TOKEN_EXPIRE_DAYS=7 \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  intel-cw-ms/auth-service:latest
```

**简化版本:**

```powershell
docker run -d \
  --name auth-service \
  --network intel-network \
  --ip 172.20.0.101 \
  -p 8001:8001 \
  --env-file .env \
  -e PYTHONPATH=/install/lib/python3.8/site-packages:/app \
  --restart unless-stopped \
  intel-cw-ms/auth-service:latest
```

### Host Service 单独部署

#### 1. 构建镜像

```powershell
docker build -f services/host-service/Dockerfile -t intel-cw-ms/host-service:latest .
```

#### 2. 运行容器

```powershell
# 创建网络（如果不存在）
docker network create --subnet=172.20.0.0/16 intel-network

# 创建数据卷（如果不存在）
docker volume create host_service_uploads

# 运行容器
docker run -d \
  --name host-service \
  --network intel-network \
  --ip 172.20.0.103 \
  -p 8003:8003 \
  --env-file .env \
  -e SERVICE_NAME=host-service \
  -e SERVICE_PORT=8003 \
  -e HOST_SERVICE_PORT=8003 \
  -e HOST_SERVICE_IP=172.20.0.103 \
  -e GATEWAY_SERVICE_IP=gateway-service \
  -e GATEWAY_SERVICE_PORT=8000 \
  -e AUTH_SERVICE_IP=auth-service \
  -e AUTH_SERVICE_PORT=8001 \
  -e MARIADB_HOST=intel-mariadb \
  -e MARIADB_PORT=3306 \
  -e MARIADB_USER=intel_user \
  -e MARIADB_PASSWORD=${MARIADB_PASSWORD} \
  -e MARIADB_DATABASE=intel_cw \
  -e REDIS_HOST=${REDIS_HOST} \
  -e REDIS_PORT=${REDIS_PORT} \
  -e REDIS_PASSWORD=${REDIS_PASSWORD} \
  -e REDIS_DB=3 \
  -e NACOS_SERVER_ADDR=http://nacos:8848 \
  -e NACOS_USERNAME=nacos \
  -e NACOS_PASSWORD=nacos \
  -e NACOS_NAMESPACE=public \
  -e NACOS_GROUP=DEFAULT_GROUP \
  -e JAEGER_ENDPOINT=jaeger:4317 \
  -e ENABLE_NACOS=false \
  -e ENABLE_JAEGER=false \
  -e ENABLE_PROMETHEUS=false \
  -e JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  -e USE_HARDWARE_MOCK=false \
  -e FILE_UPLOAD_DIR=/app/uploads \
  -v host_service_uploads:/app/uploads \
  --restart unless-stopped \
  --ulimit nofile=4096:8192 \
  intel-cw-ms/host-service:latest
```

**简化版本:**

```powershell
docker run -d \
  --name host-service \
  --network intel-network \
  --ip 172.20.0.103 \
  -p 8003:8003 \
  --env-file .env \
  -e PYTHONPATH=/install/lib/python3.8/site-packages:/app \
  -v host_service_uploads:/app/uploads \
  --restart unless-stopped \
  --ulimit nofile=4096:8192 \
  intel-cw-ms/host-service:latest
```

---

## 常用操作命令

### 查看服务状态

```powershell
# Docker Compose 方式
docker-compose ps

# Docker 单独方式
docker ps

# 查看所有容器（包括已停止的）
docker ps -a
```

### 查看服务日志

```powershell
# Docker Compose 方式
docker-compose logs -f gateway-service
docker-compose logs -f auth-service
docker-compose logs -f host-service

# 查看所有服务日志
docker-compose logs -f

# Docker 单独方式
docker logs -f gateway-service
docker logs -f auth-service
docker logs -f host-service

# 查看最近 100 行日志
docker logs --tail 100 gateway-service
```

### 重启服务

```powershell
# Docker Compose 方式
docker-compose restart gateway-service
docker-compose restart

# Docker 单独方式
docker restart gateway-service
```

### 停止服务

```powershell
# Docker Compose 方式
docker-compose stop gateway-service
docker-compose stop

# Docker 单独方式
docker stop gateway-service
```

### 删除服务

```powershell
# Docker Compose 方式
docker-compose rm -f gateway-service
docker-compose down

# Docker 单独方式
docker rm -f gateway-service
```

### 进入容器

```powershell
# Docker Compose 方式
docker-compose exec gateway-service bash

# Docker 单独方式
docker exec -it gateway-service bash
```

### 查看容器资源使用

```powershell
# 查看所有容器资源使用
docker stats

# 查看特定容器资源使用
docker stats gateway-service
```

### 查看镜像

```powershell
# 查看所有镜像
docker images

# 查看特定镜像
docker images | grep intel-cw-ms
```

### 删除镜像

```powershell
# 删除特定镜像
docker rmi intel-cw-ms/gateway-service:latest

# 删除所有未使用的镜像
docker image prune -a
```

---

## 故障排查

### 1. 服务无法启动

**问题：** 容器启动后立即退出

**排查步骤：**

```powershell
# 查看容器日志
docker logs gateway-service

# 查看容器退出状态
docker inspect gateway-service | Select-String -Pattern "ExitCode"

# 检查环境变量
docker exec gateway-service env
```

**常见原因：**
- 环境变量配置错误（特别是 `JWT_SECRET_KEY`、`MARIADB_PASSWORD`、`REDIS_PASSWORD`）
- 数据库连接失败
- Redis 连接失败
- 端口冲突

### 2. 服务健康检查失败

**问题：** 健康检查返回非 200 状态码

**排查步骤：**

```powershell
# 手动测试健康检查端点
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8003/health

# 进入容器测试
docker exec -it gateway-service bash
curl http://localhost:8000/health
```

**常见原因：**
- 服务未完全启动
- 应用代码错误
- 依赖服务未就绪

### 3. 网络连接问题

**问题：** 服务间无法通信

**排查步骤：**

**Windows PowerShell:**
```powershell
# 检查网络是否存在
docker network ls

# 检查容器网络配置
docker inspect gateway-service | Select-String -Pattern "NetworkSettings"

# 测试容器间网络连接
docker exec -it gateway-service ping auth-service
docker exec -it gateway-service ping host-service
```

**Linux:**
```bash
# 检查网络是否存在
docker network ls

# 检查容器网络配置
docker inspect gateway-service | grep -A 20 "NetworkSettings"

# 测试容器间网络连接
docker exec -it gateway-service ping -c 4 auth-service
docker exec -it gateway-service ping -c 4 host-service

# 检查防火墙状态（如果使用 firewalld）
sudo firewall-cmd --list-all

# 检查防火墙状态（如果使用 ufw）
sudo ufw status

# 如果防火墙阻止，可以临时关闭测试（不推荐生产环境）
# sudo systemctl stop firewalld
# 或
# sudo ufw disable
```

**常见原因：**
- 容器未加入同一网络
- 网络配置错误
- 防火墙规则阻止（Linux 常见）
- SELinux 策略限制（CentOS/RHEL）

### 4. 端口冲突

**问题：** 端口已被占用

**排查步骤：**

**Windows PowerShell:**
```powershell
# Windows 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :8003

# 查看占用端口的进程
tasklist | findstr <PID>
```

**Linux:**
```bash
# Linux 查看端口占用
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :8001
sudo netstat -tulpn | grep :8003

# 或使用 ss 命令（更现代）
sudo ss -tulpn | grep :8000

# 或使用 lsof
sudo lsof -i :8000

# 查看占用端口的进程详情
ps aux | grep <PID>
```

**解决方案：**
- 修改 `.env` 文件中的端口配置
- 停止占用端口的进程（Linux: `sudo kill <PID>`）
- 使用不同的端口映射

### 5. 镜像构建失败

**问题：** `docker build` 或 `docker compose build` 失败

**排查步骤：**

**Windows PowerShell:**
```powershell
# 查看详细构建日志
docker-compose build --no-cache gateway-service

# 检查 Dockerfile 语法
docker build -f services/gateway-service/Dockerfile --dry-run .
```

**Linux:**
```bash
# 查看详细构建日志
docker compose build --no-cache gateway-service

# 检查 Dockerfile 语法
docker build -f services/gateway-service/Dockerfile --dry-run .

# 检查磁盘空间
df -h

# 清理 Docker 构建缓存
docker builder prune

# 查看 Docker 系统信息
docker system df
```

**常见原因：**
- Dockerfile 语法错误
- 依赖文件缺失
- 网络问题导致依赖下载失败
- 磁盘空间不足（Linux 常见）
- 权限问题（Linux 常见，确保用户在 docker 组中）

### 8. uvicorn 模块未找到错误

**问题：** 启动容器时出现 `No module named uvicorn` 错误

**错误信息：**
```
/usr/local/bin/python: No module named uvicorn
```

**排查步骤：**

**Windows PowerShell:**
```powershell
# 进入容器检查
docker exec -it gateway-service bash

# 检查 Python 路径
python -c "import sys; print('\n'.join(sys.path))"

# 检查 uvicorn 是否安装
python -c "import uvicorn; print(uvicorn.__file__)"

# 检查 PATH 环境变量
echo $PATH

# 检查可执行文件是否存在
ls -la /install/bin/uvicorn
ls -la /install/lib/python3.8/site-packages/uvicorn/
```

**Linux:**
```bash
# 进入容器检查
docker exec -it gateway-service bash

# 检查 Python 路径
python -c "import sys; print('\n'.join(sys.path))"

# 检查 uvicorn 是否安装
python -c "import uvicorn; print(uvicorn.__file__)"

# 检查 PATH 环境变量
echo $PATH

# 检查可执行文件是否存在
ls -la /install/bin/uvicorn
ls -la /install/lib/python3.8/site-packages/uvicorn/

# 检查 PYTHONPATH
echo $PYTHONPATH
```

**解决方案：**

1. **重新构建镜像（无缓存）**
   ```bash
   # Windows PowerShell
   docker-compose build --no-cache gateway-service
   docker-compose build --no-cache auth-service
   docker-compose build --no-cache host-service

   # Linux
   docker compose build --no-cache gateway-service
   docker compose build --no-cache auth-service
   docker compose build --no-cache host-service
   ```

2. **检查 requirements 文件**
   ```bash
   # 确认 requirements-no-hash.txt 包含 uvicorn
   grep uvicorn services/gateway-service/requirements-no-hash.txt
   grep uvicorn services/auth-service/requirements-no-hash.txt
   grep uvicorn services/host-service/requirements-no-hash.txt
   ```

3. **验证安装路径**
   ```bash
   # 在构建阶段检查
   docker build -f services/gateway-service/Dockerfile --target builder -t test-builder .
   docker run --rm test-builder ls -la /install/bin/
   docker run --rm test-builder ls -la /install/lib/python3.8/site-packages/ | grep uvicorn
   ```

**常见原因：**
- 多阶段构建时依赖未正确复制
- PATH 或 PYTHONPATH 环境变量配置错误
- requirements 文件格式错误
- pip 安装失败但构建未报错

### 6. 数据卷问题

**问题：** 文件上传目录数据丢失

**排查步骤：**

**Windows PowerShell:**
```powershell
# 查看数据卷列表
docker volume ls

# 查看数据卷详情
docker volume inspect host_service_uploads

# 检查容器挂载
docker inspect host-service | Select-String -Pattern "Mounts"
```

**Linux:**
```bash
# 查看数据卷列表
docker volume ls

# 查看数据卷详情
docker volume inspect host_service_uploads

# 检查容器挂载
docker inspect host-service | grep -A 10 "Mounts"

# 查看数据卷实际存储位置
docker volume inspect host_service_uploads | grep Mountpoint

# 备份数据卷（示例）
docker run --rm \
  -v host_service_uploads:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/host_service_uploads_backup.tar.gz -C /data .
```

**解决方案：**
- 确保使用命名数据卷（`host_service_uploads`）
- 检查数据卷挂载配置
- 备份重要数据
- 检查数据卷权限（Linux 常见问题）

### 7. 环境变量未生效

**问题：** 环境变量配置了但未生效

**排查步骤：**

```powershell
# 检查容器环境变量
docker exec gateway-service env

# 检查 .env 文件格式
# 确保使用 KEY=VALUE 格式，不要有空格
# 确保没有引号（除非值中包含空格）
```

**常见原因：**
- `.env` 文件格式错误
- 环境变量名称拼写错误
- 容器启动时未加载 `.env` 文件

### 8. 启动报错: No module named uvicorn

**问题：** 容器启动失败，日志显示 `/usr/local/bin/python: No module named uvicorn`

**原因：**
本地 `.env` 文件中设置了 `PYTHONPATH`（例如 `PYTHONPATH=/your/local/project/path`），导致容器内的 `PYTHONPATH`（应为 `/install/lib/python3.8/site-packages`）被覆盖，无法找到已安装的依赖。

**解决方案：**

1.  **方法一（推荐）：** 从本地 `.env` 文件中移除 `PYTHONPATH` 变量。
2.  **方法二：** 在 `docker run` 命令中添加 `-e` 参数强制覆盖：
    ```bash
    -e PYTHONPATH=/install/lib/python3.8/site-packages:/app
    ```
3.  **方法三：** 修改 `docker-compose.yml`（已默认修复），确保显式设置环境变量。


---

## 最佳实践

### 1. 生产环境部署

- ✅ 使用强密码（`JWT_SECRET_KEY`、`MARIADB_PASSWORD`、`REDIS_PASSWORD`）
- ✅ 设置 `DEBUG=false`
- ✅ 设置 `LOG_LEVEL=INFO` 或 `WARNING`
- ✅ 使用 HTTPS（通过反向代理）
- ✅ 定期备份数据卷
- ✅ 监控容器资源使用情况
- ✅ 设置资源限制（CPU、内存）

### 2. 开发环境部署

- ✅ 可以使用 `DEBUG=true`
- ✅ 设置 `LOG_LEVEL=DEBUG`
- ✅ 使用 `USE_HARDWARE_MOCK=true`（Host Service）
- ✅ 启用所有监控组件（Nacos、Jaeger、Prometheus）

### 3. 性能优化

- ✅ 使用多阶段构建减小镜像大小
- ✅ 使用 `.dockerignore` 排除不必要的文件
- ✅ 合理设置 `ulimits`（特别是 WebSocket 服务）
- ✅ 使用健康检查确保服务可用性
- ✅ 配置自动重启策略（`restart: unless-stopped`）

---

## 快速参考

### 一键启动所有服务

**Windows PowerShell:**
```powershell
docker-compose up -d --build
```

**Linux:**
```bash
docker compose up -d --build
```

### 一键停止所有服务

**Windows PowerShell:**
```powershell
docker-compose down
```

**Linux:**
```bash
docker compose down
```

### 查看所有服务日志

**Windows PowerShell:**
```powershell
docker-compose logs -f
```

**Linux:**
```bash
docker compose logs -f
```

### 重启所有服务

**Windows PowerShell:**
```powershell
docker-compose restart
```

**Linux:**
```bash
docker compose restart
```

### 重新构建并启动

**Windows PowerShell:**
```powershell
docker-compose up -d --build --force-recreate
```

**Linux:**
```bash
docker compose up -d --build --force-recreate
```

---

## Linux 特定注意事项

### 1. 权限问题

**问题：** 执行 Docker 命令需要 `sudo`

**解决方案：**
```bash
# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker

# 验证权限
docker ps
```

### 2. SELinux 配置（CentOS/RHEL）

**问题：** SELinux 可能阻止容器访问文件系统

**解决方案：**
```bash
# 临时禁用 SELinux（不推荐生产环境）
sudo setenforce 0

# 永久禁用 SELinux（编辑 /etc/selinux/config）
sudo sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

# 或配置 SELinux 上下文（推荐）
sudo chcon -Rt svirt_sandbox_file_t /path/to/directory
```

### 3. 防火墙配置

**问题：** 防火墙阻止容器间通信

**解决方案：**
```bash
# firewalld（CentOS/RHEL）
sudo firewall-cmd --permanent --add-masquerade
sudo firewall-cmd --reload

# ufw（Ubuntu/Debian）
sudo ufw allow from 172.20.0.0/16
sudo ufw reload
```

### 4. 系统资源限制

**问题：** 容器资源使用受限

**解决方案：**
```bash
# 检查系统限制
ulimit -a

# 编辑 /etc/security/limits.conf
sudo tee -a /etc/security/limits.conf <<EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

# 重新登录使配置生效
```

### 5. Docker 服务管理

```bash
# 启动 Docker 服务
sudo systemctl start docker

# 停止 Docker 服务
sudo systemctl stop docker

# 重启 Docker 服务
sudo systemctl restart docker

# 设置开机自启
sudo systemctl enable docker

# 查看 Docker 服务状态
sudo systemctl status docker

# 查看 Docker 日志
sudo journalctl -u docker.service -f
```

---

**最后更新**: 2025-01-30  
**适用版本**: Docker 20.10+, Docker Compose 2.0+  
**操作系统**: Windows 10/11, Linux, macOS

