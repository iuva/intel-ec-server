# 代码质量保证系统设置文档

## 概述

本文档描述了 Intel EC 微服务项目的代码质量保证系统的配置和使用方法。

## 已配置的工具

### 1. Ruff - 快速 Python 代码检查器和格式化工具

**配置文件**: `.ruff.toml`

**功能**:

- 代码风格检查（PEP 8）
- 代码格式化（替代 Black，速度提升 10-100 倍）
- 导入排序（替代 isort）
- 常见错误检测
- 代码简化建议
- 性能优化建议
- 安全检查（集成 Bandit 规则）

**使用方法**:

```bash
# 检查代码
ruff check services/ shared/

# 自动修复
ruff check --fix services/ shared/

# 代码格式化（替代 black）
ruff format services/ shared/

# 格式检查（不修改文件）
ruff format --check services/ shared/

# 检查特定规则
ruff check --select I services/ shared/  # 仅检查导入排序
```

### 2. MyPy - 静态类型检查器

**配置文件**: `.pre-commit-config.yaml`

**功能**:

- 提交前自动检查
- 集成多个检查工具
- 自动修复简单问题

**使用方法**:

```bash
# 安装 pre-commit
bash scripts/setup_pre_commit.sh

# 手动运行所有检查
pre-commit run --all-files

# 跳过检查提交（不推荐）
git commit --no-verify
```

## 快速开始

### 安装依赖

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install ruff mypy pytest pytest-asyncio pytest-cov

# 注意：Black 已被移除，使用 Ruff Format 替代
```

### 运行代码质量检查

```bash
# 运行完整检查
bash scripts/check_quality.sh

# 自动修复问题
bash scripts/fix_quality.sh

# 安装 Git 钩子
bash scripts/setup_pre_commit.sh
```

## 配置说明

### Ruff 配置重点

```toml
# .ruff.toml
target-version = "py38"  # Python 3.8 兼容
line-length = 88         # 每行最大字符数

[lint]
select = [
    "E",    # pycodestyle 错误
    "W",    # pycodestyle 警告
    "F",    # Pyflakes
    "I",    # isort 导入排序
    "N",    # pep8-naming 命名规范
    "UP",   # pyupgrade 现代化语法
    "B",    # flake8-bugbear 常见错误
    "C4",   # flake8-comprehensions 推导式优化
    "SIM",  # flake8-simplify 代码简化
    "S",    # flake8-bandit 安全检查
    "PERF", # Perflint 性能优化
    "RUF",  # Ruff 特定规则
]

ignore = [
    "E501",    # 行长度由 Ruff Format 处理
    "B008",    # FastAPI Depends 需要
    "RUF001",  # 中文全角标点（项目使用中文）
    "RUF002",  # 中文文档字符串全角标点
    "RUF003",  # 中文注释全角标点
]

[format]
quote-style = "double"    # 使用双引号
indent-style = "space"    # 使用空格缩进
line-ending = "auto"      # 自动检测行结束符
```

### MyPy 配置重点

```ini
# mypy.ini
[mypy]
python_version = 3.8

# 宽松模式配置
disallow_untyped_defs = False
disallow_incomplete_defs = False
check_untyped_defs = False

# 禁用特定错误
disable_error_code = no-untyped-def, valid-type

# 忽略第三方库
ignore_missing_imports = True
```

### Black 配置重点

```toml
# ❌ Black 已被移除，使用 Ruff Format 替代
# Ruff Format 是 Black 兼容的格式化工具，速度提升 10-100 倍
# 配置在 .ruff.toml 的 [format] 部分
```

## 代码质量标准

### 必须通过的检查

- ✅ Ruff 代码检查（无错误）
- ✅ Ruff 格式检查（格式正确，替代 Black）
- ✅ MyPy 类型检查（无严重类型错误）
- ✅ Bandit 安全检查（无高危安全问题）

### 代码规范

1. **命名规范**
   - 类名：PascalCase（如 `UserService`）
   - 函数名：snake_case（如 `get_user_by_id`）
   - 常量：UPPER_CASE（如 `MAX_RETRY_COUNT`）
   - 私有成员：前缀下划线（如 `_internal_method`）

2. **导入规范**
   - 标准库导入
   - 第三方库导入
   - 本地应用导入
   - 每组之间空两行

3. **文档规范**
   - 所有公共函数必须有文档字符串
   - 使用中文编写文档
   - 包含参数说明和返回值说明

4. **类型注解规范**
   - 函数参数添加类型注解
   - 函数返回值添加类型注解
   - 使用 `Optional` 表示可能为 None 的值

## 常见问题

### 1. Ruff 检查失败

**问题**: 代码不符合规范

**解决方案**:

```bash
# 自动修复大部分问题
ruff check --fix services/ shared/

# 查看具体错误
ruff check services/ shared/
```

### 2. 代码格式检查失败

**问题**: 代码格式不正确

**解决方案**:

```bash
# 自动格式化（使用 Ruff Format）
ruff format services/ shared/
```

### 3. MyPy 类型检查失败

**问题**: 类型注解错误

**解决方案**:

- 添加缺失的类型注解
- 使用 `# type: ignore` 忽略特定行（不推荐）
- 更新 `mypy.ini` 配置

### 4. Pre-commit 钩子失败

**问题**: 提交时检查失败

**解决方案**:

```bash
# 运行自动修复
bash scripts/fix_quality.sh

# 重新提交
git add .
git commit -m "fix: 修复代码质量问题"
```

## 持续改进

### 短期目标

- [x] 配置基础代码质量工具
- [x] 创建自动化检查脚本
- [x] 修复现有代码质量问题
- [ ] 提高 MyPy 类型检查严格度
- [ ] 添加更多代码质量规则

### 长期目标

- [ ] 集成到 CI/CD 流程
- [ ] 添加代码覆盖率检查
- [ ] 添加安全扫描工具
- [ ] 建立代码审查流程

## 参考资料

- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Ruff Format 文档](https://docs.astral.sh/ruff/formatter/)
- [MyPy 文档](https://mypy.readthedocs.io/)
- [Pyright 文档](https://microsoft.github.io/pyright/)
- [Bandit 文档](https://bandit.readthedocs.io/)
- [Pre-commit 文档](https://pre-commit.com/)
- [PEP 8 风格指南](https://peps.python.org/pep-0008/)

## 更新历史

- **2025-10-13**: 工具栈优化，移除 Black
  - ❌ 移除 Black，统一使用 Ruff Format（速度提升 10-100 倍）
  - ✅ 合并 auth-service 的 Ruff 配置到根目录
  - ✅ 更新所有脚本和文档
  - ✅ 简化工具栈，减少维护复杂度
  - 详见：[13-code-quality-tools-analysis.md](./13-code-quality-tools-analysis.md)

- **2025-01-29**: 初始版本，完成代码质量保证系统配置
  - 配置 Ruff、MyPy、Black
  - 创建自动化检查和修复脚本
  - 配置 Pre-commit 钩子
  - 修复现有代码质量问题
