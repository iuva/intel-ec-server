# Pyright 类型检查完整指南

本目录包含 Pyright 类型检查的完整配置和文档。

---

## 📚 文档索引

### 🚀 快速开始
- **[PYRIGHT_QUICK_GUIDE.md](./PYRIGHT_QUICK_GUIDE.md)** - 快速使用指南，5 分钟上手

### 📖 完整文档
- **[PYRIGHT_FIXES_SUMMARY.md](./PYRIGHT_FIXES_SUMMARY.md)** - 修复总结，包含所有修复步骤和详细说明

### 🐛 故障排除
- **[PYRIGHT_TROUBLESHOOTING.md](./PYRIGHT_TROUBLESHOOTING.md)** - 常见问题和解决方案

### ⚙️ 配置文件
- **[pyrightconfig.json](./pyrightconfig.json)** - Pyright 配置文件
- **[.env](./.env)** - 环境变量配置
- **[shared/py.typed](./shared/py.typed)** - 类型检查标记文件

---

## ⚡ 30秒快速开始

```bash
# 1. 进入项目目录
cd /Users/chiyeming/KiroProjects/intel_ec_ms

# 2. 运行类型检查
./scripts/check_types.sh
```

就这么简单！✅

---

## ❗ 重要提示

### ⚠️ 如果看到 207 个错误

**原因：** 没有正确设置 PYTHONPATH

**解决：** 使用以下任一方式

```bash
# 方式 1：使用脚本（推荐）
./scripts/check_types.sh

# 方式 2：手动设置 PYTHONPATH
PYTHONPATH=$PWD pyright services/ shared/
```

详见 [故障排除指南](./PYRIGHT_TROUBLESHOOTING.md)。

---

## 📊 错误数量说明

| 运行方式 | 错误数 | 状态 |
|---------|--------|------|
| 没有 PYTHONPATH | **207** | ❌ 虚假错误 |
| 正确设置 PYTHONPATH | **56** | ✅ 真实问题 |
| 禁用 FastAPI 警告 | **6** | 🎯 需要修复 |

---

## 🎯 修复进度

- ✅ **第一阶段** - 从 983 → 56 个错误（94.3% 减少）
- ✅ **第二阶段** - 配置文档和脚本
- 🔄 **第三阶段** - 可选：修复剩余 56 个问题

---

## 📋 剩余错误分类

### 1. FastAPI 依赖注入 (~50 个) ✅ 可以忽略

```python
# 这是 FastAPI 标准用法，不是错误
@app.get("/users")
async def get_users(
    db: AsyncSession = Depends(get_db_session),  # Pyright 警告
):
    pass
```

**解决方案：** 在 pyrightconfig.json 中设置 `"reportCallInDefaultInitializer": false`

### 2. 代码问题 (~6 个) ⚠️ 需要修复

- 参数类型不匹配
- 隐式字符串连接
- 可选属性访问

详见 [修复总结](./PYRIGHT_FIXES_SUMMARY.md)。

---

## 🛠️ 工具和脚本

### 提供的脚本

```bash
# 运行 Pyright 检查（自动设置 PYTHONPATH）
./scripts/check_types.sh

# 运行代码质量检查（包含 Ruff + Pyright）
./scripts/check_quality.sh
```

### 配置文件说明

- **pyrightconfig.json** - 类型检查规则和路径配置
- **shared/py.typed** - 标记 shared 包支持类型检查
- **.env** - PYTHONPATH 等环境变量配置

---

## 📖 学习路径

### 初次使用

1. 阅读 [快速指南](./PYRIGHT_QUICK_GUIDE.md)（5 分钟）
2. 运行 `./scripts/check_types.sh`
3. 查看错误报告

### 深入了解

1. 阅读 [修复总结](./PYRIGHT_FIXES_SUMMARY.md)（20 分钟）
2. 了解每个修复步骤的原理
3. 学习最佳实践

### 遇到问题

1. 查看 [故障排除指南](./PYRIGHT_TROUBLESHOOTING.md)
2. 检查常见问题解答
3. 按步骤诊断问题

---

## 🔗 相关资源

### 官方文档

- [Pyright 官方文档](https://github.com/microsoft/pyright)
- [Pyright 配置说明](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)
- [PEP 561 - 类型信息分发](https://peps.python.org/pep-0561/)

### 项目文档

- [FastAPI 依赖注入](https://fastapi.tiangulo.com/tutorial/dependencies/)
- [Python 类型提示](https://docs.python.org/3/library/typing.html)

---

## ✨ 最佳实践

### ✅ 推荐做法

1. **始终使用脚本运行 Pyright**
   ```bash
   ./scripts/check_types.sh
   ```

2. **定期运行类型检查**
   ```bash
   # 提交代码前
   ./scripts/check_types.sh
   git commit -m "..."
   ```

3. **在 CI/CD 中集成**
   ```yaml
   - name: Type Check
     run: |
       export PYTHONPATH=$PWD
       pyright services/ shared/
   ```

### ❌ 避免做法

1. **不要直接运行 pyright**（会报 207 个错误）
   ```bash
   pyright services/ shared/  # ❌ 错误
   ```

2. **不要忽略真实的类型错误**
   - FastAPI 依赖注入警告可以忽略
   - 但参数类型不匹配等问题需要修复

3. **不要修改 pyrightconfig.json 而不理解**
   - 配置是经过优化的
   - 修改前先阅读文档

---

## 🎓 团队协作

### 新成员入职

1. 克隆项目
2. 阅读 [快速指南](./PYRIGHT_QUICK_GUIDE.md)
3. 运行 `./scripts/check_types.sh`
4. 了解当前的 56 个错误

### Code Review

- 检查新代码是否增加了类型错误
- 鼓励添加类型注解
- 使用 Pyright 检查作为 PR 检查项

### 持续改进

- 定期更新 Pyright 版本
- 逐步修复剩余错误
- 分享类型检查经验

---

## 📈 统计数据

### 修复成果

- **初始错误数：** 983
- **当前错误数：** 56
- **减少率：** 94.3%
- **修复时间：** 2025-10-13

### 错误分布

| 错误类型 | 数量 | 占比 |
|---------|------|------|
| FastAPI Depends() | 50 | 89% |
| 字符串拼接 | 3 | 5% |
| 其他代码问题 | 3 | 6% |

---

## 📞 获取帮助

### 查看文档

1. [快速指南](./PYRIGHT_QUICK_GUIDE.md) - 基本使用
2. [故障排除](./PYRIGHT_TROUBLESHOOTING.md) - 解决问题
3. [修复总结](./PYRIGHT_FIXES_SUMMARY.md) - 完整说明

### 常见问题

- **207 个错误？** → 查看 [故障排除](./PYRIGHT_TROUBLESHOOTING.md)
- **如何运行？** → 查看 [快速指南](./PYRIGHT_QUICK_GUIDE.md)
- **错误含义？** → 查看 [修复总结](./PYRIGHT_FIXES_SUMMARY.md)

---

**开始使用：`./scripts/check_types.sh`** 🚀
