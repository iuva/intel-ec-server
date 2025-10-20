# 本地开发启动问题修复说明

## 🎯 问题描述

在本地启动 Gateway Service 时出现错误：
```
ModuleNotFoundError: No module named 'app'
```

## 🔍 根本原因

1. **路径深度计算错误**：各个服务的 `main.py` 文件中的路径导入深度不正确
   - Gateway Service: `../../..` (3级) → 应改为 `../../../../..` (4级)
   - Host Service: `../../..` (3级) → 应改为 `../../../../..` (4级)
   - Admin Service: `../../..` (3级) → 应改为 `../../../../..` (4级)
   - Auth Service: `../../../..` (4级) → 确认一致为 `../../../../..` (4级)

2. **启动方式不正确**：直接使用 `uvicorn` 而不是 `python -m uvicorn`

## ✅ 修复方案

### 已完成的修复：

#### 1. 路径深度修正
已修正所有 4 个服务的 `app/main.py` 文件中的路径导入深度为统一的 4 级：
- ✅ `services/gateway-service/app/main.py` - 第 31 行
- ✅ `services/host-service/app/main.py` - 第 32 行  
- ✅ `services/admin-service/app/main.py` - 第 27 行
- ✅ `services/auth-service/app/main.py` - 第 26 行

#### 2. 创建启动脚本
创建了 `scripts/start_service_local.sh` 脚本，用于本地开发启动

#### 3. 更新文档
在 `README.md` 中添加了本地启动的详细说明

## 🚀 现在如何启动

### 方式 1：使用启动脚本（推荐）

```bash
# 激活虚拟环境
source venv/bin/activate

# 在不同终端启动不同服务
./scripts/start_service_local.sh auth    # 终端1
./scripts/start_service_local.sh admin   # 终端2
./scripts/start_service_local.sh host    # 终端3
./scripts/start_service_local.sh gateway # 终端4
```

### 方式 2：使用 Python -m 模块方式（完全兼容 Docker）

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置 PYTHONPATH（可选但推荐）
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# 在不同终端启动不同服务
python -m uvicorn services.gateway-service.app.main:app --host 0.0.0.0 --port 8000 --reload
python -m uvicorn services.auth-service.app.main:app --host 0.0.0.0 --port 8001 --reload
python -m uvicorn services.admin-service.app.main:app --host 0.0.0.0 --port 8002 --reload
python -m uvicorn services.host-service.app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 方式 3：进入服务目录启动

```bash
# 进入服务目录
cd services/gateway-service

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔑 关键要点

### ✅ 必须做的事：
- 激活虚拟环境：`source venv/bin/activate`
- 使用 `python -m uvicorn` 而非直接 `uvicorn`
- 在不同终端启动各个服务
- 建议启动顺序：auth → admin → host → gateway

### ❌ 避免做的事：
- ❌ 不要直接使用 `uvicorn` 命令
- ❌ 不要在同一终端启动多个服务
- ❌ 不要在项目目录之外启动
- ❌ 不要修改已修正的路径（保持 4 级一致）

## 🐳 Docker 启动不受影响

所有修复都是向后兼容的，Docker 启动方式完全不变：

```bash
# Docker Compose 启动完全兼容
docker-compose up -d
```

原因是 Docker 中工作目录已正确设置，首次导入成功，不会进入 except 块。

## 📊 路径深度说明

项目结构示例：
```
intel_ec_ms/                    (项目根目录) ← 目标
├── services/
│   ├── gateway-service/        (1级)
│   │   ├── app/                (2级)
│   │   │   ├── main.py         (3级)
│   │   │   └── api/
│   │   │       └── v1/
│   │   │           └── endpoints/
│   │   │               └── proxy.py  (5级)
```

从 `main.py` (3级) 向上到项目根目录 = 需要 4 级 (`../../../../..`)
从 `endpoints/proxy.py` (5级) 向上到项目根目录 = 需要 5 级 (`../../../../..` - 相对于文件的位置)

## ✔️ 验证修复

启动后，应该看到类似的输出：

```
INFO:     Will watch for changes in these directories: ['/Users/chiyeming/KiroProjects/intel_ec_ms']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

然后访问服务健康检查：
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

应该都返回 `{"status":"healthy",...}`

## 💡 故障排查

### 如果仍然出现 ModuleNotFoundError

1. 检查虚拟环境是否激活：
   ```bash
   which python  # 应该显示 venv/bin/python
   ```

2. 检查 PYTHONPATH：
   ```bash
   echo $PYTHONPATH  # 应该包含项目路径
   ```

3. 验证路径修复：
   ```bash
   grep -n "sys.path.insert" services/gateway-service/app/main.py
   # 应该显示：31:    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
   ```

4. 重新激活虚拟环境：
   ```bash
   deactivate
   source venv/bin/activate
   ```

## 📝 更新历史

- **2025-10-20**：修复本地启动路径深度问题，创建启动脚本，更新文档

## 🔗 相关文件

- 启动脚本：`scripts/start_service_local.sh`
- 修复说明：`docs/LOCAL_DEVELOPMENT_FIX.md`
- 更新文档：`README.md` - "运行服务（本地开发模式）"部分
