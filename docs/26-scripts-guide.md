# 脚本目录说明

本目录包含项目的各种自动化脚本，经过整理和规范命名。

## 📁 脚本分类

### 🚀 服务管理脚本

> **注意**: 项目使用 Docker Compose 进行服务管理。服务启动、停止、重启等操作请使用 `docker-compose` 命令。  
> 详细说明请参考 [部署指南](./03-deployment-guide.md#服务管理)

#### start_services_local.sh / start_services_local.bat

**功能**: 本地开发环境启动脚本（自动设置环境变量）

**使用方法**:

```bash
# Linux/macOS
./scripts/start_services_local.sh

# Windows
scripts\start_services_local.bat
```

**功能特性**:

- 自动设置 `*_SERVICE_IP=127.0.0.1` 环境变量
- 自动设置 `JAEGER_ENDPOINT=localhost:4317`
- 支持 Docker 和本地启动方式

#### build_services.sh

**功能**: 批量构建所有微服务Docker镜像
**使用方法**:

```bash
bash scripts/build_services.sh
```

### 🔍 代码质量脚本

#### check_quality.sh

**功能**: 运行完整的代码质量检查
**使用方法**:

```bash
bash scripts/check_quality.sh
```

**检查项目**:

1. Ruff 代码检查
2. Ruff 格式检查
3. MyPy 类型检查

#### fix_quality.sh

**功能**: 自动修复代码质量问题
**使用方法**:

```bash
bash scripts/fix_quality.sh
```

**修复内容**:

1. Ruff 自动修复
2. Ruff 格式化
3. 导入排序修复

#### check_types.sh

**功能**: 运行 Pyright 类型检查
**使用方法**:

```bash
bash scripts/check_types.sh
```

**检查内容**:

- Pyright 类型检查
- 类型注解验证
- 导入路径检查

#### setup_precommit.sh

**功能**: 安装和配置Pre-commit Git钩子
**使用方法**:

```bash
bash scripts/setup_precommit.sh
```

### 🛠️ 工具脚本

#### clean_cache.sh

**功能**: 清理项目缓存文件和目录
**使用方法**:

```bash
bash scripts/clean_cache.sh [选项]
```

**选项**:

- `--dry-run`: 预览模式
- `--aggressive`: 激进模式（清理更多类型的缓存）
- `--path <path>`: 指定清理目录

#### verify_setup.sh

**功能**: 验证项目环境配置
**使用方法**:

```bash
bash scripts/verify_setup.sh
```

#### setup_database.sh

**功能**: 创建MariaDB数据库
**使用方法**:

```bash
bash scripts/setup_database.sh
```

#### generate_token.sh

**功能**: 生成Nacos认证令牌
**使用方法**:

```bash
bash scripts/generate_token.sh [自定义密钥]
```

### 📊 监控脚本

#### start_monitoring.sh

**功能**: 启动Prometheus和Grafana监控系统
**使用方法**:

```bash
bash scripts/start_monitoring.sh
```

#### verify_monitoring.sh

**功能**: 验证监控系统配置和状态
**使用方法**:

```bash
bash scripts/verify_monitoring.sh
```

### 📚 文档生成脚本

#### generate_docs.sh

**功能**: 生成所有微服务的API文档
**使用方法**:

```bash
# 生成所有服务的API文档
bash scripts/generate_docs.sh

# 只检查服务状态
bash scripts/generate_docs.sh --check
```

**生成内容**:

1. OpenAPI JSON 规范文件
2. 端点列表 Markdown 文档
3. 文档汇总 README

**输出目录**: `docs/api/`

#### dev_docs.sh

**功能**: 开发环境一键启动服务并生成文档
**使用方法**:

```bash
# 启动所有服务并生成文档（默认）
bash scripts/dev_docs.sh

# 只生成API文档
bash scripts/dev_docs.sh --docs

# 检查服务健康状态
bash scripts/dev_docs.sh --check

# 停止所有服务
bash scripts/dev_docs.sh --stop

# 重启所有服务
bash scripts/dev_docs.sh --restart
```

**功能特性**:

- 🚀 一键启动基础设施 (MySQL, Redis, Nacos, Jaeger, Prometheus, Grafana)
- 🔄 启动所有微服务
- 📖 自动生成API文档
- 💚 健康检查验证
- 📋 服务信息展示

### 🧪 测试脚本

#### test_api.py

**功能**: API功能测试脚本，验证各服务的API功能
**使用方法**:

```bash
# 运行完整API测试
python scripts/test_api.py

# 指定不同URL或凭据
python scripts/test_api.py --url http://localhost --username admin --password admin123
```

**测试内容**:

1. ✅ 服务健康检查
2. 🔐 用户登录认证
3. 👥 用户管理API测试
4. 🖥️ 主机管理API测试
5. 🔍 404错误响应验证

**示例输出**:

```bash
Intel EC 微服务API测试脚本
========================================

📊 检查服务健康状态:
   网关服务: ✅ 健康
   认证服务: ✅ 健康
   管理服务: ✅ 健康
   主机服务: ✅ 健康

🔐 测试用户登录:
✅ 登录成功

👥 测试用户管理API:
   获取到 5 个用户

🖥️  测试主机管理API:
   获取到 3 个主机

🔍 测试404错误响应:
✅ 网关服务 404响应正确
✅ 认证服务 404响应正确
✅ 管理服务 404响应正确
✅ 主机服务 404响应正确

🎉 API测试完成！
```

#### test_oauth2.sh

**功能**: OAuth 2.0认证端点专项测试
**使用方法**:

```bash
# 运行OAuth 2.0端点测试
./scripts/test_oauth2.sh
```

**测试内容**:

1. 🔐 管理后台令牌获取
2. 🔍 令牌内省验证
3. 📱 设备令牌获取
4. 🔗 直接访问认证服务

**示例输出**:

```bash
🔐 测试OAuth 2.0认证端点
==========================
[PASS] 网关服务运行正常
[PASS] 认证服务运行正常

[INFO] 测试管理后台令牌端点...
[PASS] 管理后台令牌获取成功
[PASS] 访问令牌已获取

[INFO] 测试令牌验证...
[PASS] 令牌验证成功

[INFO] 测试设备令牌端点...
[WARN] 设备令牌获取失败（可能是设备不存在）

[INFO] 测试直接访问认证服务...
[PASS] 直接访问认证服务成功

[PASS] OAuth 2.0端点测试完成！
```

## 📋 使用工作流

### 🏁 首次设置

```bash
# 1. 验证环境
bash scripts/verify_setup.sh

# 2. 设置数据库
bash scripts/setup_database.sh

# 3. 安装pre-commit钩子
bash scripts/setup_precommit.sh

# 4. 构建所有服务
bash scripts/build_services.sh

# 5. 启动所有服务（使用 Docker Compose）
docker-compose up -d

# 6. 启动监控系统
bash scripts/start_monitoring.sh
```

### 👨‍💻 日常开发

```bash
# 1. 开发代码
# ... 编写代码 ...

# 2. 运行代码质量检查
bash scripts/check_quality.sh

# 3. 如果检查失败，自动修复
bash scripts/fix_quality.sh

# 4. 运行类型检查
bash scripts/check_types.sh

# 5. 生成API文档（如果修改了API）
bash scripts/generate_docs.sh

# 6. 提交代码（pre-commit会自动运行检查）
git add .
git commit -m "feat: 添加新功能"
```

### 📖 文档开发工作流

```bash
# 🚀 快速启动开发环境（推荐）
bash scripts/dev_docs.sh

# 📋 生成API文档
bash scripts/dev_docs.sh --docs

# 🔍 检查服务状态
bash scripts/dev_docs.sh --check

# 🔄 重启服务
bash scripts/dev_docs.sh --restart

# 🛑 停止所有服务
bash scripts/dev_docs.sh --stop
```

### 🔄 服务管理

```bash
# 启动服务（后台运行）
docker-compose up -d

# 启动服务（前台运行，查看日志）
docker-compose up

# 重新构建并启动
docker-compose up -d --build

# 停止所有服务
docker-compose down

# 停止服务并删除数据卷
docker-compose down -v

# 重启所有服务
docker-compose restart

# 本地开发环境启动（自动设置环境变量）
./scripts/start_services_local.sh  # Linux/macOS
scripts\start_services_local.bat   # Windows
```

### 🧹 维护操作

```bash
# 清理缓存（预览模式）
bash scripts/clean_cache.sh --dry-run

# 清理缓存（实际执行）
bash scripts/clean_cache.sh

# 激进模式清理（包括node_modules等）
bash scripts/clean_cache.sh --aggressive

# 验证监控系统
bash scripts/verify_monitoring.sh

# 生成Nacos令牌
bash scripts/generate_token.sh
```

## ⚙️ 脚本权限

所有脚本都已设置为可执行权限。如果遇到权限问题，可以运行：

```bash
chmod +x scripts/*.sh
```

## 🔧 故障排查

### 脚本无法执行

**问题**: `Permission denied`
**解决方案**:

```bash
chmod +x scripts/脚本名.sh
```

### 工具未安装

**问题**: `command not found: ruff`
**解决方案**:

```bash
pip install ruff mypy pre-commit
```

### Docker相关问题

**问题**: `Cannot connect to the Docker daemon`
**解决方案**:

1. 确保Docker Desktop已启动
2. 检查Docker服务状态
3. 重启Docker服务

### 端口占用问题

**问题**: 服务启动失败，端口被占用
**解决方案**:

```bash
# 查看端口占用
lsof -i :8000
# 或使用脚本验证
bash scripts/verify_setup.sh
```

### 代码质量检查失败

**解决方案**:

1. 查看错误信息
2. 运行自动修复: `bash scripts/fix_quality.sh`
3. 手动修复剩余问题
4. 重新运行检查: `bash scripts/check_quality.sh`

## 📈 脚本依赖

### 必需工具

- Docker & Docker Compose
- Python 3.8+
- Git

### Python包依赖

- ruff (代码检查和格式化)
- mypy (类型检查)
- pre-commit (Git钩子)

### 可选工具

- mysql-client (数据库操作)
- redis-cli (Redis操作)

## 📚 相关文档

- [快速开始指南](../docs/quick-start.md)
- [项目配置说明](../docs/project-setup.md)
- [Docker部署指南](../docs/docker-deployment.md)
- [监控系统配置](../docs/monitoring-setup.md)

## 🚀 更新历史

- **2025-01-XX**: v2.0 重构版本
  - 删除过时的临时修复脚本
  - 规范化脚本命名
  - 完善文档和使用说明
  - 添加监控管理脚本

- **2025-01-29**: v1.0 初始版本
  - 添加代码质量检查脚本
  - 添加自动修复脚本
  - 添加pre-commit设置脚本
  - 添加服务管理脚本
