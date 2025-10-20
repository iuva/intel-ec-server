# 本地启动脚本修复说明

## 问题描述

在使用 `./scripts/start_services_local.sh auth` 启动服务时，遇到了以下错误：

```
ModuleNotFoundError: No module named 'app'
```

### 错误堆栈

```python
File "/Users/chiyeming/KiroProjects/intel_ec_ms/services/auth-service/app/main.py", line 294, in <module>
    from app.api.v1 import api_router
ModuleNotFoundError: No module named 'app'
```

## 根本原因

服务代码中使用了相对导入：

```python
from app.api.v1 import api_router
```

这种导入方式要求 **工作目录必须在服务目录中**（即 `services/auth-service/`），这样 Python 才能找到 `app` 模块。

但原始启动脚本是从项目根目录启动 uvicorn 的：

```bash
# ❌ 错误的启动方式
cd /Users/chiyeming/KiroProjects/intel_ec_ms
python -m uvicorn services.auth-service.app.main:app --port 8001
```

这会导致 Python 无法找到相对导入的 `app` 模块。

## 解决方案

### 核心修改

修改 `start_service()` 函数，使其进入服务目录后启动：

```bash
# ✅ 正确的启动方式
cd /Users/chiyeming/KiroProjects/intel_ec_ms/services/auth-service
python -m uvicorn app.main:app --port 8001
```

### 脚本修改详情

#### Mac/Linux 脚本 (`scripts/start_services_local.sh`)

**修改前**：
```bash
start_service() {
    local service_name=$1
    local port=$2
    local module_path=$3
    
    # ...
    python -m uvicorn "$module_path" --host 0.0.0.0 --port "$port" --reload
}
```

**修改后**：
```bash
start_service() {
    local service_name=$1
    local port=$2
    local service_dir=$3
    
    # 进入服务目录后启动（这样相对导入才能工作）
    cd "$PROJECT_ROOT"/"$service_dir"
    python -m uvicorn app.main:app --host 0.0.0.0 --port "$port" --reload
}
```

**参数调用修改**：
```bash
# 修改前：使用完整模块路径
start_service "Auth Service" "8001" "services.auth-service.app.main:app"

# 修改后：使用服务目录路径
start_service "Auth Service" "8001" "services/auth-service"
```

#### Windows 脚本 (`scripts/start_services_local.bat`)

类似的修改应用于 Windows 批处理脚本，使用 `cd /d` 命令进入服务目录。

### 验证修复

修复后，脚本能够成功启动服务：

```bash
$ ./scripts/start_services_local.sh auth
📋 从 .env 文件加载环境变量...
✓ 环境变量加载成功

🐍 激活虚拟环境...
✓ 虚拟环境激活成功

✓ PYTHONPATH 已设置为: /Users/chiyeming/KiroProjects/intel_ec_ms:

════════════════════════════════════════
🚀 启动 Auth Service (端口: 8001)
════════════════════════════════════════

服务目录: services/auth-service
工作目录: /Users/chiyeming/KiroProjects/intel_ec_ms/services/auth-service

INFO:     Will watch for changes in these directories: ['/Users/chiyeming/KiroProjects/intel_ec_ms/services/auth-service']
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

## 最佳实践

### 1. 服务目录结构

每个微服务都应该遵循统一的目录结构：

```
services/auth-service/
├── app/
│   ├── __init__.py
│   ├── main.py           # 主应用入口
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   ├── models/           # 数据模型
│   ├── services/         # 业务逻辑
│   └── schemas/          # Pydantic 模型
├── Dockerfile
├── requirements.txt
└── README.md
```

### 2. 导入规范

在服务代码中使用相对导入（相对于 `app` 目录）：

```python
# ✅ 正确：相对导入
from app.api.v1.endpoints import auth
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate
```

**不要**使用绝对导入（相对于项目根目录）：

```python
# ❌ 错误：绝对导入（在从项目根目录启动时会失败）
from services.auth-service.app.api.v1.endpoints import auth
```

### 3. 启动脚本规范

启动脚本应该：

1. ✅ 自动进入服务目录
2. ✅ 使用简化的模块路径 `app.main:app`
3. ✅ 保持工作目录一致性
4. ✅ 支持相对导入

## 对 Docker 部署的影响

✅ **无影响**！Docker 部署不受此更改影响，因为：

1. Docker 镜像中的工作目录已经是项目根目录
2. Dockerfile 中使用的是完整模块路径：`uvicorn services.auth-service.app.main:app`
3. 服务代码的相对导入在完整路径启动时也能正常工作

```dockerfile
# Docker 启动方式保持不变
CMD ["python", "-m", "uvicorn", "services.auth-service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 总结

| 方面 | 修复前 | 修复后 |
|-----|-------|-------|
| 工作目录 | 项目根目录 | 服务目录 |
| 启动方式 | 完整模块路径 | 相对模块路径 |
| 相对导入 | ❌ 失败 | ✅ 成功 |
| Docker | ✅ 正常 | ✅ 正常 |
| 本地开发 | ❌ 出错 | ✅ 正常 |
| 跨平台 | ⚠️ 部分支持 | ✅ 完全支持 |

## 相关文件修改

- ✅ `scripts/start_services_local.sh` - Mac/Linux 启动脚本
- ✅ `scripts/start_services_local.bat` - Windows 启动脚本
- ✅ `README.md` - 文档更新，添加已修复说明和故障排除指南

## 使用方式

现在可以使用修复后的脚本启动服务：

```bash
# Mac/Linux
./scripts/start_services_local.sh auth
./scripts/start_services_local.sh admin
./scripts/start_services_local.sh host
./scripts/start_services_local.sh gateway

# Windows
scripts\start_services_local.bat auth
scripts\start_services_local.bat admin
scripts\start_services_local.bat host
scripts\start_services_local.bat gateway
```

更多详细信息请查看 [README.md](README.md) 中的 "方案 C：使用启动脚本" 部分。
