# Pyright 快速使用指南

## ⚡ 快速开始

### ✅ 正确的运行方式

```bash
# 推荐：使用便捷脚本
./scripts/run_pyright.sh

# 或者手动设置 PYTHONPATH
cd /Users/chiyeming/KiroProjects/intel_ec_ms
PYTHONPATH=$PWD pyright services/ shared/
```

### ❌ 错误的运行方式

```bash
# 这样会报 207 个错误！
pyright services/ shared/
```

---

## 📊 错误数量说明

| 运行方式 | 错误数 | 状态 |
|---------|--------|------|
| **没有设置 PYTHONPATH** | 207 个 | ❌ 大部分是虚假的导入错误 |
| **正确设置 PYTHONPATH** | 56 个 | ✅ 真实的代码问题 |

---

## 🔧 为什么需要 PYTHONPATH？

Pyright 需要知道 `shared` 模块的位置。通过设置 `PYTHONPATH=$PWD`，我们告诉 Pyright：

- `shared` 模块在项目根目录下
- 可以直接 `import shared.common.database` 等

没有 PYTHONPATH，Pyright 找不到 `shared` 模块，会报告大量 `reportMissingImports` 错误。

---

## 📝 剩余 56 个错误的类型

### 1. FastAPI 依赖注入 (~50 个) - 可以忽略
```python
# Pyright 警告，但这是 FastAPI 标准用法
@app.get("/users")
async def get_users(
    db: AsyncSession = Depends(get_db_session),  # ← 报错但正常
):
    ***REMOVED***
```

### 2. 字符串拼接 (~3 个) - 容易修复
```python
# 隐式字符串连接
logger.error(
    "错误: "  # ← 需要改为 + 或 f-string
    f"{message}"
)
```

### 3. 其他代码问题 (~3 个) - 需要修复
- 参数类型不匹配
- 可选属性访问

---

## 🎯 如何禁用 FastAPI 依赖注入警告

如果不想看到 50 个 FastAPI 相关警告，在 `pyrightconfig.json` 中添加：

```json
{
  "reportCallInDefaultInitializer": false
}
```

修改后只会显示 6 个真实的代码问题。

---

## 🚀 推荐工作流程

### 日常开发

```bash
# 1. 运行快速检查
./scripts/run_pyright.sh

# 2. 如果有错误，查看具体位置
PYTHONPATH=$PWD pyright services/ shared/ | less

# 3. 修复代码问题
# 编辑文件...

# 4. 再次验证
./scripts/run_pyright.sh
```

### CI/CD 集成

```yaml
# .github/workflows/type-check.yml
- name: Type Check
  run: |
    export PYTHONPATH=$PWD
    pyright services/ shared/
```

---

## ❓ 常见问题

### Q: 为什么我的错误数和文档不一致？

**A:** 检查是否设置了 PYTHONPATH：
```bash
# 检查环境变量
echo $PYTHONPATH

# 应该输出项目根目录路径
# 如果是空的，就需要设置
export PYTHONPATH=$PWD
```

### Q: 每次都要设置 PYTHONPATH 很麻烦？

**A:** 使用提供的脚本：
```bash
# 简单！自动设置 PYTHONPATH
./scripts/run_pyright.sh
```

### Q: 可以在 IDE 中使用吗？

**A:** 是的，配置 VS Code：
```json
// .vscode/settings.json
{
  "python.analysis.extraPaths": ["${workspaceFolder}"],
  "python.analysis.typeCheckingMode": "basic"
}
```

---

## 📚 相关文档

- 完整修复总结：[PYRIGHT_FIXES_SUMMARY.md](./PYRIGHT_FIXES_SUMMARY.md)
- Pyright 配置：[pyrightconfig.json](./pyrightconfig.json)
- 环境变量配置：[.env](./.env)

---

**记住：运行 pyright 前，一定要设置 PYTHONPATH！** 🎯
