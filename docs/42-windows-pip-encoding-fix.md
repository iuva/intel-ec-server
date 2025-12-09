# Windows pip 安装 requirements.txt 编码错误解决方案

## 🐛 问题描述

在 Windows 上使用 pip 安装 `requirements.txt` 时遇到以下错误：

```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d in position 163
```

## 🔍 问题原因

`requirements.txt` 文件包含中文注释，文件使用 **UTF-8** 编码保存，但 Windows 默认使用 **GBK** 或 **cp1252** 编码读取文件，导致无法正确解码 UTF-8 字符。

## ✅ 解决方案

### 方案 1：设置环境变量（推荐）

在安装依赖前，设置环境变量强制使用 UTF-8 编码：

#### PowerShell（推荐）

```powershell
# 临时设置（仅当前会话有效）
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8=1

# 然后安装依赖
pip install -r requirements.txt
```

#### CMD

```cmd
# 临时设置（仅当前会话有效）
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

# 然后安装依赖
pip install -r requirements.txt
```

#### 永久设置（系统级）

**PowerShell（管理员权限）**：
```powershell
[System.Environment]::SetEnvironmentVariable('PYTHONIOENCODING', 'utf-8', 'Machine')
[System.Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'Machine')
```

**CMD（管理员权限）**：
```cmd
setx PYTHONIOENCODING "utf-8" /M
setx PYTHONUTF8 "1" /M
```

设置后需要**重新打开终端**才能生效。

---

### 方案 2：使用 chcp 命令改变代码页

在安装依赖前，将代码页改为 UTF-8（代码页 65001）：

```cmd
# 查看当前代码页
chcp

# 切换到 UTF-8 代码页
chcp 65001

# 然后安装依赖
pip install -r requirements.txt
```

**注意**：此方法仅对当前 CMD 窗口有效，关闭窗口后需要重新设置。

---

### 方案 3：使用 PowerShell 的 UTF-8 模式（Windows 10 1809+）

在 PowerShell 中启用 UTF-8 输出：

```powershell
# 设置输出编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 设置输入编码为 UTF-8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# 然后安装依赖
pip install -r requirements.txt
```

---

### 方案 4：使用 Python 脚本安装（最可靠）

创建一个 Python 脚本，使用 UTF-8 编码读取 requirements.txt：

**`install_requirements.py`**：
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""使用 UTF-8 编码安装 requirements.txt"""

import subprocess
import sys
import os

def install_requirements():
    """安装 requirements.txt"""
    requirements_file = "requirements.txt"
    
    if not os.path.exists(requirements_file):
        print(f"错误: 找不到 {requirements_file} 文件")
        sys.exit(1)
    
    # 使用 UTF-8 编码读取 requirements.txt
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = f.read()
    
    # 临时创建纯 ASCII 版本的 requirements（移除中文注释）
    temp_file = "requirements_temp.txt"
    with open(temp_file, 'w', encoding='utf-8') as f:
        for line in requirements.splitlines():
            # 保留所有行（包括中文注释）
            f.write(line + '\n')
    
    try:
        # 使用 subprocess 调用 pip，设置环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', temp_file],
            env=env,
            check=False
        )
        
        return result.returncode
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == '__main__':
    exit_code = install_requirements()
    sys.exit(exit_code)
```

**使用方法**：
```powershell
# 运行脚本
python install_requirements.py
```

---

### 方案 5：使用虚拟环境 + 环境变量（最佳实践）

创建虚拟环境时设置环境变量：

**PowerShell**：
```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 设置编码环境变量
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8=1

# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

**CMD**：
```cmd
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate.bat

# 设置编码环境变量
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

---

## 🎯 推荐方案

**对于一次性安装**：使用**方案 1**（设置环境变量）

**对于长期开发**：使用**方案 5**（虚拟环境 + 环境变量），并在项目文档中记录此配置

**对于自动化脚本**：使用**方案 4**（Python 脚本）

---

## 🔧 验证修复

安装完成后，验证是否成功：

```powershell
# 检查已安装的包
pip list

# 验证关键包是否安装
python -c "import fastapi; print(fastapi.__version__)"
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

---

## 📝 预防措施

### 1. 在项目 README 中添加说明

在项目 README 中添加 Windows 编码问题的说明：

```markdown
## Windows 用户注意

如果遇到 `UnicodeDecodeError` 错误，请先设置环境变量：

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8=1
```

然后运行 `pip install -r requirements.txt`
```

### 2. 创建安装脚本

创建 `install.bat` 或 `install.ps1` 脚本，自动设置环境变量：

**`install.ps1`**：
```powershell
# 设置编码环境变量
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8=1

# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

**`install.bat`**：
```batch
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python -m pip install --upgrade pip
pip install -r requirements.txt
pause
```

---

## 🚨 常见错误

### 错误 1：环境变量设置后仍然报错

**原因**：环境变量设置后没有重新打开终端，或者设置的是用户级环境变量但使用了系统级终端。

**解决**：
1. 关闭当前终端，重新打开
2. 确认环境变量已设置：`echo $env:PYTHONIOENCODING` (PowerShell) 或 `echo %PYTHONIOENCODING%` (CMD)

### 错误 2：chcp 65001 后仍然报错

**原因**：某些版本的 Windows 对 UTF-8 代码页支持不完整。

**解决**：使用方案 1（环境变量）或方案 4（Python 脚本）

### 错误 3：虚拟环境中仍然报错

**原因**：虚拟环境激活后，环境变量没有正确传递。

**解决**：
1. 在激活虚拟环境**之后**设置环境变量
2. 或者在虚拟环境的激活脚本中添加环境变量设置

---

## 📚 相关文档

- [本地开发环境搭建](./33-local-development-setup.md) - 完整的 Windows 开发环境配置
- [快速开始指南](./00-quick-start.md) - 项目快速开始
- [项目设置](./04-project-setup.md) - 详细的项目配置说明

---

## 📅 更新历史

- **2025-01-29**: 初始版本，整理 Windows pip 编码错误解决方案
- **核心内容**:
  - 5 种解决方案（环境变量、chcp、PowerShell UTF-8、Python 脚本、虚拟环境）
  - 推荐方案和最佳实践
  - 预防措施和常见错误处理

