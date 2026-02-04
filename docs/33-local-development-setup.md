# 本地开发环境搭建文档

## 📋 概述

本文档提供 Intel EC 微服务项目在 **Windows** 和 **macOS** 平台上的完整本地开发环境搭建指南。

## 🎯 环境要求

### 必需软件

| 软件 | 版本要求 | Windows | macOS |
|------|---------|---------|-------|
| **Python** | 3.8.10 (严格版本) | ✅ | ✅ |
| **Docker** | 20.10+ | ✅ | ✅ |
| **Docker Compose** | v2.0+ | ✅ | ✅ |
| **Git** | 2.30+ | ✅ | ✅ |
| **MariaDB** | 10.11+ (可选，可使用Docker) | ✅ | ✅ |
| **Redis** | 6.0+ (可选，可使用Docker) | ✅ | ✅ |

### 推荐工具

- **IDE**: VS Code / PyCharm
- **数据库客户端**: DBeaver / Navicat / MySQL Workbench
- **API 测试**: Postman / Insomnia
- **终端**: Windows Terminal (Windows) / iTerm2 (macOS)

---

## 🪟 Windows 平台搭建

### 1. 安装 Python 3.8.10

#### 方法一：使用官方安装包（推荐）

1. **下载 Python 3.8.10**
   - 访问：https://www.python.org/downloads/release/python-3810/
   - 下载：`Windows installer (64-bit)` 或 `Windows installer (32-bit)`

2. **安装 Python**
   - 运行安装程序
   - ✅ **重要**：勾选 "Add Python 3.8 to PATH"
   - 选择 "Install Now" 或 "Customize installation"
   - 完成安装

3. **验证安装**
   ```powershell
   python --version
   # 应输出: Python 3.8.10
   
   pip --version
   # 应输出: pip 20.x.x from ...
   ```

#### 方法二：使用 pyenv-win（多版本管理）

```powershell
# 1. 安装 pyenv-win
git clone https://github.com/pyenv-win/pyenv-win.git %USERPROFILE%\.pyenv

# 2. 添加到 PATH（PowerShell）
[System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\.pyenv","User")
[System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\.pyenv","User")
[System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\.pyenv","User")
[System.Environment]::SetEnvironmentVariable('path', $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")

# 3. 安装 Python 3.8.10
pyenv install 3.8.10
pyenv local 3.8.10

# 4. 验证
python --version
```

### 2. 安装 Docker Desktop

1. **下载 Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop/
   - 下载：`Docker Desktop for Windows`

2. **安装 Docker Desktop**
   - 运行安装程序
   - 按照向导完成安装
   - 重启计算机（如提示）

3. **启动 Docker Desktop**
   - 从开始菜单启动 Docker Desktop
   - 等待 Docker 引擎启动完成

4. **验证安装**
   ```powershell
   docker --version
   # 应输出: Docker version 20.x.x, build ...
   
   docker-compose --version
   # 应输出: Docker Compose version v2.x.x
   ```

### 3. 安装 Git

1. **下载 Git**
   - 访问：https://git-scm.com/download/win
   - 下载：最新版本安装程序

2. **安装 Git**
   - 运行安装程序
   - 使用默认选项即可
   - 完成安装

3. **验证安装**
   ```powershell
   git --version
   # 应输出: git version 2.x.x
   ```

### 4. 安装 MariaDB（可选，推荐使用 Docker）

#### 方法一：使用 Docker（推荐）

```powershell
# 启动 MariaDB 容器
docker run -d `
  --name intel-mariadb `
  -p 3306:3306 `
  -e MARIADB_ROOT_PASSWORD=mariadb123 `
  -e MARIADB_DATABASE=intel_cw `
  -e MARIADB_USER=intel_user `
  -e MARIADB_PASSWORD=intel_pass123 `
  mariadb:10.11
```

#### 方法二：本地安装

1. **下载 MariaDB**
   - 访问：https://mariadb.org/download/
   - 下载：Windows 安装程序

2. **安装 MariaDB**
   - 运行安装程序
   - 设置 root 密码
   - 完成安装

3. **创建数据库**
   ```sql
   CREATE DATABASE intel_cw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'intel_user'@'localhost' IDENTIFIED BY 'intel_pass123';
   GRANT ALL PRIVILEGES ON intel_cw.* TO 'intel_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

### 5. 安装 Redis（可选，推荐使用 Docker）

#### 方法一：使用 Docker（推荐）

```powershell
# 启动 Redis 容器
docker run -d `
  --name intel-redis `
  -p 6379:6379 `
  redis:6.2-alpine
```

#### 方法二：使用 WSL2（推荐）

```powershell
# 在 WSL2 中安装 Redis
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

---

## 🍎 macOS 平台搭建

### 1. 安装 Python 3.8.10

#### 方法一：使用 pyenv（推荐）

```bash
# 1. 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装 pyenv
brew install pyenv

# 3. 配置 shell（添加到 ~/.zshrc 或 ~/.bash_profile）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 4. 重新加载 shell
source ~/.zshrc

# 5. 安装 Python 3.8.10
pyenv install 3.8.10
pyenv local 3.8.10

# 6. 验证安装
python --version
# 应输出: Python 3.8.10
```

#### 方法二：使用官方安装包

1. **下载 Python 3.8.10**
   - 访问：https://www.python.org/downloads/release/python-3810/
   - 下载：`macOS 64-bit installer`

2. **安装 Python**
   - 运行安装程序
   - 按照向导完成安装

3. **验证安装**
   ```bash
   python3 --version
   # 应输出: Python 3.8.10
   ```

### 2. 安装 Docker Desktop

1. **下载 Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop/
   - 下载：`Docker Desktop for Mac`

2. **安装 Docker Desktop**
   - 打开下载的 `.dmg` 文件
   - 将 Docker 拖拽到 Applications 文件夹
   - 启动 Docker Desktop

3. **验证安装**
   ```bash
   docker --version
   docker-compose --version
   ```

### 3. 安装 Git

```bash
# macOS 通常已预装 Git，验证版本
git --version

# 如果需要更新，使用 Homebrew
brew install git
```

### 4. 安装 MariaDB（可选，推荐使用 Docker）

#### 方法一：使用 Docker（推荐）

```bash
# 启动 MariaDB 容器
docker run -d \
  --name intel-mariadb \
  -p 3306:3306 \
  -e MARIADB_ROOT_PASSWORD=mariadb123 \
  -e MARIADB_DATABASE=intel_cw \
  -e MARIADB_USER=intel_user \
  -e MARIADB_PASSWORD=intel_pass123 \
  mariadb:10.11
```

#### 方法二：使用 Homebrew

```bash
# 安装 MariaDB
brew install mariadb

# 启动服务
brew services start mariadb

# 创建数据库
mysql -u root -p
CREATE DATABASE intel_cw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'intel_user'@'localhost' IDENTIFIED BY 'intel_pass123';
GRANT ALL PRIVILEGES ON intel_cw.* TO 'intel_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. 安装 Redis（可选，推荐使用 Docker）

#### 方法一：使用 Docker（推荐）

```bash
# 启动 Redis 容器
docker run -d \
  --name intel-redis \
  -p 6379:6379 \
  redis:6.2-alpine
```

#### 方法二：使用 Homebrew

```bash
# 安装 Redis
brew install redis

# 启动服务
brew services start redis

# 验证
redis-cli ping
# 应输出: PONG
```

---

## 📦 项目配置

### 1. 克隆项目

```bash
# Windows (PowerShell)
git clone <repository-url>
cd intel_ec_ms

# macOS / Linux
git clone <repository-url>
cd intel_ec_ms
```

### 2. 创建虚拟环境

#### Windows

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1
# 如果遇到执行策略问题，运行：
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或使用 cmd
venv\Scripts\activate.bat
```

#### macOS / Linux

```bash
# 创建虚拟环境
python3.8 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

### 3. 安装 Python 依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 安装开发工具（可选）
pip install ruff mypy pyright pytest pytest-asyncio pytest-cov
```

### 4. 配置环境变量

#### 创建 .env 文件

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

#### 编辑 .env 文件

**Windows 路径示例**：
```env
# Python 环境配置
PYTHONPATH=C:\Users\YourName\Projects\intel_ec_ms

# 服务配置
SERVICE_HOST_AUTH=127.0.0.1
SERVICE_HOST_HOST=127.0.0.1

# 数据库配置
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=intel_user
MARIADB_PASSWORD=intel_pass123
MARIADB_DATABASE=intel_cw

# MariaDB SSL/TLS 配置（可选，开发环境通常不需要）
# MARIADB_SSL_ENABLED=false
# MARIADB_SSL_VERIFY_CERT=false

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 组件开关（本地开发可关闭）
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false

# 文件上传配置
FILE_UPLOAD_DIR=C:\Users\YourName\Downloads\uploads
```

**macOS 路径示例**：
```env
# Python 环境配置
PYTHONPATH=/Users/YourName/KiroProjects/intel_ec_ms

# 服务配置
SERVICE_HOST_AUTH=127.0.0.1
SERVICE_HOST_HOST=127.0.0.1

# 数据库配置
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=intel_user
MARIADB_PASSWORD=intel_pass123
MARIADB_DATABASE=intel_cw

# MariaDB SSL/TLS 配置（可选，开发环境通常不需要）
# MARIADB_SSL_ENABLED=false
# MARIADB_SSL_VERIFY_CERT=false

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 组件开关（本地开发可关闭）
ENABLE_NACOS=false
ENABLE_JAEGER=false
ENABLE_PROMETHEUS=false

# 文件上传配置
FILE_UPLOAD_DIR=/Users/YourName/Downloads/uploads
```

### 5. 初始化数据库

#### 使用 Docker MariaDB

```bash
# 如果使用 Docker 启动的 MariaDB，数据库已自动创建
# 只需要导入初始化脚本（如果有）

# Windows
docker exec -i intel-mariadb mysql -uroot -pmariadb123 intel_cw < docs/database/db.sql

# macOS / Linux
docker exec -i intel-mariadb mysql -uroot -pmariadb123 intel_cw < docs/database/db.sql
```

#### 使用本地 MariaDB

```bash
# 连接数据库
mysql -h 127.0.0.1 -P 3306 -u intel_user -pintel_pass123

# 导入初始化脚本
source docs/database/db.sql
```

---

## 🚀 启动服务

### 1. 启动基础设施服务（Docker）

```bash
# 启动 MariaDB、Redis、Nacos、Jaeger（如果启用）
docker-compose up -d mariadb redis nacos jaeger

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f mariadb
```

### 2. 启动微服务（本地开发）

#### Windows

**方法一：使用启动脚本**

```powershell
# 使用 PowerShell 脚本
.\scripts\start_services_local.bat gateway
.\scripts\start_services_local.bat auth
.\scripts\start_services_local.bat host
```

**方法二：手动启动**

```powershell
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 设置 PYTHONPATH
$env:PYTHONPATH = "C:\Users\YourName\Projects\intel_ec_ms"

# 启动 Gateway Service
cd services\gateway-service
python -m app.main

# 启动 Auth Service（新终端）
cd services\auth-service
python -m app.main

# 启动 Host Service（新终端）
cd services\host-service
python -m app.main
```

#### macOS / Linux

**方法一：使用启动脚本**

```bash
# 使用 Shell 脚本
chmod +x scripts/start_services_local.sh
./scripts/start_services_local.sh gateway
./scripts/start_services_local.sh auth
./scripts/start_services_local.sh host
```

**方法二：手动启动**

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置 PYTHONPATH
export PYTHONPATH=$(pwd)

# 启动 Gateway Service
cd services/gateway-service
python -m app.main

# 启动 Auth Service（新终端）
cd services/auth-service
python -m app.main

# 启动 Host Service（新终端）
cd services/host-service
python -m app.main
```

### 3. 验证服务启动

访问以下地址确认服务正常运行：

- **Gateway Service**: http://localhost:8000/health
- **Auth Service**: http://localhost:8001/health
- **Host Service**: http://localhost:8003/health

**API 文档**：
- **Gateway**: http://localhost:8000/docs
- **Auth**: http://localhost:8001/docs
- **Host**: http://localhost:8003/docs

---

## 🧪 开发工具配置

### 1. VS Code 配置

#### 安装推荐扩展

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Ruff** (Astral Software)
- **MyPy Type Checker** (Microsoft)
- **Python Test Explorer** (Little Fox Team)

#### 工作区设置 (.vscode/settings.json)

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit"
    }
  },
  "ruff.enable": true,
  "ruff.organizeImports": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### 2. PyCharm 配置

1. **设置 Python 解释器**
   - File → Settings → Project → Python Interpreter
   - 选择项目虚拟环境：`venv/bin/python`

2. **配置代码检查**
   - File → Settings → Tools → External Tools
   - 添加 Ruff、MyPy 工具

3. **配置运行配置**
   - Run → Edit Configurations
   - 添加 Python 配置，设置：
     - Script path: `services/gateway-service/app/main.py`
     - Environment variables: `PYTHONPATH=$ProjectFileDir$`

---

## 🔧 常见问题排查

### Windows 平台

#### 问题 1: Python 版本不正确

**症状**：`python --version` 显示非 3.8.10

**解决方案**：
```powershell
# 检查已安装的 Python 版本
py -0

# 使用特定版本
py -3.8 --version

# 创建虚拟环境时指定版本
py -3.8 -m venv venv
```

#### 问题 2: PowerShell 执行策略限制

**症状**：无法运行 `.\venv\Scripts\Activate.ps1`

**解决方案**：
```powershell
# 设置执行策略（当前用户）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或使用 cmd 激活
venv\Scripts\activate.bat
```

#### 问题 3: Docker Desktop 无法启动

**症状**：Docker Desktop 启动失败

**解决方案**：
1. 确保已启用 WSL2（Windows 10/11）
2. 检查 Hyper-V 是否启用
3. 重启计算机
4. 检查防火墙设置

#### 问题 4: 端口被占用

**症状**：服务启动失败，提示端口被占用

**解决方案**：
```powershell
# 查看端口占用情况
netstat -ano | findstr :8000

# 结束占用进程（替换 PID）
taskkill /PID <PID> /F
```

### macOS 平台

#### 问题 1: Python 版本管理冲突

**症状**：多个 Python 版本导致混乱

**解决方案**：
```bash
# 使用 pyenv 管理版本
pyenv install 3.8.10
pyenv local 3.8.10

# 验证
python --version
which python
```

#### 问题 2: 权限问题

**症状**：无法安装包或创建文件

**解决方案**：
```bash
# 修复虚拟环境权限
chmod -R u+w venv

# 修复脚本执行权限
chmod +x scripts/*.sh
```

#### 问题 3: Docker Desktop 资源不足

**症状**：Docker 容器启动失败

**解决方案**：
1. Docker Desktop → Settings → Resources
2. 增加 CPU 和内存分配
3. 重启 Docker Desktop

#### 问题 4: 数据库连接失败

**症状**：无法连接到 MariaDB

**解决方案**：
```bash
# 检查 Docker 容器状态
docker ps | grep mariadb

# 检查端口占用
lsof -i :3306

# 测试连接
mysql -h 127.0.0.1 -P 3306 -u intel_user -p
```

---

## 📝 开发工作流

### 1. 日常开发流程

```bash
# 1. 激活虚拟环境
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\Activate.ps1  # Windows

# 2. 拉取最新代码
git pull origin main

# 3. 安装新依赖（如果有）
pip install -r requirements.txt

# 4. 运行代码质量检查
ruff check services/ shared/
mypy services/ shared/

# 5. 启动服务
./scripts/start_services_local.sh gateway
```

### 2. 代码提交前检查

```bash
# 运行完整检查脚本
./scripts/check_quality.sh

# 或手动运行
ruff check --fix services/ shared/
ruff format services/ shared/
mypy services/ shared/
```

### 3. 测试运行

```bash
# 运行所有测试
pytest

# 运行特定服务测试
pytest services/gateway-service/tests/

# 生成覆盖率报告
pytest --cov=services --cov-report=html
```

---

## 📚 相关文档

- [快速开始指南](./00-quick-start.md)
- [项目设置文档](./04-project-setup.md)
- [代码质量配置](./08-code-quality-setup.md)
- [WebSocket 使用指南](./18-websocket-usage.md)
- [API 文档指南](./api/API_DOCUMENTATION_GUIDE.md)

---

## 🆘 获取帮助

如果遇到问题，请：

1. **查看日志**
   ```bash
   # 服务日志
   tail -f logs/gateway-service.log
   
   # Docker 日志
   docker-compose logs -f gateway-service
   ```

2. **检查环境配置**
   ```bash
   # 验证环境变量
   ./scripts/verify_setup.sh
   ```

3. **查阅文档**
   - 项目 README.md
   - docs/ 目录下的相关文档

4. **联系团队**
   - 提交 Issue
   - 联系项目维护者

---

**最后更新**: 2025-01-29  
**版本**: 1.0.0  
**维护者**: Intel EC 开发团队

