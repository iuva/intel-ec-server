# Host Service 运行指南

## 问题说明

由于项目使用了 `shared` 共享模块，需要正确设置 Python 路径才能导入。我们提供了多种运行方式，**不需要在代码中动态修改 sys.path**。

## 推荐运行方式

### 方式 1：使用启动脚本（最简单）

```bash
# 从 host-service 目录运行
python run.py
```

### 方式 2：从项目根目录运行（推荐用于开发）

```bash
# 从项目根目录运行
python -m services.host_service.app.main
```

### 方式 3：设置 PYTHONPATH 环境变量

```bash
# 设置 PYTHONPATH 为项目根目录
export PYTHONPATH=/path/to/intel-cw-ms

# 然后可以从任何位置运行
cd services/host-service
python app/main.py
```

### 方式 4：Docker 容器运行（生产环境）

```bash
# Docker 会自动设置正确的路径
docker-compose up host-service
```

## 数据库表创建

### 使用模块方式运行

```bash
# 从项目根目录
python -m services.host_service.create_tables
```

### 使用 PYTHONPATH

```bash
export PYTHONPATH=/path/to/intel-cw-ms
cd services/host-service
python create_tables.py
```

## Docker 配置

Dockerfile 中已经正确配置了 PYTHONPATH：

```dockerfile
ENV PYTHONPATH=/app
WORKDIR /app/services/host-service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

## 开发环境配置

### VS Code

在 `.vscode/settings.json` 中添加：

```json
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}"
  ],
  "terminal.integrated.env.linux": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "terminal.integrated.env.osx": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "${workspaceFolder}"
  }
}
```

### PyCharm

1. 右键点击项目根目录
2. 选择 "Mark Directory as" → "Sources Root"
3. PyCharm 会自动将其添加到 PYTHONPATH

## 为什么不在代码中修改 sys.path？

1. **代码质量**: 避免 E402 (module level import not at top of file) 警告
2. **最佳实践**: Python 官方推荐使用 PYTHONPATH 或模块运行方式
3. **可维护性**: 路径配置应该在环境层面，而不是代码层面
4. **一致性**: 所有微服务使用相同的运行方式

## 故障排查

### 问题：ImportError: No module named 'shared'

**原因**: Python 路径未正确设置

**解决方案**:
1. 确认从项目根目录运行
2. 或设置 PYTHONPATH 环境变量
3. 或使用提供的 run.py 启动脚本

### 问题：ModuleNotFoundError: No module named 'app'

**原因**: 当前工作目录不正确

**解决方案**:
使用 `python -m services.host_service.app.main` 从项目根目录运行

## 总结

✅ **推荐**: 使用 `python -m` 模块方式或 `run.py` 脚本  
✅ **生产**: Docker 容器自动处理路径  
❌ **避免**: 在代码中使用 `sys.path.insert()`
