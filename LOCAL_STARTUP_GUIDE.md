# 🚀 本地启动快速指南

## 问题已解决 ✅

你的 `ModuleNotFoundError: No module named 'app'` 问题已经修复！

## 修复内容

### 1. 代码修复
- ✅ Gateway Service (`app/main.py`) - 路径深度从 3 改为 4 级
- ✅ Host Service (`app/main.py`) - 路径深度从 3 改为 4 级
- ✅ Admin Service (`app/main.py`) - 路径深度从 3 改为 4 级
- ✅ Auth Service (`app/main.py`) - 路径深度确认为 4 级

### 2. 工具支持
- ✅ 创建启动脚本：`scripts/start_service_local.sh`
- ✅ 更新 README.md 文档
- ✅ 创建完整的故障排查文档

## 立即启动（3 步）

### Step 1: 激活虚拟环境
```bash
source venv/bin/activate
```

### Step 2: 启动基础设施（如果还没启动）
```bash
docker-compose up -d mariadb redis nacos jaeger prometheus grafana
```

### Step 3: 在不同终端启动各个服务

**终端1 - 认证服务 (8001)**
```bash
./scripts/start_service_local.sh auth
```

**终端2 - 管理服务 (8002)**
```bash
./scripts/start_service_local.sh admin
```

**终端3 - 主机服务 (8003)**
```bash
./scripts/start_service_local.sh host
```

**终端4 - 网关服务 (8000) - 最后启动**
```bash
./scripts/start_service_local.sh gateway
```

## 或者使用完全兼容的方式

```bash
# 激活虚拟环境和设置 PYTHONPATH
source venv/bin/activate
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# 在不同终端启动
python -m uvicorn services.gateway-service.app.main:app --host 0.0.0.0 --port 8000 --reload
python -m uvicorn services.auth-service.app.main:app --host 0.0.0.0 --port 8001 --reload
python -m uvicorn services.admin-service.app.main:app --host 0.0.0.0 --port 8002 --reload
python -m uvicorn services.host-service.app.main:app --host 0.0.0.0 --port 8003 --reload
```

## 关键要点

✅ **必须做的**：
- 使用虚拟环境
- 使用 `python -m uvicorn` 命令
- 在不同终端启动服务

❌ **不能做的**：
- 不能使用直接的 `uvicorn` 命令
- 不能在同一终端启动多个服务
- 不能不激活虚拟环境

## Docker 启动完全不受影响

```bash
# Docker 启动方式完全不变
docker-compose up -d
```

所有修复都是向后兼容的！

## 访问服务

启动完成后，访问：
- 🌐 Gateway: http://localhost:8000/docs
- 🔐 Auth: http://localhost:8001/docs
- 👤 Admin: http://localhost:8002/docs
- 🖥️  Host: http://localhost:8003/docs

## 需要帮助？

查看详细文档：
```bash
# 完整修复说明
docs/LOCAL_DEVELOPMENT_FIX.md

# 本地启动快速指南
LOCAL_STARTUP_GUIDE.md
```

---

**问题已完全解决！现在就开始启动吧 🚀**
