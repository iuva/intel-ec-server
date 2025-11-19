# Pyright 故障排除指南

## 🐛 问题：运行 pyright 显示 207 个错误

### 症状

运行 `pyright services/ shared/` 时，看到大量类似的错误：

```
# 注意：admin-service 已删除，以下错误示例仅供参考
# /Users/chiyeming/KiroProjects/intel_ec_ms/services/auth-service/app/main.py:17:10 - error: Import "shared.common.database" could not be resolved (reportMissingImports)
# /Users/chiyeming/KiroProjects/intel_ec_ms/services/auth-service/app/main.py:18:10 - error: Import "shared.common.loguru_config" could not be resolved (reportMissingImports)
...
207 errors, 0 warnings, 0 informations
```

### 根本原因

**Pyright 无法找到 `shared` 模块的路径。**

可能的原因：
1. 没有设置 `PYTHONPATH` 环境变量
2. 在错误的目录下运行 pyright
3. `pyrightconfig.json` 配置被修改或损坏
4. Pyright 缓存问题

---

## ✅ 解决方案

### 方案 1：使用提供的脚本（推荐）

```bash
cd /Users/chiyeming/KiroProjects/intel_ec_ms
./scripts/run_pyright.sh
```

这个脚本会自动设置正确的 PYTHONPATH。

### 方案 2：手动设置 PYTHONPATH

```bash
cd /Users/chiyeming/KiroProjects/intel_ec_ms
export PYTHONPATH=$PWD
pyright services/ shared/
```

或者一行命令：

```bash
PYTHONPATH=$PWD pyright services/ shared/
```

### 方案 3：验证 pyrightconfig.json

确保文件包含以下配置：

```json
{
  "extraPaths": ["."],
  "executionEnvironments": [
    {
      "root": "services/gateway-service",
      "pythonVersion": "3.8",
      "extraPaths": ["../../"]
    },
    // ... 其他服务
  ]
}
```

### 方案 4：清除 Pyright 缓存

```bash
# 删除缓存
rm -rf .pyright/
rm -rf **/.pyright/

# 重新运行
./scripts/run_pyright.sh
```

---

## 🔍 诊断步骤

### 1. 检查当前目录

```bash
pwd
# 应该输出: /Users/chiyeming/KiroProjects/intel_ec_ms
```

如果不在项目根目录，先切换到根目录。

### 2. 检查 PYTHONPATH

```bash
echo $PYTHONPATH
```

- 如果输出为空或不是项目路径 → 需要设置
- 如果输出项目路径 → PYTHONPATH 正确

### 3. 验证 shared 模块

```bash
python -c "import shared.common.database; print('成功')"
```

- 如果报错 → Python 路径问题
- 如果成功 → 只是 Pyright 配置问题

### 4. 测试单个文件

```bash
PYTHONPATH=$PWD pyright services/host-service/app/main.py
```

看看单个文件是否能正确检查。

### 5. 查看 Pyright 版本

```bash
pyright --version
```

确保版本是 1.1.405 或更高。

---

## 📊 错误数量参考

| 状态 | 错误数 | 说明 |
|------|--------|------|
| ❌ **配置错误** | **207 个** | 大部分是 `reportMissingImports` |
| ✅ **配置正确** | **56 个** | 真实的代码问题 |
| 🎯 **禁用 FastAPI 警告后** | **6 个** | 需要修复的问题 |

---

## 🔧 常见问题解答

### Q1: 为什么 tmp.md 显示 207 个错误？

**A:** 因为运行 pyright 时没有正确设置 PYTHONPATH。

**解决：** 使用 `./scripts/run_pyright.sh` 或 `PYTHONPATH=$PWD pyright services/ shared/`

### Q2: 修复后还是 56 个错误正常吗？

**A:** 是的！这些是真实的代码问题：
- ~50 个是 FastAPI 的 `Depends()` 用法（可以忽略或禁用）
- ~6 个是需要修复的真实问题

### Q3: 如何只显示需要修复的问题？

**A:** 在 `pyrightconfig.json` 中添加：

```json
{
  "reportCallInDefaultInitializer": false
}
```

这会隐藏 FastAPI 依赖注入的警告。

### Q4: CI/CD 中如何运行？

**A:** 在 CI 脚本中设置 PYTHONPATH：

```yaml
steps:
  - name: Type Check
    run: |
      cd $GITHUB_WORKSPACE
      export PYTHONPATH=$PWD
      pyright services/ shared/
```

### Q5: VS Code 中也报错怎么办？

**A:** 配置 VS Code 的 settings.json：

```json
{
  "python.analysis.extraPaths": ["${workspaceFolder}"],
  "python.analysis.typeCheckingMode": "basic"
}
```

---

## 🎯 最佳实践

### ✅ 推荐做法

```bash
# 1. 使用脚本
./scripts/run_pyright.sh

# 2. 或在命令中设置 PYTHONPATH
PYTHONPATH=$PWD pyright services/ shared/

# 3. 在 shell 中导出变量（一次性）
export PYTHONPATH=$PWD
pyright services/ shared/
```

### ❌ 避免做法

```bash
# 不要直接运行（会报 207 个错误）
pyright services/ shared/

# 不要在错误的目录运行
cd services/
pyright .  # 错误的路径

# 不要使用相对路径设置 PYTHONPATH
PYTHONPATH=. pyright services/ shared/  # 不够明确
```

---

## 📈 修复进度追踪

修复 Pyright 错误的进展：

1. ✅ **初始状态** - 983 个错误（严格模式 + 缺少配置）
2. ✅ **配置优化** - 56 个错误（basic 模式 + 正确路径）
3. 🔄 **可选优化** - 6 个错误（禁用 FastAPI 警告后）
4. 🎯 **目标** - 0 个错误（修复所有真实问题）

---

## 🆘 仍然有问题？

### 完全重置配置

```bash
# 1. 备份当前配置
cp pyrightconfig.json pyrightconfig.json.backup

# 2. 恢复到已知的良好配置
# （从 Git 或文档中获取）

# 3. 清除缓存
rm -rf .pyright/

# 4. 重新运行
./scripts/run_pyright.sh
```

### 检查文件是否存在

```bash
# 检查关键文件
ls -la pyrightconfig.json
ls -la shared/py.typed
ls -la .env
```

### 验证项目结构

```bash
# 确保目录结构正确
tree -L 2 -I 'venv|__pycache__|*.pyc'
```

---

## 📞 获取帮助

如果以上方法都不能解决问题：

1. 查看详细错误日志
2. 检查 Pyright 官方文档
3. 确认 Python 版本（应该是 3.8.10）
4. 查看项目的 [PYRIGHT_FIXES_SUMMARY.md](./PYRIGHT_FIXES_SUMMARY.md)

---

**记住：207 个错误 → 56 个错误，只需要正确设置 PYTHONPATH！** 🚀
